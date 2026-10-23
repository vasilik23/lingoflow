import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from polskiflow.privacy_export_store import DATASETS, PAGE_SIZE, load_privacy_export


def _response(rows):
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = json.dumps(rows).encode()
    return response


@override_settings(
    SUPABASE_URL="https://project.supabase.co",
    SUPABASE_ANON_KEY="anon",
    SUPABASE_AUTH_TIMEOUT=2,
)
class PrivacyExportStoreTests(SimpleTestCase):
    @patch("polskiflow.privacy_export_store.urlopen")
    def test_loads_every_dataset_with_owner_filter_and_no_user_id_field(self, urlopen):
        urlopen.side_effect = [_response([{"value": name}]) for name in DATASETS]

        result = load_privacy_export("access", "user-123")

        self.assertTrue(result.available)
        self.assertEqual(set(result.datasets), set(DATASETS))
        self.assertEqual(result.datasets["lesson_drafts"], [{"value": "lesson_drafts"}])
        for call in urlopen.call_args_list:
            request = call.args[0]
            self.assertIn("eq.user-123", request.full_url)
            self.assertNotIn("user_id%2C", request.full_url)
            self.assertEqual(request.headers["Authorization"], "Bearer access")

    @patch("polskiflow.privacy_export_store.urlopen")
    def test_paginates_without_silent_truncation(self, urlopen):
        first_page = [{"lesson_id": str(index)} for index in range(PAGE_SIZE)]
        responses = [_response([]) for _ in DATASETS]
        responses[1:1] = [_response(first_page), _response([{"lesson_id": "last"}])]
        urlopen.side_effect = responses

        result = load_privacy_export("access", "user-123")

        self.assertTrue(result.available)
        self.assertEqual(len(result.datasets["lesson_completions"]), PAGE_SIZE + 1)
        completion_urls = [
            call.args[0].full_url for call in urlopen.call_args_list
            if "/lesson_completions?" in call.args[0].full_url
        ]
        self.assertIn("offset=500", completion_urls[1])

    @patch("polskiflow.privacy_export_store.urlopen", side_effect=TimeoutError)
    def test_any_upstream_failure_rejects_partial_export(self, _urlopen):
        result = load_privacy_export("access", "user-123")
        self.assertFalse(result.available)
        self.assertEqual(result.datasets, {})

    def test_missing_configuration_is_unavailable(self):
        with override_settings(SUPABASE_URL=""):
            self.assertFalse(load_privacy_export("access", "user-123").available)

    @patch('polskiflow.privacy_export_store.urlopen')
    def test_retention_metadata_is_in_existing_owner_scoped_datasets(self, urlopen):
        from urllib.parse import parse_qs, urlsplit
        urlopen.side_effect = [_response([]) for _ in DATASETS]
        self.assertTrue(load_privacy_export('access', 'user-123').available)
        queries = {urlsplit(call.args[0].full_url).path.split('/')[-1]: parse_qs(urlsplit(call.args[0].full_url).query) for call in urlopen.call_args_list}
        self.assertIn('last_request_at', queries['profiles']['select'][0])
        self.assertIn('activity_tracking_started_at', queries['profiles']['select'][0])
        self.assertIn('closed_at', queries['user_feedback']['select'][0])
        self.assertEqual(queries['profiles']['id'], ['eq.user-123'])
        self.assertEqual(queries['user_feedback']['user_id'], ['eq.user-123'])
