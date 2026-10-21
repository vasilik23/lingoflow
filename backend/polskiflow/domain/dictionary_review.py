"""Signed browser review snapshots; scheduling writes remain in the store."""
import hashlib
import json
from django.core import signing

SALT = 'lingoflow-dictionary-review-v1'


def question_version(question):
    content = {key: question.get(key) for key in ('id', 'word', 'prompt', 'context', 'options', 'correct_answer')}
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def sign_review(owner, context, mode, source):
    question = context['question']
    selected = context.get('selected')
    correct = context.get('answer_correct') if question['typed'] else selected == question['correct']
    return signing.dumps({
        'owner': owner, 'word_id': question['id'], 'version': question_version(question),
        'reviewed_at': question.get('last_reviewed_at'), 'index': context['index'], 'score': context['score'],
        'mode': mode, 'source': source, 'answered': context.get('answered', False),
        'selected': selected, 'correct': bool(correct), 'answer': context.get('submitted_answer', '')[:160],
    }, salt=SALT, compress=True)


def read_review(token, owner, question, index, score, mode, source, answered):
    state = signing.loads(token, salt=SALT, max_age=86400)
    expected = {'owner': owner, 'word_id': question['id'], 'version': question_version(question),
                'index': index, 'score': score, 'mode': mode, 'source': source, 'answered': answered}
    if not isinstance(state, dict) or any(state.get(key) != value for key, value in expected.items()):
        raise ValueError('Review changed')
    return state
