from urllib.parse import urlencode
from django.urls import reverse
from django.utils.translation import gettext

from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from polskiflow.auth_views import require_browser_user
from polskiflow.content import tasks, task
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
    items = []
    for row in rows or []:
        lesson_id, position = row.get("lesson_id"), row.get("question_position")
        lesson = lesson_map.get(lesson_id)
        if lesson and type(position) is int and (lesson_id, position) in questions:
            items.append({
                "lesson_id": lesson_id, "title": lesson["plan_title"],
                "emoji": lesson["emoji"], "level": lesson["level"],
                "prompt": questions[(lesson_id, position)],
            })
    return render(request, "mistakes.html", {"mistakes": items, "mistakes_available": rows is not None})


@require_browser_user
@require_http_methods(["GET", "POST"])
def mistake_practice(request: HttpRequest) -> HttpResponse:
    selected_lesson = request.GET.get('lesson', '')
    if len(request.GET.getlist('lesson')) > 1 or (selected_lesson and task(selected_lesson) is None):
        return HttpResponseBadRequest(gettext('Некорректная тренировка урока'))
    repeat_url = reverse('mistake-practice') + ('?' + urlencode({'lesson': selected_lesson}) if selected_lesson else '')
    scope = {'selected_lesson': selected_lesson, 'repeat_url': repeat_url}
    rows = load_mistakes(request.supabase_access_token, request.supabase_user.id)
    if rows is None:
        return _practice_response(request, {**scope, "available": False}, status=503)
    owned_list = [
        (row.get("lesson_id"), row.get("question_position"))
        for row in rows if isinstance(row, dict) and isinstance(row.get("lesson_id"), str)
        and type(row.get("question_position")) is int and row["question_position"] >= 0
        and (not selected_lesson or row["lesson_id"] == selected_lesson)
    ]
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
        current = Question.objects.filter(
            lesson_id=state.lesson_id, position=state.position, is_active=True
        ).select_related("lesson__topic__course").first()
        if current is None or not 0 <= selected < len(current.options):
            return HttpResponseBadRequest("Некорректный ответ")
        correct = selected == current.correct
        saved = set_mistake(request.supabase_access_token, request.supabase_user.id, state.lesson_id, state.position, not correct)
        result = {"correct": correct, "saved": bool(saved), "selected": selected, "correct_answer": current.options[current.correct]}
    else:
        for lesson_id, position in owned_list:
            if isinstance(lesson_id, str) and type(position) is int:
                current = Question.objects.filter(
                    lesson_id=lesson_id, position=position, is_active=True
                ).select_related("lesson__topic__course").first()
                if current:
                    break
    context = {**scope, "available": True, "question": current, "result": result, "remaining": len(owned) - int(bool(result and result["correct"] and result["saved"]))}
    if current:
        context["state"] = sign_mistake(request.supabase_user.id, current.lesson_id, current.position)
        context["lesson_level"] = current.lesson.topic.course.level
    return _practice_response(request, context)


def _practice_response(request, context, status=200):
    response = render(request, "mistake_practice.html", context, status=status)
    response["Cache-Control"] = "private, no-store"
    return response
