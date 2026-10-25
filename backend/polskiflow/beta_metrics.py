"""Opt-in operator diagnostics. No SDK, browser identifiers, or response bodies."""

import json
import math
import re
import time
import uuid
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


def configured():
    return bool(settings.BETA_METRICS_ENABLED and settings.BETA_METRICS_SERVICE_KEY
                and settings.SUPABASE_URL
                and re.fullmatch(r"[0-9a-f]{40}", settings.BETA_METRICS_RELEASE))


def rpc(name, payload):
    if not configured():
        return None
    request = Request(
        settings.SUPABASE_URL.rstrip("/") + "/rest/v1/rpc/" + name,
        data=json.dumps(payload).encode(), method="POST",
        headers={"apikey": settings.BETA_METRICS_SERVICE_KEY,
                 "Authorization": "Bearer " + settings.BETA_METRICS_SERVICE_KEY,
                 "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=1) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        # Diagnostics never change a lesson outcome. Missing delivery is unknown,
        # never evidence of zero requests, errors, or lost results.
        return None


def reserve_attempt(request, lesson_id):
    if not configured():
        return None
    value = rpc("beta_reserve_attempt", {
        "p_owner": request.supabase_user.id, "p_lesson": lesson_id,
        "p_release": settings.BETA_METRICS_RELEASE,
    })
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        return None


def finish_attempt(request):
    attempt_id = getattr(request, "beta_attempt_id", None)
    if not configured() or not attempt_id:
        return None
    value = rpc("beta_finish_attempt", {
        "p_owner": request.supabase_user.id, "p_attempt": attempt_id,
        "p_release": settings.BETA_METRICS_RELEASE,
    })
    try:
        finished = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return finished if finished.tzinfo else None
    except (ValueError, TypeError, AttributeError):
        return None


ROUTES = {"home": "today", "lesson": "lesson", "lesson-step": "lesson",
          "api-v1-lesson-results-session": "result", "api-v1-lesson-results": "result"}


class BetaMetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not configured():
            return self.get_response(request)
        started = time.monotonic()
        response = self.get_response(request)
        duration = max(0, math.ceil((time.monotonic() - started) * 1000))
        match = getattr(request, "resolver_match", None)
        route = ROUTES.get(getattr(match, "url_name", None))
        user = getattr(request, "supabase_user", None)
        if route and user and request.method in {"GET", "POST"} and not response.streaming:
            attempt = getattr(request, "beta_attempt_id", None)
            # Only an accepted explicit interaction starts an attempt.
            accepted = route == "lesson" and request.method == "POST" and response.status_code == 200
            rpc("beta_observe_request", {
                "p_owner": user.id, "p_request": str(uuid.uuid4()),
                "p_release": settings.BETA_METRICS_RELEASE, "p_route": route,
                "p_method": request.method, "p_status": response.status_code,
                "p_duration": duration,
                "p_attempt": attempt if accepted else None,
                "p_finished": bool(accepted and getattr(request, "beta_finished", False)),
                "p_saved": bool(accepted and getattr(request, "beta_saved", False)),
                "p_total": getattr(request, "beta_total", None) if accepted else None,
                "p_known": getattr(request, "beta_known", None) if accepted else None,
            })
        return response
