from datetime import date, timedelta
from unittest.mock import patch

from django.core import signing
from django.http import HttpResponse
from django.test import Client, RequestFactory, SimpleTestCase, TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.b1_weekly_mock import VARIANTS, weekly_mock_variant
from polskiflow.domain.practice_recommendations import practice_recommendation
from polskiflow.practice_preferences import (
    PREFERENCE_COOKIE, PREFERENCE_MAX_AGE, excluded_practice_topics, set_practice_topics,
)


class PracticePreferenceDomainTests(SimpleTestCase):
    def test_rotation_skips_remote_work_but_catalog_lookup_remains_available(self):
        seen = set()
        for week in range(53):
            today = date(2026, 1, 1) + timedelta(weeks=week)
            variant = weekly_mock_variant(today, ("remote-work",))
            self.assertNotIn("remote-work", variant.topics)
            seen.add(variant.id)
        self.assertEqual(seen, {"b1-weekly-v1", "b1-weekly-v3"})
        self.assertEqual(weekly_mock_variant(date(2026, 1, 5)).id, "b1-weekly-v2")
        self.assertEqual(len(VARIANTS), 3)

    def test_b2_recommendations_have_alternatives_for_every_day(self):
        seen = set()
        for offset in range(14):
            item = practice_recommendation("B2", date(2026, 1, 1) + timedelta(days=offset), ("remote-work",))
            self.assertNotIn("remote-work", item["topics"])
            seen.add(item["href"])
        self.assertEqual(len(seen), 2)
        self.assertIsNone(practice_recommendation("A1", date(2026, 1, 1)))

    def test_cookie_is_private_expiring_and_account_scoped(self):
        request = RequestFactory().get("/practice/", secure=True)
        request.supabase_user = SupabaseUser("owner", "learner@example.com")
        response = HttpResponse()
        set_practice_topics(response, request, exclude_remote_work=True)
        cookie = response.cookies[PREFERENCE_COOKIE]
        self.assertTrue(cookie["secure"])
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertEqual(cookie["max-age"], PREFERENCE_MAX_AGE)
        request.COOKIES[PREFERENCE_COOKIE] = cookie.value
        self.assertEqual(excluded_practice_topics(request), ("remote-work",))
        request.supabase_user = SupabaseUser("other", "other@example.com")
        self.assertEqual(excluded_practice_topics(request), ())
        request.supabase_user = SupabaseUser("owner", "learner@example.com")
        request.COOKIES[PREFERENCE_COOKIE] += "tampered"
        self.assertEqual(excluded_practice_topics(request), ())
        with patch("polskiflow.practice_preferences.signing.loads", side_effect=signing.SignatureExpired):
            self.assertEqual(excluded_practice_topics(request), ())


class PracticePreferenceViewTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("user-123", "learner@example.com"))
        auth.start()
        self.addCleanup(auth.stop)

    def test_save_filters_new_b1_attempts_and_reset_restores_default(self):
        with patch("polskiflow.b1_mock_views.timezone.localdate", return_value=date(2026, 1, 5)):
            opened = self.client.get("/exam/b1/mock/")
            self.assertEqual(opened.context["variant"].id, "b1-weekly-v2")
            saved = self.client.post("/practice/", {"exclude_remote_work": "on"})
            self.assertEqual(saved.status_code, 302)
            self.assertEqual(saved["Cache-Control"], "private, no-store")
            self.assertNotEqual(self.client.get("/exam/b1/mock/").context["variant"].id, "b1-weekly-v2")
            self.assertNotEqual(self.client.get("/exam/b1/simulation/?part=reading").context["variant"].id, "b1-weekly-v2")
            resumed = self.client.post("/exam/b1/mock/", {"attempt_token": opened.context["attempt_token"], "resume": "1"})
            self.assertEqual(resumed.context["variant"].id, "b1-weekly-v2")
            reset = self.client.post("/practice/", {})
            self.assertEqual(reset.cookies[PREFERENCE_COOKIE]["max-age"], 0)
            self.assertEqual(self.client.get("/exam/b1/mock/").context["variant"].id, "b1-weekly-v2")

    def test_preference_post_requires_csrf_and_authenticated_user(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.cookies[ACCESS_COOKIE] = "access"
        denied = csrf_client.post("/practice/", {"exclude_remote_work": "on"})
        self.assertEqual(denied.status_code, 403)
        self.assertNotIn(PREFERENCE_COOKIE, denied.cookies)
        self.client.cookies.clear()
        self.assertEqual(self.client.post("/practice/", {}).status_code, 302)

    def test_profile_saves_filter_only_with_valid_profile_and_preserves_it_on_failure(self):
        fields = {"display_name": "Anna", "level": "B1", "daily_goal_lessons": "2", "exclude_remote_work": "on", "practice_topics_present": "1"}
        with patch("polskiflow.auth_views.save_profile_settings", return_value=True):
            saved = self.client.post("/profile/", fields)
            self.assertEqual(saved.status_code, 200)
            self.assertIn(PREFERENCE_COOKIE, saved.cookies)
            self.assertTrue(self.client.get("/profile/").context["exclude_remote_work"])
            old_form = self.client.post("/profile/", {k: v for k, v in fields.items() if k not in {"practice_topics_present", "exclude_remote_work"}})
            self.assertNotIn(PREFERENCE_COOKIE, old_form.cookies)
            invalid = self.client.post("/profile/", {**fields, "display_name": ""})
            self.assertNotIn(PREFERENCE_COOKIE, invalid.cookies)
            self.assertTrue(self.client.get("/profile/").context["exclude_remote_work"])
            with patch("polskiflow.auth_views.save_profile_settings", return_value=False):
                failed = self.client.post("/profile/", {**fields, "exclude_remote_work": ""})
                self.assertNotIn(PREFERENCE_COOKIE, failed.cookies)
            reset = self.client.post("/profile/", {**fields, "exclude_remote_work": ""})
            self.assertEqual(reset.cookies[PREFERENCE_COOKIE]["max-age"], 0)
            self.assertFalse(self.client.get("/profile/").context["exclude_remote_work"])
