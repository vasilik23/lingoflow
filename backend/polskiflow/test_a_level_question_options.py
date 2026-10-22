from collections import Counter
from importlib import import_module

from django.apps import apps
from django.test import TestCase

from polskiflow.learning.models import Question


class ALevelQuestionOptionTests(TestCase):
    def test_correct_answers_are_balanced_per_level_and_lesson(self):
        expected = {
            "A1": (203, {0: 68, 1: 68, 2: 67}),
            "A2": (226, {0: 76, 1: 75, 2: 75}),
        }
        for level, (total, distribution) in expected.items():
            questions = Question.objects.filter(
                lesson__topic__course__level=level, is_active=True
            )
            self.assertEqual(questions.count(), total)
            self.assertEqual(
                Counter(questions.values_list("correct", flat=True)), distribution
            )
            for lesson_id in questions.values_list("lesson_id", flat=True).distinct():
                indices = set(
                    questions.filter(lesson_id=lesson_id).values_list(
                        "correct", flat=True
                    )
                )
                self.assertGreaterEqual(len(indices), 2, lesson_id)

    def test_rebalance_preserves_answers_and_legacy_option_counts(self):
        expected_answers = {
            ("food-grammar", 2): "chleb",
            ("daily-routine-grammar", 4): "Nigdy nie piję kawy wieczorem.",
            ("a2final-quiz", 5): "Powinieneś odpocząć i skontaktować się z lekarzem.",
            ("med-quiz", 3): "Mam uczulenie na penicylinę.",
        }
        for lookup, answer in expected_answers.items():
            question = Question.objects.get(lesson_id=lookup[0], position=lookup[1])
            self.assertEqual(question.options[question.correct], answer)

        questions = Question.objects.filter(
            lesson__topic__course__level__in=("A1", "A2"), is_active=True
        )
        self.assertEqual(sum(len(question.options) == 4 for question in questions), 8)
        for question in questions:
            self.assertLess(question.correct, len(question.options))

    def test_rebalance_is_rerunnable_after_distribution_is_balanced(self):
        questions = Question.objects.filter(
            lesson__topic__course__level__in=("A1", "A2"), is_active=True
        ).order_by("id")
        before = list(questions.values_list("id", "options", "correct"))

        migration = import_module(
            "polskiflow.learning.migrations.0103_rebalance_a1_a2_question_options"
        )
        migration.rebalance_options(apps, None)

        self.assertEqual(
            list(questions.values_list("id", "options", "correct")), before
        )
