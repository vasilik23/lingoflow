from unittest.mock import patch

from django.test import TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.progress_store import DashboardProgress


class BetaCenterTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        self.auth_patch = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser("user-123", "learner@example.com"),
        )
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)

    @patch("polskiflow.beta_views.load_dashboard_progress")
    def test_beta_center_shows_milestones_scenarios_and_feedback(self, load_progress):
        load_progress.return_value = DashboardProgress(
            "Learner",
            "A1",
            2,
            frozenset(),
            True,
            all_completed_lesson_ids=frozenset({"one", "two", "three"}),
            active_days=3,
        )

        response = self.client.get("/beta/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Закрытая beta")
        self.assertContains(response, "2 / 3")
        self.assertContains(response, "Основные сценарии")
        self.assertContains(response, "5 маршрутов")
        self.assertContains(response, 'href="/feedback/?from=/beta/"')
        self.assertContains(response, 'href="/reading/"')

    def test_beta_center_requires_authentication(self):
        self.client.cookies.clear()

        response = self.client.get("/beta/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])
