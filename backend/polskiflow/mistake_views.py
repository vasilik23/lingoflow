from urllib.parse import urlencode
from django.urls import reverse
from django.utils.translation import gettext

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from polskiflow.auth_views import require_browser_user
from polskiflow.content import tasks, task
from polskiflow.domain.lesson_feedback_hint import feedback_hint
from polskiflow.domain.mistake_review_focus import FOCUS_ID_BY_PROMPT, REVIEW_FOCUS
from polskiflow.learning.models import Question
from polskiflow.mistake_store import load_mistakes
from polskiflow.mistake_store import set_mistake
from polskiflow.domain.mistake_practice import InvalidMistakePracticeState, load_mistake, sign_mistake


@require_browser_user
@require_GET
def mistake_notebook(request: HttpRequest) -> HttpResponse:
    rows = load_mistakes(request.supabase_access_token, request.supabase_user.id)
    lesson_map = {item["id"]: item for item in tasks()}
    questions = {
        (row.lesson_id, row.position): row.prompt
        for row in Question.objects.filter(is_active=True).only("lesson_id", "position", "prompt")
    }
    groups = {}
    focus_counts = {}
    for row in rows or []:
        lesson_id, position = row.get("lesson_id"), row.get("question_position")
        lesson = lesson_map.get(lesson_id)
        if lesson and type(position) is int and (lesson_id, position) in questions:
            group = groups.setdefault(lesson_id, {
                "lesson_id": lesson_id, "title": lesson["plan_title"],
                "emoji": lesson["emoji"], "level": lesson["level"], "questions": [],
            })
            prompt = questions[(lesson_id, position)]
            focus_id = FOCUS_ID_BY_PROMPT.get(prompt)
            focus = None
            if focus_id:
                focus, _ = REVIEW_FOCUS[focus_id]
                focus_counts[focus_id] = focus_counts.get(focus_id, 0) + 1
            group["questions"].append({"prompt": prompt, "focus": focus})
    return render(request, "mistakes.html", {
        "mistake_groups": list(groups.values()),
        "focus_groups": [
            {"id": key, "title": REVIEW_FOCUS[key][0], "count": count}
            for key, count in focus_counts.items()
        ],
        "mistake_count": sum(len(group["questions"]) for group in groups.values()),
        "mistakes_available": rows is not None,
    })


@require_browser_user
@require_http_methods(["GET", "POST"])
def mistake_practice(request: HttpRequest) -> HttpResponse:
    selected_lesson = request.GET.get('lesson', '')
    focus_ids = request.GET.getlist('focus')
    if focus_ids and (selected_lesson or len(focus_ids) != 1 or focus_ids[0] not in REVIEW_FOCUS):
        return HttpResponseBadRequest(gettext('Некорректная тренировка урока'))
    focus_id = focus_ids[0] if focus_ids else None
    focus_title, focus_prompts = REVIEW_FOCUS[focus_id] if focus_id else (None, ())
    if len(request.GET.getlist('lesson')) > 1 or (selected_lesson and task(selected_lesson) is None):
        return HttpResponseBadRequest(gettext('Некорректная тренировка урока'))
    from_notebook = request.GET.get('from') == 'notebook' or bool(focus_id)
    from_today = not selected_lesson and request.GET.get('from') == 'today'
    query = {'lesson': selected_lesson} if selected_lesson else {}
    if focus_id:
        query['focus'] = focus_id
    if from_notebook and selected_lesson:
        query['from'] = 'notebook'
    if from_today:
        query['from'] = 'today'
    repeat_url = reverse('mistake-practice') + ('?' + urlencode(query) if query else '')
    scope = {'selected_lesson': selected_lesson, 'repeat_url': repeat_url,
             'return_to_lesson': bool(selected_lesson and not from_notebook),
             'return_to_notebook': not from_today and bool(focus_id or selected_lesson and from_notebook),
             'return_to_today': from_today, 'focus_title': focus_title}
    rows = load_mistakes(request.supabase_access_token, request.supabase_user.id)
    if rows is None:
        return _practice_response(request, {**scope, "available": False}, status=503)
    owned_list = [
        (row.get("lesson_id"), row.get("question_position"))
        for row in rows if isinstance(row, dict) and isinstance(row.get("lesson_id"), str)
        and type(row.get("question_position")) is int and row["question_position"] >= 0
        and (not selected_lesson or row["lesson_id"] == selected_lesson)
    ]
    available_questions = Question.objects.filter(is_active=True).select_related("lesson__topic__course")
    if focus_id:
        available_questions = available_questions.filter(
            prompt__in=focus_prompts, lesson__is_active=True,
            lesson__topic__is_active=True, lesson__topic__course__is_active=True,
        )
        matching = set(available_questions.values_list("lesson_id", "position"))
        owned_list = [key for key in owned_list if key in matching]
    owned = set(owned_list)
    result = None
    current = None
    if request.method == "POST":
        try:
            state = load_mistake(request.POST.get("state", ""), request.supabase_user.id)
            selected = int(request.POST.get("choice", ""))
        except (InvalidMistakePracticeState, TypeError, ValueError):
            return HttpResponseBadRequest("Некорректное состояние тренировки")
        if (state.lesson_id, state.position) not in owned:
            return HttpResponseBadRequest("Задание больше не находится в списке ошибок")
        current = available_questions.filter(lesson_id=state.lesson_id, position=state.position).first()
        if current is None or not 0 <= selected < len(current.options):
            return HttpResponseBadRequest("Некорректный ответ")
        correct = selected == current.correct
        saved = set_mistake(request.supabase_access_token, request.supabase_user.id, state.lesson_id, state.position, not correct)
        result = {"correct": correct, "saved": bool(saved), "selected": selected, "correct_answer": current.options[current.correct]}
    else:
        for lesson_id, position in owned_list:
            current = available_questions.filter(lesson_id=lesson_id, position=position).first()
            if current:
                break
    context = {**scope, "available": True, "question": current, "result": result, "remaining": len(owned) - int(bool(result and result["correct"] and result["saved"]))}
    if result and not result["correct"]:
        context["feedback_hint"] = feedback_hint(
            current.lesson_id, current.position, {"options": current.options, "correct": current.correct},
        )
    if current:
        context["state"] = sign_mistake(request.supabase_user.id, current.lesson_id, current.position)
        context["lesson_level"] = current.lesson.topic.course.level
    return _practice_response(request, context)


def _practice_response(request, context, status=200):
    response = render(request, "mistake_practice.html", context, status=status)
    response["Cache-Control"] = "private, no-store"
    return response
