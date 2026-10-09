"""Read-only excerpts of published course lessons for public demos."""
from polskiflow.learning.models import Lesson, Question

DEMO_LESSONS = {'A1': 'grammar', 'A2': 'past-grammar', 'B1': 'b1edu-grammar'}


def load_demo_lesson(level):
    lesson = Lesson.objects.filter(
        id=DEMO_LESSONS[level], is_active=True, topic__is_active=True,
        topic__course__is_active=True, topic__course__level=level,
    ).values('id', 'title', 'theory_title', 'theory_sections').first()
    if not lesson or not lesson['theory_sections']:
        return None
    question = Question.objects.filter(lesson_id=lesson['id'], position=0, is_active=True).values(
        'prompt', 'options', 'correct', 'explanation',
    ).first()
    if not question:
        return None
    return {**lesson, 'level': level, 'theory': lesson['theory_sections'][0], 'question': question}
