from unittest.mock import patch

from django.core import signing
from django.test import Client, TestCase

from polskiflow.public_views import DEMO_SALT, load_demo_question


class PublicDemoTests(TestCase):
    @patch("polskiflow.auth_views._daily_plan")
    @patch("polskiflow.auth_views.load_latest_lesson_draft")
    def test_guest_root_is_intro_without_loading_account_data(self, draft, plan):
        for path in ("/", "/start/"):
            response = self.client.get(path)
            self.assertTemplateUsed(response, "public_intro.html")
            self.assertContains(response, 'href="/demo/"')
            self.assertContains(response, 'href="/login/"')
            self.assertEqual(response["Cache-Control"], "private, no-store")
        draft.assert_not_called()
        plan.assert_not_called()
        self.assertEqual(self.client.head("/").status_code, 200)
        self.assertEqual(self.client.post("/").status_code, 405)

    def answer(self, value, **extra):
        response = self.client.get("/demo/")
        return self.client.post("/demo/", {"state": response.context["state"], "answer": value, **extra})

    def test_intro_demo_and_discovery_links_work_without_login(self):
        self.assertContains(self.client.get("/start/"), 'href="/demo/"')
        self.assertContains(self.client.get("/start/"), 'href="/register/"')
        for path in ("/login/", "/register/"):
            self.assertContains(self.client.get(path), 'href="/demo/"')
        response = self.client.get("/demo/")
        self.assertContains(response, 'name="answer"', count=4)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertNotContains(response, "Правильный ответ:")

    @patch("polskiflow.auth_views.save_profile_settings")
    @patch("polskiflow.lesson_views.save_lesson_completion_result")
    def test_correct_and_wrong_answers_explain_without_profile_or_progress_writes(self, completion, profile):
        question = load_demo_question()
        for value, passed in ((question["correct"], True), ((question["correct"] + 1) % 4, False)):
            response = self.answer(str(value), score="100")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["correct"], passed)
            self.assertContains(response, question["explanation"])
            self.assertContains(response, 'href="/register/"')
            self.assertContains(response, 'href="/demo/"')
        profile.assert_not_called()
        completion.assert_not_called()

    def test_invalid_duplicate_and_missing_values_are_rejected(self):
        for value in ("-1", "100", "true", "01", ["0", "1"]):
            self.assertEqual(self.answer(value).status_code, 400)
        self.assertEqual(self.client.post("/demo/", {}).status_code, 400)

    def test_signed_state_is_required_and_changed_bank_is_rejected(self):
        response = self.client.get("/demo/")
        self.assertEqual(self.client.post("/demo/", {"state": response.context["state"] + "bad", "answer": "1"}).status_code, 400)
        with patch("django.core.signing.TimestampSigner.unsign", side_effect=signing.SignatureExpired()):
            self.assertEqual(self.client.post("/demo/", {"state": response.context["state"], "answer": "1"}).status_code, 400)
        question = load_demo_question()
        question["prompt"] += " changed"
        with patch("polskiflow.public_views.load_demo_question", return_value=question):
            self.assertEqual(self.client.post("/demo/", {"state": response.context["state"], "answer": "1"}).status_code, 400)

    def test_csrf_and_methods(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post("/demo/", {}).status_code, 403)
        self.assertEqual(self.client.delete("/demo/").status_code, 405)
        self.assertEqual(self.client.post("/start/").status_code, 405)

    def test_unavailable_content_offers_return_to_intro(self):
        with patch("polskiflow.public_views.load_demo_question", return_value=None):
            response = self.client.get("/demo/")
        self.assertContains(response, "временно недоступно", status_code=503)
        self.assertContains(response, 'href="/start/"', status_code=503)

    def test_translated_intro_question_and_answer(self):
        for language, title, prompt in (("pl", "Zadanie próbne", "Jak przywitać się nieformalnie?"), ("en", "Sample exercise", "How do you greet someone informally?")):
            self.client.cookies["django_language"] = language
            self.assertContains(self.client.get("/demo/"), title)
            self.assertContains(self.client.get("/demo/"), prompt)
            self.assertEqual(self.answer("1").status_code, 200)
