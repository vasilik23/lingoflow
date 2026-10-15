"""Account preferences through the existing owner-only profile policies."""
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from polskiflow.b1_mock_store import _configured, _request

FIELD = 'practice_exclude_remote_work'


def load_practice_preferences(token, user_id):
    """None means unavailable; configured=False means legacy/unset, not a reset."""
    if not _configured(token):
        return None
    query = urlencode({'id': f'eq.{user_id}', 'select': f'{FIELD},level', 'limit': '1'})
    try:
        with urlopen(_request(f'profiles?{query}', token), timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            rows = json.load(response)
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            return None
        row = rows[0]
        if FIELD not in row or (row[FIELD] is not None and type(row[FIELD]) is not bool):
            return None
        return {'exclude_remote_work': row[FIELD] is True,
                'configured': row[FIELD] is not None, 'level': row.get('level', 'A1')}
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return None


def save_practice_preferences(token, user_id, exclude_remote_work):
    if type(exclude_remote_work) is not bool or not _configured(token):
        return False
    query = urlencode({'id': f'eq.{user_id}', 'select': FIELD})
    request = _request(f'profiles?{query}', token, 'PATCH', {FIELD: exclude_remote_work})
    # A zero-row RLS-filtered PATCH can return 200; require the actual owner row.
    request.add_header('Prefer', 'return=representation')
    try:
        with urlopen(request, timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            rows = json.load(response)
        return isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict) and rows[0].get(FIELD) is exclude_remote_work
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, TypeError):
        return False
