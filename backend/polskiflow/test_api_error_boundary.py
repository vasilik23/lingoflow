from unittest.mock import patch

from django.test import TestCase


class ApiErrorBoundaryTests(TestCase):
    private_paths = (
        "/api/v1/lessons/missing/",
        "/api/v1/reading/",
        "/api/v1/listening/",
        "/api/v1/me/profile/",
        "/api/v1/me/practice-preferences/",
        "/api/v1/me/feedback/",
        "/api/v1/me/today/",
        "/api/v1/me/history/",
        "/api/v1/me/sm2/",
        "/api/v1/me/lesson-drafts/latest/",
        "/api/v1/me/reading-bookmarks/",
    )

    def test_anonymous_private_api_errors_share_stable_no_store_envelope(self):
        for path in self.private_paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response["Cache-Control"], "private, no-store")
                self.assertEqual(response.json(), {
                    "api_version": "v1",
                    "error": {
                        "code": "authentication_required",
                        "detail": "Authentication is required",
                    },
                })
                self.assertTrue(response["X-Request-ID"])

    @patch("polskiflow.api_views.latest_official_news", return_value=[])
    def test_public_api_contracts_remain_public(self, _news):
        for path in ("/api/v1/catalog/", "/api/v1/news/", "/api/v1/openapi.json"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertIn("public", response["Cache-Control"])
