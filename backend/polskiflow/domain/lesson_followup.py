"""One next step and a recheck derived from the owner's saved lesson results."""
from datetime import date, timedelta

RECHECK_THRESHOLD_PERCENT = 70


def needs_recheck(known, total):
    return (type(total) is int and total > 0 and type(known) is int
            and 0 <= known <= total and known * 100 < total * RECHECK_THRESHOLD_PERCENT)


def recheck_date(result):
    if not needs_recheck(result.get('cards_known'), result.get('cards_total')):
        return None
    try:
        return date.fromisoformat(result['plan_date']) + timedelta(days=1)
    except (KeyError, TypeError, ValueError):
        return None


def latest_completions(results, today):
    """Old failures must never override a newer valid successful attempt."""
    latest = {}
    for result in results:
        lesson_id = result.get('lesson_id')
        total, known = result.get('cards_total'), result.get('cards_known')
        try:
            completed = date.fromisoformat(result.get('plan_date', ''))
        except (TypeError, ValueError):
            continue
        if (not isinstance(lesson_id, str) or not lesson_id or completed > today
                or (today - completed).days > 29 or type(total) is not int or total <= 0
                or type(known) is not int or not 0 <= known <= total):
            continue
        previous = latest.get(lesson_id)
        if previous is None or (result['plan_date'], known / total) > (previous['plan_date'], previous['cards_known'] / previous['cards_total']):
            latest[lesson_id] = result
    return latest


def lesson_followup(lesson, navigation, score, total, completed_on):
    if needs_recheck(score, total):
        return {
            'kind': 'repeat', 'lesson': {**lesson, 'title': lesson.get('theory_title') or lesson['title']},
            'due_date': recheck_date({'plan_date': completed_on.isoformat(), 'cards_known': score, 'cards_total': total}),
        }
    return {'kind': 'next', 'lesson': (navigation or {}).get('next_lesson'), 'due_date': None}
