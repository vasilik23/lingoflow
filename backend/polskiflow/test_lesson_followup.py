from datetime import date
from unittest.mock import patch

from django.test import RequestFactory, TestCase, override_settings

from polskiflow.auth import SupabaseUser
from polskiflow.content import tasks
from polskiflow.domain.daily_plan import build_daily_plan
from polskiflow.domain.lesson_followup import lesson_followup, latest_completions
from polskiflow.lesson_views import _complete
from polskiflow.progress_store import CompletionSaveResult


class LessonFollowupTests(TestCase):
    def row(self, known=2, day='2026-10-08', lesson='quiz'):
        return dict(lesson_id=lesson, cards_known=known, cards_total=5, plan_date=day)

    def test_one_action_uses_actual_topic_and_duration_or_next_material(self):
        lesson = dict(id='grammar', title='Grammar', theory_title='Dopełniacz', minutes=6)
        next_lesson = dict(id='next', title='Reading', minutes=9)
        weak = lesson_followup(lesson, {'next_lesson': next_lesson}, 2, 5, date(2026, 10, 8))
        self.assertEqual((weak['lesson']['id'], weak['lesson']['title'], weak['lesson']['minutes']), ('grammar', 'Dopełniacz', 6))
        self.assertEqual(weak['due_date'], date(2026, 10, 9))
        strong = lesson_followup(lesson, {'next_lesson': next_lesson}, 7, 10, date(2026, 10, 8))
        self.assertEqual(strong['lesson']['id'], 'next')
        self.assertIsNone(strong['due_date'])

    def test_latest_success_cancels_older_failure_regardless_of_row_order(self):
        failed, passed = self.row(), self.row(4, '2026-10-09')
        for rows in ((failed, passed), (passed, failed)):
            latest = latest_completions(rows, date(2026, 10, 10))
            self.assertEqual(latest['quiz'], passed)
            plan = self.plan(rows)
            self.assertFalse(any(item.get('plan_type') == 'reinforcement' for item in plan))

    def plan(self, rows, **kwargs):
        lessons = [dict(id='quiz',kind='quiz',title='Quiz',minutes=9,level='A1'), dict(id='next',kind='grammar',title='Next',minutes=9,level='A1')]
        return build_daily_plan(lessons, level='A1', completed_all_time=frozenset({'quiz'}), completed_today=frozenset(), personal_words=[], today=date(2026,10,10), recent_completion_results=rows, **kwargs)

    def test_due_recheck_survives_goal_one_and_time_budget_and_keeps_original_date(self):
        for options in ({'daily_task_limit': 1}, {'time_budget_minutes': 10}):
            plan = self.plan((self.row(),), **options)
            self.assertEqual(len(plan), 1)
            self.assertEqual(plan[0]['id'], 'quiz')
            self.assertEqual(plan[0]['reinforcement_reason']['due_date'], '2026-10-09')

    def test_invalid_future_expired_or_boolean_rows_cannot_schedule_or_cancel(self):
        invalid = ({**self.row(), 'cards_known': True}, self.row(4,'2027-01-01'), self.row(4,'invalid'), self.row(4,'2026-08-01'))
        self.assertEqual(latest_completions(invalid, date(2026,10,10)), {})
        self.assertEqual(latest_completions((self.row(),*invalid),date(2026,10,10))['quiz'],self.row())

    @override_settings(SUPABASE_URL='', SUPABASE_ANON_KEY='')
    @patch('polskiflow.lesson_views.delete_lesson_draft')
    @patch('polskiflow.lesson_views.save_lesson_completion_result')
    def test_saved_owner_result_schedules_recheck_and_unsaved_result_does_not_claim_it(self, save, delete):
        request = RequestFactory().post('/lesson/quiz/step/')
        request.supabase_access_token = 'fixture'
        request.supabase_user = SupabaseUser('owner', 'owner@example.test')
        for saved in (True, False):
            save.return_value = CompletionSaveResult(saved, False)
            response = _complete(request, 'quiz', 2, 5)
            self.assertContains(response, 'Следующий шаг: закрепить')
            self.assertContains(response, 'class="complete-next"', count=1)
            self.assertNotContains(response, 'Продолжить тему →')
            self.assertContains(response, 'data-followup-saved' + ('' if saved else ' hidden'))
            self.assertContains(response, 'data-followup-pending' + (' hidden' if saved else ''))
            save.assert_called_with('fixture', 'owner', 'quiz', 5, 2)
        plan = build_daily_plan(tasks(),level='A1',completed_all_time=frozenset({'quiz'}),completed_today=frozenset(),personal_words=[],today=date(2026,10,10),daily_task_limit=1,recent_completion_results=(self.row(),))
        self.assertEqual(plan[0]['id'], 'quiz')

    def test_public_demo_result_recommends_one_full_material_and_preserves_guest_privacy(self):
        from polskiflow.public_demo_store import load_demo_lesson
        from urllib.parse import parse_qs,urlparse
        for correct in (True,False):
            lesson=load_demo_lesson('A2')
            question=lesson['question']
            exercise=self.client.get('/demo/?level=A2&step=exercise')
            answer=question['correct'] if correct else (question['correct']+1)%len(question['options'])
            checked=self.client.post('/demo/?level=A2',{'state':exercise.context['state'],'answer':str(answer)},follow=True)
            review=parse_qs(urlparse(checked.redirect_chain[-1][0]).query)['review'][0]
            result=self.client.get('/demo/',{'level':'A2','step':'result','review':review})
            self.assertContains(result,'class="complete-next"',count=1)
            self.assertContains(result,'Для полного урока и сохранения повторений нужен аккаунт.')
            self.assertEqual(result.context['next_material']['id'] == lesson['id'],not correct)

    def test_scheduled_review_keeps_completed_task_even_with_goal_one(self):
        lessons = [dict(id='done',kind='quiz',title='Done',minutes=5,level='A1'),dict(id='quiz',kind='quiz',title='Quiz',minutes=9,level='A1')]
        plan = build_daily_plan(lessons,level='A1',completed_all_time=frozenset({'done','quiz'}),completed_today=frozenset({'done'}),personal_words=[],today=date(2026,10,10),daily_task_limit=1,recent_completion_results=(self.row(),))
        self.assertEqual([item['id'] for item in plan],['done','quiz'])
        self.assertTrue(plan[0]['completed'])
        self.assertEqual(plan[1]['plan_type'],'reinforcement')

    def test_offline_confirmation_schedules_only_the_matching_result_after_htmx_swap(self):
        import subprocess
        from pathlib import Path
        result = subprocess.run(['node', str(Path(__file__).with_name('test_followup_sync.cjs'))],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    @override_settings(SUPABASE_URL='', SUPABASE_ANON_KEY='')
    @patch('polskiflow.lesson_views.load_mistakes')
    @patch('polskiflow.lesson_views.delete_lesson_draft')
    @patch('polskiflow.lesson_views.save_lesson_completion_result',return_value=CompletionSaveResult(True,False))
    def test_followup_explains_an_actual_owned_mistake_and_ignores_other_lessons(self, save, delete, mistakes):
        from polskiflow.content import quiz
        mistakes.return_value = [{'lesson_id':'other','question_position':0},{'lesson_id':'quiz','question_position':True},{'lesson_id':'quiz','question_position':0}]
        request=RequestFactory().post('/lesson/quiz/step/')
        request.supabase_access_token='fixture'
        request.supabase_user=SupabaseUser('owner','owner@example.test')
        response=_complete(request,'quiz',2,5)
        self.assertContains(response,'Что закрепить')
        self.assertContains(response,quiz('quiz')[0]['prompt'])
        self.assertContains(response,quiz('quiz')[0]['explanation'])
        mistakes.assert_called_once_with('fixture','owner')
