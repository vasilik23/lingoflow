from datetime import date
from unittest.mock import patch

from django.test import TestCase, override_settings

from polskiflow.auth import SupabaseUser
from polskiflow.lesson_draft_store import LessonDraftLoadResult
from polskiflow.progress_store import DashboardProgress


@override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_ANON_KEY="anon")
class BootstrapApiTests(TestCase):
    authorization = {"HTTP_AUTHORIZATION": "Bearer owner-token"}

    def _auth(self):
        return patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser(id="owner-1", email="ada@example.com"),
        )

    def _progress(self, available=True):
        return DashboardProgress(
            "Ada", "A2", 5, frozenset({"lesson-done"}), available,
            all_completed_lesson_ids=frozenset({"lesson-done", "lesson-old"}),
            active_days=12, weekly_active_days=4, weekly_completed_count=6,
            daily_goal_lessons=3,
        )

    def test_requires_explicit_bearer_before_owner_queries(self):
        self.client.cookies["polskiflow_access_token"] = "cookie-token"
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress") as load:
            response = self.client.get("/api/v1/me/bootstrap/")
        self.assertEqual(response.status_code, 401)
        load.assert_not_called()

    def test_returns_one_consistent_profile_progress_and_today_snapshot(self):
        lessons = [
            {"id": "lesson-done", "kind": "words", "title": "Słowa", "level": "A2"},
            {"id": "lesson-next", "kind": "quiz", "title": "Quiz", "level": "A2"},
        ]
        draft = LessonDraftLoadResult(True, {"lesson_id": "lesson-next", "step_index": 2})
        with self._auth(), patch(
            "polskiflow.api_views.load_dashboard_progress", return_value=self._progress()
        ) as progress, patch(
            "polskiflow.api_views.load_personal_words", return_value=[]
        ) as words, patch(
            "polskiflow.api_views.load_latest_lesson_draft_result", return_value=draft
        ) as drafts, patch(
            "polskiflow.api_views.tasks", return_value=lessons
        ), patch("polskiflow.api_views.timezone.localdate", return_value=date(2026, 9, 18)):
            response = self.client.get("/api/v1/me/bootstrap/", **self.authorization)

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["profile"], {"display_name": "Ada", "level": "A2", "daily_goal_lessons": 3, "daily_goal_minutes": 15})
        self.assertEqual(data["progress"]["completed_lesson_count"], 2)
        self.assertEqual(data["progress"]["week"], {"active_days": 4, "completed_lessons": 6})
        self.assertEqual(data["today"]["date"], "2026-09-18")
        self.assertEqual(data["today"]["completed_count"], 1)
        self.assertEqual(data["today"]["resume"]["step"], 3)
        self.assertEqual(data["links"]["catalog"], "/api/v1/catalog/")
        self.assertNotIn("owner-1", str(data))
        self.assertNotIn("ada@example.com", str(data))
        progress.assert_called_once_with("owner-token", "owner-1", "ada")
        words.assert_called_once_with("owner-token", "owner-1")
        drafts.assert_called_once_with("owner-token", "owner-1")
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_any_owner_source_failure_returns_503_without_partial_snapshot(self):
        failures = (
            (self._progress(False), [], LessonDraftLoadResult(True)),
            (self._progress(), None, LessonDraftLoadResult(True)),
            (self._progress(), [], LessonDraftLoadResult(False)),
        )
        for progress, words, draft in failures:
            with self.subTest(progress=progress.available, words=words, draft=draft.available), self._auth(), patch(
                "polskiflow.api_views.load_dashboard_progress", return_value=progress
            ), patch("polskiflow.api_views.load_personal_words", return_value=words), patch(
                "polskiflow.api_views.load_latest_lesson_draft_result", return_value=draft
            ):
                response = self.client.get("/api/v1/me/bootstrap/", **self.authorization)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "upstream_unavailable")
            self.assertNotIn("data", response.json())

    def test_supports_head_rejects_mutation_and_is_in_openapi(self):
        with self._auth(), patch(
            "polskiflow.api_views.load_dashboard_progress", return_value=self._progress()
        ), patch("polskiflow.api_views.load_personal_words", return_value=[]), patch(
            "polskiflow.api_views.load_latest_lesson_draft_result", return_value=LessonDraftLoadResult(True)
        ), patch("polskiflow.api_views.tasks", return_value=[]):
            head = self.client.head("/api/v1/me/bootstrap/", **self.authorization)
            post = self.client.post("/api/v1/me/bootstrap/", **self.authorization)
        self.assertEqual(head.status_code, 200)
        self.assertEqual(post.status_code, 405)
        operation = self.client.get("/api/v1/openapi.json").json()["paths"]["/api/v1/me/bootstrap/"]["get"]
        self.assertEqual(operation["security"], [{"supabaseBearer": []}])
