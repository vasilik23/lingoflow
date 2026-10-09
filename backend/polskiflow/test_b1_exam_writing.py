from unittest.mock import patch
from django.test import TestCase, SimpleTestCase
from django.core import signing
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.ai_writing import SALT
from polskiflow.b1_writing_views import SETS


class WritingSetsTests(SimpleTestCase):
    def test_original_sets_have_two_tasks_and_published_volume_pairs(self):
        self.assertEqual([tuple(task['words'] for task in item['tasks']) for item in SETS], [(50, 150), (25, 175), (50, 150)])
        self.assertEqual(len({task['id'] for item in SETS for task in item['tasks']}), 6)
        self.assertTrue(all(task['prompt'] and task['genre'] for item in SETS for task in item['tasks']))


class ExamWritingViewTests(TestCase):
    def setUp(self):
        self.auth = patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('writer', 'writer@example.test'))
        self.auth.start()
        self.addCleanup(self.auth.stop)
        self.client.cookies[ACCESS_COOKIE] = 'fixture'

    def test_selected_set_has_two_editors_and_owner_bound_ai_assignments(self):
        for item in SETS:
            page = self.client.get('/writing/exam/b1/', {'set': item['id']})
            self.assertEqual(page.status_code, 200)
            self.assertEqual(page['Cache-Control'], 'private, no-store')
            self.assertEqual(page.context['selected_set']['id'], item['id'])
            self.assertContains(page, 'data-exam-draft', count=2)
            self.assertContains(page, '75:00')
            for task in page.context['exam_tasks']:
                token = signing.loads(task['ai_token'], salt=SALT)
                self.assertEqual(token['owner'], 'writer')
                self.assertEqual(token['assignment']['target_words'], task['words'])
                self.assertNotIn('minimum_words', token['assignment'])

    def test_unknown_set_falls_back_without_affecting_practice(self):
        page = self.client.get('/writing/exam/b1/?set=unknown')
        self.assertEqual(page.context['selected_set']['id'], '1')
        self.assertContains(page, 'href="/writing/?level=B1"')
        self.assertContains(self.client.get('/writing/?level=B1'), 'data-writing-draft')

    def test_guest_and_post_are_rejected(self):
        self.assertEqual(self.client.post('/writing/exam/b1/', {}).status_code, 405)
        self.client.cookies.clear()
        page = self.client.get('/writing/exam/b1/?set=2')
        self.assertEqual(page.status_code, 302)
        self.assertIn('/login/', page['Location'])
