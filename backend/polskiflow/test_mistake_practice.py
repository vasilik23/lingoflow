from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.mistake_practice import InvalidMistakePracticeState, load_mistake, sign_mistake
from polskiflow.learning.models import Course, Lesson, Question, Topic


class MistakePracticeStateTests(SimpleTestCase):
    def test_state_is_owner_bound_and_tamper_evident(self):
        token = sign_mistake("owner", "quiz", 2)
        self.assertEqual(load_mistake(token, "owner").position, 2)
        self.assertNotIn("owner", token)
        with self.assertRaises(InvalidMistakePracticeState):
            load_mistake(token, "other")
        with self.assertRaises(InvalidMistakePracticeState):
            load_mistake(token[:-1] + "x", "owner")


class MistakePracticeViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        course = Course.objects.create(id="mistake-course", title="A1", level="A1")
        topic = Topic.objects.create(id="mistake-topic", course=course, title="Тема")
        lesson = Lesson.objects.create(id="mistake-quiz", topic=topic, kind="quiz", title="Test", plan_title="Тест ошибок")
        Question.objects.create(lesson=lesson, prompt="Wybierz odpowiedź", options=["źle", "dobrze", "też źle"], correct=1, explanation="Dobry wariant pasuje do kontekstu.", position=0)

    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        patcher = patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("user-1", "a@example.com"))
        patcher.start()
        self.addCleanup(patcher.stop)

    @patch("polskiflow.mistake_views.load_mistakes", return_value=[{"lesson_id": "mistake-quiz", "question_position": 0}])
    def test_get_renders_only_owned_mistake_without_answer_key(self, _load):
        response = self.client.get("/mistakes/practice/")
        self.assertContains(response, "Wybierz odpowiedź")
        self.assertContains(response, "Тест ошибок")
        self.assertNotContains(response, "Dobry wariant pasuje")

    @patch("polskiflow.mistake_views.set_mistake", return_value=True)
    @patch("polskiflow.mistake_views.load_mistakes", return_value=[{"lesson_id": "mistake-quiz", "question_position": 0}])
    def test_correct_answer_resolves_owner_row_and_shows_explanation(self, _load, save):
        token = sign_mistake("user-1", "mistake-quiz", 0)
        response = self.client.post("/mistakes/practice/", {"state": token, "choice": "1"})
        self.assertContains(response, "ошибка убрана")
        self.assertContains(response, "Dobry wariant pasuje")
        save.assert_called_once_with("access", "user-1", "mistake-quiz", 0, False)

    @patch("polskiflow.mistake_views.load_mistakes", return_value=[])
    def test_rejects_state_for_item_no_longer_owned(self, _load):
        token = sign_mistake("user-1", "mistake-quiz", 0)
        self.assertEqual(self.client.post("/mistakes/practice/", {"state": token, "choice": "1"}).status_code, 400)

    @patch("polskiflow.mistake_views.set_mistake", return_value=True)
    @patch("polskiflow.mistake_views.load_mistakes", return_value=[{"lesson_id": "mistake-quiz", "question_position": 0}])
    def test_notebook_back_link_survives_answer_in_lesson_scope(self, _load, _save):
        path = "/mistakes/practice/?lesson=mistake-quiz&from=notebook"
        from_lesson = self.client.get("/mistakes/practice/?lesson=mistake-quiz")
        self.assertContains(from_lesson, 'class="back-button" href="/lesson/mistake-quiz/"')
        page = self.client.get(path)
        self.assertContains(page, 'class="back-button" href="/mistakes/"')
        token = sign_mistake("user-1", "mistake-quiz", 0)
        result = self.client.post(path, {"state": token, "choice": "1"})
        self.assertContains(result, 'class="back-button" href="/mistakes/"')
        self.assertContains(result, 'href="/mistakes/practice/?lesson=mistake-quiz&amp;from=notebook"')
