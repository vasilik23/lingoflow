"""English study support preserves canonical answers and account state."""
import gettext as std_gettext
import json
import re
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.template import engines
from django.test import SimpleTestCase, TestCase
from django.utils.translation import gettext, override

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.learning.templatetags.ui import learning_text, ui_text


class EnglishInterfaceTests(SimpleTestCase):
    def test_english_auth_cookie_and_no_global_menu_selector(self):
        page = self.client.get('/login/', HTTP_ACCEPT_LANGUAGE='en-US,en;q=0.9')
        self.assertContains(page, '<html lang="en">')
        self.assertContains(page, 'Sign in to LingoFlow')
        self.assertContains(page, '<option value="en" selected>English</option>')
        self.assertNotContains(page, 'class="language-switcher"')
        response = self.client.post('/language/', {'language': 'en', 'next': '/login/'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.cookies[settings.LANGUAGE_COOKIE_NAME].value, 'en')
        self.assertContains(self.client.get('/login/', HTTP_ACCEPT_LANGUAGE='ru'), '<html lang="en">')
        response = self.client.post('/login/', {})
        self.assertContains(response, 'Enter your email and password')

    def test_static_messages_placeholders_and_browser_catalog(self):
        call_command('build_ui_catalog', language='en', check=True, stdout=StringIO())
        root = Path(settings.BASE_DIR)
        with override('en'):
            for path in (root / 'templates').rglob('*.html'):
                for message in re.findall(r'\{% translate ("(?:[^"\\]|\\.)*") %\}', path.read_text()):
                    text = json.loads(message)
                    self.assertNotEqual(gettext(text), text, f'{path}: {text}')
            for name in ('browser_messages.json', 'server_patterns.json', 'learning_messages.json'):
                for text in json.loads((root / 'polskiflow/localization' / name).read_text()):
                    translated = gettext(text)
                    self.assertNotEqual(translated, text, text)
                    self.assertFalse(re.search('[А-Яа-яЁё]', translated), text)
                    self.assertEqual(re.findall(r'%\(v\d+\)s', text), re.findall(r'%\(v\d+\)s', translated), text)
            self.assertEqual(ui_text('2 урока'), '2 lessons')
            self.assertEqual(ui_text('1 слово'), '1 word')
            self.assertEqual(ui_text('12 слов'), '12 words')

    def test_english_manifest_and_offline_are_separate_from_russian_and_polish(self):
        response = self.client.get('/manifest.webmanifest?language=en', HTTP_ACCEPT_LANGUAGE='ru')
        self.assertEqual(json.loads(response.content)['lang'], 'en')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        response = self.client.get('/offline/?language=en')
        self.assertContains(response, '<html lang="en">')
        self.assertEqual(response['Content-Language'], 'en')
        self.assertIn('&language=en', self.client.get('/service-worker.js?language=en').content.decode())

    def test_learning_filter_is_english_only_and_escapes_markup(self):
        with override('en'):
            self.assertEqual(learning_text('спасибо'), 'thank you')
            self.assertEqual(learning_text('Dziękuję'), 'Dziękuję')
            self.assertEqual(learning_text('Личная заметка, которой нет в каталоге'), 'Личная заметка, которой нет в каталоге')
            template = engines['django'].from_string('{% load ui %}{{ text|learning_text }}')
            self.assertEqual(template.render({'text': '<script>alert(1)</script>'}), '&lt;script&gt;alert(1)&lt;/script&gt;')
        for language in ('ru', 'pl'):
            with override(language):
                self.assertEqual(learning_text('спасибо'), 'спасибо')


class EnglishLearningTests(TestCase):
    def test_all_shipped_learning_support_is_covered_without_changing_canonical_data(self):
        from polskiflow.learning.models import Flashcard, Lesson, Question, ReadingText
        def check(value):
            if isinstance(value, str) and re.search('[А-Яа-яЁё]', value):
                self.assertFalse(re.search('[А-Яа-яЁё]', str(learning_text(value))), value)
            elif isinstance(value, dict):
                for item in value.values(): check(item)
            elif isinstance(value, (list, tuple)):
                for item in value: check(item)
        with override('en'):
            for model, fields in ((Flashcard, ('translation', 'example')), (Lesson, ('theory_title', 'theory_sections')),
                                  (Question, ('prompt', 'options', 'explanation')), (ReadingText, ('description', 'glossary'))):
                for row in model.objects.values(*fields): check(row)
        self.assertTrue(Flashcard.objects.filter(translation='спасибо').exists())

    def test_english_search_uses_localized_metadata(self):
        from polskiflow.catalog_search import search_learning_catalog
        from polskiflow.learning.models import Topic
        topic = Topic.objects.get(title='Биография и опыт')
        with override('en'):
            self.assertIn(topic.id, [row['id'] for row in search_learning_catalog('biography')['topics']])

    @patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('english-user', 'english@example.com'))
    def test_switching_to_english_preserves_signed_exam_state(self, authenticate):
        self.client.cookies[ACCESS_COOKIE] = 'test-access'
        intro = self.client.get('/exam/b1/run/')
        started = self.client.post('/exam/b1/run/', {'run_token': intro.context['run_token'], 'action': 'start'})
        token = started.context['run_token']
        self.client.post('/language/', {'language': 'en', 'next': '/exam/b1/run/'})
        restored = self.client.post('/exam/b1/run/', {'run_token': token, 'action': 'resume'})
        self.assertEqual(restored.context['run_token'], token)
        self.assertEqual(restored.context['state'], started.context['state'])
        self.assertEqual(restored.context['questions'], started.context['questions'])
        self.assertContains(restored, 'Explanation in English')
        self.assertContains(restored, 'lang="pl"')

    def test_every_active_reading_has_complete_optional_english_translation(self):
        from polskiflow.learning.models import ReadingText
        from polskiflow.learning.templatetags.ui import english_reading
        for text in ReadingText.objects.filter(is_active=True):
            original = list(text.paragraphs)
            with override('en'):
                translated = english_reading(original)
                self.assertEqual(len(translated), len(original), text.id)
                for source, target in zip(original, translated):
                    self.assertNotEqual(source, target, text.id)
                    self.assertFalse(re.search('[А-Яа-яЁё]', target), text.id)
                    self.assertNotIn('▁', target, text.id)
            for language in ('ru', 'pl'):
                with override(language):
                    self.assertEqual(english_reading(original), [])
            text.refresh_from_db()
            self.assertEqual(text.paragraphs, original)
        with override('en'):
            self.assertEqual(english_reading(['Unpublished paragraph']), [])

    @patch('polskiflow.reading_views.save_personal_word', return_value=True)
    @patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('english-reader', 'reader@example.com'))
    def test_english_reader_preserves_original_glossary_when_saving(self, authenticate, save):
        from polskiflow.learning.models import ReadingText
        from polskiflow.reading_views import _glossary_entries
        self.client.cookies[ACCESS_COOKIE] = 'test-access'
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'en'
        text = ReadingText.objects.filter(is_active=True).first()
        surface, entry = next(iter(_glossary_entries(text.glossary).items()))
        page = self.client.get(f'/reading/{text.id}/')
        self.assertContains(page, 'English translation')
        self.assertContains(page, 'data-source-translation=')
        response = self.client.post(f'/reading/{text.id}/save/', {'word': surface, 'translation': entry['translation'], 'context': 'Polish context'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(save.call_args.args[3], entry['translation'])

    def test_polish_examples_are_retained_inside_english_explanations(self):
        from polskiflow.content import grammar
        with override('en'):
            theory = grammar('grammar')
            examples = next(body for heading, body in theory['sections'] if 'Jestem Anna' in body)
            translated = learning_text(examples)
            self.assertIn('Jestem Anna.', translated)
            self.assertIn('Jestem z Polski.', translated)
            self.assertIn("I'm Anna", translated)
