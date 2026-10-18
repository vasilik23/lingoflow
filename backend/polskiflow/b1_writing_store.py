"""Immutable, owner-scoped rehearsal metadata. Essays never enter this store."""
import json
from datetime import datetime, timedelta, timezone
from uuid import UUID
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from django.utils import formats, timezone as django_timezone
from polskiflow.b1_mock_store import _configured, _request

FIELDS = 'attempt_id,set_id,content_version,started_at,finished_at,timed_out,remaining_seconds,words_a,words_b'


def validate_attempt(payload):
    if not isinstance(payload, dict) or set(payload) != set(FIELDS.split(',')):
        raise ValueError('Invalid fields')
    item = dict(payload)
    if not isinstance(item['attempt_id'], str):
        raise ValueError('Invalid identifier')
    item['attempt_id'] = str(UUID(item['attempt_id']))
    if item['set_id'] not in ('1', '2', '3') or type(item['content_version']) is not int or item['content_version'] != 1:
        raise ValueError('Unknown material')
    if type(item['timed_out']) is not bool:
        raise ValueError('Invalid timing')
    for field, maximum in (('remaining_seconds', 4500), ('words_a', 20000), ('words_b', 20000)):
        if type(item[field]) is not int or not 0 <= item[field] <= maximum:
            raise ValueError('Invalid count')
    times = []
    for field in ('started_at', 'finished_at'):
        if not isinstance(item[field], str) or len(item[field]) > 40:
            raise ValueError('Invalid timestamp')
        value = datetime.fromisoformat(item[field].replace('Z', '+00:00'))
        if value.tzinfo is None:
            raise ValueError('Timezone required')
        value = value.astimezone(timezone.utc)
        if value > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError('Future timestamp')
        item[field] = value.isoformat()
        times.append(value)
    elapsed = (times[1] - times[0]).total_seconds()
    if not 0 <= elapsed <= 4500 or abs(elapsed + item['remaining_seconds'] - 4500) > 1.01:
        raise ValueError('Inconsistent timing')
    if item['timed_out'] and (item['remaining_seconds'] != 0 or elapsed < 4499):
        raise ValueError('Inconsistent timeout')
    return item


def save_writing_attempt(token, payload):
    if not _configured(token):
        return 'unavailable'
    try:
        with urlopen(_request('rpc/save_b1_writing_attempt', token, 'POST', {'attempt': payload}), timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            outcome = json.load(response)
        return outcome if outcome in ('saved', 'duplicate', 'conflict') else 'unavailable'
    except (HTTPError, URLError, TimeoutError, ValueError, TypeError):
        return 'unavailable'


def load_writing_attempts(token, user_id, days=None):
    if not _configured(token):
        return None
    query = {'select': FIELDS, 'user_id': f'eq.{user_id}', 'order': 'finished_at.desc,attempt_id.desc', 'limit': '12'}
    if days is not None:
        query['finished_at'] = 'gte.' + (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        with urlopen(_request('b1_writing_attempts?' + urlencode(query), token), timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            rows = json.load(response)
        if not isinstance(rows, list):
            return None
        result = []
        for row in rows:
            item = validate_attempt(row)
            finished = datetime.fromisoformat(item['finished_at'])
            item['date_display'] = formats.date_format(django_timezone.localtime(finished), 'SHORT_DATETIME_FORMAT')
            item['unanswered'] = int(item['words_a'] == 0) + int(item['words_b'] == 0)
            result.append(item)
        return result
    except (HTTPError, URLError, TimeoutError, ValueError, TypeError, KeyError):
        return None
