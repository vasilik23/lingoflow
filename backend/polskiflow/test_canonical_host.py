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
            ("polish-learn.vercel.app", "/offline/?shell=fixture&language=en"),
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

    def test_migration_notice_is_collapsed_and_only_on_login(self):
        from django.test import Client
        login = Client().get('/login/')
        self.assertContains(login, '<details class="migration-notice">')
        self.assertNotContains(login, '<details class="migration-notice" open')
        self.assertContains(login, 'https://lingoflow-learn.vercel.app/')
        self.assertContains(login, 'не переносятся автоматически')
        self.assertNotContains(Client().get('/register/'), 'class="migration-notice"')

    def test_manifest_stays_origin_relative_for_existing_installs(self):
        from django.test import Client
        for host in ('polish-learn.vercel.app', 'lingoflow-learn.vercel.app'):
            with self.subTest(host=host):
                response = Client().get('/manifest.webmanifest', HTTP_HOST=host)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['id'], '/')
                self.assertEqual(response.json()['start_url'], '/')
                self.assertEqual(response.json()['scope'], '/')

    def test_all_legacy_links_and_recovery_queries_keep_their_destination(self):
        from django.conf import settings
        for host in settings.LEGACY_APP_HOSTS:
            with self.subTest(host=host):
                response = self.middleware(self.factory.get('/reset-password/?next=%2Freading%2F', HTTP_HOST=host))
                self.assertEqual(response.status_code, 308)
                self.assertEqual(response['Location'], settings.PUBLIC_APP_ORIGIN + '/reset-password/?next=%2Freading%2F')
                self.assertNotIn('Set-Cookie', response)

    def test_legacy_worker_can_precache_its_public_offline_page(self):
        from django.test import Client
        response = Client().get("/offline/?shell=fixture&language=en", HTTP_HOST="polish-learn.vercel.app")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Language"], "en")
        self.assertNotIn("Location", response)
