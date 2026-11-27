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
        self.assertContains(result, 'class="compact-button" href="/mistakes/"')
        self.assertNotContains(result, "Следующая ошибка")

    @patch("polskiflow.mistake_views.set_mistake", return_value=True)
    @patch("polskiflow.mistake_views.load_mistakes", return_value=[{"lesson_id": "mistake-quiz", "question_position": 0}])
    def test_last_correct_answer_returns_to_its_source(self, load, save):
        token = sign_mistake("user-1", "mistake-quiz", 0)
        for query, target in (("", "/mistakes/"), ("?from=today", "/"),
                              ("?lesson=mistake-quiz", "/lesson/mistake-quiz/")):
            with self.subTest(query=query):
                response = self.client.post("/mistakes/practice/" + query, {"state": token, "choice": "1"})
                self.assertContains(response, f'class="compact-button" href="{target}"')
                self.assertNotContains(response, "Следующая ошибка")

        load.return_value += [{"lesson_id": "mistake-quiz", "question_position": 1}]
        response = self.client.post("/mistakes/practice/?from=today", {"state": token, "choice": "1"})
        self.assertContains(response, "Следующая ошибка")
        save.return_value = False
        response = self.client.post("/mistakes/practice/?from=today", {"state": token, "choice": "1"})
        self.assertContains(response, "Обновить тренировку")

    @patch("polskiflow.mistake_views.load_mistakes", return_value=[])
    def test_empty_lesson_queue_returns_to_notebook_when_started_there(self, _load):
        page = self.client.get("/mistakes/practice/?lesson=mistake-quiz&from=notebook")
        self.assertContains(page, "Ошибок этого урока нет")
        self.assertContains(page, '<a class="compact-button" href="/mistakes/">Вернуться к списку ошибок</a>',
                            html=True)

    @patch("polskiflow.mistake_views.load_mistakes")
    def test_notebook_groups_two_questions_from_one_lesson_under_one_action(self, load):
        Question.objects.create(lesson_id="mistake-quiz", position=1, prompt="Drugi przykład",
                                options=["dobrze", "źle"], correct=0)
        load.return_value = [{"lesson_id": "mistake-quiz", "question_position": n} for n in (0, 1)]
        response = self.client.get("/mistakes/")
        self.assertContains(response, "Wybierz odpowiedź")
        self.assertContains(response, "Drugi przykład")
        self.assertContains(response, 'href="/mistakes/practice/?lesson=mistake-quiz&amp;from=notebook"', count=1)
        self.assertContains(response, "Повторить ошибки урока · 2")

    @patch("polskiflow.mistake_views.load_mistakes", return_value=[
        {"lesson_id": "b1edu-grammar", "question_position": 0},
        {"lesson_id": "mistake-quiz", "question_position": 0},
    ])
    def test_notebook_shows_localized_focus_only_for_annotated_questions(self, _load):
        for locale, focus in (
            ("ru", "Что повторить · Союзы причины и уступки"),
            ("en", "What to review · Conjunctions of reason and concession"),
            ("pl", "Co powtórzyć · Spójniki przyczyny i przyzwolenia"),
        ):
            with self.subTest(locale=locale):
                self.client.cookies["django_language"] = locale
                response = self.client.get("/mistakes/")
                self.assertContains(response, focus)
                self.assertContains(response, 'class="mistake-review-focus"', count=1)
                self.assertContains(response, "Wybierz odpowiedź")

    @patch("polskiflow.mistake_views.load_mistakes", return_value=[
        {"lesson_id": "past-grammar", "question_position": 0},
        {"lesson_id": "b1edu-grammar", "question_position": 3},
    ])
    def test_notebook_shows_focus_for_past_tense_and_reported_questions(self, _load):
        self.client.cookies["django_language"] = "en"
        response = self.client.get("/mistakes/")
        self.assertContains(response, "Gender in the past tense (singular)")
        self.assertContains(response, "Reported yes–no questions")

    @patch("polskiflow.mistake_views.set_mistake", return_value=True)
    @patch("polskiflow.mistake_views.load_mistakes")
    def test_construction_queue_spans_lessons_and_leaves_other_mistakes(self, load, save):
        rows = [
            {"lesson_id": "housing-grammar", "question_position": 0},
            {"lesson_id": "housing-quiz", "question_position": 1},
            {"lesson_id": "b1edu-grammar", "question_position": 0},
        ]
        load.return_value = rows
        path = "/mistakes/practice/?focus=nie-ma-genitive"
        notebook = self.client.get("/mistakes/")
        self.assertContains(notebook, f'href="{path}"')
        self.assertContains(notebook, "Родительный падеж после nie ma · 2")
        self.assertEqual(self.client.get(path).context["question"].lesson_id, "housing-grammar")

        other = sign_mistake("user-1", "b1edu-grammar", 0)
        self.assertEqual(self.client.post(path, {"state": other, "choice": "0"}).status_code, 400)
        save.assert_not_called()

        for lesson_id, position, remaining in (("housing-grammar", 0, 1), ("housing-quiz", 1, 0)):
            page = self.client.get(path)
            self.assertEqual(page.context["question"].lesson_id, lesson_id)
            question = page.context["question"]
            answer = self.client.post(path, {"state": page.context["state"], "choice": question.correct})
            self.assertEqual(answer.context["remaining"], remaining)
            save.assert_called_with("access", "user-1", lesson_id, position, False)
            rows.pop(0)
        self.assertContains(answer, 'class="compact-button" href="/mistakes/"')
        self.assertNotContains(self.client.get("/mistakes/"), f'href="{path}"')
        self.assertContains(self.client.get("/mistakes/"), "Союзы причины и уступки")
        self.assertContains(self.client.get(path), 'class="compact-button" href="/mistakes/"')

        for query in ("?focus=unknown", "?focus=nie-ma-genitive&focus=z-instrumental",
                      "?focus=nie-ma-genitive&lesson=housing-grammar"):
            self.assertEqual(self.client.get("/mistakes/practice/" + query).status_code, 400)

    @patch("polskiflow.mistake_views.set_mistake", return_value=True)
    @patch("polskiflow.mistake_views.load_mistakes", return_value=[
        {"lesson_id": "housing-grammar", "question_position": 0},
    ])
    def test_construction_from_today_returns_to_today(self, _load, _save):
        path = "/mistakes/practice/?focus=nie-ma-genitive&from=today"
        page = self.client.get(path)
        self.assertContains(page, 'action="/mistakes/practice/?focus=nie-ma-genitive&amp;from=today"')
        answer = self.client.post(path, {"state": page.context["state"], "choice": page.context["question"].correct})
        self.assertContains(answer, 'class="compact-button" href="/"')

    @patch("polskiflow.mistake_views.set_mistake", return_value=True)
    @patch("polskiflow.mistake_views.load_mistakes", return_value=[
        {"lesson_id": "b1edu-grammar", "question_position": 0},
    ])
    def test_contextual_hint_only_appears_after_wrong_retry(self, _load, _save):
        path = "/mistakes/practice/?focus=reason-concession"
        page = self.client.get(path)
        self.assertNotContains(page, "data-feedback-hint")
        correct = page.context["question"].correct
        payload = {"state": page.context["state"], "choice": (correct + 1) % 3}
        retry = self.client.post(path, payload)
        self.assertContains(retry, "data-feedback-hint")
        self.assertContains(retry, "Chociaż")
        self.assertNotContains(self.client.post(path, {**payload, "choice": correct}), "data-feedback-hint")
