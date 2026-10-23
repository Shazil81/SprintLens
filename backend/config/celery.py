"""Celery worker and beat share the Django configuration."""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('sprintlens')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
