from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
from unittest.mock import patch

from django.test import TestCase, SimpleTestCase
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.browser_reminders import browser_namespace


class BrowserReminderTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = 'access'
        auth = patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('owner-one', 'qa@example.test'))
        auth.start()
        self.addCleanup(auth.stop)
        self.load = patch('polskiflow.browser_reminders.load_reminder_preferences').start()
        self.addCleanup(patch.stopall)
        self.load.return_value = {'daily_reminder_enabled': True, 'reminder_time': '19:00', 'timezone': 'Europe/Warsaw'}

    def test_consent_is_fresh_for_each_read_and_response_is_private(self):
        with patch('polskiflow.browser_reminders.timezone.now', return_value=datetime(2026, 10, 16, 18, tzinfo=timezone.utc)):
            first = self.client.get('/session/reminder/')
            self.assertTrue(first.json()['due'])
            self.assertEqual(first.json()['namespace'], browser_namespace('owner-one'))
            self.assertEqual(first['Cache-Control'], 'private, no-store')
            self.assertIn('Cookie', first['Vary'])
            self.load.return_value['daily_reminder_enabled'] = False
            self.assertFalse(self.client.get('/session/reminder/').json()['due'])
        self.assertEqual(self.load.call_count, 2)
        self.load.assert_called_with('access', 'owner-one')
        self.assertNotIn('access', first.content.decode())
        self.assertNotIn('qa@example.test', first.content.decode())
        self.assertNotEqual(browser_namespace('owner-one'), browser_namespace('owner-two'))

    def test_warsaw_clock_and_day_before_at_and_after_dst(self):
        for utc, due, day in (
            ('2026-10-16T16:59:00+00:00', False, '2026-10-16'),
            ('2026-10-16T17:00:00+00:00', True, '2026-10-16'),
            ('2026-10-16T22:00:00+00:00', False, '2026-10-17'),
            ('2026-10-26T17:59:00+00:00', False, '2026-10-26'),
            ('2026-10-26T18:00:00+00:00', True, '2026-10-26'),
        ):
            with self.subTest(utc=utc), patch('polskiflow.browser_reminders.timezone.now', return_value=datetime.fromisoformat(utc)):
                data = self.client.get('/session/reminder/').json()
                self.assertEqual((data['due'], data['day']), (due, day))
                self.assertFalse(data['background_delivery'])

    def test_unauthenticated_bearer_and_mutation_rejected(self):
        self.assertEqual(self.client.get('/session/reminder/', HTTP_AUTHORIZATION='Bearer access').status_code, 401)
        self.assertEqual(self.client.post('/session/reminder/').status_code, 405)
        self.client.cookies.clear()
        response = self.client.get('/session/reminder/')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.load.assert_not_called()

    def test_unavailable_or_corrupt_preferences_never_become_eligible(self):
        for value in (None, {}, {'reminder_time': '24:00', 'timezone': 'Europe/Warsaw'},
                      {'reminder_time': '19:00', 'timezone': 'Unknown'}):
            self.load.return_value = value
            self.assertEqual(self.client.get('/session/reminder/').status_code, 503)


class BrowserReminderJavascriptTests(SimpleTestCase):
    def test_foreground_consent_storage_and_account_races(self):
        node = shutil.which('node')
        self.assertIsNotNone(node)
        result = subprocess.run([node, str(Path(__file__).with_suffix('.cjs'))], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
