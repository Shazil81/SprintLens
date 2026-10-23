"""Versioned report drafts and authenticated, immutable published exports."""
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from .access import accessible_projects, current_membership, require_manager
from .development import lock_project
from .models import AuditEvent, ProjectReport
from .project_snapshot import SnapshotInput, project_snapshot
from .report_exports import csv_report, pdf_report
from .team_management import expected_version


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectReport
        fields = ['id','project','creator','title','summary','achievements','risks','next_steps','snapshot','status','version','created_at','published_at']
        read_only_fields = fields


class ReportEdit(serializers.Serializer):
    title = serializers.CharField(max_length=160, required=False)
    summary = serializers.CharField(max_length=4000, allow_blank=True, required=False)
    achievements = serializers.CharField(max_length=4000, allow_blank=True, required=False)
    risks = serializers.CharField(max_length=4000, allow_blank=True, required=False)
    next_steps = serializers.CharField(max_length=4000, allow_blank=True, required=False)
    version = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        if set(self.initial_data) - set(self.fields):
            raise serializers.ValidationError('Send only editable report text and version.')
        return attrs


class ReportViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    serializer_class = ReportSerializer

    def get_queryset(self):
        member = current_membership(self.request)
        return ProjectReport.objects.filter(project__in=accessible_projects(member)).filter(Q(creator=member) | Q(status='Published'))

    def record(self, item, action_name):
        AuditEvent.objects.create(project=item.project, actor=self.request.user, action=action_name,
            text='Updated a project report', after={'report_id':str(item.pk),'status':item.status,'version':item.version})

    @transaction.atomic
    def create(self, request):
        member = current_membership(request)
        require_manager(member)
        serializer = SnapshotInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = get_object_or_404(accessible_projects(member), pk=serializer.validated_data['project'])
        member = lock_project(member,project)
        require_manager(member)
        snapshot = project_snapshot(project,serializer.validated_data['days'])
        counts = snapshot['current']
        item = ProjectReport.objects.create(project=project,creator=member,title=f'{project.name} progress report',snapshot=snapshot,
            summary=f"As of capture: {counts['open']} open tasks, {counts['done']} currently done, {counts['blocked']} blocked and {counts['overdue']} overdue.",
            achievements=f"{snapshot['observed']['completion_events']} completion transitions recorded in the selected period. Review the captured evidence before sharing.",
            risks='Review overdue tasks, unfinished prerequisites and current blockers in the task snapshot.',
            next_steps='Confirm the next milestone, unblock dependencies and validate acceptance criteria.')
        self.record(item,'report.created')
        return Response(self.get_serializer(item).data,status=201)

    def locked_draft(self):
        original = self.get_object()
        member = lock_project(current_membership(self.request),original.project)
        require_manager(member)
        item = get_object_or_404(self.get_queryset().select_for_update(),pk=original.pk)
        if item.creator_id != member.pk or item.status != 'Draft':
            raise PermissionDenied('Only the author can change an unpublished report.')
        return item

    @transaction.atomic
    def partial_update(self, request, pk=None):
        item = self.locked_draft()
        serializer = ReportEdit(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not expected_version(serializer.validated_data,item.version):
            return Response({'detail':'Report changed. Refresh before editing.'},status=409)
        values = dict(serializer.validated_data)
        values.pop('version')
        for key,value in values.items():
            setattr(item,key,value)
        item.version += 1
        item.save()
        self.record(item,'report.updated')
        return Response(self.get_serializer(item).data)

    @action(detail=True,methods=['post'])
    @transaction.atomic
    def publish(self, request, pk=None):
        item = self.locked_draft()
        if set(request.data) != {'version'}:
            raise serializers.ValidationError('Send only version.')
        if not expected_version(request.data,item.version):
            return Response({'detail':'Report changed. Refresh before publishing.'},status=409)
        if not item.summary.strip() or not item.next_steps.strip():
            raise serializers.ValidationError('Review and complete the summary and next steps before publishing.')
        item.status, item.published_at = 'Published', timezone.now()
        item.version += 1
        item.save(update_fields=['status','published_at','version'])
        self.record(item,'report.published')
        return Response(self.get_serializer(item).data)

    @action(detail=True,methods=['get'],url_path='download')
    def download(self, request, pk=None):
        item = self.get_object()
        kind = request.query_params.get('file','pdf')
        if kind == 'json':
            import json
            body = json.dumps(self.get_serializer(item).data,ensure_ascii=False,indent=2).encode('utf-8')
            media = 'application/json'
        elif kind == 'csv':
            body,media = csv_report(item),'text/csv; charset=utf-8'
        elif kind == 'pdf':
            body,media = pdf_report(item),'application/pdf'
        else:
            raise serializers.ValidationError('Choose pdf, csv or json.')
        response = HttpResponse(body,content_type=media)
        response['Content-Disposition'] = f'attachment; filename="sprintlens-report-{item.pk}.{kind}"'
        response['Cache-Control'] = 'private, no-store'
        return response
