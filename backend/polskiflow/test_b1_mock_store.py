import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from polskiflow.b1_mock_store import load_b1_mock_attempts, save_b1_mock_attempt


@override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_ANON_KEY="anon")
class B1MockStoreTests(SimpleTestCase):
    def test_production_migration_enforces_owner_scope_and_minimal_grants(self):
        migration = Path(__file__).parents[2] / "supabase/migrations/20261001075719_b1_mock_attempts.sql"
        sql = migration.read_text()
        self.assertIn("enable row level security", sql)
        self.assertIn("revoke all on table public.b1_mock_attempts from anon, authenticated", sql)
        self.assertIn("grant select, insert", sql)
        self.assertIn("using ((select auth.uid()) = user_id)", sql)
        self.assertIn("with check ((select auth.uid()) = user_id)", sql)
        self.assertIn("references auth.users(id) on delete cascade", sql)
        self.assertNotIn("grant update", sql)
        self.assertNotIn("grant delete", sql)

    @patch("polskiflow.b1_mock_store.urlopen")
    def test_saves_only_owner_and_aggregate_module_scores(self, mocked_urlopen):
        response = MagicMock(status=201)
        response.__enter__.return_value = response
        mocked_urlopen.return_value = response
        result = {"attempt_version": "b1-weekly-v2", "modules": (
            {"id": "listening", "correct": 2},
            {"id": "reading", "correct": 1},
            {"id": "grammar", "correct": 2},
        )}

        self.assertTrue(save_b1_mock_attempt("access", "user-123", result))

        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.headers["Authorization"], "Bearer access")
        self.assertEqual(payload, {
            "user_id": "user-123", "attempt_version": "b1-weekly-v2",
            "listening_correct": 2, "reading_correct": 1, "grammar_correct": 2,
        })
        self.assertNotIn("answers", payload)

    @patch("polskiflow.b1_mock_store.urlopen")
    def test_load_is_owner_scoped_bounded_and_newest_first(self, mocked_urlopen):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'[{"listening_correct":2,"reading_correct":1,"grammar_correct":2,"attempt_version":"b1-weekly-v2"}]'
        mocked_urlopen.return_value = response

        rows = load_b1_mock_attempts("access", "user-123", 999)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["variant_label"], "Вариант 2")
        url = mocked_urlopen.call_args.args[0].full_url
        self.assertIn("user_id=eq.user-123", url)
        self.assertIn("limit=12", url)
        self.assertIn("order=attempted_at.desc", url)

    @patch("polskiflow.b1_mock_store.urlopen", side_effect=TimeoutError)
    def test_data_api_failure_is_distinct_from_empty_history(self, _mocked_urlopen):
        self.assertIsNone(load_b1_mock_attempts("access", "user-123"))
