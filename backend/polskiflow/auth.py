"""Supabase Auth client and request authentication for the Django app."""

from __future__ import annotations

import json
import logging
import ssl
import time
from dataclasses import dataclass
from functools import wraps
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import certifi
from django.conf import settings
from django.http import JsonResponse

ACCESS_COOKIE = "polskiflow_access_token"
REFRESH_COOKIE = "polskiflow_refresh_token"
REFRESH_COOKIE_MAX_AGE = 60 * 60 * 24 * 30
HTTPS_CONTEXT = ssl.create_default_context(cafile=certifi.where())
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SupabaseUser:
    id: str
    email: str | None


@dataclass(frozen=True)
class SupabaseSession:
    access_token: str
    refresh_token: str
    expires_in: int
    user: SupabaseUser


class SupabaseAuthError(Exception):
    """A safe, user-facing Supabase Auth failure."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class SupabaseAuthMiddleware:
    """Resolve an optional Bearer token through Supabase Auth.

    Token verification stays with Supabase, so Django does not depend on the
    project's current JWT signing algorithm or copy a signing secret.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.supabase_user = None
        request.supabase_access_token = None
        authorization = request.headers.get("Authorization", "")
        scheme, _, token = authorization.partition(" ")
        bearer_token = token if scheme.lower() == "bearer" and token else None
        access_token = bearer_token or request.COOKIES.get(ACCESS_COOKIE)

        if access_token:
            request.supabase_user = authenticate_access_token(access_token)
            if request.supabase_user is not None:
                request.supabase_access_token = access_token

        refreshed_session = None
        clear_cookies = False
        if (
            request.supabase_user is None
            and bearer_token is None
            and request.COOKIES.get(REFRESH_COOKIE)
        ):
            try:
                refreshed_session = refresh_session(request.COOKIES[REFRESH_COOKIE])
            except SupabaseAuthError:
                clear_cookies = True
            else:
                request.supabase_user = refreshed_session.user
                request.supabase_access_token = refreshed_session.access_token

        from polskiflow.account_activity import record_if_due
        record_if_due(request)
        response = self.get_response(request)
        if refreshed_session is not None:
            set_auth_cookies(response, refreshed_session)
        elif clear_cookies:
            clear_auth_cookies(response)
        return response


def authenticate_access_token(token: str) -> SupabaseUser | None:
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        return None

    request = Request(
        f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/user",
        headers={
            "apikey": settings.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urlopen(
            request,
            timeout=settings.SUPABASE_AUTH_TIMEOUT,
            context=HTTPS_CONTEXT,
        ) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    user_id = payload.get("id")
    if not isinstance(user_id, str):
        return None
    email = payload.get("email")
    return SupabaseUser(id=user_id, email=email if isinstance(email, str) else None)


def sign_in(email: str, password: str) -> SupabaseSession:
    payload = _auth_request(
        "/auth/v1/token?grant_type=password",
        {"email": email, "password": password},
    )
    return _parse_session(payload)


def sign_up(
    email: str, password: str, *, email_redirect_to: str | None = None
) -> SupabaseSession | None:
    signup_payload = {"email": email, "password": password}
    if email_redirect_to:
        signup_payload["options"] = {"email_redirect_to": email_redirect_to}
    payload = _auth_request("/auth/v1/signup", signup_payload)
    if not payload.get("access_token"):
        return None
    return _parse_session(payload)


def request_password_reset(email: str, redirect_to: str) -> None:
    """Send Supabase's one-time password recovery link."""

    _auth_request(
        f"/auth/v1/recover?redirect_to={quote(redirect_to, safe=':/')}",
        {"email": email},
    )


def resend_signup_confirmation(email: str, redirect_to: str) -> None:
    """Resend an existing signup confirmation without creating a new user."""

    _auth_request(
        "/auth/v1/resend",
        {
            "type": "signup",
            "email": email,
            "options": {"email_redirect_to": redirect_to},
        },
    )


def update_password(
    access_token: str, password: str, *, current_password: str | None = None
) -> None:
    """Replace a password for a recovery or authenticated user session."""

    payload = {"password": password}
    if current_password is not None:
        payload["current_password"] = current_password
    _auth_request(
        "/auth/v1/user",
        payload,
        access_token=access_token,
        method="PUT",
    )


def refresh_session(refresh_token: str) -> SupabaseSession:
    payload = _auth_request(
        "/auth/v1/token?grant_type=refresh_token",
        {"refresh_token": refresh_token},
    )
    return _parse_session(payload)


def sign_out(access_token: str) -> None:
    """End this browser session without revoking the user's other sessions."""
    _auth_request("/auth/v1/logout?scope=local", {}, access_token=access_token)


def delete_account(access_token: str, user_id: str, password: str) -> None:
    """Ask the JWT-protected Supabase worker to reauthenticate and delete its caller."""

    payload = _auth_request(
        "/functions/v1/delete-account",
        {"password": password},
        access_token=access_token,
    )
    if payload.get("deleted_user_id") != user_id:
        raise SupabaseAuthError("Не удалось подтвердить удаление аккаунта")


def set_auth_cookies(response, session: SupabaseSession) -> None:
    cookie_options = {
        "httponly": True,
        "secure": settings.AUTH_COOKIE_SECURE,
        "samesite": "Lax",
        "path": "/",
    }
    response.set_cookie(
        ACCESS_COOKIE,
        session.access_token,
        max_age=session.expires_in,
        **cookie_options,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        session.refresh_token,
        max_age=REFRESH_COOKIE_MAX_AGE,
        **cookie_options,
    )


def clear_auth_cookies(response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/", samesite="Lax")
    response.delete_cookie(REFRESH_COOKIE, path="/", samesite="Lax")


def _auth_request(
    path: str,
    payload: dict[str, object],
    access_token: str | None = None,
    method: str = "POST",
) -> dict:
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        raise SupabaseAuthError("Supabase не настроен")

    body = json.dumps(payload).encode()
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    attempts = max(1, settings.SUPABASE_AUTH_NETWORK_ATTEMPTS)
    for attempt in range(attempts):
        request = Request(
            f"{settings.SUPABASE_URL.rstrip('/')}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(
                request,
                timeout=settings.SUPABASE_AUTH_TIMEOUT,
                context=HTTPS_CONTEXT,
            ) as response:
                if response.status == 204:
                    return {}
                result = json.load(response)
        except HTTPError as error:
            raise SupabaseAuthError(
                _http_error_message(error), status_code=error.code
            ) from error
        except json.JSONDecodeError as error:
            raise SupabaseAuthError("Сервис авторизации вернул некорректный ответ") from error
        except (URLError, TimeoutError) as error:
            logger.warning(
                "Supabase Auth network request failed (attempt %s/%s, reason=%s)",
                attempt + 1,
                attempts,
                type(getattr(error, "reason", error)).__name__,
            )
            if attempt + 1 == attempts:
                raise SupabaseAuthError(
                    "Сервис авторизации временно недоступен"
                ) from error
            time.sleep(settings.SUPABASE_AUTH_RETRY_BACKOFF * (2**attempt))
            continue
        break
    if not isinstance(result, dict):
        raise SupabaseAuthError("Некорректный ответ сервиса авторизации")
    return result




def _http_error_message(error: HTTPError) -> str:
    try:
        payload = json.load(error)
    except (json.JSONDecodeError, AttributeError):
        return "Не удалось выполнить авторизацию"
    message = payload.get("msg") or payload.get("message") or payload.get("error_description")
    return message if isinstance(message, str) else "Не удалось выполнить авторизацию"


def _parse_session(payload: dict) -> SupabaseSession:
    access_token = payload.get("access_token")
    refresh_token = payload.get("refresh_token")
    expires_in = payload.get("expires_in", 3600)
    user_payload = payload.get("user")
    if not isinstance(access_token, str) or not isinstance(refresh_token, str):
        raise SupabaseAuthError("Сессия не была создана")
    if not isinstance(user_payload, dict) or not isinstance(user_payload.get("id"), str):
        raise SupabaseAuthError("Ответ авторизации не содержит пользователя")
    email = user_payload.get("email")
    return SupabaseSession(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in if isinstance(expires_in, int) else 3600,
        user=SupabaseUser(
            id=user_payload["id"],
            email=email if isinstance(email, str) else None,
        ),
    )


def require_supabase_user(view):
    @wraps(view)
    def protected(request, *args, **kwargs):
        if request.supabase_user is None:
            return JsonResponse({"detail": "Authentication required"}, status=401)
        return view(request, *args, **kwargs)

    return protected
