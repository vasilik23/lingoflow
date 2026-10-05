from datetime import date
from uuid import UUID
from unittest.mock import patch
from pathlib import Path
import subprocess

from django.core import signing
from django.test import SimpleTestCase, TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.b1_weekly_mock import QUESTIONS, VARIANTS, score_mock_answers, weekly_mock_variant


class B1WeeklyMockDomainTests(SimpleTestCase):
    def test_browser_resume_lifecycle(self):
        completed = subprocess.run(
            ["node", str(Path(__file__).with_name("test_b1_mock_resume.cjs"))],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_scores_each_objective_module_separately(self):
        answers = {question.id: question.correct for question in QUESTIONS}
        answers["g1"] = 0

        result = score_mock_answers(answers)

        self.assertEqual(result["correct"], 6)
        self.assertEqual(result["total"], 7)
        self.assertEqual(
            [(item["id"], item["correct"], item["total"]) for item in result["modules"]],
            [("listening", 2, 2), ("reading", 2, 2), ("grammar", 2, 3)],
        )

    def test_rejects_incomplete_or_invalid_answers(self):
        with self.assertRaises(ValueError):
            score_mock_answers({})
        answers = {question.id: question.correct for question in QUESTIONS}
        answers["l1"] = 99
        with self.assertRaises(ValueError):
            score_mock_answers(answers)

    def test_three_original_variants_rotate_by_iso_week_and_keep_structure(self):
        self.assertEqual(len(VARIANTS), 3)
        self.assertEqual([weekly_mock_variant(date(2026, 1, day)).id for day in (1, 5, 12)], [
            "b1-weekly-v1", "b1-weekly-v2", "b1-weekly-v3",
        ])
        for variant in VARIANTS:
            self.assertEqual((variant.origin, variant.created_for), ("original", "PolskiFlow"))
            self.assertEqual(variant.verified_at, date(2026, 10, 1))
            self.assertEqual(len(variant.questions), 7)
            self.assertEqual(
                [sum(question.module == module for question in variant.questions) for module in ("listening", "reading", "grammar")],
                [2, 2, 3],
            )
            self.assertTrue(all(len(set(question.options)) == 3 for question in variant.questions))
            self.assertTrue(all(0 <= question.correct < 3 for question in variant.questions))
            counts = [sum(question.correct == index for question in variant.questions) for index in range(3)]
            self.assertTrue(all(count >= 2 for count in counts), counts)


class B1WeeklyMockViewTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser("user-123", "learner@example.com"),
        )
        auth.start()
        self.addCleanup(auth.stop)

    def test_all_five_modules_offer_closed_russian_help_for_polish_directions(self):
        response = self.client.get("/exam/b1/mock/")
        self.assertContains(response, '<details lang="ru">', count=5)
        self.assertNotContains(response, '<details lang="ru" open')
        for instruction in response.context["instructions"].values():
            self.assertContains(response, f'<p lang="pl">{instruction["polish"]}</p>', html=True)

    def test_get_shows_five_modules_but_hides_answers_and_transcript(self):
        response = self.client.get("/exam/b1/mock/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Пробный мини‑модуль")
        self.assertContains(response, "15:00")
        self.assertContains(response, "Аудирование")
        self.assertContains(response, "Письмо")
        self.assertContains(response, "Говорение")
        self.assertNotContains(response, "Nagranie mówi")
        self.assertNotContains(response, "Баллы относятся")
        self.assertContains(response, '<main ', count=1)
        self.assertContains(response, 'role="timer" aria-live="off"')
        self.assertContains(response, 'id="mock-timer-status" role="status"')

    @patch("polskiflow.b1_mock_views.load_b1_mock_attempts", return_value=[{
        "attempted_at": "2026-10-01T08:00:00Z", "listening_correct": 2,
        "reading_correct": 2, "grammar_correct": 3,
    }])
    @patch("polskiflow.b1_mock_views.save_b1_mock_attempt", return_value=True)
    def test_post_scores_answers_saves_aggregates_and_reveals_explanations(self, save_attempt, _history):
        get_response = self.client.get("/exam/b1/mock/")
        payload = {"attempt_token": get_response.context["attempt_token"]}
        questions = get_response.context["questions"]
        payload.update({f"answer_{question.id}": str(question.correct) for question in questions})

        response = self.client.post("/exam/b1/mock/", payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "7 из 7")
        self.assertContains(response, "100%", count=3)
        self.assertContains(response, questions[0].explanation)
        self.assertContains(response, "не равны результату государственного экзамена")
        self.assertContains(response, "Агрегированный результат сохранён")
        self.assertContains(response, "2026-10-01")
        save_attempt.assert_called_once()
        saved_attempt_id = save_attempt.call_args.args[2]
        UUID(saved_attempt_id)
        saved_result = save_attempt.call_args.args[3]
        self.assertNotIn("answers", saved_result)
        self.assertEqual(saved_result["attempt_version"], get_response.context["variant"].id)

    @patch("polskiflow.b1_mock_views.load_b1_mock_attempts", return_value=[])
    @patch("polskiflow.b1_mock_views.save_b1_mock_attempt", return_value=True)
    def test_replayed_submission_reuses_the_same_idempotency_key(self, save_attempt, _history):
        opened = self.client.get("/exam/b1/mock/")
        payload = {"attempt_token": opened.context["attempt_token"]}
        payload.update({
            f"answer_{question.id}": question.correct
            for question in opened.context["questions"]
        })

        first = self.client.post("/exam/b1/mock/", payload)
        second = self.client.post("/exam/b1/mock/", payload)

        self.assertEqual((first.status_code, second.status_code), (200, 200))
        self.assertEqual(save_attempt.call_count, 2)
        self.assertEqual(
            save_attempt.call_args_list[0].args[2],
            save_attempt.call_args_list[1].args[2],
        )
        UUID(save_attempt.call_args_list[0].args[2])

    @patch("polskiflow.b1_mock_views.load_b1_mock_attempts", return_value=[])
    @patch("polskiflow.b1_mock_views.save_b1_mock_attempt", return_value=True)
    def test_signed_variant_survives_week_change(self, _save, _history):
        with patch("polskiflow.b1_mock_views.timezone.localdate", return_value=date(2026, 1, 5)):
            opened = self.client.get("/exam/b1/mock/")
        self.assertEqual(opened.context["variant"].id, "b1-weekly-v2")
        payload = {"attempt_token": opened.context["attempt_token"]}
        payload.update({f"answer_{question.id}": question.correct for question in opened.context["questions"]})

        with patch("polskiflow.b1_mock_views.timezone.localdate", return_value=date(2026, 1, 12)):
            submitted = self.client.post("/exam/b1/mock/", payload)

        self.assertEqual(submitted.status_code, 200)
        self.assertEqual(submitted.context["variant"].id, "b1-weekly-v2")
        self.assertContains(submitted, "7 из 7")

    def test_post_rejects_incomplete_unknown_and_cross_user_payloads(self):
        token = self.client.get("/exam/b1/mock/").context["attempt_token"]
        incomplete = self.client.post("/exam/b1/mock/", {"attempt_token": token})
        unknown = self.client.post("/exam/b1/mock/", {"attempt_token": token, "unexpected": "1"})
        foreign = signing.dumps({"user_id": "another-user"}, salt="polskiflow.b1-weekly-mock")
        payload = {"attempt_token": foreign, **{f"answer_{item.id}": item.correct for item in QUESTIONS}}
        cross_user = self.client.post("/exam/b1/mock/", payload)
        invalid_id = signing.dumps({
            "user_id": "user-123",
            "variant_id": "b1-weekly-v1",
            "attempt_id": "not-a-uuid",
        }, salt="polskiflow.b1-weekly-mock")
        bad_attempt = self.client.post("/exam/b1/mock/", {
            "attempt_token": invalid_id,
            **{f"answer_{item.id}": item.correct for item in QUESTIONS},
        })

        self.assertEqual(incomplete.status_code, 400)
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(cross_user.status_code, 400)
        self.assertEqual(bad_attempt.status_code, 400)
        self.assertContains(unknown, "неизвестные поля", status_code=400)

    @patch("polskiflow.b1_mock_views.save_b1_mock_attempt")
    def test_resume_restores_signed_variant_without_saving_result(self, save_attempt):
        with patch("polskiflow.b1_mock_views.timezone.localdate", return_value=date(2026, 1, 5)):
            opened = self.client.get("/exam/b1/mock/")
        with patch("polskiflow.b1_mock_views.timezone.localdate", return_value=date(2026, 1, 12)):
            resumed = self.client.post("/exam/b1/mock/", {
                "attempt_token": opened.context["attempt_token"], "resume": "1",
            })
        self.assertEqual(resumed.status_code, 200)
        self.assertEqual(resumed.context["variant"].id, opened.context["variant"].id)
        self.assertEqual(resumed.context["attempt_token"], opened.context["attempt_token"])
        self.assertIsNone(resumed.context["result"])
        save_attempt.assert_not_called()
        foreign = self.client.post("/exam/b1/mock/", {"attempt_token": "forged", "resume": "1"})
        self.assertEqual(foreign.status_code, 400)

    def test_guest_is_redirected_to_login(self):
        self.client.cookies.clear()
        self.assertRedirects(
            self.client.get("/exam/b1/mock/"),
            "/login/?next=%2Fexam%2Fb1%2Fmock%2F",
            fetch_redirect_response=False,
        )
