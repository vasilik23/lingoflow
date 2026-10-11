from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override

from polskiflow.learning.templatetags.ui import learning_language


class StudyLanguageTests(SimpleTestCase):
    def test_b1_instruction_and_review_use_the_displayed_support_language(self):
        source = 'Как неформально поздороваться?'
        for lang in ('ru', 'pl', 'en'):
            with self.subTest(lang=lang), override(lang):
                instruction = render_to_string('partials/b1_exam_instruction.html',
                    {'instruction': {'polish': 'Proszę odpowiedzieć.', 'russian': source}})
                self.assertIn('<p lang="pl">Proszę odpowiedzieć.</p>', instruction)
                self.assertIn(f'<p lang="{lang}">', instruction)
                self.assertIn(f'<details lang="{lang}">', instruction)
                question = {'id': 'one', 'prompt': source, 'options': ['Cześć'],
                            'explanation': 'Личная заметка, которой нет в каталоге'}
                html = render_to_string('partials/b1_mock_question.html', {
                    'question': question, 'result': {'details': [{'question': question,
                    'is_correct': True, 'correct_text': 'Cześć'}]}})
                self.assertIn(f'<legend lang="{lang}">', html)
                self.assertIn('<span lang="pl">Cześć</span>', html)
                self.assertIn('<span lang="ru">Личная заметка', html)

    def test_language_matches_translation_and_canonical_polish(self):
        for lang in ('ru', 'pl', 'en'):
            with override(lang):
                self.assertEqual(learning_language('Cześć'), 'pl')
                self.assertEqual(learning_language('Как неформально поздороваться?', lang), lang)
                self.assertEqual(learning_language('Личная заметка, которой нет в каталоге', lang), 'ru')
                self.assertEqual(learning_language('untranslated English', 'en'), 'en')
        self.assertEqual(learning_language('text', 'invalid'), 'ru')

    def test_rendered_answers_and_flashcard_keep_their_language(self):
        with override('en'):
            question = {'prompt': 'Как неформально поздороваться?', 'options': ['Cześć'],
                        'correct': 0, 'explanation': 'Личная заметка, которой нет в каталоге'}
            html = render_to_string('lessons/_question.html', {'question': question, 'index': 0,
                'total': 1, 'lesson_id': 'quiz', 'selected': 0, 'LANGUAGE_CODE': 'en'})
            self.assertIn('<h2 lang="en">How do you greet someone informally?</h2>', html)
            self.assertIn('<span lang="pl">Cześć</span>', html)
            self.assertIn('<span lang="ru">Личная заметка', html)
            card = render_to_string('lessons/_flashcard.html', {'card': {'polish': 'Dziękuję',
                'translation': 'спасибо', 'example': 'Dziękuję za pomoc.'},
                'index': 0, 'total': 1, 'lesson_id': 'words', 'revealed': True, 'LANGUAGE_CODE': 'en'})
            self.assertIn('<h2 class="word" lang="pl">Dziękuję</h2>', card)
            self.assertIn('<p class="translation" lang="en">thank you</p>', card)
            self.assertIn('<p class="example" lang="pl">Dziękuję za pomoc.</p>', card)

    def test_public_example_and_answer_review_preserve_polish_and_fallback_languages(self):
        question = {'prompt': 'Как неформально поздороваться?', 'options': ['Cześć'],
                    'correct': 0, 'explanation': 'Личная заметка, которой нет в каталоге'}
        for lang in ('ru', 'pl', 'en'):
            with self.subTest(lang=lang), override(lang):
                context = {'lesson': {'question': question}, 'selected_text': 'Cześć',
                           'correct_text': 'Cześć'}
                for preview in (True, False):
                    html = render_to_string('partials/public_lesson_question.html',
                                            {**context, 'preview': preview})
                    self.assertIn('<span lang="pl">Cześć</span>', html)
                    review = render_to_string('partials/public_lesson_explanation.html',
                                              {**context, 'preview': preview})
                    self.assertIn('<span lang="pl">Cześć</span>', review)
                    self.assertIn('<p lang="ru">Личная заметка', review)
                theory = render_to_string('partials/public_lesson_theory.html',
                    {'lesson': {'theory_title': 'Как неформально поздороваться?',
                                'theory': ['Cześć', 'Личная заметка, которой нет в каталоге']}})
                self.assertIn('<h3 lang="pl">Cześć</h3>', theory)
                self.assertIn('<p lang="ru">Личная заметка', theory)
