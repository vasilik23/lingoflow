"""Privacy-safe request correlation for browser, API, and runtime logs."""

import logging
import time
import uuid

from django.conf import settings


logger = logging.getLogger("polskiflow.request")


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = _request_id(request.headers.get("X-Request-ID"))
        request.request_id = request_id
        started_at = time.monotonic()
        try:
            response = self.get_response(request)
        except Exception as error:
            logger.error(
                "request_exception request_id=%s method=%s path=%s duration_ms=%s exception_type=%s",
                request_id,
                request.method,
                request.path,
                _duration_ms(started_at),
                type(error).__name__,
            )
            raise
        response["X-Request-ID"] = request_id
        duration_ms = _duration_ms(started_at)
        timing = f"app;dur={duration_ms}"
        response["Server-Timing"] = ", ".join(filter(None, (response.get("Server-Timing"), timing)))
        if response.status_code >= 500:
            logger.warning(
                "request_failed request_id=%s method=%s path=%s status=%s duration_ms=%s",
                request_id,
                request.method,
                request.path,
                response.status_code,
                duration_ms,
            )
        elif duration_ms >= settings.REQUEST_SLOW_THRESHOLD_MS:
            logger.warning(
                "request_slow request_id=%s method=%s path=%s status=%s duration_ms=%s",
                request_id,
                request.method,
                request.path,
                response.status_code,
                duration_ms,
            )
        return response


def _request_id(candidate):
    try:
        return str(uuid.UUID(candidate))
    except (AttributeError, TypeError, ValueError):
        return str(uuid.uuid4())


def _duration_ms(started_at):
    return max(0, round((time.monotonic() - started_at) * 1000))
