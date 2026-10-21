"""Owner-token persistence of immutable B2 listening summaries."""
import json
from datetime import datetime
from django.utils import formats, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from uuid import UUID

from django.conf import settings
from polskiflow.b1_mock_store import _configured, _request
from polskiflow.domain.b2_listening_followup import FIELDS, MATERIAL, VERSION


def load_listening_results(token, owner, attempt_id=None):
    if not _configured(token):
        return None
    query = {'select': FIELDS, 'user_id': 'eq.' + owner, 'material_id': 'eq.' + MATERIAL,
             'content_version': 'eq.' + str(VERSION), 'order': 'completed_at.desc,attempt_id.desc', 'limit': '12'}
    if attempt_id:
        try:
            query['attempt_id'] = 'eq.' + str(UUID(attempt_id))
        except (ValueError, TypeError, AttributeError):
            return []
    try:
        with urlopen(_request('b2_listening_attempts?' + urlencode(query), token), timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            rows = json.load(response)
        if not isinstance(rows, list):
            return None
        for row in rows:
            UUID(row['attempt_id'])
            completed = datetime.fromisoformat(row['completed_at'].replace('Z', '+00:00'))
            if completed.tzinfo is None or row['material_id'] != MATERIAL or row['content_version'] != VERSION:
                return None
            row['date_display'] = formats.date_format(timezone.localtime(completed), 'SHORT_DATETIME_FORMAT')
            mask = row['missed_mask']
            if type(mask) is not int or not 0 <= mask <= 7 or type(row['correct']) is not int or row['correct'] != 3 - mask.bit_count():
                return None
        return rows
    except (HTTPError, URLError, TimeoutError, ValueError, TypeError, KeyError):
        return None


def save_listening_result(token, owner, result):
    if not _configured(token):
        return False
    try:
        request = _request('b2_listening_attempts?on_conflict=user_id,attempt_id', token, 'POST', {'user_id': owner, **result})
        request.add_header('Prefer', 'resolution=ignore-duplicates,return=minimal')
        with urlopen(request, timeout=settings.SUPABASE_AUTH_TIMEOUT):
            pass
        # Conflicting retries cannot overwrite a result; only a matching ACK succeeds.
        rows = load_listening_results(token, owner, result['attempt_id'])
        return bool(rows and all(rows[0].get(key) == value for key, value in result.items()))
    except (HTTPError, URLError, TimeoutError, ValueError, TypeError):
        return False
