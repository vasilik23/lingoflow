import copy
from django.apps import apps
from django.test import TestCase, SimpleTestCase
from polskiflow.domain.content_workflow import (
    ManifestError, validate_manifest, validate_model_resolutions, build_executable_migration_preview,
)
from polskiflow.test_content_workflow import sample_manifest, sample_resolutions
from polskiflow.learning.models import Course, Topic, Lesson, Flashcard, LessonFlashcard, Question, ReadingText


def artifacts(manifest):
    result = validate_manifest(manifest)
    resolutions = sample_resolutions(result.checksum)
    resolutions['course_id'] = 'workflow-fixture-course'
    checked = validate_model_resolutions(result, resolutions, 'TEST-LOSSLESS', result.checksum)
    preview = build_executable_migration_preview(result, resolutions, 'TEST-LOSSLESS', result.checksum, checked['resolutions_checksum'])
    scope = {}
    exec(compile(preview['candidate-django-runpython.py'], '<migration-preview>', 'exec'), scope)
    return scope['forwards'], resolutions, preview


class LosslessPreviewValidationTests(SimpleTestCase):
    def test_rejects_malformed_extensions_and_inconsistent_legacy_glossary(self):
        original = sample_manifest(status='approved')
        for change in (
            lambda x: x['content']['grammar'].update(sections=[{'text': 'bad shape'}]),
            lambda x: x['content']['card_sets'][0][0].update(position=True),
            lambda x: x['content']['reading'].update(source_metadata={'origin': 'external'}),
            lambda x: x['content']['reading'].update(source_metadata={'origin': 'original', 'created_for': []}),
            lambda x: x['content']['reading'].update(source_glossary={'akapit': 'different meaning'}),
        ):
            candidate = copy.deepcopy(original)
            change(candidate)
            with self.assertRaises(ManifestError):
                validate_manifest(candidate)
        external = sample_manifest(status='approved', origin='external')
        external['content']['reading']['source_metadata'] = {'origin': 'original', 'created_for': 'LingoFlow', 'verified_at': '2026-11-09'}
        with self.assertRaises(ManifestError):
            validate_manifest(external)


class LosslessPreviewExecutionTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(id='workflow-fixture-course', title='Fixture', level='B1')
        self.topic = Topic.objects.create(id='test-editorial-topic', course=self.course, title='Fixture')
        self.manifest = sample_manifest(status='approved')
        self.manifest['review'] = {'language_reviewer': 'synthetic-test', 'license_reviewer': 'synthetic-test',
                                   'reviewed_at': '2026-11-09'}
        result = validate_manifest(self.manifest)
        self.resolutions = sample_resolutions(result.checksum)
        for lesson_id in {*self.resolutions['card_set_lesson_ids'], *self.resolutions['question_lesson_ids'].values()}:
            Lesson.objects.create(id=lesson_id, topic=self.topic, title=lesson_id)

    def test_existing_question_ids_metadata_and_legacy_values_survive_repeated_preview(self):
        content = self.manifest['content']
        metadata = {'origin': 'original', 'created_for': 'LingoFlow', 'verified_at': '2026-10-22', 'comprehension_lesson_id': 'example-grammar'}
        content['grammar']['sections'] = [['First heading', 'First explanation'], ['Second heading', 'Second explanation']]
        content['card_sets'][0][0].update(source_metadata=metadata, position=500)
        content['reading'].update(source_metadata=metadata, source_glossary={'akapit': 'абзац'})
        retained = Question.objects.create(lesson_id='example-grammar', position=0, prompt='Old prompt', options=['A', 'B'], correct=0)
        surplus = Question.objects.create(lesson_id='example-grammar', position=50, prompt='Old surplus', options=['A', 'B'], correct=0)
        forwards, resolutions, preview = artifacts(self.manifest)
        forwards(apps, None)
        retained.refresh_from_db(); surplus.refresh_from_db()
        self.assertEqual(retained.pk, Question.objects.get(lesson_id='example-grammar', position=0).pk)
        self.assertEqual(retained.prompt, content['exercises'][0]['prompt'])
        self.assertFalse(surplus.is_active)
        self.assertEqual(Lesson.objects.get(pk='example-grammar').theory_sections, content['grammar']['sections'])
        card = Flashcard.objects.get(pk=content['card_sets'][0][0]['id'])
        self.assertEqual(card.source_metadata, metadata)
        self.assertEqual(card.position, 500)
        reading = ReadingText.objects.get(pk=resolutions['reading']['id'])
        self.assertEqual(reading.source_metadata, metadata)
        self.assertEqual(reading.glossary, {'akapit': 'абзац'})
        questions = list(Question.objects.filter(lesson__topic=self.topic).order_by('id').values())
        links = list(LessonFlashcard.objects.filter(lesson__topic=self.topic).order_by('id').values())
        forwards(apps, None)
        self.assertEqual(questions, list(Question.objects.filter(lesson__topic=self.topic).order_by('id').values()))
        self.assertEqual(links, list(LessonFlashcard.objects.filter(lesson__topic=self.topic).order_by('id').values()))
        self.assertNotIn('delete from questions', preview['candidate-supabase-content.sql'])
        self.assertIn('on conflict (lesson_id, position)', preview['candidate-supabase-content.sql'])

    def test_summary_only_manifest_renders_the_actual_theory_pair_format(self):
        forwards, _, _ = artifacts(self.manifest)
        forwards(apps, None)
        self.assertEqual(Lesson.objects.get(pk='example-grammar').theory_sections,
                         [[self.resolutions['grammar_lesson']['theory_title'], self.manifest['content']['grammar']['summary']]])
