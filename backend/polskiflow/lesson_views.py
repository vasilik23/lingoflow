"""Server-rendered lesson flows enhanced with HTMX."""

import json
import random
import uuid
from datetime import datetime, timezone

from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.utils.translation import gettext
from django.shortcuts import redirect, render
from django.utils.crypto import salted_hmac
from django.views.decorators.http import require_POST

from polskiflow.auth_views import require_browser_user
from polskiflow.content import flashcards, grammar, lesson_navigation, quiz, task
from polskiflow.progress_store import save_lesson_completion_result
from polskiflow.lesson_draft_store import delete_lesson_draft, load_lesson_draft, save_lesson_draft
from polskiflow.lesson_bookmark_store import load_lesson_bookmarks
from polskiflow.lesson_note_store import load_lesson_note, save_lesson_note
from polskiflow.domain.lesson_state import InvalidLessonState, load_lesson_state, sign_lesson_state
from polskiflow.mistake_store import set_mistake
from polskiflow.collection_store import load_collection_summaries


# Expansion is release-gated by a successful offline -> online recovery smoke
# in a production-like Preview environment. Keep this explicit so a new lesson
# cannot silently join the persisted browser queue through a broad kind check.
OFFLINE_RESULT_QUEUE_LESSON_IDS = frozenset({"words", "grammar", "review", "quiz"})


@require_browser_user
def lesson(request: HttpRequest, lesson_id: str) -> HttpResponse:
    lesson_task = task(lesson_id)
    if lesson_task is None:
        raise Http404
    lesson_kind = lesson_task["kind"]
    draft = load_lesson_draft(request.supabase_access_token, request.supabase_user.id, lesson_id)
    index, score = _valid_draft_state(draft, lesson_id, lesson_kind)
    context = _lesson_page_context(
        request, lesson_task, lesson_id, lesson_kind, {"resume_notice": index > 0}
    )
    if lesson_kind in {"words", "review"}:
        context.update(_flashcard_context(lesson_id, lesson_kind, index, score, False))
    elif lesson_kind == "grammar":
        if index:
            context.update(_question_context(lesson_id, lesson_kind, index, score, None))
            context["resume_practice"] = True
        else:
            context["grammar"] = grammar(lesson_id)
    else:
        context.update(_question_context(lesson_id, lesson_kind, index, score, None))
    context["lesson_state"] = sign_lesson_state(
        request.supabase_user.id, lesson_id, lesson_kind, index, score
    )
    return render(request, "lessons/page.html", context)


@require_POST
@require_browser_user
def lesson_note(request: HttpRequest, lesson_id: str) -> HttpResponse:
    if task(lesson_id) is None:
        raise Http404
    body = "" if request.POST.get("action") == "delete" else request.POST.get("body", "").strip()
    if len(body) > 2000:
        return HttpResponseBadRequest(gettext("Заметка не может быть длиннее 2000 символов"))
    saved = save_lesson_note(
        request.supabase_access_token, request.supabase_user.id, lesson_id, body
    )
    status = "saved" if saved and body else "deleted" if saved else "error"
    return redirect(f"/lesson/{lesson_id}/?note={status}#lesson-note")


@require_POST
@require_browser_user
def lesson_step(request: HttpRequest, lesson_id: str) -> HttpResponse:
    lesson_task = task(lesson_id)
    if lesson_task is None:
        raise Http404
    lesson_kind = lesson_task["kind"]
    try:
        state = load_lesson_state(
            request.POST.get("state", ""), request.supabase_user.id, lesson_id, lesson_kind
        )
    except InvalidLessonState:
        return HttpResponseBadRequest(gettext("Некорректное состояние урока"))
    index, score = state.index, state.score
    action = request.POST.get("action", "")

    if lesson_kind in {"words", "review"}:
        cards = _lesson_flashcards(lesson_id, lesson_kind)
        if not 0 <= index < len(cards) or not 0 <= score <= index:
            return HttpResponseBadRequest(gettext("Некорректное состояние урока"))
        if action == "reveal":
            context = _flashcard_context(lesson_id, lesson_kind, index, score, True)
        elif action in {"again", "know"}:
            next_score = score + (action == "know")
            if action == "again":
                context = _flashcard_context(lesson_id, lesson_kind, index, score, False)
            elif index + 1 >= len(cards):
                return _complete(request, lesson_id, next_score, len(cards))
            else:
                save_lesson_draft(request.supabase_access_token, request.supabase_user.id, lesson_id, lesson_kind, index + 1, next_score)
                context = _flashcard_context(
                    lesson_id, lesson_kind, index + 1, next_score, False
                )
        else:
            return HttpResponseBadRequest(gettext("Неизвестное действие"))
        return _render_step(request, "lessons/_flashcard.html", context, lesson_id, lesson_kind)

    grammar_content = grammar(lesson_id)
    questions = (
        grammar_content["questions"]
        if lesson_kind == "grammar" and grammar_content
        else quiz(lesson_id)
    )
    max_score = index + (state.phase == "answered")
    if not 0 <= index < len(questions) or not 0 <= score <= max_score:
        return HttpResponseBadRequest(gettext("Некорректное состояние урока"))
    if action == "start" and lesson_kind == "grammar":
        context = _question_context(lesson_id, lesson_kind, 0, 0, None)
    elif action == "answer":
        if state.phase != "ready":
            return HttpResponseBadRequest(gettext("Ответ уже проверен"))
        if _is_sentence_builder(questions[index], lesson_kind):
            answer_order = _validated_builder_order(
                request.POST.get("answer_order", ""), questions[index], lesson_id, index
            )
            if answer_order is None:
                return HttpResponseBadRequest(gettext("Составьте предложение из всех слов"))
            is_correct = _builder_is_correct(answer_order, questions[index], lesson_id, index)
            set_mistake(request.supabase_access_token, request.supabase_user.id, lesson_id, index, not is_correct)
            context = _question_context(lesson_id, lesson_kind, index, score + is_correct, None, answer_order)
            context["state_phase"] = "answered"
            return _render_step(request, "lessons/_question.html", context, lesson_id, lesson_kind)
        try:
            selected = int(request.POST["choice"])
        except (KeyError, ValueError):
            return HttpResponseBadRequest(gettext("Выберите ответ"))
        if not 0 <= selected < len(questions[index]["options"]):
            return HttpResponseBadRequest(gettext("Некорректный ответ"))
        is_correct = selected == questions[index]["correct"]
        set_mistake(request.supabase_access_token, request.supabase_user.id, lesson_id, index, not is_correct)
        context = _question_context(
            lesson_id, lesson_kind, index,
            score + is_correct, selected,
        )
        context["state_phase"] = "answered"
    elif action == "next":
        if state.phase != "answered":
            return HttpResponseBadRequest(gettext("Сначала ответьте"))
        if _is_sentence_builder(questions[index], lesson_kind):
            answer_order = _validated_builder_order(
                request.POST.get("answer_order", ""), questions[index], lesson_id, index
            )
            if answer_order is None:
                return HttpResponseBadRequest(gettext("Некорректный ответ"))
            next_score = score
            if index + 1 >= len(questions):
                return _complete(request, lesson_id, next_score, len(questions))
            save_lesson_draft(request.supabase_access_token, request.supabase_user.id, lesson_id, lesson_kind, index + 1, next_score)
            context = _question_context(
                lesson_id, lesson_kind, index + 1, next_score, None
            )
            return _render_step(request, "lessons/_question.html", context, lesson_id, lesson_kind)
        next_score = score
        if index + 1 >= len(questions):
            return _complete(request, lesson_id, next_score, len(questions))
        save_lesson_draft(request.supabase_access_token, request.supabase_user.id, lesson_id, lesson_kind, index + 1, next_score)
        context = _question_context(
            lesson_id, lesson_kind, index + 1, next_score, None
        )
    else:
        return HttpResponseBadRequest(gettext("Неизвестное действие"))
    return _render_step(request, "lessons/_question.html", context, lesson_id, lesson_kind)


def _render_step(request, template, context, lesson_id, lesson_kind):
    context["lesson_state"] = sign_lesson_state(
        request.supabase_user.id, lesson_id, lesson_kind, context["index"], context["score"],
        context.get("state_phase", "ready"),
    )
    if request.headers.get("HX-Request") == "true":
        return render(request, template, context)
    lesson_task = task(lesson_id)
    page_context = _lesson_page_context(
        request,
        lesson_task,
        lesson_id,
        lesson_kind,
        {**context, "resume_practice": lesson_kind == "grammar"},
    )
    return render(request, "lessons/page.html", page_context)


def _lesson_page_context(request, lesson_task, lesson_id, lesson_kind, context):
    """Build the full page shell for initial and non-HTMX lesson requests."""
    bookmarks = load_lesson_bookmarks(
        request.supabase_access_token, request.supabase_user.id
    )
    note = load_lesson_note(
        request.supabase_access_token, request.supabase_user.id, lesson_id
    )
    collections = load_collection_summaries(
        request.supabase_access_token, request.supabase_user.id
    )
    return {
        "task": lesson_task,
        "lesson_id": lesson_id,
        "lesson_kind": lesson_kind,
        "is_bookmarked": lesson_id in (bookmarks or set()),
        "lesson_bookmarks_available": bookmarks is not None,
        "lesson_note": note,
        "collection_choices": collections or [],
        "collections_available": collections is not None,
        **context,
    }


def _lesson_flashcards(lesson_id: str, lesson_kind: str) -> list[dict]:
    return flashcards(lesson_id)


def _flashcard_context(
    lesson_id: str,
    lesson_kind: str,
    index: int,
    score: int,
    revealed: bool,
) -> dict:
    cards = _lesson_flashcards(lesson_id, lesson_kind)
    if not cards:
        raise Http404
    return {
        "lesson_id": lesson_id,
        "lesson_kind": lesson_kind,
        "card": cards[index],
        "index": index,
        "score": score,
        "revealed": revealed,
        "total": len(cards),
    }


def _question_context(
    lesson_id: str,
    lesson_kind: str,
    index: int,
    score: int,
    selected: int | None,
    builder_answer: list[int] | None = None,
) -> dict:
    grammar_content = grammar(lesson_id)
    questions = (
        grammar_content["questions"]
        if lesson_kind == "grammar" and grammar_content
        else quiz(lesson_id)
    )
    if not questions:
        raise Http404
    context = {
        "lesson_id": lesson_id,
        "lesson_kind": lesson_kind,
        "question": questions[index],
        "index": index,
        "score": score,
        "selected": selected,
        "total": len(questions),
    }
    if _is_sentence_builder(questions[index], lesson_kind):
        tokens = _builder_tokens(questions[index], lesson_id, index)
        context.update(
            {
                "sentence_builder": True,
                "builder_tokens": tokens,
                "builder_answer": builder_answer,
                "builder_answer_json": json.dumps(builder_answer or []),
                "builder_answer_words": (
                    [tokens[token_index] for token_index in builder_answer]
                    if builder_answer is not None
                    else []
                ),
                "builder_correct": (
                    _builder_is_correct(builder_answer, questions[index], lesson_id, index)
                    if builder_answer is not None
                    else False
                ),
                "builder_correct_sentence": questions[index]["options"][questions[index]["correct"]],
            }
        )
    return context


def _is_sentence_builder(question: dict, lesson_kind: str) -> bool:
    """Use sentence assembly for grammar answers that are complete phrases."""
    if lesson_kind != "grammar":
        return False
    try:
        answer = question["options"][question["correct"]]
    except (IndexError, KeyError, TypeError):
        return False
    return isinstance(answer, str) and len(answer.split()) >= 4


def _valid_draft_state(draft, lesson_id, lesson_kind):
    if not isinstance(draft, dict) or draft.get("lesson_kind") != lesson_kind:
        return 0, 0
    try:
        index, score = int(draft["step_index"]), int(draft["score"])
    except (KeyError, TypeError, ValueError):
        return 0, 0
    total = len(_lesson_flashcards(lesson_id, lesson_kind)) if lesson_kind in {"words", "review"} else len((grammar(lesson_id) or {}).get("questions", [])) if lesson_kind == "grammar" else len(quiz(lesson_id))
    return (index, score) if 0 < index < total and 0 <= score <= index else (0, 0)


def _builder_tokens(question: dict, lesson_id: str, index: int) -> list[str]:
    answer = question["options"][question["correct"]]
    tokens = answer.split()
    shuffled = list(tokens)
    random.Random(f"{lesson_id}:{index}:{answer}").shuffle(shuffled)
    if shuffled == tokens and len(shuffled) > 1:
        shuffled = shuffled[1:] + shuffled[:1]
    return shuffled


def _validated_builder_order(
    raw_order: str, question: dict, lesson_id: str, index: int
) -> list[int] | None:
    if len(raw_order) > 1024:
        return None
    try:
        order = json.loads(raw_order)
    except (TypeError, json.JSONDecodeError):
        return None
    tokens = _builder_tokens(question, lesson_id, index)
    if (
        not isinstance(order, list)
        or any(type(item) is not int for item in order)
        or sorted(order) != list(range(len(tokens)))
    ):
        return None
    return order


def _builder_is_correct(
    order: list[int], question: dict, lesson_id: str, index: int
) -> bool:
    tokens = _builder_tokens(question, lesson_id, index)
    assembled = " ".join(tokens[token_index] for token_index in order)
    correct = question["options"][question["correct"]]
    return assembled == correct


def _complete(request: HttpRequest, lesson_id: str, score: int, total: int) -> HttpResponse:
    save_result = save_lesson_completion_result(
        request.supabase_access_token,
        request.supabase_user.id,
        lesson_id,
        total,
        score,
    )
    delete_lesson_draft(request.supabase_access_token, request.supabase_user.id, lesson_id)
    context = {
        "score": score,
        "total": total,
        "saved": save_result.saved,
        "lesson_navigation": lesson_navigation(lesson_id),
    }
    # Start with one narrowly scoped flow. The browser receives an opaque,
    # stable namespace and an immutable result, never identity or auth tokens.
    if lesson_id in OFFLINE_RESULT_QUEUE_LESSON_IDS and save_result.retryable:
        completed_at = datetime.now(timezone.utc)
        context.update(
            {
                "offline_queue_namespace": salted_hmac(
                    "polskiflow.result-queue", request.supabase_user.id
                ).hexdigest()[:32],
                "offline_result_json": json.dumps(
                    {
                        "event_id": str(uuid.uuid4()),
                        "lesson_id": lesson_id,
                        "plan_date": completed_at.date().isoformat(),
                        "completed_at": completed_at.isoformat().replace("+00:00", "Z"),
                        "cards_total": total,
                        "cards_known": score,
                        "contract_version": "1.0",
                    },
                    separators=(",", ":"),
                ),
            }
        )
    template = (
        "lessons/_complete.html"
        if request.headers.get("HX-Request") == "true"
        else "lessons/complete_page.html"
    )
    return render(request, template, context)
