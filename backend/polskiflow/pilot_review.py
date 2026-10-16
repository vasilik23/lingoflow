"""Read-only editorial snapshot of the three existing pilots, never an approval."""
import hashlib
import json
import os
import re
from pathlib import Path

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.template.loader import render_to_string
from django.utils.translation import override

from polskiflow.domain.topic_journeys import PILOTS, SOURCE_METADATA, journey
from polskiflow.learning.models import Lesson, ReadingText, Topic

BACKEND = Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
CRITERIA = ('goal_alignment', 'natural_polish', 'translations', 'unique_answers',
            'explanations', 'reading_and_glossary', 'own_response', 'sources')


class ReviewPacketError(ValueError):
    pass


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf8')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build_packet(source_commit):
    if not re.fullmatch(r'[0-9a-f]{40}', source_commit):
        raise ReviewPacketError('A full lowercase Git SHA is required.')
    executor = MigrationExecutor(connection)
    if executor.migration_plan(executor.loader.graph.leaf_nodes()):
        raise ReviewPacketError('Apply pending migrations in an isolated content database first.')
    topics = []
    for topic_id, pilot in PILOTS.items():
        topic = Topic.objects.select_related('course').filter(pk=topic_id, is_active=True,
                                                             course__is_active=True).first()
        if topic is None or topic.course.level != pilot['level']:
            raise ReviewPacketError(f'Missing or mismatched pilot: {topic_id}')
        lessons = []
        for lesson_id in pilot['lessons']:
            lesson = Lesson.objects.filter(pk=lesson_id, topic=topic, is_active=True).first()
            if lesson is None:
                raise ReviewPacketError(f'Missing active pilot lesson: {lesson_id}')
            questions = []
            for question in lesson.questions.filter(is_active=True).order_by('position', 'id'):
                if (not isinstance(question.options, list) or len(question.options) < 2
                        or not all(isinstance(option, str) and option for option in question.options)
                        or len(set(question.options)) != len(question.options)
                        or type(question.correct) is not int or not 0 <= question.correct < len(question.options)
                        or not question.explanation.strip()):
                    raise ReviewPacketError(f'Invalid question: {lesson_id}:{question.position}')
                questions.append({'ref': f'{lesson_id}:q:{question.position}', 'prompt': question.prompt,
                                  'options': question.options, 'correct': question.correct,
                                  'explanation': question.explanation})
            cards = []
            for link in lesson.flashcard_links.select_related('flashcard').filter(
                    flashcard__is_active=True).order_by('position', 'flashcard_id'):
                card = link.flashcard
                cards.append({'id': card.id, 'polish': card.polish, 'translation': card.translation,
                              'example': card.example, 'source_metadata': card.source_metadata})
            if not questions and not cards:
                raise ReviewPacketError(f'Empty pilot lesson: {lesson_id}')
            lessons.append({'id': lesson.id, 'kind': lesson.kind, 'title': lesson.title,
                            'description': lesson.description, 'theory_title': lesson.theory_title,
                            'theory_sections': lesson.theory_sections, 'source_metadata': lesson.source_metadata,
                            'questions': questions, 'cards': cards})
        reading = ReadingText.objects.filter(pk=pilot['reading_id'], topic=topic, is_active=True).first()
        if reading is None or reading.level != pilot['level'] or not reading.paragraphs:
            raise ReviewPacketError(f'Missing pilot reading: {pilot["reading_id"]}')
        if reading.source_metadata.get('comprehension_lesson_id') != pilot['lessons'][3]:
            raise ReviewPacketError(f'Reading-check link mismatch: {reading.id}')
        glossary = []
        for surface, value in sorted(reading.glossary.items()):
            entry = {'translation': value, 'lemma': surface} if isinstance(value, str) else value
            if not isinstance(entry, dict) or not isinstance(entry.get('translation'), str):
                raise ReviewPacketError(f'Invalid glossary: {reading.id}')
            glossary.append({'surface': surface, 'lemma': entry.get('lemma', surface),
                             'translation': entry['translation'], 'part_of_speech': entry.get('part_of_speech', '')})
        topics.append({'id': topic.id, 'level': pilot['level'], 'title': topic.title,
                       'journeys': {lang: journey(topic_id, lang) for lang in ('ru', 'pl', 'en')},
                       'lessons': lessons, 'reading': {'id': reading.id, 'title': reading.title,
                       'paragraphs': reading.paragraphs, 'glossary': glossary,
                       'source_glossary': reading.glossary,
                       'source_metadata': reading.source_metadata}})
    dependencies = [
        'locale/pl/LC_MESSAGES/django.mo', 'locale/en/LC_MESSAGES/django.mo',
        'polskiflow/learning/templatetags/ui.py', 'polskiflow/localization/server_patterns.json',
        'polskiflow/localization/russian_explanations.json', 'polskiflow/localization/polish_study_quotes.json',
        'polskiflow/localization/reading_english.json', 'templates/editorial/pilot_review.html',
        'templates/editorial/_pilot_reading.html',
        'polskiflow/pilot_review.py',
    ]
    snapshot = {'version': 1, 'declared_source_commit': source_commit,
                'source': 'configured Django content database; production parity not verified',
                'review_status': 'not_reviewed', 'release_authorized': False,
                'journey_source_metadata': SOURCE_METADATA,
                'learning_migrations': sorted(name for app, name in executor.loader.applied_migrations if app == 'learning'),
                'render_dependencies': {name: digest((BACKEND / name).read_bytes()) for name in dependencies},
                'topics': topics}
    source = encoded(snapshot)
    checksum = digest(source)
    artifacts = {'snapshot.json': source}
    for lang in ('ru', 'pl', 'en'):
        localized_topics = [{**topic, 'journey': topic['journeys'][lang]} for topic in topics]
        with override(lang):
            artifacts[f'review-{lang}.html'] = render_to_string('editorial/pilot_review.html', {
                'topics': localized_topics, 'language': lang, 'checksum': checksum,
                'source_commit': source_commit,
            }).encode('utf8')
    artifacts['review-notes.json'] = encoded({'snapshot_sha256': checksum, 'reviewer': '',
        'release_authorized': False, 'topics': [{
            'id': topic['id'], 'criteria': {criterion: None for criterion in CRITERIA}, 'findings': []
        } for topic in topics]})
    artifacts['manifest.json'] = encoded({'version': 1, 'snapshot_sha256': checksum,
        'review_status': 'not_reviewed', 'release_authorized': False,
        'files': {name: {'bytes': len(data), 'sha256': digest(data)} for name, data in artifacts.items()}})
    return artifacts


def write_packet(artifacts, directory):
    destination = Path(directory).expanduser().resolve()
    if destination == ROOT or ROOT in destination.parents:
        raise ReviewPacketError('Write the packet outside the repository.')
    if destination.exists():
        raise ReviewPacketError('Choose a new output directory; existing files are never overwritten.')
    destination.mkdir(mode=0o700)
    # Manifest is written last; an interrupted export must not look complete.
    for name, data in artifacts.items():
        with (destination / name).open('xb') as target:
            os.fchmod(target.fileno(), 0o600)
            target.write(data)
    return destination
