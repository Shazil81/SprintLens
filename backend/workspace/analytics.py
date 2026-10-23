"""Explainable project analytics; delivery signals are never employee scores."""
from collections import Counter, defaultdict
from datetime import datetime, time, timedelta
from statistics import median
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import api_view
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from .access import accessible_projects, current_membership
from .models import AuditEvent, Blocker, GitHubActivity, Milestone, Task, WorkUpdate


class AnalyticsFilter(serializers.Serializer):
    project = serializers.IntegerField(min_value=1, required=False)
    days = serializers.ChoiceField(choices=[7, 30, 90], default=30)


def overlap_hours(intervals, start, end):
    """Union overlapping blocker intervals so parallel blockers do not double-count time."""
    intervals = sorted((max(a, start), min(b or end, end)) for a, b in intervals if a < end and (b is None or b > start))
    total = 0
    left = right = None
    for a, b in intervals:
        if left is None:
            left, right = a, b
        elif a <= right:
            right = max(right, b)
        else:
            total += (right - left).total_seconds()
            left, right = a, b
    if left is not None:
        total += (right - left).total_seconds()
    return round(total / 3600, 2)


@api_view(['GET'])
def analytics(request):
    member = current_membership(request)
    filters = AnalyticsFilter(data=request.query_params)
    filters.is_valid(raise_exception=True)
    projects = accessible_projects(member)
    if filters.validated_data.get('project'):
        selected = get_object_or_404(projects, pk=filters.validated_data['project'])
        projects = projects.filter(pk=selected.pk)
    projects = list(projects)
    tasks = list(Task.objects.filter(project__in=projects).select_related('project', 'assignee__user').prefetch_related('dependencies__depends_on', 'blockers', 'work_updates'))
    now, today = timezone.now(), timezone.localdate()
    days = int(filters.validated_data['days'])
    first_day = today - timedelta(days=days - 1)
    start = timezone.make_aware(datetime.combine(first_day, time.min))
    task_ids = [task.pk for task in tasks]
    events = list(AuditEvent.objects.filter(task_id__in=task_ids, action__in=['task.updated', 'blocker.reported', 'blocker.resolved'], at__lte=now).order_by('at'))
    date_moves, blocked_entries = Counter(), Counter()
    starts, completions = {}, []
    trend = {str(first_day + timedelta(days=i)): 0 for i in range(days)}
    for event in events:
        before, after = event.before, event.after
        if after.get('status') == 'In progress' and before.get('status') != 'In progress':
            starts.setdefault(event.task_id, event.at)
        if start <= event.at <= now:
            if after.get('status') == 'Done' and before.get('status') != 'Done':
                trend[str(timezone.localdate(event.at))] += 1
                completions.append((event.task_id, event.at))
            if after.get('status') == 'Blocked' and before.get('status') != 'Blocked':
                blocked_entries[event.task_id] += 1
            old_due, new_due = before.get('due'), after.get('due')
            if isinstance(old_due, str) and isinstance(new_due, str) and new_due > old_due:
                date_moves[event.task_id] += 1
    durations = [(at - starts[task_id]).total_seconds() / 3600 for task_id, at in completions if task_id in starts and starts[task_id] <= at]
    risk_rows, project_rows = [], []
    workload = {}
    all_blockers = defaultdict(list)
    repeated = defaultdict(set)
    repeat_text = {}
    for task in tasks:
        open_blockers = [item for item in task.blockers.all() if item.resolved_at is None]
        for item in task.blockers.all():
            all_blockers[task.pk].append((item.opened_at, item.resolved_at))
            if start <= item.opened_at <= now:
                key = (task.project_id, ' '.join(item.reason.lower().split()))
                repeated[key].add(task.pk)
                repeat_text[key] = ' '.join(item.reason.split())[:160]
        if member.role != 'Developer' or task.assignee_id == member.pk:
            person = workload.setdefault(task.assignee_id, {'member_id': task.assignee_id, 'name': task.assignee.user.get_full_name() or task.assignee.user.username, 'open': 0, 'overdue': 0, 'blocked': 0, 'complexity': Counter()})
            if task.status != 'Done':
                person['open'] += 1
                person['overdue'] += int(task.due < today)
                person['blocked'] += int(task.status == 'Blocked')
                person['complexity'][task.complexity] += 1
        if task.status == 'Done':
            continue
        signals, severity = [], 'Watch'
        if task.due < today:
            signals.append(f'Overdue since {task.due}.')
            severity = 'High'
        waiting = [link.depends_on for link in task.dependencies.all() if link.depends_on.status != 'Done']
        if waiting:
            signals.append(f'Waiting for {len(waiting)} unfinished prerequisite task(s).')
            if task.due <= today + timedelta(days=3):
                severity = 'High'
                signals.append('Deadline is within three days while prerequisites remain unfinished.')
        aged = [item for item in open_blockers if item.opened_at <= now - timedelta(hours=72)]
        if aged:
            signals.append(f'{len(aged)} blocker(s) have been open for at least 72 hours.')
        latest = max([task.updated_at] + [item.created_at for item in task.work_updates.all()])
        if task.status in ['In progress', 'In review', 'Blocked'] and latest <= now - timedelta(days=7):
            signals.append('No task change or work note in at least seven days.')
        if date_moves[task.pk] >= 2:
            signals.append(f'Deadline moved later {date_moves[task.pk]} times in this period.')
        if blocked_entries[task.pk] >= 2:
            signals.append(f'Entered Blocked status {blocked_entries[task.pk]} times in this period.')
        if signals:
            risk_rows.append({'task_id': str(task.pk), 'code': f'{task.project.code}-{str(task.pk)[:8].upper()}', 'title': task.title, 'project_id': task.project_id, 'project': task.project.name, 'assignee': task.assignee.user.get_full_name() or task.assignee.user.username, 'due': task.due, 'severity': severity, 'signals': signals})
    for project in projects:
        rows = [task for task in tasks if task.project_id == project.pk]
        related_risks = [risk for risk in risk_rows if risk['project_id'] == project.pk]
        past_deadline = project.due < today and any(t.status != 'Done' for t in rows)
        project_rows.append({'id': project.pk, 'name': project.name, 'due': project.due, 'total': len(rows), 'done': sum(t.status == 'Done' for t in rows), 'open': sum(t.status != 'Done' for t in rows), 'risk_count': len(related_risks), 'status': 'Needs attention' if past_deadline or any(r['severity'] == 'High' for r in related_risks) else 'Watch' if related_risks else 'No active signals', 'past_deadline': past_deadline})
    evidence_ids = set(WorkUpdate.objects.filter(task_id__in=task_ids, created_at__gte=start, created_at__lte=now).exclude(evidence_url='').values_list('task_id', flat=True))
    evidence_ids.update(GitHubActivity.objects.filter(task_id__in=task_ids, at__gte=start, at__lte=now).values_list('task_id', flat=True))
    milestones = []
    for item in Milestone.objects.filter(project__in=projects, due__lte=today + timedelta(days=7)).select_related('project'):
        linked = [task for task in tasks if task.milestone_id == item.pk]
        if linked and any(task.status != 'Done' for task in linked):
            milestones.append({'id': item.pk, 'title': item.title, 'project': item.project.name, 'due': item.due, 'open_tasks': sum(t.status != 'Done' for t in linked), 'overdue': item.due < today})
    risk_rows.sort(key=lambda r: (0 if r['severity'] == 'High' else 1, r['due'], r['code']))
    return Response({
        'period': {'start': first_day, 'end': today, 'days': days},
        'snapshot': {'projects': len(projects), 'tasks': len(tasks), 'open': sum(t.status != 'Done' for t in tasks), 'done': sum(t.status == 'Done' for t in tasks), 'overdue': sum(t.status != 'Done' and t.due < today for t in tasks), 'blocked': sum(t.status == 'Blocked' for t in tasks)},
        'delivery': {'completion_events': len(completions), 'unique_completed_tasks': len({task_id for task_id, _ in completions}), 'median_start_to_accept_hours': round(median(durations), 2) if durations else None, 'timed_events': len(durations), 'blocked_task_hours': round(sum(overlap_hours(intervals, start, now) for intervals in all_blockers.values()), 2), 'linked_evidence_tasks': len(evidence_ids)},
        'trend': [{'date': day, 'completions': value} for day, value in trend.items()],
        'projects': project_rows, 'workload': sorted(workload.values(), key=lambda row: row['name'].lower()),
        'risks': risk_rows[:50], 'risk_total': len(risk_rows), 'milestones': milestones[:50],
        'recurring_blockers': [{'project_id': key[0], 'description': repeat_text[key], 'task_count': len(ids)} for key, ids in repeated.items() if len(ids) >= 2][:20],
        'notes': ['Risk signals are rule-based prompts for investigation, not deadline predictions or employee ratings.', 'Current workload and risks are snapshots; the selected period applies to completion events, blocker time and repeat signals.', 'Completion events come from audit transitions, including re-completions. Missing history is not estimated.', 'Blocked hours merge overlapping blockers per task; they are project context, not hours attributed to a person.'],
    })
