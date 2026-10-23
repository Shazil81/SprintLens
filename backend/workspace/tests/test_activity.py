"""Permission, persistence, and workflow checks for nested task activity APIs."""
from unittest.mock import patch
from django.test import TestCase
from . import test_workspace as base
from ..models import AuditEvent, Blocker, Task, WorkUpdate


class TaskActivityTests(TestCase):
    setUp = base.WorkspaceTests.setUp
    task_url = base.WorkspaceTests.task_url

    def url(self, suffix):
        return self.task_url() + suffix

    def report(self, owner=None):
        return self.client.post(self.url('blockers/'), {'reason': 'Waiting for API credentials.', 'owner': owner or self.dev_member.pk}, format='json')

    def test_assignee_work_update_persists_evidence_and_actor(self):
        self.client.force_authenticate(self.developer)
        response = self.client.post(self.url('updates/'), {'body': 'Implemented the endpoint.', 'evidence_url': 'https://github.com/example/repo/pull/1'}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(WorkUpdate.objects.get().author, self.developer)
        self.assertEqual(AuditEvent.objects.get().action, 'task.work_update')
        self.assertEqual(self.client.get(self.url('updates/')).data['count'], 1)

    def test_work_update_permissions_and_feedback(self):
        self.assertEqual(self.client.post(self.url('updates/'), {'body': 'Spoofed developer update.'}, format='json').status_code, 403)
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.post(self.url('updates/'), {'kind': 'Feedback', 'body': 'Manager note.'}, format='json').status_code, 403)
        self.task.assignee = self.manager_member
        self.task.save()
        self.assertEqual(self.client.post(self.url('updates/'), {'body': 'Unassigned note.'}, format='json').status_code, 403)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(self.url('updates/'), {'kind': 'Feedback', 'body': 'Please add retry coverage.'}, format='json').status_code, 201)

    def test_activity_is_project_scoped(self):
        for suffix in ['updates/', 'blockers/']:
            self.assertEqual(self.client.get(self.task_url(self.foreign_task) + suffix).status_code, 404)

    def test_blank_notes_unsafe_links_and_actor_spoofing_rejected(self):
        self.client.force_authenticate(self.developer)
        for body in [{'body': '   '}, {'body': 'x', 'evidence_url': 'javascript:alert(1)'}, {'body': 'x', 'evidence_url': 'https://user:secret@example.com'}, {'body': 'x', 'author': self.manager.pk}]:
            self.assertEqual(self.client.post(self.url('updates/'), body, format='json').status_code, 400)
        self.assertFalse(WorkUpdate.objects.exists())

    def test_report_marks_task_blocked_and_invalidates_old_version(self):
        self.client.force_authenticate(self.developer)
        response = self.report()
        self.assertEqual(response.status_code, 201, response.data)
        self.task.refresh_from_db()
        self.assertEqual((self.task.status, self.task.version), ('Blocked', 2))
        self.assertEqual(Blocker.objects.get().reporter, self.developer)
        self.assertEqual(AuditEvent.objects.get().action, 'blocker.reported')
        self.assertEqual(self.client.patch(self.task_url(), {'status': 'In progress', 'version': 1}, format='json').status_code, 409)
        self.assertEqual(self.client.patch(self.task_url(), {'status': 'In progress', 'version': 2}, format='json').status_code, 400)

    def test_resolve_requires_note_and_restores_progress(self):
        response = self.report()
        url = self.url(f'blockers/{response.data["id"]}/resolve/')
        self.assertEqual(self.client.post(url, {'resolution': '  '}, format='json').status_code, 400)
        self.client.force_authenticate(self.developer)
        response = self.client.post(url, {'resolution': 'Credentials received and verified.'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.task.refresh_from_db()
        self.assertEqual((self.task.status, self.task.version), ('In progress', 3))
        item = Blocker.objects.get()
        self.assertEqual(item.resolved_by, self.developer)
        self.assertIsNotNone(item.resolved_at)
        self.assertEqual(self.client.post(url, {'resolution': 'Repeat'}, format='json').status_code, 409)

    def test_task_stays_blocked_until_last_open_blocker_is_resolved(self):
        first = self.report().data['id']
        second = self.report().data['id']
        self.client.post(self.url(f'blockers/{first}/resolve/'), {'resolution': 'First dependency fixed.'}, format='json')
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'Blocked')
        self.client.post(self.url(f'blockers/{second}/resolve/'), {'resolution': 'Second dependency fixed.'}, format='json')
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'In progress')

    def test_blocker_owner_must_be_project_member(self):
        self.assertEqual(self.report(self.other_member.pk).status_code, 400)
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.report(self.manager_member.pk).status_code, 400)

    def test_done_task_cannot_receive_blocker(self):
        self.task.status = 'Done'
        self.task.save()
        self.assertEqual(self.report().status_code, 400)
        self.assertFalse(Blocker.objects.exists())

    def test_blocker_owner_can_resolve_after_task_reassignment(self):
        item = self.report().data['id']
        self.task.assignee = self.manager_member
        self.task.save()
        self.client.force_authenticate(self.developer)
        # The developer owns this blocker, so resolution is still authorized after reassignment.
        self.assertEqual(self.client.post(self.url(f'blockers/{item}/resolve/'), {'resolution': 'Dependency resolved.'}, format='json').status_code, 200)

    def test_unrelated_project_member_cannot_report_or_resolve(self):
        from django.contrib.auth.models import User
        from ..models import Membership, ProjectMembership
        item = self.report().data['id']
        user = User.objects.create_user('teammate', password='test-password-123')
        membership = Membership.objects.create(user=user, organization=self.org, role='Developer')
        ProjectMembership.objects.create(project=self.project, membership=membership)
        self.client.force_authenticate(user)
        self.assertEqual(self.report(membership.pk).status_code, 403)
        self.assertEqual(self.client.post(self.url(f'blockers/{item}/resolve/'), {'resolution': 'Unauthorized'}, format='json').status_code, 403)

    def test_blocker_and_status_roll_back_on_audit_failure(self):
        with patch('workspace.task_activity.AuditEvent.objects.create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.report()
        self.task.refresh_from_db()
        self.assertFalse(Blocker.objects.exists())
        self.assertEqual((self.task.status, self.task.version), ('To do', 1))

    def test_update_rolls_back_on_audit_failure(self):
        with patch('workspace.task_activity.AuditEvent.objects.create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url('updates/'), {'kind': 'Feedback', 'body': 'Review.'}, format='json')
        self.assertFalse(WorkUpdate.objects.exists())

    def test_invalid_blocker_id_and_unsupported_edits(self):
        self.assertEqual(self.client.post(self.url('blockers/nope/resolve/'), {'resolution': 'Fixed'}, format='json').status_code, 404)
        self.assertEqual(self.client.patch(self.url('updates/'), {'body': 'Rewrite'}, format='json').status_code, 405)
