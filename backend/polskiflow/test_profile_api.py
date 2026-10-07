import json
from unittest.mock import patch

from django.test import TestCase, override_settings

from polskiflow.auth import SupabaseUser
from polskiflow.progress_store import DashboardProgress


@override_settings(SUPABASE_URL="https://example.supabase.co", SUPABASE_ANON_KEY="anon")
class ProfileApiTests(TestCase):
    def test_older_client_roundtrip_can_change_legacy_goal_without_losing_minutes(self):
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress", return_value=self._progress()), patch("polskiflow.api_views.save_profile_settings", return_value=True):
            response = self.client.patch("/api/v1/me/profile/", data=json.dumps({"display_name": "Ada", "level": "A2", "daily_goal_lessons": 6, "daily_goal_minutes": 15}), content_type="application/json", **self.authorization)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["profile"]["daily_goal_minutes"], 30)

    def test_minutes_patch_persists_canonical_goal_and_rejects_competing_fields(self):
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress", return_value=self._progress()), patch("polskiflow.api_views.save_profile_settings", return_value=True) as save:
            response = self.client.patch("/api/v1/me/profile/", data=json.dumps({"daily_goal_minutes": 30}), content_type="application/json", **self.authorization)
            self.assertEqual(response.json()["data"]["profile"]["daily_goal_minutes"], 30)
            save.assert_called_once_with("owner-token", "owner-1", "Ada", "A2", 6, daily_goal_minutes=30)
            save.reset_mock()
            for value in (True, "30", 0, 20, 31):
                invalid = self.client.patch("/api/v1/me/profile/", data=json.dumps({"daily_goal_minutes": value}), content_type="application/json", **self.authorization)
                self.assertEqual(invalid.status_code, 400)
            conflicting = self.client.patch("/api/v1/me/profile/", data=json.dumps({"daily_goal_minutes": 10, "daily_goal_lessons": 6}), content_type="application/json", **self.authorization)
            self.assertEqual(conflicting.status_code, 400)
            save.assert_not_called()

    authorization = {"HTTP_AUTHORIZATION": "Bearer owner-token"}

    def _auth(self):
        return patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser(id="owner-1", email="ada@example.com"))

    def _progress(self, available=True):
        return DashboardProgress("Ada", "A2", 3, frozenset(), available, daily_goal_lessons=4)

    def test_get_requires_explicit_bearer_and_returns_only_settings(self):
        self.client.cookies["polskiflow_access_token"] = "cookie-token"
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress") as load:
            rejected = self.client.get("/api/v1/me/profile/")
        self.assertEqual(rejected.status_code, 401)
        load.assert_not_called()

        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress", return_value=self._progress()) as load:
            response = self.client.get("/api/v1/me/profile/", **self.authorization)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["profile"], {"display_name": "Ada", "level": "A2", "daily_goal_lessons": 4, "daily_goal_minutes": 15})
        load.assert_called_once_with("owner-token", "owner-1", "ada")
        self.assertNotIn("owner-1", str(response.json()))
        self.assertNotIn("email", response.json()["data"]["profile"])

    def test_patch_merges_partial_fields_and_derives_owner(self):
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress", return_value=self._progress()), patch(
            "polskiflow.api_views.save_profile_settings", return_value=True
        ) as save:
            response = self.client.patch(
                "/api/v1/me/profile/", data=json.dumps({"display_name": "  Anna  ", "daily_goal_lessons": 6}),
                content_type="application/json", **self.authorization,
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["profile"], {"display_name": "Anna", "level": "A2", "daily_goal_lessons": 6, "daily_goal_minutes": 30})
        save.assert_called_once_with("owner-token", "owner-1", "Anna", "A2", 6)

    def test_patch_accepts_all_curriculum_levels(self):
        for level in ("A1", "A2", "B1", "B2", "C1", "C2"):
            with self.subTest(level=level), self._auth(), patch(
                "polskiflow.api_views.load_dashboard_progress", return_value=self._progress()
            ), patch("polskiflow.api_views.save_profile_settings", return_value=True):
                response = self.client.patch(
                    "/api/v1/me/profile/", data=json.dumps({"level": level}),
                    content_type="application/json", **self.authorization,
                )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["data"]["profile"]["level"], level)

    def test_patch_rejects_unknown_ownership_and_invalid_values(self):
        invalid = (
            {}, {"user_id": "other"}, {"display_name": " "}, {"display_name": "x" * 81},
            {"level": "B3"}, {"level": "b1"}, {"daily_goal_lessons": 0}, {"daily_goal_lessons": 11},
            {"daily_goal_lessons": True}, {"daily_goal_lessons": "4"},
        )
        for payload in invalid:
            with self.subTest(payload=payload), self._auth(), patch(
                "polskiflow.api_views.load_dashboard_progress", return_value=self._progress()
            ), patch("polskiflow.api_views.save_profile_settings") as save:
                response = self.client.patch(
                    "/api/v1/me/profile/", data=json.dumps(payload), content_type="application/json", **self.authorization,
                )
            self.assertEqual(response.status_code, 400)
            save.assert_not_called()

    def test_read_and_write_failures_return_503(self):
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress", return_value=self._progress(False)):
            read_failure = self.client.get("/api/v1/me/profile/", **self.authorization)
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress", return_value=self._progress()), patch(
            "polskiflow.api_views.save_profile_settings", return_value=False
        ):
            write_failure = self.client.patch(
                "/api/v1/me/profile/", data=json.dumps({"level": "B1"}), content_type="application/json", **self.authorization,
            )
        self.assertEqual(read_failure.status_code, 503)
        self.assertEqual(write_failure.status_code, 503)

    def test_supports_head_and_rejects_post(self):
        with self._auth(), patch("polskiflow.api_views.load_dashboard_progress", return_value=self._progress()):
            head = self.client.head("/api/v1/me/profile/", **self.authorization)
            post = self.client.post("/api/v1/me/profile/", **self.authorization)
        self.assertEqual(head.status_code, 200)
        self.assertEqual(post.status_code, 405)
