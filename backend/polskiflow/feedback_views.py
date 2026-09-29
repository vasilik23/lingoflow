from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from polskiflow.auth_views import require_browser_user
from polskiflow.feedback_store import load_feedback, save_feedback

CATEGORIES = (("content", "Ошибка в уроке"), ("translation", "Перевод или слово"), ("interface", "Интерфейс"), ("technical", "Техническая проблема"), ("idea", "Идея"))
PRIORITIES = (("normal", "Можно продолжать заниматься"), ("high", "Сильно мешает"), ("blocking", "Не могу продолжить"))
STATUS_LABELS = {"new": "Получено", "in_review": "На рассмотрении", "resolved": "Исправлено", "closed": "Закрыто"}
PRIORITY_LABELS = dict(PRIORITIES)

@require_browser_user
@require_http_methods(["GET", "POST"])
def feedback(request):
    form = {"category": request.POST.get("category", "content"), "priority": request.POST.get("priority", "normal"), "message": request.POST.get("message", "").strip(), "page_url": request.POST.get("page_url", request.GET.get("from", "")).strip()[:300]}
    error = ""
    if form["page_url"] and (not form["page_url"].startswith("/") or form["page_url"].startswith("//")): form["page_url"] = ""
    if request.method == "POST":
        if form["category"] not in dict(CATEGORIES): error = "Выберите категорию."
        elif form["priority"] not in PRIORITY_LABELS: error = "Выберите, насколько проблема мешает обучению."
        elif not 20 <= len(form["message"]) <= 2000: error = "Опишите проблему: от 20 до 2000 символов."
        elif save_feedback(request.supabase_access_token, request.supabase_user.id, **form): return redirect("/feedback/?sent=1")
        else: error = "Не удалось отправить сообщение. Попробуйте позже."
    items = load_feedback(request.supabase_access_token, request.supabase_user.id)
    category_labels = dict(CATEGORIES)
    visible_items = [
        {
            **item,
            "category_label": category_labels.get(item.get("category"), "Обращение"),
            "status_label": STATUS_LABELS.get(item.get("status"), "Получено"),
            "priority_label": PRIORITY_LABELS.get(item.get("priority"), "Можно продолжать заниматься"),
            "priority": item.get("priority") if item.get("priority") in PRIORITY_LABELS else "normal",
        }
        for item in (items or [])
        if isinstance(item, dict)
    ]
    return render(request, "feedback.html", {"categories": CATEGORIES, "priorities": PRIORITIES, "form": form, "error": error, "sent": request.GET.get("sent") == "1", "items": visible_items, "available": items is not None}, status=400 if error else 200)
