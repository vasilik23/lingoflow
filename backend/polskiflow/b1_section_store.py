"""Owner-scoped aggregate history for separately timed B1 sections."""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils.dateparse import parse_datetime

from polskiflow.b1_mock_store import ATTEMPT_LABELS


SECTION_LABELS = {
    "listening": "Аудирование",
    "reading": "Чтение",
    "grammar": "Грамматика",
}


def save_b1_section_attempt(access_token, user_id, attempt_id, variant_id, result):
    """Persist only one aggregate objective score; never persist selected answers."""
    section_id = result.get("section_id")
    if section_id not in SECTION_LABELS or not _configured(access_token):
        return False
    payload = {
        "user_id": user_id,
        "attempt_id": attempt_id,
        "attempt_version": variant_id,
        "section_id": section_id,
        "correct": result["correct"],
        "total": result["total"],
    }
    try:
        path = "b1_section_attempts?on_conflict=user_id%2Cattempt_id"
        with urlopen(
            _request(path, access_token, "POST", payload, ignore_duplicates=True),
            timeout=settings.SUPABASE_AUTH_TIMEOUT,
        ) as response:
            return response.status in (200, 201, 204)
    except (HTTPError, URLError, TimeoutError, KeyError, TypeError, ValueError):
        return False


def load_b1_section_attempts(access_token, user_id, limit=12):
    """Return a bounded newest-first aggregate history, or None when unavailable."""
    if not _configured(access_token):
        return []
    safe_limit = min(max(int(limit), 1), 20)
    query = urlencode({
        "select": "attempted_at,attempt_version,section_id,correct,total",
        "user_id": f"eq.{user_id}",
        "order": "attempted_at.desc",
        "limit": str(safe_limit),
    })
    try:
        with urlopen(
            _request(f"b1_section_attempts?{query}", access_token),
            timeout=settings.SUPABASE_AUTH_TIMEOUT,
        ) as response:
            rows = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(rows, list):
        return None
    history = []
    for row in rows:
        if not isinstance(row, dict) or row.get("section_id") not in SECTION_LABELS:
            continue
        try:
            correct, total = int(row["correct"]), int(row["total"])
            if total < 1 or not 0 <= correct <= total:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        history.append({
            **row,
            "correct": correct,
            "total": total,
            "percent": round(correct * 100 / total),
            "section_label": SECTION_LABELS[row["section_id"]],
            "variant_label": ATTEMPT_LABELS.get(row.get("attempt_version"), "Версия задания"),
            "attempted_at_display": _display_datetime(row.get("attempted_at")),
        })
    return history


def _request(path, token, method="GET", payload=None, ignore_duplicates=False):
    headers = {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if payload is not None:
        headers.update({
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates,return=minimal" if ignore_duplicates else "return=minimal",
        })
    return Request(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers=headers,
    )


def _configured(token):
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY and token)


def _display_datetime(value):
    parsed = parse_datetime(value) if isinstance(value, str) else None
    return parsed.strftime("%d.%m.%Y %H:%M") if parsed else "Дата недоступна"
