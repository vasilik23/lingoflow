import time
from uuid import UUID, uuid4

from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.http import require_http_methods

from polskiflow.auth_views import require_browser_user
from polskiflow.b1_mock_store import load_b1_mock_attempts, save_b1_mock_attempt
from polskiflow.b1_section_store import load_b1_section_attempts, save_b1_section_attempt
from polskiflow.domain.b1_exam_instructions import B1_INSTRUCTIONS
from polskiflow.domain.b1_exam_simulation import (
    B1_SIMULATION_PARTS,
    get_simulation_part,
    score_simulation_part,
    simulation_questions,
    simulation_timing,
)
from polskiflow.domain.b1_weekly_mock import get_mock_variant, score_mock_answers, weekly_mock_variant
from polskiflow.practice_preferences import excluded_practice_topics

ATTEMPT_SALT = "polskiflow.b1-weekly-mock"
ATTEMPT_MAX_AGE_SECONDS = 20 * 60
SIMULATION_SALT = "polskiflow.b1-exam-simulation"
SIMULATION_MAX_AGE_SECONDS = 90 * 60


def _attempt_token(user_id: str, variant_id: str, attempt_id: str | None = None) -> str:
    return signing.dumps({
        "user_id": user_id,
        "variant_id": variant_id,
        "attempt_id": attempt_id or str(uuid4()),
    }, salt=ATTEMPT_SALT)


def _token_started_at(token: str) -> int:
    # Read the timestamp only after signature verification for scoring.
    # Rendering an invalid token must still return the existing form error.
    try:
        return signing.b62_decode(token.rsplit(":", 2)[1])
    except (ValueError, IndexError):
        return int(time.time())


@require_browser_user
@require_http_methods(["GET", "POST"])
def b1_weekly_mock(request: HttpRequest) -> HttpResponse:
    result = None
    error = None
    status = 200
    saved = None
    variant = weekly_mock_variant(timezone.localdate(), excluded_practice_topics(request))
    token = _attempt_token(request.supabase_user.id, variant.id)
    if request.method == "POST":
        token = request.POST.get("attempt_token", "")
        try:
            payload = signing.loads(token, salt=ATTEMPT_SALT, max_age=ATTEMPT_MAX_AGE_SECONDS)
            if not isinstance(payload, dict) or payload.get("user_id") != request.supabase_user.id:
                raise BadSignature
            variant = get_mock_variant(payload.get("variant_id", ""))
            if variant is None:
                raise BadSignature
            attempt_id = str(UUID(payload.get("attempt_id", "")))
            allowed = {"csrfmiddlewaretoken", "attempt_token", *(f"answer_{item.id}" for item in variant.questions)}
            if request.POST.get("resume") == "1" and set(request.POST) <= {"csrfmiddlewaretoken", "attempt_token", "resume"}:
                pass  # Restore the signed variant without scoring or writing history.
            elif set(request.POST) - allowed or any(len(values) != 1 for _, values in request.POST.lists()):
                error, status = "Форма содержит неизвестные поля. Начни попытку заново.", 400
            else:
                timed_out = time.time() >= _token_started_at(token) + 15 * 60
                answers = {item.id: int(request.POST[f"answer_{item.id}"]) for item in variant.questions if f"answer_{item.id}" in request.POST}
                result = score_mock_answers(answers, variant, allow_missing=timed_out)
                result.update(timed_out=timed_out, unanswered=result.get("unanswered", 0), incorrect=result.get("incorrect", result["total"] - result["correct"]))
                saved = save_b1_mock_attempt(
                    request.supabase_access_token,
                    request.supabase_user.id,
                    attempt_id,
                    result,
                )
        except SignatureExpired:
            error, status = "Время попытки истекло. Начни новый модуль.", 400
        except (BadSignature, KeyError, TypeError, ValueError):
            error, status = "Ответь на все проверяемые вопросы и попробуй снова.", 400
    history = load_b1_mock_attempts(
        request.supabase_access_token, request.supabase_user.id
    )
    return render(request, "b1_weekly_mock.html", {
        "variant": variant,
        "instructions": B1_INSTRUCTIONS,
        "questions": variant.questions,
        "listening_transcript": variant.listening_transcript,
        "reading_text": variant.reading_text,
        "attempt_token": token,
        "attempt_started_at_ms": _token_started_at(token) * 1000,
        "duration_seconds": 15 * 60,
        "result": result,
        "saved": saved,
        "history": history,
        "error": error,
        "mock_storage_namespace": salted_hmac(
            "polskiflow.b1-weekly-mock-browser", request.supabase_user.id,
        ).hexdigest()[:32],
    }, status=status)


@require_browser_user
@require_http_methods(["GET", "POST"])
def b1_exam_simulation(request: HttpRequest) -> HttpResponse:
    """Run one timed exam-shaped section with stateless objective feedback."""
    part_id = request.GET.get("part", "") if request.method == "GET" else ""
    part = get_simulation_part(part_id)
    timing_mode = "full" if request.GET.get("timing") == "full" else "short"
    variant = weekly_mock_variant(timezone.localdate(), excluded_practice_topics(request))
    result = None
    error = None
    status = 200
    token = ""
    saved = None
    if request.method == "POST":
        token = request.POST.get("simulation_token", "")
        try:
            payload = signing.loads(
                token, salt=SIMULATION_SALT, max_age=SIMULATION_MAX_AGE_SECONDS
            )
            if not isinstance(payload, dict) or payload.get("user_id") != request.supabase_user.id:
                raise BadSignature
            part = get_simulation_part(payload.get("part_id", ""))
            variant = get_mock_variant(payload.get("variant_id", ""))
            if part is None or variant is None or part["mode"] != "objective":
                raise BadSignature
            candidate_timing = payload.get("timing_mode", "full")
            simulation_timing(variant, part, candidate_timing)
            timing_mode = candidate_timing
            attempt_id = str(UUID(payload.get("attempt_id", "")))
            questions = simulation_questions(variant, part["id"])
            allowed = {"csrfmiddlewaretoken", "simulation_token", *(f"answer_{item.id}" for item in questions)}
            if set(request.POST) - allowed or any(len(values) != 1 for _, values in request.POST.lists()):
                error, status = "Форма содержит неизвестные поля. Начни часть заново.", 400
            else:
                timed_out = time.time() >= _token_started_at(token) + simulation_timing(variant, part, timing_mode)["duration_seconds"]
                answers = {item.id: int(request.POST[f"answer_{item.id}"]) for item in questions if f"answer_{item.id}" in request.POST}
                result = score_simulation_part(variant, part["id"], answers, allow_missing=timed_out)
                result.update(timed_out=timed_out, unanswered=result.get("unanswered", 0), incorrect=result.get("incorrect", result["total"] - result["correct"]))
                saved = save_b1_section_attempt(
                    request.supabase_access_token,
                    request.supabase_user.id,
                    attempt_id,
                    variant.id,
                    result,
                )
        except SignatureExpired:
            error, status = "Время этой части истекло. Начни новую попытку.", 400
        except (BadSignature, KeyError, TypeError, ValueError):
            error, status = "Ответь на все вопросы выбранной части и попробуй снова.", 400
    elif part is not None:
        token = signing.dumps({
            "user_id": request.supabase_user.id,
            "variant_id": variant.id,
            "part_id": part["id"],
            "timing_mode": simulation_timing(variant, part, timing_mode)["timing_mode"],
            "attempt_id": str(uuid4()),
        }, salt=SIMULATION_SALT)
    questions = simulation_questions(variant, part["id"]) if part else ()
    parts = tuple({
        **item,
        "question_count": len(simulation_questions(variant, item["id"])),
        **simulation_timing(variant, item),
    } for item in B1_SIMULATION_PARTS)
    history = load_b1_section_attempts(
        request.supabase_access_token, request.supabase_user.id
    )
    return render(request, "b1_exam_simulation.html", {
        "parts": parts,
        "part": part,
        "instruction": B1_INSTRUCTIONS.get(part["id"]) if part else None,
        "variant": variant,
        "questions": questions,
        "question_count": len(questions),
        "simulation_token": token,
        "attempt_started_at_ms": _token_started_at(token) * 1000,
        **(simulation_timing(variant, part, timing_mode) if part else {}),
        "result": result,
        "saved": saved,
        "history": history,
        "error": error,
        "simulation_storage_namespace": salted_hmac(
            "polskiflow.b1-exam-simulation-browser",
            request.supabase_user.id,
        ).hexdigest()[:32],
    }, status=status)
