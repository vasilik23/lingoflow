"""RLS-aware persistence through the Supabase Data API."""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from polskiflow.domain.progress import current_streak
from polskiflow.domain.lesson_results import LessonResult
from polskiflow.domain.daily_goal import minutes_from_legacy_lessons, legacy_lessons_from_minutes


@dataclass(frozen=True)
class DashboardProgress:
    display_name: str
    level: str
    streak_days: int
    completed_lesson_ids: frozenset[str]
    available: bool
    all_completed_lesson_ids: frozenset[str] = frozenset()
    active_days: int = 0
    weekly_active_days: int = 0
    weekly_completed_count: int = 0
    previous_week_active_days: int = 0
    previous_week_completed_count: int = 0
    monthly_active_days: int = 0
    monthly_completed_count: int = 0
    daily_goal_lessons: int = 4
    recent_daily_completion_counts: tuple[int, ...] = ()
    recent_completion_results: tuple[dict, ...] = ()
    daily_goal_minutes: int = 15

    @property
    def completed_count(self) -> int:
        return len(self.completed_lesson_ids)

    @property
    def weekly_active_days_delta(self) -> int:
        return self.weekly_active_days - self.previous_week_active_days

    @property
    def weekly_completed_delta(self) -> int:
        return self.weekly_completed_count - self.previous_week_completed_count


@dataclass(frozen=True)
class CompletionSaveResult:
    saved: bool
    retryable: bool


@dataclass(frozen=True)
class CompletionHistoryPage:
    rows: tuple[dict, ...]
    available: bool
    has_previous: bool
    has_next: bool
    page: int


def load_dashboard_progress(
    access_token: str | None,
    user_id: str,
    fallback_name: str,
) -> DashboardProgress:
    """Read the signed-in learner's profile and completion history via RLS."""

    if not _configured(access_token):
        return _empty_dashboard(fallback_name)

    profile = _get_rows(
        "profiles",
        {"select": "display_name,level,daily_goal_lessons,daily_goal_minutes", "id": f"eq.{user_id}", "limit": "1"},
        access_token,
    )
    completions = _get_rows(
        "lesson_completions",
        {
            "select": "lesson_id,plan_date,cards_total,cards_known",
            "user_id": f"eq.{user_id}",
            "order": "plan_date.desc",
            "limit": "1500",
        },
        access_token,
    )
    profile_row = profile[0] if profile else {}
    completion_rows = completions or []
    today = _utc_today()
    active_dates = []
    weekly_dates = set()
    weekly_lesson_ids = set()
    previous_week_dates = set()
    previous_week_lesson_ids = set()
    monthly_dates = set()
    monthly_lesson_ids = set()
    completed_today = set()
    completed_all_time = set()
    recent_completion_results = []
    recent_lessons_by_date = {
        today - timedelta(days=offset): set() for offset in range(28)
    }
    for completion in completion_rows:
        try:
            plan_date = datetime.strptime(completion["plan_date"], "%Y-%m-%d").date()
        except (KeyError, TypeError, ValueError):
            continue
        active_dates.append(plan_date)
        lesson_id = completion.get("lesson_id")
        if lesson_id and plan_date in recent_lessons_by_date:
            recent_lessons_by_date[plan_date].add(lesson_id)
        if today - timedelta(days=29) <= plan_date <= today:
            monthly_dates.add(plan_date)
            if lesson_id:
                monthly_lesson_ids.add(lesson_id)
        if today - timedelta(days=6) <= plan_date <= today:
            weekly_dates.add(plan_date)
            if lesson_id:
                weekly_lesson_ids.add(lesson_id)
        elif today - timedelta(days=13) <= plan_date <= today - timedelta(days=7):
            previous_week_dates.add(plan_date)
            if lesson_id:
                previous_week_lesson_ids.add(lesson_id)
        if lesson_id:
            completed_all_time.add(lesson_id)
            if plan_date == today:
                completed_today.add(lesson_id)
            if today - timedelta(days=29) <= plan_date < today:
                cards_total = completion.get("cards_total")
                cards_known = completion.get("cards_known")
                if (
                    isinstance(cards_total, int)
                    and not isinstance(cards_total, bool)
                    and cards_total > 0
                    and isinstance(cards_known, int)
                    and not isinstance(cards_known, bool)
                    and 0 <= cards_known <= cards_total
                ):
                    recent_completion_results.append(
                        {
                            "lesson_id": lesson_id,
                            "plan_date": plan_date.isoformat(),
                            "cards_total": cards_total,
                            "cards_known": cards_known,
                        }
                    )

    return DashboardProgress(
        display_name=profile_row.get("display_name") or fallback_name,
        level=profile_row.get("level") or "A1",
        streak_days=current_streak(active_dates, today),
        completed_lesson_ids=frozenset(completed_today),
        available=profile is not None and completions is not None,
        all_completed_lesson_ids=frozenset(completed_all_time),
        active_days=len(set(active_dates)),
        weekly_active_days=len(weekly_dates),
        weekly_completed_count=len(weekly_lesson_ids),
        previous_week_active_days=len(previous_week_dates),
        previous_week_completed_count=len(previous_week_lesson_ids),
        monthly_active_days=len(monthly_dates),
        monthly_completed_count=len(monthly_lesson_ids),
        daily_goal_lessons=profile_row.get("daily_goal_lessons") or 4,
        daily_goal_minutes=profile_row.get("daily_goal_minutes") or minutes_from_legacy_lessons(profile_row.get("daily_goal_lessons") or 4),
        recent_daily_completion_counts=tuple(
            len(recent_lessons_by_date[today - timedelta(days=offset)])
            for offset in range(27, -1, -1)
        ),
        recent_completion_results=tuple(recent_completion_results),
    )


def save_lesson_completion(
    access_token: str | None,
    user_id: str,
    lesson_id: str,
    cards_total: int,
    cards_known: int,
) -> bool:
    """Upsert today's completion as the authenticated user.

    Local development without Supabase remains usable; in a configured
    environment, a rejected or unavailable write is reported to the UI.
    """

    return save_lesson_completion_result(
        access_token, user_id, lesson_id, cards_total, cards_known
    ).saved


def load_completion_history(
    access_token: str | None,
    user_id: str,
    *,
    page: int = 1,
    page_size: int = 20,
    days: int | None = None,
) -> CompletionHistoryPage:
    """Load one owner-scoped page of lesson completion details through RLS."""

    page = max(1, min(page, 500))
    query = {
        "select": "lesson_id,plan_date,cards_total,cards_known",
        "user_id": f"eq.{user_id}",
        "order": "plan_date.desc,lesson_id.asc",
        "limit": str(page_size + 1),
        "offset": str((page - 1) * page_size),
    }
    if days is not None:
        query["plan_date"] = f"gte.{(_utc_today() - timedelta(days=days - 1)).isoformat()}"
    if not _configured(access_token):
        return CompletionHistoryPage((), False, page > 1, False, page)
    rows = _get_rows("lesson_completions", query, access_token)
    if rows is None:
        return CompletionHistoryPage((), False, page > 1, False, page)
    return CompletionHistoryPage(
        tuple(rows[:page_size]), True, page > 1, len(rows) > page_size, page
    )


def save_lesson_completion_result(
    access_token: str | None,
    user_id: str,
    lesson_id: str,
    cards_total: int,
    cards_known: int,
) -> CompletionSaveResult:
    """Save a completion and identify failures that are safe to retry later."""

    if not _configured(access_token):
        return CompletionSaveResult(saved=False, retryable=False)
    query = urlencode({"on_conflict": "user_id,lesson_id,plan_date"})
    payload = {
        "user_id": user_id,
        "lesson_id": lesson_id,
        "plan_date": _utc_today().isoformat(),
        "cards_total": cards_total,
        "cards_known": cards_known,
    }
    request = Request(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/lesson_completions?{query}",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "apikey": settings.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
    )
    try:
        with urlopen(request, timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            saved = response.status in (200, 201, 204)
            return CompletionSaveResult(saved=saved, retryable=response.status >= 500)
    except HTTPError as error:
        return CompletionSaveResult(saved=False, retryable=error.code >= 500)
    except (URLError, TimeoutError):
        return CompletionSaveResult(saved=False, retryable=True)


def record_lesson_result_event(
    access_token: str | None, result: LessonResult
) -> dict | None:
    """Atomically record an immutable event and update its completion projection."""
    if not _configured(access_token):
        return None
    payload = {
        "p_event_id": result.event_id,
        "p_lesson_id": result.lesson_id,
        "p_plan_date": result.plan_date,
        "p_completed_at": result.completed_at,
        "p_cards_total": result.cards_total,
        "p_cards_known": result.cards_known,
        "p_contract_version": result.contract_version,
        "p_client_instance_id": result.client_instance_id,
        "p_payload_hash": result.payload_hash,
    }
    request = Request(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/rpc/record_lesson_result",
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "apikey": settings.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            stored = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
    return stored if isinstance(stored, dict) else None


def save_profile_settings(
    access_token: str | None,
    user_id: str,
    display_name: str,
    level: str,
    daily_goal_lessons: int = 4,
    *,
    daily_goal_minutes: int | None = None,
) -> bool:
    """Update the authenticated learner's existing profile through RLS."""

    if not _configured(access_token):
        return False
    request = Request(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/profiles?"
        f"{urlencode({'id': f'eq.{user_id}'})}",
        data=json.dumps({"display_name": display_name, "level": level,
            "daily_goal_lessons": legacy_lessons_from_minutes(daily_goal_minutes) if daily_goal_minutes is not None else daily_goal_lessons,
            "daily_goal_minutes": daily_goal_minutes if daily_goal_minutes is not None else minutes_from_legacy_lessons(daily_goal_lessons)}).encode(),
        method="PATCH",
        headers={
            "apikey": settings.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    try:
        with urlopen(request, timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            return response.status in (200, 204)
    except (HTTPError, URLError, TimeoutError):
        return False


def _get_rows(table: str, query: dict[str, str], access_token: str) -> list[dict] | None:
    request = Request(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/{table}?{urlencode(query)}",
        headers={
            "apikey": settings.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            rows = json.load(response)
            return rows if isinstance(rows, list) else None
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def _configured(access_token: str | None) -> bool:
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY and access_token)


def _empty_dashboard(fallback_name: str) -> DashboardProgress:
    return DashboardProgress(fallback_name, "A1", 0, frozenset(), False)


def _utc_today():
    return datetime.now(timezone.utc).date()
