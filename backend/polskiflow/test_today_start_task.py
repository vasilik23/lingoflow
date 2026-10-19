from unittest.mock import patch
from django.test import TestCase
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.progress_store import DashboardProgress


class TodayStartTaskTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = 'fixture'
        auth = patch('polskiflow.auth.authenticate_access_token',return_value=SupabaseUser('learner','learner@example.test'))
        auth.start(); self.addCleanup(auth.stop)

    def page(self, tasks, available=True, level='A1', catalog=None, draft=None):
        dashboard = DashboardProgress('Learner',level,0,frozenset(),available)
        with patch('polskiflow.auth_views._daily_plan',return_value=(dashboard,tasks,sum(task['completed'] for task in tasks),0,15)), patch('polskiflow.auth_views.tasks',return_value=catalog or []), patch('polskiflow.auth_views.load_latest_lesson_draft',return_value=draft):
            return self.client.get('/')

    def task(self, id, completed=False, kind='words'):
        return dict(id=id,completed=completed,kind=kind,title=id,minutes=5,description='',emoji='')

    def test_start_skips_completed_lesson_and_links_directly_to_next(self):
        page = self.page([self.task('done',True),self.task('next'),self.task('later')])
        self.assertEqual(page.context['daily_start_task']['id'],'next')
        self.assertContains(page,'class="compact-button daily-action" href="/lesson/next/"')
        self.assertContains(page,'Продолжить занятия')
        self.assertContains(page, '<section class="card daily-tasks-panel" id="daily-tasks">')
        self.assertNotContains(page, '<details class="card daily-tasks-panel"')
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

    def test_resume_replaces_daily_start_without_removing_plan(self):
        page = self.page([self.task('next')], catalog=[self.task('draft')],
                         draft={'lesson_id': 'draft', 'step_index': 2})
        self.assertContains(page, 'class="compact-button daily-action"', count=1)
        self.assertContains(page, 'class="compact-button daily-action" href="/lesson/draft/"')
        self.assertContains(page, 'Незавершённый урок')
        self.assertContains(page, 'href="/lesson/next/"')
        self.assertNotContains(page, 'class="card resume-card"')

    def test_b1_shows_exam_destination_without_second_daily_plan(self):
        page = self.page([self.task('next')], level='B1', available=False)
        self.assertContains(page, 'class="compact-button daily-action"', count=1)
        self.assertContains(page, 'href="/exam/b1/"')
        self.assertNotContains(page, 'exam-home-card')
        self.assertNotContains(page, 'минут по трём экзаменационным навыкам')
        self.assertContains(page, '<section class="card daily-tasks-panel" id="daily-tasks">')
