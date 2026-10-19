"""Actual B2 course route; persistence is mocked, not live-user acceptance."""
from datetime import date, timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.content import quiz, tasks
from polskiflow.domain.daily_plan import build_daily_plan
from polskiflow.progress_store import CompletionSaveResult, DashboardProgress


@override_settings(SUPABASE_URL='', SUPABASE_ANON_KEY='')
class B2AuditJourneyTests(TestCase):
    def test_goal_error_review_saved_result_and_next_day_recheck(self):
        owner = SupabaseUser('b2-audit-owner', 'fixture@example.test')
        progress = DashboardProgress('Learner', 'B2', 0, frozenset(), True)
        self.client.cookies[ACCESS_COOKIE] = 'fixture'
        with patch('polskiflow.auth.authenticate_access_token', return_value=owner), \
             patch('polskiflow.auth_views.load_dashboard_progress', return_value=progress), \
             patch('polskiflow.auth_views.save_profile_settings', return_value=True) as profile, \
             patch('polskiflow.lesson_views.load_lesson_draft', return_value=None), \
             patch('polskiflow.lesson_views.save_lesson_draft'), \
             patch('polskiflow.lesson_views.set_mistake') as mistake, \
             patch('polskiflow.lesson_views.load_mistakes', return_value=[]), \
             patch('polskiflow.lesson_views.delete_lesson_draft'), \
             patch('polskiflow.lesson_views.save_lesson_completion_result', return_value=CompletionSaveResult(True, False)) as save:
            goal = self.client.post('/welcome/', {'display_name': 'Learner', 'level': 'B2', 'daily_goal_minutes': '15'})
            self.assertEqual(goal.status_code, 302)
            self.assertEqual(profile.call_args.args[:4], ('fixture', owner.id, 'Learner', 'B2'))
            lesson_id = next(t['id'] for t in tasks() if t['level'] == 'B2' and t['kind'] == 'quiz')
            questions = quiz(lesson_id)
            page = self.client.get(f'/lesson/{lesson_id}/')
            self.assertEqual(page.status_code, 200)
            for question in questions:
                choice = (question['correct'] + 1) % len(question['options'])
                answer = self.client.post(f'/lesson/{lesson_id}/step/', {
                    'action': 'answer', 'state': page.context['lesson_state'], 'choice': choice,
                })
                self.assertEqual(answer.status_code, 200)
                self.assertContains(answer, question['explanation'])
                page = self.client.post(f'/lesson/{lesson_id}/step/', {
                    'action': 'next', 'state': answer.context['lesson_state'], 'selected': choice,
                })
                self.assertEqual(page.status_code, 200)
            self.assertTrue(mistake.called)
            save.assert_called_once_with('fixture', owner.id, lesson_id, len(questions), 0)
            self.assertContains(page, 'data-followup-saved')
            self.assertContains(page, f'href="/lesson/{lesson_id}/"')
            today = date.today()
            result = dict(lesson_id=lesson_id, cards_known=0, cards_total=len(questions), plan_date=today.isoformat())
            plan = build_daily_plan(tasks(), level='B2', completed_all_time=frozenset({lesson_id}),
                                    completed_today=frozenset(), personal_words=[], today=today + timedelta(days=1),
                                    daily_task_limit=1, recent_completion_results=(result,))
            self.assertEqual(plan[0]['id'], lesson_id)
            self.assertEqual(plan[0]['plan_type'], 'reinforcement')
            self.assertEqual(plan[0]['reinforcement_reason']['due_date'], (today + timedelta(days=1)).isoformat())
            # Open the assigned lesson again and finish with correct answers.
            page = self.client.get(f"/lesson/{plan[0]['id']}/")
            for question in questions:
                answer = self.client.post(f'/lesson/{lesson_id}/step/', {
                    'action': 'answer', 'state': page.context['lesson_state'], 'choice': question['correct'],
                })
                page = self.client.post(f'/lesson/{lesson_id}/step/', {
                    'action': 'next', 'state': answer.context['lesson_state'], 'selected': question['correct'],
                })
                self.assertEqual(page.status_code, 200)
            self.assertEqual(save.call_count, 2)
            success = {**result, 'cards_known': len(questions), 'plan_date': (today + timedelta(days=1)).isoformat()}
            plan = build_daily_plan(tasks(), level='B2', completed_all_time=frozenset({lesson_id}),
                                    completed_today=frozenset(), personal_words=[], today=today + timedelta(days=2),
                                    daily_task_limit=1, recent_completion_results=(result, success))
            self.assertFalse(any(t.get('plan_type') == 'reinforcement' for t in plan))
