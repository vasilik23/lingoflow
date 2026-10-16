"""Read-only eligibility for the foreground Today reminder; no push delivery."""
import re
from zoneinfo import ZoneInfo

from django.http import JsonResponse
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.http import require_safe

from polskiflow.reminder_preference_store import load_reminder_preferences


def browser_namespace(user_id):
    return salted_hmac("lingoflow.browser-reminder", str(user_id)).hexdigest()[:32]


def reminder_context(request):
    user = getattr(request, "supabase_user", None)
    return {"browser_reminder_namespace": browser_namespace(user.id) if user else ""}


@require_safe
def browser_reminder(request):
    response = _eligibility(request)
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Cookie"
    return response


def _eligibility(request):
    user = getattr(request, "supabase_user", None)
    if user is None or request.headers.get("Authorization"):
        return JsonResponse({"error": "cookie_session_required"}, status=401)
    preferences = load_reminder_preferences(request.supabase_access_token, user.id)
    if preferences is None:
        return JsonResponse({"error": "preferences_unavailable"}, status=503)
    clock = preferences.get("reminder_time")
    if (not isinstance(clock, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", clock)
            or preferences.get("timezone") != "Europe/Warsaw"):
        return JsonResponse({"error": "invalid_preferences"}, status=503)
    now = timezone.now().astimezone(ZoneInfo("Europe/Warsaw"))
    return JsonResponse({
        "namespace": browser_namespace(user.id),
        "day": now.date().isoformat(),
        "due": preferences.get("daily_reminder_enabled") is True and now.strftime("%H:%M") >= clock,
        "channel": "today_foreground",
        "background_delivery": False,
    })
