"""Guard actual browser lookup keys, including messages assembled after a click."""
import ast
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.utils.translation import gettext, override


class BrowserLocalizationCoverageTests(SimpleTestCase):
    def test_literal_browser_lookups_have_translations(self):
        root = Path(settings.BASE_DIR)
        paths = list((root / 'templates').rglob('*.html'))
        paths += list((root / 'polskiflow/learning/static/polskiflow').glob('*.js'))
        lookup = re.compile(r'''\b(?:ui|t)\(\s*("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')\s*\)''')
        for path in paths:
            if path.name.startswith('i18n-'):
                continue
            for match in lookup.finditer(path.read_text()):
                source = ast.literal_eval(match[1])
                if not re.search('[А-Яа-яЁё]', source):
                    continue
                for language in ('pl', 'en'):
                    with self.subTest(path=path.name, source=source, language=language), override(language):
                        self.assertNotEqual(gettext(source), source)

    def test_word_counters_and_length_requirements_preserve_numbers(self):
        messages = {
            'pl': ('Słów: %(v0)s', 'Minimum słów: %(v0)s', 'Minimum akapitów: %(v0)s'),
            'en': ('Words: %(v0)s', 'Minimum words: %(v0)s', 'Minimum paragraphs: %(v0)s'),
        }
        sources = ('Слов: %(v0)s', 'Минимум слов: %(v0)s', 'Минимум абзацев: %(v0)s')
        for language, expected in messages.items():
            with override(language):
                for source, target in zip(sources, expected):
                    self.assertEqual(gettext(source), target)
                    for count in (0, 1, 2, 5, 12, 22, 101):
                        self.assertIn(str(count), gettext(source) % {'v0': count})

    def test_english_audio_status_and_grammar_labels_describe_the_actual_action(self):
        with override('en'):
            for level in ('B1', 'B2'):
                self.assertEqual(gettext(f'Запись {level} прослушана'), f'{level} recording finished')
                self.assertEqual(gettext(f'Воспроизведение записи {level}'), f'Playing {level} recording')
            self.assertEqual(gettext('Род'), 'Gender')
            self.assertEqual(gettext('Род и прилагательные'), 'Gender and adjectives')
