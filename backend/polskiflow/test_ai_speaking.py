import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core import signing
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, override_settings
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.ai_speaking import SALT, MAX_AUDIO_BYTES, speaking_token, transcribe_audio, review_speaking
from polskiflow.ai_writing import WritingAIUnavailable
from polskiflow.test_ai_writing import feedback


@override_settings(GROQ_SPEAKING_ENABLED=True, GROQ_API_KEY="test-only")
class AISpeakingTests(SimpleTestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("owner", "private@example.test"))
        auth.start(); self.addCleanup(auth.stop)
        quota = patch("polskiflow.ai_speaking_views.consume_distributed_api_mutation", return_value=(True, 86400))
        self.consume = quota.start(); self.addCleanup(quota.stop)
        self.token = speaking_token("owner", [SimpleNamespace(prompt="Opisz sytuację.")])
        self.assignment = signing.loads(self.token, salt=SALT)["assignment"]
        self.receipt = signing.dumps({"owner":"owner", "assignment":self.assignment, "stage":"transcript"}, salt=SALT)

    def upload(self, token=None, consent="true", data=b"\x1aE\xdf\xa3audio", mime="audio/webm"):
        return self.client.post("/speaking/ai-transcribe/", {"token":token or self.token, "consent":consent,
            "audio":SimpleUploadedFile("private-name.webm", data, content_type=mime)})

    def review(self, **updates):
        return self.client.post("/speaking/ai-review/", json.dumps({"token":self.receipt,"text":"Mam problem","consent":True,"confirmed":True,**updates}), content_type="application/json")

    @patch("polskiflow.ai_speaking_views.transcribe_audio", return_value="Mam problem")
    def test_transcription_receipt_is_owner_bound_and_uses_shared_quota(self, transcribe):
        response = self.upload()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response.json()["text"], "Mam problem")
        self.assertFalse(response.json()["persisted"])
        receipt = signing.loads(response.json()["token"], salt=SALT)
        self.assertEqual(receipt, {"owner":"owner", "assignment":self.assignment, "stage":"transcript"})
        self.consume.assert_called_once_with("access", "ai_writing")
        transcribe.assert_called_once_with(b"\x1aE\xdf\xa3audio", "webm", "audio/webm")

    @patch("polskiflow.ai_speaking_views.transcribe_audio")
    def test_upload_requires_consent_owner_stage_and_real_container(self, transcribe):
        foreign = speaking_token("someone-else", [SimpleNamespace(prompt="Task")])
        for options in ({"consent":"false"}, {"token":foreign}, {"token":self.receipt}, {"token":"bad"}, {"data":b"<html>bad</html>"}, {"mime":"image/png"}):
            self.assertEqual(self.upload(**options).status_code, 400)
        self.consume.assert_not_called(); transcribe.assert_not_called()

    @patch("polskiflow.ai_speaking_views.transcribe_audio", return_value="Mam problem")
    def test_mp4_and_ogg_supported_and_audio_never_uses_temporary_files(self, transcribe):
        with patch("django.core.files.uploadhandler.TemporaryFileUploadHandler.new_file", side_effect=AssertionError("must stay in memory")):
            for data, mime in ((b"\x00\x00\x00\x18ftypisom", "audio/mp4"), (b"OggSaudio", "audio/ogg")):
                self.assertEqual(self.upload(data=data,mime=mime).status_code, 200)
        self.assertEqual(self.upload(data=b"\x1aE\xdf\xa3" + b"a" * MAX_AUDIO_BYTES).status_code, 413)
        self.assertEqual(transcribe.call_count,2)

    @patch("polskiflow.ai_speaking_views.review_speaking", return_value={"assessment":"ai_speech_transcript","pronunciation_assessed":False})
    def test_review_requires_confirmed_transcript_receipt_and_sends_edited_text(self, review):
        for options in ({"confirmed":False}, {"consent":False}, {"confirmed":1}, {"token":self.token}, {"text":" "}, {"text":"a"*6001}):
            self.assertEqual(self.review(**options).status_code, 400)
        self.consume.assert_not_called(); review.assert_not_called()
        response = self.review(text="Poprawiony tekst")
        self.assertEqual(response.status_code, 200)
        review.assert_called_once_with(self.assignment,"Poprawiony tekst","ru")
        self.assertFalse(response.json()["result"]["pronunciation_assessed"])

    @patch("polskiflow.ai_speaking_views.transcribe_audio")
    @patch("polskiflow.ai_speaking_views.review_speaking")
    def test_disabled_unavailable_and_limited_requests_never_call_provider(self, review, transcribe):
        with override_settings(GROQ_SPEAKING_ENABLED=False):
            self.assertEqual(self.upload().status_code, 503)
            self.assertEqual(self.review().status_code, 503)
            with self.assertRaises(WritingAIUnavailable): transcribe_audio(b"OggSaudio", "ogg", "audio/ogg")
            with self.assertRaises(WritingAIUnavailable): review_speaking(self.assignment, "Mam problem", "ru")
        self.consume.assert_not_called()
        self.consume.return_value = None
        self.assertEqual(self.upload().status_code, 503)
        self.assertEqual(self.review().status_code, 503)
        self.consume.return_value = (False,123)
        for response in (self.upload(),self.review()):
            self.assertEqual(response.status_code,429)
            self.assertEqual(response["Retry-After"],"123")
        transcribe.assert_not_called(); review.assert_not_called()

    def test_methods_auth_csrf_and_expiry(self):
        for path in ("/speaking/ai-transcribe/","/speaking/ai-review/"):
            self.assertEqual(self.client.get(path).status_code,405)
        protected = Client(enforce_csrf_checks=True)
        protected.cookies[ACCESS_COOKIE] = "access"
        self.assertEqual(protected.post("/speaking/ai-transcribe/",{"token":self.token,"consent":"true","audio":SimpleUploadedFile("a.webm",b"audio")}).status_code,403)
        self.assertEqual(protected.post("/speaking/ai-review/","{}",content_type="application/json").status_code,403)
        with patch("django.core.signing.time.time",return_value=0):
            expired = speaking_token("owner",[SimpleNamespace(prompt="Task")])
        self.assertEqual(self.upload(token=expired).status_code,400)
        self.client.cookies.clear()
        self.assertEqual(self.upload().status_code,401)
        self.assertEqual(self.review().status_code,401)
        self.consume.assert_not_called()

    @patch("polskiflow.ai_speaking_views.transcribe_audio", side_effect=WritingAIUnavailable)
    @patch("polskiflow.ai_speaking_views.review_speaking", side_effect=WritingAIUnavailable)
    def test_provider_failure_does_not_expose_audio_or_credentials(self, review, transcribe):
        for response in (self.upload(),self.review()):
            self.assertEqual(response.status_code,503)
            self.assertNotIn("test-only",response.content.decode())
            self.assertNotIn("Mam problem",response.content.decode())

    @patch("polskiflow.ai_speaking.urlopen")
    def test_provider_transcribes_polish_without_filename_identity_or_task(self, transport):
        transport.return_value.__enter__.return_value = BytesIO(b'{"text":"Mam problem"}')
        self.assertEqual(transcribe_audio(b"OggSaudio","ogg","audio/ogg"),"Mam problem")
        request = transport.call_args.args[0]
        self.assertEqual(request.full_url,"https://api.groq.com/openai/v1/audio/transcriptions")
        self.assertIn(b'filename="answer.ogg"', request.data)
        self.assertIn(b'\r\n\r\npl\r\n', request.data)
        self.assertNotIn(b"owner",request.data)
        self.assertNotIn(b"private-name",request.data)
        self.assertEqual(transport.call_args.kwargs["timeout"],25)
        for data in (b"not json",b'{"text":""}',b'{"text":true}',json.dumps({"text":"a"*6001}).encode()):
            transport.return_value.__enter__.return_value=BytesIO(data)
            with self.assertRaises(WritingAIUnavailable): transcribe_audio(b"OggSaudio","ogg","audio/ogg")

    @patch("polskiflow.ai_writing.urlopen")
    def test_speech_feedback_has_no_pronunciation_grade_and_validates_quotes(self, transport):
        payload={"choices":[{"finish_reason":"stop","message":{"content":json.dumps(feedback())}}]}
        transport.return_value.__enter__.return_value=BytesIO(json.dumps(payload).encode())
        result=review_speaking(self.assignment,"Mam problem","en")
        self.assertEqual(result["assessment"],"ai_speech_transcript")
        self.assertFalse(result["pronunciation_assessed"])
        instruction=json.loads(transport.call_args.args[0].data)["messages"][0]["content"]
        self.assertIn("Never evaluate pronunciation",instruction)
        self.assertIn("English",instruction)
        payload["choices"][0]["message"]["content"]=json.dumps(feedback("invented"))
        transport.return_value.__enter__.return_value=BytesIO(json.dumps(payload).encode())
        with self.assertRaises(WritingAIUnavailable): review_speaking(self.assignment,"Mam problem","en")

    def test_speaking_panel_is_opt_in_and_disabled_without_flag(self):
        import time
        from polskiflow.b1_run_views import RUN_SALT
        state = dict(self.client.get("/exam/b1/run/").context["state"], phase="part", step=4, deadline=int(time.time())+600,
                     results=[{"id":part,"status":"skipped"} for part in ("listening","reading","grammar","writing")])
        fields = {"run_token":signing.dumps(state,salt=RUN_SALT),"action":"resume"}
        page = self.client.post("/exam/b1/run/",fields)
        self.assertContains(page,"data-ai-speaking")
        self.assertContains(page,"data-ai-confirmed")
        signed = signing.loads(page.context["speech_ai_token"],salt=SALT)
        self.assertEqual(signed["owner"],"owner")
        self.assertEqual(signed["stage"],"recording")
        self.assertEqual(signed["assignment"]["task"], "\n\n".join(task.prompt for task in page.context["speaking_tasks"]))
        self.assertEqual(signed["assignment"]["tasks"][1]["image_description"], page.context["speaking_tasks"][1].image_description)
        self.assertEqual(signed["assignment"]["tasks"][2]["dialogue_turns"], list(page.context["speaking_tasks"][2].dialogue_turns))
        with override_settings(GROQ_SPEAKING_ENABLED=False):
            disabled = self.client.post("/exam/b1/run/",fields)
        self.assertContains(disabled,"ИИ речи пока не подключён")
        self.assertNotContains(disabled,"data-ai-transcribe")
        self.consume.assert_not_called()

    def test_browser_consent_and_stale_transcription_cleanup(self):
        import subprocess
        from pathlib import Path
        result = subprocess.run(["node", str(Path(__file__).with_name("test_ai_speaking_ui.cjs"))], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
