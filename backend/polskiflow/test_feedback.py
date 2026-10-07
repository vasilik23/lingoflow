from unittest.mock import patch
from django.test import TestCase
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser

class FeedbackTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("user-1", "a@example.com"))
        auth.start(); self.addCleanup(auth.stop)

    @patch("polskiflow.feedback_views.load_feedback", return_value=[])
    def test_page_is_private_and_available_from_user_menu(self, _load):
        response = self.client.get("/feedback/?from=/lesson/words/")
        self.assertContains(response, "Обратная связь")
        self.assertContains(response, 'value="/lesson/words/"')
        self.assertContains(self.client.get("/help/?from=/"), 'href="/feedback/?from=/"')

    @patch("polskiflow.feedback_views.load_feedback", return_value=[])
    def test_authenticated_pages_offer_contextual_feedback_link(self, _load):
        response = self.client.get("/course/?level=B1")

        self.assertContains(response, 'href="/help/?from=/course/"')
        self.assertNotContains(response, 'class="feedback-launcher')
        self.assertContains(self.client.get("/help/?from=/course/"), 'href="/feedback/?from=/course/"')

    @patch(
        "polskiflow.feedback_views.load_feedback",
        return_value=[{"category": "interface", "priority": "blocking", "status": "resolved", "message": "Кнопка перекрывала текст.", "page_url": "/course/"}],
    )
    def test_history_uses_readable_category_and_status_labels(self, _load):
        response = self.client.get("/feedback/")

        self.assertContains(response, "Интерфейс")
        self.assertContains(response, "Исправлено")
        self.assertContains(response, "Не могу продолжить")
        self.assertContains(response, "/course/")

    @patch("polskiflow.feedback_views.load_feedback", return_value=[])
    @patch("polskiflow.feedback_views.save_feedback", return_value=True)
    def test_valid_feedback_is_owner_scoped(self, save, _load):
        response = self.client.post("/feedback/", {"category": "content", "priority": "high", "message": "В упражнении есть неточный вариант ответа.", "page_url": "/lesson/quiz/"})
        self.assertRedirects(response, "/feedback/?sent=1", fetch_redirect_response=False)
        save.assert_called_once_with("access", "user-1", category="content", priority="high", message="В упражнении есть неточный вариант ответа.", page_url="/lesson/quiz/")

    @patch("polskiflow.feedback_views.load_feedback", return_value=[])
    @patch("polskiflow.feedback_views.save_feedback")
    def test_invalid_input_never_writes(self, save, _load):
        response = self.client.post("/feedback/", {"category": "other", "message": "short", "page_url": "https://evil.example"})
        self.assertEqual(response.status_code, 400)
        save.assert_not_called()

    @patch("polskiflow.feedback_views.load_feedback", return_value=[])
    @patch("polskiflow.feedback_views.save_feedback")
    def test_invalid_priority_never_writes(self, save, _load):
        response = self.client.post("/feedback/", {"category": "idea", "priority": "urgent", "message": "Предлагаю добавить новый тип упражнения."})
        self.assertEqual(response.status_code, 400)
        save.assert_not_called()

    def test_requires_authentication(self):
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/feedback/").status_code, 302)
