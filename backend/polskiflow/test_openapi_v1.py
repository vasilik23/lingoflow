import json

from django.test import SimpleTestCase


class OpenApiV1Tests(SimpleTestCase):
    def test_document_is_public_deterministic_and_covers_live_v1_contracts(self):
        first = self.client.get("/api/v1/openapi.json")
        second = self.client.get("/api/v1/openapi.json")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.content, second.content)
        self.assertIn("public", first["Cache-Control"])
        document = first.json()
        self.assertEqual(document["openapi"], "3.1.0")
        self.assertEqual(
            set(document["paths"]),
            {
                "/api/v1/catalog/", "/api/v1/news/", "/api/v1/me/progress/", "/api/v1/me/sm2/",
                "/api/v1/me/profile/",
                "/api/v1/me/account/",
                "/api/v1/me/export/",
                "/api/v1/me/reminder-preferences/",
                "/api/v1/me/practice-preferences/",
                "/api/v1/me/feedback/",
                "/api/v1/me/today/",
                "/api/v1/me/bootstrap/",
                "/api/v1/me/achievements/",
                "/api/v1/me/sm2/{word_id}/review/",
                "/api/v1/lessons/{lesson_id}/",
                "/api/v1/lessons/{lesson_id}/answer/",
                "/api/v1/listening/",
                "/api/v1/listening/{exercise_id}/answer/",
                "/api/v1/interaction/",
                "/api/v1/interaction/{scenario_id}/answer/",
                "/api/v1/diagnostic/",
                "/api/v1/diagnostic/evaluate/",
                "/api/v1/writing/",
                "/api/v1/writing/{prompt_id}/check/",
                "/api/v1/reading/",
                "/api/v1/reading/{text_id}/",
                "/api/v1/reading/{text_id}/dictionary/",
                "/api/v1/me/dictionary/{word_id}/",
                "/api/v1/me/history/",
                "/api/v1/me/lesson-drafts/latest/",
                "/api/v1/me/lesson-drafts/{lesson_id}/",
                "/api/v1/me/lesson-results/",
                "/api/v1/me/lesson-results/session/",
                "/api/v1/me/reading-bookmarks/",
                "/api/v1/me/reading-bookmarks/{text_id}/",
            },
        )

    def test_security_boundaries_and_offline_payload_are_explicit(self):
        document = self.client.get("/api/v1/openapi.json").json()
        paths = document["paths"]
        self.assertNotIn("security", paths["/api/v1/catalog/"]["get"])
        self.assertNotIn("security", paths["/api/v1/news/"]["get"])
        self.assertEqual(
            paths["/api/v1/me/lesson-results/"]["post"]["security"],
            [{"supabaseBearer": []}],
        )
        self.assertEqual(paths["/api/v1/me/profile/"]["patch"]["security"], [{"supabaseBearer": []}])
        self.assertFalse(document["components"]["schemas"]["ProfilePatchRequest"]["additionalProperties"])
        self.assertIn("429", paths["/api/v1/me/profile/"]["patch"]["responses"])
        self.assertIn("429", paths["/api/v1/me/lesson-results/"]["post"]["responses"])
        self.assertEqual(
            paths["/api/v1/lessons/{lesson_id}/answer/"]["post"]["security"],
            [{"supabaseBearer": []}],
        )
        self.assertEqual(paths["/api/v1/reading/{text_id}/"]["get"]["security"], [{"supabaseBearer": []}])
        self.assertEqual(paths["/api/v1/listening/"]["get"]["security"], [{"supabaseBearer": []}])
        self.assertEqual(paths["/api/v1/listening/{exercise_id}/answer/"]["post"]["security"], [{"supabaseBearer": []}])
        self.assertEqual(paths["/api/v1/reading/{text_id}/dictionary/"]["post"]["security"], [{"supabaseBearer": []}])
        self.assertFalse(document["components"]["schemas"]["GlossaryWordRequest"]["additionalProperties"])
        self.assertEqual(
            paths["/api/v1/me/history/"]["get"]["security"],
            [{"supabaseBearer": []}],
        )
        self.assertEqual(paths["/api/v1/me/today/"]["get"]["security"], [{"supabaseBearer": []}])
        self.assertEqual(paths["/api/v1/me/sm2/{word_id}/review/"]["post"]["security"], [{"supabaseBearer": []}])
        self.assertEqual(
            paths["/api/v1/me/lesson-drafts/{lesson_id}/"]["put"]["security"],
            [{"supabaseBearer": []}],
        )
        self.assertFalse(document["components"]["schemas"]["LessonDraftRequest"]["additionalProperties"])
        self.assertEqual(
            paths["/api/v1/me/lesson-results/session/"]["post"]["security"],
            [{"browserSession": [], "csrfHeader": []}],
        )
        request = document["components"]["schemas"]["LessonResultRequest"]
        self.assertFalse(request["additionalProperties"])
        serialized = json.dumps(document).lower()
        self.assertNotIn("service_role", serialized)
        self.assertNotIn("refresh_token", serialized)
        deletion = document["components"]["schemas"]["AccountDeletionRequest"]
        self.assertEqual(deletion["required"], ["password"])
        self.assertFalse(deletion["additionalProperties"])
        self.assertEqual(deletion["properties"]["password"]["format"], "password")

    def test_document_supports_head_and_rejects_mutation(self):
        self.assertEqual(self.client.head("/api/v1/openapi.json").status_code, 200)
        response = self.client.post("/api/v1/openapi.json")
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response["Allow"], "GET, HEAD")
