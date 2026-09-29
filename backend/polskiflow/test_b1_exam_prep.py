from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.b1_exam_prep import build_b1_exam_prep
from polskiflow.progress_store import DashboardProgress


class B1ExamPrepDomainTests(SimpleTestCase):
    def test_plan_matches_official_structure_and_daily_budget(self):
        plan = build_b1_exam_prep(date(2026, 9, 28))

        self.assertEqual(plan["countdown"]["days_remaining"], 19)
        self.assertEqual(plan["daily_minutes"], 15)
        self.assertEqual(len(plan["daily_plan"]), 3)
        self.assertEqual(len(plan["modules"]), 5)
        self.assertEqual(plan["pass_percent"], 50)
        self.assertEqual(plan["written_minutes"], 190)
        self.assertEqual(
            [module["duration_minutes"] for module in plan["modules"]],
            [25, 45, 45, 75, 15],
        )

    def test_countdown_handles_exam_day_and_published_sessions(self):
        exam_day = build_b1_exam_prep(date(2026, 10, 17))["countdown"]
        next_year = build_b1_exam_prep(date(2026, 12, 7))["countdown"]
        after_schedule = build_b1_exam_prep(date(2027, 11, 29))["countdown"]

        self.assertEqual(exam_day["days_remaining"], 0)
        self.assertEqual(exam_day["label"], "Экзамен начинается сегодня")
        self.assertTrue(next_year["available"])
        self.assertEqual(next_year["starts_on"], date(2027, 2, 6))
        self.assertFalse(after_schedule["available"])


class B1ExamPrepViewTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser("user-123", "learner@example.com"),
        )
        auth.start()
        self.addCleanup(auth.stop)

    @patch("polskiflow.auth_views.timezone.localdate", return_value=date(2026, 9, 28))
    def test_exam_page_presents_five_modules_and_daily_plan(self, _localdate):
        response = self.client.get("/exam/b1/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "До экзамена осталось 19 дней")
        self.assertContains(response, "15 минут подготовки")
        self.assertContains(response, 'class="card exam-module-card', count=5)
        self.assertContains(response, "Rozumienie ze słuchu")
        self.assertContains(response, "Poprawność gramatyczna")
        self.assertContains(response, "минимум 50% в каждом модуле")
        self.assertContains(response, "certyfikatpolski.pl")
        self.assertContains(response, "Официальные даты")

    def test_guest_is_redirected_to_login_with_return_path(self):
        self.client.cookies.clear()

        self.assertRedirects(
            self.client.get("/exam/b1/"),
            "/login/?next=%2Fexam%2Fb1%2F",
            fetch_redirect_response=False,
        )

    def _dashboard(self, level):
        return DashboardProgress(
            display_name="Anna",
            level=level,
            streak_days=2,
            completed_lesson_ids=frozenset(),
            available=True,
            daily_goal_lessons=2,
        )

    def test_home_promotes_exam_plan_for_b1_only(self):
        with patch(
            "polskiflow.auth_views.load_dashboard_progress",
            return_value=self._dashboard("B1"),
        ), patch("polskiflow.auth_views.load_personal_words", return_value=[]), patch(
            "polskiflow.auth_views.load_latest_lesson_draft", return_value=None
        ), patch(
            "polskiflow.auth_views.timezone.localdate", return_value=date(2026, 9, 28)
        ):
            b1_response = self.client.get("/")

        with patch(
            "polskiflow.auth_views.load_dashboard_progress",
            return_value=self._dashboard("A2"),
        ), patch("polskiflow.auth_views.load_personal_words", return_value=[]), patch(
            "polskiflow.auth_views.load_latest_lesson_draft", return_value=None
        ):
            a2_response = self.client.get("/")

        self.assertContains(b1_response, "Подготовка к государственному B1")
        self.assertContains(b1_response, 'href="/exam/b1/"')
        self.assertNotContains(a2_response, "Подготовка к государственному B1")
