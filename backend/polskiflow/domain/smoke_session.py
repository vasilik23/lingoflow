"""Ephemeral password-grant session for a dedicated synthetic learner."""

import json
import os
import re
from contextlib import contextmanager
from uuid import UUID
from urllib.error import HTTPError, URLError
from urllib.request import Request

from polskiflow.domain.synthetic_smoke import SSL_CONTEXT, SmokeFailure, urlopen

PRODUCTION_ORIGIN = "https://lingoflow-learn.vercel.app"


def _request(origin, key, path, payload, token=""):
    headers = {"apikey": key, "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(origin + path, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=10, context=SSL_CONTEXT) as response:
            if token:
                if response.status != 204:
                    raise SmokeFailure("smoke session logout failed")
                return None
            if response.status != 200:
                raise SmokeFailure("smoke session login failed")
            body = response.read(65537)
            if len(body) > 65536:
                raise SmokeFailure("smoke session response too large")
            return json.loads(body)
    except (HTTPError, URLError, TimeoutError, ValueError, UnicodeError):
        raise SmokeFailure("smoke session request failed; check credentials, Auth availability and limits") from None


@contextmanager
def fresh_smoke_session(base_url):
    """Keep credentials/tokens in memory; revoke only this session in finally."""
    if base_url.rstrip("/") != PRODUCTION_ORIGIN:
        raise SmokeFailure("fresh session is restricted to the canonical production origin")
    origin = os.environ.get("LINGOFLOW_SMOKE_AUTH_URL", "")
    key = os.environ.get("LINGOFLOW_SMOKE_PUBLISHABLE_KEY", "")
    email = os.environ.get("LINGOFLOW_SMOKE_EMAIL", "")
    password = os.environ.get("LINGOFLOW_SMOKE_PASSWORD", "")
    owner = os.environ.get("LINGOFLOW_SMOKE_USER_ID", "")
    if not re.fullmatch(r"https://[a-z0-9]{20}\.supabase\.co", origin):
        raise SmokeFailure("configure a hosted Supabase Auth origin")
    if not key.startswith("sb_publishable_") or any(c.isspace() for c in key):
        raise SmokeFailure("configure a Supabase publishable key, never a secret/service key")
    try:
        UUID(owner)
    except (ValueError, AttributeError):
        raise SmokeFailure("configure the dedicated smoke user UUID") from None
    if not email or not password:
        raise SmokeFailure("configure dedicated smoke account credentials")
    payload = _request(origin, key, "/auth/v1/token?grant_type=password", {"email": email, "password": password})
    token = payload.get("access_token") if isinstance(payload, dict) else None
    if not isinstance(token, str) or not token or len(token) > 16384 or any(c.isspace() for c in token):
        raise SmokeFailure("smoke session token missing or invalid")
    try:
        user = payload.get("user")
        ttl = payload.get("expires_in")
        if (payload.get("token_type") != "bearer" or type(ttl) is not int or not 300 <= ttl <= 3600
                or not isinstance(user, dict) or user.get("id") != owner or user.get("is_anonymous") is not False):
            raise SmokeFailure("smoke session identity or lifetime mismatch")
        yield token
    finally:
        _request(origin, key, "/auth/v1/logout?scope=local", {}, token)
