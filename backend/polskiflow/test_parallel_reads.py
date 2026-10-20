from functools import partial
from threading import Barrier
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.lesson_note_store import LessonNote
from polskiflow.parallel_reads import parallel_reads
from polskiflow.progress_store import DashboardProgress


class ParallelReadTests(SimpleTestCase):
    def test_reads_overlap_and_results_keep_input_order(self):
        ready = Barrier(3)
        def read(value):
            ready.wait(timeout=2)
            return value
        self.assertEqual(parallel_reads(*(partial(read, value) for value in ('a', None, 'c'))), ('a', None, 'c'))

    def test_request_batches_do_not_cache_or_reuse_owner_data(self):
        for owner in ('owner-A', 'owner-B'):
            self.assertEqual(parallel_reads(partial(str, owner)), (owner,))
        self.assertEqual(parallel_reads(), ())


class PageReadConcurrencyTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = 'fixture-access'
        auth = patch('polskiflow.auth.authenticate_access_token', return_value=SupabaseUser('fixture-owner', 'qa@example.test'))
        auth.start(); self.addCleanup(auth.stop)

    def test_lesson_tools_reads_overlap_and_keep_owner_and_failure_states(self):
        ready = Barrier(3)
        def read(value, token, owner, *extra):
            self.assertEqual((token, owner), ('fixture-access', 'fixture-owner'))
            ready.wait(timeout=2)
            return value
        with patch('polskiflow.lesson_views.load_lesson_bookmarks', side_effect=partial(read, None)), \
             patch('polskiflow.lesson_views.load_lesson_note', side_effect=partial(read, LessonNote(False))), \
             patch('polskiflow.lesson_views.load_collection_summaries', side_effect=partial(read, None)):
            response = self.client.get('/lesson/grammar/')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['collections_available'])
        self.assertFalse(response.context['lesson_bookmarks_available'])
        self.assertFalse(response.context['lesson_note'].available)

    def test_today_reads_overlap_and_catalog_is_queried_once(self):
        from polskiflow.content import tasks
        ready = Barrier(2)
        dashboard = DashboardProgress('QA', 'B1', 0, frozenset(), True)
        def read(value, token, owner, *extra):
            self.assertEqual((token, owner), ('fixture-access', 'fixture-owner'))
            ready.wait(timeout=2)
            return value
        with patch('polskiflow.auth_views.load_dashboard_progress', side_effect=partial(read, dashboard)), \
             patch('polskiflow.auth_views.load_personal_words', side_effect=partial(read, [])), \
             patch('polskiflow.auth_views.tasks', wraps=tasks) as catalog:
            response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(catalog.call_count, 1)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
