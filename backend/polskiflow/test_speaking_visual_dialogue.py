from pathlib import Path
from unittest.mock import patch
import time
from django.conf import settings
from django.core import signing
from django.test import SimpleTestCase, TestCase
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.b1_run_views import RUN_SALT
from polskiflow.domain.b1_training_speaking import training_speaking_tasks
from polskiflow.domain.b1_weekly_mock import get_mock_variant
from polskiflow.domain.b1_run_review import run_review
from polskiflow.domain.b1_exam_simulation import B1_SIMULATION_PARTS


class SpeakingMaterialTests(SimpleTestCase):
    def test_new_tasks_have_local_picture_and_three_ordered_replies(self):
        for variant_id in ('b1-weekly-v1', 'b1-weekly-v2', 'b1-weekly-v3'):
            tasks = training_speaking_tasks(get_mock_variant(variant_id), 9, interactive=True)
            self.assertEqual([task.id for task in tasks], ['personal', 'situation', 'dialogue'])
            self.assertTrue((Path(settings.BASE_DIR) / 'polskiflow/learning/static' / tasks[1].image).is_file())
            self.assertTrue(tasks[1].image_alt and tasks[1].image_description)
            self.assertEqual(len(tasks[2].dialogue_turns), 3)
            self.assertNotIn(tasks[2].dialogue_turns[1], tasks[2].prompt)

    def test_legacy_runs_keep_textual_situation_and_printed_dialogue(self):
        variant = get_mock_variant('b1-weekly-v1')
        old = training_speaking_tasks(variant, 9)
        self.assertFalse(old[1].image)
        self.assertFalse(old[2].dialogue_turns)
        self.assertIn('wydrukowane', old[2].prompt)
        self.assertEqual(len(training_speaking_tasks(variant, 4, interactive=True)), 1)
        for speaking_version, expected in ((None, False), (2, True)):
            state = dict(content_version=9, speaking_version=speaking_version, results=[{'id':'speaking','status':'self_review'}])
            review = run_review(state, variant, B1_SIMULATION_PARTS[4])
            self.assertEqual(bool(review['tasks'][1].image), expected)


class SpeakingViewsTests(TestCase):
    def setUp(self):
        auth = patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('speaker', 'speaker@example.test'))
        auth.start(); self.addCleanup(auth.stop)
        self.client.cookies[ACCESS_COOKIE] = 'fixture'

    def test_practice_exposes_picture_and_hides_future_dialogue_turns(self):
        page = self.client.get('/interaction/')
        self.assertContains(page, '/static/polskiflow/speaking-neighbourhood-v1.png')
        self.assertContains(page, 'data-dialogue-turn hidden', count=2)
        self.assertContains(page, 'data-speaking-dialogue', count=1)
        self.assertContains(page, 'Микрофон необязателен')
        self.assertNotContains(page, 'name="dialogue')

    def test_signed_new_run_preserves_speaking_version_and_legacy_resume(self):
        intro = self.client.get('/exam/b1/run/')
        self.assertEqual(intro.context['state']['speaking_version'], 2)
        for legacy in (False, True):
            state = {**intro.context['state'], 'phase':'part', 'step':4, 'deadline':int(time.time())+660}
            if legacy: state.pop('speaking_version')
            token = signing.dumps(state, salt=RUN_SALT, compress=True)
            page = self.client.post('/exam/b1/run/', {'run_token':token,'action':'resume'})
            self.assertEqual(page.status_code, 200)
            if legacy: self.assertNotContains(page, 'data-speaking-dialogue')
            else:
                self.assertContains(page, 'data-dialogue-turn hidden', count=2)
                self.assertContains(page, '/static/polskiflow/speaking-neighbourhood-v1.png')
