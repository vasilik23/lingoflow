"""Guided, privacy-safe checklist for the closed web beta."""

from django.shortcuts import render
from django.views.decorators.http import require_GET

from polskiflow.auth_views import require_browser_user
from polskiflow.progress_store import load_dashboard_progress


BETA_SCENARIOS = (
    {"id": "daily-plan", "title": "Пройти план на сегодня", "description": "Открой задание, заверши урок и проверь, что карточка обновилась.", "url_name": "home", "action": "Открыть Сегодня"},
    {"id": "course", "title": "Продолжить свой уровень", "description": "Выбери тему, пройди упражнение и вернись в каталог курса.", "url_name": "course", "action": "Открыть курс"},
    {"id": "reading", "title": "Прочитать текст и сохранить слово", "description": "Нажми на слово в тексте, проверь лемму и добавь её в словарь.", "url_name": "reading-library", "action": "Выбрать текст"},
    {"id": "practice", "title": "Попробовать отдельную тренировку", "description": "Выбери словарь, аудирование, письмо, общение или диагностику.", "url_name": "practice-hub", "action": "Выбрать практику"},
    {"id": "materials", "title": "Собрать личные материалы", "description": "Сохрани урок или текст и добавь его в тематическую подборку.", "url_name": "learning-space", "action": "Открыть материалы"},
)


@require_browser_user
@require_GET
def beta_center(request):
    fallback_name = (request.supabase_user.email or "ученик").split("@", 1)[0]
    dashboard = load_dashboard_progress(request.supabase_access_token, request.supabase_user.id, fallback_name)
    completed = len(dashboard.all_completed_lesson_ids)
    milestones = (
        {"label": "Первый урок", "done": completed >= 1, "detail": f"Пройдено уроков: {completed}"},
        {"label": "Три активных дня", "done": dashboard.active_days >= 3, "detail": f"Активных дней: {dashboard.active_days}"},
        {"label": "Первая учебная неделя", "done": completed >= 7, "detail": "7 разных уроков"},
    )
    return render(request, "beta_center.html", {"dashboard": dashboard, "scenarios": BETA_SCENARIOS, "milestones": milestones, "milestones_done": sum(item["done"] for item in milestones)})
