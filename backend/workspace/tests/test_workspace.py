from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase
from django.core.cache import cache
from rest_framework.test import APIClient
from ..models import Organization, Membership, Project, ProjectMembership, Task, AuditEvent


class WorkspaceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.org = Organization.objects.create(name='One', slug='one')
        self.other_org = Organization.objects.create(name='Two', slug='two')
        self.manager = User.objects.create_user('manager', password='test-password-123')
        self.developer = User.objects.create_user('developer', password='test-password-123')
        self.other = User.objects.create_user('other', password='test-password-123')
        self.manager_member = Membership.objects.create(user=self.manager, organization=self.org, role='Manager')
        self.dev_member = Membership.objects.create(user=self.developer, organization=self.org, role='Developer')
        self.other_member = Membership.objects.create(user=self.other, organization=self.other_org, role='Manager')
        self.project = Project.objects.create(organization=self.org, name='Portal', code='CP', due='2026-12-01')
        self.private = Project.objects.create(organization=self.org, name='Private', code='PR', due='2026-12-01')
        self.foreign = Project.objects.create(organization=self.other_org, name='Foreign', code='FO', due='2026-12-01')
        for member in [self.manager_member, self.dev_member]:
            ProjectMembership.objects.create(project=self.project, membership=member, is_reviewer=member.role == 'Manager')
        ProjectMembership.objects.create(project=self.foreign, membership=self.other_member)
        self.task = Task.objects.create(project=self.project, assignee=self.dev_member, title='Build portal', due='2026-12-01', acceptance_criteria='Tests pass')
        self.foreign_task = Task.objects.create(project=self.foreign, assignee=self.other_member, title='Private work', due='2026-12-01')
        self.client = APIClient()
        self.client.force_authenticate(self.manager)

    def task_url(self, task=None):
        return f'/api/v1/tasks/{(task or self.task).pk}/'

    def payload(self, **changes):
        return {'title': 'New task', 'project': self.project.id, 'assignee': self.dev_member.id, 'due': '2026-12-01', **changes}

    def test_anonymous_access_denied(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/v1/tasks/').status_code, 403)

    def test_project_and_organization_scope(self):
        response = self.client.get('/api/v1/projects/')
        self.assertEqual([p['id'] for p in response.data['results']], [self.project.id])
        self.assertEqual(self.client.get(self.task_url(self.foreign_task)).status_code, 404)
        self.assertEqual(self.client.get('/api/v1/tasks/', HTTP_X_ORGANIZATION_ID=str(self.other_org.id)).status_code, 404)

    def test_manager_create_records_actor_and_audit(self):
        response = self.client.post('/api/v1/tasks/', self.payload(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        event = AuditEvent.objects.get(task_id=response.data['id'])
        self.assertEqual(event.actor, self.manager)
        self.assertEqual(event.after['title'], 'New task')

    def test_developer_cannot_create_or_reassign(self):
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.post('/api/v1/tasks/', self.payload(), format='json').status_code, 403)
        response = self.client.patch(self.task_url(), {'assignee': self.manager_member.pk, 'version': 1}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_developer_updates_own_task(self):
        self.client.force_authenticate(self.developer)
        response = self.client.patch(self.task_url(), {'status': 'In progress', 'version': 1}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.task.refresh_from_db()
        self.assertEqual(self.task.version, 2)
        self.assertEqual(AuditEvent.objects.get().actor, self.developer)

    def test_developer_cannot_update_another_assignment(self):
        self.task.assignee = self.manager_member
        self.task.save()
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.patch(self.task_url(), {'status': 'In progress', 'version': 1}, format='json').status_code, 403)

    def test_reject_foreign_and_nonproject_assignees(self):
        response = self.client.post('/api/v1/tasks/', self.payload(assignee=self.other_member.pk), format='json')
        self.assertEqual(response.status_code, 400)
        ProjectMembership.objects.filter(project=self.project, membership=self.dev_member).delete()
        self.assertEqual(self.client.post('/api/v1/tasks/', self.payload(), format='json').status_code, 400)

    def test_cannot_create_in_unassigned_project(self):
        self.assertEqual(self.client.post('/api/v1/tasks/', self.payload(project=self.private.pk), format='json').status_code, 400)

    def test_invalid_transition_and_missing_version(self):
        self.assertEqual(self.client.patch(self.task_url(), {'status': 'Done', 'version': 1}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(self.task_url(), {'status': 'In progress'}, format='json').status_code, 400)
        self.assertFalse(AuditEvent.objects.exists())

    def test_stale_version_does_not_overwrite_or_duplicate_audit(self):
        self.client.patch(self.task_url(), {'status': 'In progress', 'version': 1}, format='json')
        response = self.client.patch(self.task_url(), {'status': 'Blocked', 'version': 1}, format='json')
        self.assertEqual(response.status_code, 409)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'In progress')
        self.assertEqual(AuditEvent.objects.count(), 1)

    def test_manager_accepts_reviewed_work(self):
        self.task.status = 'In review'
        self.task.save()
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.patch(self.task_url(), {'status': 'Done', 'version': 1}, format='json').status_code, 403)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.patch(self.task_url(), {'status': 'Done', 'version': 1}, format='json').status_code, 200)

    def test_completion_requires_criteria(self):
        self.task.status = 'In review'
        self.task.acceptance_criteria = ''
        self.task.save()
        self.assertEqual(self.client.patch(self.task_url(), {'status': 'Done', 'version': 1}, format='json').status_code, 400)

    def test_audit_is_read_only_and_scoped(self):
        self.client.patch(self.task_url(), {'status': 'In progress', 'version': 1}, format='json')
        event = AuditEvent.objects.get()
        self.assertEqual(self.client.post('/api/v1/audit-events/', {}, format='json').status_code, 405)
        self.assertEqual(self.client.patch(f'/api/v1/audit-events/{event.pk}/', {'text': 'tampered'}, format='json').status_code, 405)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get('/api/v1/audit-events/').data['results'], [])

    def test_unknown_fields_rejected(self):
        self.assertEqual(self.client.post('/api/v1/tasks/', self.payload(actor=self.other.pk), format='json').status_code, 400)

    def test_mutation_rolls_back_when_audit_fails(self):
        with patch('workspace.views.AuditEvent.objects.create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.patch(self.task_url(), {'status': 'In progress', 'version': 1}, format='json')
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'To do')
        self.assertEqual(self.task.version, 1)

    def test_login_csrf_session_and_logout(self):
        client = APIClient(enforce_csrf_checks=True)
        credentials = {'username': 'manager', 'password': 'test-password-123'}
        self.assertEqual(client.post('/api/v1/auth/login/', credentials, format='json').status_code, 403)
        token = client.get('/api/v1/auth/session/').json()['csrfToken']
        result = client.post('/api/v1/auth/login/', credentials, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()['user']['role'], 'Manager')
        token = result.json()['csrfToken']
        self.assertEqual(client.patch(self.task_url(), {'status': 'In progress', 'version': 1}, format='json').status_code, 403)
        self.assertEqual(client.patch(self.task_url(), {'status': 'In progress', 'version': 1}, format='json', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.post('/api/v1/auth/logout/', {}, format='json', HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.get('/api/v1/tasks/').status_code, 403)

    def test_login_rate_limit(self):
        for _ in range(10):
            result = self.client.post('/api/v1/auth/login/', {'username': 'missing', 'password': 'bad'}, format='json')
            self.assertEqual(result.status_code, 400)
        self.assertEqual(self.client.post('/api/v1/auth/login/', {'username': 'missing', 'password': 'bad'}, format='json').status_code, 429)

    def test_dashboard_counts_are_project_scoped(self):
        self.assertEqual(self.client.get('/api/v1/dashboard/').data['tasks'], 1)

    def test_malformed_identifiers_are_client_errors(self):
        self.assertEqual(self.client.get('/api/v1/tasks/not-a-uuid/').status_code, 404)
        response = self.client.get('/api/v1/tasks/', HTTP_X_ORGANIZATION_ID='invalid')
        self.assertEqual(response.status_code, 400)
