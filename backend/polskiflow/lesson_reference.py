"""Optional published reference material, with explicit pilot lesson bindings."""
from polskiflow.content import grammar, reading_text
from polskiflow.domain.topic_journeys import PILOTS


def lesson_reference(lesson_id, lesson_kind, grammar_content=None):
    for topic_id, pilot in PILOTS.items():
        if lesson_id not in pilot['lessons']:
            continue
        if lesson_id == pilot['lessons'][3]:
            reading = reading_text(pilot['reading_id'])
            if (reading and reading.topic_id == topic_id
                    and isinstance(reading.source_metadata, dict)
                    and reading.source_metadata.get('comprehension_lesson_id') == lesson_id):
                return {'kind': 'reading', 'title': reading.title, 'paragraphs': reading.paragraphs}
            return None
        if lesson_kind == 'grammar' or lesson_id == pilot['lessons'][4]:
            theory = grammar_content if lesson_kind == 'grammar' else grammar(pilot['lessons'][1])
            if theory and theory.get('sections'):
                return {'kind': 'grammar', 'title': theory['title'], 'sections': theory['sections']}
        return None
    return None
