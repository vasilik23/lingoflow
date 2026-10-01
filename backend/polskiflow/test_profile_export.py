from unittest.mock import patch

from django.test import TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.privacy_export_store import PrivacyExport


class ProfileExportTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("user-123", "anna@example.com"))
        auth.start(); self.addCleanup(auth.stop)

    @patch("polskiflow.auth_views.load_privacy_export")
    def test_export_is_private_download_without_tokens(self, load_export):
        load_export.return_value = PrivacyExport(True, {
            "profile": [{"display_name": "Anna", "level": "B1"}],
            "lesson_completions": [{"lesson_id": "a"}],
            "lesson_result_events": [{"event_id": "event-1"}],
            "lesson_drafts": [{"lesson_id": "quiz"}],
            "personal_words": [{"word": "dom"}],
            "reading_bookmarks": [{"reading_text_id": "story-b"}],
            "lesson_bookmarks": [{"lesson_id": "words"}],
            "learner_mistakes": [{"lesson_id": "quiz", "question_position": 1}],
            "lesson_notes": [{"lesson_id": "words", "body": "Моя заметка"}],
            "learning_collections": [],
            "learning_collection_items": [],
            "feedback": [{"category": "idea", "message": "Dłuższa wiadomość"}],
            "reminder_preferences": [{"daily_reminder_enabled": False}],
        })
        response = self.client.get("/profile/export/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response.json()["schema_version"], "2.1")
        self.assertEqual(response.json()["account"]["email"], "anna@example.com")
        self.assertEqual(response.json()["lesson_drafts"][0]["lesson_id"], "quiz")
        self.assertNotIn("token", response.content.decode().lower())

    @patch("polskiflow.auth_views.load_privacy_export", return_value=PrivacyExport(False, {}))
    def test_export_fails_closed_instead_of_returning_partial_data(self, _load_export):
        response = self.client.get("/profile/export/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_export_requires_authentication(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/profile/export/").status_code, 302)
