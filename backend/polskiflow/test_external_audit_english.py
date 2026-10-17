"""Regression for the five grammar terminology errors reported on 17 October."""
import json
from pathlib import Path

from django.conf import settings
from django.template import Context, Template
from django.test import TestCase
from django.utils.translation import override

from polskiflow.public_demo_store import load_demo_lesson


GRAMMAR_MESSAGES = {
    'В единственном числе форма показывает род: on pracował/był, ona pracowała/była.':
        'In the singular, the verb form shows grammatical gender: on pracował/był, ona pracowała/była.',
    'В мужском роде прошедшее время имеет окончание -ł: pracował.':
        'The masculine past-tense form ends in -ł: pracował.',
    'Говорящий выбирает форму по своему роду: robiłem/byłem или robiłam/byłam.':
        'The speaker chooses the form according to their gender: robiłem/byłem or robiłam/byłam.',
    'Форма który меняется по роду, числу и роли: osoba, która pomaga; kolega, któremu ufam.':
        'The form of który changes according to gender, number and grammatical role: osoba, która pomaga; kolega, któremu ufam.',
    'Я проверил вид, род и согласование глаголов прошедшего времени.':
        'I checked the aspect, gender and agreement of past-tense verbs.',
}


class ExternalAuditEnglishTests(TestCase):
    def test_grammar_messages_agree_in_rendered_support_and_browser_catalogue(self):
        script = (Path(settings.BASE_DIR) /
                  'polskiflow/learning/static/polskiflow/i18n-en.js').read_text()
        catalogue = json.loads(script.split(' = ', 1)[1].removesuffix(';\n'))
        template = Template('{% load ui %}{{ source|ui_text }}')
        with override('en'):
            for source, expected in GRAMMAR_MESSAGES.items():
                with self.subTest(source=source):
                    self.assertEqual(template.render(Context({'source': source})), expected)
                    self.assertEqual(catalogue[source], expected)
                    self.assertNotIn('genus', expected)
        with override('ru'):
            for source in GRAMMAR_MESSAGES:
                self.assertEqual(template.render(Context({'source': source})), source)

    def test_real_a2_guest_intro_theory_and_wrong_answer_use_grammatical_terms(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = 'en'
        theory = GRAMMAR_MESSAGES['В единственном числе форма показывает род: on pracował/był, ona pracowała/była.']
        explanation = GRAMMAR_MESSAGES['В мужском роде прошедшее время имеет окончание -ł: pracował.']
        intro = self.client.get('/start/')
        self.assertContains(intro, theory)
        self.assertContains(intro, explanation)
        self.assertContains(self.client.get('/demo/', {'level': 'A2'}), theory)
        question = load_demo_lesson('A2')['question']
        exercise = self.client.get('/demo/', {'level': 'A2', 'step': 'exercise'})
        answer = (question['correct'] + 1) % len(question['options'])
        response = self.client.post('/demo/?level=A2', {
            'state': exercise.context['state'], 'answer': str(answer),
        }, follow=True)
        self.assertFalse(response.context['correct'])
        self.assertContains(response, explanation)
        self.assertNotContains(response, 'genus')
