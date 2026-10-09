"""Original B1 writing sets matching the published adult exam structure."""
from django.shortcuts import render
from django.views.decorators.http import require_GET
from polskiflow.auth_views import require_browser_user
from polskiflow.ai_writing import assignment_token

from polskiflow.domain.b1_exam_writing import SETS, SOURCE

@require_browser_user
@require_GET
def exam_writing(request):
    selected = next((item for item in SETS if item["id"] == request.GET.get("set")), SETS[0])
    tasks = tuple({**task, "editor": f"exam-writing-{selected['id']}-{task['id']}",
                   "ai_token": assignment_token(request.supabase_user.id, {
                       "id": f"exam-writing-v1-{selected['id']}-{task['id']}", "level": "B1",
                       "task": task["prompt"], "target_words": task["words"],
                   })} for task in selected["tasks"])
    response = render(request, "b1_exam_writing.html", {
        "writing_sets": SETS, "selected_set": selected, "exam_tasks": tasks,
        "writing_source": SOURCE,
    })
    response["Cache-Control"] = "private, no-store"
    return response
