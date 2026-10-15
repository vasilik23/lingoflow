import json
from datetime import date, timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from django.http import JsonResponse
from django.test import SimpleTestCase, TestCase, override_settings

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.practice_preference_store import FIELD, load_practice_preferences, save_practice_preferences
from polskiflow.domain.practice_recommendations import native_practice_recommendation
from polskiflow.privacy_export_store import DATASETS


@override_settings(SUPABASE_URL='https://example.supabase.co', SUPABASE_ANON_KEY='anon')
class PracticePreferenceStoreTests(SimpleTestCase):
    @patch('polskiflow.practice_preference_store.urlopen')
    def test_load_preserves_unset_versus_explicit_reset_and_filters_owner(self, opened):
        for value in (None, False, True):
            response = MagicMock()
            response.__enter__.return_value = BytesIO(json.dumps([{FIELD: value, 'level': 'B2'}]).encode())
            opened.return_value = response
            result = load_practice_preferences('access', 'owner')
            self.assertEqual(result, {'exclude_remote_work': value is True, 'configured': value is not None, 'level': 'B2'})
            self.assertIn('id=eq.owner', opened.call_args.args[0].full_url)
        self.assertIn(FIELD, DATASETS['profile'][1])

    @patch('polskiflow.practice_preference_store.urlopen')
    def test_save_requires_a_real_row_not_just_an_http_success(self, opened):
        for rows, expected in (([], False), ([{FIELD: False}], False), ([{FIELD: True}], True)):
            response = MagicMock()
            response.__enter__.return_value = BytesIO(json.dumps(rows).encode())
            opened.return_value = response
            self.assertEqual(save_practice_preferences('access', 'owner', True), expected)
            req = opened.call_args.args[0]
            self.assertEqual(json.loads(req.data), {FIELD: True})
            self.assertEqual(req.get_header('Prefer'), 'return=representation')
            self.assertEqual(req.method, 'PATCH')
            self.assertIn('id=eq.owner', req.full_url)
        opened.reset_mock()
        self.assertFalse(save_practice_preferences('access', 'owner', 'true'))
        opened.assert_not_called()

    @patch('polskiflow.practice_preference_store.urlopen')
    def test_missing_malformed_or_unavailable_profile_never_looks_like_a_reset(self, opened):
        for rows in ([], {}, [{}], [{FIELD: 'true'}], [None]):
            response = MagicMock()
            response.__enter__.return_value = BytesIO(json.dumps(rows).encode())
            opened.return_value = response
            self.assertIsNone(load_practice_preferences('access', 'owner'))
        opened.side_effect = URLError('offline')
        self.assertIsNone(load_practice_preferences('access', 'owner'))
        self.assertFalse(save_practice_preferences('access', 'owner', False))

    def test_native_recommendations_do_not_offer_excluded_topic_or_an_unsupported_exam(self):
        seen = set()
        for offset in range(14):
            item = native_practice_recommendation('B2', date(2026, 1, 1) + timedelta(days=offset), ('remote-work',))
            seen.add(item['screen'])
        self.assertEqual(seen, {'writing', 'interaction'})
        self.assertIsNone(native_practice_recommendation('B1', date(2026, 1, 1)))


class PracticePreferencesApiTests(TestCase):
    path = '/api/v1/me/practice-preferences/'
    authorization = {'HTTP_AUTHORIZATION': 'Bearer access'}

    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = 'access'
        for target, value in (
            ('polskiflow.auth.authenticate_access_token', SupabaseUser('owner', 'qa@example.test')),
            ('polskiflow.api_views._mutation_rate_limit', None),
            ('polskiflow.api_views.load_practice_preferences', {'exclude_remote_work': False, 'configured': False, 'level': 'B2'}),
        ):
            mocked = patch(target, return_value=value)
            setattr(self, target.rsplit('.', 1)[1], mocked.start())
            self.addCleanup(mocked.stop)

    def test_get_is_bearer_only_private_and_does_not_import_a_browser_cookie(self):
        self.assertEqual(self.client.get(self.path).status_code, 401)
        response = self.client.get(self.path, **self.authorization)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertFalse(response.json()['data']['configured'])
        self.load_practice_preferences.assert_called_once_with('access', 'owner')

    @patch('polskiflow.api_views.save_practice_preferences', return_value=True)
    def test_patch_synchronizes_both_enable_and_explicit_reset(self, saved):
        for enabled in (True, False):
            response = self.client.patch(self.path, json.dumps({'exclude_remote_work': enabled}), content_type='application/json', **self.authorization)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['data']['preferences'], {'exclude_remote_work': enabled})
            self.assertTrue(response.json()['data']['configured'])
            saved.assert_called_with('access', 'owner', enabled)
            if enabled:
                self.assertIn(response.json()['data']['recommendation']['screen'], ('writing', 'interaction'))

    @patch('polskiflow.api_views.save_practice_preferences')
    def test_validation_and_rate_limit_reject_before_storage(self, saved):
        for value in ({}, {'exclude_remote_work': 1}, {'exclude_remote_work': None}, {'exclude_remote_work': True, 'user_id': 'other'}, []):
            response = self.client.patch(self.path, json.dumps(value), content_type='application/json', **self.authorization)
            self.assertEqual(response.status_code, 400)
        self._mutation_rate_limit.return_value = JsonResponse({'error': 'limited'}, status=429)
        self.assertEqual(self.client.patch(self.path, '{}', content_type='application/json', **self.authorization).status_code, 429)
        self.load_practice_preferences.assert_not_called()
        saved.assert_not_called()

    @patch('polskiflow.api_views.save_practice_preferences', return_value=False)
    def test_upstream_failures_are_503_not_a_saved_default(self, saved):
        response = self.client.patch(self.path, json.dumps({'exclude_remote_work': True}), content_type='application/json', **self.authorization)
        self.assertEqual(response.status_code, 503)
        self.assertNotIn('data', response.json())
        self.load_practice_preferences.return_value = None
        self.assertEqual(self.client.get(self.path, **self.authorization).status_code, 503)
