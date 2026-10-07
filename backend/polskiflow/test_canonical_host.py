from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from django.http import HttpResponse

from polskiflow.canonical_host import CanonicalHostMiddleware, email_callback_url


@override_settings(ALLOWED_HOSTS=[".vercel.app", "testserver"])
class CanonicalHostTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.next = lambda request: HttpResponse("unchanged")
        self.middleware = CanonicalHostMiddleware(self.next)

    def test_old_browser_links_keep_path_and_query_on_new_domain(self):
        for host in ("polish-learn.vercel.app", "polskiflow-python.vercel.app"):
            request = self.factory.get("/reading/?level=B1&q=Anna", HTTP_HOST=host)
            response = self.middleware(request)
            self.assertEqual(response.status_code, 308)
            self.assertEqual(response["Location"], "https://lingoflow-learn.vercel.app/reading/?level=B1&q=Anna")
            self.assertEqual(response["Cache-Control"], "no-store")

    def test_current_preview_and_api_requests_are_not_redirected(self):
        for host, path in (
            ("lingoflow-learn.vercel.app", "/reading/"),
            ("branch-preview.vercel.app", "/reading/"),
            ("polish-learn.vercel.app", "/api/v1/me/profile/"),
            ("polish-learn.vercel.app", "/static/polskiflow/app.css"),
            ("polish-learn.vercel.app", "/service-worker.js"),
        ):
            with self.subTest(host=host, path=path):
                self.assertEqual(self.middleware(self.factory.get(path, HTTP_HOST=host)).status_code, 200)
        self.assertEqual(self.middleware(self.factory.post("/profile/", HTTP_HOST="polish-learn.vercel.app")).status_code, 200)

    def test_email_callback_gateway_keeps_existing_provider_allowlist(self):
        current = self.factory.get("/", HTTP_HOST="lingoflow-learn.vercel.app", secure=True)
        self.assertEqual(email_callback_url(current, "/reset-password/"), "https://polish-learn.vercel.app/reset-password/")
        callback = self.middleware(self.factory.get("/reset-password/", HTTP_HOST="polish-learn.vercel.app"))
        self.assertEqual(callback["Location"], "https://lingoflow-learn.vercel.app/reset-password/")
        local = self.factory.get("/", HTTP_HOST="testserver")
        self.assertEqual(email_callback_url(local, "/reset-password/"), "http://testserver/reset-password/")

    def test_new_domain_recovery_uses_the_gateway(self):
        from django.test import Client
        with patch("polskiflow.auth_views.request_password_reset") as recover, patch("polskiflow.auth_views.consume_auth_attempt", return_value=(True, 0)):
            response = Client().post("/forgot-password/", {"email": "learner@example.com"}, HTTP_HOST="lingoflow-learn.vercel.app", secure=True)
        self.assertEqual(response.status_code, 200)
        recover.assert_called_once_with("learner@example.com", "https://polish-learn.vercel.app/reset-password/")
