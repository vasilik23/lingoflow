from unittest.mock import patch

from django.test import TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.progress_store import CompletionHistoryPage, DashboardProgress


class MenuSectionTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        dashboard = DashboardProgress("Learner", "A1", 2, frozenset(), True)
        for target, value in (
            ("polskiflow.auth.authenticate_access_token", SupabaseUser("user-1", "learner@example.com")),
            ("polskiflow.auth_views.load_dashboard_progress", dashboard),
            ("polskiflow.history_views.load_dashboard_progress", dashboard),
            ("polskiflow.history_views.load_personal_words", []),
            ("polskiflow.history_views.load_completion_history", CompletionHistoryPage((), True, False, False, 1)),
            ("polskiflow.auth_views.load_reminder_preferences", {"daily_reminder_enabled": False, "reminder_time": "19:00", "timezone": "Europe/Warsaw"}),
        ):
            mocked = patch(target, return_value=value)
            mocked.start()
            self.addCleanup(mocked.stop)

    def test_controls_and_progress_have_one_owner_section(self):
        pages = {path: self.client.get(path) for path in (
            "/profile/", "/settings/", "/history/", "/account/security/", "/help/",
        )}
        owners = {
            'name="display_name"': "/profile/",
            'name="level"': "/profile/",
            'id="interface-language"': "/settings/",
            'data-theme-select aria-label=': "/settings/",
            'name="daily_reminder_enabled"': "/settings/",
            'id="achievements-title"': "/history/",
            'id="progress-title"': "/history/",
            'name="current_password"': "/account/security/",
            'href="/profile/export/"': "/account/security/",
            'href="/account/delete/"': "/account/security/",
            'href="/sources/"': "/help/",
        }
        for marker, owner in owners.items():
            for path, response in pages.items():
                with self.subTest(marker=marker, path=path):
                    self.assertEqual(response.status_code, 200)
                    if path == owner:
                        self.assertContains(response, marker, count=1)
                    else:
                        self.assertNotContains(response, marker)
        menu = pages["/profile/"].content.decode().split('class="user-menu-popover">', 1)[1].split('</details>', 1)[0]
        self.assertEqual(menu.count('class="user-menu-link"'), 6)
        self.assertNotIn('<details', menu)

    @patch("polskiflow.auth_views.save_profile_settings")
    @patch("polskiflow.auth_views.save_reminder_preferences", return_value=True)
    def test_system_settings_save_reminders_without_writing_profile(self, reminders, profile):
        response = self.client.post("/settings/", {
            "form_action": "reminders", "daily_reminder_enabled": "on", "reminder_time": "08:30",
        })
        self.assertContains(response, "Настройки напоминаний сохранены")
        reminders.assert_called_once_with("access", "user-1", True, "08:30", "Europe/Warsaw")
        profile.assert_not_called()
        self.assertEqual(self.client.post("/settings/", {"form_action": "profile"}).status_code, 405)
        profile.assert_not_called()

    def test_new_sections_require_login(self):
        self.client.cookies.clear()
        for path in ("/settings/", "/help/"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 302)
