"""Move browser navigation to LingoFlow while preserving existing API clients."""

from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponse


class CanonicalHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(":", 1)[0].lower()
        compatible_endpoint = (
            request.path_info.startswith(("/api/", "/static/"))
            or request.path_info in {"/health/", "/ready/", "/service-worker.js", "/manifest.webmanifest"}
        )
        if (
            settings.PUBLIC_APP_ORIGIN
            and host in settings.LEGACY_APP_HOSTS
            and request.method in {"GET", "HEAD"}
            and not compatible_endpoint
        ):
            response = HttpResponse(status=308)
            response["Location"] = settings.PUBLIC_APP_ORIGIN.rstrip("/") + request.get_full_path()
            response["Cache-Control"] = "no-store"
            return response
        return self.get_response(request)


def email_callback_url(request, path):
    """Use the provider-approved legacy gateway until its allowlist is updated."""
    canonical_host = urlsplit(settings.PUBLIC_APP_ORIGIN).hostname
    if settings.AUTH_EMAIL_CALLBACK_ORIGIN and request.get_host().split(":", 1)[0].lower() == canonical_host:
        return settings.AUTH_EMAIL_CALLBACK_ORIGIN.rstrip("/") + path
    return request.build_absolute_uri(path)
