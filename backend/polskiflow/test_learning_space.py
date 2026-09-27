from unittest.mock import patch

from django.test import TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser


class LearningSpaceTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser(
                "11111111-1111-4111-8111-111111111111", "learner@example.com"
            ),
        )
        auth.start()
        self.addCleanup(auth.stop)

    def test_learning_space_groups_personal_materials(self):
        response = self.client.get("/my-learning/")

        self.assertContains(response, "Мои материалы")
        self.assertContains(response, 'class="card learning-space-card"', count=4)
        for href in ("/saved/", "/collections/", "/notes/", "/mistakes/"):
            self.assertContains(response, f'href="{href}"')
        self.assertContains(response, 'aria-current="page"')

    def test_learning_space_requires_authentication(self):
        self.client.cookies.clear()
        response = self.client.get("/my-learning/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])
