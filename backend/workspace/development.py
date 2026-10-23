"""Private two-way reviews and developer growth records."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from .access import accessible_projects, current_membership
from .models import AuditEvent, GoalEntry, GrowthGoal, Membership, Organization, PerformanceReview, Project, ProjectMembership, ReviewResponse
from .serializers import StrictSerializer
from .team_management import expected_version
from .evaluation import EvaluationMixin, assessment_data


def is_reviewer(member, project):
    return member.role in ['Admin', 'Manager'] and ProjectMembership.objects.filter(project=project, membership=member, is_reviewer=True).exists()


def require_reviewer(member, project):
    if not is_reviewer(member, project):
        raise PermissionDenied('Only assigned project reviewers can perform this action.')


def lock_project(member, project):
    # Role and roster changes share this ordering with review publication.
    Organization.objects.select_for_update().get(pk=member.organization_id)
    Project.objects.select_for_update().get(pk=project.pk)
    member = Membership.objects.get(pk=member.pk)
    if not accessible_projects(member).filter(pk=project.pk).exists():
        raise PermissionDenied('Your project access has changed. Refresh the workspace.')
    return member


def validate_participant(member, project):
    if not member.user.is_active or not ProjectMembership.objects.filter(project=project, membership=member).exists():
        raise serializers.ValidationError('Choose an active member of this project.')


class ReviewResponseSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = ReviewResponse
        fields = ['id', 'body', 'author_name', 'created_at']


class ReviewSerializer(StrictSerializer):
    assessment = serializers.SerializerMethodField()

    def get_assessment(self, obj):
        return assessment_data(obj)

    subject_name = serializers.CharField(source='subject.user.get_full_name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.user.get_full_name', read_only=True)
    responses = ReviewResponseSerializer(many=True, read_only=True)
    strengths = serializers.CharField(max_length=4000)
    improvements = serializers.CharField(max_length=4000)
    collaboration = serializers.CharField(max_length=4000)
    delivery_context = serializers.CharField(max_length=4000)

    def validate(self, attrs):
        if self.instance and set(attrs) - {'cycle', 'period_start', 'period_end', 'strengths', 'improvements', 'collaboration', 'delivery_context', 'version'}:
            raise serializers.ValidationError('The project, subject and reviewer cannot change.')
        project = attrs.get('project', self.instance.project if self.instance else None)
        member = current_membership(self.context['request'])
        if not project or not accessible_projects(member).filter(pk=project.pk).exists():
            raise serializers.ValidationError('Choose an accessible project.')
        subject = attrs.get('subject', self.instance.subject if self.instance else None)
        if not subject:
            raise serializers.ValidationError('Choose a review subject.')
        validate_participant(subject, project)
        if subject.pk == member.pk:
            raise serializers.ValidationError('Self-reviews are not supported; use a developer response instead.')
        start = attrs.get('period_start', self.instance.period_start if self.instance else None)
        end = attrs.get('period_end', self.instance.period_end if self.instance else None)
        if start and end and end < start:
            raise serializers.ValidationError('The review period end must follow its start.')
        return attrs

    class Meta:
        model = PerformanceReview
        fields = ['id', 'project', 'subject', 'subject_name', 'reviewer', 'reviewer_name', 'cycle', 'period_start', 'period_end', 'strengths', 'improvements', 'collaboration', 'delivery_context', 'status', 'version', 'published_at', 'responses', 'assessment']
        read_only_fields = ['id', 'reviewer', 'status', 'published_at']


class ReviewViewSet(EvaluationMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        member = current_membership(self.request)
        return PerformanceReview.objects.filter(project__in=accessible_projects(member)).filter(Q(reviewer=member) | (Q(subject=member) & ~Q(status='Draft'))).select_related('subject__user', 'reviewer__user', 'assessment').prefetch_related('responses__author')

    @transaction.atomic
    def perform_create(self, serializer):
        member = lock_project(current_membership(self.request), serializer.validated_data['project'])
        require_reviewer(member, serializer.validated_data['project'])
        validate_participant(serializer.validated_data['subject'], serializer.validated_data['project'])
        if 'version' in serializer.validated_data:
            raise serializers.ValidationError('Version is generated by the server.')
        item = serializer.save(reviewer=member)
        self.record(item, 'review.created')

    def record(self, item, action):
        # Audit records reference IDs and state, never private review text.
        AuditEvent.objects.create(project=item.project, actor=self.request.user, action=action, text='Updated a performance review', after={'review_id': item.pk, 'status': item.status, 'version': item.version})

    def locked_review(self):
        original = self.get_object()
        member = lock_project(current_membership(self.request), original.project)
        return get_object_or_404(self.get_queryset().select_for_update(of=('self',)), pk=original.pk), member

    @transaction.atomic
    def partial_update(self, request, pk=None):
        item, member = self.locked_review()
        require_reviewer(member, item.project)
        if item.reviewer_id != member.pk or item.status != 'Draft':
            raise PermissionDenied('Only the author can edit an unpublished draft.')
        if not expected_version(request.data, item.version):
            return Response({'detail': 'Review changed. Refresh before saving.'}, status=409)
        serializer = self.get_serializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(version=item.version + 1)
        self.record(item, 'review.updated')
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def publish(self, request, pk=None):
        item, member = self.locked_review()
        require_reviewer(member, item.project)
        if item.reviewer_id != member.pk or item.status != 'Draft':
            raise PermissionDenied('Only the author can publish an unpublished draft.')
        if set(request.data) != {'version'}:
            raise serializers.ValidationError('Send only version.')
        if not expected_version(request.data, item.version):
            return Response({'detail': 'Review changed. Refresh before publishing.'}, status=409)
        assessment = assessment_data(item)
        if assessment and (assessment['evidence_snapshot']['period_start'] != str(item.period_start) or assessment['evidence_snapshot']['period_end'] != str(item.period_end)):
            raise serializers.ValidationError('The review period changed. Refresh the assessment snapshot before publishing.')
        item.status, item.published_at = 'Published', timezone.now()
        item.version += 1
        item.save(update_fields=['status', 'published_at', 'version'])
        self.record(item, 'review.published')
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def respond(self, request, pk=None):
        item, member = self.locked_review()
        if item.subject_id != member.pk or item.status == 'Draft':
            raise PermissionDenied('Only the review subject can respond to a published review.')
        serializer = BodyInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        ReviewResponse.objects.create(review=item, author=request.user, **serializer.validated_data)
        item.status = 'Responded'
        item.version += 1
        item.save(update_fields=['status', 'version'])
        self.record(item, 'review.responded')
        return Response(self.get_serializer(item).data, status=201)


class BodyInput(serializers.Serializer):
    body = serializers.CharField(max_length=4000)

    def validate(self, attrs):
        if set(self.initial_data) != {'body'}:
            raise serializers.ValidationError('Send only body.')
        return attrs


class GoalEntrySerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = GoalEntry
        fields = ['id', 'author_name', 'kind', 'body', 'created_at']


class GoalSerializer(StrictSerializer):
    owner_name = serializers.CharField(source='owner.user.get_full_name', read_only=True)
    entries = GoalEntrySerializer(many=True, read_only=True)

    def validate(self, attrs):
        if self.instance and set(attrs) - {'title', 'skill', 'target_date', 'status', 'version'}:
            raise serializers.ValidationError('The project and owner cannot change.')
        project = attrs.get('project', self.instance.project if self.instance else None)
        if not project or not accessible_projects(current_membership(self.context['request'])).filter(pk=project.pk).exists():
            raise serializers.ValidationError('Choose an accessible project.')
        owner = attrs.get('owner', self.instance.owner if self.instance else None)
        if not owner:
            raise serializers.ValidationError('Choose a goal owner.')
        validate_participant(owner, project)
        return attrs

    class Meta:
        model = GrowthGoal
        fields = ['id', 'project', 'owner', 'owner_name', 'title', 'skill', 'target_date', 'status', 'version', 'entries']
        read_only_fields = ['id']


class GoalViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = GoalSerializer

    def get_queryset(self):
        member = current_membership(self.request)
        review_projects = ProjectMembership.objects.filter(membership=member, is_reviewer=True).values_list('project_id', flat=True) if member.role in ['Admin', 'Manager'] else []
        return GrowthGoal.objects.filter(project__in=accessible_projects(member)).filter(Q(owner=member) | Q(project_id__in=review_projects)).select_related('owner__user').prefetch_related('entries__author')

    def authorize(self, member, goal):
        if goal.owner_id != member.pk:
            require_reviewer(member, goal.project)

    @transaction.atomic
    def perform_create(self, serializer):
        member = lock_project(current_membership(self.request), serializer.validated_data['project'])
        owner = serializer.validated_data['owner']
        validate_participant(owner, serializer.validated_data['project'])
        if owner.pk != member.pk:
            require_reviewer(member, serializer.validated_data['project'])
        if 'version' in serializer.validated_data:
            raise serializers.ValidationError('Version is generated by the server.')
        item = serializer.save()
        self.record(item, 'goal.created')

    def record(self, item, action):
        AuditEvent.objects.create(project=item.project, actor=self.request.user, action=action, text='Updated a developer growth goal', after={'goal_id': item.pk, 'status': item.status, 'version': item.version})

    @transaction.atomic
    def partial_update(self, request, pk=None):
        original = self.get_object()
        member = lock_project(current_membership(request), original.project)
        item = get_object_or_404(self.get_queryset().select_for_update(of=('self',)), pk=pk)
        self.authorize(member, item)
        if not expected_version(request.data, item.version):
            return Response({'detail': 'Goal changed. Refresh before saving.'}, status=409)
        serializer = self.get_serializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item = serializer.save(version=item.version + 1)
        self.record(item, 'goal.updated')
        return Response(self.get_serializer(item).data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def entries(self, request, pk=None):
        original = self.get_object()
        member = lock_project(current_membership(request), original.project)
        item = get_object_or_404(self.get_queryset().select_for_update(of=('self',)), pk=pk)
        serializer = BodyInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.authorize(member, item)
        entry = GoalEntry.objects.create(goal=item, author=request.user, kind='Progress' if item.owner_id == member.pk else 'Feedback', **serializer.validated_data)
        self.record(item, 'goal.entry')
        return Response(GoalEntrySerializer(entry).data, status=201)
