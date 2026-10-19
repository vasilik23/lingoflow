"""Original B1 writing sets matching the published adult exam structure."""
import json

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from polskiflow.auth import require_supabase_user
from polskiflow.auth_views import require_browser_user
from polskiflow.b1_writing_store import validate_attempt, save_writing_attempt
from polskiflow.domain.api_rate_limit import consume_api_mutation
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


@require_POST
@require_supabase_user
def writing_history_save(request):
    """CSRF-protected browser session endpoint; no essay or owner from the client."""
    def reply(payload, status=200):
        response = JsonResponse(payload, status=status)
        response['Cache-Control'] = 'private, no-store'
        return response
    if request.headers.get('Authorization'):
        return reply({'error': 'cookie_session_required'}, 401)
    # An old tab must not replay its owner's queue into a newly signed-in account.
    expected_owner = request.headers.get('X-LingoFlow-Writing-Owner')
    if expected_owner is not None and expected_owner != str(request.supabase_user.id):
        return reply({'error': 'owner_session_changed'}, 409)
    if request.content_type != 'application/json':
        return reply({'error': 'unsupported_media_type'}, 415)
    if len(request.body) > 2048:
        return reply({'error': 'payload_too_large'}, 413)
    try:
        payload = validate_attempt(json.loads(request.body))
    except (ValueError, TypeError, UnicodeDecodeError, OverflowError):
        return reply({'error': 'invalid_attempt'}, 400)
    allowed, retry_after = consume_api_mutation(request.supabase_access_token, str(request.supabase_user.id), 'result')
    if not allowed:
        response = reply({'error': 'rate_limited'}, 429)
        response['Retry-After'] = str(retry_after)
        return response
    outcome = save_writing_attempt(request.supabase_access_token, payload)
    if outcome == 'conflict':
        return reply({'error': 'attempt_conflict'}, 409)
    if outcome not in ('saved', 'duplicate'):
        return reply({'error': 'history_unavailable'}, 503)
    return reply({'saved': True, 'attempt_id': payload['attempt_id']})
