from datetime import date
from unittest.mock import patch

from django.test import TestCase, override_settings

from polskiflow.auth import SupabaseUser
from polskiflow.lesson_draft_store import LessonDraftLoadResult
from polskiflow.progress_store import DashboardProgress


@override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_ANON_KEY="anon")
class TodayApiTests(TestCase):
    authorization = {"HTTP_AUTHORIZATION": "Bearer owner-token"}

    def _auth(self):
        return patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser(id="owner-1", email="ada@example.com"))

    def _progress(self, available=True):
        return DashboardProgress(
            "Ada", "A2", 3, frozenset({"lesson-done"}), available,
            all_completed_lesson_ids=frozenset({"lesson-done"}), daily_goal_lessons=3,
        )

    def test_requires_explicit_bearer_even_with_browser_cookie(self):
        self.client.cookies["polskiflow_access_token"] = "cookie-token"
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress") as load:
            response = self.client.get("/api/v1/me/today/")
        self.assertEqual(response.status_code, 401)
        load.assert_not_called()

    def test_returns_canonical_plan_progress_and_resume(self):
        lessons = [
            {"id": "lesson-done", "kind": "words", "title": "Słowa", "description": "", "minutes": 5, "emoji": "📘", "level": "A2"},
            {"id": "lesson-next", "kind": "quiz", "title": "Quiz", "description": "Sprawdź", "minutes": 8, "emoji": "✅", "level": "A2"},
            {"id": "lesson-later", "kind": "grammar", "title": "Gramatyka", "description": "", "minutes": 10, "emoji": "🧩", "level": "A2"},
        ]
        draft = {"lesson_id": "lesson-next", "step_index": 1, "score": 1}
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress", return_value=self._progress()) as progress, patch(
            "polskiflow.api_views.load_personal_words", return_value=[]
        ), patch("polskiflow.api_views.load_latest_lesson_draft_result", return_value=LessonDraftLoadResult(True, draft)), patch(
            "polskiflow.api_views.tasks", return_value=lessons
        ), patch("polskiflow.api_views.timezone.localdate", return_value=date(2026, 9, 16)):
            response = self.client.get("/api/v1/me/today/", **self.authorization)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["date"], "2026-09-16")
        self.assertEqual(data["daily_goal_lessons"], 3)
        self.assertEqual(data["completed_count"], 1)
        self.assertEqual(data["progress_percent"], 33)
        self.assertEqual([item["id"] for item in data["tasks"]], ["lesson-done", "lesson-next", "lesson-later"])
        self.assertEqual(data["tasks"][1]["api_path"], "/api/v1/lessons/lesson-next/")
        self.assertEqual(data["tasks"][1]["skill"]["group"], "integrated")
        self.assertEqual(data["resume"]["step"], 2)
        progress.assert_called_once_with("owner-token", "owner-1", "ada")
        self.assertNotIn("owner-1", str(data))

    def test_due_dictionary_review_links_browser_and_native_sm2_flows(self):
        words = [{"next_review_date": "2026-09-01"} for _ in range(4)]
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress", return_value=self._progress()), patch(
            "polskiflow.api_views.load_personal_words", return_value=words
        ), patch("polskiflow.api_views.load_latest_lesson_draft_result", return_value=LessonDraftLoadResult(True)), patch(
            "polskiflow.api_views.tasks", return_value=[{"id": "lesson-next", "kind": "quiz", "title": "Quiz", "level": "A2"}]
        ), patch("polskiflow.api_views.timezone.localdate", return_value=date(2026, 9, 16)):
            response = self.client.get("/api/v1/me/today/", **self.authorization)
        review = response.json()["data"]["tasks"][-1]
        self.assertEqual(review["kind"], "dictionary-review")
        self.assertEqual(review["path"], "/dictionary/practice/")
        self.assertEqual(review["api_path"], "/api/v1/me/sm2/")

    def test_low_recent_result_is_identical_transparent_reinforcement(self):
        progress = DashboardProgress(
            "Ada", "A2", 3, frozenset(), True,
            all_completed_lesson_ids=frozenset({"lesson-done"}), daily_goal_lessons=3,
            recent_completion_results=(
                {"lesson_id": "lesson-done", "plan_date": "2026-09-15", "cards_total": 5, "cards_known": 2},
            ),
        )
        lessons = [
            {"id": "lesson-done", "kind": "words", "title": "Słowa", "level": "A2"},
            {"id": "lesson-next", "kind": "quiz", "title": "Quiz", "level": "A2"},
            {"id": "lesson-later", "kind": "grammar", "title": "Gramatyka", "level": "A2"},
        ]
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress", return_value=progress), patch(
            "polskiflow.api_views.load_personal_words", return_value=[]
        ), patch("polskiflow.api_views.load_latest_lesson_draft_result", return_value=LessonDraftLoadResult(True)), patch(
            "polskiflow.api_views.tasks", return_value=lessons
        ), patch("polskiflow.api_views.timezone.localdate", return_value=date(2026, 9, 16)):
            response = self.client.get("/api/v1/me/today/", **self.authorization)
        reinforcement = response.json()["data"]["tasks"][1]
        self.assertEqual(reinforcement["id"], "lesson-done")
        self.assertEqual(reinforcement["plan_type"], "reinforcement")
        self.assertEqual(reinforcement["reinforcement_reason"]["cards_known"], 2)
        self.assertEqual(reinforcement["description"], "Лексика: Słowa: результат 2 из 5 — стоит закрепить")
        self.assertEqual(reinforcement["reinforcement_reason"]["skill"]["group"], "vocabulary")

    def test_any_owner_data_failure_returns_503_not_partial_plan(self):
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
                response = self.client.get("/api/v1/me/today/", **self.authorization)
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.json()["error"]["code"], "upstream_unavailable")
