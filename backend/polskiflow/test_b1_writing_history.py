import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from django.test import SimpleTestCase, TestCase, Client, override_settings
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.b1_writing_store import validate_attempt, save_writing_attempt, load_writing_attempts
from polskiflow.privacy_export_store import DATASETS


def attempt(**changes):
    start = datetime.now(timezone.utc) - timedelta(minutes=10)
    return {**dict(attempt_id='a1d294a5-3e43-4ad0-b40c-ec988d21f322', set_id='2', content_version=1,
                  started_at=start.isoformat(), finished_at=(start + timedelta(seconds=123)).isoformat(),
                  timed_out=False, remaining_seconds=4377, words_a=25, words_b=0), **changes}


class WritingMetadataValidationTests(SimpleTestCase):
    def test_preserves_metadata_and_accepts_background_timeout(self):
        self.assertEqual(validate_attempt(attempt())['words_b'], 0)
        start = datetime.now(timezone.utc) - timedelta(hours=3)
        payload = attempt(started_at=start.isoformat(), finished_at=(start + timedelta(minutes=75)).isoformat(),
                          timed_out=True, remaining_seconds=0)
        self.assertTrue(validate_attempt(payload)['timed_out'])

    def test_rejects_text_owner_scores_bad_types_and_inconsistent_times(self):
        for change in ({'essay': 'PRIVATE'}, {'user_id': 'other'}, {'score': 10}, {'set_id': '4'},
                       {'content_version': True}, {'words_a': True}, {'words_b': -1}, {'words_a': 20001},
                       {'timed_out': 'false'}, {'remaining_seconds': 4501}, {'remaining_seconds': 1},
                       {'timed_out': True}, {'attempt_id': 'invalid'}, {'started_at': '2026-01-01T12:00:00'},
                       {'finished_at': (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()}):
            with self.subTest(change=change), self.assertRaises((ValueError, TypeError)):
                validate_attempt(attempt(**change))
        for invalid in (None, [], {}, {'attempt_id': 'x'}):
            with self.assertRaises(ValueError):
                validate_attempt(invalid)

    def test_node_sync_retries_refresh_timeout_and_stale_ack(self):
        node = shutil.which('node')
        self.assertIsNotNone(node)
        result = subprocess.run([node, str(Path(__file__).with_name('test_exam_writing_history.cjs'))], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_export_includes_only_aggregates(self):
        table, fields, order = DATASETS['b1_writing_attempts']
        self.assertEqual(table, 'b1_writing_attempts')
        self.assertEqual(set(fields.split(',')), set(attempt()))
        self.assertNotIn('text', fields)


@override_settings(SUPABASE_URL='https://fixture.supabase.co', SUPABASE_ANON_KEY='publishable', SUPABASE_AUTH_TIMEOUT=1)
class WritingMetadataStoreTests(SimpleTestCase):
    @patch('polskiflow.b1_writing_store.urlopen')
    def test_rpc_preserves_outcome_and_uses_callers_token(self, mocked):
        for outcome in ('saved', 'duplicate', 'conflict', 'unexpected'):
            response = MagicMock()
            response.__enter__.return_value = response
            response.read.return_value = json.dumps(outcome).encode()
            mocked.return_value = response
            self.assertEqual(save_writing_attempt('owner-token', attempt()), outcome if outcome != 'unexpected' else 'unavailable')
        request = mocked.call_args.args[0]
        self.assertEqual(request.headers['Authorization'], 'Bearer owner-token')
        self.assertTrue(request.full_url.endswith('/rpc/save_b1_writing_attempt'))
        self.assertEqual(set(json.loads(request.data)['attempt']), set(attempt()))

    @patch('polskiflow.b1_writing_store.urlopen')
    def test_owner_period_order_and_unavailable_states(self, mocked):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps([attempt()]).encode()
        mocked.return_value = response
        rows = load_writing_attempts('token', 'owner', days=7)
        self.assertEqual(rows[0]['unanswered'], 1)
        url = mocked.call_args.args[0].full_url
        for expected in ('user_id=eq.owner', 'finished_at=gte.', 'limit=12', 'order=finished_at.desc'):
            self.assertIn(expected, url)
        mocked.side_effect = URLError('unavailable')
        self.assertIsNone(load_writing_attempts('token', 'owner'))
        self.assertEqual(save_writing_attempt('token', attempt()), 'unavailable')
        with override_settings(SUPABASE_URL=''):
            self.assertIsNone(load_writing_attempts('token', 'owner'))


class WritingMetadataEndpointTests(TestCase):
    def setUp(self):
        self.auth = patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('writer', 'fixture@example.test'))
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.client.cookies[ACCESS_COOKIE] = 'owner-token'
        self.limit = patch('polskiflow.b1_writing_views.consume_api_mutation', return_value=(True, 60))
        self.limit.start()
        self.addCleanup(self.limit.stop)

    def post(self, payload=None, **extra):
        return self.client.post('/writing/exam/b1/history/', json.dumps(payload if payload is not None else attempt()), content_type='application/json', **extra)

    @patch('polskiflow.b1_writing_views.save_writing_attempt')
    def test_ack_duplicate_conflict_and_unavailable(self, save):
        for outcome, code in (('saved', 200), ('duplicate', 200), ('conflict', 409), ('unavailable', 503)):
            save.return_value = outcome
            response = self.post()
            self.assertEqual(response.status_code, code)
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            if code == 200:
                self.assertTrue(response.json()['saved'])
                self.assertEqual(response.json()['attempt_id'], attempt()['attempt_id'])
            self.assertEqual(save.call_args.args[0], 'owner-token')

    @patch('polskiflow.b1_writing_views.save_writing_attempt')
    def test_invalid_payload_and_auth_never_persist(self, save):
        self.assertEqual(self.post(attempt(essay='PRIVATE')).status_code, 400)
        self.assertEqual(self.post(HTTP_AUTHORIZATION='Bearer other').status_code, 401)
        self.assertEqual(self.client.get('/writing/exam/b1/history/').status_code, 405)
        self.assertEqual(self.client.post('/writing/exam/b1/history/', 'x'*2049, content_type='application/json').status_code, 413)
        self.client.cookies.clear()
        self.assertEqual(self.post().status_code, 401)
        save.assert_not_called()

    @patch('polskiflow.b1_writing_views.save_writing_attempt')
    def test_csrf_and_rate_limit(self, save):
        protected = Client(enforce_csrf_checks=True)
        protected.cookies[ACCESS_COOKIE] = 'owner-token'
        self.assertEqual(protected.post('/writing/exam/b1/history/', json.dumps(attempt()), content_type='application/json').status_code, 403)
        with patch('polskiflow.b1_writing_views.consume_api_mutation', return_value=(False, 60)):
            response = self.post()
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response['Retry-After'], '60')
        save.assert_not_called()


class WritingHistoryDisplayTests(TestCase):
    @patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('writer', 'fixture@example.test'))
    @patch('polskiflow.history_views.load_writing_attempts')
    def test_period_is_owner_scoped_and_page_distinguishes_empty_unavailable_and_metadata(self, load, _auth):
        self.client.cookies[ACCESS_COOKIE] = 'owner-token'
        for rows, expected in ((None, 'История письма временно недоступна.'), ([], 'В этом периоде ещё нет сохранённых письменных попыток.'),
                               ([{**attempt(), 'date_display': '18.10.2026', 'unanswered': 1}], '18.10.2026')):
            load.return_value = rows
            response = self.client.get('/history/?period=7')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            self.assertContains(response, expected)
            load.assert_called_with('owner-token', 'writer', days=7)
        self.assertContains(response, 'Без автоматического балла')
        self.assertContains(response, 'href="/writing/exam/b1/?set=2"')
