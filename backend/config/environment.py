"""Validate runtime configuration without loading local files or revealing secret values."""
from dataclasses import dataclass, field
import re
from urllib.parse import urlsplit
from django.core.exceptions import ImproperlyConfigured


def boolean(env, name, default=False):
    value = env.get(name, '1' if default else '0').strip().lower()
    if value not in {'0', '1', 'false', 'true'}:
        raise ImproperlyConfigured(f'{name} must be 0 or 1.')
    return value in {'1', 'true'}


def integer(env, name, default, minimum, maximum):
    try:
        value = int(env.get(name, str(default)))
    except (TypeError, ValueError):
        raise ImproperlyConfigured(f'{name} must be an integer.') from None
    if not minimum <= value <= maximum:
        raise ImproperlyConfigured(f'{name} must be between {minimum} and {maximum}.')
    return value


def csv_values(value):
    return list(dict.fromkeys(part.strip() for part in value.split(',') if part.strip()))


def service_url(value, name, schemes):
    try:
        parsed = urlsplit(value)
        valid = parsed.scheme in schemes and parsed.hostname and parsed.port != 0
    except ValueError:
        valid = False
    if not valid:
        raise ImproperlyConfigured(f'{name} must be a valid service URL with an allowed scheme.')


@dataclass(frozen=True)
class Runtime:
    debug: bool
    secret: str = field(repr=False)
    hosts: list[str]
    origins: list[str]
    database_url: str = field(repr=False)
    redis_url: str = field(repr=False)
    cache_url: str = field(repr=False)


def read_runtime(env):
    debug = boolean(env, 'DJANGO_DEBUG')
    if env.get('RENDER') and debug:
        raise ImproperlyConfigured('DJANGO_DEBUG must be disabled on Render. Use manage.py, not local.py.')
    secret = env.get('DJANGO_SECRET_KEY', '')
    database = env.get('DATABASE_URL', '')
    redis = env.get('REDIS_URL', 'redis://127.0.0.1:6379/0' if debug else '')
    cache = env.get('CACHE_URL', redis)
    hosts = csv_values(env.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1' if debug else ''))
    render_host = env.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
    if render_host and render_host not in hosts:
        hosts.append(render_host)
    origins = csv_values(env.get('DJANGO_CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173' if debug else ''))
    if not debug:
        if len(secret) < 50 or len(set(secret)) < 5 or secret.startswith(('django-insecure-', 'REPLACE_', 'CHANGE_ME')):
            raise ImproperlyConfigured('Set a unique DJANGO_SECRET_KEY of at least 50 characters in production. For local development, use python local.py runserver.')
        if not hosts or any(not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', host) or '..' in host for host in hosts):
            raise ImproperlyConfigured('DJANGO_ALLOWED_HOSTS must contain exact hostnames without schemes, paths or wildcards.')
        if not origins:
            raise ImproperlyConfigured('Set DJANGO_CSRF_TRUSTED_ORIGINS to the exact HTTPS frontend origin.')
        for origin in origins:
            try:
                parsed = urlsplit(origin)
                valid = (parsed.scheme == 'https' and parsed.hostname and re.fullmatch(r'[A-Za-z0-9.-]+', parsed.hostname) and '*' not in origin
                         and parsed.path == '' and not parsed.query and not parsed.fragment
                         and not parsed.username and not parsed.password and parsed.port != 0)
            except ValueError:
                valid = False
            if not valid:
                raise ImproperlyConfigured('CSRF trusted origins must be exact HTTPS origins without paths or wildcards.')
        service_url(database, 'DATABASE_URL', {'postgres', 'postgresql'})
        service_url(redis, 'REDIS_URL', {'redis', 'rediss'})
        service_url(cache, 'CACHE_URL', {'redis', 'rediss'})
    elif not secret:
        secret = 'sprintlens-local-development-only-not-for-production'
    return Runtime(debug, secret, hosts, origins, database, redis, cache)
