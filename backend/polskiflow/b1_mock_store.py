"""Owner-scoped aggregate B1 mock history through Supabase RLS."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

ATTEMPT_LABELS = {
    "b1-weekly-v1": "Вариант 1",
    "b1-weekly-v2": "Вариант 2",
    "b1-weekly-v3": "Вариант 3",
}


def save_b1_mock_attempt(
    access_token: str | None, user_id: str, attempt_id: str, result: dict
) -> bool:
    """Persist scores only; selected answers and free production never leave the page."""
    if not _configured(access_token):
        return False
    by_id = {item["id"]: item for item in result["modules"]}
    payload = {
        "user_id": user_id,
        "attempt_id": attempt_id,
        "attempt_version": result.get("attempt_version", "b1-weekly-v1"),
        "listening_correct": by_id["listening"]["correct"],
        "reading_correct": by_id["reading"]["correct"],
        "grammar_correct": by_id["grammar"]["correct"],
    }
    try:
        path = "b1_mock_attempts?on_conflict=user_id%2Cattempt_id"
        with urlopen(
            _request(path, access_token, "POST", payload, ignore_duplicates=True),
            timeout=settings.SUPABASE_AUTH_TIMEOUT,
        ) as response:
            return response.status in (200, 201, 204)
    except (HTTPError, URLError, TimeoutError):
        return False


def load_b1_mock_attempts(access_token: str | None, user_id: str, limit: int = 8) -> list[dict] | None:
    """Return a bounded newest-first history, or None when history is unavailable."""
    if not _configured(access_token):
        return []
    safe_limit = min(max(int(limit), 1), 12)
    query = urlencode({
        "select": "attempted_at,listening_correct,reading_correct,grammar_correct,attempt_version",
        "user_id": f"eq.{user_id}",
        "order": "attempted_at.desc",
        "limit": str(safe_limit),
    })
    try:
        with urlopen(_request(f"b1_mock_attempts?{query}", access_token), timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            rows = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(rows, list):
        return None
    return [
        {**row, "variant_label": ATTEMPT_LABELS.get(row.get("attempt_version"), "Версия задания")}
        for row in rows if isinstance(row, dict)
    ]


def _request(path, token, method="GET", payload=None, ignore_duplicates=False):
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        prefer = "resolution=ignore-duplicates,return=minimal" if ignore_duplicates else "return=minimal"
        headers.update({"Content-Type": "application/json", "Prefer": prefer})
    return Request(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers=headers,
    )


def _configured(token):
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY and token)
