from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser


class PrivacyPageTests(SimpleTestCase):
    def test_public_page_has_factual_inventory_controls_and_limits(self):
        response = self.client.get("/privacy/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Приватность и данные")
        self.assertContains(response, "Supabase")
        self.assertContains(response, "Vercel")
        self.assertContains(response, "Черновики письма")
        self.assertContains(response, "самостоятельно удалить аккаунт")
        self.assertContains(response, "Vasili Kamisarau")
        self.assertContains(response, "mailto:lingoflow.privacy@gmail.com")
        self.assertContains(response, "Автоматическое предупреждение и удаление пока не включены")
        self.assertContains(response, "https://commission.europa.eu/")
        self.assertContains(response, "https://uodo.gov.pl/")
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_public_page_does_not_expose_authenticated_export_action(self):
        response = self.client.get("/privacy/")
        self.assertNotContains(response, "Скачать мои данные")
        self.assertContains(response, 'href="/login/"')

    @patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("user-1", "learner@example.com"))
    def test_authenticated_controls_are_private_and_not_cached(self, _authenticate):
        self.client.cookies[ACCESS_COOKIE] = "access"
        response = self.client.get("/privacy/")
        self.assertContains(response, 'href="/account/security/#account-delete-title"')
        self.assertEqual(response["Cache-Control"], "private, no-store")

    @override_settings(
        MIDDLEWARE=["django.middleware.cache.UpdateCacheMiddleware", *settings.MIDDLEWARE,
                    "django.middleware.cache.FetchFromCacheMiddleware"],
        CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                            "LOCATION": "privacy-language-regression"}},
        CACHE_MIDDLEWARE_SECONDS=300,
    )
    def test_warmed_shared_cache_does_not_override_language_cookie(self):
        cache.clear()
        self.addCleanup(cache.clear)
        titles = {'ru': 'Приватность и данные', 'pl': 'Prywatność i dane', 'en': 'Privacy and data'}
        for lang in ('ru', 'pl', 'en', 'en', 'pl', 'ru'):
            self.client.cookies['django_language'] = lang
            response = self.client.get('/privacy/', HTTP_ACCEPT_LANGUAGE='ru')
            self.assertEqual(response['Content-Language'], lang)
            self.assertContains(response, f'<html lang="{lang}">')
            self.assertContains(response, titles[lang])
            self.assertEqual(response['Cache-Control'], 'private, no-store')
            self.assertIn('Cookie', response['Vary'])

    @patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("user-1", "learner@example.com"))
    def test_authenticated_language_and_export_controls_keep_private_boundary(self, _authenticate):
        self.client.cookies[ACCESS_COOKIE] = 'access'
        self.client.cookies['django_language'] = 'en'
        response = self.client.get('/privacy/', HTTP_ACCEPT_LANGUAGE='ru')
        self.assertEqual(response['Content-Language'], 'en')
        self.assertContains(response, 'href="/account/security/#account-delete-title"')
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertIn('Cookie', response['Vary'])

    def test_owner_contact_age_and_retention_are_translated_in_all_languages(self):
        for language, expected in (
            ('ru', ('Кто отвечает за данные', 'Хранение и удаление', 'Автоматическое предупреждение и удаление пока не включены')),
            ('pl', ('Administrator danych', 'Przechowywanie i usuwanie', 'Automatyczne ostrzeganie i usuwanie nie są jeszcze włączone')),
            ('en', ('Who is responsible for your data', 'Retention and deletion', 'Automatic warnings and deletion are not yet enabled')),
        ):
            self.client.cookies['django_language'] = language
            response = self.client.get('/privacy/')
            for text in (*expected, 'Vasili Kamisarau', 'mailto:lingoflow.privacy@gmail.com'):
                self.assertContains(response, text)
            if language != 'ru':
                self.assertNotContains(response, 'Кто отвечает за данные')
                self.assertNotContains(response, 'Перед широким публичным запуском владелец')

    def test_published_limits_distinguish_build_logs_and_manual_backups(self):
        response = self.client.get('/privacy/')
        for text in ('Build-журналы Vercel', 'Google Drive', 'Apple «Пароли»', '180 дней после закрытия', 'автоматическое расписание пока не настроено'):
            self.assertContains(response, text)
        self.assertNotContains(response, 'v.kamisarau@gmail.com')
