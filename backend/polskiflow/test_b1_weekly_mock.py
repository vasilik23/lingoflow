from unittest.mock import patch

from django.core import signing
from django.test import SimpleTestCase, TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.b1_weekly_mock import QUESTIONS, score_mock_answers


class B1WeeklyMockDomainTests(SimpleTestCase):
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


class B1WeeklyMockViewTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser("user-123", "learner@example.com"),
        )
        auth.start()
        self.addCleanup(auth.stop)

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

    def test_post_scores_answers_and_reveals_explanations(self):
        get_response = self.client.get("/exam/b1/mock/")
        payload = {"attempt_token": get_response.context["attempt_token"]}
        payload.update({f"answer_{question.id}": str(question.correct) for question in QUESTIONS})

        response = self.client.post("/exam/b1/mock/", payload)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "7 из 7")
        self.assertContains(response, "100%", count=3)
        self.assertContains(response, "Nagranie mówi")
        self.assertContains(response, "не равны результату государственного экзамена")

    def test_post_rejects_incomplete_unknown_and_cross_user_payloads(self):
        token = self.client.get("/exam/b1/mock/").context["attempt_token"]
        incomplete = self.client.post("/exam/b1/mock/", {"attempt_token": token})
        unknown = self.client.post("/exam/b1/mock/", {"attempt_token": token, "unexpected": "1"})
        foreign = signing.dumps({"user_id": "another-user"}, salt="polskiflow.b1-weekly-mock")
        payload = {"attempt_token": foreign, **{f"answer_{item.id}": item.correct for item in QUESTIONS}}
        cross_user = self.client.post("/exam/b1/mock/", payload)

        self.assertEqual(incomplete.status_code, 400)
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(cross_user.status_code, 400)
        self.assertContains(unknown, "неизвестные поля", status_code=400)

    def test_guest_is_redirected_to_login(self):
        self.client.cookies.clear()
        self.assertRedirects(
            self.client.get("/exam/b1/mock/"),
            "/login/?next=%2Fexam%2Fb1%2Fmock%2F",
            fetch_redirect_response=False,
        )
