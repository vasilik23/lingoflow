import hashlib
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils.translation import override

from polskiflow.domain.topic_journeys import PILOTS
from polskiflow.learning.models import Lesson, Question
from polskiflow.learning.templatetags.ui import learning_text
from polskiflow.pilot_review import ReviewPacketError, build_packet, write_packet

SHA = 'a' * 40


class PilotReviewPacketTests(TestCase):
    def test_biography_english_glosses_retain_actions_and_complete_meaning(self):
        with override('en'):
            for source, expected in (
                ('переехать', 'move (to a new home)'), ('начать карьеру', 'start a career'),
                ('достичь цели', 'achieve a goal'), ('важное событие', 'important event'),
            ):
                self.assertEqual(learning_text(source), expected)

    def test_all_pilots_and_current_translations_export_without_learner_queries_or_writes(self):
        with CaptureQueriesContext(connection) as queries:
            artifacts = build_packet(SHA)
        snapshot = json.loads(artifacts['snapshot.json'])
        self.assertFalse(snapshot['release_authorized'])
        self.assertEqual(snapshot['review_status'], 'not_reviewed')
        self.assertEqual(len(snapshot['topics']), 3)
        self.assertEqual(sum(len(t['lessons']) for t in snapshot['topics']), 15)
        for topic in snapshot['topics']:
            self.assertEqual([lesson['id'] for lesson in topic['lessons']], list(PILOTS[topic['id']]['lessons']))
            self.assertTrue(topic['reading']['glossary'])
            for language in ('ru', 'pl', 'en'):
                self.assertIn(topic['journeys'][language]['goal'].encode(), artifacts[f'review-{language}.html'])
            for lesson in topic['lessons']:
                self.assertTrue(lesson['cards'] or lesson['questions'])
                for question in lesson['questions']:
                    self.assertTrue(question['ref'].startswith(lesson['id'] + ':q:'))
                    self.assertIn(question['correct'], range(len(question['options'])))
        for query in queries.captured_queries:
            sql = query['sql'].lower()
            self.assertFalse(sql.lstrip().startswith(('insert ', 'update ', 'delete ', 'create ', 'alter ', 'drop ')))
            self.assertFalse(any(table in sql for table in ('"profiles"', '"lesson_completions"', '"personal_words"', '"b1_run_attempts"')))
        self.assertIn(b'English translation', artifacts['review-en.html'])
        self.assertEqual(artifacts, build_packet(SHA))

    def test_content_change_changes_bound_snapshot_and_review_notes(self):
        before = build_packet(SHA)
        question = Question.objects.filter(lesson_id='housing-quiz').first()
        question.explanation += ' Additional editorial test context.'
        question.save(update_fields=['explanation'])
        after = build_packet(SHA)
        self.assertNotEqual(before['snapshot.json'], after['snapshot.json'])
        notes = json.loads(after['review-notes.json'])
        self.assertEqual(notes['snapshot_sha256'], hashlib.sha256(after['snapshot.json']).hexdigest())
        self.assertFalse(notes['release_authorized'])
        self.assertTrue(all(value is None for topic in notes['topics'] for value in topic['criteria'].values()))

    def test_answer_keys_and_metadata_are_html_escaped_without_remote_resources(self):
        question = Question.objects.filter(lesson_id='quiz').first()
        question.prompt = '<script>alert("fixture")</script>'
        question.save(update_fields=['prompt'])
        html = build_packet(SHA)['review-en.html'].decode()
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<script src=', html)
        self.assertNotIn('<link ', html)
        self.assertIn("default-src 'none'", html)

    def test_missing_content_invalid_answer_and_pending_migrations_fail_closed(self):
        for value in ('short', 'A' * 40, SHA + '\n'):
            with self.assertRaises(ReviewPacketError):
                build_packet(value)
        with patch('polskiflow.pilot_review.MigrationExecutor') as executor:
            executor.return_value.migration_plan.return_value = ['pending']
            with self.assertRaisesRegex(ReviewPacketError, 'pending migrations'):
                build_packet(SHA)
        Lesson.objects.filter(id='housing-words').update(is_active=False)
        with self.assertRaisesRegex(ReviewPacketError, 'housing-words'):
            build_packet(SHA)
        Lesson.objects.filter(id='housing-words').update(is_active=True)
        Question.objects.filter(lesson_id='quiz', position=0).update(correct=999)
        with self.assertRaisesRegex(ReviewPacketError, 'Invalid question'):
            build_packet(SHA)

    def test_private_new_external_directory_and_manifest_cover_every_file(self):
        artifacts = build_packet(SHA)
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'packet'
            write_packet(artifacts, destination)
            self.assertEqual(destination.stat().st_mode & 0o077, 0)
            manifest = json.loads((destination / 'manifest.json').read_bytes())
            self.assertEqual(set(manifest['files']), set(artifacts) - {'manifest.json'})
            for name, expected in manifest['files'].items():
                self.assertEqual(expected['sha256'], hashlib.sha256((destination / name).read_bytes()).hexdigest())
                self.assertEqual(expected['bytes'], len((destination / name).read_bytes()))
                self.assertEqual((destination / name).stat().st_mode & 0o077, 0)
            with self.assertRaises(ReviewPacketError):
                write_packet(artifacts, destination)
        with self.assertRaisesRegex(ReviewPacketError, 'outside'):
            write_packet(artifacts, Path(__file__).parent / 'review-packet')

    def test_command_exports_only_to_requested_external_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            output = io.StringIO()
            call_command('pilot_review_packet', source_commit=SHA,
                         output_directory=str(Path(temp) / 'packet'), stdout=output)
            self.assertIn('release_authorized=false', output.getvalue())
            with self.assertRaises(CommandError):
                call_command('pilot_review_packet', source_commit=SHA,
                             output_directory=str(Path(temp) / 'packet'), stdout=output)
            with patch('polskiflow.learning.management.commands.pilot_review_packet.build_packet',
                       side_effect=DatabaseError('private connection string')):
                with self.assertRaises(CommandError) as raised:
                    call_command('pilot_review_packet', source_commit=SHA,
                                 output_directory=str(Path(temp) / 'failed'), stdout=output)
                self.assertNotIn('private connection', str(raised.exception))
                self.assertFalse((Path(temp) / 'failed').exists())
