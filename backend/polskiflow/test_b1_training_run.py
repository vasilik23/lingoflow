import time
import subprocess
from pathlib import Path
from unittest.mock import patch

from django.test import Client, TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.b1_run_views import BREAK_SECONDS, RUN_MAX_AGE


class B1TrainingRunTests(TestCase):
    def test_local_recording_lifecycle(self):
        result = subprocess.run(
            ["node", str(Path(__file__).with_name("test_b1_run_recorder.cjs"))],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_listening_limits_pause_and_resume(self):
        result = subprocess.run(
            ["node", str(Path(__file__).with_name("test_b1_run_listening.cjs"))],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        opened = self.advance(self.client.get("/exam/b1/run/"), "start")
        self.assertContains(opened, "data-run-audio-stop")
        self.assertContains(opened, "два прослушивания")

    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        self.now = int(time.time())
        for target, kwargs in (
            ("polskiflow.auth.authenticate_access_token", {"return_value": SupabaseUser("user-123", "learner@example.com")}),
            ("polskiflow.b1_run_views.time.time", {"side_effect": lambda: self.now}),
        ):
            mocked = patch(target, **kwargs)
            mocked.start()
            self.addCleanup(mocked.stop)

    def advance(self, response, action, **fields):
        return self.client.post("/exam/b1/run/", {
            "run_token": response.context["run_token"], "action": action, **fields,
        })

    def test_complete_run_has_five_results_without_grading_free_production(self):
        response = self.advance(self.client.get("/exam/b1/run/"), "start")
        run_id = response.context["state"]["run_id"]
        for index in range(5):
            self.assertEqual(response.context["state"]["step"], index)
            part = response.context["part"]
            fields = {f"answer_{q.id}": q.correct for q in response.context["questions"]}
            if part["mode"] == "self_review":
                fields = {"reviewed": "on"}
            response = self.advance(response, "finish", **fields)
            self.assertEqual(response.status_code, 200)
            if index < 4:
                self.assertEqual(response.context["state"]["phase"], "break")
                self.now += BREAK_SECONDS
                response = self.advance(response, "start")
        self.assertEqual(response.context["state"]["phase"], "report")
        self.assertEqual(response.context["state"]["run_id"], run_id)
        report = response.context["report"]
        self.assertEqual([item["status"] for item in report], ["scored"] * 3 + ["self_review"] * 2)
        self.assertEqual([item["total"] for item in report[:3]], [5, 5, 6])
        self.assertTrue(all(item["percent"] == 100 for item in report[:3]))
        self.assertTrue(all("percent" not in item for item in report[3:]))
        self.assertTrue(all("details" not in item for item in response.context["state"]["results"]))
        self.assertContains(response, "Итог по пяти модулям")
        self.assertContains(response, "Общего балла нет")
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_break_and_part_deadline_cannot_be_bypassed_by_post(self):
        opened = self.advance(self.client.get("/exam/b1/run/"), "start")
        fields = {f"answer_{q.id}": q.correct for q in opened.context["questions"]}
        self.now = opened.context["state"]["deadline"]
        late = self.advance(opened, "finish", **fields)
        self.assertEqual(late.status_code, 400)
        self.assertEqual(late.context["state"]["results"], [])
        skipped = self.advance(opened, "skip", **fields)
        self.assertEqual(skipped.context["state"]["results"][0]["status"], "skipped")
        early = self.advance(skipped, "start")
        self.assertEqual(early.status_code, 400)
        self.assertEqual(early.context["state"]["phase"], "break")
        self.now += BREAK_SECONDS
        self.assertEqual(self.advance(skipped, "start").context["part"]["id"], "reading")

    def test_resume_preserves_deadline_variant_and_result_without_answers(self):
        opened = self.advance(self.client.get("/exam/b1/run/"), "start")
        self.now += 20
        resumed = self.advance(opened, "resume")
        self.assertEqual(resumed.context["state"], opened.context["state"])
        self.assertEqual(resumed.context["run_token"], opened.context["run_token"])
        self.assertEqual(resumed.context["timer_seconds"], 8 * 60 - 20)
        denied = self.advance(opened, "resume", answer_l1="0")
        self.assertEqual(denied.status_code, 400)

    def test_tampering_foreign_account_and_overall_expiry_are_rejected(self):
        opened = self.client.get("/exam/b1/run/")
        tampered = self.client.post("/exam/b1/run/", {"run_token": opened.context["run_token"] + "tampered", "action": "start"})
        self.assertEqual(tampered.status_code, 400)
        with patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("other-user", "other@example.com")):
            self.assertEqual(self.advance(opened, "resume").status_code, 400)
        self.now += RUN_MAX_AGE
        expired = self.advance(opened, "resume")
        self.assertEqual(expired.status_code, 400)
        self.assertTrue(expired.context["discard_draft"])
        self.assertEqual(expired.context["state"]["phase"], "intro")

    def test_free_text_is_never_accepted_and_self_review_requires_confirmation(self):
        response = self.advance(self.client.get("/exam/b1/run/"), "start")
        for _ in range(3):
            response = self.advance(response, "skip")
            self.now += BREAK_SECONDS
            response = self.advance(response, "start")
        self.assertEqual(response.context["part"]["id"], "writing")
        self.assertContains(response, '<textarea id="run-writing"')
        self.assertNotContains(response, 'name="writing"')
        self.assertEqual(self.advance(response, "finish").status_code, 400)
        self.assertEqual(self.advance(response, "finish", reviewed="on", writing="private text").status_code, 400)
        completed = self.advance(response, "finish", reviewed="on")
        self.assertEqual(completed.context["state"]["results"][-1], {"id": "writing", "status": "self_review"})
        self.now += BREAK_SECONDS
        speaking = self.advance(completed, "start")
        self.assertContains(speaking, "data-run-recorder")
        self.assertEqual(self.advance(speaking, "finish", reviewed="on", audio="private audio").status_code, 400)
        self.assertEqual(self.advance(speaking, "finish", reviewed="on").status_code, 200)

    def test_guest_and_csrf_boundaries(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.cookies[ACCESS_COOKIE] = "access"
        self.assertEqual(csrf.post("/exam/b1/run/", {"action": "start"}).status_code, 403)
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/exam/b1/run/").status_code, 302)
