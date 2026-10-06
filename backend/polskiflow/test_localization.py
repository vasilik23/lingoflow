import gettext as std_gettext
import ast
import json
import re
import subprocess
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command
from django.template import engines
from django.test import Client, SimpleTestCase, TestCase
from django.utils.translation import gettext, override

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.learning.templatetags.ui import ui_text


class LocalizationCatalogTests(SimpleTestCase):
    def test_every_template_compiles_and_has_translated_static_interface(self):
        backend = Path(settings.BASE_DIR)
        with override("pl"):
            for path in (backend / "templates").rglob("*.html"):
                engines["django"].get_template(str(path.relative_to(backend / "templates")))
                for message in re.findall(r'\{% translate ("(?:[^"\\]|\\.)*") %\}', path.read_text()):
                    source = json.loads(message)
                    self.assertNotEqual(gettext(source), source, f"Missing Polish message in {path}: {source}")

    def test_browser_catalog_is_current(self):
        call_command("build_ui_catalog", check=True, stdout=StringIO())

    def test_patterns_and_browser_ids_have_polish_translations(self):
        root = Path(settings.BASE_DIR) / "polskiflow/localization"
        with override("pl"):
            for name in ("server_patterns.json", "browser_messages.json"):
                for message in json.loads((root / name).read_text()):
                    self.assertNotEqual(gettext(message), message, message)

    def test_dynamic_labels_keep_values_and_escape_untrusted_text(self):
        with override("pl"):
            self.assertEqual(ui_text("До экзамена осталось 12 дней"), "Do egzaminu pozostało 12 dni")
            self.assertEqual(ui_text("Пароль должен содержать не менее 10 символов"), "Hasło musi zawierać co najmniej 10 znaków")
            self.assertEqual(ui_text("Неизвестная пользовательская заметка"), "Неизвестная пользовательская заметка")
            template = engines["django"].from_string("{% load ui %}{{ label|ui_text }}")
            self.assertIn("&lt;script&gt;", template.render({"label": "Лексика: <script>alert(1)</script>"}))
            for source, translated in (("1 тема", "1 temat"), ("2 темы", "2 tematy"), ("12 тем", "12 tematów"),
                                       ("22 темы", "22 tematy"), ("2 урока", "2 lekcje"), ("1 слово", "1 słowo")):
                self.assertEqual(ui_text(source), translated)
        with override("ru"):
            self.assertEqual(ui_text("До экзамена осталось 12 дней"), "До экзамена осталось 12 дней")

    def test_polish_auth_and_validation_and_russian_fallback(self):
        response = self.client.get("/login/", HTTP_ACCEPT_LANGUAGE="pl-PL,pl;q=0.9")
        self.assertContains(response, '<html lang="pl">')
        self.assertContains(response, "Zaloguj się do PolskiFlow")
        self.assertContains(response, "Język interfejsu")
        response = self.client.post("/login/", {}, HTTP_ACCEPT_LANGUAGE="pl")
        self.assertContains(response, "Podaj email i hasło")
        self.assertEqual(response["Content-Language"], "pl")
        from polskiflow.auth import SupabaseAuthError
        with patch("polskiflow.auth_views.sign_in", side_effect=SupabaseAuthError("Invalid login credentials")):
            response = self.client.post("/login/", {"email": "locale@example.com", "password": "invalid"}, HTTP_ACCEPT_LANGUAGE="pl")
        self.assertContains(response, "Nieprawidłowy email lub hasło.")
        response = self.client.get("/login/", HTTP_ACCEPT_LANGUAGE="de")
        self.assertContains(response, '<html lang="ru">')
        self.assertContains(response, "Войти в PolskiFlow")

    def test_language_choice_persists_and_overrides_browser_header(self):
        response = self.client.post("/language/", {"language": "pl", "next": "/practice/?level=B1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/practice/?level=B1")
        cookie = response.cookies[settings.LANGUAGE_COOKIE_NAME]
        self.assertEqual(cookie.value, "pl")
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")
        self.assertContains(self.client.get("/login/", HTTP_ACCEPT_LANGUAGE="ru"), '<html lang="pl">')
        self.client.post("/language/", {"language": "ru", "next": "/login/"})
        self.assertContains(self.client.get("/login/", HTTP_ACCEPT_LANGUAGE="pl"), '<html lang="ru">')

    def test_language_post_requires_csrf_and_rejects_external_next(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post("/language/", {"language": "pl"}).status_code, 403)
        response = self.client.post("/language/", {"language": "pl", "next": "https://evil.example/"})
        self.assertEqual(response["Location"], "/")
        response = self.client.post("/language/", {"language": "invalid", "next": "/login/"})
        self.assertNotIn(settings.LANGUAGE_COOKIE_NAME, response.cookies)

    def test_polish_public_pages_and_language_specific_offline_shell(self):
        for url, title in (("/register/", "Utwórz konto"), ("/forgot-password/", "Odzyskiwanie hasła"),
                           ("/sources/", "Źródła"), ("/privacy/", "Prywatność i dane")):
            response = self.client.get(url, HTTP_ACCEPT_LANGUAGE="pl")
            self.assertContains(response, title)
        response = self.client.get("/offline/?language=pl", HTTP_ACCEPT_LANGUAGE="ru")
        self.assertContains(response, "Teraz brak połączenia")
        self.assertEqual(response["Content-Language"], "pl")
        response = self.client.get("/manifest.webmanifest?language=pl")
        self.assertEqual(json.loads(response.content)["lang"], "pl")
        self.assertIn("Cookie", response["Vary"])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        source = self.client.get("/service-worker.js?language=pl").content.decode()
        self.assertIn("&language=pl", source)
        self.assertNotIn('"/api/', source)
        self.assertNotIn("cache.put(request", source)

    def test_browser_messages_keep_placeholders_and_russian_mode(self):
        result = subprocess.run(["node", str(Path(__file__).with_name("test_i18n.cjs"))], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_compiled_gettext_matches_reviewable_po_source(self):
        root = Path(settings.BASE_DIR) / "locale/pl/LC_MESSAGES"
        with (root / "django.mo").open("rb") as source:
            compiled = std_gettext.GNUTranslations(source)
        msgid, strings, current = None, {}, None
        entries = []
        for line in (root / "django.po").read_text().splitlines() + [""]:
            if not line:
                if msgid is not None:
                    entries.append((msgid, strings))
                msgid, strings, current = None, {}, None
            elif line.startswith("msgid "):
                msgid = ast.literal_eval(line[6:])
                current = "id"
            elif line.startswith("msgstr "):
                strings[0] = ast.literal_eval(line[7:]); current = 0
            elif line.startswith("msgstr["):
                index = int(line[7:line.index("]")])
                strings[index] = ast.literal_eval(line[line.index("]") + 2:]); current = index
            elif line.startswith('"') and current is not None:
                if current == "id":
                    msgid += ast.literal_eval(line)
                else:
                    strings[current] += ast.literal_eval(line)
        for message, translations in entries:
            if not message:
                continue
            self.assertTrue(translations, message)
            for index, translated in translations.items():
                self.assertTrue(translated, message)
                self.assertFalse(re.search("[А-Яа-яЁё]", translated), message)
                key = (message, index) if len(translations) > 1 else message
                self.assertEqual(compiled._catalog[key], translated, message)


class LocalizedLearningTests(TestCase):
    def test_shipped_course_metadata_has_polish_presentation(self):
        from polskiflow.learning.models import Course, Topic, Lesson
        with override("pl"):
            for model, fields in ((Course, ("title", "description")), (Topic, ("title", "description")),
                                  (Lesson, ("title", "plan_title", "subtitle", "description", "theory_title"))):
                for row in model.objects.values(*fields):
                    for value in row.values():
                        self.assertFalse(re.search("[А-Яа-яЁё]", str(ui_text(value))), value)

    def test_polish_search_finds_original_course_metadata_without_mutating_it(self):
        from polskiflow.catalog_search import search_learning_catalog
        from polskiflow.domain.course_catalog import filter_course_topics
        from polskiflow.learning.models import Topic
        original = Topic.objects.filter(title="Биография и опыт").first()
        self.assertIsNotNone(original)
        with override("pl"):
            result = search_learning_catalog("biografia")
            self.assertIn(original.id, [item["id"] for item in result["topics"]])
            topics = [{"id": original.id, "title": original.title, "description": original.description,
                       "lessons": [{"title": "Первый шаг", "description": "", "minutes": 5}]}]
            self.assertEqual(len(filter_course_topics(topics, query="biografia", localize=gettext)), 1)
        original.refresh_from_db()
        self.assertEqual(original.title, "Биография и опыт")

    @patch("polskiflow.account_views.delete_account")
    @patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("locale-delete-user", "delete@example.com"))
    def test_polish_delete_confirmation_keeps_password_check(self, authenticate, delete):
        self.client.cookies[ACCESS_COOKIE] = "test-access"
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "pl"
        response = self.client.post("/account/delete/", {"confirmation": "USUŃ"})
        self.assertContains(response, "Podaj bieżące hasło")
        delete.assert_not_called()
        response = self.client.post("/account/delete/", {"confirmation": "USUŃ", "current_password": "test-password"})
        self.assertEqual(response.status_code, 302)
        delete.assert_called_once()

    @patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("locale-user", "test@example.com"))
    def test_language_switch_keeps_signed_run_and_original_answers(self, authenticate):
        self.client.cookies[ACCESS_COOKIE] = "test-access"
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "ru"
        intro = self.client.get("/exam/b1/run/")
        token = intro.context["run_token"]
        started = self.client.post("/exam/b1/run/", {"run_token": token, "action": "start"})
        token, state = started.context["run_token"], started.context["state"]
        self.client.post("/language/", {"language": "pl", "next": "/exam/b1/run/"})
        restored = self.client.post("/exam/b1/run/", {"run_token": token, "action": "resume"})
        self.assertContains(restored, "Rozumienie ze słuchu")
        self.assertEqual(restored.context["state"], state)
        self.assertEqual(restored.context["run_token"], token)
        self.assertEqual(restored.context["questions"], started.context["questions"])
        self.assertEqual(restored["Cache-Control"], "private, no-store")

    def test_user_content_does_not_go_through_ui_translation(self):
        root = Path(settings.BASE_DIR) / "templates"
        for path in root.rglob("*.html"):
            for expression in re.findall(r"\{\{([^}]+)\}\}", path.read_text()):
                if re.search(r"display_name|\.body\b|\.message\b|\.name\b|\.translation\b", expression):
                    self.assertNotIn("|ui_text", expression, str(path))
