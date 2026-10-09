"""Version and validate isolated, ungraded public lesson answers."""
import hashlib
import json

DEMO_SALT = 'lingoflow-public-mini-lesson-v2'


def demo_version(lesson):
    return hashlib.sha256(json.dumps(lesson, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def checked_answer(lesson, state):
    if not isinstance(state, dict) or set(state) != {'version', 'answer'} or state['version'] != demo_version(lesson):
        raise ValueError('Changed lesson or invalid state')
    answer = state['answer']
    if type(answer) is not int or not 0 <= answer < len(lesson['question']['options']):
        raise ValueError('Invalid answer')
    question = lesson['question']
    return {'answer': answer, 'correct': answer == question['correct'],
            'selected_text': question['options'][answer], 'correct_text': question['options'][question['correct']]}
