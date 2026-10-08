from unittest.mock import patch

from django.test import TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.progress_store import DashboardProgress


class OnboardingTests(TestCase):
    @patch("polskiflow.auth_views.save_profile_settings")
    def test_suggestion_only_preselects_and_manual_choice_still_wins(self, save):
        response = self.client.get("/welcome/?suggested_level=B1")
        self.assertContains(response, 'value="B1" checked')
        self.assertContains(response, 'href="/welcome/check/"')
        self.assertContains(self.client.get("/welcome/?suggested_level=invalid"), 'value="A1" checked')
        save.assert_not_called()
        save.return_value = True
        self.client.post("/welcome/?suggested_level=B1", {"display_name": "Anna", "level": "A2", "daily_goal_minutes": "15"})
        self.assertEqual(save.call_args.args[3], "A2")

    @patch("polskiflow.auth_views.save_profile_settings", return_value=True)
    def test_minute_goal_uses_same_owner_profile_and_rejects_invalid_duration(self, save):
        response = self.client.post("/welcome/", {"display_name": "Anna", "level": "B1", "daily_goal_minutes": "30"})
        self.assertRedirects(response, "/?welcome=1", fetch_redirect_response=False)
        self.assertEqual(save.call_args.kwargs, {"daily_goal_minutes": 30})
        save.reset_mock()
        self.assertContains(self.client.post("/welcome/", {"display_name": "Anna", "level": "B1", "daily_goal_minutes": "20"}), "Выбери цель 10, 15 или 30 минут.", status_code=400)
        save.assert_not_called()

    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser("11111111-1111-4111-8111-111111111111", "anna@example.com"),
        )
        auth.start()
        self.addCleanup(auth.stop)
        progress = patch(
            "polskiflow.auth_views.load_dashboard_progress",
            return_value=DashboardProgress(
                display_name="Anna",
                level="A1",
                streak_days=0,
                completed_lesson_ids=frozenset(),
                available=True,
                daily_goal_lessons=2,
            ),
        )
        progress.start()
        self.addCleanup(progress.stop)

    def test_page_is_one_accessible_reversible_step(self):
        response = self.client.get("/welcome/")
        self.assertContains(response, "Первый шаг из одного")
        self.assertContains(response, 'name="level"', count=6)
        self.assertContains(response, 'name="daily_goal_minutes"', count=3)
        self.assertContains(response, "Это не тест CEFR")
        self.assertContains(response, 'value="A1" checked')
        self.assertContains(response, 'value="15" checked')

    @patch("polskiflow.auth_views.save_profile_settings", return_value=True)
    def test_valid_setup_updates_existing_owner_profile(self, save):
        response = self.client.post(
            "/welcome/",
            {"display_name": "  Ania  ", "level": "B1", "daily_goal_lessons": "3"},
        )
        save.assert_called_once_with(
            "access",
            "11111111-1111-4111-8111-111111111111",
            "Ania",
            "B1",
            3,
        )
        self.assertRedirects(response, "/?welcome=1", fetch_redirect_response=False)

    @patch("polskiflow.auth_views.save_profile_settings")
    def test_invalid_level_and_goal_never_write(self, save):
        level = self.client.post(
            "/welcome/",
            {"display_name": "Anna", "level": "admin", "daily_goal_lessons": "2"},
        )
        goal = self.client.post(
            "/welcome/",
            {"display_name": "Anna", "level": "A2", "daily_goal_lessons": "20"},
        )
        self.assertEqual(level.status_code, 400)
        self.assertEqual(goal.status_code, 400)
        self.assertContains(level, "A1 до C2", status_code=400)
        self.assertContains(goal, "одного до четырёх", status_code=400)
        save.assert_not_called()

    def test_guest_is_redirected_to_login_with_return_path(self):
        self.client.cookies.clear()
        self.assertRedirects(
            self.client.get("/welcome/"),
            "/login/?next=%2Fwelcome%2F",
            fetch_redirect_response=False,
        )
