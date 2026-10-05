from unittest.mock import patch

from django.core.cache import cache
from django.http import HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings

from polskiflow.auth import ACCESS_COOKIE, SupabaseAuthError, SupabaseUser
from polskiflow.auth_cache import AuthFormCacheMiddleware


class AuthCacheMiddlewareTests(SimpleTestCase):
    def test_all_statuses_and_canonical_redirects_are_private(self):
        for path in ("/login/", "/register/", "/login", "/register"):
            for status in (200, 302, 403, 405, 429, 500):
                with self.subTest(path=path, status=status):
                    response = HttpResponse(status=status)
                    response["Cache-Control"] = "public, max-age=300"
                    middleware = AuthFormCacheMiddleware(lambda request: response)
                    result = middleware(RequestFactory().get(path))
                    self.assertEqual(result["Cache-Control"], "private, no-store")
                    self.assertEqual(result["Expires"], "0")

    def test_public_response_keeps_its_cache_policy(self):
        response = HttpResponse()
        response["Cache-Control"] = "public, max-age=300"
        result = AuthFormCacheMiddleware(lambda request: response)(
            RequestFactory().get("/api/v1/catalog/")
        )
        self.assertEqual(result["Cache-Control"], "public, max-age=300")


@override_settings(AUTH_FORM_RATE_LIMITS={"login": (1, 60), "register": (1, 60)})
class AuthCacheViewTests(TestCase):
    def setUp(self):
        cache.clear()

    def assert_private(self, response, status):
        self.assertEqual(response.status_code, status)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["Pragma"], "no-cache")
        self.assertEqual(response["Expires"], "0")

    def test_forms_validation_method_errors_and_csrf_rejections(self):
        for path in ("/login/", "/register/"):
            with self.subTest(path=path):
                self.assert_private(self.client.get(path), 200)
                self.assert_private(self.client.post(path, {}), 200)
                self.assert_private(self.client.put(path), 405)
                self.assert_private(Client(enforce_csrf_checks=True).post(path, {}), 403)

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_https_redirects_are_private(self):
        for path in ("/login/", "/register/"):
            self.assert_private(self.client.get(path), 301)

    def test_upstream_errors_and_rate_limits(self):
        for path, function in (("/login/", "sign_in"), ("/register/", "sign_up")):
            with self.subTest(path=path), patch(
                f"polskiflow.auth_views.{function}", side_effect=SupabaseAuthError("Ошибка входа")
            ):
                payload = {"email": "learner@example.com", "password": "StrongPassword2026!"}
                self.assert_private(self.client.post(path, payload), 200)
                self.assert_private(self.client.post(path, payload), 429)

    @patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("user-123", "learner@example.com"))
    def test_authenticated_redirects_are_private(self, _auth):
        self.client.cookies[ACCESS_COOKIE] = "access"
        for path in ("/login/", "/register/"):
            self.assert_private(self.client.get(path), 302)
