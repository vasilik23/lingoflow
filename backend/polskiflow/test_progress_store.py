import json
from datetime import date
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.test import SimpleTestCase, override_settings

from polskiflow.progress_store import (
    CompletionSaveResult,
    load_dashboard_progress,
    record_lesson_result_event,
    save_lesson_completion,
    save_lesson_completion_result,
    save_profile_settings,
)
from polskiflow.domain.lesson_results import validate_lesson_result


class ProgressStoreTests(SimpleTestCase):
    @override_settings(SUPABASE_URL="https://project.supabase.co", SUPABASE_ANON_KEY="public-key")
    @patch("polskiflow.progress_store.urlopen")
    def test_minute_goal_is_saved_with_derived_legacy_count(self, urlopen):
        response = MagicMock()
        response.status = 204
        urlopen.return_value.__enter__.return_value = response
        self.assertTrue(save_profile_settings("access", "owner", "Ada", "B1", 4, daily_goal_minutes=30))
        request = urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data), {"display_name": "Ada", "level": "B1", "daily_goal_lessons": 6, "daily_goal_minutes": 30})
        self.assertIn("id=eq.owner", request.full_url)
        self.assertEqual(request.headers["Authorization"], "Bearer access")

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
        SUPABASE_AUTH_TIMEOUT=2,
    )
    @patch("polskiflow.progress_store.urlopen")
    def test_result_event_rpc_uses_user_token_without_user_id_payload(self, mocked_urlopen):
        response = MagicMock()
        response.read.return_value = b'{"status":"created"}'
        mocked_urlopen.return_value.__enter__.return_value = response
        result = validate_lesson_result(
            {
                "event_id": "d576c21f-69d1-4dd7-89b6-d804f34611f1",
                "lesson_id": "lesson-one",
                "plan_date": "2026-09-02",
                "completed_at": "2026-09-02T08:00:00Z",
                "cards_total": 5,
                "cards_known": 4,
                "contract_version": "1.0",
            },
            today=date(2026, 9, 2),
        )

        stored = record_lesson_result_event("access", result)

        self.assertEqual(stored, {"status": "created"})
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.headers["Authorization"], "Bearer access")
        self.assertTrue(request.full_url.endswith("/rest/v1/rpc/record_lesson_result"))
        payload = json.loads(request.data)
        self.assertNotIn("user_id", payload)
        self.assertNotIn("p_user_id", payload)
        self.assertEqual(payload["p_event_id"], result.event_id)

    def test_unconfigured_profile_store_does_not_attempt_a_write(self):
        self.assertFalse(save_profile_settings("token", "user", "Anna", "A2"))

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
        SUPABASE_AUTH_TIMEOUT=2,
    )
    @patch("polskiflow.progress_store.urlopen")
    def test_profile_is_updated_with_user_token(self, mocked_urlopen):
        mocked_urlopen.return_value.__enter__.return_value = MagicMock(status=204)

        saved = save_profile_settings("access", "user-123", "Anna", "B1")

        self.assertTrue(saved)
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.method, "PATCH")
        self.assertEqual(request.headers["Authorization"], "Bearer access")
        self.assertEqual(
            json.loads(request.data), {"display_name": "Anna", "level": "B1", "daily_goal_lessons": 4, "daily_goal_minutes": 15}
        )
        self.assertIn("profiles?id=eq.user-123", request.full_url)

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
    )
    @patch("polskiflow.progress_store.urlopen", side_effect=TimeoutError)
    def test_profile_update_reports_data_api_failure(self, _mocked_urlopen):
        self.assertFalse(save_profile_settings("access", "user", "Anna", "A2"))

    def test_unconfigured_store_does_not_attempt_a_write(self):
        self.assertFalse(save_lesson_completion("token", "user", "quiz", 5, 4))

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
        SUPABASE_AUTH_TIMEOUT=2,
    )
    @patch("polskiflow.progress_store.urlopen")
    def test_completion_is_upserted_with_user_token(self, mocked_urlopen):
        response = MagicMock(status=201)
        mocked_urlopen.return_value.__enter__.return_value = response

        saved = save_lesson_completion("access", "user-123", "quiz", 5, 4)

        self.assertTrue(saved)
        request = mocked_urlopen.call_args.args[0]
        self.assertEqual(request.headers["Authorization"], "Bearer access")
        self.assertEqual(json.loads(request.data)["cards_known"], 4)
        self.assertIn("on_conflict=user_id%2Clesson_id%2Cplan_date", request.full_url)

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
        SUPABASE_AUTH_TIMEOUT=2,
    )
    @patch("polskiflow.progress_store.urlopen", side_effect=TimeoutError)
    def test_completion_timeout_is_safe_to_retry(self, _mocked_urlopen):
        self.assertEqual(
            save_lesson_completion_result("access", "user", "words", 5, 4),
            CompletionSaveResult(saved=False, retryable=True),
        )

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
        SUPABASE_AUTH_TIMEOUT=2,
    )
    @patch("polskiflow.progress_store.urlopen")
    def test_completion_client_error_is_not_queued(self, mocked_urlopen):
        mocked_urlopen.side_effect = HTTPError(
            "https://project.supabase.co", 400, "bad request", {}, None
        )
        self.assertEqual(
            save_lesson_completion_result("access", "user", "words", 5, 4),
            CompletionSaveResult(saved=False, retryable=False),
        )

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
        SUPABASE_AUTH_TIMEOUT=2,
    )
    @patch("polskiflow.progress_store._utc_today", return_value=date(2026, 8, 17))
    @patch("polskiflow.progress_store.urlopen")
    def test_dashboard_uses_profile_and_completion_history(
        self, mocked_urlopen, _mocked_today
    ):
        profile_response = MagicMock()
        profile_response.read.return_value = json.dumps(
            [{"display_name": "Василий", "level": "A2"}]
        ).encode()
        completions_response = MagicMock()
        completions_response.read.return_value = json.dumps(
            [
                {"lesson_id": "words", "plan_date": "2026-08-17"},
                {"lesson_id": "quiz", "plan_date": "2026-08-17"},
                {"lesson_id": "grammar", "plan_date": "2026-08-16", "cards_total": 5, "cards_known": 2},
            ]
        ).encode()
        mocked_urlopen.return_value.__enter__.side_effect = [
            profile_response,
            completions_response,
        ]

        dashboard = load_dashboard_progress("access", "user-123", "learner")

        self.assertEqual(dashboard.display_name, "Василий")
        self.assertEqual(dashboard.level, "A2")
        self.assertEqual(dashboard.streak_days, 2)
        self.assertEqual(dashboard.completed_lesson_ids, {"words", "quiz"})
        self.assertEqual(
            dashboard.all_completed_lesson_ids, {"words", "quiz", "grammar"}
        )
        self.assertEqual(dashboard.active_days, 2)
        self.assertEqual(dashboard.weekly_active_days, 2)
        self.assertEqual(dashboard.weekly_completed_count, 3)
        self.assertEqual(dashboard.monthly_active_days, 2)
        self.assertEqual(dashboard.monthly_completed_count, 3)
        self.assertEqual(len(dashboard.recent_daily_completion_counts), 28)
        self.assertEqual(dashboard.recent_daily_completion_counts[-2:], (1, 2))
        self.assertEqual(
            dashboard.recent_completion_results,
            ({"lesson_id": "grammar", "plan_date": "2026-08-16", "cards_total": 5, "cards_known": 2},),
        )
        self.assertTrue(dashboard.available)
        for call in mocked_urlopen.call_args_list:
            request = call.args[0]
            self.assertEqual(request.headers["Authorization"], "Bearer access")

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
    )
    @patch("polskiflow.progress_store.urlopen", side_effect=TimeoutError)
    def test_dashboard_falls_back_when_data_api_is_unavailable(self, _mocked_urlopen):
        dashboard = load_dashboard_progress("access", "user-123", "learner")

        self.assertEqual(dashboard.display_name, "learner")
        self.assertEqual(dashboard.level, "A1")
        self.assertEqual(dashboard.completed_count, 0)
        self.assertFalse(dashboard.available)

    @override_settings(
        SUPABASE_URL="https://project.supabase.co",
        SUPABASE_ANON_KEY="public-key",
        SUPABASE_AUTH_TIMEOUT=2,
    )
    @patch("polskiflow.progress_store._utc_today", return_value=date(2026, 8, 17))
    @patch("polskiflow.progress_store.urlopen")
    def test_dashboard_compares_two_non_overlapping_seven_day_periods(
        self, mocked_urlopen, _mocked_today
    ):
        profile_response = MagicMock()
        profile_response.read.return_value = b'[{"display_name":"Anna","level":"B1"}]'
        completions_response = MagicMock()
        completions_response.read.return_value = json.dumps(
            [
                {"lesson_id": "current-1", "plan_date": "2026-08-17"},
                {"lesson_id": "current-2", "plan_date": "2026-08-12"},
                {"lesson_id": "previous-1", "plan_date": "2026-08-10"},
                {"lesson_id": "previous-1", "plan_date": "2026-08-09"},
                {"lesson_id": "too-old", "plan_date": "2026-08-03"},
            ]
        ).encode()
        mocked_urlopen.return_value.__enter__.side_effect = [
            profile_response,
            completions_response,
        ]

        dashboard = load_dashboard_progress("access", "user-123", "learner")

        self.assertEqual(dashboard.weekly_completed_count, 2)
        self.assertEqual(dashboard.weekly_active_days, 2)
        self.assertEqual(dashboard.previous_week_completed_count, 1)
        self.assertEqual(dashboard.previous_week_active_days, 2)
        self.assertEqual(dashboard.weekly_completed_delta, 1)
        self.assertEqual(dashboard.weekly_active_days_delta, 0)
