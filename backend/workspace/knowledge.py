"""Project-scoped reusable solutions with private drafts and append-only revisions."""
import re
from django.db import transaction
from django.db.models import Q
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from .access import accessible_projects, current_membership
from .development import is_reviewer, lock_project, validate_participant
from .models import ArticleRevision, AuditEvent, KnowledgeArticle
from .serializers import StrictSerializer
from .team_management import expected_version


class ArticleSerializer(StrictSerializer):
    author_name = serializers.CharField(source='author.user.get_full_name', read_only=True)
    content = serializers.CharField(max_length=20000)
    tags = serializers.ListField(child=serializers.CharField(max_length=30), max_length=10, required=False)

    def validate_tags(self, values):
        tags = list(dict.fromkeys(value.strip().lower() for value in values))
        if any(not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,29}', value) for value in tags):
            raise serializers.ValidationError('Tags use lowercase letters, numbers and hyphens (maximum 30 characters).')
        return tags

    def validate(self, attrs):
        member = current_membership(self.context['request'])
        project = attrs.get('project', self.instance.project if self.instance else None)
        if not project or not accessible_projects(member).filter(pk=project.pk).exists():
            raise serializers.ValidationError('Choose an accessible project.')
        if self.instance and 'project' in attrs:
            raise serializers.ValidationError('The article project cannot change.')
        return attrs

    class Meta:
        model = KnowledgeArticle
        fields = ['id', 'project', 'author', 'author_name', 'title', 'summary', 'content', 'tags', 'status', 'version', 'created_at', 'updated_at']
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']


class RevisionSerializer(serializers.ModelSerializer):
    editor_name = serializers.CharField(source='editor.get_full_name', read_only=True)

    class Meta:
        model = ArticleRevision
        fields = ['id', 'version', 'editor_name', 'snapshot', 'at']


class ArticleListSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.user.get_full_name', read_only=True)

    class Meta:
        model = KnowledgeArticle
        fields = ['id', 'project', 'author', 'author_name', 'title', 'summary', 'tags', 'status', 'version', 'created_at', 'updated_at']


def article_snapshot(item):
    return {key: getattr(item, key) for key in ['title', 'summary', 'content', 'tags', 'status']}


class KnowledgeViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ArticleSerializer

    def get_serializer_class(self):
        return ArticleListSerializer if self.action == 'list' else ArticleSerializer

    def get_queryset(self):
        member = current_membership(self.request)
        # A draft is private to its author even when another user administers the workspace.
        qs = KnowledgeArticle.objects.filter(project__in=accessible_projects(member)).filter(~Q(status='Draft') | Q(author=member)).select_related('author__user', 'project')
        if self.action != 'list':
            return qs
        status = self.request.query_params.get('status')
        if status:
            if status not in ['Draft', 'Published', 'Archived']:
                raise serializers.ValidationError('Choose a valid article status.')
            qs = qs.filter(status=status)
        else:
            qs = qs.exclude(status='Archived')
        project = self.request.query_params.get('project')
        if project:
            try:
                project = int(project)
            except ValueError:
                raise serializers.ValidationError('Invalid project ID.')
            get_object_or_404(accessible_projects(member), pk=project)
            qs = qs.filter(project_id=project)
        search = self.request.query_params.get('search', '').strip()
        if len(search) > 100:
            raise serializers.ValidationError('Search uses at most 100 characters.')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(summary__icontains=search) | Q(content__icontains=search))
        tag = self.request.query_params.get('tag', '').strip().lower()
        if tag:
            if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,29}', tag):
                raise serializers.ValidationError('Invalid tag.')
            qs = qs.filter(tags__contains=[tag])
        return qs

    def authorize_editor(self, member, item):
        if item.author_id != member.pk and not is_reviewer(member, item.project):
            raise PermissionDenied('Only the author or an assigned project reviewer can curate this article.')

    def record(self, item, action):
        ArticleRevision.objects.create(article=item, editor=self.request.user, version=item.version, snapshot=article_snapshot(item))
        AuditEvent.objects.create(project=item.project, actor=self.request.user, action=action, text=f'Updated knowledge article: {item.title}' if item.status != 'Draft' else 'Updated a private knowledge draft', after={'article_id': item.pk, 'version': item.version, 'status': item.status})

    @transaction.atomic
    def perform_create(self, serializer):
        member = lock_project(current_membership(self.request), serializer.validated_data['project'])
        validate_participant(member, serializer.validated_data['project'])
        if 'version' in serializer.validated_data:
            raise serializers.ValidationError('Version is generated by the server.')
        if serializer.validated_data.get('status') == 'Archived':
            raise serializers.ValidationError('Create a draft or published article before archiving it.')
        item = serializer.save(author=member)
        self.record(item, 'knowledge.created')

    @transaction.atomic
    def partial_update(self, request, pk=None):
        original = self.get_object()
        member = lock_project(current_membership(request), original.project)
        item = get_object_or_404(self.get_queryset().select_for_update(of=('self',)), pk=pk)
        self.authorize_editor(member, item)
        if not expected_version(request.data, item.version):
            return Response({'detail': 'Article changed. Refresh before saving.'}, status=409)
        serializer = self.get_serializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(version=item.version + 1)
        self.record(item, 'knowledge.updated')
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        item = self.get_object()
        member = current_membership(request)
        qs = item.revisions.select_related('editor')
        if item.author_id != member.pk:
            qs = qs.filter(snapshot__status='Published')
        page = self.paginate_queryset(qs)
        return self.get_paginated_response(RevisionSerializer(page, many=True).data)
