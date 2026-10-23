"""Idempotent database-backed notifications; no email is sent by these jobs."""
from datetime import timedelta
from celery import shared_task
from django.db import transaction
from django.db import OperationalError, InterfaceError
from django.utils import timezone
from .models import Blocker, Membership, Notification, PerformanceReview, ProjectMembership, Task


def reviewer_ids(project):
    return set(ProjectMembership.objects.filter(project=project, is_reviewer=True, membership__role__in=['Admin', 'Manager'], membership__user__is_active=True).values_list('membership_id', flat=True))


def notify(recipient_id, project, kind, key, title, body):
    # Recheck active project access; reminders never bypass a removed membership.
    if not Membership.objects.filter(pk=recipient_id, user__is_active=True, organization_id=project.organization_id).exists():
        return 0
    member = Membership.objects.get(pk=recipient_id)
    if member.role != 'Admin' and not ProjectMembership.objects.filter(project=project, membership=member).exists():
        return 0
    _, created = Notification.objects.get_or_create(recipient_id=recipient_id, dedupe_key=key, defaults={'project': project, 'kind': kind, 'title': title[:200], 'body': body})
    return int(created)


@shared_task(autoretry_for=(OperationalError, InterfaceError), retry_backoff=True, max_retries=3)
def generate_reminders():
    today = timezone.localdate()
    count = 0
    for task in Task.objects.filter(due__lte=today + timedelta(days=2)).exclude(status='Done').select_related('project'):
        for recipient in reviewer_ids(task.project) | {task.assignee_id}:
            count += notify(recipient, task.project, 'deadline', f'deadline:{task.pk}:{today}', f'Deadline: {task.title}', f'{task.project.name} · Due {task.due} · {task.status}')
    for blocker in Blocker.objects.filter(resolved_at__isnull=True, opened_at__lte=timezone.now() - timedelta(days=1)).select_related('task__project'):
        for recipient in reviewer_ids(blocker.task.project) | {blocker.owner_id, blocker.task.assignee_id}:
            count += notify(recipient, blocker.task.project, 'blocker', f'blocker:{blocker.pk}:{today}', f'Blocker needs attention: {blocker.task.title}', 'This blocker has remained open for at least one day. Open the task to review its owner and resolution.')
    for review in PerformanceReview.objects.filter(status='Published').select_related('project'):
        count += notify(review.subject_id, review.project, 'review', f'review:{review.pk}', 'A performance review is ready', 'Open Reviews to read your published feedback and share your perspective.')
    return count


@shared_task(autoretry_for=(OperationalError, InterfaceError), retry_backoff=True, max_retries=3)
def generate_digests():
    today = timezone.localdate()
    count = 0
    # Runs hourly for catch-up after downtime, but creates at most one digest per day/project/person.
    for link in ProjectMembership.objects.filter(is_reviewer=True, membership__role__in=['Admin', 'Manager'], membership__user__is_active=True).select_related('project'):
        tasks = Task.objects.filter(project=link.project)
        count += notify(link.membership_id, link.project, 'digest', f'digest:{link.project_id}:{today}', f'Daily progress: {link.project.name}', f'{tasks.filter(status="Done").count()} completed · {tasks.filter(status="Blocked").count()} blocked · {tasks.exclude(status="Done").filter(due__lt=today).count()} overdue. Open the workspace for details.')
    return count
