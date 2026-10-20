import uuid
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from polskiflow.request_id import RequestIdMiddleware


class RequestIdMiddlewareTests(SimpleTestCase):
    def test_server_timing_preserves_existing_metrics_without_identifiers(self):
        request = RequestFactory().get('/health/')
        response = RequestIdMiddleware(lambda _: HttpResponse(headers={'Server-Timing': 'db;dur=2'}))(request)
        self.assertRegex(response['Server-Timing'], r'^db;dur=2, app;dur=\d+$')
        self.assertNotIn(response['X-Request-ID'], response['Server-Timing'])

    def test_response_gets_generated_uuid_request_id(self):
        response = self.client.get("/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(uuid.UUID(response["X-Request-ID"])), response["X-Request-ID"])

    def test_valid_client_request_id_is_preserved(self):
        request_id = "cf4fc5e8-6f30-4a96-b89c-779fca0456b3"
        response = self.client.get("/health/", headers={"X-Request-ID": request_id})
        self.assertEqual(response["X-Request-ID"], request_id)

    def test_invalid_or_oversized_value_is_replaced(self):
        for value in ("not-a-uuid", "x" * 10_000):
            with self.subTest(value=value[:20]):
                response = self.client.get("/health/", headers={"X-Request-ID": value})
                self.assertNotEqual(response["X-Request-ID"], value)
                uuid.UUID(response["X-Request-ID"])

    def test_not_found_response_also_has_request_id(self):
        response = self.client.get("/missing-page/")
        self.assertEqual(response.status_code, 404)
        uuid.UUID(response["X-Request-ID"])

    def test_server_error_is_logged_with_request_id(self):
        middleware = RequestIdMiddleware(lambda _request: HttpResponse(status=503))
        request = RequestFactory().get("/health/")
        with self.assertLogs("polskiflow.request", level="WARNING") as captured:
            response = middleware(request)
        self.assertIn(f"request_id={response['X-Request-ID']}", captured.output[0])
        self.assertIn("path=/health/", captured.output[0])
        self.assertIn("duration_ms=", captured.output[0])

    @patch("polskiflow.request_id.time.monotonic", side_effect=(10, 12))
    def test_slow_request_is_logged_without_query_string(self, _monotonic):
        middleware = RequestIdMiddleware(lambda _request: HttpResponse(status=200))
        request = RequestFactory().get("/reading/?token=secret")
        with self.assertLogs("polskiflow.request", level="WARNING") as captured:
            middleware(request)

        self.assertIn("request_slow", captured.output[0])
        self.assertIn("path=/reading/", captured.output[0])
        self.assertNotIn("token", captured.output[0])

    def test_uncaught_exception_is_logged_and_reraised(self):
        def fail(_request):
            raise RuntimeError("boom")

        middleware = RequestIdMiddleware(fail)
        request = RequestFactory().get("/health/")
        with self.assertLogs("polskiflow.request", level="ERROR") as captured:
            with self.assertRaises(RuntimeError):
                middleware(request)

        self.assertIn("request_exception", captured.output[0])
        self.assertIn("request_id=", captured.output[0])
        self.assertIn("exception_type=RuntimeError", captured.output[0])
        self.assertNotIn("boom", captured.output[0])
