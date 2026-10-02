from django.test import SimpleTestCase

from polskiflow.auth_views import WRITING_PROMPTS
from polskiflow.domain.writing_reinforcement import (
    enrich_writing_prompts,
    writing_focus_recommendation,
)


class WritingReinforcementTests(SimpleTestCase):
    def test_every_b1_focus_resolves_to_a_specific_grammar_lesson(self):
        prompts = enrich_writing_prompts(WRITING_PROMPTS["B1"])

        for prompt in prompts:
            self.assertEqual(
                len(prompt["grammar_recommendations"]),
                len(prompt["grammar_focus"]),
            )
            for focus, recommendation in zip(
                prompt["grammar_focus"], prompt["grammar_recommendations"]
            ):
                self.assertEqual(recommendation["label"], focus)
                self.assertTrue(recommendation["lesson_id"].endswith("-grammar"))
                self.assertTrue(recommendation["lesson_title"])

    def test_known_focus_uses_relevant_stable_lesson(self):
        self.assertEqual(
            writing_focus_recommendation("вид глагола"),
            {
                "label": "вид глагола",
                "lesson_id": "bio-grammar",
                "lesson_title": "Вид и прошедшее время",
            },
        )
        self.assertEqual(
            writing_focus_recommendation("условные конструкции")["lesson_id"],
            "b1work-grammar",
        )

    def test_enrichment_does_not_mutate_shared_prompt_contract(self):
        enrich_writing_prompts(WRITING_PROMPTS["B1"])

        self.assertNotIn("grammar_recommendations", WRITING_PROMPTS["B1"][0])
