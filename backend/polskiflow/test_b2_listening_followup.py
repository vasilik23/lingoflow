from datetime import date
import json
from unittest.mock import patch, MagicMock
from urllib.error import URLError
from uuid import uuid4

from django.core import signing
from django.http import QueryDict
from django.test import SimpleTestCase, TestCase, override_settings

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.auth_views import LISTENING_B2
from polskiflow.b2_listening_store import load_listening_results, save_listening_result
from polskiflow.domain.b2_listening_followup import attempt_state, grade, followup, MATERIAL


def result(mask=1, **extra):
    return {'attempt_id': str(uuid4()), 'material_id': MATERIAL, 'content_version': 1,
            'correct': 3-mask.bit_count(), 'missed_mask': mask,
            'completed_at': '2026-10-21T08:00:00+00:00', **extra}


class B2ListeningDomainTests(SimpleTestCase):
    def answers(self, mask):
        values = QueryDict('', mutable=True)
        for index, question in enumerate(LISTENING_B2['questions']):
            values[question['id']] = next(option for option in question['options'] if (option != question['answer']) == bool(mask & (1 << index)))
        return values

    def test_all_masks_are_graded_from_canonical_form_values(self):
        for mask in range(8):
            checked = grade('owner', attempt_state('owner'), self.answers(mask), LISTENING_B2['questions'])
            self.assertEqual(checked['missed_mask'], mask)
            self.assertEqual(checked['correct'], 3-mask.bit_count())
            self.assertNotIn('answers', checked)

    def test_owner_tamper_expiry_missing_duplicate_and_invalid_answers(self):
        state = attempt_state('owner')
        with self.assertRaises(ValueError):
            grade('other', state, self.answers(0), LISTENING_B2['questions'])
        with self.assertRaises(signing.BadSignature):
            grade('owner', state+'bad', self.answers(0), LISTENING_B2['questions'])
        with patch('django.core.signing.TimestampSigner.unsign', side_effect=signing.SignatureExpired()):
            with self.assertRaises(signing.SignatureExpired):
                grade('owner', state, self.answers(0), LISTENING_B2['questions'])
        for values in ([], ['invalid'], ['x', 'y']):
            answers = self.answers(0)
            answers.setlist(LISTENING_B2['questions'][0]['id'], values)
            with self.assertRaises(ValueError):
                grade('owner', state, answers, LISTENING_B2['questions'])

    def test_failure_selects_matching_lesson_and_becomes_due_next_day(self):
        for mask, lesson in ((1, 'b2view-grammar'), (2, 'b2prof-quiz'), (4, 'b2prof-grammar')):
            item = result(mask)
            current = followup(item, date(2026, 10, 21))
            self.assertFalse(current['due'])
            self.assertEqual(current['href'], '/lesson/'+lesson+'/')
            self.assertEqual(current['due_date'], date(2026, 10, 22))
            self.assertTrue(followup(item, date(2026, 10, 22))['due'])
        self.assertTrue(followup(result(0))['passed'])
        self.assertFalse(followup(result(0))['due'])


@override_settings(SUPABASE_URL='https://fixture.supabase.co', SUPABASE_ANON_KEY='public')
class B2ListeningStoreTests(SimpleTestCase):
    @patch('polskiflow.b2_listening_store.urlopen')
    def test_owner_filter_token_order_and_matching_idempotent_receipt(self, urlopen):
        row = result()
        ack = MagicMock()
        read = MagicMock()
        read.read.return_value = json.dumps([row]).encode()
        urlopen.side_effect = [ack, read]
        ack.__enter__.return_value = ack
        read.__enter__.return_value = read
        payload = {key: value for key, value in row.items() if key != 'completed_at'}
        self.assertTrue(save_listening_result('access', 'owner', payload))
        request = urlopen.call_args_list[0].args[0]
        self.assertIn('ignore-duplicates', request.get_header('Prefer'))
        self.assertEqual(json.loads(request.data), {'user_id': 'owner', **payload})
        self.assertEqual(request.get_header('Authorization'), 'Bearer access')
        query = urlopen.call_args_list[1].args[0].full_url
        self.assertIn('user_id=eq.owner', query)
        self.assertIn('attempt_id=eq.', query)
        self.assertIn('completed_at.desc', query)

    @patch('polskiflow.b2_listening_store.urlopen')
    def test_conflict_and_network_failure_never_report_success(self, urlopen):
        payload = {key: value for key, value in result().items() if key != 'completed_at'}
        with patch('polskiflow.b2_listening_store.load_listening_results', return_value=[{**payload, 'correct': 0}]):
            self.assertFalse(save_listening_result('access', 'owner', payload))
        urlopen.side_effect = URLError('offline')
        self.assertFalse(save_listening_result('access', 'owner', payload))
        self.assertIsNone(load_listening_results('access', 'owner'))


@override_settings(SUPABASE_URL='', SUPABASE_ANON_KEY='')
class B2ListeningRouteTests(TestCase):
    def setUp(self):
        auth = patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('owner', 'fixture@example.test'))
        auth.start()
        self.addCleanup(auth.stop)
        self.client.cookies[ACCESS_COOKIE] = 'fixture'

    def payload(self):
        page = self.client.get('/listening/')
        return {'b2_attempt': page.context['b2_state'], 'active_section': 'b2-listening',
                **{q['id']: q['answer'] for q in LISTENING_B2['questions']}}

    @patch('polskiflow.auth_views.save_listening_result', return_value=True)
    @patch('polskiflow.auth_views.load_listening_results')
    def test_save_redirect_refresh_and_foreign_result_is_not_exposed(self, load, save):
        response = self.client.post('/listening/', self.payload())
        self.assertEqual(response.status_code, 302)
        payload = save.call_args.args[2]
        load.return_value = [{**payload, 'completed_at': '2026-10-21T08:00:00+00:00'}]
        for _ in range(2):
            page = self.client.get(response.url)
            self.assertTrue(page.context['b2_saved'])
            self.assertEqual(page.context['b2_score'], 3)
            self.assertEqual(page['Cache-Control'], 'private, no-store')
        self.assertEqual(save.call_count, 1)
        load.return_value = []
        self.assertTrue(self.client.get(response.url).context['b2_error'])
        self.assertEqual(load.call_args.args[1], 'owner')

    @patch('polskiflow.auth_views.save_listening_result', return_value=False)
    def test_failed_save_keeps_same_retry_identity_and_selected_answers(self, save):
        payload = self.payload()
        for _ in range(2):
            page = self.client.post('/listening/', payload)
            self.assertTrue(page.context['b2_error'])
            self.assertEqual(page.context['b2_state'], payload['b2_attempt'])
            self.assertEqual(page.context['b2_score'], 3)
            self.assertFalse(page.context['b2_saved'])
            self.assertIsNone(page.context['b2_followup'])
        self.assertEqual(save.call_args_list[0].args[2], save.call_args_list[1].args[2])

    @patch('polskiflow.auth_views.save_listening_result')
    def test_foreign_signed_state_and_incomplete_answers_are_rejected(self, save):
        payload = self.payload()
        payload['b2_attempt'] = attempt_state('another-owner')
        self.assertEqual(self.client.post('/listening/', payload).status_code, 400)
        payload = self.payload()
        del payload['b2_listening_model']
        self.assertEqual(self.client.post('/listening/', payload).status_code, 400)
        save.assert_not_called()

    @patch('polskiflow.auth_views.load_listening_results')
    @patch('polskiflow.auth_views.load_dashboard_progress')
    @patch('polskiflow.auth_views.excluded_practice_topics', return_value=())
    def test_practice_recommendation_due_and_new_success_replaces_old_failure(self, excluded, dashboard, load):
        from polskiflow.progress_store import DashboardProgress
        dashboard.return_value = DashboardProgress('QA', 'B2', 0, frozenset(), True)
        load.return_value = [result(4)]
        with patch('polskiflow.domain.b2_listening_followup.timezone.localdate', return_value=date(2026, 10, 21)):
            page = self.client.get('/practice/')
            self.assertEqual(page.context['recommendation']['href'], '/lesson/b2prof-grammar/')
        with patch('polskiflow.domain.b2_listening_followup.timezone.localdate', return_value=date(2026, 10, 22)):
            page = self.client.get('/practice/')
            self.assertEqual(page.context['recommendation']['href'], '/listening/#b2-listening')
            load.return_value = [result(0), result(4)]
            page = self.client.get('/practice/')
            self.assertNotEqual(page.context['recommendation']['title'], 'Повторить аудирование B2')
        excluded.return_value = ('remote-work',)
        load.reset_mock()
        self.client.get('/practice/')
        load.assert_not_called()
