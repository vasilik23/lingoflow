"""Regression evidence for the 28 internal editorial findings, not approval."""
import importlib
import json
from pathlib import Path
from types import SimpleNamespace
from django.apps import apps
from django.db import connection
from django.test import TestCase
from django.utils.translation import override
from polskiflow.learning.models import Lesson, Question, ReadingText
from polskiflow.learning.templatetags.ui import learning_text, english_reading
from polskiflow.reading_views import _glossary_entries, _tokenize
from polskiflow.pilot_review import build_packet


class PilotEditorialCorrectionsTests(TestCase):
    def test_misleading_glosses_are_corrected(self):
        with override('en'):
            for source, expected in {'из Польши': 'from Poland', 'быть родом': 'come from / be originally from',
                'снимать; сдавать': 'rent / rent out', 'со временем': 'over time / as time went by',
                'приобрести опыт': 'gain experience', 'оказаться': 'turn out (to be)',
                'счётчик': 'meter', 'день': 'day', 'спрашивает': 'asks', 'знакомым': 'acquaintance / classmate'}.items():
                self.assertEqual(learning_text(source), expected)

    def test_aspect_questions_specify_the_target_and_explain_alternative(self):
        for pos, correct in ((1, 'ukończyła'), (2, 'ukończył')):
            q = Question.objects.get(lesson_id='bio-grammar', position=pos)
            self.assertIn('совершенного вида', q.prompt)
            self.assertEqual(q.options[q.correct], correct)
            self.assertIn('Kończy', q.explanation)
            for lang in ('pl', 'en'):
                with override(lang):
                    self.assertNotRegex(learning_text(q.prompt), '[А-Яа-яЁё]')
                    self.assertNotRegex(learning_text(q.explanation), '[А-Яа-яЁё]')

    def test_housing_request_and_appointment_are_taught_and_practised(self):
        lesson = Lesson.objects.get(pk='housing-grammar')
        theory = str(lesson.theory_sections)
        for fragment in ('Proszę o pomoc', 'we wtorek po szesnastej', 'Panu', 'Pani'):
            self.assertIn(fragment, theory)
        questions = list(lesson.questions.order_by('position'))
        self.assertEqual(len(questions), 7)
        self.assertIn('Proszę o pomoc', questions[5].options[questions[5].correct])
        self.assertIn('we wtorek po szesnastej', questions[6].options[questions[6].correct])
        self.assertIn('Pani odpowiada', questions[6].options[questions[6].correct])
        for lang in ('pl', 'en'):
            with override(lang):
                for q in questions[-2:]:
                    self.assertNotRegex(learning_text(q.prompt), '[А-Яа-яЁё]')
                    self.assertNotRegex(learning_text(q.explanation), '[А-Яа-яЁё]')

    def test_reading_meaning_and_complete_english_translation(self):
        housing = ReadingText.objects.get(pk='usterka-w-mieszkaniu')
        self.assertIn('kaloryfery są zimne', housing.paragraphs[0])
        self.assertNotIn('od wieczora', housing.paragraphs[0])
        self.assertEqual(Question.objects.get(lesson_id='housing-reading-check', position=4).prompt,
                         'Co Lena zrobi, jeśli fachowiec się spóźni?')
        with override('en'):
            translated = english_reading(housing.paragraphs)
            self.assertIn('photo of the meter', translated[1])
            self.assertIn('Lena will contact', translated[2])
            self.assertNotIn('tonight', translated[2])
            bio = ReadingText.objects.get(pk='bio-droga-joanny')
            translated = english_reading(bio.paragraphs)
            self.assertEqual(len(translated), 4)
            self.assertIn('The turning point was a project to design a library', translated[2])

    def test_glossary_lemmas_and_full_expressions_are_usable_in_reader(self):
        a1 = ReadingText.objects.get(pk='pierwszy-dzien-na-kursie')
        self.assertNotIn('mieszka', a1.glossary)
        self.assertEqual(a1.glossary['przedstawia']['lemma'], 'przedstawiać się')
        self.assertEqual(a1.glossary['kursie']['lemma'], 'kurs')
        self.assertIn('Перед чтением', str(Lesson.objects.get(pk='grammar').theory_sections))
        bio = ReadingText.objects.get(pk='bio-droga-joanny')
        entries = _glossary_entries(bio.glossary)
        for full in ('punktem zwrotnym', 'przyzwyczaić się', 'wpłynąć na'):
            self.assertIn(full, entries)
        paragraphs = _tokenize(bio.paragraphs, bio.glossary, bio.id)
        tokens = [token for paragraph in paragraphs for token in paragraph]
        for full in ('punktem zwrotnym', 'przyzwyczaić się', 'wpłynąć na'):
            self.assertTrue(any(t.get('word', '').casefold() == full for t in tokens), full)

    def test_revised_distractors_and_polish_support_do_not_copy_the_answer(self):
        for pos in (1, 3, 6, 8):
            q = Question.objects.get(lesson_id='bio-quiz', position=pos)
            self.assertEqual(len(q.options), len(set(q.options)))
            self.assertNotRegex(str(q.options), 'wspominała się|osiągał się|Na końcu wczoraj|lecz że')
        with override('pl'):
            self.assertEqual(learning_text('взрослеть'), 'stawać się dorosłym')
            self.assertNotIn('Jestem Anna', learning_text('Как сказать «Я Анна»?'))
            self.assertNotIn('założyła firmę', learning_text('Составьте: Сначала она работала в школе, а потом открыла фирму.'))

    def test_frozen_migration_is_idempotent_and_matches_sql_payload(self):
        migration = importlib.import_module('polskiflow.learning.migrations.0126_pilot_editorial_corrections')
        root = Path(__file__).resolve().parents[2]
        sql = next((root / 'supabase/migrations').glob('*_pilot_editorial_corrections.sql')).read_text()
        self.assertEqual(json.loads(sql.split('$payload$')[1]), migration.PATCH)
        before = list(Question.objects.filter(lesson_id__in=['housing-grammar', 'bio-grammar', 'bio-quiz']).values_list('id','lesson_id','position','prompt','options','correct'))
        editor = SimpleNamespace(connection=connection)
        migration.seed(apps, editor)
        migration.seed(apps, editor)
        self.assertEqual(before, list(Question.objects.filter(lesson_id__in=['housing-grammar', 'bio-grammar', 'bio-quiz']).values_list('id','lesson_id','position','prompt','options','correct')))

    def test_new_packet_is_bound_to_updated_content_without_acceptance(self):
        artifacts = build_packet('a' * 40)
        snapshot = json.loads(artifacts['snapshot.json'])
        self.assertEqual(sum(len(l['questions']) for t in snapshot['topics'] for l in t['lessons']), 58)
        self.assertFalse(snapshot['release_authorized'])
        self.assertEqual(snapshot['review_status'], 'not_reviewed')
        for lang in ('ru','pl','en'):
            self.assertIn('housing-grammar:q:6', artifacts[f'review-{lang}.html'].decode())
        self.assertIn('from Poland', artifacts['review-en.html'].decode())
        self.assertNotIn('timelessly', artifacts['review-en.html'].decode())
