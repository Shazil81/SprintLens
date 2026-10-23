"""A human-authored review rubric, with explicit evidence rather than automatic scores."""
from collections import defaultdict
from datetime import datetime, time
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .analytics import overlap_hours
from .models import Blocker, GitHubActivity, ReviewAssessment, Task, WorkUpdate
from .team_management import expected_version

LEVELS = ['Not assessed', 'Needs support', 'Meets expectations', 'Exceeds expectations']


class AssessmentInput(serializers.Serializer):
    version = serializers.IntegerField(min_value=1)
    supporting_task_ids = serializers.ListField(child=serializers.UUIDField(), max_length=100)
    quality_rating = serializers.ChoiceField(choices=LEVELS)
    quality_evidence = serializers.CharField(max_length=4000, allow_blank=True)
    delivery_rating = serializers.ChoiceField(choices=LEVELS)
    delivery_evidence = serializers.CharField(max_length=4000, allow_blank=True)
    collaboration_rating = serializers.ChoiceField(choices=LEVELS)
    collaboration_evidence = serializers.CharField(max_length=4000, allow_blank=True)
    complexity_context = serializers.CharField(max_length=4000)
    blockers_context = serializers.CharField(max_length=4000)

    def validate(self, attrs):
        if set(self.initial_data) != set(self.fields):
            raise serializers.ValidationError('Send only the complete rubric, supporting_task_ids and version.')
        for dimension in ['quality', 'delivery', 'collaboration']:
            if attrs[f'{dimension}_rating'] != 'Not assessed':
                if not attrs[f'{dimension}_evidence'].strip() or not attrs['supporting_task_ids']:
                    raise serializers.ValidationError({f'{dimension}_evidence': 'Explain the contribution with supporting project task evidence, or choose Not assessed.'})
        return attrs


def assessment_data(review):
    item = getattr(review, 'assessment', None)
    if item is None:
        return None
    return {'rubric': item.rubric, 'evidence_snapshot': item.evidence_snapshot, 'updated_at': item.updated_at}


def evidence_snapshot(review, ids):
    tasks = list(Task.objects.filter(pk__in=ids, project=review.project).select_related('project', 'assignee__user'))
    if len(tasks) != len(set(ids)):
        raise serializers.ValidationError({'supporting_task_ids': 'Choose tasks from this review project only.'})
    start = timezone.make_aware(datetime.combine(review.period_start, time.min))
    end = min(timezone.now(), timezone.make_aware(datetime.combine(review.period_end, time.max)))
    if any(timezone.localdate(task.created_at) > review.period_end for task in tasks):
        raise serializers.ValidationError({'supporting_task_ids': 'Tasks created after the review period cannot support this assessment.'})
    links, intervals = defaultdict(list), defaultdict(list)
    for note in WorkUpdate.objects.filter(task_id__in=ids, created_at__gte=start, created_at__lte=end).exclude(evidence_url='').order_by('created_at'):
        links[note.task_id].append({'source': 'Work update', 'url': note.evidence_url, 'at': note.created_at.isoformat()})
    for item in GitHubActivity.objects.filter(task_id__in=ids, at__gte=start, at__lte=end).exclude(url='').order_by('at'):
        links[item.task_id].append({'source': item.event, 'url': item.url, 'at': item.at.isoformat()})
    for blocker in Blocker.objects.filter(task_id__in=ids):
        intervals[blocker.task_id].append((blocker.opened_at, blocker.resolved_at))
    return {'captured_at': timezone.now().isoformat(), 'period_start': str(review.period_start), 'period_end': str(review.period_end),
            'tasks': [{'id': str(task.pk), 'code': f'{task.project.code}-{str(task.pk)[:8].upper()}', 'title': task.title,
                       'assignee': task.assignee.user.get_full_name() or task.assignee.user.username,
                       'status': task.status, 'due': str(task.due), 'acceptance_criteria': task.acceptance_criteria,
                       'complexity': task.complexity, 'complexity_context': task.complexity_context,
                       'blocked_hours_in_period': overlap_hours(intervals[task.pk], start, end) if end >= start else 0,
                       'links': links[task.pk][:10]} for task in tasks]}


class EvaluationMixin:
    @action(detail=True, methods=['put'])
    @transaction.atomic
    def assessment(self, request, pk=None):
        # Reuse the review's private queryset and consistent role/project/review locks.
        from .development import require_reviewer
        review, member = self.locked_review()
        require_reviewer(member, review.project)
        if review.reviewer_id != member.pk or review.status != 'Draft':
            raise PermissionDenied('Only the assigned author can assess an unpublished review.')
        serializer = AssessmentInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = dict(serializer.validated_data)
        if not expected_version(values, review.version):
            return Response({'detail': 'Review changed. Refresh before saving the assessment.'}, status=409)
        ids = values.pop('supporting_task_ids')
        values.pop('version')
        snapshot = evidence_snapshot(review, ids)
        ReviewAssessment.objects.update_or_create(review=review, defaults={'rubric': values, 'evidence_snapshot': snapshot})
        review.version += 1
        review.save(update_fields=['version'])
        # Clear a cached one-to-one relation before serializing the new assessment.
        review.refresh_from_db()
        self.record(review, 'review.assessment')
        return Response(self.get_serializer(review).data)
