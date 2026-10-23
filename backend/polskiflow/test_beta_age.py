from unittest.mock import patch

from django.test import SimpleTestCase


class AdultBetaRegistrationTests(SimpleTestCase):
    @patch('polskiflow.auth_views.sign_up', return_value=None)
    @patch('polskiflow.auth_views.consume_auth_attempt', return_value=(True, 0))
    def test_only_one_explicit_confirmation_allows_signup(self, rate, signup):
        base = {'email': 'adult@example.com', 'password': 'Bezpieczne2026'}
        for value in (None, '', 'off', 'true', ['on', 'on'], ['off', 'on']):
            payload = dict(base)
            if value is not None:
                payload['adult_confirmation'] = value
            response = self.client.post('/register/', payload)
            self.assertContains(response, 'Beta LingoFlow доступна только с 18 лет')
            self.assertEqual(response['Cache-Control'], 'private, no-store')
        signup.assert_not_called()
        rate.assert_not_called()
        self.client.post('/register/', {**base, 'adult_confirmation': 'on'})
        signup.assert_called_once()

    def test_checkbox_is_registration_only_and_not_preselected(self):
        response = self.client.get('/register/')
        self.assertContains(response, 'name="adult_confirmation" required')
        self.assertNotContains(response, 'name="adult_confirmation" checked')
        self.assertContains(response, 'href="/privacy/"')
        self.assertNotContains(response, 'type="date"')
        self.assertNotContains(self.client.get('/login/'), 'adult_confirmation')
