"""Project roster, account creation, role, and audit isolation regression tests."""
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from . import test_workspace as base
from ..models import AuditEvent, Blocker, Membership, Project, ProjectMembership, Task


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ManagementTests(TestCase):
    setUp = base.WorkspaceTests.setUp

    def admin(self):
        user = User.objects.create_user('owner', password='test-password-123')
        member = Membership.objects.create(user=user, organization=self.org, role='Admin')
        self.client.force_authenticate(user)
        return member

    def project_payload(self, **changes):
        return {'name': 'New delivery project', 'code': 'NEW', 'due': '2026-12-15', **changes}

    def roster(self, ids, version=1):
        return self.client.put(f'/api/v1/projects/{self.project.pk}/members/', {'member_ids': ids, 'version': version}, format='json')

    def account_payload(self, **changes):
        return {'username': 'newdeveloper', 'first_name': 'New', 'last_name': 'Developer', 'password': 'N0t-a-real-Password!2026', 'role': 'Developer', **changes}

    def test_manager_creates_project_and_audit(self):
        result = self.client.post('/api/v1/projects/', self.project_payload(), format='json')
        self.assertEqual(result.status_code, 201, result.data)
        project = Project.objects.get(pk=result.data['id'])
        self.assertTrue(project.memberships.filter(membership=self.manager_member).exists())
        event = AuditEvent.objects.get(action='project.created')
        self.assertIsNone(event.task_id)
        self.assertEqual(event.organization, self.org)

    def test_duplicate_code_and_invalid_code_are_client_errors(self):
        for code in ['cp', 'BAD CODE', '1BAD']:
            result = self.client.post('/api/v1/projects/', self.project_payload(code=code), format='json')
            self.assertEqual(result.status_code, 400, result.data)

    def test_developer_cannot_create_or_edit_projects(self):
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.post('/api/v1/projects/', self.project_payload(), format='json').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/v1/projects/{self.project.pk}/', {'name': 'Changed', 'version': 1}, format='json').status_code, 403)
        self.assertEqual(self.roster([self.dev_member.pk]).status_code, 403)

    def test_project_edit_version_code_and_scope(self):
        url = f'/api/v1/projects/{self.project.pk}/'
        result = self.client.patch(url, {'name': 'Portal v2', 'version': 1}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['version'], 2)
        self.assertEqual(self.client.patch(url, {'name': 'Stale', 'version': 1}, format='json').status_code, 409)
        self.assertEqual(self.client.patch(url, {'code': 'CHANGE', 'version': 2}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(f'/api/v1/projects/{self.foreign.pk}/', {'name': 'Leak', 'version': 1}, format='json').status_code, 404)

    def test_manager_directory_contains_unassigned_workspace_members(self):
        fresh = User.objects.create_user('unassigned')
        membership = Membership.objects.create(user=fresh, organization=self.org, role='Developer')
        ids = [item['id'] for item in self.client.get('/api/v1/members/').data['results']]
        self.assertIn(membership.pk, ids)
        self.assertNotIn(self.other_member.pk, ids)
        result = self.roster([self.manager_member.pk, self.dev_member.pk, membership.pk])
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(AuditEvent.objects.get().action, 'project.members_changed')

    def test_invalid_roster_and_manager_self_removal(self):
        self.assertEqual(self.roster([self.manager_member.pk, self.other_member.pk]).status_code, 400)
        self.assertEqual(self.roster([self.dev_member.pk]).status_code, 400)
        self.assertEqual(self.roster(['bad']).status_code, 400)

    def test_cannot_remove_open_assignee_but_can_remove_completed_assignee(self):
        self.assertEqual(self.roster([self.manager_member.pk]).status_code, 400)
        self.task.status = 'Done'
        self.task.save()
        self.assertEqual(self.roster([self.manager_member.pk]).status_code, 200)
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get(f'/api/v1/tasks/{self.task.pk}/').status_code, 404)

    def test_cannot_remove_owner_with_open_blocker(self):
        self.task.assignee = self.manager_member
        self.task.save()
        Blocker.objects.create(task=self.task, reporter=self.manager, owner=self.dev_member, reason='Dependency')
        self.assertEqual(self.roster([self.manager_member.pk]).status_code, 400)

    def test_stale_roster_rejected(self):
        self.project.version = 2
        self.project.save()
        self.assertEqual(self.roster([self.manager_member.pk, self.dev_member.pk]).status_code, 409)

    def test_manager_cannot_create_account_or_change_roles(self):
        self.assertEqual(self.client.post('/api/v1/members/', self.account_payload(), format='json').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/v1/members/{self.dev_member.pk}/', {'role': 'Manager'}, format='json').status_code, 403)

    def test_admin_creates_account_with_hashed_password_no_secret_in_response_or_audit(self):
        self.admin()
        result = self.client.post('/api/v1/members/', self.account_payload(), format='json')
        self.assertEqual(result.status_code, 201, result.data)
        user = User.objects.get(username='newdeveloper')
        self.assertTrue(user.check_password(self.account_payload()['password']))
        self.assertNotIn('password', result.data)
        self.assertNotIn(self.account_payload()['password'], str(AuditEvent.objects.get().after))
        self.assertFalse(user.is_superuser)

    def test_invalid_weak_duplicate_or_injected_account_payload_rejected(self):
        self.admin()
        for changes in [{'password': '123'}, {'username': 'manager'}, {'username': 'bad name'}, {'is_superuser': True}]:
            result = self.client.post('/api/v1/members/', self.account_payload(**changes), format='json')
            self.assertEqual(result.status_code, 400, result.data)
        self.assertFalse(User.objects.filter(username='newdeveloper').exists())

    def test_role_change_scope_and_last_admin_guard(self):
        admin = self.admin()
        result = self.client.patch(f'/api/v1/members/{self.dev_member.pk}/', {'role': 'Manager'}, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.client.patch(f'/api/v1/members/{self.other_member.pk}/', {'role': 'Manager'}, format='json').status_code, 404)
        self.assertEqual(self.client.patch(f'/api/v1/members/{admin.pk}/', {'role': 'Developer'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(f'/api/v1/members/{self.dev_member.pk}/', {'role': 'Root'}, format='json').status_code, 400)

    def test_organization_audit_is_admin_only(self):
        self.admin()
        self.client.post('/api/v1/members/', self.account_payload(), format='json')
        self.assertEqual(self.client.get('/api/v1/audit-events/').data['count'], 1)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.get('/api/v1/audit-events/').data['count'], 0)

    def test_role_is_rechecked_after_waiting_for_organization_lock(self):
        admin = self.admin()
        # Simulate an admin demoted by another request before this request obtains the lock.
        with patch('workspace.team_management.current_membership', side_effect=[admin, self.dev_member]):
            result = self.client.patch(f'/api/v1/members/{self.manager_member.pk}/', {'role': 'Developer'}, format='json')
        self.assertEqual(result.status_code, 403)
        self.manager_member.refresh_from_db()
        self.assertEqual(self.manager_member.role, 'Manager')

    def test_account_and_project_roll_back_on_audit_failure(self):
        self.admin()
        with patch('workspace.team_management.AuditEvent.objects.create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.post('/api/v1/members/', self.account_payload(), format='json')
            with self.assertRaises(RuntimeError):
                self.client.post('/api/v1/projects/', self.project_payload(), format='json')
        self.assertFalse(User.objects.filter(username='newdeveloper').exists())
        self.assertFalse(Project.objects.filter(code='NEW').exists())
