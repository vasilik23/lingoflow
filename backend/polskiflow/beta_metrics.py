"""Opt-in operator diagnostics. No SDK, browser identifiers, or response bodies."""

import json
import math
import re
import time
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.shortcuts import render
from polskiflow.domain.lesson_state import sign_lesson_state


def configured():
    return bool(settings.BETA_METRICS_ENABLED and settings.BETA_METRICS_SERVICE_KEY
                and settings.SUPABASE_URL
                and re.fullmatch(r"[0-9a-f]{40}", settings.BETA_METRICS_RELEASE))


def service_headers(key):
    headers = {"apikey": key, "Content-Type": "application/json"}
    # New secret keys are opaque API keys, not JWTs. Legacy service-role JWTs
    # still need the Authorization header; fixture transports use that path too.
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + key
    return headers


def rpc(name, payload):
    if not configured():
        return None
    request = Request(
        settings.SUPABASE_URL.rstrip("/") + "/rest/v1/rpc/" + name,
        data=json.dumps(payload).encode(), method="POST",
        headers=service_headers(settings.BETA_METRICS_SERVICE_KEY),
    )
    try:
        with urlopen(request, timeout=1) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError):
        # Diagnostics never change a lesson outcome. Missing delivery is unknown,
        # never evidence of zero requests, errors, or lost results.
        return None


def reserve_attempt(request, lesson_id):
    # Reserve together with observation, after the first render. No early RTT.
    if configured():
        request.beta_reserve_lesson = lesson_id
    return None


def _uuid(value):
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        return None


def render_for_metrics(request, template, context, *, state=None):
    response = render(request, template, context)
    if not configured():
        return response

    def apply_collected(value):
        if not isinstance(value, dict):
            return None
        attempt = _uuid(value.get('attempt_id'))
        updated = dict(context)
        if state and attempt:
            lesson, kind, index, score = state
            updated['lesson_state'] = sign_lesson_state(
                request.supabase_user.id, lesson, kind, index, score, attempt_id=attempt)
        elif context.get('offline_result_json') and attempt == getattr(request, 'beta_attempt_id', None) and attempt:
            try:
                finished = datetime.fromisoformat(value['finished_at'].replace('Z','+00:00'))
                if finished.tzinfo is None:
                    return None
                finished = finished.astimezone(timezone.utc)
                payload = json.loads(context['offline_result_json'])
                payload.update(event_id=attempt, plan_date=finished.date().isoformat(),
                               completed_at=finished.isoformat().replace('+00:00','Z'))
                updated['offline_result_json'] = json.dumps(payload,separators=(',',':'))
            except (KeyError, ValueError, TypeError, AttributeError):
                return None
        else:
            return None
        # The first render already initialized CSRF; keep its response headers
        # and cookies. Only final HTML changes, before the response is sent.
        return render(request, template, updated).content

    request.beta_apply_collected = apply_collected
    return response


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
            value = rpc("beta_collect_request", {
                "p_owner": user.id, "p_request": str(uuid.uuid4()),
                "p_release": settings.BETA_METRICS_RELEASE, "p_route": route,
                "p_method": request.method, "p_status": response.status_code,
                "p_duration": duration,
                "p_attempt": attempt if accepted else None,
                "p_finished": bool(accepted and getattr(request, "beta_finished", False)),
                "p_saved": bool(accepted and getattr(request, "beta_saved", False)),
                "p_total": getattr(request, "beta_total", None) if accepted else None,
                "p_known": getattr(request, "beta_known", None) if accepted else None,
                "p_reserve_lesson": getattr(request, "beta_reserve_lesson", None)
                    if request.method == "GET" and response.status_code == 200 else None,
            })
            apply_collected = getattr(request, 'beta_apply_collected', None)
            if apply_collected and response.status_code == 200:
                body = apply_collected(value)
                if body is not None:
                    response.content = body
                    if 'Content-Length' in response:
                        response['Content-Length'] = str(len(body))
        return response
