"""Submit actual rendered form values, rather than bypassing localized HTML."""
from html.parser import HTMLParser
from unittest.mock import patch

from django.test import TestCase, override_settings
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.auth_views import LISTENING_ITEMS, LISTENING_DIALOGUE, LISTENING_B1, LISTENING_B2


class Radios(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.groups = {}
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'input' and attrs.get('type') == 'radio':
            self.groups.setdefault(attrs['name'], []).append(attrs)


@override_settings(SUPABASE_URL='', SUPABASE_ANON_KEY='')
class ListeningFormLocalizationTests(TestCase):
    def setUp(self):
        auth = patch('polskiflow.auth.authenticate_access_token',
                     return_value=SupabaseUser('listening-fixture', 'fixture@example.test'))
        auth.start()
        self.addCleanup(auth.stop)
        self.client.cookies[ACCESS_COOKIE] = 'fixture'

    def test_rendered_values_grade_and_retain_correct_wrong_and_mixed_choices_in_all_languages(self):
        groups = (
            ('a1-a2-listening', LISTENING_DIALOGUE['questions'], 'dialogue_score', 'dialogue_submitted'),
            ('b1-listening', LISTENING_B1['questions'], 'b1_score', 'b1_submitted'),
            ('b2-listening', LISTENING_B2['questions'], 'b2_score', 'b2_submitted'),
            ('listening-words', LISTENING_ITEMS, 'score', 'submitted'),
        )
        flags = {group[3] for group in groups}
        for language in ('ru', 'pl', 'en'):
            self.client.cookies['django_language'] = language
            form = Radios(self.client.get('/listening/').content.decode())
            for section, questions, score_key, flag in groups:
                for mode in ('correct', 'wrong', 'mixed'):
                    with self.subTest(language=language, section=section, mode=mode):
                        data = {'active_section': section}
                        expected = 0
                        for index, question in enumerate(questions):
                            options = form.groups[question['id']]
                            self.assertEqual([option['value'] for option in options], list(question['options']))
                            correct = mode == 'correct' or (mode == 'mixed' and index == 0)
                            chosen = next(option for option in options
                                          if (option['value'] == question['answer']) == correct)
                            data[question['id']] = chosen['value']
                            expected += int(correct)
                        result = self.client.post('/listening/', data)
                        self.assertEqual(result.status_code, 200)
                        self.assertEqual(result.context[score_key], expected)
                        self.assertTrue(result.context[flag])
                        for inactive in flags - {flag}:
                            self.assertFalse(result.context[inactive])
                        rendered = Radios(result.content.decode())
                        for question in questions:
                            selected = [option['value'] for option in rendered.groups[question['id']]
                                        if 'checked' in option]
                            self.assertEqual(selected, [data[question['id']]])

    def test_unknown_answer_does_not_become_a_correct_choice(self):
        question = LISTENING_DIALOGUE['questions'][0]
        result = self.client.post('/listening/', {'active_section': 'a1-a2-listening', question['id']: 'invalid'})
        self.assertEqual(result.context['dialogue_score'], 0)
        self.assertFalse(any('checked' in option for option in
                             Radios(result.content.decode()).groups[question['id']]))
