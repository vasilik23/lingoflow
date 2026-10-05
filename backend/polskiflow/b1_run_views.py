"""Signed, browser-resumable five-part B1 training run without server history."""

import time
from uuid import uuid4

from django.core import signing
from django.shortcuts import render
from django.utils import timezone
from django.utils.crypto import salted_hmac
from django.views.decorators.http import require_http_methods

from polskiflow.auth_views import require_browser_user
from polskiflow.domain.b1_exam_instructions import B1_INSTRUCTIONS, B1_RUN_LISTENING_INSTRUCTION, B1_RUN_READING_INSTRUCTION, B1_RUN_WRITING_INSTRUCTION
from polskiflow.domain.b1_exam_simulation import B1_SIMULATION_PARTS
from polskiflow.domain.b1_training_content import CONTENT_VERSION, score_training_part, training_questions, training_reading_blocks
from polskiflow.domain.b1_training_writing import training_writing_tasks
from polskiflow.domain.b1_weekly_mock import get_mock_variant, weekly_mock_variant
from polskiflow.practice_preferences import excluded_practice_topics

RUN_SALT = "polskiflow.b1-training-run.v1"
RUN_MAX_AGE = 4 * 60 * 60
BREAK_SECONDS = 120
TRAINING_MINUTES = {"listening": 8, "reading": 22, "grammar": 20, "writing": 35, "speaking": 3}


def _minutes(state, part_id):
    if part_id == "writing" and state.get("content_version", 1) < 4:
        return 15
    if part_id == "reading" and state.get("content_version", 1) < 3:
        return 7
    if part_id == "grammar" and state.get("content_version", 1) < 2:
        return 6
    return TRAINING_MINUTES[part_id]


def _new_state(request):
    variant = weekly_mock_variant(timezone.localdate(), excluded_practice_topics(request))
    return {
        "user_id": request.supabase_user.id, "run_id": str(uuid4()),
        "variant_id": variant.id, "phase": "intro", "step": 0, "results": [],
        "created_at": int(time.time()),
        "content_version": CONTENT_VERSION,
    }


def _finish_part(state, result, now):
    state["results"].append(result)
    state["step"] += 1
    state["phase"] = "report" if state["step"] == len(B1_SIMULATION_PARTS) else "break"
    state["break_until"] = now + BREAK_SECONDS
    state.pop("deadline", None)


@require_browser_user
@require_http_methods(["GET", "POST"])
def b1_training_run(request):
    now = int(time.time())
    state = _new_state(request)
    token = ""
    error = ""
    status = 200
    if request.method == "POST":
        token = request.POST.get("run_token", "")
        try:
            candidate = signing.loads(token, salt=RUN_SALT, max_age=RUN_MAX_AGE)
            if not isinstance(candidate, dict) or candidate.get("user_id") != request.supabase_user.id:
                raise signing.BadSignature
            if not 0 <= now - candidate.get("created_at", 0) < RUN_MAX_AGE:
                raise signing.SignatureExpired
            state = candidate
        except (signing.BadSignature, TypeError, ValueError):
            token = ""
            error, status = "Прогон устарел или недоступен. Начни новый прогон.", 400
        if not error:
            action = request.POST.get("action", "")
            variant = get_mock_variant(state["variant_id"])
            part = B1_SIMULATION_PARTS[state["step"]] if state["step"] < 5 else None
            questions = training_questions(variant, part["id"], state.get("content_version", 1)) if part else ()
            allowed = {"csrfmiddlewaretoken", "run_token", "action"}
            if action in {"finish", "skip"} and state["phase"] == "part":
                allowed |= {f"answer_{question.id}" for question in questions}
                if part["mode"] == "self_review":
                    allowed.add("reviewed")
            if set(request.POST) - allowed or any(len(request.POST.getlist(key)) != 1 for key in request.POST):
                error, status = "Форма содержит неизвестные или повторные поля.", 400
            elif action == "resume":
                pass  # Restore only the signed state, never submitted draft text.
            elif action == "start" and state["phase"] in {"intro", "break"}:
                if state["phase"] == "break" and now < state["break_until"]:
                    error, status = "Учебный перерыв ещё не закончился.", 400
                else:
                    state["phase"] = "part"
                    state["deadline"] = now + _minutes(state, part["id"]) * 60
                    token = ""
            elif action == "skip" and state["phase"] == "part":
                _finish_part(state, {"id": part["id"], "status": "skipped"}, now)
                token = ""
            elif action == "finish" and state["phase"] == "part":
                if now >= state["deadline"]:
                    error, status = "Время части истекло. Отметь её как пропущенную и продолжи.", 400
                elif part["mode"] == "objective":
                    try:
                        answers = {question.id: int(request.POST[f"answer_{question.id}"]) for question in questions}
                        score = score_training_part(variant, part["id"], answers, state.get("content_version", 1))
                    except (KeyError, TypeError, ValueError):
                        error, status = "Ответь на все вопросы этой части.", 400
                    else:
                        _finish_part(state, {"id": part["id"], "status": "scored", **{
                            key: score[key] for key in ("correct", "total", "percent")
                        }}, now)
                        token = ""
                elif request.POST.get("reviewed") != "on":
                    error, status = "Подтверди самопроверку или пропусти часть.", 400
                else:
                    _finish_part(state, {"id": part["id"], "status": "self_review"}, now)
                    token = ""
            else:
                error, status = "Это действие сейчас недоступно.", 400
    variant = get_mock_variant(state["variant_id"])
    part = B1_SIMULATION_PARTS[state["step"]] if state["step"] < 5 else None
    token = token or signing.dumps(state, salt=RUN_SALT)
    report = tuple({**part_info, **result} for part_info, result in zip(B1_SIMULATION_PARTS, state["results"]))
    instruction = B1_INSTRUCTIONS.get(part["id"]) if part else None
    if part and part["id"] == "listening":
        instruction = B1_RUN_LISTENING_INSTRUCTION
    elif part and part["id"] == "reading" and state.get("content_version", 1) >= 3:
        instruction = B1_RUN_READING_INSTRUCTION
    elif part and part["id"] == "writing" and state.get("content_version", 1) >= 4:
        instruction = B1_RUN_WRITING_INSTRUCTION
    response = render(request, "b1_training_run.html", {
        "state": state, "variant": variant, "part": part,
        "questions": training_questions(variant, part["id"], state.get("content_version", 1)) if part else (),
        "reading_blocks": training_reading_blocks(variant, state.get("content_version", 1)) if part and part["id"] == "reading" else (),
        "writing_tasks": training_writing_tasks(variant, state.get("content_version", 1)) if part and part["id"] == "writing" else (),
        "instruction": instruction,
        "run_token": token, "error": error, "report": report,
        "timer_seconds": max(0, state.get("deadline", state.get("break_until", now)) - now),
        "run_namespace": salted_hmac(RUN_SALT, request.supabase_user.id).hexdigest()[:32],
        "fresh": request.method == "GET", "discard_draft": bool(error and not request.POST.get("run_token") == token),
        "normalize_navigation": request.method == "POST" and request.POST.get("action") != "resume" and not error,
        "parts": tuple({**item, "training_minutes": _minutes(state, item["id"]), "question_count": len(training_questions(variant, item["id"], state.get("content_version", 1)))} for item in B1_SIMULATION_PARTS),
    }, status=status)
    response["Cache-Control"] = "private, no-store"
    return response
