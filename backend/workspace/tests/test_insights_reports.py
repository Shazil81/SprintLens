"""Exercise disclosure boundaries, AI failures and immutable report exports without paid requests."""
import json
from datetime import timedelta
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from django.test import TestCase, override_settings
from django.utils import timezone
from . import test_workspace as base
from ..ai_provider import ProviderError, generate_insight, validate_output
from ..models import AuditEvent, InsightRun, Membership, ProjectMembership, ProjectReport, Task, WorkUpdate
from ..project_snapshot import project_snapshot
from ..report_exports import csv_cell


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ReportsAndInsightsTests(TestCase):
    setUp = base.WorkspaceTests.setUp

    def report(self, **changes):
        response = self.client.post('/api/v1/reports/', {'project':self.project.pk,'days':7,**changes}, format='json')
        self.assertEqual(response.status_code,201,response.data)
        return response.data

    def preview(self):
        response = self.client.post('/api/v1/insights/', {'project':self.project.pk,'days':7}, format='json')
        self.assertEqual(response.status_code,201,response.data)
        return response.data

    def generate(self, run, **changes):
        return self.client.post(f"/api/v1/insights/{run['id']}/generate/", {'input_hash':run['input_hash'],'consent':True,**changes},format='json')

    def output(self):
        return {'summary':'The snapshot shows one open task.','findings':[{'kind':'Follow-up','text':'Confirm acceptance criteria.','evidence_ids':['current']}],
                'limitations':['No quality conclusion can be drawn from task counts.']}

    def test_snapshot_excludes_names_notes_and_foreign_project(self):
        WorkUpdate.objects.create(task=self.task,author=self.manager,kind='Feedback',body='PRIVATE MANAGER FEEDBACK')
        WorkUpdate.objects.create(task=self.task,author=self.developer,kind='Update',body='PRIVATE PROGRESS BODY')
        result = project_snapshot(self.project)
        text = json.dumps(result)
        for secret in ['PRIVATE MANAGER FEEDBACK','PRIVATE PROGRESS BODY','Private work','manager','developer']:
            self.assertNotIn(secret,text)
        self.assertEqual(result['observed']['work_updates'],1)
        self.assertEqual(result['observed']['completion_events'],0)

    def test_preview_makes_no_ai_request_and_configuration_hides_key(self):
        with patch('workspace.insights.generate_insight') as generate:
            run = self.preview()
        generate.assert_not_called()
        self.assertEqual(run['status'],'Prepared')
        self.assertIn('current',run['input_snapshot']['evidence'])
        with self.settings(GEMINI_API_KEY='hidden-test-key'):
            config = self.client.get('/api/v1/insights/configuration/')
        self.assertNotIn('hidden-test-key',str(config.data))

    def test_preview_permission_and_foreign_scope(self):
        self.assertEqual(self.client.post('/api/v1/insights/',{'project':self.foreign.pk},format='json').status_code,404)
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.post('/api/v1/insights/',{'project':self.project.pk},format='json').status_code,403)
        self.assertEqual(self.client.get('/api/v1/insights/').status_code,403)

    def test_insight_is_author_private_even_for_other_manager(self):
        run = self.preview()
        Membership.objects.filter(pk=self.dev_member.pk).update(role='Manager')
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get(f"/api/v1/insights/{run['id']}/").status_code,404)

    def test_missing_config_consent_and_digest_never_call_provider(self):
        run = self.preview()
        with self.settings(AI_INSIGHTS_ENABLED=False),patch('workspace.insights.generate_insight') as generate:
            self.assertEqual(self.generate(run,consent=False).status_code,400)
            self.assertEqual(self.generate(run,input_hash='different').status_code,400)
            self.assertEqual(self.generate(run).status_code,503)
        generate.assert_not_called()
        self.assertIsNone(InsightRun.objects.get(pk=run['id']).started_at)

    @override_settings(AI_INSIGHTS_ENABLED=True,GEMINI_API_KEY='test-only-key',AI_DAILY_LIMIT=5)
    def test_generation_is_once_only_and_audited(self):
        run = self.preview()
        with patch('workspace.insights.generate_insight',return_value=self.output()) as generate:
            result = self.generate(run)
            self.assertEqual(result.status_code,200,result.data)
            self.assertEqual(result.data['status'],'Ready')
            self.assertEqual(self.generate(run).status_code,200)
        self.assertEqual(generate.call_count,1)
        self.assertTrue(AuditEvent.objects.filter(action='insight.generated').exists())

    @override_settings(AI_INSIGHTS_ENABLED=True,GEMINI_API_KEY='test-only-key',AI_DAILY_LIMIT=1)
    def test_quota_and_expired_preview(self):
        run = self.preview()
        InsightRun.objects.filter(pk=run['id']).update(created_at=timezone.now()-timedelta(hours=2))
        with patch('workspace.insights.generate_insight') as generate:
            self.assertEqual(self.generate(run).status_code,400)
        generate.assert_not_called()
        first,second = self.preview(),self.preview()
        with patch('workspace.insights.generate_insight',return_value=self.output()) as generate:
            self.assertEqual(self.generate(first).status_code,200)
            self.assertEqual(self.generate(second).status_code,429)
        self.assertEqual(generate.call_count,1)

    @override_settings(AI_INSIGHTS_ENABLED=True,GEMINI_API_KEY='test-only-key')
    def test_provider_failure_has_no_fake_output_or_silent_retry(self):
        run = self.preview()
        with patch('workspace.insights.generate_insight',side_effect=ProviderError('Gemini quota reached.')) as generate:
            response = self.generate(run)
            self.assertEqual(response.status_code,502)
            self.assertEqual(response.data['detail'],'Gemini quota reached.')
            self.assertEqual(self.generate(run).status_code,409)
        self.assertEqual(generate.call_count,1)
        item = InsightRun.objects.get(pk=run['id'])
        self.assertEqual(item.status,'Failed')
        self.assertEqual(item.output,{})

    def test_output_schema_and_foreign_citations_rejected(self):
        output = self.output()
        self.assertEqual(validate_output(output,{'current'}),output)
        for wrong in [{**output,'score':99},{**output,'findings':[{'kind':'Risk','text':'Unsafe claim','evidence_ids':['foreign-task']}]}]:
            with self.assertRaises(ProviderError):
                validate_output(wrong,{'current'})

    @override_settings(GEMINI_API_KEY='test-only-key')
    def test_adapter_headers_schema_bounded_request_and_response(self):
        run = self.preview()
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(self.output())}]}}]}).encode()
        opener = MagicMock()
        opener.open.return_value = response
        with patch('workspace.ai_provider.build_opener',return_value=opener):
            result = generate_insight(run['input_snapshot'],'gemini-2.5-flash-lite')
        self.assertEqual(result,self.output())
        sent = opener.open.call_args.args[0]
        self.assertNotIn('test-only-key',sent.full_url)
        payload = json.loads(sent.data)
        self.assertNotIn('tools',payload)
        self.assertEqual(payload['generationConfig']['responseMimeType'],'application/json')
        self.assertEqual(opener.open.call_args.kwargs['timeout'],30)
        response.read.assert_called_once_with(131073)

    def test_http_errors_do_not_expose_provider_body_or_key(self):
        run = self.preview()
        opener = MagicMock()
        opener.open.side_effect = HTTPError('https://example.com',429,'SECRET PROVIDER BODY',{},None)
        with patch('workspace.ai_provider.build_opener',return_value=opener):
            with self.assertRaises(ProviderError) as error:
                generate_insight(run['input_snapshot'],'gemini-2.5-flash-lite')
        self.assertIn('quota',str(error.exception))
        self.assertNotIn('SECRET',str(error.exception))

    def test_draft_private_then_published_shared_and_immutable(self):
        report = self.report()
        url = f"/api/v1/reports/{report['id']}/"
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get(url).status_code,404)
        self.client.force_authenticate(self.manager)
        result = self.client.patch(url,{'version':1,'summary':'Verified project update.'},format='json')
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(self.client.post(url+'publish/',{'version':2},format='json').status_code,200)
        self.assertEqual(self.client.patch(url,{'version':3,'summary':'Overwrite'},format='json').status_code,403)
        Task.objects.filter(pk=self.task.pk).update(title='Changed later')
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get(url).data['snapshot']['tasks'][0]['title'],'Build portal')

    def test_report_version_and_snapshot_spoof_rejected(self):
        report = self.report()
        url = f"/api/v1/reports/{report['id']}/"
        self.assertEqual(self.client.patch(url,{'version':1,'snapshot':{}},format='json').status_code,400)
        self.assertEqual(self.client.patch(url,{'version':99,'summary':'Stale'},format='json').status_code,409)
        self.assertEqual(self.client.post('/api/v1/reports/',{'project':self.foreign.pk},format='json').status_code,404)
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.post('/api/v1/reports/',{'project':self.project.pk},format='json').status_code,403)

    def test_export_permissions_pdf_csv_json_and_no_cache(self):
        report = self.report()
        url = f"/api/v1/reports/{report['id']}/download/"
        for kind in ['pdf','csv','json']:
            response = self.client.get(url,{'file':kind})
            self.assertEqual(response.status_code,200)
            directives = {part.strip() for part in response['Cache-Control'].split(',')}
            self.assertTrue({'private','no-store'} <= directives)
            self.assertNotIn('public',directives)
            self.assertIn('attachment',response['Content-Disposition'])
            if kind == 'pdf':
                self.assertTrue(response.content.startswith(b'%PDF-'))
            elif kind == 'json':
                self.assertEqual(json.loads(response.content)['id'],report['id'])
            else:
                self.assertIn(b'Task title',response.content)
        self.assertEqual(self.client.get(url,{'file':'html'}).status_code,400)
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get(url,{'file':'pdf'}).status_code,404)

    def test_formula_injection_and_markup_in_pdf(self):
        for cell in ['=SUM(A1:A2)',' +cmd','@IMPORT','-1+1','\tformula']:
            self.assertTrue(csv_cell(cell).startswith("'"))
        report = self.report()
        url = f"/api/v1/reports/{report['id']}/"
        self.client.patch(url,{'version':1,'summary':'<script>not executable</script> & safe text'},format='json')
        response = self.client.get(url+'download/',{'file':'pdf'})
        self.assertEqual(response.status_code,200)

    def test_published_report_revoked_project_access(self):
        report = self.report()
        url = f"/api/v1/reports/{report['id']}/"
        self.client.post(url+'publish/',{'version':1},format='json')
        ProjectMembership.objects.filter(project=self.project,membership=self.dev_member).delete()
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get(url+'download/',{'file':'json'}).status_code,404)

    def test_report_creation_rollback_when_audit_fails(self):
        with patch('workspace.reports.AuditEvent.objects.create',side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.report()
        self.assertFalse(ProjectReport.objects.exists())

    def test_snapshot_marks_truncation_and_no_completion_estimate(self):
        Task.objects.bulk_create([Task(project=self.project,assignee=self.dev_member,title=f'Task {i}',due='2026-12-01') for i in range(201)])
        snapshot = project_snapshot(self.project)
        self.assertEqual(len(snapshot['tasks']),200)
        self.assertEqual(snapshot['current']['total'],202)
        self.assertEqual(snapshot['omitted_tasks'],2)
