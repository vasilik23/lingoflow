"""Public server translation must not depend on an unnecessary client catalogue."""
from django.conf import settings
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.utils.translation import gettext, override

from polskiflow.public_demo_store import load_demo_lesson


class PublicLocaleLoadingTests(TestCase):
    def assert_lightweight(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'polskiflow/i18n-pl.js')
        self.assertNotContains(response, 'polskiflow/i18n-en.js')
        self.assertContains(response, 'polskiflow/i18n.js')
        self.assertContains(response, 'polskiflow/audio-session.js')

    def test_public_pages_keep_server_translations_without_browser_catalogue(self):
        for language in ('ru', 'pl', 'en'):
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
            with override(language):
                for path in ('/', '/start/', '/login/', '/register/', '/forgot-password/',
                             '/reset-password/', '/resend-confirmation/', '/sources/', '/privacy/'):
                    with self.subTest(language=language, path=path):
                        response = self.client.get(path)
                        self.assert_lightweight(response)
                        self.assertContains(response, f'<html lang="{language}">')
                self.assertContains(self.client.get('/login/'), gettext('Вход'))
                self.assertContains(self.client.get('/privacy/'), gettext('Хранение и удаление'))

    def test_wrong_demo_answer_explanation_and_result_remain_localized(self):
        for language in ('ru', 'pl', 'en'):
            self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = language
            for level in ('A1', 'A2', 'B1'):
                with self.subTest(language=language, level=level):
                    self.assert_lightweight(self.client.get('/demo/', {'level': level}))
                    exercise = self.client.get('/demo/', {'level': level, 'step': 'exercise'})
                    self.assert_lightweight(exercise)
                    lesson = load_demo_lesson(level)
                    wrong = (lesson['question']['correct'] + 1) % len(lesson['question']['options'])
                    response = self.client.post('/demo/?level=' + level, {
                        'state': exercise.context['state'], 'answer': str(wrong),
                    }, follow=True)
                    self.assert_lightweight(response)
                    self.assertFalse(response.context['correct'])
                    review = response.context['review']
                    result = self.client.get('/demo/', {'level': level, 'step': 'result', 'review': review})
                    self.assert_lightweight(result)
                    self.assertEqual(result.context['step'], 'result')

    def test_default_learning_shell_keeps_catalogue_before_bootstrap(self):
        request = RequestFactory().get('/')
        for language in ('pl', 'en'):
            with override(language):
                html = render_to_string('base.html', {'request': request, 'LANGUAGE_CODE': language})
                dictionary = html.index(f'polskiflow/i18n-{language}.js')
                bootstrap = html.index('polskiflow/i18n.js')
                self.assertLess(dictionary, bootstrap)
                other = 'en' if language == 'pl' else 'pl'
                self.assertNotIn(f'polskiflow/i18n-{other}.js', html)
