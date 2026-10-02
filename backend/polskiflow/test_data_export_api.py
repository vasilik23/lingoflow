from unittest.mock import patch

from django.test import TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.privacy_export_store import PrivacyExport


class LearnerDataExportApiTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser("user-123", "anna@example.com"),
        )
        auth.start()
        self.addCleanup(auth.stop)

    @patch("polskiflow.api_views.load_privacy_export")
    def test_bearer_export_uses_portable_private_envelope(self, load_export):
        load_export.return_value = PrivacyExport(True, {
            "profile": [{"display_name": "Anna"}],
            "lesson_completions": [{"lesson_id": "words"}],
            "lesson_result_events": [], "lesson_drafts": [],
            "personal_words": [], "reading_bookmarks": [], "lesson_bookmarks": [], "learner_mistakes": [], "lesson_notes": [], "learning_collections": [], "learning_collection_items": [],
            "feedback": [], "reminder_preferences": [],
        })

        response = self.client.get(
            "/api/v1/me/export/", HTTP_AUTHORIZATION="Bearer access"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertIn("Authorization", response["Vary"])
        payload = response.json()
        self.assertEqual(payload["meta"]["contract"], "learner-data-export")
        self.assertEqual(payload["data"]["schema_version"], "2.2")
        self.assertEqual(payload["data"]["account"]["email"], "anna@example.com")
        self.assertNotIn("token", response.content.decode().lower())
        load_export.assert_called_once_with("access", "user-123")

    @patch(
        "polskiflow.api_views.load_privacy_export",
        return_value=PrivacyExport(False, {}),
    )
    def test_export_fails_closed_when_any_dataset_is_unavailable(self, _load_export):
        response = self.client.get(
            "/api/v1/me/export/", HTTP_AUTHORIZATION="Bearer access"
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "upstream_unavailable")

    def test_export_requires_explicit_bearer_and_rejects_mutation(self):
        self.assertEqual(self.client.get("/api/v1/me/export/").status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/v1/me/export/", HTTP_AUTHORIZATION="Bearer access"
            ).status_code,
            405,
        )

    def test_openapi_documents_export_boundary(self):
        operation = self.client.get("/api/v1/openapi.json").json()["paths"][
            "/api/v1/me/export/"
        ]["get"]
        self.assertEqual(operation["security"], [{"supabaseBearer": []}])
        self.assertIn("503", operation["responses"])
