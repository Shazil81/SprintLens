from django.urls import include, path
from rest_framework.routers import DefaultRouter
from workspace import auth, views
from workspace.planning import MilestoneViewSet
from workspace.development import ReviewViewSet, GoalViewSet
from workspace.github import ConnectionViewSet, ActivityViewSet, github_webhook
from workspace.notifications import NotificationViewSet
from workspace.analytics import analytics
from workspace.knowledge import KnowledgeViewSet
from workspace.reports import ReportViewSet
from workspace.insights import InsightViewSet
from workspace import health

handler400 = 'workspace.errors.bad_request'
handler403 = 'workspace.errors.forbidden'
handler404 = 'workspace.errors.not_found'
handler500 = 'workspace.errors.server_error'

router = DefaultRouter()
router.register('projects', views.ProjectViewSet, basename='project')
router.register('members', views.MemberViewSet, basename='member')
router.register('tasks', views.TaskViewSet, basename='task')
router.register('audit-events', views.AuditViewSet, basename='audit')
router.register('milestones', MilestoneViewSet, basename='milestone')
router.register('reviews', ReviewViewSet, basename='review')
router.register('goals', GoalViewSet, basename='goal')
router.register('github-connections', ConnectionViewSet, basename='github-connection')
router.register('github-activity', ActivityViewSet, basename='github-activity')
router.register('notifications', NotificationViewSet, basename='notification')
router.register('knowledge', KnowledgeViewSet, basename='knowledge')
router.register('reports', ReportViewSet, basename='report')
router.register('insights', InsightViewSet, basename='insight')
urlpatterns = [
    path('health/live/', health.live),
    path('health/ready/', health.ready),
    path('api/v1/hooks/github/<uuid:connection_id>/', github_webhook),
    path('api/v1/auth/session/', auth.session),
    path('api/v1/auth/login/', auth.sign_in),
    path('api/v1/auth/logout/', auth.sign_out),
    path('api/v1/me/', views.me),
    path('api/v1/dashboard/', views.dashboard),
    path('api/v1/analytics/', analytics),
    path('api/v1/', include(router.urls)),
]
