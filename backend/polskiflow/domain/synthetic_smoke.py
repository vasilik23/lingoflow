"""Read-only production smoke checks for public and owner-scoped contracts."""

import json
import ssl
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPSHandler, HTTPRedirectHandler, Request, build_opener

import certifi


PUBLIC_CHECKS = (
    ("health", "health/"),
    ("ready", "ready/"),
    ("openapi", "api/v1/openapi.json"),
    ("catalog", "api/v1/catalog/"),
)
PRIVATE_CHECKS = (
    ("bootstrap", "api/v1/me/bootstrap/"),
    ("export", "api/v1/me/export/"),
)
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class _RejectRedirects(HTTPRedirectHandler):
    """Require direct contracts; never forward a learner token to a redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def urlopen(request, *, timeout, context):
    opener = build_opener(HTTPSHandler(context=context), _RejectRedirects())
    return opener.open(request, timeout=timeout)


@dataclass(frozen=True)
class SmokeResult:
    name: str
    status: int
    request_id: str


class SmokeFailure(ValueError):
    pass


def run_synthetic_smoke(
    base_url: str,
    access_token: str = "",
    *,
    timeout: float = 10,
    include_private: bool = True,
) -> tuple[SmokeResult, ...]:
    """Verify the read-only cold-start path without logging credentials or data."""

    base_url = _validated_base_url(base_url)
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout <= 60:
        raise SmokeFailure("timeout must be between 0 and 60 seconds")
    if include_private and (
        not access_token or any(character.isspace() for character in access_token)
    ):
        raise SmokeFailure("access token must be a non-empty single-line value")
    if not include_private and access_token:
        raise SmokeFailure("public-only smoke must not receive an access token")
    results = []
    checks = (*PUBLIC_CHECKS, *PRIVATE_CHECKS) if include_private else PUBLIC_CHECKS
    for name, path in checks:
        private = (name, path) in PRIVATE_CHECKS
        headers = {"Accept": "application/json", "User-Agent": "PolskiFlow-Synthetic-Smoke/1.0"}
        if private:
            headers["Authorization"] = f"Bearer {access_token}"
        request = Request(urljoin(base_url, path), headers=headers)
        try:
            with urlopen(request, timeout=timeout, context=SSL_CONTEXT) as response:
                payload = json.load(response)
                status = response.status
                response_headers = response.headers
        except HTTPError as error:
            raise SmokeFailure(f"{name}: HTTP {error.code}") from error
        except (URLError, TimeoutError, json.JSONDecodeError) as error:
            raise SmokeFailure(f"{name}: unavailable or invalid JSON") from error
        if status != 200 or not isinstance(payload, dict):
            raise SmokeFailure(f"{name}: unexpected response")
        _validate_payload(name, payload)
        cache_control = response_headers.get("Cache-Control", "").lower()
        if private and ("private" not in cache_control or "no-store" not in cache_control):
            raise SmokeFailure(f"{name}: private cache boundary missing")
        request_id = response_headers.get("X-Request-ID", "")
        if not request_id:
            raise SmokeFailure(f"{name}: request ID missing")
        results.append(SmokeResult(name, status, request_id))
    return tuple(results)


def _validated_base_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise SmokeFailure("base URL must be an HTTPS origin without credentials")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise SmokeFailure("base URL must be an origin without path, query or fragment")
    return value.strip().rstrip("/") + "/"


def _validate_payload(name, payload):
    if name == "health" and payload.get("status") != "ok":
        raise SmokeFailure("health: application is not healthy")
    if name == "ready" and payload.get("status") != "ready":
        raise SmokeFailure("ready: application is not ready")
    if name == "openapi" and "/api/v1/me/bootstrap/" not in payload.get("paths", {}):
        raise SmokeFailure("openapi: bootstrap contract missing")
    if name == "catalog" and not isinstance(payload.get("data", {}).get("courses"), list):
        raise SmokeFailure("catalog: course list missing")
    if name in {"bootstrap", "export"}:
        expected = f"learner-{'data-export' if name == 'export' else 'bootstrap'}"
        if payload.get("meta", {}).get("contract") != expected or not isinstance(payload.get("data"), dict):
            raise SmokeFailure(f"{name}: contract mismatch")
