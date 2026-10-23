"""End-to-end API regressions for editing, planning, reviews, growth, webhooks and jobs."""
import hashlib
import hmac
import json
from datetime import date, timedelta
from unittest.mock import patch
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from . import test_workspace as base
from ..github import webhook_secret
from ..models import (AuditEvent, Blocker, GitHubActivity, GitHubConnection, GitHubDelivery,
                     GoalEntry, GrowthGoal, Membership, Milestone, Notification, PerformanceReview,
                     ProjectMembership, ReviewResponse, Task, TaskDependency)
from ..tasks import generate_digests, generate_reminders


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class FeatureTests(TestCase):
    setUp = base.WorkspaceTests.setUp
    task_url = base.WorkspaceTests.task_url

    def owner(self):
        user = User.objects.create_user('owner')
        member = Membership.objects.create(user=user, organization=self.org, role='Admin')
        self.client.force_authenticate(user)
        return member

    def colleague(self):
        user = User.objects.create_user('colleague')
        member = Membership.objects.create(user=user, organization=self.org, role='Developer')
        ProjectMembership.objects.create(project=self.project, membership=member)
        return member

    def prerequisite(self):
        return Task.objects.create(project=self.project, assignee=self.dev_member, title='Prerequisite', due='2026-12-01')

    def plan(self, task, dependencies, milestone=None, version=1):
        return self.client.put(self.task_url(task) + 'planning/', {'dependency_ids': [str(t.pk) for t in dependencies], 'milestone': milestone, 'version': version}, format='json')

    def review_payload(self, **changes):
        return {'project': self.project.pk, 'subject': self.dev_member.pk, 'cycle': 'October', 'period_start': '2026-10-01', 'period_end': '2026-10-31', 'strengths': 'Reliable API delivery.', 'improvements': 'Add failure-path tests.', 'collaboration': 'Helped another developer.', 'delivery_context': 'Blocked by upstream credentials.', **changes}

    def review(self):
        result = self.client.post('/api/v1/reviews/', self.review_payload(), format='json')
        self.assertEqual(result.status_code, 201, result.data)
        return result.data

    def goal_payload(self, **changes):
        return {'project': self.project.pk, 'owner': self.dev_member.pk, 'title': 'Learn job retries', 'skill': 'Celery', 'target_date': '2026-12-15', **changes}

    def connection(self):
        return GitHubConnection.objects.create(project=self.project, repository='team/portal')

    def deliver(self, connection, payload=None, event='push', delivery='event-1', signature=True):
        payload = payload if payload is not None else {'repository': {'full_name': 'team/portal'}, 'sender': {'login': 'dev'}, 'commits': [{'id': 'abc123', 'message': f'CP-{str(self.task.pk)[:8].upper()} implement portal', 'url': 'https://github.com/team/portal/commit/abc123'}]}
        body = json.dumps(payload).encode()
        digest = 'sha256=' + hmac.new(webhook_secret(connection).encode(), body, hashlib.sha256).hexdigest() if signature else 'bad'
        return self.client.post(f'/api/v1/hooks/github/{connection.pk}/', body, content_type='application/json', HTTP_X_HUB_SIGNATURE_256=digest, HTTP_X_GITHUB_DELIVERY=delivery, HTTP_X_GITHUB_EVENT=event)

    def test_task_edit_reassignment_and_stale_version(self):
        result = self.client.patch(self.task_url(), {'title': 'Updated', 'assignee': self.manager_member.pk, 'priority': 'High', 'due': '2026-12-02', 'acceptance_criteria': 'Verified by tests.', 'version': 1}, format='json')
        self.assertEqual(result.status_code, 200, result.data)
        self.task.refresh_from_db()
        self.assertEqual((self.task.title, self.task.assignee_id, self.task.version), ('Updated', self.manager_member.pk, 2))
        self.assertEqual(self.client.patch(self.task_url(), {'title': 'Lost update', 'version': 1}, format='json').status_code, 409)
        self.assertEqual(AuditEvent.objects.get().before['assignee_id'], str(self.dev_member.pk))

    def test_task_edit_foreign_assignment_and_developer_denied(self):
        self.assertEqual(self.client.patch(self.task_url(), {'assignee': self.other_member.pk, 'version': 1}, format='json').status_code, 400)
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.patch(self.task_url(), {'title': 'Spoof', 'version': 1}, format='json').status_code, 403)

    def test_milestone_dates_scope_progress_and_edit(self):
        body = {'project': self.project.pk, 'title': 'Release 1', 'kind': 'Sprint', 'start': '2026-12-01', 'due': '2026-12-15'}
        result = self.client.post('/api/v1/milestones/', body, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        milestone = result.data['id']
        self.assertEqual(self.plan(self.task, [], milestone).status_code, 200)
        self.assertEqual(self.client.get(f'/api/v1/milestones/{milestone}/').data['total'], 1)
        self.assertEqual(self.client.patch(f'/api/v1/milestones/{milestone}/', {'title': 'New sprint', 'version': 1}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(f'/api/v1/milestones/{milestone}/', {'title': 'Stale', 'version': 1}, format='json').status_code, 409)
        for changes in [{'start': '2027-01-01'}, {'project': self.foreign.pk}]:
            self.assertEqual(self.client.post('/api/v1/milestones/', {**body, **changes}, format='json').status_code, 400)

    def test_dependency_cycle_self_foreign_and_stale_rejected(self):
        other = self.prerequisite()
        self.assertEqual(self.plan(self.task, [other]).status_code, 200)
        for target in [[self.task], [self.foreign_task]]:
            self.assertEqual(self.plan(other, target).status_code, 400)
        self.assertEqual(self.plan(self.task, [], version=1).status_code, 409)
        self.assertEqual(self.plan(other, [other]).status_code, 400)
        self.assertEqual(TaskDependency.objects.count(), 1)

    def test_dependency_gate_and_milestone_isolation(self):
        other = self.prerequisite()
        self.plan(self.task, [other])
        self.assertEqual(self.client.patch(self.task_url(), {'status': 'In progress', 'version': 2}, format='json').status_code, 400)
        other.status = 'Done'; other.save()
        self.assertEqual(self.client.patch(self.task_url(), {'status': 'In progress', 'version': 2}, format='json').status_code, 200)
        milestone = Milestone.objects.create(project=self.foreign, title='Foreign', start='2026-12-01', due='2026-12-02')
        self.assertEqual(self.plan(self.task, [], milestone.pk, 3).status_code, 404)

    def test_developer_cannot_plan_or_create_milestone(self):
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.plan(self.task, []).status_code, 403)
        self.assertEqual(self.client.post('/api/v1/milestones/', {'project': self.project.pk, 'title': 'No', 'start': '2026-12-01', 'due': '2026-12-02'}, format='json').status_code, 403)

    def test_new_dependency_on_started_task_rejected(self):
        self.task.status = 'In progress'; self.task.save()
        self.assertEqual(self.plan(self.task, [self.prerequisite()]).status_code, 400)

    def test_reopen_done_prerequisite_requires_reopening_dependents(self):
        other = self.prerequisite()
        other.status = 'Done'; other.save()
        self.task.status = 'Done'; self.task.save()
        self.plan(self.task, [other])
        self.assertEqual(self.client.patch(self.task_url(other), {'status': 'In progress', 'version': 1}, format='json').status_code, 400)

    def test_blocker_resolution_preserves_dependency_gate(self):
        self.plan(self.task, [self.prerequisite()])
        self.task.status = 'Blocked'; self.task.save()
        blocker = Blocker.objects.create(task=self.task, reporter=self.developer, owner=self.dev_member, reason='Wait')
        self.assertEqual(self.client.post(self.task_url() + f'blockers/{blocker.pk}/resolve/', {'resolution': 'Fixed local problem'}, format='json').status_code, 200)
        self.task.refresh_from_db(); self.assertEqual(self.task.status, 'Blocked')

    def test_review_draft_privacy_publish_and_subject_response(self):
        item = self.review(); url = f'/api/v1/reviews/{item["id"]}/'
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get('/api/v1/reviews/').data['count'], 0)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(url + 'publish/', {'version': 1}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'strengths': 'Overwrite', 'version': 2}, format='json').status_code, 403)
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get(url).status_code, 200)
        result = self.client.post(url + 'respond/', {'body': 'The dependency delayed delivery.'}, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data['status'], 'Responded')
        self.assertEqual(ReviewResponse.objects.get().author, self.developer)

    def test_review_admin_not_automatic_reviewer_and_self_review_denied(self):
        self.assertEqual(self.client.post('/api/v1/reviews/', self.review_payload(subject=self.manager_member.pk), format='json').status_code, 400)
        self.owner()
        self.assertEqual(self.client.post('/api/v1/reviews/', self.review_payload(), format='json').status_code, 403)

    def test_review_invalid_period_and_cross_workspace_subject(self):
        for changes in [{'period_end': '2026-09-01'}, {'subject': self.other_member.pk}, {'strengths': '  '}, {'reviewer': self.dev_member.pk}]:
            self.assertEqual(self.client.post('/api/v1/reviews/', self.review_payload(**changes), format='json').status_code, 400)

    def test_review_revocation_stale_version_and_private_audit(self):
        item = self.review(); url = f'/api/v1/reviews/{item["id"]}/'
        self.assertEqual(self.client.patch(url, {'cycle': 'Revised', 'version': 1}, format='json').status_code, 200)
        self.assertEqual(self.client.post(url + 'publish/', {'version': 1}, format='json').status_code, 409)
        ProjectMembership.objects.filter(project=self.project, membership=self.manager_member).update(is_reviewer=False)
        self.assertEqual(self.client.post(url + 'publish/', {'version': 2}, format='json').status_code, 403)
        self.assertNotIn('Reliable API delivery', json.dumps(list(AuditEvent.objects.values('before', 'after', 'text'))))

    def test_unrelated_member_cannot_read_review(self):
        colleague = self.colleague()
        item = self.review()
        self.client.post(f'/api/v1/reviews/{item["id"]}/publish/', {'version': 1}, format='json')
        self.client.force_authenticate(colleague.user)
        self.assertEqual(self.client.get(f'/api/v1/reviews/{item["id"]}/').status_code, 404)

    def test_goal_owner_progress_reviewer_feedback_and_stale_edit(self):
        self.client.force_authenticate(self.developer)
        result = self.client.post('/api/v1/goals/', self.goal_payload(), format='json')
        self.assertEqual(result.status_code, 201, result.data)
        url = f'/api/v1/goals/{result.data["id"]}/'
        self.assertEqual(self.client.post(url + 'entries/', {'body': 'Implemented retries.'}, format='json').status_code, 201)
        self.assertEqual(GoalEntry.objects.get().kind, 'Progress')
        self.assertEqual(self.client.patch(url, {'status': 'Achieved', 'version': 1}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'status': 'Planned', 'version': 1}, format='json').status_code, 409)
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.post(url + 'entries/', {'body': 'Good failure-path coverage.'}, format='json').status_code, 201)
        self.assertEqual(GoalEntry.objects.last().kind, 'Feedback')

    def test_growth_privacy_and_unassigned_admin(self):
        colleague = self.colleague()
        goal = GrowthGoal.objects.create(project=self.project, owner=self.dev_member, title='Private', skill='TS', target_date='2026-12-01')
        for user in [colleague.user, self.owner().user]:
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get(f'/api/v1/goals/{goal.pk}/').status_code, 404)
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.post('/api/v1/goals/', self.goal_payload(owner=colleague.pk), format='json').status_code, 403)

    def test_goal_audit_failure_rolls_back(self):
        with patch('workspace.development.AuditEvent.objects.create', side_effect=RuntimeError('unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.post('/api/v1/goals/', self.goal_payload(), format='json')
        self.assertFalse(GrowthGoal.objects.exists())

    def test_github_signature_dedup_and_task_linking(self):
        connection = self.connection()
        self.assertEqual(self.deliver(connection, signature=False).status_code, 403)
        self.assertFalse(GitHubActivity.objects.exists())
        self.assertEqual(self.deliver(connection).status_code, 200)
        self.assertEqual(self.deliver(connection).json(), {'duplicate': True})
        self.assertEqual(GitHubActivity.objects.get().task, self.task)
        self.assertEqual(GitHubDelivery.objects.count(), 1)

    def test_github_repository_spoof_and_unsafe_links(self):
        connection = self.connection()
        bad = {'repository': {'full_name': 'other/repo'}, 'commits': []}
        self.assertEqual(self.deliver(connection, bad).status_code, 400)
        body = {'repository': {'full_name': connection.repository}, 'sender': {'login': 'dev'}, 'commits': [{'message': 'No task reference', 'url': 'https://evil.example/'}]}
        self.assertEqual(self.deliver(connection, body).status_code, 200)
        item = GitHubActivity.objects.get(); self.assertEqual(item.url, ''); self.assertIsNone(item.task)

    def test_github_pr_review_and_disabled_connection(self):
        connection = self.connection()
        body = {'repository': {'full_name': connection.repository}, 'sender': {'login': 'reviewer'}, 'action': 'submitted', 'pull_request': {'number': 12, 'title': f'CP-{str(self.task.pk)[:8]} add API', 'body': '', 'html_url': 'https://github.com/team/portal/pull/12'}, 'review': {'id': 99, 'html_url': 'https://github.com/team/portal/pull/12#review-99'}}
        self.assertEqual(self.deliver(connection, body, event='pull_request_review').status_code, 200)
        self.assertEqual(GitHubActivity.objects.get().event, 'pull_request_review')
        connection.enabled = False; connection.save()
        self.assertEqual(self.deliver(connection, delivery='second').status_code, 410)

    def test_github_connection_admin_only_and_secret_not_in_lists(self):
        body = {'project': self.project.pk, 'repository': 'team/portal'}
        self.assertEqual(self.client.post('/api/v1/github-connections/', body, format='json').status_code, 403)
        self.owner()
        result = self.client.post('/api/v1/github-connections/', body, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        url = f'/api/v1/github-connections/{result.data["id"]}/setup/'
        self.assertIn('secret', self.client.get(url).data)
        self.assertNotIn('secret', str(self.client.get('/api/v1/github-connections/').data))
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_github_foreign_events_are_hidden(self):
        connection = GitHubConnection.objects.create(project=self.foreign, repository='foreign/repo')
        GitHubActivity.objects.create(connection=connection, event='push', title='Private', actor='other', external_id='1')
        self.assertEqual(self.client.get('/api/v1/github-activity/').data['count'], 0)

    def test_github_ping_confirms_delivery_without_inventing_code_activity(self):
        connection = self.connection()
        result = self.deliver(connection, {'repository': {'full_name': connection.repository}, 'zen': 'Testing webhook.'}, event='ping')
        self.assertEqual(result.status_code, 200)
        item = self.client.get('/api/v1/github-connections/').data['results'][0]
        self.assertEqual(item['event_count'], 0)
        self.assertEqual(item['delivery_count'], 1)
        self.assertIsNotNone(item['last_delivery_at'])

    def test_github_ambiguous_task_references_not_auto_linked(self):
        connection = self.connection(); other = self.prerequisite()
        payload = {'repository': {'full_name': connection.repository}, 'commits': [{'message': f'CP-{str(self.task.pk)[:8]} CP-{str(other.pk)[:8]}', 'url': ''}]}
        self.deliver(connection, payload)
        self.assertIsNone(GitHubActivity.objects.get().task)

    def test_github_non_ascii_signature_is_rejected(self):
        connection = self.connection()
        response = self.client.post(f'/api/v1/hooks/github/{connection.pk}/', b'{}', content_type='application/json', HTTP_X_HUB_SIGNATURE_256='sha256=\u00e9')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(GitHubDelivery.objects.exists())

    def test_planning_rolls_back_graph_and_version_if_audit_fails(self):
        other = self.prerequisite()
        with patch('workspace.planning.AuditEvent.objects.create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.plan(self.task, [other])
        self.task.refresh_from_db()
        self.assertEqual(self.task.version, 1)
        self.assertFalse(TaskDependency.objects.exists())

    def test_review_response_cannot_publish_or_mutate_manager_text(self):
        item = self.review(); url = f'/api/v1/reviews/{item["id"]}/'
        self.client.post(url + 'publish/', {'version': 1}, format='json')
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.post(url + 'publish/', {'version': 2}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(url, {'strengths': 'Tampered', 'version': 2}, format='json').status_code, 403)
        with patch('workspace.development.AuditEvent.objects.create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.post(url + 'respond/', {'body': 'Subject perspective'}, format='json')
        self.assertFalse(ReviewResponse.objects.exists())

    def test_notifications_are_idempotent_private_and_markable(self):
        with patch('workspace.tasks.timezone.localdate', return_value=date(2026, 12, 1)):
            self.assertEqual(generate_reminders(), 3)  # Includes the foreign task's own recipient.
            self.assertEqual(generate_reminders(), 0)
            self.assertEqual(generate_digests(), 1)
            self.assertEqual(generate_digests(), 0)
        self.client.force_authenticate(self.developer)
        result = self.client.get('/api/v1/notifications/').data
        self.assertEqual(result['count'], 1)
        own = result['results'][0]
        self.assertEqual(self.client.post(f'/api/v1/notifications/{own["id"]}/read/', {}, format='json').status_code, 200)
        foreign = Notification.objects.exclude(recipient=self.dev_member).first()
        self.assertEqual(self.client.post(f'/api/v1/notifications/{foreign.pk}/read/', {}, format='json').status_code, 404)

    def test_review_notification_only_after_publication(self):
        review = self.review()
        generate_reminders()
        self.assertFalse(Notification.objects.filter(kind='review').exists())
        self.client.post(f'/api/v1/reviews/{review["id"]}/publish/', {'version': 1}, format='json')
        generate_reminders()
        self.assertEqual(Notification.objects.get(kind='review').recipient, self.dev_member)

    def test_old_blocker_alert_owner_and_removed_access(self):
        blocker = Blocker.objects.create(task=self.task, reporter=self.developer, owner=self.dev_member, reason='Credentials')
        Blocker.objects.filter(pk=blocker.pk).update(opened_at=timezone.now() - timedelta(days=2))
        generate_reminders()
        self.assertEqual(Notification.objects.filter(kind='blocker').count(), 2)
        ProjectMembership.objects.filter(project=self.project, membership=self.dev_member).delete()
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get('/api/v1/notifications/').data['count'], 0)
