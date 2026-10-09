import io
import json
from unittest.mock import patch
from urllib.error import URLError

from django.test import SimpleTestCase, override_settings

from polskiflow.auth import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    SupabaseAuthError,
    SupabaseSession,
    SupabaseUser,
    authenticate_access_token,
    delete_account,
    request_password_reset,
    resend_signup_confirmation,
    sign_in,
    sign_up,
    update_password,
)


class _Response(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


@override_settings(
    SUPABASE_URL="https://project.supabase.co",
    SUPABASE_ANON_KEY="public-anon-key",
    SUPABASE_AUTH_TIMEOUT=2,
    SUPABASE_AUTH_NETWORK_ATTEMPTS=3,
    SUPABASE_AUTH_RETRY_BACKOFF=0.01,
)
class SupabaseAuthTests(SimpleTestCase):
    @patch("polskiflow.auth.urlopen")
    def test_account_deletion_uses_user_jwt_and_password_only(self, urlopen):
        urlopen.return_value = _Response(b'{"deleted_user_id":"user-123"}')
        delete_account("user-access", "user-123", "CurrentPassword2026")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertTrue(request.full_url.endswith("/functions/v1/delete-account"))
        self.assertEqual(request.get_header("Apikey"), "public-anon-key")
        self.assertEqual(request.get_header("Authorization"), "Bearer user-access")
        self.assertEqual(json.loads(request.data), {"password": "CurrentPassword2026"})

    @patch("polskiflow.auth.urlopen")
    def test_account_deletion_rejects_mismatched_worker_result(self, urlopen):
        urlopen.return_value = _Response(b'{"deleted_user_id":"another-user"}')
        with self.assertRaises(SupabaseAuthError):
            delete_account("user-access", "user-123", "CurrentPassword2026")

    @patch("polskiflow.auth.urlopen")
    def test_password_recovery_uses_allowed_redirect(self, urlopen):
        urlopen.return_value = _Response(b"{}")

        request_password_reset(
            "learner@example.com", "https://polish.example/reset-password/"
        )

        request = urlopen.call_args.args[0]
        self.assertIn("/auth/v1/recover?redirect_to=https://polish.example/reset-password/", request.full_url)
        self.assertEqual(json.loads(request.data), {"email": "learner@example.com"})

    @patch("polskiflow.auth.urlopen")
    def test_signup_confirmation_resend_does_not_create_user(self, urlopen):
        urlopen.return_value = _Response(b"{}")

        resend_signup_confirmation("learner@example.com", "https://polish.example/login/")

        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/auth/v1/resend"))
        self.assertEqual(json.loads(request.data)["type"], "signup")
        self.assertEqual(json.loads(request.data)["options"]["email_redirect_to"], "https://polish.example/login/")

    @patch("polskiflow.auth.urlopen")
    def test_recovery_token_updates_password_with_put(self, urlopen):
        urlopen.return_value = _Response(b"{}")

        update_password("recovery-access", "Bezpieczne2026")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.method, "PUT")
        self.assertTrue(request.full_url.endswith("/auth/v1/user"))
        self.assertEqual(request.get_header("Authorization"), "Bearer recovery-access")
        self.assertEqual(json.loads(request.data), {"password": "Bezpieczne2026"})

    @patch("polskiflow.auth.urlopen")
    def test_authenticated_password_change_sends_current_password(self, urlopen):
        urlopen.return_value = _Response(b"{}")

        update_password("access", "NewPassword2026", current_password="OldPassword2026")

        request = urlopen.call_args.args[0]
        self.assertEqual(request.method, "PUT")
        self.assertEqual(json.loads(request.data), {
            "password": "NewPassword2026",
            "current_password": "OldPassword2026",
        })

    @patch("polskiflow.auth.urlopen")
    def test_valid_token_populates_current_user(self, urlopen):
        urlopen.return_value = _Response(
            json.dumps({"id": "user-123", "email": "learner@example.com"}).encode()
        )

        response = self.client.get(
            "/api/auth/me/", headers={"Authorization": "Bearer access-token"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "user-123")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer access-token")
        self.assertEqual(request.get_header("Apikey"), "public-anon-key")
        self.assertIn("context", urlopen.call_args.kwargs)

    def test_missing_token_is_rejected(self):
        response = self.client.get("/api/auth/me/")
        self.assertEqual(response.status_code, 401)

    @override_settings(SUPABASE_URL="", SUPABASE_ANON_KEY="")
    def test_authentication_is_disabled_without_configuration(self):
        self.assertIsNone(authenticate_access_token("token"))

    @patch("polskiflow.auth.authenticate_access_token")
    def test_middleware_exposes_verified_user(self, authenticate):
        authenticate.return_value = SupabaseUser("user-456", None)
        response = self.client.get(
            "/api/auth/me/", headers={"Authorization": "Bearer token"}
        )
        self.assertEqual(response.json(), {"id": "user-456", "email": None})

    @patch("polskiflow.auth.urlopen")
    def test_password_sign_in_returns_session(self, urlopen):
        urlopen.return_value = _Response(
            json.dumps(
                {
                    "access_token": "access",
                    "refresh_token": "refresh",
                    "expires_in": 3600,
                    "user": {"id": "user-123", "email": "learner@example.com"},
                }
            ).encode()
        )

        session = sign_in("learner@example.com", "password")

        self.assertEqual(session.access_token, "access")
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/auth/v1/token?grant_type=password"))
        self.assertEqual(json.loads(request.data), {
            "email": "learner@example.com",
            "password": "password",
        })
        self.assertIn("context", urlopen.call_args.kwargs)

    @patch("polskiflow.auth.urlopen")
    def test_signup_sets_safe_welcome_redirect(self, urlopen):
        urlopen.return_value = _Response(b'{}')
        self.assertIsNone(
            sign_up(
                "learner@example.com",
                "Bezpieczne2026",
                email_redirect_to="https://polish.example/login/?next=%2Fwelcome%2F",
            )
        )
        payload = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(
            payload["options"]["email_redirect_to"],
            "https://polish.example/login/?next=%2Fwelcome%2F",
        )

    @patch("polskiflow.auth.time.sleep")
    @patch("polskiflow.auth.urlopen")
    def test_password_sign_in_retries_one_network_failure(self, urlopen, sleep):
        urlopen.side_effect = [
            URLError("temporary failure"),
            _Response(
                json.dumps(
                    {
                        "access_token": "access",
                        "refresh_token": "refresh",
                        "expires_in": 3600,
                        "user": {"id": "user-123", "email": "learner@example.com"},
                    }
                ).encode()
            ),
        ]

        session = sign_in("learner@example.com", "password")

        self.assertEqual(session.user.id, "user-123")
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(0.01)
        self.assertIsNot(urlopen.call_args_list[0].args[0], urlopen.call_args_list[1].args[0])

    @patch("polskiflow.auth.time.sleep")
    @patch("polskiflow.auth.urlopen", side_effect=URLError("service unavailable"))
    def test_password_sign_in_reports_network_failure_after_retry(self, urlopen, sleep):
        with self.assertRaisesMessage(
            SupabaseAuthError, "Сервис авторизации временно недоступен"
        ):
            sign_in("learner@example.com", "password")

        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.01, 0.02])

    @patch("polskiflow.auth.refresh_session")
    @patch("polskiflow.auth.authenticate_access_token")
    def test_expired_cookie_session_is_refreshed(self, authenticate, refresh):
        authenticate.return_value = None
        refresh.return_value = SupabaseSession(
            "new-access",
            "new-refresh",
            3600,
            SupabaseUser("user-789", "renewed@example.com"),
        )
        self.client.cookies[ACCESS_COOKIE] = "expired-access"
        self.client.cookies[REFRESH_COOKIE] = "refresh"

        response = self.client.get("/api/auth/me/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "user-789")
        self.assertEqual(response.cookies[ACCESS_COOKIE].value, "new-access")
        self.assertTrue(response.cookies[ACCESS_COOKIE]["httponly"])


@override_settings(AUTH_COOKIE_SECURE=False)
class BrowserAuthTests(SimpleTestCase):
    def test_login_uses_product_shell(self):
        response = self.client.get("/login/")

        self.assertContains(response, "Рады видеть!")
        self.assertContains(response, "Польский становится привычкой.")
        self.assertContains(response, "/static/polskiflow/app.css")
        self.assertContains(response, 'href="/forgot-password/"')

    @patch("polskiflow.auth_views.request_password_reset")
    def test_password_recovery_request_is_generic_and_not_cached(self, recover):
        response = self.client.post(
            "/forgot-password/", {"email": "learner@example.com"}
        )

        self.assertContains(response, "Если аккаунт существует")
        self.assertEqual(response["Cache-Control"], "private, no-store")
        recover.assert_called_once_with(
            "learner@example.com", "http://testserver/reset-password/"
        )

    @patch("polskiflow.auth_views.request_password_reset", side_effect=SupabaseAuthError("User not found"))
    def test_password_recovery_does_not_reveal_account_existence(self, _recover):
        response = self.client.post(
            "/forgot-password/", {"email": "unknown@example.com"}
        )
        self.assertContains(response, "Если аккаунт существует")
        self.assertNotContains(response, "User not found")

    def test_reset_page_extracts_fragment_token_in_browser(self):
        response = self.client.get("/reset-password/")

        self.assertContains(response, 'data-recovery-token')
        self.assertContains(response, 'params.get("type") === "recovery"')
        self.assertContains(response, "history.replaceState")
        self.assertContains(response, 'disabled data-recovery-submit')
        self.assertEqual(response["Cache-Control"], "private, no-store")

    @patch("polskiflow.auth_views.update_password")
    def test_password_reset_validates_and_updates_with_recovery_token(self, update):
        response = self.client.post(
            "/reset-password/",
            {
                "recovery_token": "one-time-token",
                "password": "NoweBezpieczne2026",
                "password_confirmation": "NoweBezpieczne2026",
            },
        )

        update.assert_called_once_with("one-time-token", "NoweBezpieczne2026")
        self.assertRedirects(response, "/login/?password_reset=1", fetch_redirect_response=False)
        self.assertEqual(response["Cache-Control"], "private, no-store")

    @patch("polskiflow.auth_views.update_password")
    def test_password_reset_rejects_missing_token_and_mismatch(self, update):
        missing = self.client.post(
            "/reset-password/",
            {"password": "NoweBezpieczne2026", "password_confirmation": "NoweBezpieczne2026"},
        )
        mismatch = self.client.post(
            "/reset-password/",
            {"recovery_token": "token", "password": "NoweBezpieczne2026", "password_confirmation": "InneBezpieczne2026"},
        )

        self.assertContains(missing, "недействительна или устарела")
        self.assertContains(mismatch, "Пароли не совпадают")
        self.assertContains(mismatch, 'value="token"')
        update.assert_not_called()

    @patch("polskiflow.auth_views.resend_signup_confirmation")
    def test_confirmation_resend_uses_generic_response(self, resend):
        response = self.client.post(
            "/resend-confirmation/", {"email": "learner@example.com"}
        )

        self.assertContains(response, "Если подтверждение ожидается")
        resend.assert_called_once_with(
            "learner@example.com",
            "http://testserver/login/?next=%2Fwelcome%2F",
        )

    @patch("polskiflow.auth_views.sign_in")
    def test_login_sets_http_only_cookies_and_redirects(self, login):
        login.return_value = SupabaseSession(
            "access",
            "refresh",
            3600,
            SupabaseUser("user-123", "learner@example.com"),
        )

        response = self.client.post(
            "/login/?next=/lesson/words",
            {"email": "learner@example.com", "password": "password", "next": "/lesson/words"},
        )

        self.assertRedirects(response, "/lesson/words", fetch_redirect_response=False)
        self.assertTrue(response.cookies[ACCESS_COOKIE]["httponly"])
        self.assertEqual(response.cookies[REFRESH_COOKIE]["samesite"], "Lax")

    @patch("polskiflow.auth_views.sign_in")
    def test_login_rejects_external_next_url(self, login):
        login.return_value = SupabaseSession(
            "access", "refresh", 3600, SupabaseUser("user-123", None)
        )

        response = self.client.post(
            "/login/",
            {"email": "a@example.com", "password": "password", "next": "https://evil.example"},
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)

    @patch("polskiflow.auth_views.sign_in")
    def test_login_displays_safe_auth_error(self, login):
        login.side_effect = SupabaseAuthError("Invalid login credentials")
        response = self.client.post(
            "/login/", {"email": "a@example.com", "password": "wrong-password"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid login credentials")

    def test_protected_page_redirects_guest_to_login(self):
        response = self.client.get("/course/")
        self.assertRedirects(response, "/login/?next=%2Fcourse%2F", fetch_redirect_response=False)

    @patch("polskiflow.auth_views.sign_up")
    def test_registration_waits_for_email_confirmation(self, signup):
        signup.return_value = None
        response = self.client.post(
            "/register/", {"email": "new@example.com", "password": "Bezpieczne2026"}
        )
        self.assertContains(response, "Подтвердите email")
        signup.assert_called_once_with(
            "new@example.com",
            "Bezpieczne2026",
            email_redirect_to="http://testserver/login/?next=%2Fwelcome%2F",
        )

    @patch("polskiflow.auth_views.sign_up")
    def test_registration_with_session_opens_onboarding(self, signup):
        signup.return_value = SupabaseSession(
            "access", "refresh", 3600, SupabaseUser("user-123", "new@example.com")
        )
        response = self.client.post(
            "/register/", {"email": "new@example.com", "password": "Bezpieczne2026"}
        )
        self.assertRedirects(response, "/welcome/", fetch_redirect_response=False)
        self.assertTrue(response.cookies[ACCESS_COOKIE]["httponly"])

    @patch("polskiflow.auth_views.sign_up")
    def test_registration_rejects_weak_password_before_supabase(self, signup):
        response = self.client.post(
            "/register/", {"email": "new@example.com", "password": "Password123"}
        )

        self.assertContains(response, "пароль слишком распространён")
        self.assertContains(response, 'value="new@example.com"')
        signup.assert_not_called()

    def test_registration_explains_free_plan_password_policy(self):
        response = self.client.get("/register/")

        self.assertContains(response, 'minlength="10"')
        self.assertContains(response, 'aria-describedby="password-hint"')
        self.assertContains(response, "строчные и заглавные буквы")

    @patch("polskiflow.auth_views.sign_out")
    @patch("polskiflow.auth.authenticate_access_token")
    def test_logout_clears_auth_cookies(self, authenticate, logout):
        authenticate.return_value = SupabaseUser("user-123", "learner@example.com")
        self.client.cookies[ACCESS_COOKIE] = "access"
        self.client.cookies[REFRESH_COOKIE] = "refresh"

        response = self.client.post("/logout/")

        logout.assert_called_once_with("access")
        self.assertRedirects(response, "/login/", fetch_redirect_response=False)
        self.assertEqual(response.cookies[ACCESS_COOKIE]["max-age"], 0)
