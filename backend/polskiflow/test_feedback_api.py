import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from polskiflow.auth import SupabaseUser


@override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_ANON_KEY="anon")
class FeedbackApiTests(TestCase):
    authorization = {"HTTP_AUTHORIZATION": "Bearer owner-token"}

    def auth(self):
        return patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("owner-1", "owner@example.com"))

    @patch("polskiflow.api_views.load_feedback")
    def test_get_returns_only_owner_scoped_history(self, load):
        load.return_value = [{"id": "one", "category": "content", "status": "new"}]
        with self.auth():
            response = self.client.get("/api/v1/me/feedback/", **self.authorization)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response.json()["data"]["items"][0]["id"], "one")
        load.assert_called_once_with("owner-token", "owner-1")

    @patch("polskiflow.api_views.consume_api_mutation", return_value=(True, 60))
    @patch("polskiflow.api_views.save_feedback", return_value=True)
    def test_post_validates_and_saves_under_authenticated_owner(self, save, limit):
        payload = {"category": "technical", "priority": "blocking", "message": "После завершения урока результат не обновился.", "page_url": "/lesson/quiz/"}
        with self.auth():
            response = self.client.post("/api/v1/me/feedback/", data=json.dumps(payload), content_type="application/json", **self.authorization)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"], {"created": True, "status": "new", "priority": "blocking"})
        limit.assert_called_once_with("owner-token", "owner-1", "feedback")
        save.assert_called_once_with("owner-token", "owner-1", payload["category"], payload["message"], payload["page_url"], payload["priority"])

    @patch("polskiflow.api_views.consume_api_mutation", return_value=(True, 60))
    @patch("polskiflow.api_views.save_feedback")
    def test_invalid_payload_never_writes(self, save, _limit):
        cases = (
            {"category": "other", "message": "x" * 30},
            {"category": "idea", "message": "short"},
            {"category": "idea", "message": "x" * 30, "page_url": "https://evil.example"},
            {"category": "idea", "message": "x" * 30, "user_id": "other"},
            {"category": "idea", "message": "x" * 30, "priority": "urgent"},
        )
        with self.auth():
            for payload in cases:
                with self.subTest(payload=payload):
                    response = self.client.post("/api/v1/me/feedback/", data=json.dumps(payload), content_type="application/json", **self.authorization)
                    self.assertEqual(response.status_code, 400)
        save.assert_not_called()

    @patch("polskiflow.api_views.consume_api_mutation", return_value=(True, 60))
    @patch("polskiflow.api_views.save_feedback", return_value=True)
    def test_omitted_priority_defaults_to_normal(self, save, _limit):
        payload = {"category": "idea", "message": "Предлагаю добавить ещё один сценарий практики."}
        with self.auth():
            response = self.client.post("/api/v1/me/feedback/", data=json.dumps(payload), content_type="application/json", **self.authorization)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["data"]["priority"], "normal")
        save.assert_called_once_with("owner-token", "owner-1", "idea", payload["message"], "", "normal")

    def test_requires_bearer_and_rejects_unsupported_method(self):
        self.assertEqual(self.client.get("/api/v1/me/feedback/").status_code, 401)
        with self.auth():
            self.assertEqual(self.client.delete("/api/v1/me/feedback/", **self.authorization).status_code, 405)
