from django.test import Client, TestCase


class PublicLanguageTests(TestCase):
    def test_language_choice_preserves_route_query_and_translates_both_pages(self):
        for path in ('/?source=welcome', '/start/?source=welcome', '/demo/?source=welcome'):
            for language in ('ru', 'pl', 'en'):
                response = self.client.post('/language/', {'language': language, 'next': path})
                self.assertRedirects(response, path, fetch_redirect_response=False)
                self.assertEqual(response.cookies['django_language'].value, language)
                page = self.client.get(path)
                self.assertContains(page, f'<html lang="{language}"')
                self.assertContains(page, f'value="{language}" lang="{language}"')
                self.assertContains(page, 'aria-pressed="true"', count=1)
                self.assertContains(page, 'class="public-languages"', count=1)
                self.assertContains(page, 'name="next" value="' + path + '"')
                self.assertContains(page, {'ru': 'Войти', 'pl': 'Zaloguj się', 'en': 'Sign in'}[language])
                self.assertEqual(self.client.get('/login/').headers.get('Content-Language'), language)

    def test_language_change_requires_csrf_and_rejects_external_redirect(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/language/', {'language': 'en', 'next': '/demo/'}).status_code, 403)
        client.get('/demo/')
        response = client.post('/language/', {'language': 'en', 'next': '/demo/', 'csrfmiddlewaretoken': client.cookies['csrftoken'].value})
        self.assertRedirects(response, '/demo/', fetch_redirect_response=False)
        self.assertEqual(self.client.post('/language/', {'language': 'en', 'next': 'https://other.example/'}).headers['Location'], '/')
