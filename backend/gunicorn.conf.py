"""Linux production server configuration; Django's local runserver remains separate."""
import os

bind = f"0.0.0.0:{int(os.getenv('PORT','8000'))}"
workers = int(os.getenv('WEB_CONCURRENCY','2'))
worker_class = 'gthread'
threads = int(os.getenv('GUNICORN_THREADS','2'))
timeout = 60
graceful_timeout = 45
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = '-'
errorlog = '-'
# U omits the query string; authorization headers and cookies are never logged here.
access_log_format = '%(m)s %(U)s %(s)s %(L)s'
capture_output = False
