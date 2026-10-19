from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override

from polskiflow.learning.templatetags.ui import learning_language, learning_markup, learning_text, explanation_text, explanation_language
from django.utils.safestring import mark_safe


class StudyLanguageTests(SimpleTestCase):
    def test_russian_explanation_overlay_keeps_canonical_questions_intact(self):
        source = 'Mimo że łączy fakt ograniczający z wnioskiem, który pozostaje aktualny.'
        with override('ru'):
            self.assertEqual(learning_text(source), source)
            self.assertIn('Союз', explanation_text(source))
            self.assertEqual(explanation_language(source), 'ru')
            html = render_to_string('lessons/_question.html', {'question': {
                'prompt': 'Wybierz.', 'options': ['zasługują na'], 'correct': 0,
                'explanation': source}, 'selected': 0, 'index': 0, 'total': 1, 'lesson_id': 'quiz'})
            self.assertIn('<span lang="pl">Mimo że</span>', html)
            self.assertIn('<p lang="ru">Союз', html)
            self.assertIn('class="lesson-answer-status"', html)
            self.assertIn('class="lesson-answer-text" lang="pl">zasługują na', html)
        for language in ('pl', 'en'):
            with override(language):
                self.assertEqual(explanation_text(source), learning_text(source))

    def test_unknown_explanation_is_not_fabricated_and_marks_source_language(self):
        with override('ru'):
            self.assertEqual(explanation_text('Nieznane wyjaśnienie.'), 'Nieznane wyjaśnienie.')
            self.assertEqual(explanation_language('Nieznane wyjaśnienie.'), 'pl')
            self.assertEqual(explanation_language('Пояснение'), 'ru')

    def test_daily_review_description_translates_without_technical_terms(self):
        for language, expected in [('ru', '2 слова к повторению'), ('pl', '2 słowa do powtórki'), ('en', '2 words to review')]:
            with self.subTest(language=language), override(language):
                self.assertEqual(learning_text('2 слова к повторению'), expected)

    def test_writing_selector_uses_plain_escaped_text(self):
        with override('ru'):
            html = render_to_string('writing.html', {'writing_prompts': [{
                'id': 'example', 'title': 'Текст «Jak się masz?» <b>пример</b>',
            }], 'selected_writing_level': 'A1'})
            self.assertIn('<option value="example" lang="ru">Текст «Jak się masz?» &lt;b&gt;пример&lt;/b&gt;</option>', html)

    def test_writing_support_marks_display_language_and_preserves_attributes(self):
        prompt = {'id': 'example', 'title': 'Как неформально поздороваться?',
                  'task': 'Выберите ответ на «Jak się masz?»', 'hint': 'Личная заметка, которой нет в каталоге',
                  'requirements': ['Cześć'], 'checklist': ['Личная заметка, которой нет в каталоге']}
        for language in ('ru', 'pl', 'en'):
            with self.subTest(language=language), override(language):
                html = render_to_string('writing.html', {'writing_prompts': [prompt], 'selected_writing_level': 'A1'})
                self.assertIn(f'<span lang="{language}">', html)
                self.assertIn('<span lang="pl">Jak się masz?</span>', html)
                self.assertIn('<span lang="pl">Cześć</span>', html)
                self.assertIn('<span lang="ru">Личная заметка', html)
                self.assertIn('lang="pl" aria-describedby="draft-help-example"', html)

    def test_speaking_image_accessible_name_is_polish_and_escaped(self):
        html = render_to_string('partials/speaking_visual_dialogue.html', {
            'task': {'image': 'example.png', 'image_alt': 'Osoba <test>', 'image_description': 'Osoba czyta.'}})
        self.assertIn('<img lang="pl"', html)
        self.assertIn('alt="Osoba &lt;test&gt;"', html)

    def test_b1_shared_question_and_review_mark_quotes_and_answers(self):
        question = {'id': 'one', 'prompt': 'Выберите ответ на «Jak się masz?»',
                    'explanation': 'Wyrażenie „jak tylko” oznacza natychmiast.',
                    'options': ['Dobrze', 'Źle']}
        detail = {'question': question, 'is_correct': False, 'selected_text': 'Źle',
                  'correct_text': 'Dobrze', 'theory_lesson': 'grammar'}
        for language in ('ru', 'pl', 'en'):
            with self.subTest(language=language), override(language):
                mock = render_to_string('partials/b1_mock_question.html', {
                    'question': question, 'result': {'details': [detail]}})
                review = render_to_string('partials/b1_run_review.html', {
                    'review': {'status': 'scored', 'details': [detail]}})
                for html in (mock, review):
                    self.assertIn('<span lang="pl">Jak się masz?</span>', html)
                    self.assertIn('<span lang="pl">jak tylko</span>', html)
                    self.assertIn('lang="pl">Dobrze</', html)
                    self.assertIn('lang="pl">Źle</', html)

    def test_b1_written_answer_is_escaped_without_quote_markup(self):
        question = {'id': 'one', 'prompt': 'Uzupełnij.', 'written': True}
        detail = {'question': question, 'selected_text': '<img src=x> „jak tylko”', 'correct_text': 'tak'}
        html = render_to_string('partials/b1_mock_question.html', {
            'question': question, 'result': {'details': [detail]}})
        self.assertIn('&lt;img src=x&gt;', html)
        self.assertNotIn('<span lang="pl">jak tylko</span>', html)
        self.assertNotIn('<img', html)

    def test_reviewed_polish_quote_is_marked_without_changing_translation(self):
        source = 'Выберите ответ на «Jak się masz?»'
        for language in ('ru', 'pl', 'en'):
            with self.subTest(language=language), override(language):
                html = str(learning_markup(source))
                self.assertIn('<span lang="pl">Jak się masz?</span>', html)
                from django.utils.html import strip_tags
                self.assertEqual(strip_tags(html), learning_text(source))

    def test_markup_escapes_html_and_leaves_unknown_quotes_unmarked(self):
        with override('ru'):
            html = str(learning_markup(mark_safe('<img src=x onerror=alert(1)> «Jak się masz?» «Hello»')))
            self.assertNotIn('<img', html)
            self.assertIn('&lt;img', html)
            self.assertIn('<span lang="pl">Jak się masz?</span>', html)
            self.assertNotIn('<span lang="pl">Hello</span>', html)

    def test_rendered_question_marks_polish_inside_support(self):
        with override('en'):
            html = render_to_string('lessons/_question.html', {'question': {
                'prompt': 'Выберите ответ на «Jak się masz?»', 'options': ['Dobrze'],
            }, 'index': 0, 'total': 1, 'lesson_id': 'quiz', 'LANGUAGE_CODE': 'en'})
            self.assertIn('<span lang="pl">Jak się masz?</span>', html)

    def test_b1_instruction_and_review_use_the_displayed_support_language(self):
        source = 'Как неформально поздороваться?'
        for lang in ('ru', 'pl', 'en'):
            with self.subTest(lang=lang), override(lang):
                instruction = render_to_string('partials/b1_exam_instruction.html',
                    {'instruction': {'polish': 'Proszę odpowiedzieć.', 'russian': source}})
                self.assertIn('<p lang="pl">Proszę odpowiedzieć.</p>', instruction)
                self.assertIn(f'<p lang="{lang}">', instruction)
                self.assertIn(f'<section lang="{lang}">', instruction)
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
            self.assertIn('<span class="lesson-answer-text" lang="pl">Cześć</span>', html)
            self.assertIn('<p lang="ru">Личная заметка', html)
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
