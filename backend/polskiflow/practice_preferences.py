"""Account-scoped, browser-only preferences for new practice recommendations."""

from django.core import signing
from django.utils.crypto import salted_hmac

PREFERENCE_COOKIE = "polskiflow_practice_topics"
PREFERENCE_SALT = "polskiflow.practice-topics.v1"
PREFERENCE_MAX_AGE = 90 * 24 * 60 * 60
REMOTE_WORK_TOPIC = "remote-work"


def _owner(user_id):
    return salted_hmac(PREFERENCE_SALT, user_id).hexdigest()


def excluded_practice_topics(request):
    try:
        payload = signing.loads(
            request.COOKIES.get(PREFERENCE_COOKIE, ""),
            salt=PREFERENCE_SALT, max_age=PREFERENCE_MAX_AGE,
        )
    except signing.BadSignature:
        return ()
    if not isinstance(payload, dict) or payload.get("owner") != _owner(request.supabase_user.id):
        return ()
    return (REMOTE_WORK_TOPIC,) if payload.get("exclude_remote_work") is True else ()


def set_practice_topics(response, request, *, exclude_remote_work):
    if not exclude_remote_work:
        response.delete_cookie(PREFERENCE_COOKIE, path="/", samesite="Lax")
        return
    value = signing.dumps({
        "owner": _owner(request.supabase_user.id), "exclude_remote_work": True,
    }, salt=PREFERENCE_SALT)
    response.set_cookie(
        PREFERENCE_COOKIE, value, max_age=PREFERENCE_MAX_AGE,
        secure=request.is_secure(), httponly=True, samesite="Lax", path="/",
    )
