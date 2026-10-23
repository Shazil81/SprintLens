from django.db import transaction
from django.db.models import Count, Q
from rest_framework.generics import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .access import accessible_projects, current_membership, require_manager
from .auth import identity
from .models import AuditEvent, Membership, Organization, Project, ProjectMembership, Task
from .serializers import AuditSerializer, MemberSerializer, ProjectSerializer, TaskSerializer
from .task_activity import TaskActivityMixin
from .planning import TaskPlanningMixin
from .team_management import ProjectManagementViewSet as ProjectViewSet, TeamManagementViewSet as MemberViewSet


def task_snapshot(task):
    return {key: str(getattr(task, key)) for key in ['title', 'project_id', 'assignee_id', 'status', 'priority', 'complexity', 'complexity_context', 'due', 'acceptance_criteria', 'version']}


class TaskViewSet(TaskPlanningMixin, TaskActivityMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        member = current_membership(self.request)
        qs = Task.objects.filter(project__in=accessible_projects(member)).select_related('project', 'assignee__user')
        # Developers can see project tasks but can only mutate their own assignments.
        return qs

    def get_serializer_context(self):
        return {**super().get_serializer_context(), 'member': current_membership(self.request)}

    @transaction.atomic
    def perform_create(self, serializer):
        member = current_membership(self.request)
        require_manager(member)
        Organization.objects.select_for_update().get(pk=member.organization_id)
        member = current_membership(self.request)
        require_manager(member)
        # Share the project lock with roster edits and recheck the assignment before saving.
        project = Project.objects.select_for_update().get(pk=serializer.validated_data['project'].pk)
        if not accessible_projects(member).filter(pk=project.pk).exists():
            raise PermissionDenied('Your project access has changed. Refresh before creating work.')
        if not ProjectMembership.objects.filter(project=project, membership=serializer.validated_data['assignee']).exists():
            raise serializers.ValidationError({'assignee': 'Assignee is no longer a member of this project.'})
        task = serializer.save()
        AuditEvent.objects.create(project=task.project, actor=self.request.user, task=task, action='task.created',
                                  text=f'Created {task.title}', after=task_snapshot(task))

    @transaction.atomic
    def partial_update(self, request, pk=None):
        member = current_membership(request)
        # Compare-and-swap below prevents stale updates even on the local SQLite fallback.
        original = self.get_object()
        Organization.objects.select_for_update().get(pk=member.organization_id)
        member = current_membership(request)
        Project.objects.select_for_update().get(pk=original.project_id)
        task = get_object_or_404(self.get_queryset().select_for_update(of=('self',)), pk=pk)
        if member.role == Membership.Role.DEVELOPER:
            if task.assignee_id != member.id:
                raise PermissionDenied('You can update only tasks assigned to you.')
            if set(request.data) - {'status', 'version'}:
                raise PermissionDenied('Developers may change only task status.')
        expected_version = request.data.get('version')
        if isinstance(expected_version, bool) or not isinstance(expected_version, int):
            raise serializers.ValidationError({'version': 'Send the current integer task version.'})
        if expected_version != task.version:
            return Response({'detail': 'This task changed. Refresh before saving.'}, status=409)
        serializer = self.get_serializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data.get('status', task.status)
        if new_status != task.status:
            if new_status in ['In progress', 'In review', 'Done'] and task.dependencies.exclude(depends_on__status='Done').exists():
                raise serializers.ValidationError({'status': 'Complete prerequisite tasks before starting this work.'})
            if task.status == 'Done' and task.dependents.filter(task__status='Done').exists():
                raise serializers.ValidationError({'status': 'Reopen completed dependent tasks before reopening this prerequisite.'})
            if new_status != Task.Status.BLOCKED and task.blockers.filter(resolved_at__isnull=True).exists():
                raise serializers.ValidationError({'status': 'Resolve all open blockers before moving this task forward.'})
            transitions = {
                'To do': ['In progress', 'Blocked'],
                'In progress': ['To do', 'In review', 'Blocked'],
                'In review': ['In progress', 'Done', 'Blocked'],
                'Blocked': ['To do', 'In progress'],
                'Done': ['In progress'],
            }
            if new_status not in transitions[task.status]:
                raise serializers.ValidationError({'status': f'Cannot move directly from {task.status} to {new_status}.'})
            if member.role == Membership.Role.DEVELOPER and (new_status == 'Done' or task.status == 'Done'):
                raise PermissionDenied('A manager must accept or reopen completed work.')
            criteria = serializer.validated_data.get('acceptance_criteria', task.acceptance_criteria)
            if new_status == 'Done' and not criteria.strip():
                raise serializers.ValidationError({'acceptance_criteria': 'Add acceptance criteria before completing the task.'})
        before = task_snapshot(task)
        updates = dict(serializer.validated_data)
        updates.pop('version', None)
        if not any(getattr(task, key) != value for key, value in updates.items()):
            return Response(self.get_serializer(task).data)
        changed = Task.objects.filter(pk=task.pk, version=expected_version).update(**updates, version=expected_version + 1, updated_at=timezone.now())
        if not changed:
            return Response({'detail': 'This task changed. Refresh before saving.'}, status=409)
        task.refresh_from_db()
        summary = f'Moved {task.title} from {before["status"]} to {task.status}' if before['status'] != task.status else f'Updated {task.title}'
        AuditEvent.objects.create(project=task.project, actor=request.user, task=task, action='task.updated', text=summary, before=before, after=task_snapshot(task))
        return Response(self.get_serializer(task).data)


class AuditViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = AuditSerializer

    def get_queryset(self):
        member = current_membership(self.request)
        visible = Q(project__in=accessible_projects(member))
        if member.role == Membership.Role.ADMIN:
            visible |= Q(organization=member.organization, project__isnull=True)
        return AuditEvent.objects.filter(visible).select_related('actor')


@api_view(['GET'])
def me(request):
    return Response(identity(request.user))


@api_view(['GET'])
def dashboard(request):
    member = current_membership(request)
    projects = accessible_projects(member)
    tasks = Task.objects.filter(project__in=projects)
    if member.role == Membership.Role.DEVELOPER:
        tasks = tasks.filter(assignee=member)
    return Response({'active_projects': projects.count(), 'tasks': tasks.count(), 'by_status': dict(tasks.values_list('status').annotate(total=Count('id')))})
