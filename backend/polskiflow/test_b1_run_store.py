import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase, override_settings
from polskiflow.b1_run_store import aggregate_results, save_b1_run_attempt, load_b1_run_attempts
from polskiflow.privacy_export_store import DATASETS


def results():
    return [{"id": part, "status": "scored", "correct": 1, "incorrect": 1, "unanswered": 3, "total": 5, "timed_out": True} for part in ('listening','reading','grammar')] + [{"id": part, "status": "self_review", "timed_out": False} for part in ('writing','speaking')]


@override_settings(SUPABASE_URL='https://example.supabase.co', SUPABASE_ANON_KEY='anon')
class B1RunStoreTests(SimpleTestCase):
    def state(self):
        return dict(user_id='owner', run_id='11111111-1111-4111-8111-111111111111', variant_id='b1-weekly-v1', content_version=9, created_at=1000, started_at=1010, finished_at=1100, phase='report', results=results(), review_answers={'grammar': {'tw31':'private response'}}, writing='private essay', audio='private audio')

    @patch('polskiflow.b1_run_store.urlopen')
    def test_idempotent_save_only_has_aggregates_and_fixed_completion_date(self, opened):
        response = MagicMock(status=201)
        response.__enter__.return_value = response
        opened.return_value = response
        state = self.state()
        state['results'][0]['details'] = ['private answer']
        self.assertTrue(save_b1_run_attempt('token','owner',state))
        self.assertTrue(save_b1_run_attempt('token','owner',state))
        first, second = [call.args[0] for call in opened.call_args_list]
        self.assertEqual(first.data, second.data)
        self.assertIn('on_conflict=user_id%2Crun_id', first.full_url)
        self.assertIn('ignore-duplicates', first.get_header('Prefer'))
        payload = json.loads(first.data)
        self.assertEqual(set(payload), {'user_id','run_id','variant_id','content_version','started_at','finished_at','results'})
        self.assertNotIn('private', first.data.decode())
        self.assertEqual(payload['results'][0]['unanswered'], 3)
        self.assertEqual(payload['results'][3], {'id':'writing','status':'self_review','timed_out':False})

    @patch('polskiflow.b1_run_store.urlopen')
    def test_incomplete_foreign_and_legacy_without_end_date_never_save(self, opened):
        state = self.state()
        self.assertFalse(save_b1_run_attempt('token','other',state))
        self.assertFalse(save_b1_run_attempt('token','owner',dict(state,phase='break')))
        del state['finished_at']
        self.assertFalse(save_b1_run_attempt('token','owner',state))
        opened.assert_not_called()

    def test_aggregate_validation_preserves_unknown_legacy_timing(self):
        rows = results()
        del rows[0]['timed_out']
        self.assertIsNone(aggregate_results(rows)[0]['timed_out'])
        for invalid in (rows[:4], list(reversed(rows)), [dict(rows[0],correct=9),*rows[1:]], [dict(rows[0],correct=True),*rows[1:]]):
            with self.assertRaises(ValueError): aggregate_results(invalid)

    @patch('polskiflow.b1_run_store.urlopen', side_effect=TimeoutError)
    def test_unavailable_does_not_claim_success(self, opened):
        self.assertFalse(save_b1_run_attempt('token','owner',self.state()))
        self.assertIsNone(load_b1_run_attempts('token','owner'))

    @patch('polskiflow.b1_run_store.urlopen')
    def test_history_is_owner_filtered_bounded_localized_and_period_filtered(self, opened):
        row = dict(run_id='run',variant_id='b1-weekly-v2',content_version=9,finished_at='2026-10-09T07:00:00Z',results=results())
        response=MagicMock()
        response.__enter__.return_value=BytesIO(json.dumps([row,{'results':[]}]).encode())
        opened.return_value=response
        history=load_b1_run_attempts('token','owner',days=7)
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]['date_display'],'09.10.2026 09:00')
        self.assertEqual(len(history[0]['parts']),5)
        self.assertIn('user_id=eq.owner',opened.call_args.args[0].full_url)
        self.assertIn('limit=12',opened.call_args.args[0].full_url)
        self.assertIn('finished_at=gte.',opened.call_args.args[0].full_url)
        self.assertIn('b1_run_attempts',DATASETS)
