from unittest.mock import patch

from django.test import TestCase
from django.utils.translation import override

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.learning.templatetags.ui import navigation_section


class LearningNavigationTests(TestCase):
    def test_guest_hub_requires_login(self):
        response = self.client.get('/learn/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    @patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('fixture', 'fixture@example.test'))
    def test_hub_keeps_old_routes_and_three_primary_destinations(self, auth):
        self.client.cookies[ACCESS_COOKIE] = 'fixture'
        for lang, label in [('ru', 'Учиться'), ('pl', 'Nauka'), ('en', 'Learn')]:
            with self.subTest(language=lang), override(lang):
                self.client.cookies['django_language'] = lang
                response = self.client.get('/learn/')
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, label)
                self.assertContains(response, 'class="nav-link ', count=3)
                self.assertContains(response, 'href="/learn/" class="nav-link active"')
                self.assertContains(response, 'aria-current="true"', count=1)
                for href in ['/course/', '/reading/', '/dictionary/', '/search/']:
                    self.assertContains(response, f'href="{href}"', count=1)
                self.assertIn('no-store', response['Cache-Control'])

    def test_materials_and_training_keep_correct_section(self):
        for route in ['course', 'lesson', 'reader', 'dictionary', 'news-library', 'global-search']:
            self.assertEqual(navigation_section(route), 'learn')
        for route in ['b1-exam-prep', 'b1-training-run', 'b1-exam-writing', 'dictionary-practice', 'writing-practice']:
            self.assertEqual(navigation_section(route), 'practice')
        self.assertEqual(navigation_section('home'), 'today')
        self.assertEqual(navigation_section('system-settings'), '')
        self.assertEqual(navigation_section(None), '')
