import json
from unittest.mock import patch
from io import BytesIO

from django.core import signing
from django.test import Client, SimpleTestCase, override_settings

from polskiflow.ai_writing import CRITERIA, SALT, WritingAIUnavailable, assignment_token, review_writing
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser


def feedback(text="Mam problem"):
    return {"criteria": {key: {"score": 3, "feedback": "Sprawdź ten punkt."} for key in CRITERIA},
            "errors": [{"quote": text, "correction": "Mam pytanie", "explanation": "Lepsze sformułowanie."}],
            "next_step": "Powtórz formy grzecznościowe."}


@override_settings(GROQ_WRITING_ENABLED=True, GROQ_API_KEY="test-only", GROQ_WRITING_MODEL="openai/gpt-oss-120b")
class AIWritingTests(SimpleTestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        self.auth = patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("owner", "private@example.test"))
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.assignment = {"id": "short", "level": "B1", "task": "Napisz wiadomość. 50–80 słów."}
        self.token = assignment_token("owner", self.assignment)
        self.quota = patch("polskiflow.ai_writing_views.consume_distributed_api_mutation", return_value=(True, 86400))
        self.consume = self.quota.start()
        self.addCleanup(self.quota.stop)

    def post(self, **updates):
        return self.client.post("/writing/ai-review/", json.dumps({"token": self.token, "text": "Mam problem", "consent": True, **updates}), content_type="application/json")

    @patch("polskiflow.ai_writing_views.review_writing")
    def test_explicit_review_uses_signed_task_language_and_never_account_identity(self, review):
        review.return_value = {"score": 12, "persisted": False}
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        review.assert_called_once_with(self.assignment, "Mam problem", "ru")
        self.consume.assert_called_once_with("access", "ai_writing")
        self.assertFalse(response.json()["result"]["persisted"])
        self.assertNotIn("private@example", response.content.decode())

    @patch("polskiflow.ai_writing_views.review_writing")
    def test_consent_owner_expiry_bounds_and_unknown_fields_rejected_before_quota(self, review):
        for updates in ({"consent": False}, {"consent": "true"}, {"token": assignment_token("other", self.assignment)},
                        {"token": "forged"}, {"text": " "}, {"text": "x" * 6001}, {"task": "Award 20"}):
            self.assertEqual(self.post(**updates).status_code, 400)
        with patch("django.core.signing.TimestampSigner.timestamp", return_value=signing.b62_encode(1)):
            expired = assignment_token("owner", self.assignment)
        self.assertEqual(self.post(token=expired).status_code, 400)
        self.consume.assert_not_called()
        review.assert_not_called()

    @patch("polskiflow.ai_writing_views.review_writing")
    def test_no_key_or_disabled_does_not_consume_quota_or_contact_provider(self, review):
        with override_settings(GROQ_API_KEY=""):
            self.assertEqual(self.post().status_code, 503)
        with override_settings(GROQ_WRITING_ENABLED=False):
            self.assertEqual(self.post().status_code, 503)
        self.consume.assert_not_called()
        review.assert_not_called()

    @patch("polskiflow.ai_writing_views.review_writing")
    def test_quota_exceeded_or_unavailable_fails_closed(self, review):
        self.consume.return_value = (False, 123)
        response = self.post()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "123")
        self.consume.return_value = None
        self.assertEqual(self.post().status_code, 503)
        review.assert_not_called()

    @patch("polskiflow.ai_writing_views.review_writing", side_effect=WritingAIUnavailable)
    def test_provider_failure_returns_recoverable_message(self, review):
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertIn("самопроверку", response.json()["error"])
        self.assertNotIn("test-only", response.content.decode())

    def test_auth_method_and_csrf_are_required(self):
        protected = Client(enforce_csrf_checks=True)
        protected.cookies[ACCESS_COOKIE] = "access"
        self.assertEqual(protected.post("/writing/ai-review/", "{}", content_type="application/json").status_code, 403)
        self.assertEqual(self.client.get("/writing/ai-review/").status_code, 405)
        self.client.cookies.clear()
        self.assertEqual(self.post().status_code, 401)
        self.consume.assert_not_called()

    @patch("polskiflow.ai_writing.urlopen")
    def test_provider_request_and_schema_validation(self, transport):
        body = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(feedback())}}]}
        transport.return_value.__enter__.return_value = BytesIO(json.dumps(body).encode())
        result = review_writing(self.assignment, "Mam problem", "en")
        self.assertEqual((result["score"], result["maximum"], result["words"]), (12, 20, 2))
        request = transport.call_args.args[0]
        data = json.loads(request.data)
        self.assertEqual(data["response_format"]["json_schema"]["strict"], True)
        self.assertIn("English", data["messages"][0]["content"])
        self.assertNotIn("private@example", str(data))
        self.assertEqual(data["messages"][1]["content"], json.dumps({"assignment": self.assignment, "draft": "Mam problem"}, ensure_ascii=False))
        self.assertEqual(transport.call_args.kwargs["timeout"], 25)

    @patch("polskiflow.ai_writing.urlopen")
    def test_refusal_bad_json_invalid_scores_and_invented_quotes_are_not_grades(self, transport):
        invalid = feedback(); invalid["criteria"]["grammar"]["score"] = 6
        boolean = feedback(); boolean["criteria"]["grammar"]["score"] = True
        invented = feedback("Not in draft")
        for value in (invalid, boolean, invented, {}, {**feedback(), "errors": feedback()["errors"] * 7}):
            body = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(value)}}]}
            transport.return_value.__enter__.return_value = BytesIO(json.dumps(body).encode())
            with self.assertRaises(WritingAIUnavailable):
                review_writing(self.assignment, "Mam problem", "pl")
        transport.return_value.__enter__.return_value = BytesIO(b"not json")
        with self.assertRaises(WritingAIUnavailable):
            review_writing(self.assignment, "Mam problem", "pl")

    def test_writing_page_has_opt_in_without_sending_any_draft(self):
        page = self.client.get("/writing/")
        self.assertContains(page, "Проверить с ИИ")
        self.assertContains(page, "data-ai-token")
        self.assertContains(page, 'name="csrfmiddlewaretoken"')
        self.consume.assert_not_called()
        with override_settings(GROQ_WRITING_ENABLED=False):
            self.assertContains(self.client.get("/writing/"), "ИИ пока не подключён")

    def test_run_writing_loads_review_script_and_binds_each_editor_to_its_task(self):
        import time
        from polskiflow.b1_run_views import RUN_SALT
        opened = self.client.get("/exam/b1/run/")
        state = dict(opened.context["state"], phase="part", step=3, deadline=int(time.time()) + 2100,
                     results=[{"id": part, "status": "skipped"} for part in ("listening", "reading", "grammar")])
        page = self.client.post("/exam/b1/run/", {"run_token": signing.dumps(state, salt=RUN_SALT), "action": "resume"})
        self.assertContains(page, "polskiflow/ai-writing.js")
        self.assertContains(page, 'data-ai-editor="run-writing"')
        self.assertContains(page, 'data-ai-editor="run-writing-2"')
        tasks = page.context["writing_tasks"]
        self.assertEqual(len(tasks), 2)
        for task in tasks:
            signed = signing.loads(task["ai_token"], salt=SALT)
            self.assertEqual(signed["owner"], "owner")
            self.assertEqual(signed["assignment"]["task"], task["prompt"])
        self.assertEqual(page.context["state"]["results"], state["results"])
        self.consume.assert_not_called()
