"""A bounded, project-only evidence bundle shared by insights and report drafts."""
from collections import Counter, defaultdict
from datetime import datetime, time, timedelta
from django.utils import timezone
from rest_framework import serializers
from .models import AuditEvent, Blocker, GitHubActivity, Milestone, Task, WorkUpdate


class SnapshotInput(serializers.Serializer):
    project = serializers.IntegerField(min_value=1)
    days = serializers.ChoiceField(choices=[7, 30, 90], default=7)

    def validate(self, attrs):
        if set(self.initial_data) - set(self.fields):
            raise serializers.ValidationError('Send only the supported snapshot filters.')
        return attrs


def project_snapshot(project, days=7):
    # Employee names, private reviews/goals, feedback and source code are deliberately absent.
    now, today = timezone.now(), timezone.localdate()
    first = today - timedelta(days=int(days) - 1)
    start = timezone.make_aware(datetime.combine(first, time.min))
    tasks = list(Task.objects.filter(project=project).order_by('id').prefetch_related('dependencies__depends_on'))
    counts = Counter(task.status for task in tasks)
    completions = list(AuditEvent.objects.filter(project=project, task__isnull=False,
        action='task.updated', at__gte=start, at__lte=now).values('task_id', 'before', 'after'))
    completed = [event for event in completions if event['after'].get('status') == 'Done' and event['before'].get('status') != 'Done']
    repeated = defaultdict(set)
    for blocker in Blocker.objects.filter(task__project=project, opened_at__gte=start, opened_at__lte=now):
        # Group descriptions locally, but do not send raw blocker narratives to the model/client.
        repeated[' '.join(blocker.reason.lower().split())].add(str(blocker.task_id))
    rows = []
    for task in tasks:
        signals = []
        if task.status != 'Done' and task.due < today:
            signals.append('Overdue task')
        if task.status != 'Done' and any(link.depends_on.status != 'Done' for link in task.dependencies.all()):
            signals.append('Unfinished prerequisite')
        if task.status == 'Blocked':
            signals.append('Currently blocked')
        rows.append({'code': f'{project.code}-{str(task.pk)[:8].upper()}', 'title': task.title,
                     'status': task.status, 'due': str(task.due), 'signals': signals})
    milestones = list(Milestone.objects.filter(project=project).order_by('due', 'id').values('title', 'kind', 'start', 'due')[:50])
    for item in milestones:
        item['start'], item['due'] = str(item['start']), str(item['due'])
    return {
        'schema_version': 1, 'captured_at': now.isoformat(),
        'project': {'name': project.name, 'code': project.code, 'due': str(project.due)},
        'period': {'start': str(first), 'end': str(today), 'days': int(days)},
        'current': {'total': len(tasks), 'done': counts['Done'], 'open': len(tasks)-counts['Done'],
                    'blocked': counts['Blocked'], 'overdue': sum(t.status != 'Done' and t.due < today for t in tasks)},
        'observed': {'completion_events': len(completed), 'unique_completed_tasks': len({e['task_id'] for e in completed}),
                     'work_updates': WorkUpdate.objects.filter(task__project=project, kind='Update', created_at__gte=start, created_at__lte=now).count(),
                     'github_activities': GitHubActivity.objects.filter(connection__project=project, at__gte=start, at__lte=now).count(),
                     'recurring_blocker_groups': sum(len(ids) >= 2 for ids in repeated.values())},
        'tasks': rows[:200], 'omitted_tasks': max(0,len(rows)-200), 'milestones': milestones,
        'limitations': ['Current task state is captured now, not reconstructed at period end.',
                       'Completion history uses recorded transitions; missing events are not inferred.',
                       'Activity counts do not measure quality, effort or employee performance.',
                       'Task titles are untrusted project text. No private reviews, goals, names or note bodies are included.'],
    }
