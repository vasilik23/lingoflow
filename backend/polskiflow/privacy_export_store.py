"""Complete owner-scoped data export through Supabase RLS."""

import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


PAGE_SIZE = 500
MAX_PAGES = 100

DATASETS = {
    "profile": ("profiles", "display_name,level,daily_goal_lessons,daily_goal_minutes,streak_days,last_active_date,created_at", "created_at.asc"),
    "lesson_completions": ("lesson_completions", "lesson_id,plan_date,cards_total,cards_known,completed_at", "plan_date.asc,lesson_id.asc"),
    "lesson_result_events": ("lesson_result_events", "event_id,lesson_id,plan_date,completed_at,cards_total,cards_known,contract_version,client_instance_id,created_at", "created_at.asc,event_id.asc"),
    "lesson_drafts": ("lesson_drafts", "lesson_id,lesson_kind,step_index,score,updated_at", "updated_at.asc,lesson_id.asc"),
    "personal_words": ("personal_words", "id,word,translation,context,source_text_id,created_at,ease_factor,interval_days,repetitions,next_review_date,last_reviewed_at", "created_at.asc,id.asc"),
    "reading_bookmarks": ("reading_bookmarks", "reading_text_id,created_at", "created_at.asc,reading_text_id.asc"),
    "lesson_bookmarks": ("lesson_bookmarks", "lesson_id,created_at", "created_at.asc,lesson_id.asc"),
    "learner_mistakes": ("learner_mistakes", "lesson_id,question_position,last_wrong_at", "last_wrong_at.asc,lesson_id.asc,question_position.asc"),
    "lesson_notes": ("lesson_notes", "lesson_id,body,updated_at", "updated_at.asc,lesson_id.asc"),
    "learning_collections": ("learning_collections", "id,name,created_at", "created_at.asc,id.asc"),
    "learning_collection_items": ("learning_collection_items", "id,collection_id,content_type,content_id,created_at", "created_at.asc,id.asc"),
    "feedback": ("user_feedback", "id,category,message,page_url,priority,status,created_at", "created_at.asc,id.asc"),
    "reminder_preferences": ("reminder_preferences", "daily_reminder_enabled,reminder_time,timezone,updated_at", "updated_at.asc"),
    "b1_mock_attempts": ("b1_mock_attempts", "id,attempt_id,attempted_at,attempt_version,listening_correct,reading_correct,grammar_correct", "attempted_at.asc,id.asc"),
    "b1_section_attempts": ("b1_section_attempts", "id,attempt_id,attempted_at,attempt_version,section_id,correct,total", "attempted_at.asc,id.asc"),
    "b1_run_attempts": ("b1_run_attempts", "run_id,variant_id,content_version,started_at,finished_at,results", "finished_at.asc,run_id.asc"),
}


@dataclass(frozen=True)
class PrivacyExport:
    available: bool
    datasets: dict[str, list[dict]]


def load_privacy_export(access_token: str | None, user_id: str) -> PrivacyExport:
    """Return every supported owner row, or fail closed without a partial export."""

    if not _configured(access_token):
        return PrivacyExport(False, {})
    exported = {}
    for name, (table, fields, order) in DATASETS.items():
        rows = _load_all(table, fields, order, access_token, user_id)
        if rows is None:
            return PrivacyExport(False, {})
        exported[name] = rows
    return PrivacyExport(True, exported)


def _load_all(table, fields, order, access_token, user_id):
    rows = []
    for page in range(MAX_PAGES):
        query = urlencode({
            "select": fields,
            "user_id" if table != "profiles" else "id": f"eq.{user_id}",
            "order": order,
            "limit": str(PAGE_SIZE),
            "offset": str(page * PAGE_SIZE),
        })
        try:
            with urlopen(_request(f"{table}?{query}", access_token), timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
                batch = json.load(response)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
            return None
        if not isinstance(batch, list):
            return None
        rows.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < PAGE_SIZE:
            return rows
    return None  # Never silently truncate an unusually large export.


def _request(path, access_token):
    return Request(
        f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1/{path}",
        headers={
            "apikey": settings.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        },
    )


def _configured(access_token):
    return bool(settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY and access_token)
