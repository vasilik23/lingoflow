import hashlib
import json
import re
from pathlib import Path
from unittest.mock import patch

from django.core import signing
from django.test import Client, TestCase
from django.utils.translation import override
from polskiflow.learning.templatetags.ui import ui_text

from polskiflow.domain.public_demo import DEMO_SALT, demo_version
from polskiflow.public_demo_store import load_demo_lesson
from polskiflow.learning.models import Lesson, Question


class PublicDemoTests(TestCase):
    def exercise(self, level='A1'):
        return self.client.get('/demo/', {'level': level, 'step': 'exercise'})

    def answer(self, value, level='A1', **extra):
        response = self.exercise(level)
        return self.client.post('/demo/?level=' + level, {'state': response.context['state'], 'answer': value, **extra}, follow=True)

    @patch('polskiflow.auth_views._daily_plan')
    @patch('polskiflow.auth_views.load_latest_lesson_draft')
    def test_guest_root_is_intro_without_loading_account_data(self, draft, plan):
        for path in ('/', '/start/'):
            response = self.client.get(path)
            self.assertTemplateUsed(response, 'public_intro.html')
            self.assertContains(response, 'href="/demo/"')
            self.assertContains(response, 'href="/login/"')
            self.assertEqual(response['Cache-Control'], 'private, no-store')
        draft.assert_not_called()
        plan.assert_not_called()
        self.assertEqual(self.client.head('/').status_code, 200)
        self.assertEqual(self.client.post('/').status_code, 405)

    def test_intro_shows_real_course_question_and_explanation_in_shared_components(self):
        lesson = load_demo_lesson('A2')
        page = self.client.get('/start/')
        self.assertContains(page, lesson['question']['prompt'])
        self.assertContains(page, lesson['question']['explanation'])
        self.assertContains(page, 'href="/demo/?level=A2"')
        self.assertContains(page, 'public-example-selected', count=1)
        self.assertNotContains(page, 'name="answer"')
        self.assertTemplateUsed(page, 'partials/public_lesson_question.html')
        self.assertTemplateUsed(page, 'partials/public_lesson_explanation.html')
        self.assertContains(self.exercise('A2'), lesson['question']['prompt'])

    def test_all_levels_start_with_theory_then_exercise_without_answer_leak(self):
        for level in ('A1', 'A2', 'B1'):
            lesson = load_demo_lesson(level)
            page = self.client.get('/demo/', {'level': level})
            self.assertEqual(page.context['step'], 'theory')
            self.assertContains(page, lesson['theory'][1])
            self.assertContains(page, 'aria-current="step"', count=1)
            exercise = self.exercise(level)
            self.assertEqual(exercise.context['step'], 'exercise')
            self.assertContains(exercise, 'name="answer"', count=len(lesson['question']['options']))
            self.assertNotContains(exercise, lesson['question']['explanation'])
            self.assertNotContains(exercise, 'Правильный ответ:')
            self.assertEqual(exercise['Cache-Control'], 'private, no-store')

    @patch('polskiflow.auth_views.save_profile_settings')
    @patch('polskiflow.lesson_views.save_lesson_completion_result')
    def test_correct_and_wrong_answers_show_feedback_and_result_without_writes(self, completion, profile):
        for level in ('A1', 'A2', 'B1'):
            question = load_demo_lesson(level)['question']
            for value, passed in ((question['correct'], True), ((question['correct'] + 1) % len(question['options']), False)):
                result = self.answer(str(value), level, score='100')
                self.assertEqual(len(result.redirect_chain), 1)
                self.assertEqual(result.context['step'], 'result')
                self.assertEqual(result.context['correct'], passed)
                self.assertContains(result, question['explanation'], count=1)
                self.assertContains(result, ('1' if passed else '0') + ' / 1')
                self.assertContains(result, 'href="/register/?next=')
                self.assertContains(result, 'а не проверка уровня')
                self.assertNotIn('sessionid', result.cookies)
        profile.assert_not_called()
        completion.assert_not_called()

    def test_result_shows_feedback_before_the_next_action(self):
        lesson = load_demo_lesson('B1')
        result = self.answer(str(lesson['question']['correct']), level='B1')
        html = result.content.decode()
        self.assertContains(result, 'public-demo-outcome')
        self.assertLess(html.index('id="demo-feedback-title"'), html.index('class="complete-next"'))
        self.assertNotContains(result, 'К результату')
        self.assertContains(result, 'Мини-урок завершён', count=1)

    def test_english_b1_demo_heading_matches_the_question(self):
        self.client.cookies['django_language'] = 'en'
        theory = self.client.get('/demo/', {'level': 'B1'})
        exercise = self.exercise('B1')
        for page in (theory, exercise):
            self.assertContains(page, 'Giving a reason with ponieważ')
            self.assertNotContains(page, 'Indirect Speech')
        self.assertContains(exercise, 'Uczę się regularnie, ___ chcę dobrze zdać egzamin.')
        options = exercise.context['lesson']['question']['options']
        result = self.answer(str(options.index('ponieważ')), 'B1')
        self.assertTrue(result.context['correct'])
        self.assertContains(result, 'ponieważ')

    def test_invalid_duplicate_and_missing_values_are_rejected(self):
        for value in ('-1', '100', 'true', '01', ['0', '1']):
            self.assertEqual(self.answer(value).status_code, 400)
        self.assertEqual(self.client.post('/demo/', {}).status_code, 400)
        state = self.exercise().context['state']
        self.assertEqual(self.client.post('/demo/', {'state': [state, state], 'answer': '1'}).status_code, 400)

    def test_signed_state_expiry_content_changes_and_cross_level_are_rejected(self):
        response = self.exercise()
        state = response.context['state']
        self.assertEqual(self.client.post('/demo/', {'state': state + 'bad', 'answer': '1'}).status_code, 400)
        with patch('django.core.signing.TimestampSigner.unsign', side_effect=signing.SignatureExpired()):
            self.assertEqual(self.client.post('/demo/', {'state': state, 'answer': '1'}).status_code, 400)
        self.assertEqual(self.client.post('/demo/?level=B1', {'state': state, 'answer': '1'}).status_code, 400)
        Question.objects.filter(lesson_id='grammar', position=0).update(prompt='Changed')
        self.assertEqual(self.client.post('/demo/', {'state': state, 'answer': '1'}).status_code, 400)

    def test_result_requires_valid_current_review_and_survives_refresh_and_language_change(self):
        lesson = load_demo_lesson('B1')
        response = self.answer(str(lesson['question']['correct']), 'B1')
        url = response.redirect_chain[-1][0] + '&step=result'
        self.assertEqual(self.client.get(url).context['step'], 'result')
        self.client.post('/language/', {'language': 'en', 'next': url})
        page = self.client.get(url)
        self.assertContains(page, 'Mini-lesson completed')
        self.assertEqual(page.context['correct'], True)
        for review in ('invalid', signing.dumps({'version': demo_version(lesson), 'answer': True}, salt=DEMO_SALT), signing.dumps({'version': demo_version(lesson), 'answer': 99}, salt=DEMO_SALT)):
            self.assertEqual(self.client.get('/demo/', {'level': 'B1', 'step': 'result', 'review': review}).status_code, 400)
        self.assertEqual(self.client.get('/demo/?level=B1&step=result').context['step'], 'theory')
        self.assertEqual(self.client.get('/demo/', {'level': 'B1', 'review': ['bad', 'bad']}).status_code, 400)

    def test_inactive_or_missing_materials_degrade_without_hiding_intro(self):
        Lesson.objects.filter(id='past-grammar').update(is_active=False)
        self.assertContains(self.client.get('/demo/?level=A2'), 'временно недоступно', status_code=503)
        page = self.client.get('/start/')
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, 'public-example-selected')
        self.assertContains(page, 'href="/demo/"')
        Question.objects.filter(lesson_id='grammar').update(is_active=False)
        self.assertEqual(self.client.get('/demo/').status_code, 503)

    def test_csrf_methods_and_fallback_level(self):
        self.assertEqual(Client(enforce_csrf_checks=True).post('/demo/', {}).status_code, 403)
        self.assertEqual(self.client.delete('/demo/').status_code, 405)
        self.assertEqual(self.client.post('/start/').status_code, 405)
        self.assertEqual(self.client.head('/demo/').status_code, 200)
        self.assertEqual(self.client.get('/demo/?level=C2').context['level'], 'A1')

    def test_translated_materials_and_demo_discovery_links(self):
        for language, title in (('pl', 'Zadanie próbne'), ('en', 'Sample exercise')):
            self.client.cookies['django_language'] = language
            for level in ('A1', 'A2', 'B1'):
                lesson = load_demo_lesson(level)
                with override(language):
                    for text in [lesson['theory_title'], *lesson['theory'], lesson['question']['prompt'], lesson['question']['explanation']]:
                        self.assertFalse(re.search('[А-Яа-яЁё]', ui_text(text)), (language, level, text))
                self.assertContains(self.exercise(level), title)
                self.assertEqual(self.answer('1', level).status_code, 200)
        for path in ('/login/', '/register/'):
            self.assertContains(self.client.get(path), 'href="/demo/"')


class PublicMeetingMissionTests(TestCase):
    url = "/demo/?level=B1&mission=meeting"

    def test_wrong_choice_leads_to_new_example_and_transfer_before_local_writing(self):
        start = self.client.get(self.url)
        self.assertContains(start, "z wtorku na środę")
        retry = self.client.post(self.url, {"step": "0", "answer": "1"})
        self.assertContains(retry, "z czwartku na piątek")
        self.assertContains(retry, "новый день указан неверно")
        self.assertNotContains(retry, 'id="mission-draft"')
        transfer = self.client.post(self.url, {"step": "1", "answer": "1"})
        self.assertContains(transfer, "Просмотр квартиры")
        self.assertNotContains(transfer, "В конструкции")
        self.assertNotContains(transfer, 'id="mission-draft"')
        self.assertNotContains(transfer, "dialogue-fragment-1.m4a")
        result = self.client.post(self.url, {"step": "2", "answer": "0"})
        self.assertContains(result, 'id="mission-draft"')
        self.assertContains(result, "przełożyć spotkanie na środę")
        self.assertContains(result, 'href="/register/?next=%2Flesson%2Fb1edu-grammar%2F"')
        self.assertEqual(result["Cache-Control"], "private, no-store")

    def test_correct_first_choice_goes_directly_to_transfer(self):
        result = self.client.post(self.url, {"step": "0", "answer": "0"})
        self.assertContains(result, "z soboty na poniedziałek")
        self.assertNotContains(result, "В конструкции")
        self.assertNotContains(result, "z czwartku na piątek")

    def test_wrong_transfer_answer_returns_to_guided_retry(self):
        result = self.client.post(self.url, {"step": "2", "answer": "1"})
        self.assertContains(result, "В конструкции")
        self.assertContains(result, "z czwartku na piątek")
        self.assertNotContains(result, 'id="mission-draft"')

    def test_writing_screen_offers_listening_with_a_matching_transcript(self):
        self.client.cookies["django_language"] = "en"
        result = self.client.post(self.url, {"step": "2", "answer": "0"})
        self.assertContains(result, "Where are they meeting?")
        self.assertContains(result, "In front of ticket counter number three.")
        self.assertContains(result, "dialogue-fragment-1.m4a")
        self.assertContains(result, "Spotkajmy się o ósmej przed kasą numer trzy.")
        manifest_path = Path(__file__).parent / "domain" / "practice_listening_media.json"
        clip = json.loads(manifest_path.read_text())["clips"]["dialogue-fragment-1"]
        transcript_hash = hashlib.sha256(result.context["listening_transcript"].encode()).hexdigest()
        self.assertEqual(transcript_hash, clip["transcript_sha256"])
