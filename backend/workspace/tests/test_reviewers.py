"""Project reviewer authorization is enforced by the API, independently of the UI."""
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from . import test_workspace as base
from ..models import AuditEvent, Membership, ProjectMembership, WorkUpdate


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ReviewerTests(TestCase):
    setUp = base.WorkspaceTests.setUp
    task_url = base.WorkspaceTests.task_url

    def owner(self):
        user = User.objects.create_user('owner')
        member = Membership.objects.create(user=user, organization=self.org, role='Admin')
        self.client.force_authenticate(user)
        return member

    def feedback(self):
        return self.client.post(self.task_url() + 'updates/', {'kind': 'Feedback', 'body': 'Add regression coverage.'}, format='json')

    def roster(self, ids, reviewers, version=1):
        return self.client.put(f'/api/v1/projects/{self.project.pk}/members/', {'member_ids': ids, 'reviewer_ids': reviewers, 'version': version}, format='json')

    def test_admin_requires_explicit_project_assignment(self):
        member = self.owner()
        self.assertEqual(self.feedback().status_code, 403)
        ProjectMembership.objects.create(project=self.project, membership=member, is_reviewer=True)
        self.assertEqual(self.feedback().status_code, 201)

    def test_unassigned_manager_cannot_feedback_or_self_authorize(self):
        ProjectMembership.objects.filter(project=self.project, membership=self.manager_member).update(is_reviewer=False)
        self.assertEqual(self.feedback().status_code, 403)
        self.assertEqual(self.roster([self.manager_member.pk, self.dev_member.pk], [self.manager_member.pk]).status_code, 403)
        self.assertFalse(WorkUpdate.objects.exists())

    def test_admin_assign_revoke_version_and_audit(self):
        self.owner()
        ids = [self.manager_member.pk, self.dev_member.pk]
        result = self.roster(ids, [])
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['reviewer_ids'], [])
        self.assertEqual(result.data['version'], 2)
        self.assertEqual(AuditEvent.objects.get().before['reviewer_ids'], [self.manager_member.pk])
        self.assertEqual(self.roster(ids, [self.manager_member.pk]).status_code, 409)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.feedback().status_code, 403)
        self.owner_user = Membership.objects.get(user__username='owner').user
        self.client.force_authenticate(self.owner_user)
        self.assertEqual(self.roster(ids, [self.manager_member.pk], 2).status_code, 200)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.feedback().status_code, 201)

    def test_developer_foreign_and_nonmember_reviewers_rejected(self):
        self.owner()
        ids = [self.manager_member.pk, self.dev_member.pk]
        for reviewers in [[self.dev_member.pk], [self.other_member.pk], [True], 'invalid']:
            self.assertEqual(self.roster(ids, reviewers).status_code, 400)
        self.assertFalse(AuditEvent.objects.exists())

    def test_workspace_demotion_blocks_existing_reviewer(self):
        self.manager_member.role = 'Developer'
        self.manager_member.save()
        self.assertEqual(self.feedback().status_code, 403)
        project = self.client.get(f'/api/v1/projects/{self.project.pk}/').data
        self.assertEqual(project['reviewer_ids'], [])
