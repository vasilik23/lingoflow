"""Reading library and personal dictionary browser flows."""

import re
import unicodedata
from datetime import date
from urllib.parse import urlencode

from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from polskiflow.auth_views import require_browser_user, select_cefr_level
from polskiflow.content import reading_text, reading_texts, task
from polskiflow.dictionary_store import (
    delete_personal_word,
    load_personal_words,
    save_personal_word,
    save_personal_word_review,
)
from polskiflow.domain.sm2 import DEFAULT_SM2_STATE, Sm2State, sm2_next
from polskiflow.domain.reading_catalog import (
    READING_DURATION_FILTERS,
    filter_reading_texts,
)
from polskiflow.progress_store import load_dashboard_progress, save_lesson_completion
from polskiflow.reading_bookmark_store import load_reading_bookmarks, set_reading_bookmark
from polskiflow.collection_store import load_collection_summaries
from polskiflow.news_feed import CATEGORIES, CATEGORY_IDS, latest_official_news

TOKEN_PATTERN = re.compile(r"([\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ-]+)", re.UNICODE)
REVIEW_QUALITIES = {"again", "hard", "good", "easy"}
PRACTICE_WORD_IDS_SESSION_KEY = "dictionary_practice_word_ids"
PRACTICE_MODE_SESSION_KEY = "dictionary_practice_mode"
PRACTICE_SOURCE_SESSION_KEY = "dictionary_practice_source"
PRACTICE_ANSWER_SESSION_KEY = "dictionary_practice_answer"
PRACTICE_MODES = {"translation", "lemma", "context"}
READING_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
DICTIONARY_QUERY_MAX_LENGTH = 80
DICTIONARY_REVIEW_FILTERS = {"", "due", "upcoming"}


@require_browser_user
def reading_library(request: HttpRequest) -> HttpResponse:
    selected_category = request.GET.get("category", "")
    if selected_category in CATEGORY_IDS:
        return redirect(f"/news/?{urlencode({'category': selected_category})}")
    fallback_name = (request.supabase_user.email or "ученик").split("@", 1)[0]
    dashboard = load_dashboard_progress(
        request.supabase_access_token,
        request.supabase_user.id,
        fallback_name,
    )
    selected_level = select_cefr_level(request, dashboard.level)
    texts = reading_texts()
    for text in texts:
        if text.get("level") not in READING_LEVELS:
            text["level"] = "A1"
    level_texts = [text for text in texts if text["level"] == selected_level]
    topic_options = sorted(
        {
            (text["topic_id"], text["topic_title"])
            for text in level_texts
            if text.get("topic_id")
        },
        key=lambda item: item[1].casefold(),
    )
    filters = {
        "q": request.GET.get("q", "").strip()[:120],
        "topic": request.GET.get("topic", ""),
        "duration": request.GET.get("duration", ""),
    }
    if filters["topic"] not in {item[0] for item in topic_options}:
        filters["topic"] = ""
    if filters["duration"] not in READING_DURATION_FILTERS:
        filters["duration"] = ""
    filtered_texts = filter_reading_texts(
        level_texts,
        query=filters["q"],
        topic_id=filters["topic"],
        duration=filters["duration"],
    )
    bookmarks = load_reading_bookmarks(request.supabase_access_token, request.supabase_user.id)
    saved_only = request.GET.get("saved") == "1"
    for text in filtered_texts:
        text["saved"] = text["id"] in (bookmarks or set())
    if saved_only:
        filtered_texts = [text for text in filtered_texts if text["saved"]]
    preserved_filters = {
        key: value for key, value in filters.items() if value
    }
    level_tabs = [
        {
            "id": level,
            "href": f"?{urlencode({'level': level, **preserved_filters})}#texts-title",
        }
        for level in READING_LEVELS
    ]
    return render(
        request,
        "reading/library.html",
        {
            "texts": filtered_texts,
            "reading_levels": level_tabs,
            "selected_reading_level": selected_level,
            "reading_filters": filters,
            "reading_topic_options": topic_options,
            "reading_result_count": len(filtered_texts),
            "reading_filters_active": any(filters.values()),
            "saved_only": saved_only,
            "bookmarks_available": bookmarks is not None,
        },
    )


@require_browser_user
def news_library(request: HttpRequest) -> HttpResponse:
    selected_category = request.GET.get("category", "")
    if selected_category not in CATEGORY_IDS:
        selected_category = ""
    categories = [
        {
            **category,
            "href": f"?{urlencode({'category': category['id']})}#news-title",
        }
        for category in CATEGORIES
    ]
    return render(
        request,
        "reading/news.html",
        {
            "news_all_href": "?#news-title",
            "news": latest_official_news(category=selected_category or None),
            "news_categories": categories,
            "selected_news_category": selected_category,
        },
    )


@require_browser_user
def reader(request: HttpRequest, text_id: str) -> HttpResponse:
    text = reading_text(text_id)
    if text is None:
        raise Http404
    metadata = text.source_metadata if isinstance(text.source_metadata, dict) else {}
    comprehension_lesson_id = metadata.get("comprehension_lesson_id", "")
    comprehension_task = (
        task(comprehension_lesson_id)
        if isinstance(comprehension_lesson_id, str) and comprehension_lesson_id
        else None
    )
    bookmarks = load_reading_bookmarks(request.supabase_access_token, request.supabase_user.id)
    collections = load_collection_summaries(request.supabase_access_token, request.supabase_user.id)
    return render(
        request,
        "reading/reader.html",
        {
            "text": text,
            "paragraphs": _tokenize(text.paragraphs, text.glossary),
            "comprehension_task": comprehension_task,
            "is_bookmarked": text_id in (bookmarks or set()),
            "bookmarks_available": bookmarks is not None,
            "collection_choices": collections or [],
            "collections_available": collections is not None,
        },
    )


@require_POST
@require_browser_user
def toggle_reading_bookmark(request: HttpRequest, text_id: str) -> HttpResponse:
    if reading_text(text_id) is None:
        raise Http404
    saved = request.POST.get("saved") == "1"
    set_reading_bookmark(request.supabase_access_token, request.supabase_user.id, text_id, saved)
    return redirect("reader", text_id=text_id)


@require_browser_user
def dictionary(request: HttpRequest) -> HttpResponse:
    words = load_personal_words(
        request.supabase_access_token, request.supabase_user.id
    )
    all_words = words or []
    query = request.GET.get("q", "").strip()[:DICTIONARY_QUERY_MAX_LENGTH]
    review_filter = request.GET.get("review", "")
    if review_filter not in DICTIONARY_REVIEW_FILTERS:
        review_filter = ""
    filtered_words = _filter_dictionary_words(
        all_words, query=query, review_filter=review_filter
    )
    return render(
        request,
        "reading/dictionary.html",
        {
            "words": filtered_words,
            "available": words is not None,
            "can_practice": len(all_words) >= 4,
            "needed_words": max(0, 4 - len(all_words)),
            "word_count": len(all_words),
            "result_count": len(filtered_words),
            "dictionary_query": query,
            "review_filter": review_filter,
            "filters_active": bool(query or review_filter),
        },
    )


@require_browser_user
def dictionary_practice(request: HttpRequest) -> HttpResponse:
    words = load_personal_words(
        request.supabase_access_token, request.supabase_user.id
    )
    source_text_id = request.GET.get("source", "").strip()
    if source_text_id and reading_text(source_text_id) is None:
        raise Http404
    mode = request.GET.get("mode", "")
    if mode not in PRACTICE_MODES:
        mode = "lemma" if source_text_id else "translation"
    questions = _practice_questions(
        words or [], source_text_id=source_text_id or None, mode=mode
    )
    request.session[PRACTICE_WORD_IDS_SESSION_KEY] = [
        question["id"] for question in questions
    ]
    request.session[PRACTICE_MODE_SESSION_KEY] = mode
    request.session[PRACTICE_SOURCE_SESSION_KEY] = source_text_id
    request.session.pop(PRACTICE_ANSWER_SESSION_KEY, None)
    source_word_count = (
        sum(word.get("source_text_id") == source_text_id for word in (words or []))
        if source_text_id
        else len(words or [])
    )
    return render(
        request,
        "reading/practice.html",
        {
            "available": words is not None,
            "word_count": len(words or []),
            "source_text_id": source_text_id,
            "source_word_count": source_word_count,
            "mode": mode,
            "mode_urls": {
                item: _practice_url(source_text_id, item)
                for item in ("translation", "lemma", "context")
            },
            "repeat_url": _practice_url(source_text_id, mode),
            "question": questions[0] if questions else None,
            "total": len(questions),
            "index": 0,
            "score": 0,
            "selected": None,
        },
    )


@require_POST
@require_browser_user
def dictionary_practice_step(request: HttpRequest) -> HttpResponse:
    words = load_personal_words(
        request.supabase_access_token, request.supabase_user.id
    )
    session_word_ids = request.session.get(PRACTICE_WORD_IDS_SESSION_KEY)
    mode = request.session.get(PRACTICE_MODE_SESSION_KEY, "translation")
    if mode not in PRACTICE_MODES:
        mode = "translation"
    source_text_id = request.session.get(PRACTICE_SOURCE_SESSION_KEY, "")
    if not isinstance(source_text_id, str):
        source_text_id = ""
    questions = _practice_questions(
        words or [],
        word_ids=session_word_ids if isinstance(session_word_ids, list) else None,
        mode=mode,
    )
    try:
        index = int(request.POST.get("index", "0"))
        score = int(request.POST.get("score", "0"))
    except ValueError:
        return HttpResponseBadRequest("Некорректное состояние тренировки")
    if not questions or not 0 <= index < len(questions) or not 0 <= score <= index:
        return HttpResponseBadRequest("Некорректное состояние тренировки")
    action = request.POST.get("action", "")
    question = questions[index]
    if action == "answer":
        if mode == "context":
            submitted_answer = request.POST.get("answer", "")
            if not submitted_answer.strip():
                return HttpResponseBadRequest("Введите польскую лемму")
            answer_correct = _normalize_typed_answer(
                submitted_answer
            ) == _normalize_typed_answer(question["correct_answer"])
            request.session[PRACTICE_ANSWER_SESSION_KEY] = {
                "index": index,
                "word_id": question["id"],
                "correct": answer_correct,
            }
            context = _practice_context(
                questions,
                index,
                score,
                None,
                answered=True,
                answer_correct=answer_correct,
                submitted_answer=submitted_answer.strip(),
            )
        else:
            try:
                selected = int(request.POST["choice"])
            except (KeyError, ValueError):
                return HttpResponseBadRequest("Выберите ответ")
            if not 0 <= selected < len(question["options"]):
                return HttpResponseBadRequest("Некорректный ответ")
            context = _practice_context(
                questions, index, score, selected, answered=True
            )
    elif action == "next":
        if mode == "context":
            answer_state = request.session.get(PRACTICE_ANSWER_SESSION_KEY)
            if (
                not isinstance(answer_state, dict)
                or answer_state.get("index") != index
                or answer_state.get("word_id") != question["id"]
                or not isinstance(answer_state.get("correct"), bool)
            ):
                return HttpResponseBadRequest("Сначала ответьте")
            answer_correct = answer_state["correct"]
            request.session.pop(PRACTICE_ANSWER_SESSION_KEY, None)
        else:
            try:
                selected = int(request.POST["selected"])
            except (KeyError, ValueError):
                return HttpResponseBadRequest("Сначала ответьте")
            if not 0 <= selected < len(question["options"]):
                return HttpResponseBadRequest("Некорректный ответ")
            answer_correct = selected == question["correct"]
        quality = request.POST.get("quality", "")
        if quality not in REVIEW_QUALITIES:
            return HttpResponseBadRequest("Оцените, насколько легко вспомнилось слово")
        if not answer_correct:
            quality = "again"
        now = timezone.now()
        state = Sm2State(
            ease_factor=float(question.get("ease_factor", 2.5)),
            interval_days=int(question.get("interval_days", 0)),
            repetitions=int(question.get("repetitions", 0)),
        )
        review = sm2_next(state, quality, now.date())
        review_saved = save_personal_word_review(
            request.supabase_access_token,
            request.supabase_user.id,
            question["id"],
            review,
            now.isoformat(),
        )
        next_score = score + answer_correct
        if index + 1 >= len(questions):
            request.session.pop(PRACTICE_WORD_IDS_SESSION_KEY, None)
            request.session.pop(PRACTICE_MODE_SESSION_KEY, None)
            request.session.pop(PRACTICE_SOURCE_SESSION_KEY, None)
            request.session.pop(PRACTICE_ANSWER_SESSION_KEY, None)
            saved = save_lesson_completion(
                request.supabase_access_token,
                request.supabase_user.id,
                "dictionary-practice",
                len(questions),
                next_score,
            )
            return render(
                request,
                "reading/_practice_complete.html",
                {
                    "score": next_score,
                    "total": len(questions),
                    "saved": saved,
                    "review_saved": review_saved,
                    "repeat_url": _practice_url(source_text_id, mode),
                },
            )
        context = _practice_context(questions, index + 1, next_score, None)
        context["review_saved"] = review_saved
    else:
        return HttpResponseBadRequest("Неизвестное действие")
    return render(request, "reading/_practice_question.html", context)


@require_POST
@require_browser_user
def add_dictionary_word(request: HttpRequest, text_id: str) -> HttpResponse:
    text = reading_text(text_id)
    if text is None:
        raise Http404
    surface_word = request.POST.get("word", "").strip().casefold()
    translation = request.POST.get("translation", "").strip()
    context = request.POST.get("context", "").strip()
    entry = _glossary_entries(text.glossary).get(surface_word)
    if (
        not entry
        or translation != entry["translation"]
        or len(context) > 500
    ):
        return HttpResponseBadRequest("Некорректное слово")
    word = entry["lemma"]
    saved = save_personal_word(
        request.supabase_access_token,
        request.supabase_user.id,
        word,
        translation,
        context,
        text.id,
    )
    return render(
        request,
        "reading/_save_status.html",
        {
            "saved": saved,
            "word": word,
            "practice_url": _practice_url(text.id, "lemma"),
        },
    )


@require_POST
@require_browser_user
def remove_dictionary_word(request: HttpRequest, word_id: str) -> HttpResponse:
    deleted = delete_personal_word(
        request.supabase_access_token, request.supabase_user.id, word_id
    )
    if request.headers.get("HX-Request") == "true" and deleted:
        return HttpResponse("")
    return redirect("dictionary")


def _tokenize(paragraphs: list, glossary: dict) -> list[list[dict]]:
    entries = _glossary_entries(glossary)
    result = []
    for paragraph in paragraphs if isinstance(paragraphs, list) else []:
        if not isinstance(paragraph, str):
            continue
        tokens = []
        for token in TOKEN_PATTERN.split(paragraph):
            if token:
                entry = entries.get(token.casefold())
                tokens.append({"text": token, "word": token.casefold(), **(entry or {})})
        result.append(tokens)
    return result


def _glossary_entries(glossary: dict) -> dict[str, dict[str, str]]:
    """Normalize legacy translations and lemma-aware glossary entries."""
    if not isinstance(glossary, dict):
        return {}
    entries = {}
    for surface, value in glossary.items():
        if not isinstance(surface, str) or not surface.strip():
            continue
        if isinstance(value, str):
            translation = value.strip()
            lemma = surface.strip().casefold()
            part_of_speech = ""
        elif isinstance(value, dict):
            translation = value.get("translation", "")
            lemma = value.get("lemma", surface)
            part_of_speech = value.get("part_of_speech", "")
            if not all(isinstance(item, str) for item in (translation, lemma, part_of_speech)):
                continue
            translation = translation.strip()
            lemma = lemma.strip().casefold()
            part_of_speech = part_of_speech.strip()
        else:
            continue
        if translation and lemma:
            entries[surface.strip().casefold()] = {
                "translation": translation,
                "lemma": lemma,
                "part_of_speech": part_of_speech,
            }
    return entries


def _practice_questions(
    words: list[dict],
    limit: int = 10,
    word_ids: list[str] | None = None,
    source_text_id: str | None = None,
    mode: str = "translation",
) -> list[dict]:
    usable = [
        word
        for word in words
        if isinstance(word.get("word"), str)
        and isinstance(word.get("translation"), str)
        and word["word"].strip()
        and word["translation"].strip()
    ]
    answer_key = "word" if mode in {"lemma", "context"} else "translation"
    answers = list(dict.fromkeys(word[answer_key] for word in usable))
    if mode != "context" and len(answers) < 4:
        return []
    if word_ids is None:
        chosen_words = [
            word
            for word in usable
            if (not source_text_id or word.get("source_text_id") == source_text_id)
            and _is_due(word.get("next_review_date"))
        ]
        chosen_words.sort(key=lambda word: word.get("next_review_date") or "")
    else:
        words_by_id = {str(word.get("id", "")): word for word in usable}
        chosen_words = [words_by_id[word_id] for word_id in word_ids if word_id in words_by_id]
    questions = []
    for index, word in enumerate(chosen_words[:limit]):
        correct_answer = word[answer_key]
        options = []
        correct = None
        context_text = word.get("context") or ""
        context_gap = _context_with_gap(context_text, word["word"])
        if mode != "context":
            distractors = [item for item in answers if item != correct_answer][:3]
            if len(distractors) < 3:
                continue
            options = distractors + [correct_answer]
            correct = index % 4
            options[correct], options[-1] = options[-1], options[correct]
        questions.append(
            {
                "id": str(word.get("id", "")),
                "word": word["word"],
                "prompt": (
                    context_gap
                    if mode == "context" and context_gap
                    else word["translation"] if mode in {"lemma", "context"}
                    else word["word"]
                ),
                "instruction": (
                    "Впиши польскую лемму в контекст"
                    if mode == "context" and context_gap
                    else "Впиши польскую лемму"
                    if mode == "context"
                    else "Выбери польскую лемму"
                    if mode == "lemma"
                    else "Выбери перевод"
                ),
                "context": "" if context_gap and mode == "context" else context_text,
                "context_missing": mode == "context" and not context_gap,
                "typed": mode == "context",
                "options": options,
                "correct": correct,
                "correct_answer": correct_answer,
                "ease_factor": word.get("ease_factor", DEFAULT_SM2_STATE.ease_factor),
                "interval_days": word.get("interval_days", DEFAULT_SM2_STATE.interval_days),
                "repetitions": word.get("repetitions", DEFAULT_SM2_STATE.repetitions),
            }
        )
    return questions


def _practice_url(source_text_id: str, mode: str) -> str:
    params = {}
    if source_text_id:
        params["source"] = source_text_id
    if mode != "translation":
        params["mode"] = mode
    query = urlencode(params)
    return f"/dictionary/practice/{'?' + query if query else ''}"


def _is_due(value: object, today: date | None = None) -> bool:
    if value in (None, ""):
        return True
    if not isinstance(value, str):
        return True
    try:
        return date.fromisoformat(value) <= (today or timezone.now().date())
    except ValueError:
        return True


def _filter_dictionary_words(
    words: list[dict], *, query: str = "", review_filter: str = ""
) -> list[dict]:
    """Filter only the already owner-scoped dictionary rows loaded by the store."""

    normalized_query = _normalize_typed_answer(query)
    filtered = []
    for word in words:
        if normalized_query:
            searchable = " ".join(
                str(word.get(field) or "")
                for field in ("word", "translation", "context")
            )
            if normalized_query not in _normalize_typed_answer(searchable):
                continue
        due = _is_due(word.get("next_review_date"))
        if review_filter == "due" and not due:
            continue
        if review_filter == "upcoming" and due:
            continue
        filtered.append(word)
    return filtered


def _normalize_typed_answer(value: str) -> str:
    """Normalize presentation differences while preserving Polish letters."""
    return " ".join(unicodedata.normalize("NFC", value).strip().casefold().split())


def _context_with_gap(context: object, lemma: str) -> str:
    if not isinstance(context, str) or not context.strip():
        return ""
    pattern = re.compile(rf"(?<!\w){re.escape(lemma)}(?!\w)", re.IGNORECASE)
    if not pattern.search(context):
        return ""
    return pattern.sub("_____", context.strip())


def _practice_context(
    questions: list[dict],
    index: int,
    score: int,
    selected: int | None,
    *,
    answered: bool = False,
    answer_correct: bool | None = None,
    submitted_answer: str = "",
) -> dict:
    return {
        "question": questions[index],
        "index": index,
        "score": score,
        "selected": selected,
        "answered": answered,
        "answer_correct": answer_correct,
        "submitted_answer": submitted_answer,
        "total": len(questions),
    }
