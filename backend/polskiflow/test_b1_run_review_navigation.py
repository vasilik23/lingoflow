"""Review filters preserve assessment; source links follow the pinned version."""
from copy import deepcopy

from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override

from polskiflow.domain.b1_weekly_mock import VARIANTS
from polskiflow.domain.b1_exam_simulation import B1_SIMULATION_PARTS
from polskiflow.domain.b1_training_content import training_questions, training_reading_blocks
from polskiflow.domain.b1_run_review import run_review


class B1ReviewNavigationTests(SimpleTestCase):
    def review(self, variant, part_id, version):
        questions = training_questions(variant, part_id, version)
        answers = {questions[0].id: questions[0].correct,
                   questions[1].id: (questions[1].correct + 1) % len(questions[1].options)}
        part = next(item for item in B1_SIMULATION_PARTS if item['id'] == part_id)
        state = {'content_version': version, 'results': [{'id': part_id, 'status': 'scored'}],
                 'review_answers': {part_id: answers}}
        original = deepcopy(state)
        review = run_review(state, variant, part)
        self.assertEqual(state, original)
        return review

    def test_each_reading_question_links_to_its_exact_versioned_source(self):
        for version in (1, 3, 8, 9):
            for variant in VARIANTS:
                review = self.review(variant, 'reading', version)
                blocks = training_reading_blocks(variant, version)
                for detail in review['details']:
                    index = next(i for i, block in enumerate(blocks)
                                 if detail['question'].id in {q.id for q in block.questions})
                    self.assertEqual(detail['source_anchor'], f'run-review-reading-source-{index}')
                    self.assertIsNone(detail['theory_lesson'])
                    self.assertEqual(review['sources'][index]['text'], blocks[index].text)

    def test_listening_uses_transcript_not_unrelated_grammar(self):
        for version in (1, 9, 10):
            for variant in VARIANTS:
                review = self.review(variant, 'listening', version)
                sources = {source['anchor'] for source in review['sources']}
                self.assertTrue(sources)
                for detail in review['details']:
                    self.assertIn(detail['source_anchor'], sources)
                    self.assertIsNone(detail['theory_lesson'])
                if version < 10:
                    self.assertEqual(review['sources'][0]['text'], variant.listening_transcript)

    @override('ru')
    def test_without_javascript_all_answers_and_sources_remain_available(self):
        review = self.review(VARIANTS[0], 'reading', 9)
        html = render_to_string('partials/b1_run_review.html', {'review': review})
        self.assertIn('data-review-filters', html)
        self.assertIn('aria-label="Показать ответы" hidden', html)
        self.assertEqual(html.count('data-review-answer='), len(review['details']))
        self.assertNotIn('data-review-answer="correct" hidden', html)
        self.assertNotIn('b1media-grammar', html)
        self.assertIn('data-review-source-link', html)
        for source in review['sources']:
            self.assertIn(f'id="{source["anchor"]}"', html)
        self.assertIn('data-review-answer="correct"', html)
        self.assertIn('data-review-answer="incorrect"', html)
        self.assertIn('data-review-answer="unanswered"', html)
