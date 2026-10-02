"""Versioned API contracts for separate clients."""

from datetime import date
from functools import wraps

import json
import re

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from polskiflow.auth import SupabaseAuthError, delete_account, require_supabase_user as require_authenticated_user
from polskiflow.content import flashcards, grammar, public_course_catalog, quiz, reading_text, reading_texts, task, tasks
from polskiflow.dictionary_store import delete_personal_word, load_personal_words, save_personal_word, save_personal_word_review
from polskiflow.feedback_store import load_feedback, save_feedback
from polskiflow.domain.lesson_results import (
    MAX_REQUEST_BYTES,
    LessonResultValidationError,
    validate_lesson_result,
)
from polskiflow.domain.daily_plan import DAILY_TIME_MODES, build_daily_plan
from polskiflow.domain.achievements import build_achievements
from polskiflow.domain.api_rate_limit import consume_api_mutation
from polskiflow.domain.openapi_v1 import build_openapi_v1
from polskiflow.domain.native_lessons import NativeLessonError, build_native_lesson, evaluate_native_answer
from polskiflow.domain.native_listening import NativeListeningError, build_native_listening, evaluate_native_listening_answer
from polskiflow.domain.native_interaction import NativeInteractionError, build_native_interaction, evaluate_native_interaction
from polskiflow.domain.native_diagnostic import NativeDiagnosticError, build_native_diagnostic, evaluate_native_diagnostic
from polskiflow.native_writing import NativeWritingError, build_native_writing, evaluate_native_writing
from polskiflow.domain.native_reading import READING_LEVELS, filter_native_readings, resolve_glossary_entry, serialize_reading_detail
from polskiflow.domain.sm2 import Sm2State, sm2_next
from polskiflow.learning.models import Lesson, Level
from polskiflow.lesson_draft_store import delete_lesson_draft, load_latest_lesson_draft_result, save_lesson_draft
from polskiflow.news_feed import CATEGORIES, CATEGORY_IDS, latest_official_news
from polskiflow.progress_store import load_completion_history, load_dashboard_progress, record_lesson_result_event, save_profile_settings
from polskiflow.privacy_export_store import load_privacy_export
from polskiflow.reading_bookmark_store import load_reading_bookmarks, set_reading_bookmark
from polskiflow.reminder_preference_store import load_reminder_preferences, save_reminder_preferences


API_VERSION = "v1"
CATALOG_CONTRACT_VERSION = "1.0.0"
LEARNER_CONTRACT_VERSION = "1.0.0"
FEEDBACK_CATEGORIES = frozenset({"content", "translation", "interface", "technical", "idea"})
FEEDBACK_PRIORITIES = frozenset({"normal", "high", "blocking"})


def require_supabase_user(view):
    """Keep every v1 authentication failure inside the private API envelope."""
    @wraps(view)
    @require_authenticated_user
    def protected(request, *args, **kwargs):
        return view(request, *args, **kwargs)

    def api_protected(request, *args, **kwargs):
        if request.supabase_user is None:
            return _error_response(
                "authentication_required", "Authentication is required", 401
            )
        return protected(request, *args, **kwargs)

    return wraps(view)(api_protected)


@csrf_exempt
@require_http_methods(["DELETE"])
@require_supabase_user
def learner_account_v1(request):
    """Permanently delete the authenticated caller after password reauthentication."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "account"):
        return limited
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 2048:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    if (
        not isinstance(payload, dict)
        or set(payload) != {"password"}
        or not isinstance(payload["password"], str)
        or not payload["password"]
        or len(payload["password"]) > 1024
    ):
        return _error_response("validation_error", "Use exactly one non-empty password string", 400)
    try:
        delete_account(
            request.supabase_access_token,
            str(request.supabase_user.id),
            payload["password"],
        )
    except SupabaseAuthError as error:
        status = 403 if error.status_code == 403 else 503
        return _error_response(
            "password_verification_failed" if status == 403 else "account_deletion_unavailable",
            "Password verification failed or account deletion is temporarily unavailable",
            status,
        )
    return _private_response("learner-account", {"deleted": True})


@require_safe
@require_supabase_user
def learner_data_export_v1(request):
    """Return a complete portable snapshot for the authenticated owner."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    export = load_privacy_export(
        request.supabase_access_token, str(request.supabase_user.id)
    )
    if not export.available:
        return _unavailable_response("learner-data-export")
    return _private_response(
        "learner-data-export",
        {
            "schema_version": "2.2",
            "account": {"email": request.supabase_user.email},
            **export.datasets,
        },
    )


@require_safe
def openapi_v1(_request):
    response = JsonResponse(build_openapi_v1(), json_dumps_params={"ensure_ascii": False})
    response["Cache-Control"] = "public, max-age=300, s-maxage=3600"
    return response


@require_safe
def catalog_v1(_request):
    """Expose active learning structure, never learner-owned state or answers."""
    courses = public_course_catalog()
    response = JsonResponse(
        {
            "api_version": API_VERSION,
            "meta": {
                "contract": "public-course-catalog",
                "contract_version": CATALOG_CONTRACT_VERSION,
                "generated_at": timezone.now().isoformat(),
                "levels": list(Level.values),
                "course_count": len(courses),
            },
            "data": {"courses": courses},
        },
        json_dumps_params={"ensure_ascii": False},
    )
    response["Cache-Control"] = "public, max-age=60, s-maxage=300, stale-while-revalidate=600"
    return response


@require_safe
def news_v1(request):
    """Expose bounded, attributed headlines without proxying article content."""
    category = request.GET.get("category", "")
    try:
        limit = int(request.GET.get("limit", "12"))
    except (TypeError, ValueError):
        limit = 0
    if (category and category not in CATEGORY_IDS) or not 1 <= limit <= 12:
        return _error_response(
            "invalid_filters", "Use a supported category and limit from 1 to 12", 400
        )
    items = latest_official_news(limit=limit, category=category or None)
    response = JsonResponse(
        {
            "api_version": API_VERSION,
            "meta": {
                "contract": "public-news-headlines",
                "contract_version": "1.0.0",
                "generated_at": timezone.now().isoformat(),
                "available": bool(items),
                "external_content": True,
            },
            "data": {
                "category": category or None,
                "categories": list(CATEGORIES),
                "headlines": [
                    {
                        key: item.get(key, "")
                        for key in (
                            "title", "url", "source", "category",
                            "category_label", "published",
                        )
                    }
                    for item in items
                ],
            },
        },
        json_dumps_params={"ensure_ascii": False},
    )
    response["Cache-Control"] = "public, max-age=60, s-maxage=300, stale-while-revalidate=600"
    return response


@require_safe
@require_supabase_user
def native_lesson_v1(request, lesson_id):
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    lesson = build_native_lesson(lesson_id)
    if lesson is None:
        return _error_response("lesson_not_found", "Active lesson was not found", 404)
    return _private_response("native-lesson", {
        "lesson": lesson.metadata,
        "theory": lesson.theory,
        "steps": lesson.steps,
        "step_count": len(lesson.steps),
    })


@csrf_exempt
@require_POST
@require_supabase_user
def native_lesson_answer_v1(request, lesson_id):
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "answer"):
        return limited
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 2048:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    if not isinstance(payload, dict):
        return _error_response("validation_error", "Request body must be an object", 400)
    try:
        evaluation = evaluate_native_answer(lesson_id, payload.get("position"), payload)
    except NativeLessonError as error:
        if str(error) == "lesson_not_found":
            return _error_response("lesson_not_found", "Active lesson was not found", 404)
        return _error_response("validation_error", str(error), 400)
    return _private_response("native-lesson-answer", evaluation)


@require_safe
@require_supabase_user
def native_listening_v1(request):
    """Return bounded listening exercises without answer keys."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    exercises = build_native_listening()
    return _private_response(
        "native-listening",
        {"exercises": exercises, "exercise_count": len(exercises)},
    )


@csrf_exempt
@require_POST
@require_supabase_user
def native_listening_answer_v1(request, exercise_id):
    """Evaluate one listening choice without persisting learner state."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "answer"):
        return limited
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 512:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    if not isinstance(payload, dict) or set(payload) != {"question_id", "selected_index"}:
        return _error_response(
            "validation_error", "Use exactly question_id and selected_index", 400
        )
    question_id = payload["question_id"]
    if not isinstance(question_id, str) or not question_id or len(question_id) > 80:
        return _error_response("validation_error", "question_id must contain 1..80 characters", 400)
    try:
        evaluation = evaluate_native_listening_answer(
            exercise_id, question_id, payload["selected_index"]
        )
    except NativeListeningError as error:
        if str(error) == "exercise_not_found":
            return _error_response("listening_exercise_not_found", "Listening exercise was not found", 404)
        return _error_response("validation_error", str(error), 400)
    return _private_response("native-listening-answer", evaluation)


@require_safe
@require_supabase_user
def native_interaction_v1(request):
    """Return interaction prompts without answer keys."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    return _private_response("native-interaction", build_native_interaction())


@csrf_exempt
@require_POST
@require_supabase_user
def native_interaction_answer_v1(request, scenario_id):
    """Evaluate one choice or sequence without persisting learner state."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "answer"):
        return limited
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 1024:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    if not isinstance(payload, dict):
        return _error_response("validation_error", "Request body must be an object", 400)
    try:
        evaluation = evaluate_native_interaction(scenario_id, payload)
    except NativeInteractionError as error:
        if str(error) == "scenario_not_found":
            return _error_response("interaction_scenario_not_found", "Interaction scenario was not found", 404)
        return _error_response("validation_error", str(error), 400)
    return _private_response("native-interaction-answer", evaluation)


@require_safe
@require_supabase_user
def native_diagnostic_v1(request):
    """Return the diagnostic form without answer keys."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    return _private_response("native-diagnostic", build_native_diagnostic())


@csrf_exempt
@require_POST
@require_supabase_user
def native_diagnostic_evaluate_v1(request):
    """Evaluate the complete diagnostic without storing answers or profile state."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "answer"):
        return limited
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 4096:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    if not isinstance(payload, dict):
        return _error_response("validation_error", "Request body must be an object", 400)
    try:
        result = evaluate_native_diagnostic(payload)
    except NativeDiagnosticError as error:
        return _error_response("validation_error", str(error), 400)
    return _private_response("native-diagnostic-result", result)


@require_safe
@require_supabase_user
def native_writing_v1(request):
    """Return B1/B2 writing prompts and honest structural criteria."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    return _private_response("native-writing", build_native_writing())


@csrf_exempt
@require_POST
@require_supabase_user
def native_writing_check_v1(request, prompt_id):
    """Check visible text structure without storing or grading the draft."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "answer"):
        return limited
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 20000:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    if not isinstance(payload, dict) or set(payload) != {"text"}:
        return _error_response("validation_error", "Use exactly text", 400)
    try:
        result = evaluate_native_writing(prompt_id, payload["text"])
    except NativeWritingError as error:
        if str(error) == "prompt_not_found":
            return _error_response("writing_prompt_not_found", "Writing prompt was not found", 404)
        return _error_response("validation_error", str(error), 400)
    return _private_response("native-writing-check", result)


@require_safe
@require_supabase_user
def learner_progress_v1(request):
    """Expose only the authenticated learner's aggregate progress."""
    user = request.supabase_user
    progress = load_dashboard_progress(
        request.supabase_access_token,
        user.id,
        user.email or "Ученик",
    )
    if not progress.available:
        return _unavailable_response("learner-progress")

    return _private_response(
        "learner-progress",
        {
            "profile": {"display_name": progress.display_name, "level": progress.level, "daily_goal_lessons": progress.daily_goal_lessons},
            "streak_days": progress.streak_days,
            "active_days": progress.active_days,
            "completed_lesson_ids": sorted(progress.all_completed_lesson_ids),
            "periods": {
                "week": {"active_days": progress.weekly_active_days, "completed_lessons": progress.weekly_completed_count},
                "previous_week": {"active_days": progress.previous_week_active_days, "completed_lessons": progress.previous_week_completed_count},
                "month": {"active_days": progress.monthly_active_days, "completed_lessons": progress.monthly_completed_count},
            },
        },
    )


@csrf_exempt
@require_http_methods(["GET", "HEAD", "PATCH"])
@require_supabase_user
def learner_profile_v1(request):
    """Read or update bounded owner-scoped profile settings."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if request.method == "PATCH" and (limited := _mutation_rate_limit(request, "profile")):
        return limited
    user = request.supabase_user
    progress = load_dashboard_progress(
        request.supabase_access_token, user.id, (user.email or "learner").split("@", 1)[0]
    )
    if not progress.available:
        return _unavailable_response("learner-profile")
    profile = {
        "display_name": progress.display_name,
        "level": progress.level,
        "daily_goal_lessons": progress.daily_goal_lessons,
    }
    if request.method in {"GET", "HEAD"}:
        return _private_response("learner-profile", {"profile": profile})
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 1024:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    allowed = {"display_name", "level", "daily_goal_lessons"}
    if not isinstance(payload, dict) or not payload or not set(payload) <= allowed:
        return _error_response("validation_error", "Use one or more supported profile fields", 400)
    display_name = payload.get("display_name", profile["display_name"])
    level = payload.get("level", profile["level"])
    daily_goal = payload.get("daily_goal_lessons", profile["daily_goal_lessons"])
    if not isinstance(display_name, str) or not display_name.strip() or len(display_name.strip()) > 80:
        return _error_response("validation_error", "display_name must contain 1..80 characters", 400)
    if not isinstance(level, str) or level not in Level.values:
        return _error_response("validation_error", "level must be A1, A2, B1, B2, C1, or C2", 400)
    if isinstance(daily_goal, bool) or not isinstance(daily_goal, int) or not 1 <= daily_goal <= 10:
        return _error_response("validation_error", "daily_goal_lessons must be an integer from 1 to 10", 400)
    profile = {"display_name": display_name.strip(), "level": level, "daily_goal_lessons": daily_goal}
    if not save_profile_settings(
        request.supabase_access_token, user.id,
        profile["display_name"], profile["level"], profile["daily_goal_lessons"],
    ):
        return _unavailable_response("learner-profile")
    return _private_response("learner-profile", {"profile": profile})


@csrf_exempt
@require_http_methods(["GET", "HEAD", "PATCH"])
@require_supabase_user
def learner_reminder_preferences_v1(request):
    """Read or update explicit opt-in reminder settings; delivery is not implied."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    user = request.supabase_user
    preferences = load_reminder_preferences(request.supabase_access_token, user.id)
    if preferences is None:
        return _unavailable_response("learner-reminder-preferences")
    if request.method in {"GET", "HEAD"}:
        return _private_response(
            "learner-reminder-preferences",
            {"preferences": preferences, "delivery_active": False},
        )
    if limited := _mutation_rate_limit(request, "profile"):
        return limited
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 512:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    allowed = {"daily_reminder_enabled", "reminder_time"}
    if not isinstance(payload, dict) or not payload or not set(payload) <= allowed:
        return _error_response("validation_error", "Use one or more supported reminder fields", 400)
    enabled = payload.get("daily_reminder_enabled", preferences["daily_reminder_enabled"])
    reminder_time = payload.get("reminder_time", preferences["reminder_time"])
    if not isinstance(enabled, bool):
        return _error_response("validation_error", "daily_reminder_enabled must be boolean", 400)
    if not isinstance(reminder_time, str) or not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", reminder_time):
        return _error_response("validation_error", "reminder_time must use HH:MM", 400)
    timezone_name = "Europe/Warsaw"
    if not save_reminder_preferences(
        request.supabase_access_token, user.id, enabled, reminder_time, timezone_name
    ):
        return _unavailable_response("learner-reminder-preferences")
    return _private_response(
        "learner-reminder-preferences",
        {
            "preferences": {
                "daily_reminder_enabled": enabled,
                "reminder_time": reminder_time,
                "timezone": timezone_name,
            },
            "delivery_active": False,
        },
    )


@csrf_exempt
@require_http_methods(["GET", "HEAD", "POST"])
@require_supabase_user
def learner_feedback_v1(request):
    """List or create feedback owned by the authenticated learner."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    user = request.supabase_user
    if request.method in {"GET", "HEAD"}:
        items = load_feedback(request.supabase_access_token, user.id)
        if items is None:
            return _unavailable_response("learner-feedback")
        return _private_response("learner-feedback", {"items": items})
    if limited := _mutation_rate_limit(request, "feedback"):
        return limited
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 4096:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    if not isinstance(payload, dict) or not {"category", "message"} <= set(payload) or not set(payload) <= {"category", "message", "page_url", "priority"}:
        return _error_response(
            "validation_error", "Use category, message, optional page_url and priority", 400
        )
    category, message = payload.get("category"), payload.get("message")
    page_url = payload.get("page_url", "")
    priority = payload.get("priority", "normal")
    if category not in FEEDBACK_CATEGORIES:
        return _error_response("validation_error", "Unsupported feedback category", 400)
    if priority not in FEEDBACK_PRIORITIES:
        return _error_response("validation_error", "Unsupported feedback priority", 400)
    if not isinstance(message, str) or not 20 <= len(message.strip()) <= 2000:
        return _error_response("validation_error", "message must contain 20..2000 characters", 400)
    if not isinstance(page_url, str) or len(page_url) > 300 or (
        page_url and (not page_url.startswith("/") or page_url.startswith("//"))
    ):
        return _error_response("validation_error", "page_url must be an internal path up to 300 characters", 400)
    if not save_feedback(
        request.supabase_access_token, user.id, category, message.strip(), page_url, priority
    ):
        return _unavailable_response("learner-feedback")
    return _private_response(
        "learner-feedback", {"created": True, "status": "new", "priority": priority}, status=201
    )


@require_safe
@require_supabase_user
def learner_today_v1(request):
    """Return one canonical daily plan for browser and separate clients."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    raw_minutes = request.GET.get("minutes", "15")
    if raw_minutes not in {str(value) for value in DAILY_TIME_MODES}:
        return _error_response("validation_error", "minutes must be one of 10, 15, 30", 400)
    plan_minutes = int(raw_minutes)
    user = request.supabase_user
    progress = load_dashboard_progress(
        request.supabase_access_token, user.id, (user.email or "learner").split("@", 1)[0]
    )
    words = load_personal_words(request.supabase_access_token, user.id)
    draft_result = load_latest_lesson_draft_result(request.supabase_access_token, user.id)
    data = _build_today_data(progress, words, draft_result, time_budget_minutes=plan_minutes)
    if data is None:
        return _unavailable_response("learner-today")
    return _private_response("learner-today", data)


def _build_today_data(progress, words, draft_result, *, time_budget_minutes=15):
    """Build the canonical plan from already loaded owner-scoped state."""
    if not progress.available or words is None or not draft_result.available:
        return None
    lesson_rows = tasks()
    plan = build_daily_plan(
        lesson_rows,
        level=progress.level,
        completed_all_time=progress.all_completed_lesson_ids,
        completed_today=progress.completed_lesson_ids,
        personal_words=words,
        today=timezone.localdate(),
        daily_task_limit=progress.daily_goal_lessons,
        recent_completion_results=progress.recent_completion_results,
        time_budget_minutes=time_budget_minutes,
    )
    serialized_tasks = [
        {
            "id": item["id"], "kind": item["kind"], "title": item["title"],
            "description": item.get("description") or "", "minutes": item.get("minutes") or 0,
            "emoji": item.get("emoji") or "", "level": item.get("level") or progress.level,
            "completed": bool(item["completed"]),
            "plan_type": item.get("plan_type", "lesson"),
            "reinforcement_reason": item.get("reinforcement_reason"),
            "skill": item.get("skill"),
            "path": "/dictionary/practice/" if item["kind"] == "dictionary-review" else f"/lesson/{item['id']}/",
            "api_path": "/api/v1/me/sm2/" if item["kind"] == "dictionary-review" else f"/api/v1/lessons/{item['id']}/",
        }
        for item in plan
    ]
    completed_count = sum(item["completed"] for item in serialized_tasks)
    resume = _today_resume(draft_result.draft, lesson_rows, progress.all_completed_lesson_ids)
    return {
        "date": timezone.localdate().isoformat(),
        "level": progress.level,
        "daily_goal_lessons": progress.daily_goal_lessons,
        "time_budget_minutes": time_budget_minutes,
        "estimated_minutes": sum(item.get("minutes") or 5 for item in serialized_tasks),
        "completed_count": completed_count,
        "task_count": len(serialized_tasks),
        "progress_percent": round(completed_count / len(serialized_tasks) * 100) if serialized_tasks else 0,
        "tasks": serialized_tasks,
        "resume": resume,
    }


@require_safe
@require_supabase_user
def learner_bootstrap_v1(request):
    """Return one consistent initial owner-scoped snapshot for native clients."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    user = request.supabase_user
    fallback_name = (user.email or "learner").split("@", 1)[0]
    progress = load_dashboard_progress(
        request.supabase_access_token, user.id, fallback_name
    )
    words = load_personal_words(request.supabase_access_token, user.id)
    draft_result = load_latest_lesson_draft_result(
        request.supabase_access_token, user.id
    )
    today = _build_today_data(progress, words, draft_result)
    if today is None:
        return _unavailable_response("learner-bootstrap")
    return _private_response(
        "learner-bootstrap",
        {
            "profile": {
                "display_name": progress.display_name,
                "level": progress.level,
                "daily_goal_lessons": progress.daily_goal_lessons,
            },
            "progress": {
                "streak_days": progress.streak_days,
                "active_days": progress.active_days,
                "completed_lesson_count": len(progress.all_completed_lesson_ids),
                "week": {
                    "active_days": progress.weekly_active_days,
                    "completed_lessons": progress.weekly_completed_count,
                },
            },
            "today": today,
            "links": {
                "catalog": "/api/v1/catalog/",
                "profile": "/api/v1/me/profile/",
                "history": "/api/v1/me/history/",
                "sm2": "/api/v1/me/sm2/",
                "reading": "/api/v1/reading/",
            },
        },
    )


@require_safe
@require_supabase_user
def learner_achievements_v1(request):
    """Derive stable milestones from current owner-scoped learner state."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    user = request.supabase_user
    fallback_name = (user.email or "learner").split("@", 1)[0]
    progress = load_dashboard_progress(
        request.supabase_access_token, user.id, fallback_name
    )
    words = load_personal_words(request.supabase_access_token, user.id)
    if not progress.available or words is None:
        return _unavailable_response("learner-achievements")
    lesson_ids = {item["id"] for item in tasks()}
    achievements = build_achievements(
        completed_lessons=len(progress.all_completed_lesson_ids & lesson_ids),
        streak_days=progress.streak_days,
        dictionary_count=len(words),
        active_days=progress.active_days,
    )
    items = [
        {
            "id": item.id,
            "icon": item.icon,
            "title": item.title,
            "description": item.description,
            "current": item.current,
            "target": item.target,
            "progress_percent": item.progress_percent,
            "unlocked": item.unlocked,
        }
        for item in achievements
    ]
    return _private_response(
        "learner-achievements",
        {
            "unlocked_count": sum(item["unlocked"] for item in items),
            "achievement_count": len(items),
            "achievements": items,
        },
    )


def _today_resume(draft, lesson_rows, completed_all_time):
    if not isinstance(draft, dict) or draft.get("lesson_id") in completed_all_time:
        return None
    lesson = next((item for item in lesson_rows if item["id"] == draft.get("lesson_id")), None)
    if lesson is None:
        return None
    try:
        step = max(1, int(draft.get("step_index", 0)) + 1)
    except (TypeError, ValueError):
        step = 1
    return {
        "lesson_id": lesson["id"], "kind": lesson["kind"], "title": lesson["title"],
        "step": step, "path": f"/lesson/{lesson['id']}/", "api_path": f"/api/v1/lessons/{lesson['id']}/",
    }


@require_safe
@require_supabase_user
def learner_sm2_v1(request):
    """Expose the authenticated learner's personal SM-2 review queue."""
    words = load_personal_words(request.supabase_access_token, request.supabase_user.id)
    if words is None:
        return _unavailable_response("learner-sm2")

    today = timezone.localdate()
    reviews = [_serialize_review(word, today) for word in words]
    reviews.sort(key=lambda item: (item["next_review_date"] or "9999-12-31", item["id"]))
    return _private_response(
        "learner-sm2",
        {
            "as_of": today.isoformat(),
            "due_count": sum(review["due"] for review in reviews),
            "reviews": reviews,
        },
    )


@csrf_exempt
@require_POST
@require_supabase_user
def learner_sm2_review_v1(request, word_id):
    """Schedule one owner-scoped dictionary card from a native client."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "sm2"):
        return limited
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 512:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    if not isinstance(payload, dict) or set(payload) != {"quality"} or payload["quality"] not in {"again", "hard", "good", "easy"}:
        return _error_response("validation_error", "quality must be again, hard, good, or easy", 400)
    words = load_personal_words(request.supabase_access_token, request.supabase_user.id)
    if words is None:
        return _unavailable_response("learner-sm2-review")
    word = next((item for item in words if str(item.get("id")) == str(word_id)), None)
    if word is None:
        return _error_response("word_not_found", "Owned dictionary word was not found", 404)
    try:
        state = Sm2State(
            ease_factor=float(word.get("ease_factor", 2.5)),
            interval_days=int(word.get("interval_days", 0)),
            repetitions=int(word.get("repetitions", 0)),
        )
    except (TypeError, ValueError):
        return _error_response("upstream_invalid", "Stored review state is invalid", 503)
    now = timezone.now()
    review = sm2_next(state, payload["quality"], now.date())
    if not save_personal_word_review(
        request.supabase_access_token, request.supabase_user.id, str(word_id), review, now.isoformat()
    ):
        return _unavailable_response("learner-sm2-review")
    return _private_response("learner-sm2-review", {
        "word_id": str(word_id), "quality": payload["quality"],
        "ease_factor": review.ease_factor, "interval_days": review.interval_days,
        "repetitions": review.repetitions, "next_review_date": review.next_review_date.isoformat(),
    })


@require_safe
@require_supabase_user
def learner_reading_bookmarks_v1(request):
    bookmarks = load_reading_bookmarks(request.supabase_access_token, request.supabase_user.id)
    if bookmarks is None:
        return _unavailable_response("learner-reading-bookmarks")
    return _private_response("learner-reading-bookmarks", {"reading_text_ids": sorted(bookmarks)})


@require_safe
@require_supabase_user
def native_reading_library_v1(request):
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    level = request.GET.get("level", "").upper()
    query = request.GET.get("q", "").strip()
    try:
        page = int(request.GET.get("page", "1"))
    except (TypeError, ValueError):
        page = 0
    if (level and level not in READING_LEVELS) or len(query) > 120 or not 1 <= page <= 100:
        return _error_response("invalid_filters", "Use level A1..C2, q up to 120 characters, and page 1..100", 400)
    bookmarks = load_reading_bookmarks(request.supabase_access_token, request.supabase_user.id)
    if bookmarks is None:
        return _unavailable_response("native-reading-library")
    filtered = filter_native_readings(reading_texts(), level=level, query=query)
    page_size, start = 20, (page - 1) * 20
    rows = filtered[start:start + page_size + 1]
    items = [
        {**item, "level": item["level"] if item.get("level") in READING_LEVELS else "A1", "saved": item["id"] in bookmarks,
         "path": f"/reading/{item['id']}/", "api_path": f"/api/v1/reading/{item['id']}/"}
        for item in rows[:page_size]
    ]
    return _private_response("native-reading-library", {
        "level": level or None, "query": query, "page": page, "page_size": page_size,
        "has_previous": page > 1, "has_next": len(rows) > page_size, "texts": items,
    })


@require_safe
@require_supabase_user
def native_reading_detail_v1(request, text_id):
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    text = reading_text(text_id)
    if text is None:
        return _error_response("reading_text_not_found", "Active reading text was not found", 404)
    bookmarks = load_reading_bookmarks(request.supabase_access_token, request.supabase_user.id)
    if bookmarks is None:
        return _unavailable_response("native-reading-detail")
    detail = serialize_reading_detail(text, saved=text_id in bookmarks)
    comprehension_id = detail["comprehension_lesson_id"]
    detail["comprehension_api_path"] = (
        f"/api/v1/lessons/{comprehension_id}/" if comprehension_id and task(comprehension_id) else None
    )
    return _private_response("native-reading-detail", {"text": detail})


@csrf_exempt
@require_POST
@require_supabase_user
def native_reading_dictionary_v1(request, text_id):
    """Save only a server-verified glossary lemma from an active text."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "dictionary"):
        return limited
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 512:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    if not isinstance(payload, dict) or set(payload) != {"surface"} or not isinstance(payload["surface"], str) or not payload["surface"].strip() or len(payload["surface"]) > 160:
        return _error_response("validation_error", "Use exactly one non-empty surface string up to 160 characters", 400)
    text = reading_text(text_id)
    if text is None:
        return _error_response("reading_text_not_found", "Active reading text was not found", 404)
    entry = resolve_glossary_entry(text.glossary, payload["surface"])
    if entry is None:
        return _error_response("glossary_entry_not_found", "Surface form was not found in this text glossary", 404)
    surface = entry["surface"].casefold()
    context = next(
        (paragraph.strip()[:500] for paragraph in text.paragraphs if isinstance(paragraph, str) and surface in paragraph.casefold()),
        "",
    )
    if not save_personal_word(
        request.supabase_access_token, request.supabase_user.id,
        entry["lemma"].casefold(), entry["translation"], context, text.id,
    ):
        return _unavailable_response("native-reading-dictionary")
    return _private_response("native-reading-dictionary", {
        "text_id": text.id, "surface": entry["surface"], "word": entry["lemma"].casefold(),
        "translation": entry["translation"], "part_of_speech": entry["part_of_speech"],
    })


@csrf_exempt
@require_http_methods(["DELETE"])
@require_supabase_user
def native_dictionary_word_v1(request, word_id):
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "dictionary"):
        return limited
    if not delete_personal_word(request.supabase_access_token, request.supabase_user.id, str(word_id)):
        return _unavailable_response("native-dictionary-word")
    return _private_response("native-dictionary-word", {"word_id": str(word_id), "deleted": True})


@require_safe
@require_supabase_user
def learner_history_v1(request):
    """Return one bounded owner-scoped completion page for separate clients."""
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    period = request.GET.get("period", "30")
    periods = {"7": 7, "30": 30, "90": 90, "all": None}
    try:
        page = int(request.GET.get("page", "1"))
    except (TypeError, ValueError):
        page = 0
    if period not in periods or not 1 <= page <= 500:
        return _error_response("invalid_pagination", "Use page 1..500 and period 7, 30, 90, or all", 400)
    history = load_completion_history(
        request.supabase_access_token,
        request.supabase_user.id,
        page=page,
        page_size=50,
        days=periods[period],
    )
    if not history.available:
        return _unavailable_response("learner-history")
    return _private_response("learner-history", {
        "period": period,
        "page": history.page,
        "page_size": 50,
        "has_previous": history.has_previous,
        "has_next": history.has_next,
        "completions": list(history.rows),
    })


@require_safe
@require_supabase_user
def learner_latest_lesson_draft_v1(request):
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    result = load_latest_lesson_draft_result(
        request.supabase_access_token, request.supabase_user.id
    )
    if not result.available:
        return _unavailable_response("learner-lesson-draft")
    return _private_response("learner-lesson-draft", {"draft": result.draft})


@csrf_exempt
@require_http_methods(["PUT", "DELETE"])
@require_supabase_user
def learner_lesson_draft_v1(request, lesson_id):
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "draft"):
        return limited
    lesson = task(lesson_id)
    if lesson is None:
        return _error_response("lesson_not_found", "Active lesson was not found", 404)
    token, owner = request.supabase_access_token, request.supabase_user.id
    if request.method == "DELETE":
        if not delete_lesson_draft(token, owner, lesson_id):
            return _unavailable_response("learner-lesson-draft")
        return _private_response("learner-lesson-draft", {"draft": None})
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > 1024:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    if not isinstance(payload, dict) or set(payload) != {"step_index", "score"}:
        return _error_response("validation_error", "Use exactly step_index and score", 400)
    step_index, score = payload["step_index"], payload["score"]
    if isinstance(step_index, bool) or isinstance(score, bool) or not isinstance(step_index, int) or not isinstance(score, int):
        return _error_response("validation_error", "step_index and score must be integers", 400)
    total = _lesson_step_count(lesson_id, lesson["kind"])
    if total < 2 or not (0 < step_index < total) or not (0 <= score <= step_index):
        return _error_response("validation_error", "Draft must describe a valid unfinished step and score", 400)
    if not save_lesson_draft(token, owner, lesson_id, lesson["kind"], step_index, score):
        return _unavailable_response("learner-lesson-draft")
    return _private_response("learner-lesson-draft", {"draft": {
        "lesson_id": lesson_id, "lesson_kind": lesson["kind"],
        "step_index": step_index, "score": score,
    }})


def _lesson_step_count(lesson_id, lesson_kind):
    if lesson_kind in {"words", "review"}:
        return len(flashcards(lesson_id))
    if lesson_kind == "grammar":
        content = grammar(lesson_id)
        return len(content["questions"]) if content else 0
    return len(quiz(lesson_id))


@csrf_exempt
@require_http_methods(["PUT", "DELETE"])
@require_supabase_user
def learner_reading_bookmark_v1(request, text_id):
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "bookmark"):
        return limited
    if reading_text(text_id) is None:
        return _error_response("reading_text_not_found", "Active reading text was not found", 404)
    saved = request.method == "PUT"
    if not set_reading_bookmark(request.supabase_access_token, request.supabase_user.id, text_id, saved):
        return _unavailable_response("learner-reading-bookmark")
    return _private_response("learner-reading-bookmark", {"reading_text_id": text_id, "saved": saved})


@csrf_exempt
@require_POST
@require_supabase_user
def lesson_results_v1(request):
    if not _valid_bearer(request):
        return _error_response("bearer_required", "A valid Bearer token is required", 401)
    if limited := _mutation_rate_limit(request, "result"):
        return limited
    return _store_lesson_result(request)


def _valid_bearer(request):
    scheme, separator, token = request.headers.get("Authorization", "").partition(" ")
    return scheme.lower() == "bearer" and separator == " " and bool(token) and token == request.supabase_access_token


def _mutation_rate_limit(request, action):
    allowed, retry_after = consume_api_mutation(
        request.supabase_access_token, str(request.supabase_user.id), action
    )
    if allowed:
        return None
    response = _error_response("rate_limited", "Too many mutation requests; retry later", 429)
    response["Retry-After"] = str(retry_after)
    return response


@require_POST
@require_supabase_user
def lesson_results_session_v1(request):
    """Store a browser-queued result without exposing its HttpOnly token."""
    if request.headers.get("Authorization"):
        return _error_response(
            "cookie_session_required",
            "Use the browser session without an Authorization header",
            401,
        )
    return _store_lesson_result(request)


def _store_lesson_result(request):
    if request.content_type != "application/json":
        return _error_response("unsupported_media_type", "Content-Type must be application/json", 415)
    if len(request.body) > MAX_REQUEST_BYTES:
        return _error_response("payload_too_large", "Request body is too large", 413)
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error_response("invalid_json", "Request body must be valid JSON", 400)
    try:
        result = validate_lesson_result(payload)
    except LessonResultValidationError as error:
        return _error_response("validation_error", str(error), 400)
    if not Lesson.objects.filter(id=result.lesson_id, is_active=True).exists():
        return _error_response("lesson_not_found", "Active lesson was not found", 404)
    stored = record_lesson_result_event(request.supabase_access_token, result)
    if stored is None:
        return _error_response("upstream_unavailable", "Result could not be stored", 503)
    status = stored.get("status")
    if status == "conflict":
        return _error_response("idempotency_conflict", "event_id already has different data", 409)
    if status not in {"created", "duplicate"}:
        return _error_response("upstream_unavailable", "Unexpected storage response", 503)
    response = JsonResponse(
        {
            "api_version": API_VERSION,
            "meta": {"contract": "lesson-result", "contract_version": "1.0"},
            "data": {"event_id": result.event_id, "status": status},
        },
        status=201 if status == "created" else 200,
    )
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Authorization, Cookie"
    return response


def _serialize_review(word: dict, today: date) -> dict:
    next_review_date = word.get("next_review_date")
    try:
        due = date.fromisoformat(next_review_date) <= today
    except (TypeError, ValueError):
        due = True
        next_review_date = None
    return {
        "id": str(word.get("id") or ""),
        "word": word.get("word") or "",
        "translation": word.get("translation") or "",
        "context": word.get("context") or "",
        "source_text_id": word.get("source_text_id") or "",
        "ease_factor": word.get("ease_factor"),
        "interval_days": word.get("interval_days") or 0,
        "repetitions": word.get("repetitions") or 0,
        "next_review_date": next_review_date,
        "last_reviewed_at": word.get("last_reviewed_at"),
        "due": due,
    }


def _private_response(contract: str, data: dict, *, status: int = 200) -> JsonResponse:
    response = JsonResponse(
        {
            "api_version": API_VERSION,
            "meta": {
                "contract": contract,
                "contract_version": LEARNER_CONTRACT_VERSION,
                "generated_at": timezone.now().isoformat(),
            },
            "data": data,
        },
        status=status,
        json_dumps_params={"ensure_ascii": False},
    )
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Authorization, Cookie"
    return response


def _unavailable_response(contract: str) -> JsonResponse:
    response = JsonResponse(
        {
            "api_version": API_VERSION,
            "meta": {
                "contract": contract,
                "contract_version": LEARNER_CONTRACT_VERSION,
            },
            "error": {
                "code": "upstream_unavailable",
                "detail": "Learner data is temporarily unavailable",
            },
        },
        status=503,
    )
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Authorization, Cookie"
    return response


def _error_response(code: str, detail: str, status: int) -> JsonResponse:
    response = JsonResponse(
        {"api_version": API_VERSION, "error": {"code": code, "detail": detail}},
        status=status,
    )
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Authorization, Cookie"
    return response
