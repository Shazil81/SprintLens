"""Author-private AI previews with explicit consent, daily limits and source citations."""
import hashlib
import json
from datetime import timedelta
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from .access import accessible_projects, current_membership, require_manager
from .ai_provider import ProviderError, generate_insight
from .development import lock_project
from .models import AuditEvent, InsightRun
from .project_snapshot import SnapshotInput, project_snapshot


def ai_status():
    configured = bool(settings.AI_INSIGHTS_ENABLED and settings.GEMINI_API_KEY)
    return {'provider':'Gemini','model':settings.GEMINI_MODEL,'configured':configured,
            'daily_limit':settings.AI_DAILY_LIMIT,
            'message':'Ready for explicit generation.' if configured else 'Gemini is not enabled. Configure a free-tier API key on the backend to generate AI insights.'}


def evidence_bundle(snapshot):
    evidence = {'project':snapshot['project'],'current':snapshot['current'],'observed':snapshot['observed']}
    evidence.update({f'task:{row["code"]}':row for row in snapshot['tasks']})
    evidence.update({f'milestone:{i+1}':row for i,row in enumerate(snapshot['milestones'])})
    return {'period':snapshot['period'],'captured_at':snapshot['captured_at'],'omitted_tasks':snapshot['omitted_tasks'],
            'limitations':snapshot['limitations'],'evidence':evidence}


class InsightSerializer(serializers.ModelSerializer):
    class Meta:
        model = InsightRun
        fields = ['id','project','creator','provider','model','status','input_snapshot','input_hash','output','error','created_at','started_at','finished_at']
        read_only_fields = fields


class InsightViewSet(mixins.ListModelMixin,mixins.RetrieveModelMixin,viewsets.GenericViewSet):
    serializer_class = InsightSerializer

    def get_queryset(self):
        member = current_membership(self.request)
        require_manager(member)
        return InsightRun.objects.filter(creator=member,project__in=accessible_projects(member))

    @action(detail=False,methods=['get'])
    def configuration(self, request):
        require_manager(current_membership(request))
        return Response(ai_status())

    @transaction.atomic
    def create(self, request):
        member = current_membership(request)
        require_manager(member)
        serializer = SnapshotInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = get_object_or_404(accessible_projects(member),pk=serializer.validated_data['project'])
        member = lock_project(member,project)
        require_manager(member)
        snapshot = evidence_bundle(project_snapshot(project,serializer.validated_data['days']))
        digest = hashlib.sha256(json.dumps(snapshot,sort_keys=True).encode()).hexdigest()
        item = InsightRun.objects.create(project=project,creator=member,provider='Gemini',model=settings.GEMINI_MODEL,
                                         input_snapshot=snapshot,input_hash=digest)
        self.record(item,'insight.prepared')
        return Response(self.get_serializer(item).data,status=201)

    def record(self, item, action_name):
        AuditEvent.objects.create(project=item.project,actor=self.request.user,action=action_name,
            text='Updated a private AI insight',after={'insight_id':str(item.pk),'status':item.status})

    @action(detail=True,methods=['post'])
    def generate(self, request, pk=None):
        # Claim once in a short transaction; never hold database locks during the network request.
        original = self.get_object()
        with transaction.atomic():
            member = lock_project(current_membership(request),original.project)
            require_manager(member)
            item = get_object_or_404(self.get_queryset().select_for_update(),pk=pk)
            if set(request.data) != {'input_hash','consent'} or request.data.get('consent') is not True:
                raise serializers.ValidationError('Review the snapshot and explicitly consent to send it to Gemini.')
            if request.data['input_hash'] != item.input_hash:
                raise serializers.ValidationError('The approved snapshot does not match. Reload the preview.')
            if item.status == 'Ready':
                return Response(self.get_serializer(item).data)
            if item.status != 'Prepared':
                return Response({'detail':'This preview was already submitted. Prepare a new preview to retry.'},status=409)
            if not ai_status()['configured']:
                return Response({'detail':ai_status()['message']},status=503)
            if timezone.now()-item.created_at > timedelta(hours=1):
                raise serializers.ValidationError('This preview expired. Prepare a fresh snapshot.')
            used = InsightRun.objects.filter(creator=member,started_at__date=timezone.localdate()).count()
            if used >= settings.AI_DAILY_LIMIT:
                return Response({'detail':'Your daily AI generation limit is reached. Reports remain available.'},status=429)
            item.status,item.started_at = 'Generating',timezone.now()
            item.save(update_fields=['status','started_at'])
            self.record(item,'insight.started')
        try:
            output,error = generate_insight(item.input_snapshot,item.model),''
        except ProviderError as exc:
            output,error = {},str(exc)
        with transaction.atomic():
            # A revoked membership must not receive model output after an in-flight request.
            member = lock_project(current_membership(request),original.project)
            require_manager(member)
            item = get_object_or_404(self.get_queryset().select_for_update(),pk=pk)
            item.output,item.error = output,error
            item.status = 'Failed' if error else 'Ready'
            item.finished_at = timezone.now()
            item.save(update_fields=['output','error','status','finished_at'])
            self.record(item,'insight.failed' if error else 'insight.generated')
        if error:
            return Response({'detail':error,'run':self.get_serializer(item).data},status=502)
        return Response(self.get_serializer(item).data)
