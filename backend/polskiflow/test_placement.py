from unittest.mock import patch

from django.test import TestCase, Client
from django.core.signing import SignatureExpired
from django.utils import translation
import re

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.placement import evaluate
from polskiflow.placement_views import load_questions


class PlacementTests(TestCase):
    def test_every_selected_russian_prompt_option_and_explanation_is_translated(self):
        for lang in ("pl", "en"):
            with translation.override(lang):
                for question in load_questions():
                    for text in [question["prompt"], question["explanation"], *question["options"]]:
                        if re.search("[А-Яа-яЁё]", text):
                            self.assertNotRegex(translation.gettext(text), "[А-Яа-яЁё]", msg=f"{lang}: {text}")

    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("owner", "owner@example.test"))
        auth.start()
        self.addCleanup(auth.stop)

    def advance(self, response, answers):
        return self.client.post("/welcome/check/", {"state": response.context["state"], **{f"answer_{i}": str(answer) for i, answer in enumerate(answers)}})

    def test_existing_active_bank_and_no_answers_leaked_before_result(self):
        bank = load_questions()
        self.assertEqual(len(bank), 12)
        self.assertGreater(len({q["correct"] for q in bank}), 1)
        response = self.client.get("/welcome/check/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="answer_0"')
        self.assertNotContains(response, "correct_text")
        self.assertEqual(response["Cache-Control"], "private, no-store")

    @patch("polskiflow.auth_views.save_profile_settings")
    @patch("polskiflow.lesson_views.save_lesson_completion_result")
    def test_complete_check_recommends_without_profile_or_progress_writes(self, completion, profile):
        bank = load_questions()
        response = self.client.get("/welcome/check/")
        for offset in range(0, 12, 3):
            response = self.advance(response, [q["correct"] for q in bank[offset:offset + 3]])
            self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["result"].level, "B2")
        self.assertTrue(response.context["result"].strong_b2)
        self.assertContains(response, "/welcome/?suggested_level=B2")
        self.assertEqual(len(response.context["reviews"]), 12)
        profile.assert_not_called()
        completion.assert_not_called()

    def test_unknown_and_advanced_answers_do_not_mask_foundation_gaps(self):
        bank = load_questions()
        answers = [q["correct"] for q in bank]
        for block, level in enumerate(("A1", "A2", "B1", "B2")):
            changed = answers.copy()
            changed[block * 3:block * 3 + 2] = [-1, -1]
            self.assertEqual(evaluate(bank, changed).level, level)
        self.assertEqual(evaluate(bank, [-1] * 12).level, "A1")
        with self.assertRaises(ValueError):
            evaluate(bank, [])

    def test_invalid_or_missing_answers_restart_with_error(self):
        response = self.client.get("/welcome/check/")
        for answers in ({}, {"answer_0": "100", "answer_1": "0", "answer_2": "0"}, {"answer_0": ["0", "1"], "answer_1": "0", "answer_2": "0"}):
            failed = self.client.post("/welcome/check/", {"state": response.context["state"], **answers})
            self.assertEqual(failed.status_code, 400)
            self.assertEqual(failed.context["step"], 1)

    def test_signed_state_rejects_tampering_and_cross_owner(self):
        response = self.client.get("/welcome/check/")
        bad = self.client.post("/welcome/check/", {"state": response.context["state"] + "changed"})
        self.assertEqual(bad.status_code, 400)
        with patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("other", "other@example.test")):
            self.assertEqual(self.advance(response, [0, 0, 0]).status_code, 400)

    def test_expired_or_changed_question_bank_state_is_rejected(self):
        response = self.client.get("/welcome/check/")
        with patch("django.core.signing.TimestampSigner.unsign", side_effect=SignatureExpired()):
            self.assertEqual(self.advance(response, [0, 0, 0]).status_code, 400)
        bank = load_questions()
        bank[0]["prompt"] += " changed"
        with patch("polskiflow.placement_views.load_questions", return_value=bank):
            self.assertEqual(self.advance(response, [0, 0, 0]).status_code, 400)

    def test_unavailable_bank_offers_manual_choice(self):
        with patch("polskiflow.placement_views.load_questions", return_value=[]):
            response = self.client.get("/welcome/check/")
        self.assertContains(response, "Выбери уровень самостоятельно", status_code=503)
        self.assertNotContains(response, 'name="state"', status_code=503)

    def test_login_and_csrf_are_required(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/welcome/check/").status_code, 302)
        csrf = Client(enforce_csrf_checks=True)
        csrf.cookies[ACCESS_COOKIE] = "access"
        self.assertEqual(csrf.post("/welcome/check/", {}).status_code, 403)

    def test_translated_page_and_skip_link(self):
        for lang, title in (("pl", "Sprawdzenie poziomu startowego"), ("en", "Starting level check")):
            self.client.cookies["django_language"] = lang
            with translation.override(lang):
                response = self.client.get("/welcome/check/")
                self.assertContains(response, title)
                self.assertContains(response, 'href="/welcome/"')
