"""Unauthenticated, non-sensitive probes; readiness is independent of third-party AI."""
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def live(request):
    return JsonResponse({'status':'ok'})


@never_cache
@require_GET
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
        cache.get('health:readiness')
    except Exception:
        # Public probes must never expose connection details or credential-bearing exceptions.
        return JsonResponse({'status':'unavailable'},status=503)
    return JsonResponse({'status':'ready'})
