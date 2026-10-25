import json
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from uuid import uuid4

from django.core import signing
from django.http import HttpResponse
from django.test import SimpleTestCase, RequestFactory, override_settings

from polskiflow.beta_metrics import BetaMetricsMiddleware, reserve_attempt, rpc
from polskiflow.domain.lesson_state import SALT, InvalidLessonState, sign_lesson_state, load_lesson_state
from polskiflow.beta_metrics_report import summarize


@override_settings(BETA_METRICS_ENABLED=True, BETA_METRICS_SERVICE_KEY='server-only',
                   BETA_METRICS_RELEASE='a' * 40, SUPABASE_URL='https://project.test')
class BetaMetricsTests(SimpleTestCase):
    def request(self, route='lesson-step', method='POST'):
        request = getattr(RequestFactory(), method.lower())('/private?secret=never-export')
        request.resolver_match = SimpleNamespace(url_name=route)
        request.supabase_user = SimpleNamespace(id=str(uuid4()), email='never-export@example.test')
        return request

    @override_settings(BETA_METRICS_ENABLED=False)
    @patch('polskiflow.beta_metrics.urlopen')
    def test_disabled_has_no_collection_or_reservation(self, opened):
        request = self.request()
        self.assertIsNone(reserve_attempt(request, 'quiz'))
        self.assertIsNone(rpc('beta_observe_request', {}))
        self.assertEqual(BetaMetricsMiddleware(lambda r: HttpResponse('ok'))(request).status_code, 200)
        opened.assert_not_called()

    @override_settings(BETA_METRICS_RELEASE='unknown')
    @patch('polskiflow.beta_metrics.urlopen')
    def test_missing_release_does_not_create_mixed_unknown_version(self, opened):
        self.assertIsNone(rpc('beta_observe_request', {}))
        opened.assert_not_called()

    @patch('polskiflow.beta_metrics.rpc')
    def test_only_allowlisted_routes_and_authenticated_nonstreaming_requests(self, call):
        middleware = BetaMetricsMiddleware(lambda r: HttpResponse('ok'))
        middleware(self.request('login'))
        request = self.request()
        request.supabase_user = None
        middleware(request)
        call.assert_not_called()

    @patch('polskiflow.beta_metrics.rpc')
    def test_get_and_rejected_actions_never_start_attempts(self, call):
        for method, status in [('GET',200), ('POST',400), ('POST',500)]:
            request = self.request(method=method)
            request.beta_attempt_id = str(uuid4())
            BetaMetricsMiddleware(lambda r: HttpResponse(status=status))(request)
            payload = call.call_args.args[1]
            self.assertIsNone(payload['p_attempt'])
            self.assertFalse(payload['p_finished'])
            self.assertEqual(payload['p_status'], status)

    @patch('polskiflow.beta_metrics.rpc')
    def test_accepted_final_action_has_stable_owner_bound_identity_not_content(self, call):
        request = self.request()
        request.beta_attempt_id = str(uuid4())
        request.beta_finished = True
        request.beta_saved = False
        request.beta_total, request.beta_known = 7, 5
        middleware = BetaMetricsMiddleware(lambda r: HttpResponse('private answers'))
        middleware(request)
        first = call.call_args.args[1]
        middleware(request)
        second = call.call_args.args[1]
        self.assertEqual(first['p_attempt'], second['p_attempt'])
        self.assertNotEqual(first['p_request'], second['p_request'])
        self.assertTrue(first['p_finished'])
        self.assertFalse(first['p_saved'])
        self.assertEqual(first['p_total'], 7)
        serialized = json.dumps(first)
        for private in ['secret', 'never-export', 'private answers', 'server-only']:
            self.assertNotIn(private, serialized)

    @patch('polskiflow.beta_metrics.urlopen', side_effect=TimeoutError)
    def test_store_failure_does_not_break_response(self, opened):
        request = self.request()
        response = BetaMetricsMiddleware(lambda r: HttpResponse('lesson still works'))(request)
        self.assertEqual(response.content, b'lesson still works')
        self.assertEqual(opened.call_args.kwargs['timeout'], 1)

    @patch('polskiflow.beta_metrics.rpc')
    def test_reservation_is_deferred_without_an_early_rpc(self, call):
        request = self.request()
        self.assertIsNone(reserve_attempt(request, 'quiz'))
        self.assertEqual(request.beta_reserve_lesson,'quiz')
        call.assert_not_called()

    def test_signed_identity_survives_steps_and_old_tokens_remain_valid(self):
        attempt = str(uuid4())
        token = sign_lesson_state('owner', 'quiz', 'quiz', 0, 0, attempt_id=attempt)
        state = load_lesson_state(token, 'owner', 'quiz', 'quiz')
        self.assertEqual(state.attempt_id, attempt)
        next_token = sign_lesson_state('owner', 'quiz', 'quiz', 1, 1, attempt_id=state.attempt_id)
        self.assertEqual(load_lesson_state(next_token, 'owner', 'quiz', 'quiz').attempt_id, attempt)
        with self.assertRaises(InvalidLessonState):
            load_lesson_state(token, 'another-owner', 'quiz', 'quiz')
        old = sign_lesson_state('owner', 'quiz', 'quiz', 0, 0)
        self.assertIsNone(load_lesson_state(old, 'owner', 'quiz', 'quiz').attempt_id)
        payload = signing.loads(token, salt=SALT)
        payload['attempt_id'] = []
        with self.assertRaises(InvalidLessonState):
            load_lesson_state(signing.dumps(payload, salt=SALT), 'owner', 'quiz', 'quiz')


class BetaMetricsReportTests(SimpleTestCase):
    def snapshot(self, rows):
        return {'schema_version':1,'coverage':'best_effort_received_only','requests':rows,'attempts':[],
                'latency_scope':'django_app_before_collector','since':'2026-10-25T00:00:00Z','until':'2026-10-26T00:00:00Z'}

    def row(self, ms, count, **kwargs):
        return dict(cohort='fixture',release_sha='a'*40,route_group='lesson',method='POST',status=200,app_ms=ms,count=count,**kwargs)

    def test_merges_frequencies_not_percentiles_and_separates_errors_and_versions(self):
        error = self.row(9000,1)
        error['status'] = 503
        other = self.row(500,1)
        other['release_sha'] = 'b'*40
        result = summarize(self.snapshot([self.row(10,94), self.row(20,1),self.row(100,5),error,other]))
        self.assertEqual(result['requests'][0]['app_p95_ms'],20)
        self.assertEqual(result['requests'][0]['count'],100)
        self.assertEqual(len(result['requests']),3)
        self.assertIsNone(result['lost_results'])
        self.assertFalse(result['beta_readiness_evidence'])

    def test_empty_unknown_and_private_extra_fields(self):
        self.assertEqual(summarize(self.snapshot([]))['requests'],[])
        with self.assertRaises(ValueError):
            summarize(self.snapshot([self.row(10,True)]))
        with self.assertRaises(ValueError):
            summarize(self.snapshot([self.row(10,1,email='private@example.test')]))
        with self.assertRaises(ValueError):
            summarize({'schema_version':1})
