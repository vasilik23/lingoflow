import json
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from django.test import TestCase, override_settings

from polskiflow.auth import SupabaseUser


@override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_ANON_KEY="anon")
class Sm2ReviewApiTests(TestCase):
    word_id = uuid.UUID("11111111-1111-4111-8111-111111111111")
    authorization = {"HTTP_AUTHORIZATION": "Bearer owner-token"}

    def _auth(self):
        return patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser(id="owner-1", email="owner@example.com"))

    def _post(self, payload):
        return self.client.post(
            f"/api/v1/me/sm2/{self.word_id}/review/", data=json.dumps(payload),
            content_type="application/json", **self.authorization,
        )

    def _word(self):
        return {"id": str(self.word_id), "ease_factor": 2.5, "interval_days": 6, "repetitions": 2}

    def test_requires_explicit_bearer_even_with_cookie(self):
        self.client.cookies["polskiflow_access_token"] = "cookie-token"
        with self._auth(), patch("polskiflow.api_views.load_personal_words") as load:
            response = self.client.post(
                f"/api/v1/me/sm2/{self.word_id}/review/", data='{"quality":"good"}', content_type="application/json"
            )
        self.assertEqual(response.status_code, 401)
        load.assert_not_called()

    def test_review_uses_owner_state_and_returns_new_schedule(self):
        now = datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
        with self._auth(), patch("polskiflow.api_views.load_personal_words", return_value=[self._word()]) as load, patch(
            "polskiflow.api_views.save_personal_word_review", return_value=True
        ) as save, patch("polskiflow.api_views.timezone.now", return_value=now):
            response = self._post({"quality": "good"})
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["word_id"], str(self.word_id))
        self.assertEqual(data["repetitions"], 3)
        self.assertEqual(data["interval_days"], 15)
        self.assertEqual(data["next_review_date"], "2026-10-01")
        load.assert_called_once_with("owner-token", "owner-1")
        self.assertEqual(save.call_args.args[0:3], ("owner-token", "owner-1", str(self.word_id)))
        self.assertNotIn("owner-1", str(response.json()))

    def test_again_resets_repetitions(self):
        with self._auth(), patch("polskiflow.api_views.load_personal_words", return_value=[self._word()]), patch(
            "polskiflow.api_views.save_personal_word_review", return_value=True
        ), patch("polskiflow.api_views.timezone.now", return_value=datetime(2026, 9, 16, tzinfo=timezone.utc)):
            response = self._post({"quality": "again"})
        self.assertEqual(response.json()["data"]["repetitions"], 0)
        self.assertEqual(response.json()["data"]["next_review_date"], "2026-09-17")

    def test_payload_is_strict_and_never_accepts_ownership_or_state(self):
        invalid = ({}, {"quality": "know"}, {"quality": "good", "user_id": "other"}, {"quality": "good", "repetitions": 99})
        for payload in invalid:
            with self.subTest(payload=payload), self._auth(), patch("polskiflow.api_views.load_personal_words") as load:
                response = self._post(payload)
            self.assertEqual(response.status_code, 400)
            load.assert_not_called()

    def test_missing_owned_word_and_upstream_failures_are_explicit(self):
        with self._auth(), patch("polskiflow.api_views.load_personal_words", return_value=[]):
            missing = self._post({"quality": "good"})
        with self._auth(), patch("polskiflow.api_views.load_personal_words", return_value=None):
            load_failure = self._post({"quality": "good"})
        with self._auth(), patch("polskiflow.api_views.load_personal_words", return_value=[self._word()]), patch(
            "polskiflow.api_views.save_personal_word_review", return_value=False
        ):
            save_failure = self._post({"quality": "good"})
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(load_failure.status_code, 503)
        self.assertEqual(save_failure.status_code, 503)

    def test_versioned_request_uses_conditional_write_and_normalized_snapshot(self):
        previous = '2026-09-16T12:00:00Z'
        word = {**self._word(), 'last_reviewed_at': previous}
        with self._auth(), patch('polskiflow.api_views.load_personal_words', return_value=[word]), patch(
            'polskiflow.api_views.compare_and_save_personal_word_review', return_value='saved'
        ) as save, patch('polskiflow.api_views.save_personal_word_review') as legacy, patch(
            'polskiflow.api_views.timezone.now', return_value=datetime(2026, 9, 16, 12, 0, tzinfo=timezone.utc)
        ):
            response = self._post({'quality': 'good', 'expected_reviewed_at': '2026-09-16T14:00:00+02:00'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(save.call_args.args[0:3], ('owner-token', 'owner-1', str(self.word_id)))
        self.assertEqual(save.call_args.args[4], '2026-09-16T12:00:00.000001+00:00')
        self.assertEqual(save.call_args.args[5], previous)
        legacy.assert_not_called()

    def test_lost_ack_retry_cannot_advance_an_already_changed_snapshot(self):
        word = {**self._word(), 'last_reviewed_at': '2026-09-16T12:00:00Z'}
        with self._auth(), patch('polskiflow.api_views.load_personal_words', return_value=[word]), patch(
            'polskiflow.api_views.compare_and_save_personal_word_review'
        ) as save:
            response = self._post({'quality': 'good', 'expected_reviewed_at': None})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['error']['code'], 'review_stale')
        save.assert_not_called()

    def test_concurrent_write_conflict_and_unavailable_receipt_are_distinct(self):
        for outcome, status in (('stale', 409), ('unavailable', 503), ('saved', 200)):
            with self.subTest(outcome=outcome), self._auth(), patch('polskiflow.api_views.load_personal_words', return_value=[self._word()]), patch(
                'polskiflow.api_views.compare_and_save_personal_word_review', return_value=outcome
            ):
                response = self._post({'quality': 'good', 'expected_reviewed_at': None})
            self.assertEqual(response.status_code, status)

    def test_invalid_snapshot_and_non_string_quality_are_rejected(self):
        payloads = [{'quality': q} for q in ([], {}, True, None)]
        payloads += [{'quality': 'good', 'expected_reviewed_at': version} for version in (
            [], {}, True, '2026-09-16', '2026-09-16T12:00:00', 'eq.x,or=(user_id.not.is.null)')]
        for payload in payloads:
            with self.subTest(payload=payload), self._auth(), patch('polskiflow.api_views.load_personal_words') as load:
                self.assertEqual(self._post(payload).status_code, 400)
            load.assert_not_called()
