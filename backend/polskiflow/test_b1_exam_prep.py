from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.b1_exam_prep import build_b1_exam_prep, build_b1_module_results
from polskiflow.progress_store import DashboardProgress


class B1ExamPrepDomainTests(SimpleTestCase):
    def test_module_results_use_only_measured_b1_reading_and_grammar(self):
        results = build_b1_module_results(
            (
                {"lesson_id": "b1-topic-grammar", "cards_known": 4, "cards_total": 5},
                {"lesson_id": "b1-topic-reading-check", "cards_known": 3, "cards_total": 5},
                {"lesson_id": "a2-topic-grammar", "cards_known": 5, "cards_total": 5},
            ),
            [
                {"id": "b1-topic-grammar", "kind": "grammar", "level": "B1"},
                {"id": "b1-topic-reading-check", "kind": "quiz", "level": "B1"},
                {"id": "a2-topic-grammar", "kind": "grammar", "level": "A2"},
            ],
        )

        by_id = {item["id"]: item for item in results}
        self.assertEqual(by_id["grammar"]["percent"], 80)
        self.assertEqual(by_id["reading"]["percent"], 60)
        self.assertEqual(by_id["listening"]["status"], "unmeasured")
        self.assertIsNone(by_id["writing"]["percent"])

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

    def test_plan_prioritises_only_a_measured_module_below_seventy_percent(self):
        results = build_b1_module_results(
            (
                {"lesson_id": "b1-grammar", "cards_known": 8, "cards_total": 10},
                {"lesson_id": "b1-reading-check", "cards_known": 3, "cards_total": 5},
            ),
            [
                {"id": "b1-grammar", "kind": "grammar", "level": "B1"},
                {"id": "b1-reading-check", "kind": "quiz", "level": "B1"},
            ],
        )

        plan = build_b1_exam_prep(date(2026, 9, 28), results)

        self.assertEqual(plan["focus"]["id"], "reading")
        self.assertEqual(plan["daily_plan"][0]["module_id"], "reading")
        self.assertEqual(
            plan["daily_plan"][0]["focus_reason"],
            "Последние тренировки: 60% — стоит закрепить",
        )
        self.assertEqual(len(plan["daily_plan"]), 3)
        self.assertEqual(plan["daily_minutes"], 15)

    def test_plan_does_not_invent_focus_for_unmeasured_or_strong_modules(self):
        plan = build_b1_exam_prep(
            date(2026, 9, 28),
            (
                {"id": "grammar", "status": "measured", "percent": 80},
                {"id": "writing", "status": "unmeasured", "percent": None},
            ),
        )

        self.assertIsNone(plan["focus"])
        self.assertFalse(any(item.get("is_focus") for item in plan["daily_plan"]))

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

    @patch("polskiflow.auth_views.tasks", return_value=[
        {"id": "b1-topic-grammar", "kind": "grammar", "level": "B1"},
    ])
    @patch("polskiflow.auth_views.load_dashboard_progress")
    @patch("polskiflow.auth_views.timezone.localdate", return_value=date(2026, 9, 28))
    def test_exam_page_presents_modules_plan_and_measured_results(self, _localdate, progress, _tasks):
        progress.return_value = DashboardProgress(
            display_name="Anna", level="B1", streak_days=2,
            completed_lesson_ids=frozenset(), available=True,
            recent_completion_results=({"lesson_id": "b1-topic-grammar", "cards_known": 4, "cards_total": 5},),
        )
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
        self.assertContains(response, "Результаты по модулям")
        self.assertContains(response, "80%")
        self.assertContains(response, "Пока без автоматического балла")
        self.assertContains(response, "не прогноз экзамена")

    @patch("polskiflow.auth_views.tasks", return_value=[
        {"id": "b1-topic-reading-check", "kind": "quiz", "level": "B1"},
    ])
    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_exam_page_explains_measured_weak_module_focus(self, progress, _tasks):
        progress.return_value = DashboardProgress(
            display_name="Anna", level="B1", streak_days=2,
            completed_lesson_ids=frozenset(), available=True,
            recent_completion_results=(
                {"lesson_id": "b1-topic-reading-check", "cards_known": 3, "cards_total": 5},
            ),
        )

        response = self.client.get("/exam/b1/")

        self.assertContains(response, "фокус дня")
        self.assertContains(response, "Последние тренировки: 60% — стоит закрепить")
        self.assertContains(response, "все 5 модулей в недельной ротации")

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

    @patch("polskiflow.auth_views.tasks", return_value=[
        {"id": "b1-reading-check", "kind": "quiz", "level": "B1", "minutes": 5},
    ])
    @patch("polskiflow.auth_views.load_latest_lesson_draft", return_value=None)
    @patch("polskiflow.auth_views.load_personal_words", return_value=[])
    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_home_explains_b1_focus_without_calling_it_exam_readiness(
        self, progress, _words, _draft, _tasks
    ):
        progress.return_value = DashboardProgress(
            display_name="Anna", level="B1", streak_days=2,
            completed_lesson_ids=frozenset(), available=True,
            recent_completion_results=(
                {"lesson_id": "b1-reading-check", "cards_known": 3, "cards_total": 5},
            ),
        )

        response = self.client.get("/")

        self.assertContains(response, "Фокус: Чтение — последние тренировки 60%")
        self.assertNotContains(response, "готовность 60%")
