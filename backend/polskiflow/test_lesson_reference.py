"""Published pilot support stays in the exercise without changing assessment state."""
import re
from unittest.mock import patch

from django.test import TestCase, override_settings, RequestFactory
from django.utils.translation import override

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.content import grammar, quiz, reading_text
from polskiflow.domain.topic_journeys import PILOTS
from polskiflow.lesson_reference import lesson_reference
from polskiflow.lesson_views import _complete
from polskiflow.progress_store import CompletionSaveResult


@override_settings(SUPABASE_URL='', SUPABASE_ANON_KEY='')
class LessonReferenceTests(TestCase):
    def setUp(self):
        self.user = SupabaseUser('reference-fixture', 'fixture@example.test')
        auth = patch('polskiflow.auth.authenticate_access_token', return_value=self.user)
        auth.start()
        self.addCleanup(auth.stop)
        self.client.cookies[ACCESS_COOKIE] = 'fixture'

    def state(self, response):
        return re.search(r'name="state" value="([^"]+)"', response.content.decode()).group(1)

    def test_pilot_checks_render_the_matching_rule_or_full_reading_in_three_languages(self):
        for lang in ('ru', 'pl', 'en'):
            self.client.cookies['django_language'] = lang
            for pilot in PILOTS.values():
                for position in (1, 3, 4):
                    lesson_id = pilot['lessons'][position]
                    response = self.client.get(f'/lesson/{lesson_id}/')
                    if position == 1:
                        response = self.client.post(f'/lesson/{lesson_id}/step/', {'action':'start', 'state':self.state(response)})
                    self.assertContains(response, 'data-lesson-reference', count=1)
                    reference = response.context['lesson_reference']
                    if position == 3:
                        self.assertEqual(reference['paragraphs'], reading_text(pilot['reading_id']).paragraphs)
                        self.assertContains(response, reference['paragraphs'][0])
                    else:
                        self.assertEqual(reference['sections'], grammar(pilot['lessons'][1])['sections'])

    @patch('polskiflow.lesson_views.set_mistake', return_value=True)
    @patch('polskiflow.lesson_views.save_lesson_draft', return_value=True)
    def test_wrong_answer_and_next_keep_reference_and_authoritative_score(self, save, mistake):
        for pilot in PILOTS.values():
            lesson_id = pilot['lessons'][4]
            response = self.client.get(f'/lesson/{lesson_id}/')
            wrong = (quiz(lesson_id)[0]['correct'] + 1) % len(quiz(lesson_id)[0]['options'])
            response = self.client.post(f'/lesson/{lesson_id}/step/', {'action':'answer','state':self.state(response),'choice':wrong})
            self.assertEqual(response.context['score'], 0)
            self.assertContains(response, 'data-lesson-feedback')
            self.assertContains(response, 'data-lesson-reference', count=1)
            response = self.client.post(f'/lesson/{lesson_id}/step/', {'action':'next','state':self.state(response)})
            self.assertEqual((response.context['index'], response.context['score']), (1, 0))
            self.assertContains(response, 'data-lesson-reference', count=1)
            save.assert_called_with('fixture', self.user.id, lesson_id, 'quiz', 1, 0)

    def test_no_cross_topic_or_unbound_reading_reference(self):
        self.assertIsNone(lesson_reference('words', 'words'))
        self.assertIsNone(lesson_reference('b2-work-quiz', 'quiz'))
        reading = reading_text(PILOTS['introductions']['reading_id'])
        reading.source_metadata = {'comprehension_lesson_id':'housing-reading-check'}
        with patch('polskiflow.lesson_reference.reading_text', return_value=reading):
            self.assertIsNone(lesson_reference('a1read-kurs-check', 'quiz'))

    @override('ru')
    @patch('polskiflow.lesson_views.load_mistakes', return_value=[])
    @patch('polskiflow.lesson_views.delete_lesson_draft')
    @patch('polskiflow.lesson_views.save_lesson_completion_result', return_value=CompletionSaveResult(True, False))
    def test_result_separates_self_reported_words_from_correct_answers(self, save, delete, mistakes):
        request = RequestFactory().post('/lesson/words/step/')
        request.supabase_user = self.user
        request.supabase_access_token = 'fixture'
        for pilot in PILOTS.values():
            for position in (0, 2, 4):
                response = _complete(request, pilot['lessons'][position], 1, 5)
                label = 'Правильных ответов' if position == 4 else 'Отмечено «Знаю» · самооценка'
                self.assertContains(response, label)
                self.assertContains(response, '1 / 5')
