"""One bounded listening route, separate from lesson scores and self-assessment."""
from datetime import timedelta
from uuid import uuid4

from django.core import signing
from django.utils import timezone


MATERIAL = 'hybrid-work-message'
VERSION = 1
SALT = 'lingoflow-b2-listening-v1'
FIELDS = 'attempt_id,material_id,content_version,correct,missed_mask,completed_at'
TARGETS = (
    ('b2view-grammar', 'Различить уступку и основной вывод'),
    ('b2prof-quiz', 'Проверить понимание делового сообщения'),
    ('b2prof-grammar', 'Закрепить решения и результаты встречи'),
)


def attempt_state(owner):
    return signing.dumps({'owner': owner, 'attempt_id': str(uuid4()), 'version': VERSION}, salt=SALT)


def grade(owner, state, answers, questions):
    payload = signing.loads(state, salt=SALT, max_age=7 * 86400)
    if payload.get('owner') != owner or payload.get('version') != VERSION:
        raise ValueError('Wrong owner or version')
    mask = 0
    for index, question in enumerate(questions):
        values = answers.getlist(question['id'])
        if len(values) != 1 or values[0] not in question['options']:
            raise ValueError('Choose one answer to each question')
        if values[0] != question['answer']:
            mask |= 1 << index
    return {'attempt_id': payload['attempt_id'], 'material_id': MATERIAL,
            'content_version': VERSION, 'correct': 3 - mask.bit_count(), 'missed_mask': mask}


def followup(result, today=None):
    if not result or result.get('material_id') != MATERIAL or result.get('content_version') != VERSION:
        return None
    today = today or timezone.localdate()
    completed = timezone.datetime.fromisoformat(result['completed_at'].replace('Z', '+00:00'))
    completed_on = timezone.localtime(completed).date()
    mask = result['missed_mask']
    if not mask:
        return {'passed': True, 'correct': result['correct'], 'total': 3, 'due': False}
    index = next(i for i in range(3) if mask & (1 << i))
    lesson, title = TARGETS[index]
    due_date = completed_on + timedelta(days=1)
    return {'passed': False, 'correct': result['correct'], 'total': 3,
            'href': '/lesson/' + lesson + '/', 'title': title,
            'due_date': due_date, 'due': today >= due_date,
            'repeat_href': '/listening/#b2-listening',
            'review_href': '/listening/?result=' + result['attempt_id'] + '#b2-listening'}
