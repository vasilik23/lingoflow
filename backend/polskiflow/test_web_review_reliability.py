from copy import deepcopy
from unittest.mock import patch
from django.core import signing
from django.test import TestCase, override_settings
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser


@override_settings(SUPABASE_URL='', SUPABASE_ANON_KEY='')
class WebReviewReliabilityTests(TestCase):
    def setUp(self):
        self.words = [{'id': f'w{i}', 'word': word, 'translation': translation, 'context': context,
                       'last_reviewed_at': None} for i, (word, translation, context) in enumerate((
            ('dom', 'дом', 'To jest dom.'), ('kot', 'кот', 'To jest kot.'),
            ('chleb', 'хлеб', 'Jem chleb.'), ('okno', 'окно', 'Otwieram okno.')))]
        auth = patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('owner', 'fixture@example.test'))
        auth.start(); self.addCleanup(auth.stop)
        self.client.cookies[ACCESS_COOKIE] = 'fixture'
        load = patch('polskiflow.reading_views.load_personal_words', side_effect=lambda *args: deepcopy(self.words))
        load.start(); self.addCleanup(load.stop)

    def answer(self, mode='translation'):
        page = self.client.get('/dictionary/practice/', {'mode': mode})
        payload = {'action': 'answer', 'index': 0, 'score': 0, 'review_state': page.context['review_state']}
        payload.update({'answer': ' DOM '} if mode == 'context' else {'choice': 0})
        return self.client.post('/dictionary/practice/step/', payload)

    def advance(self, page, **extra):
        return self.client.post('/dictionary/practice/step/', {
            'action': 'next', 'index': page.context['index'], 'score': page.context['score'],
            'selected': page.context['selected'] if page.context['selected'] is not None else '', 'quality': 'good',
            'review_state': page.context['review_state'], **extra})

    @patch('polskiflow.reading_views.save_lesson_completion')
    @patch('polskiflow.reading_views.compare_and_save_personal_word_review', return_value='unavailable')
    def test_failed_grade_keeps_answer_card_score_and_same_snapshot(self, save, completion):
        page = self.answer()
        self.assertContains(page, 'name="review_state"')
        failed = self.advance(page)
        self.assertEqual(failed.context['index'], 0)
        self.assertEqual(failed.context['score'], 0)
        self.assertEqual(failed.context['review_state'], page.context['review_state'])
        self.assertTrue(failed.context['answered'])
        self.assertFalse(failed.context['review_saved'])
        self.assertEqual(failed['Cache-Control'], 'private, no-store')
        completion.assert_not_called()
        save.return_value = 'saved'
        advanced = self.advance(failed)
        self.assertEqual(advanced.context['index'], 1)
        self.assertEqual(advanced.context['score'], 1)
        self.assertEqual(save.call_args_list[0].args[5], save.call_args_list[1].args[5])

    @patch('polskiflow.reading_views.compare_and_save_personal_word_review', return_value='stale')
    def test_stale_snapshot_requires_refresh_and_does_not_advance(self, save):
        failed = self.advance(self.answer())
        self.assertTrue(failed.context['review_stale'])
        self.assertEqual(failed.context['index'], 0)
        self.assertContains(failed, 'Обновить тренировку')
        self.assertNotContains(failed, 'name="quality"')

    @patch('polskiflow.reading_views.save_lesson_completion', return_value=True)
    @patch('polskiflow.reading_views.compare_and_save_personal_word_review', return_value='unavailable')
    def test_last_typed_answer_is_not_consumed_or_completed_before_ack(self, save, completion):
        for row in self.words[1:]: row['next_review_date'] = '2999-01-01'
        page = self.answer('context')
        failed = self.advance(page)
        self.assertTrue(failed.context['answered'])
        self.assertEqual(failed.context['submitted_answer'], 'DOM')
        self.assertIn('dictionary_practice_answer', self.client.session)
        self.assertIn('dictionary_practice_word_ids', self.client.session)
        completion.assert_not_called()
        save.return_value = 'saved'
        done = self.advance(failed)
        self.assertTrue(done.context['practice_complete'])
        completion.assert_called_once()

    @patch('polskiflow.reading_views.compare_and_save_personal_word_review')
    def test_missing_foreign_expired_tampered_or_wrong_phase_form_never_writes(self, save):
        page = self.answer()
        for token in ('', page.context['review_state']+'bad'):
            response = self.advance(page, review_state=token)
            self.assertTrue(response.context['practice_expired'])
        response = self.advance(page, score=1)
        self.assertEqual(response.status_code, 400)
        with patch('django.core.signing.TimestampSigner.unsign', side_effect=signing.SignatureExpired()):
            self.assertTrue(self.advance(page).context['practice_expired'])
        with patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('other', 'other@example.test')):
            self.assertTrue(self.advance(page).context['practice_expired'])
        save.assert_not_called()

    def test_unavailable_dictionary_is_not_an_empty_success(self):
        with patch('polskiflow.reading_views.load_personal_words', return_value=None):
            response = self.client.get('/dictionary/practice/')
            self.assertContains(response, 'Не удалось загрузить тренировку')
            self.assertNotContains(response, 'На сегодня всё')

    @patch('polskiflow.reading_views.compare_and_save_personal_word_review', return_value='stale')
    def test_replaying_old_answer_does_not_get_a_fresh_schedule_snapshot(self, save):
        first = self.client.get('/dictionary/practice/')
        token = first.context['review_state']
        self.words[0]['last_reviewed_at'] = '2026-10-21T12:00:00Z'
        page = self.client.post('/dictionary/practice/step/', {'action': 'answer', 'index': 0,
            'score': 0, 'choice': 0, 'review_state': token})
        failed = self.advance(page)
        self.assertTrue(failed.context['review_stale'])
        self.assertIsNone(save.call_args.args[5])

    @patch('polskiflow.reading_views.compare_and_save_personal_word_review')
    def test_ready_phase_cannot_skip_directly_to_schedule_write(self, save):
        page = self.client.get('/dictionary/practice/')
        response = self.client.post('/dictionary/practice/step/', {'action': 'next', 'index': 0,
            'score': 0, 'selected': 0, 'quality': 'good', 'review_state': page.context['review_state']})
        self.assertTrue(response.context['practice_expired'])
        save.assert_not_called()
