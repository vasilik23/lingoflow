from uuid import UUID

from django.http import Http404, HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from polskiflow.auth_views import require_browser_user
from polskiflow.collection_store import add_collection_item, create_collection, delete_collection, delete_collection_item, load_collections, rename_collection
from polskiflow.learning.models import Lesson, ReadingText
from polskiflow.lesson_bookmark_store import load_lesson_bookmarks
from polskiflow.reading_bookmark_store import load_reading_bookmarks
from polskiflow.progress_store import load_dashboard_progress


@require_browser_user
@require_GET
def collections(request: HttpRequest) -> HttpResponse:
    loaded = load_collections(request.supabase_access_token, request.supabase_user.id)
    lesson_ids = load_lesson_bookmarks(request.supabase_access_token, request.supabase_user.id)
    reading_ids = load_reading_bookmarks(request.supabase_access_token, request.supabase_user.id)
    available = loaded is not None and lesson_ids is not None and reading_ids is not None
    progress = load_dashboard_progress(request.supabase_access_token, request.supabase_user.id, request.supabase_user.email)
    rows, item_rows = loaded or ([], [])
    lessons = {x.id: x for x in Lesson.objects.filter(id__in={i["content_id"] for i in item_rows if i.get("content_type") == "lesson"}).select_related("topic__course")}
    readings = {x.id: x for x in ReadingText.objects.filter(id__in={i["content_id"] for i in item_rows if i.get("content_type") == "reading"})}
    grouped = []
    for row in rows:
        items = [{**item, "content": lessons.get(item["content_id"]) if item.get("content_type") == "lesson" else readings.get(item["content_id"])} for item in item_rows if item.get("collection_id") == row.get("id")]
        items = [item for item in items if item["content"] is not None]
        lesson_items = [item for item in items if item["content_type"] == "lesson"]
        completed = sum(item["content_id"] in progress.all_completed_lesson_ids for item in lesson_items)
        next_item = next((item for item in lesson_items if item["content_id"] not in progress.all_completed_lesson_ids), None) or (items[0] if items else None)
        grouped.append({**row, "items": items, "lesson_count": len(lesson_items), "completed_count": completed, "progress_percent": round(completed * 100 / len(lesson_items)) if lesson_items else 0, "next_item": next_item, "all_lessons_completed": bool(lesson_items) and completed == len(lesson_items)})
    saved_lessons = Lesson.objects.filter(id__in=lesson_ids or (), is_active=True).order_by("plan_title")
    saved_readings = ReadingText.objects.filter(id__in=reading_ids or (), is_active=True).order_by("title")
    return render(request, "collections.html", {"collections": grouped, "available": available, "saved_lessons": saved_lessons, "saved_readings": saved_readings})


@require_POST
@require_browser_user
def create_collection_view(request):
    name = request.POST.get("name", "").strip()
    if not 1 <= len(name) <= 60: return HttpResponseBadRequest("Название должно содержать от 1 до 60 символов")
    ok = create_collection(request.supabase_access_token, request.supabase_user.id, name)
    return redirect("/collections/?status=created" if ok else "/collections/?status=error")


@require_POST
@require_browser_user
def collection_action(request, collection_id):
    try: UUID(str(collection_id))
    except ValueError: raise Http404
    action = request.POST.get("action")
    if action == "delete": ok = delete_collection(request.supabase_access_token, request.supabase_user.id, collection_id)
    elif action == "rename":
        name = request.POST.get("name", "").strip()
        if not 1 <= len(name) <= 60: return HttpResponseBadRequest("Название должно содержать от 1 до 60 символов")
        ok = rename_collection(request.supabase_access_token, request.supabase_user.id, collection_id, name)
    elif action == "add":
        try: content_type, content_id = request.POST.get("material", "").split(":", 1)
        except ValueError: return HttpResponseBadRequest("Выберите материал")
        exists = Lesson.objects.filter(id=content_id, is_active=True).exists() if content_type == "lesson" else ReadingText.objects.filter(id=content_id, is_active=True).exists() if content_type == "reading" else False
        if not exists: return HttpResponseBadRequest("Материал не найден")
        ok = add_collection_item(request.supabase_access_token, request.supabase_user.id, collection_id, content_type, content_id)
    else: return HttpResponseBadRequest("Неизвестное действие")
    return redirect("/collections/?status=updated" if ok else "/collections/?status=error")


@require_POST
@require_browser_user
def remove_collection_item(request, item_id):
    try: UUID(str(item_id))
    except ValueError: raise Http404
    ok = delete_collection_item(request.supabase_access_token, request.supabase_user.id, item_id)
    return redirect("/collections/?status=updated" if ok else "/collections/?status=error")
