import re

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


from django.test import TestCase
from polskiflow.learning.models import Flashcard, Lesson, Question


class PolishIntroductionsSupportTests(TestCase):
    def test_introductory_lessons_have_polish_support_and_unchanged_source(self):
        lessons = Lesson.objects.filter(pk__in=('words', 'review', 'grammar', 'quiz'))
        self.assertEqual(lessons.count(), 4)
        support = []
        for lesson in lessons:
            support.append(lesson.theory_title)
            support.extend(value for pair in lesson.theory_sections for value in pair)
        questions = list(Question.objects.filter(lesson__in=lessons))
        self.assertEqual(len(questions), 13)
        for question in questions:
            support.extend((question.prompt, question.explanation, *question.options))
        support.extend(Flashcard.objects.filter(lesson_links__lesson__in=lessons).values_list('translation', flat=True))
        with override('pl'):
            for source in support:
                self.assertNotRegex(learning_text(source), r'[А-Яа-яЁё]', source)
        with override('ru'):
            for source in support:
                self.assertEqual(learning_text(source), source)
        for question in questions:
            question.refresh_from_db()
            self.assertLess(question.correct, len(question.options))


class PolishCountriesSupportTests(TestCase):
    def test_countries_lessons_have_polish_support_without_collapsing_choices(self):
        lessons = Lesson.objects.filter(topic_id='countries-languages')
        self.assertEqual(lessons.count(), 5)
        support = []
        for lesson in lessons:
            support.append(lesson.theory_title)
            support.extend(value for pair in lesson.theory_sections for value in pair)
        questions = list(Question.objects.filter(lesson__in=lessons))
        self.assertEqual(len(questions), 16)
        for question in questions:
            support.extend((question.prompt, question.explanation, *question.options))
        support.extend(Flashcard.objects.filter(lesson_links__lesson__in=lessons).values_list('translation', flat=True))
        with override('pl'):
            self.assertEqual([source for source in support if re.search(r'[А-Яа-яЁё]', learning_text(source))], [])
            for question in questions:
                options = [learning_text(option) for option in question.options]
                self.assertEqual(len(set(options)), len(options), question.prompt)
        with override('ru'):
            for source in support:
                self.assertEqual(learning_text(source), source)


class PolishFamilySupportTests(TestCase):
    def test_family_lessons_have_polish_support_without_collapsing_choices(self):
        lessons = Lesson.objects.filter(topic_id='family')
        self.assertEqual(lessons.count(), 5)
        support = []
        for lesson in lessons:
            support.append(lesson.theory_title)
            support.extend(value for pair in lesson.theory_sections for value in pair)
        questions = list(Question.objects.filter(lesson__in=lessons))
        self.assertEqual(len(questions), 16)
        for question in questions:
            support.extend((question.prompt, question.explanation, *question.options))
        support.extend(Flashcard.objects.filter(lesson_links__lesson__in=lessons).values_list('translation', flat=True))
        with override('pl'):
            self.assertEqual([source for source in support if re.search(r'[А-Яа-яЁё]', learning_text(source))], [])
            for question in questions:
                options = [learning_text(option) for option in question.options]
                self.assertEqual(len(set(options)), len(options), question.prompt)
        with override('ru'):
            for source in support:
                self.assertEqual(learning_text(source), source)


class PolishDailyRoutineSupportTests(TestCase):
    def test_daily_routine_lessons_have_polish_support_without_collapsing_choices(self):
        lessons = Lesson.objects.filter(topic_id='daily-routine')
        self.assertEqual(lessons.count(), 5)
        support = []
        for lesson in lessons:
            support.append(lesson.theory_title)
            support.extend(value for pair in lesson.theory_sections for value in pair)
        questions = list(Question.objects.filter(lesson__in=lessons))
        self.assertEqual(len(questions), 16)
        for question in questions:
            support.extend((question.prompt, question.explanation, *question.options))
        support.extend(Flashcard.objects.filter(lesson_links__lesson__in=lessons).values_list('translation', flat=True))
        with override('pl'):
            self.assertEqual([source for source in support if re.search(r'[А-Яа-яЁё]', learning_text(source))], [])
            for question in questions:
                options = [learning_text(option) for option in question.options]
                self.assertEqual(len(set(options)), len(options), question.prompt)
        with override('ru'):
            for source in support:
                self.assertEqual(learning_text(source), source)


class PolishHomeSupportTests(TestCase):
    def test_home_lessons_have_polish_support_without_collapsing_choices(self):
        lessons = Lesson.objects.filter(topic_id='home')
        self.assertEqual(lessons.count(), 5)
        support = []
        for lesson in lessons:
            support.append(lesson.theory_title)
            support.extend(value for pair in lesson.theory_sections for value in pair)
        questions = list(Question.objects.filter(lesson__in=lessons))
        self.assertEqual(len(questions), 16)
        for question in questions:
            support.extend((question.prompt, question.explanation, *question.options))
        support.extend(Flashcard.objects.filter(lesson_links__lesson__in=lessons).values_list('translation', flat=True))
        with override('pl'):
            self.assertEqual([source for source in support if re.search(r'[А-Яа-яЁё]', learning_text(source))], [])
            for question in questions:
                options = [learning_text(option) for option in question.options]
                self.assertEqual(len(set(options)), len(options), question.prompt)
        with override('ru'):
            for source in support:
                self.assertEqual(learning_text(source), source)
