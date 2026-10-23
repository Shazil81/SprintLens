"""Production fail-fast configuration, reverse-proxy sessions, probes and first-owner bootstrap."""
import json
import logging
import os
from pathlib import Path
import subprocess
import sys
from io import StringIO
from unittest.mock import patch
from uuid import UUID
from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command, CommandError
from django.db import OperationalError
from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient
from config.environment import read_runtime, integer
from . import test_workspace as base
from ..middleware import ApiLogFormatter
from ..models import AuditEvent, Membership, Organization


class RuntimeTests(SimpleTestCase):
    def test_standard_runserver_uses_local_config_only_without_production_intent(self):
        from manage import use_local_runserver
        self.assertTrue(use_local_runserver(['runserver'],{},True))
        self.assertFalse(use_local_runserver(['runserver'],{},False))
        self.assertFalse(use_local_runserver(['migrate'],{},True))
        for environment in [{'RENDER':'true'}, {'DJANGO_DEBUG':'0'}, {'DJANGO_DEBUG':'false'},
                            {'DJANGO_SECRET_KEY':'explicit'}, {'DATABASE_URL':'explicit'},
                            {'DJANGO_SETTINGS_MODULE':'config.settings'}]:
            self.assertFalse(use_local_runserver(['runserver'],environment,True))

    def env(self, **changes):
        return {'DJANGO_SECRET_KEY':'test-only-strong-key-1234567890-abcdefghijklmnopqrstuvwxyz-ABCDEFG',
                'DJANGO_ALLOWED_HOSTS':'api.sprintlens.test',
                'DJANGO_CSRF_TRUSTED_ORIGINS':'https://app.sprintlens.test',
                'DATABASE_URL':'postgresql://test:private-value@db.sprintlens.test/sprintlens',
                'REDIS_URL':'redis://redis.sprintlens.test:6379/0', **changes}

    def test_production_requires_secret_exact_hosts_origins_postgres_and_redis(self):
        for key in ['DJANGO_SECRET_KEY','DJANGO_ALLOWED_HOSTS','DJANGO_CSRF_TRUSTED_ORIGINS','DATABASE_URL','REDIS_URL']:
            with self.subTest(key=key), self.assertRaises(ImproperlyConfigured):
                read_runtime(self.env(**{key:''}))
        self.assertFalse(read_runtime(self.env()).debug)

    def test_invalid_values_fail_without_credential_disclosure(self):
        for changes in [{'DJANGO_DEBUG':'sometimes'}, {'DJANGO_SECRET_KEY':'REPLACE_WITH_'+'abc'*30},
                        {'DJANGO_ALLOWED_HOSTS':'*'}, {'DJANGO_ALLOWED_HOSTS':'https://api.sprintlens.test'},
                        {'DJANGO_CSRF_TRUSTED_ORIGINS':'http://app.sprintlens.test'},
                        {'DJANGO_CSRF_TRUSTED_ORIGINS':'https://*.vercel.app'},
                        {'DJANGO_CSRF_TRUSTED_ORIGINS':'https://app.sprintlens.test/path'},
                        {'DATABASE_URL':'sqlite:///private-value'}, {'DATABASE_URL':'postgresql://test:private-value@host:invalid/db'},
                        {'REDIS_URL':'https://private-value.example.com'}]:
            with self.subTest(changes=changes), self.assertRaises(ImproperlyConfigured) as error:
                read_runtime(self.env(**changes))
            self.assertNotIn('private-value',str(error.exception))

    def test_render_host_is_added_but_render_debug_is_rejected(self):
        runtime = read_runtime(self.env(RENDER='true',RENDER_EXTERNAL_HOSTNAME='sprintlens-api.onrender.com'))
        self.assertIn('sprintlens-api.onrender.com',runtime.hosts)
        with self.assertRaises(ImproperlyConfigured):
            read_runtime(self.env(RENDER='true',DJANGO_DEBUG='1'))

    def test_local_defaults_and_numeric_limits(self):
        runtime = read_runtime({'DJANGO_DEBUG':'1'})
        self.assertTrue(runtime.debug)
        self.assertIn('127.0.0.1',runtime.hosts)
        self.assertNotIn('private-value',repr(read_runtime(self.env())))
        for value in ['abc','0','21']:
            with self.assertRaises(ImproperlyConfigured):
                integer({'AI_DAILY_LIMIT':value},'AI_DAILY_LIMIT',5,1,20)

    def test_local_launcher_refuses_render_before_loading_private_files(self):
        from local_environment import configure_environment
        with patch.dict(os.environ,{'RENDER':'true'}),patch('pathlib.Path.read_text') as read:
            with self.assertRaises(RuntimeError):
                configure_environment()
        read.assert_not_called()

    def test_real_production_settings_use_redis_secure_cookies_and_ssl(self):
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(('DJANGO_','DATABASE_','REDIS_','CACHE_','RENDER','GEMINI_','AI_')):
                env.pop(key)
        env.update(self.env(DJANGO_DEBUG='0'))
        env['DJANGO_SETTINGS_MODULE']='config.settings'
        script = '''
import json, django
django.setup()
from django.conf import settings
from django.core.checks import run_checks, ERROR
checks=run_checks(include_deployment_checks=True)
print(json.dumps({'debug':settings.DEBUG,'cache':settings.CACHES['default']['BACKEND'],
 'session_secure':settings.SESSION_COOKIE_SECURE,'session_httponly':settings.SESSION_COOKIE_HTTPONLY,
 'domain':settings.SESSION_COOKIE_DOMAIN,'csrf_secure':settings.CSRF_COOKIE_SECURE,
 'ssl':settings.DATABASES['default']['OPTIONS']['sslmode'],'forwarded_host':settings.USE_X_FORWARDED_HOST,
 'errors':[item.id for item in checks if item.level>=ERROR],
 'warnings':[item.id for item in checks if item.level<ERROR]}))
'''
        result = subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[2],
                                env=env,text=True,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr)
        values = json.loads(result.stdout)
        self.assertFalse(values['debug'])
        self.assertIn('redis.RedisCache',values['cache'])
        self.assertTrue(values['session_secure'] and values['csrf_secure'] and values['session_httponly'])
        self.assertIsNone(values['domain'])
        self.assertEqual(values['ssl'],'require')
        self.assertFalse(values['forwarded_host'])
        self.assertEqual(values['errors'],[])
        self.assertLessEqual(set(values['warnings']),{'security.W005','security.W021'})

    def test_log_formatter_excludes_message_and_sensitive_fields(self):
        record = logging.LogRecord('api',logging.INFO,'',0,'password=private-value',(),None)
        record.request_id='a'; record.method='POST'; record.route='api/v1/auth/login/'; record.status=400; record.duration_ms=2
        record.cookie='private-cookie'
        text = ApiLogFormatter().format(record)
        self.assertNotIn('private',text)
        self.assertEqual(json.loads(text)['status'],400)


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],DEBUG=False,
                   ALLOWED_HOSTS=['api.sprintlens.test'],CSRF_TRUSTED_ORIGINS=['https://app.sprintlens.test'],
                   SESSION_COOKIE_SECURE=True,CSRF_COOKIE_SECURE=True,SECURE_SSL_REDIRECT=True)
class ProxyAndHealthTests(TestCase):
    setUp = base.WorkspaceTests.setUp

    def test_session_and_csrf_login_through_https_proxy(self):
        client = APIClient(enforce_csrf_checks=True)
        # Other local Django projects must not overwrite this application's cookies.
        client.cookies['csrftoken'] = 'unrelated-project-token'
        client.cookies['sessionid'] = 'unrelated-project-session'
        headers = {'HTTP_HOST':'api.sprintlens.test','HTTP_X_FORWARDED_PROTO':'https','HTTP_ORIGIN':'https://app.sprintlens.test',
                   'HTTP_X_FORWARDED_HOST':'untrusted.example.com'}
        session = client.get('/api/v1/auth/session/',**headers)
        self.assertEqual(session.status_code,200)
        self.assertTrue(session.cookies['sprintlens_csrftoken']['secure'])
        self.assertEqual(session.cookies['sprintlens_csrftoken']['domain'],'')
        token = session.json()['csrfToken']
        credentials = {'username':'manager','password':'test-password-123'}
        response = client.post('/api/v1/auth/login/',credentials,format='json',HTTP_X_CSRFTOKEN=token,**headers)
        self.assertEqual(response.status_code,200,response.content)
        self.assertTrue(response.cookies['sprintlens_sessionid']['secure'])
        self.assertTrue(response.cookies['sprintlens_sessionid']['httponly'])
        self.assertEqual(response.cookies['sprintlens_sessionid']['samesite'],'Lax')
        self.assertEqual(response.cookies['sprintlens_sessionid']['domain'],'')
        self.assertIn('no-store',response['Cache-Control'])
        self.assertNotEqual(response['X-Request-ID'],'spoofed')
        UUID(response['X-Request-ID'])
        headers['HTTP_ORIGIN']='https://attacker.example.com'
        response = client.post('/api/v1/auth/logout/',{},format='json',HTTP_X_CSRFTOKEN=response.json()['csrfToken'],**headers)
        self.assertEqual(response.status_code,403)

    def test_http_redirects_api_but_not_probes_and_404_is_json(self):
        self.assertEqual(self.client.get('/api/v1/auth/session/',HTTP_HOST='api.sprintlens.test').status_code,301)
        self.assertEqual(self.client.get('/health/live/',HTTP_HOST='api.sprintlens.test').json(),{'status':'ok'})
        response = self.client.get('/api/v1/missing-endpoint/',HTTP_HOST='api.sprintlens.test',HTTP_X_FORWARDED_PROTO='https')
        self.assertEqual(response.status_code,404)
        self.assertEqual(response.json(),{'detail':'Endpoint not found.'})
        self.assertEqual(response['Vercel-CDN-Cache-Control'],'no-store')

    def test_readiness_queries_database_and_cache_and_returns_no_secrets(self):
        response = self.client.get('/health/ready/',HTTP_HOST='api.sprintlens.test')
        self.assertEqual(response.status_code,200)
        with patch('workspace.health.cache.get',side_effect=ConnectionError('redis://secret-password@host')):
            response = self.client.get('/health/ready/',HTTP_HOST='api.sprintlens.test')
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json(),{'status':'unavailable'})
        self.assertNotIn('secret',response.content.decode())
        with patch('workspace.health.connection.cursor',side_effect=OperationalError('private-database-url')):
            response = self.client.get('/health/ready/',HTTP_HOST='api.sprintlens.test')
        self.assertEqual(response.status_code,503)
        self.assertNotIn('private',response.content.decode())


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class BootstrapTests(TestCase):
    def create(self, **kwargs):
        return call_command('bootstrap_workspace',organization_name='Real team',organization_slug='real-team',username='owner',**kwargs)

    def test_hidden_password_creates_workspace_admin_without_django_admin_or_demo_data(self):
        output=StringIO()
        with patch('workspace.management.commands.bootstrap_workspace.getpass.getpass',return_value='a-strong-private-test-password-184'):
            self.create(stdout=output)
        member=Membership.objects.get(role='Admin')
        self.assertFalse(member.user.is_superuser)
        self.assertTrue(member.user.check_password('a-strong-private-test-password-184'))
        self.assertEqual(member.organization.slug,'real-team')
        self.assertNotIn('private-test',output.getvalue())
        self.assertEqual(member.organization.project_set.count(),0)
        with patch('workspace.management.commands.bootstrap_workspace.getpass.getpass') as prompt:
            with self.assertRaises(CommandError):
                self.create()
        prompt.assert_not_called()

    def test_mismatch_and_audit_failure_leave_no_workspace(self):
        with patch('workspace.management.commands.bootstrap_workspace.getpass.getpass',side_effect=['first','second']):
            with self.assertRaises(CommandError):
                self.create()
        self.assertFalse(Organization.objects.exists())
        with patch('workspace.management.commands.bootstrap_workspace.getpass.getpass',return_value='a-strong-private-test-password-184'),patch('workspace.management.commands.bootstrap_workspace.AuditEvent.objects.create',side_effect=RuntimeError('audit offline')):
            with self.assertRaises(RuntimeError):
                self.create()
        self.assertFalse(Organization.objects.exists())
        self.assertFalse(Membership.objects.exists())
