"""Verify analytics context, private evidence reviews and revisioned knowledge sharing."""
from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone
from . import test_workspace as base
from ..analytics import overlap_hours
from ..models import (ArticleRevision, AuditEvent, Blocker, KnowledgeArticle,
                     Membership, PerformanceReview, ProjectMembership, ReviewAssessment,
                     Task, TaskDependency, WorkUpdate)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class InsightTests(TestCase):
    setUp = base.WorkspaceTests.setUp
    task_url = base.WorkspaceTests.task_url

    def analytics(self, query=''):
        response = self.client.get('/api/v1/analytics/' + query)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def event(self, before, after, at):
        event = AuditEvent.objects.create(project=self.project, task=self.task, actor=self.manager,
                                         action='task.updated', before=before, after=after)
        AuditEvent.objects.filter(pk=event.pk).update(at=at)

    def test_scope_and_invalid_filters(self):
        data = self.analytics()
        self.assertEqual(data['snapshot']['tasks'], 1)
        self.assertEqual(len(data['trend']), 30)
        self.assertEqual(self.client.get(f'/api/v1/analytics/?project={self.foreign.pk}').status_code, 404)
        self.assertEqual(self.client.get('/api/v1/analytics/?days=8').status_code, 400)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/v1/analytics/').status_code, 403)

    def test_unknown_history_is_not_estimated(self):
        self.task.status = 'Done'
        self.task.save()
        data = self.analytics()
        self.assertEqual(data['snapshot']['done'], 1)
        self.assertEqual(data['delivery']['completion_events'], 0)
        self.assertIsNone(data['delivery']['median_start_to_accept_hours'])

    def test_observed_delivery_and_recompletion(self):
        now = timezone.now()
        self.event({'status': 'To do'}, {'status': 'In progress'}, now - timedelta(hours=25))
        self.event({'status': 'In review'}, {'status': 'Done'}, now - timedelta(hours=1))
        data = self.analytics()
        self.assertEqual(data['delivery']['median_start_to_accept_hours'], 24)
        self.event({'status': 'In review'}, {'status': 'Done'}, now)
        data = self.analytics()
        self.assertEqual(data['delivery']['completion_events'], 2)
        self.assertEqual(data['delivery']['unique_completed_tasks'], 1)

    def test_rules_cover_delays_dependencies_and_stale_updates(self):
        now = timezone.now()
        self.task.due = timezone.localdate() - timedelta(days=1)
        self.task.status = 'Blocked'
        self.task.save()
        Task.objects.filter(pk=self.task.pk).update(updated_at=now - timedelta(days=8))
        prerequisite = Task.objects.create(project=self.project, assignee=self.dev_member, title='Dependency', due=timezone.localdate())
        TaskDependency.objects.create(task=self.task, depends_on=prerequisite)
        blocker = Blocker.objects.create(task=self.task, reporter=self.developer, owner=self.manager_member, reason='Awaiting access')
        Blocker.objects.filter(pk=blocker.pk).update(opened_at=now - timedelta(days=4))
        for i in range(2):
            self.event({'due': '2026-01-01', 'status': 'In progress'}, {'due': '2026-01-02', 'status': 'Blocked'}, now - timedelta(minutes=i))
        risk = next(r for r in self.analytics()['risks'] if r['task_id'] == str(self.task.pk))
        self.assertEqual(risk['severity'], 'High')
        self.assertEqual(len(risk['signals']), 7)

    def test_project_deadline_is_an_independent_risk(self):
        self.project.due = timezone.localdate() - timedelta(days=1)
        self.project.save()
        row = self.analytics()['projects'][0]
        self.assertTrue(row['past_deadline'])
        self.assertEqual(row['status'], 'Needs attention')

    def test_developer_workload_does_not_list_peers(self):
        Task.objects.create(project=self.project, assignee=self.manager_member, title='Peer task', due=timezone.localdate())
        self.client.force_authenticate(self.developer)
        data = self.analytics()
        self.assertEqual([p['member_id'] for p in data['workload']], [self.dev_member.pk])
        self.assertNotIn('reviews', data)

    def test_blocker_union_and_repeated_exact_reason(self):
        now = timezone.now()
        self.assertEqual(overlap_hours([(now-timedelta(hours=4), now-timedelta(hours=1)),
                                        (now-timedelta(hours=2), None)], now-timedelta(hours=3), now), 3)
        second = Task.objects.create(project=self.project, assignee=self.dev_member, title='Second', due=timezone.localdate())
        for task, reason in [(self.task, 'Waiting   for API'), (second, 'waiting for api')]:
            Blocker.objects.create(task=task, reporter=self.developer, owner=self.manager_member, reason=reason)
        self.assertEqual(self.analytics()['recurring_blockers'][0]['task_count'], 2)

    def review(self):
        return PerformanceReview.objects.create(project=self.project, subject=self.dev_member, reviewer=self.manager_member,
            cycle='Evidence cycle', period_start=timezone.localdate()-timedelta(days=30), period_end=timezone.localdate(),
            strengths='Careful validation', improvements='Document context', collaboration='Reviewed together', delivery_context='Dependency wait')

    def rubric(self, version=1, **changes):
        return {'version': version, 'supporting_task_ids': [str(self.task.pk)],
                'quality_rating': 'Meets expectations', 'quality_evidence': 'Acceptance criteria verified in linked task.',
                'delivery_rating': 'Not assessed', 'delivery_evidence': '',
                'collaboration_rating': 'Not assessed', 'collaboration_evidence': '',
                'complexity_context': 'Unestimated; discuss scope before judging.',
                'blockers_context': 'External dependency considered.', **changes}

    def assess(self, review, **changes):
        return self.client.put(f'/api/v1/reviews/{review.pk}/assessment/', self.rubric(**changes), format='json')

    def test_complexity_requires_context_and_cannot_be_changed_by_developer(self):
        response = self.client.patch(self.task_url(), {'complexity':'Large', 'version':1}, format='json')
        self.assertEqual(response.status_code, 400)
        response = self.client.patch(self.task_url(), {'complexity':'Large', 'complexity_context':'New integration with unknown constraints', 'version':1}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(AuditEvent.objects.latest('at').after['complexity'], 'Large')
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.patch(self.task_url(), {'complexity':'Small', 'version':2}, format='json').status_code, 403)

    def test_assessment_needs_evidence_and_rejects_scores_and_foreign_tasks(self):
        review = self.review()
        self.assertEqual(self.assess(review, quality_evidence='').status_code, 400)
        self.assertEqual(self.assess(review, overall_score=100).status_code, 400)
        self.assertEqual(self.assess(review, supporting_task_ids=[str(self.foreign_task.pk)]).status_code, 400)
        self.assertFalse(ReviewAssessment.objects.exists())

    def test_assessment_is_versioned_and_draft_private(self):
        review = self.review()
        response = self.assess(review)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['version'], 2)
        self.assertEqual(self.assess(review).status_code, 409)
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get(f'/api/v1/reviews/{review.pk}/').status_code, 404)

    def test_published_snapshot_is_frozen_and_subject_can_respond(self):
        review = self.review()
        self.assertEqual(self.assess(review).status_code, 200)
        url = f'/api/v1/reviews/{review.pk}/'
        self.assertEqual(self.client.post(url+'publish/', {'version':2}, format='json').status_code, 200)
        Task.objects.filter(pk=self.task.pk).update(title='Changed later')
        self.assertEqual(self.assess(review, version=3).status_code, 403)
        self.client.force_authenticate(self.developer)
        response = self.client.get(url)
        self.assertEqual(response.data['assessment']['evidence_snapshot']['tasks'][0]['title'], 'Build portal')
        self.assertEqual(self.client.post(url+'respond/', {'body':'Here is my context.'}, format='json').status_code, 201)
        self.assertEqual(self.assess(review, version=4).status_code, 403)

    def test_changed_period_requires_fresh_snapshot(self):
        review = self.review()
        self.assertEqual(self.assess(review).status_code, 200)
        url = f'/api/v1/reviews/{review.pk}/'
        changed = self.client.patch(url, {'period_start':str(timezone.localdate()-timedelta(days=10)), 'version':2}, format='json')
        self.assertEqual(changed.status_code, 200, changed.data)
        self.assertEqual(self.client.post(url+'publish/', {'version':3}, format='json').status_code, 400)
        self.assertEqual(self.assess(review, version=3).status_code, 200)
        self.assertEqual(self.client.post(url+'publish/', {'version':4}, format='json').status_code, 200)

    def test_review_role_revocation_prevents_assessment(self):
        review = self.review()
        ProjectMembership.objects.filter(project=self.project, membership=self.manager_member).update(is_reviewer=False)
        self.assertEqual(self.assess(review).status_code, 403)

    def test_assessment_rollback_if_audit_fails(self):
        review = self.review()
        with patch('workspace.development.AuditEvent.objects.create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.assess(review)
        review.refresh_from_db()
        self.assertEqual(review.version, 1)
        self.assertFalse(ReviewAssessment.objects.exists())

    def test_evidence_links_use_period_and_not_other_tasks(self):
        review = self.review()
        WorkUpdate.objects.create(task=self.task, author=self.developer, body='Proof', evidence_url='https://example.com/proof')
        WorkUpdate.objects.create(task=self.foreign_task, author=self.other, body='Other', evidence_url='https://example.com/private')
        response = self.assess(review)
        self.assertEqual(response.status_code, 200, response.data)
        links = response.data['assessment']['evidence_snapshot']['tasks'][0]['links']
        self.assertEqual([link['url'] for link in links], ['https://example.com/proof'])

    def article(self, **changes):
        return self.client.post('/api/v1/knowledge/', {'project':self.project.pk, 'title':'Reusable solution',
            'summary':'How we solved it', 'content':'Private draft context', 'tags':['Django', 'django'], **changes}, format='json')

    def test_knowledge_draft_private_and_body_not_in_list_or_audit(self):
        response = self.article()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['tags'], ['django'])
        self.assertNotIn('content', self.client.get('/api/v1/knowledge/').data['results'][0])
        event = AuditEvent.objects.get(action='knowledge.created')
        self.assertNotIn('Reusable solution', event.text)
        self.assertNotIn('Private draft context', str(event.after))
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get(f"/api/v1/knowledge/{response.data['id']}/").status_code, 404)
        self.assertEqual(self.client.get('/api/v1/knowledge/').data['count'], 0)

    def test_published_search_and_revision_privacy(self):
        article = self.article().data
        url = f"/api/v1/knowledge/{article['id']}/"
        saved = self.client.patch(url, {'status':'Published', 'content':'Public answer with unique-search-term', 'version':1}, format='json')
        self.assertEqual(saved.status_code, 200, saved.data)
        self.assertEqual(self.client.get(url+'history/').data['count'], 2)
        self.client.force_authenticate(self.developer)
        results = self.client.get('/api/v1/knowledge/?search=unique-search-term&tag=django').data['results']
        self.assertEqual(len(results), 1)
        revisions = self.client.get(url+'history/').data['results']
        self.assertEqual([r['version'] for r in revisions], [2])
        self.assertEqual(self.client.patch(url, {'content':'overwrite', 'version':2}, format='json').status_code, 403)

    def test_curator_can_edit_published_but_cannot_see_author_draft_revisions(self):
        self.client.force_authenticate(self.developer)
        article = self.article().data
        url = f"/api/v1/knowledge/{article['id']}/"
        self.client.patch(url, {'status':'Published', 'version':1}, format='json')
        self.client.force_authenticate(self.manager)
        self.assertEqual(self.client.get(url+'history/').data['count'], 1)
        response = self.client.patch(url, {'summary':'Curated solution', 'version':2}, format='json')
        self.assertEqual(response.status_code, 200, response.data)

    def test_conflict_archive_history_and_no_delete(self):
        article = self.article(status='Published').data
        url = f"/api/v1/knowledge/{article['id']}/"
        self.assertEqual(self.client.patch(url, {'status':'Archived', 'version':1}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(url, {'summary':'Stale', 'version':1}, format='json').status_code, 409)
        self.assertEqual(self.client.get('/api/v1/knowledge/').data['count'], 0)
        self.assertEqual(self.client.get('/api/v1/knowledge/?status=Archived').data['count'], 1)
        self.assertEqual(self.client.get(url+'history/').data['count'], 2)
        self.assertEqual(self.client.delete(url).status_code, 405)

    def test_cross_project_creation_and_client_owned_fields_rejected(self):
        self.assertEqual(self.article(project=self.foreign.pk).status_code, 400)
        self.assertEqual(self.article(author=self.dev_member.pk).status_code, 400)
        self.assertEqual(self.article(version=20).status_code, 400)
        self.assertEqual(self.article(status='Archived').status_code, 400)
        self.assertFalse(KnowledgeArticle.objects.exists())

    def test_knowledge_audit_failure_rolls_back_article_and_revision(self):
        with patch('workspace.knowledge.AuditEvent.objects.create', side_effect=RuntimeError('audit unavailable')):
            with self.assertRaises(RuntimeError):
                self.article()
        self.assertFalse(KnowledgeArticle.objects.exists())
        self.assertFalse(ArticleRevision.objects.exists())

    def test_removed_member_cannot_read_published_article(self):
        article = self.article(status='Published').data
        ProjectMembership.objects.filter(project=self.project, membership=self.dev_member).delete()
        self.client.force_authenticate(self.developer)
        self.assertEqual(self.client.get(f"/api/v1/knowledge/{article['id']}/").status_code, 404)
