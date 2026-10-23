from rest_framework import serializers
from .models import AuditEvent, Membership, Project, ProjectMembership, Task, WorkUpdate, Blocker


class StrictSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        unknown = set(data) - {name for name, field in self.fields.items() if not field.read_only}
        if unknown:
            raise serializers.ValidationError({key: 'This field cannot be written.' for key in unknown})
        return super().to_internal_value(data)


class MemberSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(read_only=True)

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    class Meta:
        model = Membership
        fields = ['id', 'user_id', 'name', 'role']


class ProjectSerializer(StrictSerializer):
    member_ids = serializers.SerializerMethodField()
    reviewer_ids = serializers.SerializerMethodField()
    version = serializers.IntegerField(min_value=1, required=False)

    def validate_code(self, value):
        import re
        value = value.upper()
        if not re.fullmatch(r'[A-Z][A-Z0-9]{1,11}', value):
            raise serializers.ValidationError('Use 2–12 uppercase letters/numbers, starting with a letter.')
        return value

    def get_member_ids(self, obj):
        return list(obj.memberships.values_list('membership_id', flat=True))

    def get_reviewer_ids(self, obj):
        return list(obj.memberships.filter(is_reviewer=True, membership__role__in=['Admin', 'Manager'], membership__user__is_active=True).values_list('membership_id', flat=True))

    class Meta:
        model = Project
        fields = ['id', 'name', 'code', 'description', 'due', 'color', 'member_ids', 'reviewer_ids', 'version']
        read_only_fields = ['id']


class TaskSerializer(StrictSerializer):
    milestone = serializers.PrimaryKeyRelatedField(read_only=True)
    dependency_ids = serializers.SerializerMethodField()

    def get_dependency_ids(self, obj):
        return list(obj.dependencies.values_list('depends_on_id', flat=True))

    assignee_name = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True)
    code = serializers.SerializerMethodField()
    version = serializers.IntegerField(min_value=1, required=False)

    def get_assignee_name(self, obj):
        return obj.assignee.user.get_full_name() or obj.assignee.user.username

    def get_code(self, obj):
        return f'{obj.project.code}-{str(obj.id)[:8].upper()}'

    def validate(self, attrs):
        member = self.context['member']
        project = attrs.get('project', self.instance.project if self.instance else None)
        assignee = attrs.get('assignee', self.instance.assignee if self.instance else None)
        from .access import accessible_projects
        if not project or not accessible_projects(member).filter(pk=project.pk).exists():
            raise serializers.ValidationError({'project': 'Select an accessible project.'})
        if self.instance and project.pk != self.instance.project_id:
            raise serializers.ValidationError({'project': 'Moving tasks between projects is not supported.'})
        if not assignee or assignee.organization_id != member.organization_id or not ProjectMembership.objects.filter(project=project, membership=assignee).exists():
            raise serializers.ValidationError({'assignee': 'Assignee must be a member of this project.'})
        if not assignee.user.is_active:
            raise serializers.ValidationError({'assignee': 'Assignee is inactive.'})
        if not self.instance and ('version' in attrs or attrs.get('status', Task.Status.TODO) != Task.Status.TODO):
            raise serializers.ValidationError('New tasks must start in To do with a server-generated version.')
        complexity = attrs.get('complexity', self.instance.complexity if self.instance else 'Unestimated')
        context = attrs.get('complexity_context', self.instance.complexity_context if self.instance else '')
        if complexity != 'Unestimated' and not context.strip():
            raise serializers.ValidationError({'complexity_context': 'Explain the scope, uncertainty or technical challenge behind this estimate.'})
        if len(context) > 4000:
            raise serializers.ValidationError({'complexity_context': 'Use at most 4000 characters.'})
        return attrs

    class Meta:
        model = Task
        fields = ['id', 'code', 'title', 'project', 'project_name', 'assignee', 'assignee_name', 'status', 'priority', 'complexity', 'complexity_context', 'due', 'acceptance_criteria', 'version', 'created_at', 'updated_at', 'milestone', 'dependency_ids']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AuditSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    def get_actor(self, obj):
        return obj.actor.get_full_name() or obj.actor.username

    class Meta:
        model = AuditEvent
        fields = ['id', 'actor', 'text', 'action', 'task', 'project', 'before', 'after', 'at', 'request_id']


class WorkUpdateSerializer(StrictSerializer):
    author = serializers.CharField(source='author.get_full_name', read_only=True)
    body = serializers.CharField(max_length=4000)

    def validate_evidence_url(self, value):
        from urllib.parse import urlsplit
        parts = urlsplit(value)
        if value and (parts.scheme not in ['http', 'https'] or parts.username or parts.password):
            raise serializers.ValidationError('Use an HTTP or HTTPS link without embedded credentials.')
        return value

    class Meta:
        model = WorkUpdate
        fields = ['id', 'author', 'kind', 'body', 'evidence_url', 'created_at']
        read_only_fields = ['id', 'created_at']


class BlockerSerializer(StrictSerializer):
    reporter = serializers.CharField(source='reporter.get_full_name', read_only=True)
    reporter_user_id = serializers.IntegerField(source='reporter_id', read_only=True)
    owner_name = serializers.CharField(source='owner.user.get_full_name', read_only=True)
    resolved_by = serializers.CharField(source='resolved_by.get_full_name', read_only=True, allow_null=True)
    reason = serializers.CharField(max_length=2000)

    def validate_owner(self, owner):
        task = self.context['task']
        member = self.context['member']
        if owner.organization_id != task.project.organization_id or not owner.user.is_active or not ProjectMembership.objects.filter(project=task.project, membership=owner).exists():
            raise serializers.ValidationError('Select an active member of this project.')
        if member.role == Membership.Role.DEVELOPER and owner.pk != member.pk:
            raise serializers.ValidationError('Developers can report blockers owned by themselves. Managers can assign other owners.')
        return owner

    class Meta:
        model = Blocker
        fields = ['id', 'reporter', 'reporter_user_id', 'owner', 'owner_name', 'reason', 'opened_at', 'resolved_at', 'resolved_by', 'resolution']
        read_only_fields = ['id', 'opened_at', 'resolved_at', 'resolution']


class ResolutionSerializer(serializers.Serializer):
    resolution = serializers.CharField(max_length=2000)

    def validate(self, attrs):
        if set(self.initial_data) != {'resolution'}:
            raise serializers.ValidationError('Only the resolution field is accepted.')
        return attrs
