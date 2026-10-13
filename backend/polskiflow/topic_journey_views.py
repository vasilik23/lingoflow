"""One scenario and one next action, based on existing owner-scoped results."""
from django.http import Http404
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import get_language
from django.views.decorators.http import require_GET

from polskiflow.auth_views import require_browser_user
from polskiflow.content import course_topics, reading_text, task
from polskiflow.domain.topic_journeys import journey
from polskiflow.domain.lesson_followup import latest_completions, needs_recheck
from polskiflow.progress_store import load_dashboard_progress


@require_browser_user
@require_GET
def topic_journey(request, topic_id):
    pilot = journey(topic_id, get_language())
    topic = next((t for t in course_topics() if t['id'] == topic_id), None)
    if not pilot or not topic or topic['level'] != pilot['level']:
        raise Http404
    lessons = {item['id']: item for item in topic['lessons']}
    if not set(pilot['lessons']) <= lessons.keys():
        raise Http404
    reading = reading_text(pilot['reading_id'])
    if not reading or reading.topic_id != topic_id or not isinstance(reading.source_metadata, dict) or reading.source_metadata.get('comprehension_lesson_id') != pilot['lessons'][3]:
        raise Http404
    dashboard = load_dashboard_progress(request.supabase_access_token, request.supabase_user.id,
                                        (request.supabase_user.email or 'learner').split('@')[0])
    latest = latest_completions(dashboard.recent_completion_results or (), timezone.localdate())
    steps = []
    for index, lesson_id in enumerate(pilot['lessons']):
        lesson = task(lesson_id)
        if not lesson:
            raise Http404
        steps.append({**lesson, 'href': f'/reading/{reading.id}/' if index == 3 else f'/lesson/{lesson_id}/',
                      'title': reading.title if index == 3 else lesson['plan_title'],
                      'completed': dashboard.available and lesson_id in dashboard.all_completed_lesson_ids,
                      'needs_review': dashboard.available and lesson_id in latest and needs_recheck(
                          latest[lesson_id]['cards_known'], latest[lesson_id]['cards_total'])})
    next_action = next((s for s in steps if s['needs_review']), None) or next((s for s in steps if not s['completed']), None)
    return render(request, 'topic_journey.html', {'topic': topic, 'journey': pilot, 'steps': steps,
                                               'next_action': next_action, 'progress_available': dashboard.available})
