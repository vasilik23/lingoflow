"""Short contextual contrasts for existing original learning questions."""
from django.utils.translation import gettext_noop

_HINTS = {
    ('grammar', 0): ('Jestem Anna.', gettext_noop('Jestem — форма для «я», jesteś — для «ты». Говоря о себе, выбираем jestem: Jestem Anna.')),
    ('b1edu-grammar', 0): ('ponieważ', gettext_noop('Ponieważ — «потому что»: здесь объясняется причина регулярных занятий. Chociaż — «хотя»: это уступка, а не причина.')),
}


def feedback_hint(lesson_id, position, question):
    expected, hint = _HINTS.get((lesson_id, position), (None, None))
    try:
        answer = question['options'][question['correct']]
    except (KeyError, IndexError, TypeError):
        return None
    return hint if expected is not None and answer == expected else None
