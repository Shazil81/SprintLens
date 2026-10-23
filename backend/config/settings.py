import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from .environment import read_runtime, boolean, integer

BASE_DIR = Path(__file__).resolve().parent.parent
runtime = read_runtime(os.environ)
DEBUG = runtime.debug
SECRET_KEY = runtime.secret
ALLOWED_HOSTS = runtime.hosts
CSRF_TRUSTED_ORIGINS = runtime.origins
INSTALLED_APPS = [
    'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
    'rest_framework', 'workspace',
]
MIDDLEWARE = [
    # This API-only service does not serve frontend assets or Django templates.
    'django.middleware.security.SecurityMiddleware',
    'workspace.middleware.ApiResponseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF = 'config.urls'
WSGI_APPLICATION = 'config.wsgi.application'
database_url = runtime.database_url
if database_url:
    DATABASES = {'default': dj_database_url.parse(database_url,
        conn_max_age=integer(os.environ, 'DATABASE_CONN_MAX_AGE', 60, 0, 600), conn_health_checks=True,
        ssl_require=boolean(os.environ, 'DATABASE_SSL_REQUIRE', not DEBUG))}
    if not DEBUG:
        DATABASES['default'].setdefault('OPTIONS', {}).update(connect_timeout=2, options='-c statement_timeout=15000')
elif DEBUG:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
else:
    raise ImproperlyConfigured('DATABASE_URL is required in production.')
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.SessionAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_RENDERER_CLASSES': ['rest_framework.renderers.JSONRenderer'],
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.UserRateThrottle', 'rest_framework.throttling.AnonRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'user': '300/minute', 'anon': '30/minute'},
    # Account throttles use user IDs; anonymous requests never trust arbitrary forwarded IPs.
    'NUM_PROXIES': 0,
}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache', 'LOCATION': 'sprintlens-local'}} if DEBUG else {
    'default': {'BACKEND': 'django.core.cache.backends.redis.RedisCache', 'LOCATION': runtime.cache_url,
                'KEY_PREFIX': 'sprintlens', 'TIMEOUT': 300,
                'OPTIONS': {'socket_connect_timeout': 1, 'socket_timeout': 1}}}
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_COOKIE_HTTPONLY = True
# Isolate this workspace from other Django applications on the same local host.
SESSION_COOKIE_NAME = 'sprintlens_sessionid'
CSRF_COOKIE_NAME = 'sprintlens_csrftoken'
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_DOMAIN = None
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_DOMAIN = None
CSRF_COOKIE_HTTPONLY = False
CSRF_FAILURE_VIEW = 'workspace.auth.csrf_failure'
SESSION_COOKIE_AGE = 60 * 60 * 8
SECURE_SSL_REDIRECT = not DEBUG
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = False
SECURE_HSTS_SECONDS = integer(os.environ, 'DJANGO_HSTS_SECONDS', 3600, 0, 31536000) if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_REDIRECT_EXEMPT = [r'^health/(live|ready)/$']
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024

# Redis is a broker for background work; PostgreSQL remains the durable data store.
CELERY_BROKER_URL = runtime.redis_url
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_DEFAULT_QUEUE = 'sprintlens'
# Isolate broker bookkeeping as well as queues when Redis is shared.
CELERY_BROKER_TRANSPORT_OPTIONS = {'global_keyprefix': 'sprintlens:broker:'}
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_SOFT_TIME_LIMIT = 240
CELERY_TASK_TIME_LIMIT = 300
CELERY_BEAT_SCHEDULE = {
    'workspace-reminders': {'task': 'workspace.tasks.generate_reminders', 'schedule': 300.0, 'options': {'expires': 300}},
    'daily-team-digest': {'task': 'workspace.tasks.generate_digests', 'schedule': 3600.0, 'options': {'expires': 3600}},
}

# Gemini generation stays disabled until explicitly configured on the backend.
AI_INSIGHTS_ENABLED = boolean(os.environ, 'AI_INSIGHTS_ENABLED')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')
AI_DAILY_LIMIT = integer(os.environ, 'AI_DAILY_LIMIT', 5, 1, 20)
if not DEBUG and AI_INSIGHTS_ENABLED and not GEMINI_API_KEY:
    raise ImproperlyConfigured('GEMINI_API_KEY is required when AI_INSIGHTS_ENABLED is enabled.')

# API request logs contain fixed fields, never bodies, cookies, query strings or provider keys.
LOGGING = {
    'version': 1, 'disable_existing_loggers': False,
    'formatters': {'api_json': {'()': 'workspace.middleware.ApiLogFormatter'}},
    'handlers': {'api_console': {'class': 'logging.StreamHandler', 'formatter': 'api_json'}},
    'loggers': {'sprintlens.api': {'handlers': ['api_console'], 'level': 'WARNING' if DEBUG else 'INFO', 'propagate': False}},
}
