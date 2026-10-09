from unittest.mock import patch
from django.test import TestCase
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.progress_store import DashboardProgress


class TodayStartTaskTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = 'fixture'
        auth = patch('polskiflow.auth.authenticate_access_token',return_value=SupabaseUser('learner','learner@example.test'))
        auth.start(); self.addCleanup(auth.stop)

    def page(self, tasks, available=True):
        dashboard = DashboardProgress('Learner','A1',0,frozenset(),available)
        with patch('polskiflow.auth_views._daily_plan',return_value=(dashboard,tasks,sum(task['completed'] for task in tasks),0,15)), patch('polskiflow.auth_views.tasks',return_value=[]):
            return self.client.get('/')

    def task(self, id, completed=False, kind='words'):
        return dict(id=id,completed=completed,kind=kind,title=id,minutes=5,description='',emoji='')

    def test_start_skips_completed_lesson_and_links_directly_to_next(self):
        page = self.page([self.task('done',True),self.task('next'),self.task('later')])
        self.assertEqual(page.context['daily_start_task']['id'],'next')
        self.assertContains(page,'class="compact-button daily-action" href="/lesson/next/"')
        self.assertContains(page,'Продолжить занятия')
        self.assertContains(page,'class="daily-plan-link" href="#daily-tasks"')
        self.assertNotContains(page,'class="compact-button daily-action" href="#daily-tasks"')

    def test_dictionary_recommendation_uses_its_actual_practice_route(self):
        page = self.page([self.task('dictionary-practice',kind='dictionary-review')])
        self.assertContains(page,'class="compact-button daily-action" href="/dictionary/practice/"')
        self.assertContains(page,'Начать занятия')

    def test_completed_plan_offers_explicit_repeat_and_empty_plan_course(self):
        completed = self.page([self.task('done',True)])
        self.assertContains(completed,'Повторить задание')
        self.assertContains(completed,'class="compact-button daily-action" href="/lesson/done/"')
        empty = self.page([])
        self.assertIsNone(empty.context['daily_start_task'])
        self.assertContains(empty,'class="compact-button daily-action" href="/course/"')
        self.assertNotContains(empty,'Повторить задание')

    def test_unavailable_progress_still_allows_start_without_claiming_completion(self):
        page = self.page([self.task('first')],available=False)
        self.assertContains(page,'Прогресс временно недоступен')
        self.assertContains(page,'class="compact-button daily-action" href="/lesson/first/"')
