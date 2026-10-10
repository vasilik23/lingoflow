from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override

from polskiflow.learning.templatetags.ui import learning_text


class PolishLearningSupportTests(SimpleTestCase):
    def test_question_and_review_use_existing_polish_support_without_changing_answers(self):
        question = {
            'prompt': 'Как неформально поздороваться?',
            'options': ['Do widzenia', 'Cześć', 'Dziękuję', 'Przepraszam'],
            'correct': 1,
            'explanation': 'Cześć — неформальное приветствие; оно также может означать «пока».',
        }
        original = dict(question)
        with override('pl'):
            context = {'question': question, 'index': 0, 'total': 1, 'lesson_id': 'quiz', 'selected': None}
            ready = render_to_string('lessons/_question.html', context)
            self.assertIn('Jak przywitać się nieformalnie?', ready)
            self.assertNotIn(question['prompt'], ready)
            answered = render_to_string('lessons/_question.html', {**context, 'selected': 0})
            self.assertIn('Cześć to nieformalne powitanie', answered)
            self.assertNotIn(question['explanation'], answered)
            for option in question['options']:
                self.assertIn(option, ready)
                self.assertIn(option, answered)
            self.assertIn('Niepoprawnie', answered)
            self.assertIn('Poprawna odpowiedź', answered)
        self.assertEqual(question, original)
        with override('ru'):
            self.assertEqual(learning_text(question['prompt']), question['prompt'])
        with override('en'):
            self.assertEqual(learning_text(question['prompt']), 'How do you greet someone informally?')
