import io
import json
import os
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from polskiflow.domain.smoke_session import PRODUCTION_ORIGIN, fresh_smoke_session
from polskiflow.domain.synthetic_smoke import SmokeFailure

ENV = {
    "LINGOFLOW_SMOKE_AUTH_URL": "https://abcdefghijklmnopqrst.supabase.co",
    "LINGOFLOW_SMOKE_PUBLISHABLE_KEY": "sb_publishable_test",
    "LINGOFLOW_SMOKE_EMAIL": "smoke@example.test",
    "LINGOFLOW_SMOKE_PASSWORD": "private-password",
    "LINGOFLOW_SMOKE_USER_ID": "11111111-1111-4111-8111-111111111111",
}
PAYLOAD = {
    "access_token": "private-token", "refresh_token": "private-refresh",
    "token_type": "bearer", "expires_in": 3600,
    "user": {"id": ENV["LINGOFLOW_SMOKE_USER_ID"], "is_anonymous": False},
}


def response(body, status=200):
    result = MagicMock()
    result.__enter__.return_value = result
    result.status = status
    result.read.return_value = json.dumps(body).encode()
    return result


@patch.dict(os.environ, ENV, clear=True)
class SmokeSessionTests(SimpleTestCase):
    @patch("polskiflow.domain.smoke_session.urlopen")
    def test_login_local_logout_and_no_refresh_token_use(self, request):
        request.side_effect = [response(PAYLOAD), response(None, 204)]
        with fresh_smoke_session(PRODUCTION_ORIGIN) as token:
            self.assertEqual(token, "private-token")
        login, logout = [call.args[0] for call in request.call_args_list]
        self.assertTrue(login.full_url.endswith("/token?grant_type=password"))
        self.assertEqual(json.loads(login.data), {"email": ENV["LINGOFLOW_SMOKE_EMAIL"], "password": "private-password"})
        self.assertNotIn("Authorization", login.headers)
        self.assertTrue(logout.full_url.endswith("/logout?scope=local"))
        self.assertEqual(logout.headers["Authorization"], "Bearer private-token")
        self.assertNotIn(b"private-refresh", logout.data)

    @patch("polskiflow.domain.smoke_session.urlopen")
    def test_cleanup_after_probe_failure_or_invalid_identity_and_lifetime(self, request):
        for payload in (PAYLOAD, {**PAYLOAD, "expires_in": True}, {**PAYLOAD, "expires_in": 3601},
                        {**PAYLOAD, "user": {"id": "other"}}):
            request.reset_mock()
            request.side_effect = [response(payload), response(None, 204)]
            with self.assertRaises(SmokeFailure):
                with fresh_smoke_session(PRODUCTION_ORIGIN):
                    raise SmokeFailure("probe failed")
            self.assertEqual(request.call_count, 2)

    @patch("polskiflow.domain.smoke_session.urlopen")
    def test_invalid_configuration_never_sends_credentials(self, request):
        for url in ("https://other.example", PRODUCTION_ORIGIN + "/path"):
            with self.assertRaises(SmokeFailure), fresh_smoke_session(url):
                pass
        for name, value in (("LINGOFLOW_SMOKE_AUTH_URL", "https://attacker.example"),
                            ("LINGOFLOW_SMOKE_PUBLISHABLE_KEY", "sb_secret_private"),
                            ("LINGOFLOW_SMOKE_USER_ID", "invalid"), ("LINGOFLOW_SMOKE_PASSWORD", "")):
            with patch.dict(os.environ, {name: value}), self.assertRaises(SmokeFailure), fresh_smoke_session(PRODUCTION_ORIGIN):
                pass
        request.assert_not_called()

    @patch("polskiflow.domain.smoke_session.urlopen")
    def test_auth_errors_sanitized_not_retried(self, request):
        for result in (HTTPError("https://secret.example", 401, "private-password", {}, None),
                       response(["private-password"]), response({"access_token": "bad token"})):
            request.reset_mock()
            request.side_effect = result if isinstance(result, Exception) else [result]
            with self.assertRaises(SmokeFailure) as raised, fresh_smoke_session(PRODUCTION_ORIGIN):
                pass
            self.assertNotIn("private-password", str(raised.exception))
            self.assertEqual(request.call_count, 1)

    @patch("polskiflow.domain.smoke_session.urlopen")
    @patch("polskiflow.learning.management.commands.production_smoke.run_synthetic_smoke", return_value=())
    def test_command_requires_successful_logout_and_incompatible_flags_fail(self, smoke, request):
        request.side_effect = [response(PAYLOAD), response(None, 204)]
        output = io.StringIO()
        call_command("production_smoke", PRODUCTION_ORIGIN, fresh_session=True, stdout=output)
        smoke.assert_called_once_with(PRODUCTION_ORIGIN, "private-token", timeout=10, include_private=True)
        self.assertNotIn("private-token", output.getvalue())
        request.side_effect = [response(PAYLOAD), response(None, 500)]
        output = io.StringIO()
        with self.assertRaises(CommandError):
            call_command("production_smoke", PRODUCTION_ORIGIN, fresh_session=True, stdout=output)
        self.assertNotIn("passed", output.getvalue())
        request.reset_mock()
        with self.assertRaises(CommandError):
            call_command("production_smoke", PRODUCTION_ORIGIN, fresh_session=True, public_only=True)
        request.assert_not_called()
