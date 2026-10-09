from unittest.mock import patch
from django.test import SimpleTestCase, TestCase
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.daily_plan import daily_plan_progress
from polskiflow.progress_store import DashboardProgress


class DurationProgressTests(SimpleTestCase):
    def test_different_lengths_have_different_weight_and_same_task_count(self):
        plan = [{'minutes':2,'completed':True},{'minutes':8,'completed':False}]
        self.assertEqual(daily_plan_progress(plan), dict(estimated_minutes=10, completed_estimated_minutes=2, completed_count=1, progress_percent=20))
        self.assertEqual(daily_plan_progress([{'minutes':2,'completed':False},{'minutes':8,'completed':True}])['progress_percent'], 80)

    def test_empty_and_fully_completed_plans(self):
        self.assertEqual(daily_plan_progress([])['progress_percent'], 0)
        self.assertEqual(daily_plan_progress([{'minutes':3,'completed':True},{'minutes':7,'completed':True}])['progress_percent'], 100)

    def test_invalid_durations_use_same_five_minute_fallback_as_selection(self):
        for minutes in (None, 0, -1, True, '8', 2.5):
            self.assertEqual(daily_plan_progress([{'minutes':minutes,'completed':True}])['completed_estimated_minutes'], 5)


class HomeDurationProgressTests(TestCase):
    def test_home_separates_weighted_plan_minutes_from_profile_goal(self):
        self.client.cookies[ACCESS_COOKIE] = 'fixture'
        rows = [{'id':'short','kind':'words','level':'A1','title':'Short','minutes':2}, {'id':'long','kind':'words','level':'A1','title':'Long','minutes':8}]
        dashboard = DashboardProgress('Learner','A1',0,frozenset({'short'}),True,all_completed_lesson_ids=frozenset({'short'}),daily_goal_minutes=15)
        with patch('polskiflow.auth.authenticate_access_token',return_value=SupabaseUser('learner','learner@example.test')), patch('polskiflow.auth_views.tasks',return_value=rows), patch('polskiflow.auth_views.load_dashboard_progress',return_value=dashboard), patch('polskiflow.auth_views.load_personal_words',return_value=[]):
            page = self.client.get('/')
        self.assertEqual(page.context['progress_percent'],20)
        self.assertEqual(page.context['completed_count'],1)
        self.assertEqual(page.context['completed_estimated_minutes'],2)
        self.assertEqual(page.context['plan_estimated_minutes'],10)
        self.assertEqual(page.context['plan_minutes'],15)
        self.assertContains(page,'aria-valuenow="20"')
        self.assertContains(page,'не время по таймеру')
        self.assertContains(page,'class="task-complete">✓')
