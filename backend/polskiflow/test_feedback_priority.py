from pathlib import Path

from django.test import SimpleTestCase

from polskiflow.learning.models import UserFeedback
from polskiflow.privacy_export_store import DATASETS


class FeedbackPrioritySchemaTests(SimpleTestCase):
    def test_django_state_and_export_include_priority(self):
        field = UserFeedback._meta.get_field("priority")
        self.assertEqual(field.default, "normal")
        self.assertIn("priority", DATASETS["feedback"][1].split(","))

    def test_supabase_migration_is_bounded_and_preserves_security(self):
        root = Path(__file__).resolve().parents[2]
        sql = (root / "supabase/migrations/20260929071757_add_feedback_priority.sql").read_text()
        self.assertIn("add column if not exists priority", sql)
        self.assertIn("'normal', 'high', 'blocking'", sql)
        self.assertNotIn("disable row level security", sql.lower())
        self.assertNotIn("grant ", sql.lower())
