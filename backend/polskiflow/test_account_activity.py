import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from polskiflow.account_activity import record_activity, record_if_due

OWNER = '11111111-1111-4111-8111-111111111111'
OTHER = '22222222-2222-4222-8222-222222222222'


@override_settings(ACCOUNT_ACTIVITY_ENABLED=True, SUPABASE_URL='https://project.supabase.co', SUPABASE_ANON_KEY='anon', SUPABASE_AUTH_TIMEOUT=5)
class AccountActivityTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def request(self, owner=OWNER, path='/course/'):
        return SimpleNamespace(path=path, supabase_user=SimpleNamespace(id=owner), supabase_access_token='access')

    @patch('polskiflow.account_activity.urlopen')
    def test_rpc_uses_owner_token_no_caller_owner_or_timestamp_and_bounded_timeout(self, urlopen):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'890'
        urlopen.return_value = response
        self.assertEqual(record_activity('owner-token', OWNER), 890)
        req = urlopen.call_args.args[0]
        self.assertTrue(req.full_url.endswith('/rest/v1/rpc/record_account_activity'))
        self.assertEqual(json.loads(req.data), {})
        self.assertEqual(req.headers['Authorization'], 'Bearer owner-token')
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 1.0)

    @patch('polskiflow.account_activity.urlopen')
    def test_only_exact_bounded_integer_is_acknowledged(self, urlopen):
        for result in (True, False, 0, -1, 901, '900', {}, None):
            response = MagicMock()
            response.__enter__.return_value.read.return_value = json.dumps(result).encode()
            urlopen.return_value = response
            self.assertEqual(record_activity('token', OWNER), 0)

    @patch('polskiflow.account_activity.record_activity', return_value=800)
    def test_ack_coalesces_same_account_but_not_different_account(self, record):
        record_if_due(self.request())
        record_if_due(self.request())
        self.assertEqual(record.call_count, 1)
        record_if_due(self.request(OTHER))
        self.assertEqual(record.call_count, 2)

    @patch('polskiflow.account_activity.record_activity', return_value=0)
    def test_failed_write_is_not_acknowledged_and_has_short_retry_backoff(self, record):
        record_if_due(self.request())
        self.assertIsNone(cache.get(f'account-activity:v1:{OWNER}'))
        self.assertTrue(cache.get(f'account-activity:v1:{OWNER}:retry'))
        record_if_due(self.request())
        record.assert_called_once()
        cache.delete(f'account-activity:v1:{OWNER}:retry')
        record_if_due(self.request())
        self.assertEqual(record.call_count, 2)

    @patch('polskiflow.account_activity.record_activity', return_value=900)
    def test_inflight_lock_does_not_poison_ack(self, record):
        cache.set(f'account-activity:v1:{OWNER}:inflight', True, 5)
        record_if_due(self.request())
        record.assert_not_called()
        self.assertIsNone(cache.get(f'account-activity:v1:{OWNER}'))

    @patch('polskiflow.account_activity.record_activity')
    def test_guests_disabled_flag_invalid_owner_and_health_do_not_write(self, record):
        guest = self.request()
        guest.supabase_user = None
        record_if_due(guest)
        record_if_due(self.request(path='/health/'))
        record_if_due(self.request(owner='invalid'))
        with override_settings(ACCOUNT_ACTIVITY_ENABLED=False):
            record_if_due(self.request())
        record.assert_not_called()

    @patch('polskiflow.account_activity.urlopen', side_effect=TimeoutError)
    def test_transport_failure_is_unavailable_not_a_login_error(self, _open):
        self.assertEqual(record_activity('token', OWNER), 0)
        record_if_due(self.request())
        self.assertIsNone(cache.get(f'account-activity:v1:{OWNER}'))

    @patch('polskiflow.account_activity.cache.get', side_effect=RuntimeError('cache down'))
    def test_cache_read_failure_never_breaks_navigation(self, _get):
        record_if_due(self.request())

    @patch('polskiflow.account_activity.cache.set', side_effect=RuntimeError('cache down'))
    @patch('polskiflow.account_activity.cache.delete', side_effect=RuntimeError('cache down'))
    @patch('polskiflow.account_activity.record_activity', return_value=900)
    def test_cache_write_failure_never_breaks_navigation(self, *_mocks):
        record_if_due(self.request())

    @patch('polskiflow.account_activity.record_if_due')
    @patch('polskiflow.auth.authenticate_access_token', return_value=SimpleNamespace(id=OWNER, email='test@example.invalid'))
    def test_auth_middleware_covers_web_and_native_bearer_requests(self, _auth, record):
        for headers in ({}, {'HTTP_AUTHORIZATION': 'Bearer native-token'}):
            self.client.cookies['polskiflow_access_token'] = 'web-token'
            self.client.get('/privacy/', **headers)
            request = record.call_args.args[0]
            self.assertEqual(request.supabase_user.id, OWNER)
            self.assertEqual(request.supabase_access_token, 'native-token' if headers else 'web-token')
        self.assertEqual(record.call_count, 2)
