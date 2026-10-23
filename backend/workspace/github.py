"""Signed, replay-safe GitHub webhooks. No access tokens or source code are stored."""
import hashlib
import hmac
import json
import re
from urllib.parse import urlsplit
from django.db import transaction
from django.http import JsonResponse
from django.utils.crypto import salted_hmac
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .access import accessible_projects, current_membership
from .development import lock_project
from .models import AuditEvent, GitHubActivity, GitHubConnection, GitHubDelivery, Task
from .serializers import StrictSerializer
from .team_management import require_admin


def webhook_secret(connection):
    # Derive a distinct high-entropy secret per connection; never expose the Django key.
    return salted_hmac('sprintlens.github.v1', str(connection.pk), algorithm='sha256').hexdigest()


class ConnectionSerializer(StrictSerializer):
    event_count = serializers.SerializerMethodField()
    delivery_count = serializers.SerializerMethodField()
    last_delivery_at = serializers.SerializerMethodField()

    def get_event_count(self, obj):
        return GitHubActivity.objects.filter(connection=obj).count()

    def get_delivery_count(self, obj):
        return GitHubDelivery.objects.filter(connection=obj).count()

    def get_last_delivery_at(self, obj):
        return GitHubDelivery.objects.filter(connection=obj).order_by('-received_at').values_list('received_at', flat=True).first()

    def validate_repository(self, value):
        value = value.lower().strip()
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,38}/[a-z0-9_.-]{1,100}', value):
            raise serializers.ValidationError('Enter a GitHub repository as owner/repository.')
        if GitHubConnection.objects.filter(repository=value).exists():
            raise serializers.ValidationError('This repository is already connected.')
        return value

    def validate_project(self, project):
        if not accessible_projects(current_membership(self.context['request'])).filter(pk=project.pk).exists():
            raise serializers.ValidationError('Choose an accessible project.')
        return project

    class Meta:
        model = GitHubConnection
        fields = ['id', 'project', 'repository', 'enabled', 'event_count', 'delivery_count', 'last_delivery_at', 'created_at']
        read_only_fields = ['id', 'enabled', 'created_at']


class ConnectionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ConnectionSerializer

    def get_queryset(self):
        return GitHubConnection.objects.filter(project__in=accessible_projects(current_membership(self.request)))

    @transaction.atomic
    def perform_create(self, serializer):
        member = lock_project(current_membership(self.request), serializer.validated_data['project'])
        require_admin(member)
        # Serialize duplicate repository checks, including cross-workspace administrators.
        from django.db import IntegrityError
        try:
            with transaction.atomic():
                item = serializer.save()
        except IntegrityError:
            raise serializers.ValidationError('This repository is already connected.')
        AuditEvent.objects.create(project=item.project, actor=self.request.user, action='github.connected', text=f'Configured repository {item.repository}')

    @action(detail=True, methods=['get'])
    def setup(self, request, pk=None):
        require_admin(current_membership(request))
        item = self.get_object()
        response = Response({'webhook_path': f'/api/v1/hooks/github/{item.pk}/', 'secret': webhook_secret(item), 'events': ['push', 'pull_request', 'pull_request_review'], 'content_type': 'application/json'})
        response['Cache-Control'] = 'no-store'
        return response

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def toggle(self, request, pk=None):
        original = self.get_object()
        member = lock_project(current_membership(request), original.project)
        require_admin(member)
        item = GitHubConnection.objects.select_for_update().get(pk=original.pk)
        if set(request.data) != {'enabled'} or not isinstance(request.data['enabled'], bool):
            raise serializers.ValidationError('Send only a boolean enabled value.')
        item.enabled = request.data['enabled']
        item.save(update_fields=['enabled'])
        AuditEvent.objects.create(project=item.project, actor=request.user, action='github.toggled', text=f'Changed repository connection {item.repository}', after={'enabled': item.enabled})
        return Response(self.get_serializer(item).data)


class ActivitySerializer(serializers.ModelSerializer):
    project = serializers.IntegerField(source='connection.project_id', read_only=True)
    repository = serializers.CharField(source='connection.repository', read_only=True)

    class Meta:
        model = GitHubActivity
        fields = ['id', 'project', 'repository', 'task', 'event', 'title', 'actor', 'url', 'external_id', 'at']


class ActivityViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = ActivitySerializer

    def get_queryset(self):
        qs = GitHubActivity.objects.filter(connection__project__in=accessible_projects(current_membership(self.request))).select_related('connection')
        task = self.request.query_params.get('task')
        if task:
            from uuid import UUID
            try:
                task = UUID(task)
            except ValueError:
                raise serializers.ValidationError('Invalid task ID.')
            qs = qs.filter(task_id=task)
        return qs


def safe_url(value, repository):
    if not isinstance(value, str) or len(value) > 1000:
        return ''
    try:
        parts = urlsplit(value)
    except ValueError:
        return ''
    if parts.scheme == 'https' and parts.netloc.lower() == 'github.com' and parts.path.lower().startswith('/' + repository + '/'):
        return value
    return ''


def normalize(payload, event):
    """Store selected event metadata, never raw payloads, code diffs or tokens."""
    actor = str((payload.get('sender') or {}).get('login', 'GitHub'))[:100]
    if event == 'push':
        commits = payload.get('commits', [])
        if not isinstance(commits, list) or len(commits) > 2048:
            raise ValueError('Invalid commit list.')
        return [(str(c.get('message', 'Commit'))[:300], actor, c.get('url', ''), str(c.get('id', ''))[:100], str(c.get('message', ''))[:4000]) for c in commits if isinstance(c, dict)]
    if event in ['pull_request', 'pull_request_review']:
        pr = payload.get('pull_request') or {}
        review = payload.get('review') or {}
        if not isinstance(pr, dict) or not isinstance(review, dict):
            raise ValueError('Invalid pull request.')
        title = f'{payload.get("action", "updated")}: {pr.get("title", "Pull request")}'[:300]
        return [(title, actor, review.get('html_url') or pr.get('html_url', ''), str(review.get('id') or pr.get('number', ''))[:100], str(pr.get('title', '')) + '\n' + str(pr.get('body') or '')[:4000])]
    return []


@csrf_exempt
@require_POST
def github_webhook(request, connection_id):
    # CSRF is replaced only here by HMAC authentication over the exact request bytes.
    if len(request.body) > 1024 * 1024:
        return JsonResponse({'detail': 'Payload too large.'}, status=413)
    connection = GitHubConnection.objects.filter(pk=connection_id).first()
    if not connection:
        return JsonResponse({'detail': 'Unknown connection.'}, status=404)
    expected = 'sha256=' + hmac.new(webhook_secret(connection).encode(), request.body, hashlib.sha256).hexdigest()
    signature = request.headers.get('X-Hub-Signature-256', '')
    if not re.fullmatch(r'sha256=[0-9a-f]{64}', signature) or not hmac.compare_digest(expected, signature):
        return JsonResponse({'detail': 'Invalid signature.'}, status=403)
    delivery = request.headers.get('X-GitHub-Delivery', '')
    event = request.headers.get('X-GitHub-Event', '')
    if not re.fullmatch(r'[a-zA-Z0-9-]{1,100}', delivery):
        return JsonResponse({'detail': 'Missing or invalid delivery ID.'}, status=400)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or not isinstance(payload.get('repository'), dict) or payload['repository'].get('full_name', '').lower() != connection.repository:
            raise ValueError('Repository does not match this connection.')
        rows = normalize(payload, event)
    except (ValueError, TypeError, AttributeError, UnicodeDecodeError):
        return JsonResponse({'detail': 'Invalid event payload or repository.'}, status=400)
    with transaction.atomic():
        # Toggle and deliveries serialize through the connection row.
        connection = GitHubConnection.objects.select_for_update().get(pk=connection.pk)
        if not connection.enabled:
            return JsonResponse({'detail': 'Connection disabled.'}, status=410)
        _, created = GitHubDelivery.objects.get_or_create(connection=connection, delivery_id=delivery)
        if not created:
            return JsonResponse({'duplicate': True})
        tasks = {}
        for task in Task.objects.filter(project=connection.project).select_related('project'):
            tasks.setdefault(f'{task.project.code}-{str(task.pk)[:8]}'.upper(), []).append(task)
        activities = []
        for title, actor, url, external_id, text in rows:
            codes = set(re.findall(r'(?<![A-Z0-9])[A-Z][A-Z0-9]{1,11}-[A-F0-9]{8}(?![A-Z0-9])', text.upper()))
            matches = [task for code in codes for task in tasks.get(code, [])]
            activities.append(GitHubActivity(connection=connection, task=matches[0] if len(matches) == 1 else None, event=event, title=title, actor=actor, url=safe_url(url, connection.repository), external_id=external_id))
        GitHubActivity.objects.bulk_create(activities)
    return JsonResponse({'accepted': True, 'activities': len(rows)})
