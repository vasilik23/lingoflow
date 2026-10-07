"""Owner-scoped learning history UI."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from polskiflow.auth_views import require_browser_user
from polskiflow.content import tasks
from polskiflow.dictionary_store import load_personal_words
from polskiflow.domain.progress_overview import build_progress_overview
from polskiflow.domain.learning_insights import build_learning_insights
from polskiflow.domain.weekly_review import build_weekly_review
from polskiflow.progress_store import load_completion_history, load_dashboard_progress


PERIODS = {"7": 7, "30": 30, "90": 90, "all": None}


@require_browser_user
@require_GET
def learning_history(request: HttpRequest) -> HttpResponse:
    period = request.GET.get("period", "30")
    if period not in PERIODS:
        period = "30"
    try:
        page_number = int(request.GET.get("page", "1"))
    except (TypeError, ValueError):
        page_number = 1
    page = load_completion_history(
        request.supabase_access_token,
        request.supabase_user.id,
        page=max(1, page_number),
        days=PERIODS[period],
    )
    lesson_tasks = tasks()
    lesson_map = {lesson["id"]: lesson for lesson in lesson_tasks}
    rows = []
    for completion in page.rows:
        lesson = lesson_map.get(completion.get("lesson_id"), {})
        total = completion.get("cards_total") or 0
        known = completion.get("cards_known") or 0
        rows.append({
            **completion,
            "title": lesson.get("title") or completion.get("lesson_id") or "Урок",
            "emoji": lesson.get("emoji") or "✓",
            "level": lesson.get("level") or "—",
            "score": f"{known} / {total}" if total else "завершён",
        })
    fallback_name = (request.supabase_user.email or "ученик").split("@", 1)[0]
    dashboard = load_dashboard_progress(
        request.supabase_access_token,
        request.supabase_user.id,
        fallback_name,
    )
    return render(request, "history.html", {
        **build_progress_overview(dashboard, lesson_tasks, load_personal_words(
            request.supabase_access_token, request.supabase_user.id,
        )),
        "history_rows": rows,
        "history_available": page.available,
        "history_page": page,
        "selected_period": period,
        "insights": build_learning_insights(dashboard, lesson_tasks),
        "weekly_review": build_weekly_review(dashboard, lesson_tasks),
    })
