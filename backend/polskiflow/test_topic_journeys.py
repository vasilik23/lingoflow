from datetime import date
import re
from unittest.mock import patch

from django.test import TestCase, override_settings, RequestFactory
from django.utils.translation import override

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.content import grammar, quiz, reading_text, tasks
from polskiflow.domain.topic_journeys import PILOTS, journey, next_target
from polskiflow.domain.daily_plan import build_daily_plan
from polskiflow.lesson_views import _complete
from polskiflow.progress_store import DashboardProgress, CompletionSaveResult


@override_settings(SUPABASE_URL='', SUPABASE_ANON_KEY='')
class TopicJourneyTests(TestCase):
    def setUp(self):
        self.user = SupabaseUser('pilot-owner', 'pilot@example.test')
        self.auth = patch('polskiflow.auth.authenticate_access_token', return_value=self.user)
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.client.cookies[ACCESS_COOKIE] = 'fixture'

    def dashboard(self, completed=(), results=(), available=True):
        return DashboardProgress(display_name='Pilot', level='A1', streak_days=0,
                                 completed_lesson_ids=frozenset(), available=available,
                                 all_completed_lesson_ids=frozenset(completed), recent_completion_results=results)

    def test_three_pilots_reuse_active_reading_checks_and_explained_exercises(self):
        for topic_id, pilot in PILOTS.items():
            reading = reading_text(pilot['reading_id'])
            self.assertEqual(reading.topic_id, topic_id)
            self.assertEqual(reading.source_metadata['comprehension_lesson_id'], pilot['lessons'][3])
            for lang in ('ru', 'pl', 'en'):
                localized = journey(topic_id, lang)
                self.assertTrue(localized['goal'])
                self.assertEqual(len(localized['checks']), 3)
            for question in [*grammar(pilot['lessons'][1])['questions'], *quiz(pilot['lessons'][4])]:
                self.assertTrue(question['explanation'])
                self.assertEqual(len(set(question['options'])), len(question['options']))
                self.assertIn(question['correct'], range(len(question['options'])))
        # Check the current migrated content, not the stale original seed.
        self.assertNotIn('przepracowała', grammar('bio-grammar')['questions'][0]['options'])

    def test_one_next_step_uses_only_saved_owner_results_and_never_awards_self_response(self):
        for topic_id, pilot in PILOTS.items():
            for count in range(6):
                completed = pilot['lessons'][:count]
                with patch('polskiflow.topic_journey_views.load_dashboard_progress', return_value=self.dashboard(completed)) as load:
                    response = self.client.get(f'/course/topic/{topic_id}/')
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-journey-next', count=1)
                self.assertContains(response, 'href="/learn/" class="nav-link active" aria-current="true"')
                self.assertEqual(sum(s['completed'] for s in response.context['steps']), min(count, 5))
                if count < 5:
                    self.assertEqual(response.context['next_action']['id'], pilot['lessons'][count])
                else:
                    self.assertContains(response, 'data-journey-next href="#own-answer"')
                self.assertEqual(len(load.call_args.args), 3)
                self.assertEqual(load.call_args.args[:2], ('fixture', self.user.id))
                self.assertEqual(self.client.post(f'/course/topic/{topic_id}/', {'answer':'private'}).status_code, 405)

    def test_weak_result_keeps_repeat_before_other_steps_and_new_success_cancels_it(self):
        today = date.today().isoformat()
        pilot = PILOTS['housing-services']
        weak = dict(lesson_id='housing-grammar', cards_known=1, cards_total=5, plan_date=today)
        for rows, expected in (((weak,), 'housing-grammar'), ((weak, {**weak,'cards_known':5}), 'housing-review')):
            with patch('polskiflow.topic_journey_views.load_dashboard_progress', return_value=self.dashboard(pilot['lessons'][:2], rows)):
                response = self.client.get('/course/topic/housing-services/')
            self.assertEqual(response.context['next_action']['id'], expected)

    def test_unavailable_progress_does_not_claim_any_completed_steps_and_unknown_pilot_is_404(self):
        with patch('polskiflow.topic_journey_views.load_dashboard_progress', return_value=self.dashboard(PILOTS['introductions']['lessons'], available=False)):
            response = self.client.get('/course/topic/introductions/')
        self.assertFalse(any(step['completed'] for step in response.context['steps']))
        self.assertContains(response, 'Прогресс временно недоступен')
        self.assertEqual(self.client.get('/course/topic/not-a-topic/').status_code, 404)

    @patch('polskiflow.lesson_views.load_mistakes', return_value=[])
    @patch('polskiflow.lesson_views.delete_lesson_draft')
    @patch('polskiflow.lesson_views.save_lesson_completion_result', return_value=CompletionSaveResult(True, False))
    def test_success_follows_scenario_and_weak_result_preserves_recheck(self, save, delete, mistakes):
        request = RequestFactory().post('/lesson/quiz/step/')
        request.supabase_user = self.user
        request.supabase_access_token = 'fixture'
        for topic_id, pilot in PILOTS.items():
            for lesson_id in pilot['lessons'][2:]:
                strong = _complete(request, lesson_id, 5, 5)
                self.assertContains(strong, next_target(topic_id, lesson_id)['href'])
                self.assertContains(strong, 'class="complete-next"', count=1)
                weak = _complete(request, lesson_id, 1, 5)
                self.assertContains(weak, 'Следующий шаг: закрепить')
                weak_target = re.search(r'class="complete-next" href="([^"]+)"', weak.content.decode()).group(1)
                self.assertEqual(weak_target, f'/lesson/{lesson_id}/')
            lesson_id = pilot['lessons'][4]
            failure = dict(lesson_id=lesson_id, cards_known=1, cards_total=5, plan_date='2026-10-13')
            plan = build_daily_plan(tasks(), level=pilot['level'], completed_all_time=frozenset(pilot['lessons']),
                                   completed_today=frozenset(), personal_words=[], today=date(2026,10,14),
                                   daily_task_limit=1, recent_completion_results=(failure,))
            self.assertEqual(plan[0]['id'], lesson_id)
            self.assertEqual(plan[0]['plan_type'], 'reinforcement')
            passed = {**failure, 'cards_known':5, 'plan_date':'2026-10-14'}
            plan = build_daily_plan(tasks(), level=pilot['level'], completed_all_time=frozenset(pilot['lessons']),
                                   completed_today=frozenset(), personal_words=[], today=date(2026,10,14),
                                   daily_task_limit=1, recent_completion_results=(failure,passed))
            self.assertFalse(any(s.get('plan_type')=='reinforcement' and s['id']==lesson_id for s in plan))

    def test_goals_and_self_response_are_localized(self):
        for language in ('ru','pl','en'):
            self.client.cookies['django_language'] = language
            with override(language), patch('polskiflow.topic_journey_views.load_dashboard_progress', return_value=self.dashboard()):
                response = self.client.get('/course/topic/introductions/')
                self.assertContains(response, journey('introductions', language)['goal'])
                self.assertContains(response, 'lang="pl" rows="5"')
