"""Nested task discussion and blocker endpoints, isolated from task CRUD views."""
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from .access import current_membership, require_manager
from .models import AuditEvent, Blocker, Membership, Organization, Project, ProjectMembership, Task, WorkUpdate
from .serializers import WorkUpdateSerializer, BlockerSerializer, ResolutionSerializer


class TaskActivityMixin:
    def require_task_contributor(self, member, task):
        if member.role == Membership.Role.DEVELOPER and task.assignee_id != member.pk:
            raise PermissionDenied('You can contribute only to tasks assigned to you.')

    def activity_page(self, queryset, serializer_class):
        page = self.paginate_queryset(queryset)
        serializer = serializer_class(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def updates(self, request, pk=None):
        task = self.get_object()
        if request.method == 'GET':
            return self.activity_page(task.work_updates.select_related('author'), WorkUpdateSerializer)
        member = current_membership(request)
        serializer = WorkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind = serializer.validated_data.get('kind', WorkUpdate.Kind.UPDATE)
        # Author comes from the session; notes and their audit event commit together.
        with transaction.atomic():
            # Serialize feedback with project roster and reviewer assignment changes.
            Organization.objects.select_for_update().get(pk=member.organization_id)
            Project.objects.select_for_update().get(pk=task.project_id)
            member = current_membership(request)
            task = get_object_or_404(self.get_queryset().select_for_update(of=('self',)), pk=pk)
            if kind == WorkUpdate.Kind.FEEDBACK:
                require_manager(member)
                if not ProjectMembership.objects.filter(project=task.project, membership=member, is_reviewer=True).exists():
                    raise PermissionDenied('Only an assigned project reviewer can submit feedback.')
            elif task.assignee_id != member.pk:
                raise PermissionDenied('Only the assignee can submit a work update.')
            item = serializer.save(task=task, author=request.user)
            AuditEvent.objects.create(project=task.project, task=task, actor=request.user,
                                      action='task.feedback' if kind == 'Feedback' else 'task.work_update',
                                      text=f'Added {kind.lower()} to {task.title}',
                                      after={'update_id': item.pk, 'kind': kind})
        return Response(WorkUpdateSerializer(item).data, status=201)

    @action(detail=True, methods=['get', 'post'])
    def blockers(self, request, pk=None):
        task = self.get_object()
        if request.method == 'GET':
            return self.activity_page(task.blockers.select_related('owner__user', 'reporter', 'resolved_by'), BlockerSerializer)
        member = current_membership(request)
        self.require_task_contributor(member, task)
        serializer = BlockerSerializer(data=request.data, context={'task': task, 'member': member})
        serializer.is_valid(raise_exception=True)
        # Lock the task so blocker creation cannot race completion or another blocker mutation.
        with transaction.atomic():
            task = get_object_or_404(self.get_queryset().select_for_update(of=('self',)), pk=pk)
            self.require_task_contributor(member, task)
            if task.status == Task.Status.DONE:
                raise serializers.ValidationError({'task': 'Reopen completed work before reporting a blocker.'})
            item = serializer.save(task=task, reporter=request.user)
            before_status = task.status
            task.status = Task.Status.BLOCKED
            task.version += 1
            task.save(update_fields=['status', 'version', 'updated_at'])
            AuditEvent.objects.create(project=task.project, task=task, actor=request.user, action='blocker.reported',
                                      text=f'Reported a blocker on {task.title}',
                                      before={'status': before_status},
                                      after={'blocker_id': item.pk, 'status': task.status, 'owner_id': item.owner_id, 'reason': item.reason})
        return Response(BlockerSerializer(item).data, status=201)

    @action(detail=True, methods=['post'], url_path=r'blockers/(?P<blocker_id>[^/.]+)/resolve')
    def resolve_blocker(self, request, pk=None, blocker_id=None):
        member = current_membership(request)
        serializer = ResolutionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Always acquire task before blocker locks, giving all writers a consistent lock order.
        with transaction.atomic():
            task = get_object_or_404(self.get_queryset().select_for_update(of=('self',)), pk=pk)
            item = get_object_or_404(Blocker.objects.select_for_update(), task=task, pk=blocker_id)
            if member.role == Membership.Role.DEVELOPER and member.pk not in [item.owner_id, task.assignee_id] and request.user.pk != item.reporter_id:
                raise PermissionDenied('Only the assignee, blocker owner, reporter, or manager can resolve this blocker.')
            if item.resolved_at:
                return Response({'detail': 'This blocker is already resolved.'}, status=409)
            item.resolution = serializer.validated_data['resolution']
            item.resolved_at = timezone.now()
            item.resolved_by = request.user
            item.save(update_fields=['resolution', 'resolved_at', 'resolved_by'])
            before_status = task.status
            if task.status == Task.Status.BLOCKED and not task.blockers.filter(resolved_at__isnull=True).exists() and not task.dependencies.exclude(depends_on__status='Done').exists():
                task.status = Task.Status.IN_PROGRESS
            task.version += 1
            task.save(update_fields=['status', 'version', 'updated_at'])
            AuditEvent.objects.create(project=task.project, task=task, actor=request.user, action='blocker.resolved',
                                      text=f'Resolved a blocker on {task.title}',
                                      before={'status': before_status, 'blocker_id': item.pk},
                                      after={'status': task.status, 'resolution': item.resolution})
        return Response(BlockerSerializer(item).data)
