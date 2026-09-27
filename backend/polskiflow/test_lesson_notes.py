import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.lesson_note_store import LessonNote, load_lesson_note, save_lesson_note


@override_settings(SUPABASE_URL="https://project.supabase.co", SUPABASE_ANON_KEY="anon", SUPABASE_AUTH_TIMEOUT=2)
class LessonNoteStoreTests(TestCase):
    @patch("polskiflow.lesson_note_store.urlopen")
    def test_load_and_save_are_owner_scoped(self, urlopen):
        response = MagicMock(status=201)
        response.__enter__.return_value = response
        response.read.return_value = json.dumps([{"body": "  Moja zasada  ", "updated_at": "2026-09-26T08:00:00Z"}]).encode()
        urlopen.return_value = response
        self.assertEqual(load_lesson_note("token", "owner", "words").body, "  Moja zasada  ")
        self.assertIn("user_id=eq.owner", urlopen.call_args.args[0].full_url)
        self.assertIn("lesson_id=eq.words", urlopen.call_args.args[0].full_url)
        self.assertTrue(save_lesson_note("token", "owner", "words", "  Nowa zasada  "))
        request = urlopen.call_args.args[0]
        self.assertEqual(json.loads(request.data)["body"], "Nowa zasada")
        self.assertEqual(json.loads(request.data)["user_id"], "owner")

    @patch("polskiflow.lesson_note_store.urlopen")
    def test_blank_note_deletes_owner_row(self, urlopen):
        response = MagicMock(status=204)
        response.__enter__.return_value = response
        urlopen.return_value = response
        self.assertTrue(save_lesson_note("token", "owner", "words", "  "))
        request = urlopen.call_args.args[0]
        self.assertEqual(request.method, "DELETE")
        self.assertIn("user_id=eq.owner", request.full_url)

    def test_schema_has_owner_rls_explicit_grants_and_cascades(self):
        sql = (Path(__file__).parents[2] / "supabase/migrations/20260926092500_lesson_notes.sql").read_text()
        self.assertIn("enable row level security", sql)
        self.assertIn("revoke all on table public.lesson_notes from anon", sql)
        self.assertIn("with check ((select auth.uid()) = user_id)", sql)
        self.assertGreaterEqual(sql.count("on delete cascade"), 2)


class LessonNoteViewTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("11111111-1111-4111-8111-111111111111", "a@example.com"))
        auth.start()
        self.addCleanup(auth.stop)

    @patch("polskiflow.lesson_views.load_lesson_note", return_value=LessonNote(True, "Moja notatka"))
    @patch("polskiflow.lesson_views.load_lesson_bookmarks", return_value=set())
    @patch("polskiflow.lesson_views.load_lesson_draft", return_value=None)
    def test_lesson_shows_note_editor(self, _draft, _bookmarks, _note):
        response = self.client.get("/lesson/words/")
        self.assertContains(response, 'class="card content-tools"')
        self.assertContains(response, "Инструменты урока")
        self.assertContains(response, "Заметка к уроку")
        self.assertContains(response, "Moja notatka")

    @patch("polskiflow.lesson_views.load_lesson_note", return_value=LessonNote(True, ""))
    @patch("polskiflow.lesson_views.load_lesson_bookmarks", return_value=set())
    @patch("polskiflow.lesson_views.load_lesson_draft", return_value=None)
    def test_lesson_tools_open_after_note_action(self, _draft, _bookmarks, _note):
        response = self.client.get("/lesson/words/?note=saved")
        self.assertContains(response, 'class="card content-tools" open')
        self.assertContains(response, "Заметка сохранена")

    @patch("polskiflow.lesson_views.save_lesson_note", return_value=True)
    def test_save_uses_authenticated_owner(self, save):
        response = self.client.post("/lesson/words/note/", {"body": "  правило  "})
        self.assertRedirects(response, "/lesson/words/?note=saved#lesson-note", fetch_redirect_response=False)
        save.assert_called_once_with("access", "11111111-1111-4111-8111-111111111111", "words", "правило")

    def test_rejects_oversized_note_and_requires_auth(self):
        self.assertEqual(self.client.post("/lesson/words/note/", {"body": "x" * 2001}).status_code, 400)
        self.client.cookies.clear()
        self.assertEqual(self.client.post("/lesson/words/note/", {"body": "test"}).status_code, 302)
