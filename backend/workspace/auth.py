import hashlib
import json
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.core.cache import cache
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST
from .models import Membership


def identity(user):
    if not user.is_authenticated:
        return None
    member = Membership.objects.filter(user=user).select_related('organization').order_by('id').first()
    return {'id': user.id, 'name': user.get_full_name() or user.username, 'username': user.username,
            'role': member.role if member else None, 'membership_id': member.id if member else None,
            'organization': {'id': member.organization_id, 'name': member.organization.name} if member else None}


@never_cache
@require_GET
def session(request):
    return JsonResponse({'user': identity(request.user), 'csrfToken': get_token(request)})


@never_cache
@require_POST
@csrf_protect
def sign_in(request):
    try:
        data = json.loads(request.body)
        username, password = data.get('username', ''), data.get('password', '')
        if not isinstance(username, str) or not isinstance(password, str) or len(username) > 150 or len(password) > 1024:
            raise ValueError
    except (ValueError, AttributeError, UnicodeDecodeError):
        return JsonResponse({'detail': 'Enter a valid username and password.'}, status=400)
    # An account-based key works behind proxies without trusting forwarded IP headers.
    key = 'login:' + hashlib.sha256(username.strip().lower().encode()).hexdigest()
    # Atomic shared-cache increments keep a fixed window across production workers.
    cache.add(key, 0, 60)
    try:
        attempts = cache.incr(key)
    except ValueError:
        cache.add(key, 0, 60)
        attempts = cache.incr(key)
    if attempts > 10:
        return JsonResponse({'detail': 'Too many attempts. Try again in a minute.'}, status=429)
    user = authenticate(request, username=username, password=password)
    if not user or not Membership.objects.filter(user=user).exists():
        return JsonResponse({'detail': 'Invalid credentials or no workspace access.'}, status=400)
    cache.delete(key)
    login(request, user)
    return JsonResponse({'user': identity(user), 'csrfToken': get_token(request)})


@never_cache
@require_POST
@csrf_protect
def sign_out(request):
    logout(request)
    return JsonResponse({'user': None, 'csrfToken': get_token(request)})


def csrf_failure(request, reason=''):
    return JsonResponse({'detail': 'Security token expired. Refresh and try again.'}, status=403)
