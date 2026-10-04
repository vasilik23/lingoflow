import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from polskiflow.b1_section_store import (
    load_b1_section_attempts,
    save_b1_section_attempt,
)
from polskiflow.privacy_export_store import DATASETS


@override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_ANON_KEY="anon")
class B1SectionStoreTests(SimpleTestCase):
    def test_migration_has_owner_rls_minimal_grants_and_cascade(self):
        migration = Path(__file__).parents[2] / "supabase/migrations/20261004083700_b1_section_attempts.sql"
        sql = migration.read_text()

        self.assertIn("enable row level security", sql)
        self.assertIn("revoke all on table public.b1_section_attempts from anon, authenticated", sql)
        self.assertIn("grant select, insert", sql)
        self.assertIn("using ((select auth.uid()) = user_id)", sql)
        self.assertIn("with check ((select auth.uid()) = user_id)", sql)
        self.assertIn("references auth.users(id) on delete cascade", sql)
        self.assertNotIn("grant update", sql)
        self.assertNotIn("grant delete", sql)

    @patch("polskiflow.b1_section_store.urlopen")
    def test_save_is_idempotent_and_contains_only_aggregate(self, mocked_urlopen):
        response = MagicMock(status=201)
        response.__enter__.return_value = response
        mocked_urlopen.return_value = response

        saved = save_b1_section_attempt(
            "access",
            "user-123",
            "11111111-1111-4111-8111-111111111111",
            "b1-weekly-v2",
            {"section_id": "reading", "correct": 4, "total": 5, "details": ["private"]},
        )

        self.assertTrue(saved)
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data), {
            "user_id": "user-123",
            "attempt_id": "11111111-1111-4111-8111-111111111111",
            "attempt_version": "b1-weekly-v2",
            "section_id": "reading",
            "correct": 4,
            "total": 5,
        })
        self.assertIn("on_conflict=user_id%2Cattempt_id", request.full_url)
        self.assertEqual(request.headers["Prefer"], "resolution=ignore-duplicates,return=minimal")

    @patch("polskiflow.b1_section_store.urlopen")
    def test_load_is_owner_scoped_bounded_and_derives_safe_labels(self, mocked_urlopen):
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = b'[{"attempted_at":"2026-10-04T08:00:00Z","attempt_version":"b1-weekly-v2","section_id":"reading","correct":4,"total":5}]'
        mocked_urlopen.return_value = response

        rows = load_b1_section_attempts("access", "user-123", 999)

        self.assertEqual(rows[0]["section_label"], "Чтение")
        self.assertEqual(rows[0]["percent"], 80)
        self.assertEqual(rows[0]["variant_label"], "Вариант 2")
        self.assertEqual(rows[0]["attempted_at_display"], "04.10.2026 08:00")
        url = mocked_urlopen.call_args.args[0].full_url
        self.assertIn("user_id=eq.user-123", url)
        self.assertIn("limit=20", url)
        self.assertIn("order=attempted_at.desc", url)

    @patch("polskiflow.b1_section_store.urlopen", side_effect=TimeoutError)
    def test_upstream_failure_is_not_reported_as_empty_history(self, _urlopen):
        self.assertIsNone(load_b1_section_attempts("access", "user-123"))

    def test_privacy_export_includes_section_aggregates(self):
        table, fields, _order = DATASETS["b1_section_attempts"]
        self.assertEqual(table, "b1_section_attempts")
        self.assertIn("section_id", fields)
        self.assertNotIn("answers", fields)
