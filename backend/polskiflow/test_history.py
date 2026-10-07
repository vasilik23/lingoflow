import datetime
import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, TestCase, override_settings

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.weekly_review import build_weekly_review
from polskiflow.domain.progress_overview import build_progress_overview
from polskiflow.progress_store import CompletionHistoryPage, DashboardProgress, load_completion_history


class WeeklyReviewTests(SimpleTestCase):
    def test_builds_strong_and_reinforcement_lists_from_latest_results(self):
        dashboard = DashboardProgress(
            "Learner", "A2", 2, frozenset(), True,
            weekly_active_days=3, weekly_completed_count=2,
            previous_week_completed_count=1,
            recent_completion_results=(
                {"lesson_id": "strong", "plan_date": "2026-09-23", "cards_total": 10, "cards_known": 9},
                {"lesson_id": "focus", "plan_date": "2026-09-22", "cards_total": 10, "cards_known": 5},
                {"lesson_id": "focus", "plan_date": "2026-09-24", "cards_total": 10, "cards_known": 6},
            ),
        )
        review = build_weekly_review(dashboard, [
            {"id": "strong", "title": "Сильный урок", "level": "A2"},
            {"id": "focus", "title": "Повторить тему", "level": "A2"},
        ], today=datetime.date(2026, 9, 25))

        self.assertEqual(review["accuracy"], 75)
        self.assertEqual(review["completed_delta"], 1)
        self.assertEqual([item["id"] for item in review["strongest"]], ["strong"])
        self.assertEqual([item["id"] for item in review["reinforcement"]], ["focus"])

    def test_ignores_stale_unknown_and_invalid_results(self):
        dashboard = DashboardProgress(
            "Learner", "A1", 0, frozenset(), True,
            recent_completion_results=(
                {"lesson_id": "known", "plan_date": "2026-09-01", "cards_total": 5, "cards_known": 2},
                {"lesson_id": "missing", "plan_date": "2026-09-24", "cards_total": 5, "cards_known": 2},
                {"lesson_id": "known", "plan_date": "2026-09-24", "cards_total": 0, "cards_known": 0},
            ),
        )
        review = build_weekly_review(
            dashboard, [{"id": "known", "title": "Урок"}],
            today=datetime.date(2026, 9, 25),
        )
        self.assertFalse(review["has_results"])


class ProgressOverviewTests(SimpleTestCase):
    def test_primary_progress_uses_selected_level_and_achievements_use_all_levels(self):
        lessons = [{"id": "a1", "level": "A1"}, {"id": "b1-one", "level": "B1"}, {"id": "b1-two", "level": "B1"}]
        completed = frozenset({"a1", "b1-one", "dictionary-practice", "removed"})
        b1 = build_progress_overview(DashboardProgress("Learner", "B1", 0, completed, True, all_completed_lesson_ids=completed), lessons, [])
        a1 = build_progress_overview(DashboardProgress("Learner", "A1", 0, completed, True, all_completed_lesson_ids=completed), lessons, [])
        self.assertEqual((b1["completed_lessons"], b1["total_lessons"], b1["progress_percent"]), (1, 2, 50))
        self.assertEqual((a1["completed_lessons"], a1["total_lessons"], a1["progress_percent"]), (1, 1, 100))
        self.assertEqual((b1["course_completed_lessons"], b1["course_total_lessons"], b1["course_progress_percent"]), (2, 3, 67))
        self.assertEqual(b1["achievements"], a1["achievements"])

    def test_empty_selected_level_does_not_inherit_other_level_progress(self):
        overview = build_progress_overview(DashboardProgress("Learner", "B1", 0, frozenset({"a1"}), True, all_completed_lesson_ids=frozenset({"a1"})), [{"id": "a1", "level": "A1"}], [])
        self.assertEqual((overview["completed_lessons"], overview["total_lessons"], overview["progress_percent"]), (0, 0, 0))
        self.assertEqual(overview["course_progress_percent"], 100)


class CompletionHistoryStoreTests(SimpleTestCase):
    @override_settings(SUPABASE_URL="https://project.supabase.co", SUPABASE_ANON_KEY="public", SUPABASE_AUTH_TIMEOUT=2)
    @patch("polskiflow.progress_store.urlopen")
    def test_history_query_is_owner_scoped_paginated_and_bounded(self, urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps([
            {"lesson_id": f"lesson-{index}", "plan_date": "2026-09-15"}
            for index in range(21)
        ]).encode()
        urlopen.return_value.__enter__.return_value = response

        result = load_completion_history("access", "user-1", page=2, days=30)

        self.assertEqual(len(result.rows), 20)
        self.assertTrue(result.has_previous)
        self.assertTrue(result.has_next)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer access")
        self.assertIn("user_id=eq.user-1", request.full_url)
        self.assertIn("limit=21", request.full_url)
        self.assertIn("offset=20", request.full_url)
        self.assertIn("plan_date=gte.", request.full_url)


class LearningHistoryViewTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("user-1", "a@example.com"))
        auth.start()
        self.addCleanup(auth.stop)

    @patch("polskiflow.history_views.load_personal_words", return_value=[])
    @patch("polskiflow.history_views.load_dashboard_progress", return_value=DashboardProgress("Learner", "B1", 0, frozenset(), True))
    @patch("polskiflow.history_views.tasks", return_value=[])
    @patch("polskiflow.history_views.load_completion_history")
    def test_single_page_hides_pagination_and_dictionary_has_a_readable_title(self, load, *_):
        load.return_value = CompletionHistoryPage(({"lesson_id": "dictionary-practice", "plan_date": "2026-10-07", "cards_known": 3, "cards_total": 4},), True, False, False, 1)
        response = self.client.get("/history/")
        self.assertContains(response, "Повторение словаря")
        self.assertNotContains(response, "dictionary-practice")
        self.assertNotContains(response, 'class="history-pagination"')
        self.assertContains(response, 'class="activity-column" role="listitem"', count=14)
        self.assertContains(response, "Твой прогресс · B1")

    @patch("polskiflow.history_views.load_personal_words", return_value=[])
    @patch("polskiflow.history_views.load_dashboard_progress", return_value=DashboardProgress("Learner", "B1", 0, frozenset(), True))
    @patch("polskiflow.history_views.tasks", return_value=[])
    @patch("polskiflow.history_views.load_completion_history")
    def test_last_page_keeps_previous_link_and_selected_period(self, load, *_):
        load.return_value = CompletionHistoryPage(({"lesson_id": "dictionary-practice", "plan_date": "2026-10-07"},), True, True, False, 2)
        response = self.client.get("/history/?period=90&page=2")
        self.assertContains(response, 'class="history-pagination"')
        self.assertContains(response, '?period=90&page=1')
        self.assertNotContains(response, "Старее →")

    @patch("polskiflow.history_views.load_dashboard_progress")
    @patch("polskiflow.history_views.tasks", return_value=[{"id": "words", "kind": "words", "title": "Первые слова", "emoji": "💬", "level": "A1"}])
    @patch("polskiflow.history_views.load_completion_history")
    def test_history_renders_insights_lesson_metadata_and_pagination(self, load, _tasks, progress):
        load.return_value = CompletionHistoryPage(
            ({"lesson_id": "words", "plan_date": "2026-09-15", "cards_total": 8, "cards_known": 7},),
            True, False, True, 1,
        )
        progress.return_value = DashboardProgress(
            "Learner", "A1", 2, frozenset(), True,
            weekly_active_days=1, weekly_completed_count=1,
            recent_daily_completion_counts=(0,) * 27 + (1,),
            recent_completion_results=({"lesson_id": "words", "plan_date": datetime.date.today().isoformat(), "cards_total": 8, "cards_known": 7},),
        )

        response = self.client.get("/history/?period=30")

        self.assertContains(response, "Прогресс и история")
        self.assertContains(response, "Итог недели")
        self.assertContains(response, "Сильные результаты")
        self.assertContains(response, "Ритм занятий")
        self.assertContains(response, "Новые слова")
        self.assertContains(response, "88%", count=6)
        self.assertContains(response, "Первые слова")
        self.assertContains(response, "7 / 8")
        self.assertContains(response, "Старее")
        load.assert_called_once_with("access", "user-1", page=1, days=30)

    @patch("polskiflow.history_views.load_dashboard_progress", return_value=DashboardProgress("Learner", "A1", 0, frozenset(), True))
    @patch("polskiflow.history_views.tasks", return_value=[])
    @patch("polskiflow.history_views.load_completion_history", return_value=CompletionHistoryPage((), True, False, False, 1))
    def test_invalid_filters_fall_back_and_empty_state_is_honest(self, load, _tasks, _progress):
        response = self.client.get("/history/?period=invalid&page=nope")
        self.assertContains(response, "Пока нет завершённых занятий")
        load.assert_called_once_with("access", "user-1", page=1, days=30)

    def test_history_requires_authentication(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/history/").status_code, 302)
