import io
import json
import os
from email.message import Message
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError
from urllib.request import HTTPSHandler, Request, build_opener
from urllib.response import addinfourl

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from polskiflow.domain.synthetic_smoke import _RejectRedirects, SmokeFailure, run_synthetic_smoke


def _response(payload, *, cache="public, max-age=0", request_id="request-1"):
    response = MagicMock()
    response.__enter__.return_value = response
    response.status = 200
    response.headers = {"Cache-Control": cache, "X-Request-ID": request_id}
    response.read.return_value = json.dumps(payload).encode()
    return response


class SyntheticSmokeTests(SimpleTestCase):
    def test_redirects_never_make_a_second_request_with_credentials(self):
        class RedirectServer(HTTPSHandler):
            def __init__(self, code, destination):
                super().__init__()
                self.code = code
                self.destination = destination
                self.requests = []

            def https_open(self, request):
                self.requests.append(request)
                headers = Message()
                headers["Location"] = self.destination
                response = addinfourl(io.BytesIO(b""), headers, request.full_url, self.code)
                response.msg = "Redirect"
                return response

        for code in (301, 302, 303, 307, 308):
            for destination in ("https://other.example/", "https://learn.example/login/"):
                with self.subTest(code=code, destination=destination):
                    server = RedirectServer(code, destination)
                    opener = build_opener(server, _RejectRedirects())
                    request = Request("https://learn.example/api/v1/me/bootstrap/",
                                      headers={"Authorization": "Bearer private-token"})
                    with self.assertRaises(HTTPError) as raised:
                        opener.open(request)
                    self.assertEqual(raised.exception.code, code)
                    self.assertEqual(len(server.requests), 1)

    @patch("polskiflow.domain.synthetic_smoke.urlopen")
    def test_redirect_failure_does_not_print_sensitive_location(self, urlopen):
        urlopen.side_effect = HTTPError("https://example.com/?token=private-token", 302,
                                       "secret redirect", {}, None)
        with self.assertRaisesMessage(SmokeFailure, "health: HTTP 302"):
            run_synthetic_smoke("https://example.com", include_private=False)

    @patch("polskiflow.domain.synthetic_smoke.urlopen")
    def test_read_only_public_and_private_path_passes_without_exposing_token(self, urlopen):
        urlopen.side_effect = [
            _response({"status": "ok"}),
            _response({"status": "ready"}),
            _response({"paths": {"/api/v1/me/bootstrap/": {}}}),
            _response({"data": {"courses": []}}),
            _response({"meta": {"contract": "learner-bootstrap"}, "data": {}}, cache="private, no-store"),
            _response({"meta": {"contract": "learner-data-export"}, "data": {}}, cache="private, no-store"),
        ]

        results = run_synthetic_smoke("https://learn.example/", "secret-token")

        self.assertEqual([result.name for result in results], ["health", "ready", "openapi", "catalog", "bootstrap", "export"])
        for index, call in enumerate(urlopen.call_args_list):
            request = call.args[0]
            self.assertEqual(request.get_method(), "GET")
            if index < 4:
                self.assertNotIn("Authorization", request.headers)
            else:
                self.assertEqual(request.headers["Authorization"], "Bearer secret-token")

    def test_rejects_unsafe_origin_and_invalid_token(self):
        for base_url in ("http://example.com", "https://user:pass@example.com", "https://example.com/app/", "https://example.com/?x=1"):
            with self.subTest(base_url=base_url), self.assertRaises(SmokeFailure):
                run_synthetic_smoke(base_url, "token")
        with self.assertRaises(SmokeFailure):
            run_synthetic_smoke("https://example.com", "token with whitespace")
        with self.assertRaises(SmokeFailure):
            run_synthetic_smoke("https://example.com", "token", timeout=0)

    @patch("polskiflow.domain.synthetic_smoke.urlopen")
    def test_rejects_private_response_without_no_store(self, urlopen):
        urlopen.side_effect = [
            _response({"status": "ok"}), _response({"status": "ready"}),
            _response({"paths": {"/api/v1/me/bootstrap/": {}}}),
            _response({"data": {"courses": []}}),
            _response({"meta": {"contract": "learner-bootstrap"}, "data": {}}),
        ]
        with self.assertRaisesRegex(SmokeFailure, "private cache boundary"):
            run_synthetic_smoke("https://example.com", "token")

    @patch("polskiflow.learning.management.commands.production_smoke.run_synthetic_smoke", return_value=())
    def test_command_reads_token_only_from_environment(self, run):
        output = io.StringIO()
        with patch.dict(os.environ, {"CUSTOM_SMOKE_TOKEN": "token-value"}):
            call_command("production_smoke", "https://example.com", token_env="CUSTOM_SMOKE_TOKEN", stdout=output)
        run.assert_called_once_with(
            "https://example.com", "token-value", timeout=10, include_private=True
        )
        self.assertNotIn("token-value", output.getvalue())

    def test_command_requires_configured_token(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(CommandError):
            call_command("production_smoke", "https://example.com")

    @patch("polskiflow.domain.synthetic_smoke.urlopen")
    def test_public_only_checks_need_no_token(self, urlopen):
        urlopen.side_effect = [
            _response({"status": "ok"}),
            _response({"status": "ready"}),
            _response({"paths": {"/api/v1/me/bootstrap/": {}}}),
            _response({"data": {"courses": []}}),
        ]
        results = run_synthetic_smoke("https://example.com", include_private=False)
        self.assertEqual(
            [result.name for result in results],
            ["health", "ready", "openapi", "catalog"],
        )
        self.assertTrue(all("Authorization" not in call.args[0].headers for call in urlopen.call_args_list))

    @patch("polskiflow.learning.management.commands.production_smoke.run_synthetic_smoke", return_value=())
    def test_command_public_only_does_not_read_token(self, run):
        output = io.StringIO()
        with patch.dict(os.environ, {"POLSKIFLOW_SMOKE_ACCESS_TOKEN": "must-not-be-used"}):
            call_command("production_smoke", "https://example.com", public_only=True, stdout=output)
        run.assert_called_once_with(
            "https://example.com", "", timeout=10, include_private=False
        )
