import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from polskiflow.auth import SupabaseUser


@override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_ANON_KEY="anon")
class NativeWritingApiTests(TestCase):
    authorization = {"HTTP_AUTHORIZATION": "Bearer owner-token"}

    def _auth(self):
        return patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser(id="owner-1", email="owner@example.com"),
        )

    def test_catalog_requires_bearer_and_describes_honest_local_boundary(self):
        self.client.cookies["polskiflow_access_token"] = "cookie-token"
        with self._auth():
            rejected = self.client.get("/api/v1/writing/")
            response = self.client.get("/api/v1/writing/", **self.authorization)
        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["levels"], ["B1", "B2"])
        self.assertEqual(data["prompt_count"], 11)
        self.assertEqual(
            [item["id"] for item in data["prompts"] if item["level"] == "B1"],
            [
                "formal-request", "recommendation", "opinion",
                "congratulations", "announcement", "description", "story",
            ],
        )
        self.assertEqual(data["persistence"], "none")
        self.assertEqual(data["assessment"], "observable_structure_only")
        self.assertEqual(len(data["prompts"][0]["checklist"]), 4)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_check_reports_only_observable_signals_and_does_not_echo_text(self):
        text = "Proszę o materiały i proponuję nowy termin. " + "słowo " * 75 + "\n\nTermin może być w poniedziałek."
        with self._auth(), patch(
            "polskiflow.api_views.consume_api_mutation", return_value=(True, 0)
        ):
            response = self.client.post(
                "/api/v1/writing/formal-request/check/",
                data=json.dumps({"text": text}), content_type="application/json",
                **self.authorization,
            )
        self.assertEqual(response.status_code, 200)
        result = response.json()["data"]
        self.assertTrue(result["all_observable_checks_passed"])
        self.assertEqual([item["id"] for item in result["checks"]], ["minimum_words", "minimum_paragraphs", "required_markers"])
        self.assertFalse(result["persisted"])
        self.assertIn("не оценивает грамматику", result["limitations"])
        self.assertNotIn(text, response.content.decode())

    def test_check_strictly_validates_prompt_payload_and_size(self):
        cases = (
            ("formal-request", {}, 400),
            ("formal-request", {"text": "tekst", "extra": True}, 400),
            ("formal-request", {"text": 1}, 400),
            ("formal-request", {"text": "   "}, 400),
            ("missing", {"text": "tekst"}, 404),
        )
        with self._auth(), patch(
            "polskiflow.api_views.consume_api_mutation", return_value=(True, 0)
        ):
            for prompt_id, payload, status in cases:
                with self.subTest(prompt_id=prompt_id, payload=payload):
                    response = self.client.post(
                        f"/api/v1/writing/{prompt_id}/check/",
                        data=json.dumps(payload), content_type="application/json",
                        **self.authorization,
                    )
                    self.assertEqual(response.status_code, status)
            oversized = self.client.post(
                "/api/v1/writing/formal-request/check/",
                data=json.dumps({"text": "x" * 21000}), content_type="application/json",
                **self.authorization,
            )
        self.assertEqual(oversized.status_code, 413)

    def test_check_requires_bearer_json_post(self):
        with self._auth():
            no_bearer = self.client.post(
                "/api/v1/writing/formal-request/check/",
                data=json.dumps({"text": "tekst"}), content_type="application/json",
            )
            wrong_type = self.client.post(
                "/api/v1/writing/formal-request/check/", data="{}",
                content_type="text/plain", **self.authorization,
            )
            wrong_method = self.client.get(
                "/api/v1/writing/formal-request/check/", **self.authorization
            )
        self.assertEqual(no_bearer.status_code, 401)
        self.assertEqual(wrong_type.status_code, 415)
        self.assertEqual(wrong_method.status_code, 405)

    def test_openapi_describes_non_persistent_bearer_contract(self):
        paths = self.client.get("/api/v1/openapi.json").json()["paths"]
        self.assertEqual(paths["/api/v1/writing/"]["get"]["security"], [{"supabaseBearer": []}])
        operation = paths["/api/v1/writing/{prompt_id}/check/"]["post"]
        self.assertEqual(operation["security"], [{"supabaseBearer": []}])
        self.assertIn("429", operation["responses"])
