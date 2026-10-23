"""Coalesced, acknowledged activity stamps; never keep request paths or tokens."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import UUID

from django.conf import settings
from django.core.cache import cache


def record_activity(token, user_id):
    """Return DB-confirmed remaining throttle seconds; zero is not an ACK."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY or not token:
        return 0
    request = Request(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/record_account_activity",
        data=b'{}', method='POST', headers={
            'apikey': settings.SUPABASE_ANON_KEY, 'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json', 'Accept': 'application/json',
        },
    )
    try:
        with urlopen(request, timeout=min(settings.SUPABASE_AUTH_TIMEOUT, 1.0)) as response:
            ttl = json.load(response)
        return ttl if type(ttl) is int and 1 <= ttl <= 900 else 0
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return 0


def record_if_due(request):
    if not settings.ACCOUNT_ACTIVITY_ENABLED or not request.supabase_user:
        return
    if request.path.startswith(('/health/', '/ready/', '/static/', '/admin/')):
        return
    try:
        owner = str(UUID(request.supabase_user.id))
    except (ValueError, AttributeError, TypeError):
        return
    # Different accounts and in-flight requests cannot share acknowledgement.
    key = f'account-activity:v1:{owner}'
    lock = key + ':inflight'
    try:
        if cache.get(key) or cache.get(key + ':retry') or not cache.add(lock, True, timeout=5):
            return
    except Exception:
        # Cache outage must not turn read-only navigation into a login failure.
        return
    try:
        ttl = record_activity(request.supabase_access_token, owner)
        if ttl:
            cache.set(key, True, timeout=ttl)
        else:
            cache.set(key + ':retry', True, timeout=30)
    except Exception:
        # Activity telemetry/cache must never break the user's request.
        pass
    finally:
        try:
            cache.delete(lock)
        except Exception:
            pass
