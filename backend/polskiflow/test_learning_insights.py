from datetime import date
from types import SimpleNamespace

from django.test import SimpleTestCase

from polskiflow.domain.learning_insights import build_learning_insights


class LearningInsightsTests(SimpleTestCase):
    def dashboard(self, **overrides):
        values = {
            "available": True,
            "level": "B1",
            "recent_daily_completion_counts": tuple(range(28)),
            "recent_completion_results": (),
        }
        values.update(overrides)
        return SimpleNamespace(**values)

    def test_builds_activity_accuracy_breakdown_and_bounded_recommendation(self):
        dashboard = self.dashboard(
            recent_daily_completion_counts=(0,) * 26 + (1, 2),
            recent_completion_results=(
                {"lesson_id": "grammar", "cards_known": 3, "cards_total": 10},
                {"lesson_id": "words", "cards_known": 9, "cards_total": 10},
            ),
        )
        lessons = [
            {"id": "grammar", "kind": "grammar"},
            {"id": "words", "kind": "words"},
        ]

        result = build_learning_insights(dashboard, lessons, date(2026, 9, 24))

        self.assertEqual(result["completed_28_days"], 3)
        self.assertEqual(result["active_28_days"], 2)
        self.assertEqual(result["accuracy"], 30)
        self.assertEqual(result["activity"][-1]["date"], "24.09")
        self.assertEqual(result["recommendation"]["href"], "/course/?level=B1&kind=grammar")
        self.assertEqual({item["kind"] for item in result["breakdown"]}, {"grammar"})

    def test_self_assessment_does_not_inflate_verified_accuracy(self):
        result = build_learning_insights(self.dashboard(recent_completion_results=(
            {"lesson_id": "cards", "cards_known": 10, "cards_total": 10},
            {"lesson_id": "quiz", "cards_known": 0, "cards_total": 2},
        )), [{"id": "cards", "kind": "words"}, {"id": "quiz", "kind": "quiz"}])
        self.assertEqual(result["accuracy"], 0)
        self.assertEqual(result["answer_count"], 2)
        self.assertEqual((result["self_known"], result["self_total"]), (10, 10))
        self.assertEqual([row["kind"] for row in result["breakdown"]], ["quiz"])

    def test_empty_results_are_honest_and_keep_linear_plan(self):
        result = build_learning_insights(
            self.dashboard(recent_daily_completion_counts=(), recent_completion_results=()),
            [],
            date(2026, 9, 24),
        )

        self.assertIsNone(result["accuracy"])
        self.assertEqual(result["breakdown"], [])
        self.assertEqual(result["recommendation"]["href"], "/#daily-tasks")
        self.assertEqual(len(result["activity"]), 14)
