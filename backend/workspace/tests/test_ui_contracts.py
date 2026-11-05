"""UI summaries and filters must retain project permissions and truthful counts."""
from django.test import TestCase
from .test_workspace import WorkspaceTests
from ..models import Task


class UIContractTests(TestCase):
    setUp = WorkspaceTests.setUp

    def test_portal_mismatch_does_not_create_a_session(self):
        self.client.force_authenticate(None)
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'developer', 'password': 'test-password-123', 'portal': 'Manager',
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIsNone(self.client.get('/api/v1/auth/session/').json()['user'])
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'developer', 'password': 'test-password-123', 'portal': 'Developer',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['role'], 'Developer')

    def test_admin_can_use_manager_portal(self):
        self.manager_member.role = 'Admin'
        self.manager_member.save()
        self.client.force_authenticate(None)
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'manager', 'password': 'test-password-123', 'portal': 'Manager',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['role'], 'Admin')

    def test_invalid_portal_rejected(self):
        self.client.force_authenticate(None)
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'manager', 'password': 'test-password-123', 'portal': ['Admin'],
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_project_counts_include_teammates_for_developer(self):
        Task.objects.create(project=self.project, assignee=self.manager_member,
                            title='Accepted work', due='2026-12-01', status='Done')
        self.client.force_authenticate(self.developer)
        project = self.client.get('/api/v1/projects/').data['results'][0]
        self.assertEqual((project['task_total'], project['task_completed'], project['task_blocked']), (2, 1, 0))

    def test_member_counts_exclude_inaccessible_projects(self):
        Task.objects.create(project=self.private, assignee=self.dev_member,
                            title='Hidden task', due='2026-12-01', status='Blocked')
        members = self.client.get('/api/v1/members/').data['results']
        developer = next(member for member in members if member['id'] == self.dev_member.id)
        self.assertEqual((developer['task_open'], developer['task_blocked']), (1, 0))

    def test_task_filters_remain_scoped_and_paginated(self):
        Task.objects.create(project=self.project, assignee=self.manager_member,
                            title='Another task', due='2026-12-02')
        self.client.force_authenticate(self.developer)
        own = self.client.get('/api/v1/tasks/', {'mine': '1', 'page_size': 1}).data
        self.assertEqual(own['count'], 1)
        self.assertEqual(own['results'][0]['id'], str(self.task.id))
        page = self.client.get('/api/v1/tasks/', {'page_size': 1}).data
        self.assertEqual(page['count'], 2)
        self.assertIsNotNone(page['next'])
        self.assertEqual(self.client.get('/api/v1/tasks/', {'project': self.foreign.id}).data['count'], 0)
        self.assertEqual(self.client.get('/api/v1/tasks/', {'search': 'Build portal'}).data['count'], 1)
        code = f'CP-{str(self.task.id)[:8].upper()}'
        self.assertEqual(self.client.get('/api/v1/tasks/', {'search': code}).data['count'], 1)
        self.assertEqual(self.client.get('/api/v1/tasks/', {'due': '2026-12-02'}).data['count'], 1)
        self.assertEqual(self.client.get('/api/v1/tasks/', {'project': 'invalid'}).status_code, 400)
        self.assertEqual(self.client.get('/api/v1/tasks/', {'due': 'invalid'}).status_code, 400)
