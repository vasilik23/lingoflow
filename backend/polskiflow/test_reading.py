from unittest.mock import patch

from django.test import TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.learning.models import Course, ReadingText, Topic
from polskiflow.progress_store import DashboardProgress


class ReadingViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        course = Course.objects.create(
            id="test-reading-course", title="Тестовое чтение", level="A1"
        )
        short_topic = Topic.objects.create(
            id="test-reading-life", course=course, title="Повседневная жизнь"
        )
        long_topic = Topic.objects.create(
            id="test-reading-travel", course=course, title="Путешествия", position=1
        )
        ReadingText.objects.create(
            id="test-story",
            title="Krótka historia",
            description="Тестовый рассказ",
            level="A1",
            emoji="📖",
            paragraphs=["Ala ma kota. Kot lubi mleko."],
            glossary={
                "kota": {
                    "lemma": "kot",
                    "translation": "кот",
                    "part_of_speech": "существительное",
                },
                "lubi": {
                    "lemma": "lubić",
                    "translation": "любить",
                    "part_of_speech": "глагол",
                },
                "mleko": "молоко",
            },
            topic=short_topic,
        )
        ReadingText.objects.create(
            id="test-long-story",
            title="Długa podróż",
            description="Opowieść kolejowa",
            level="A1",
            minutes=12,
            paragraphs=["Pociąg jedzie daleko."],
            glossary={},
            topic=long_topic,
            position=3,
        )
        ReadingText.objects.create(
            id="test-story-a2", title="Historia A2", description="Уровень A2",
            level="A2", paragraphs=["To jest A2."], glossary={}, position=1,
        )
        ReadingText.objects.create(
            id="test-story-fallback", title="Historia bez poziomu",
            description="Резервный уровень", level="", paragraphs=["Tekst."],
            glossary={}, position=2,
        )

    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        self.auth_patch = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser(
                "00000000-0000-0000-0000-000000000123", "reader@example.com"
            ),
        )
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)
        self.news_patch = patch(
            "polskiflow.reading_views.latest_official_news", return_value=[]
        )
        self.news_mock = self.news_patch.start()
        self.addCleanup(self.news_patch.stop)

    @patch("polskiflow.reading_views.load_reading_bookmarks", return_value={"test-story"})
    def test_library_can_filter_saved_texts(self, _bookmarks):
        response = self.client.get("/reading/?level=A1&saved=1")
        self.assertContains(response, "Krótka historia")
        self.assertNotContains(response, "Długa podróż")
        self.assertContains(response, "Krótka historia ★")

    @patch("polskiflow.reading_views.set_reading_bookmark", return_value=True)
    def test_bookmark_write_is_csrf_protected_and_owner_scoped(self, save):
        response = self.client.post("/reading/test-story/bookmark/", {"saved": "1"})
        self.assertRedirects(response, "/reading/test-story/", fetch_redirect_response=False)
        save.assert_called_once_with(
            "access", "00000000-0000-0000-0000-000000000123", "test-story", True
        )

    def test_library_lists_active_texts(self):
        response = self.client.get("/reading/")

        self.assertContains(response, "Krótka historia")
        self.assertContains(response, "Historia bez poziomu")
        self.assertNotContains(response, "Historia A2")
        self.assertContains(response, "Тестовый рассказ")
        self.assertNotContains(response, "Свежие новости</h2>")
        self.assertContains(response, 'href="/news/">Свежие новости →</a>')
        self.assertNotContains(response, 'href="/dictionary/">Мой словарь →</a>')
        self.assertContains(response, 'aria-label="Уровень учебных текстов"')
        self.assertContains(response, 'href="?level=A1#texts-title" aria-current="page"')

    def test_library_filters_texts_by_level_and_falls_back_to_a1(self):
        response = self.client.get("/reading/?level=A2")

        self.assertContains(response, "Historia A2")
        self.assertNotContains(response, "Krótka historia")
        self.assertContains(response, 'href="?level=A2#texts-title" aria-current="page"')

        response = self.client.get("/reading/?level=unknown")
        self.assertContains(response, "Krótka historia")
        self.assertContains(response, 'href="?level=A1#texts-title" aria-current="page"')

    @patch("polskiflow.reading_views.load_dashboard_progress")
    def test_library_defaults_to_profile_level(self, mocked_progress):
        mocked_progress.return_value = DashboardProgress(
            display_name="Czytelnik",
            level="A2",
            streak_days=0,
            completed_lesson_ids=frozenset(),
            available=True,
        )

        response = self.client.get("/reading/")

        self.assertContains(response, "Historia A2")
        self.assertNotContains(response, "Krótka historia")
        self.assertContains(response, 'href="?level=A2#texts-title" aria-current="page"')

    @patch("polskiflow.reading_views.load_dashboard_progress")
    def test_library_explicit_level_overrides_profile_level(self, mocked_progress):
        mocked_progress.return_value = DashboardProgress(
            display_name="Czytelnik",
            level="A2",
            streak_days=0,
            completed_lesson_ids=frozenset(),
            available=True,
        )

        response = self.client.get("/reading/?level=A1")

        self.assertContains(response, "Krótka historia")
        self.assertNotContains(response, "Historia A2")

    @patch("polskiflow.reading_views.load_dashboard_progress")
    def test_library_invalid_level_falls_back_to_profile_level(self, mocked_progress):
        mocked_progress.return_value = DashboardProgress(
            display_name="Czytelnik",
            level="A2",
            streak_days=0,
            completed_lesson_ids=frozenset(),
            available=True,
        )

        response = self.client.get("/reading/?level=unknown")

        self.assertContains(response, "Historia A2")
        self.assertContains(response, 'href="?level=A2#texts-title" aria-current="page"')

    def test_legacy_reading_news_category_redirects_to_news_tab(self):
        response = self.client.get("/reading/?category=sport")

        self.assertRedirects(response, "/news/?category=sport", fetch_redirect_response=False)
        self.news_mock.assert_not_called()

    def test_news_tab_filters_by_allowlisted_category(self):
        response = self.client.get("/news/?category=sport")

        self.assertEqual(response.status_code, 200)
        self.news_mock.assert_called_with(category="sport")
        self.assertContains(response, 'href="?category=sport#news-title" aria-current="page"')
        self.assertContains(response, 'href="/dictionary/">Мой словарь →</a>')
        self.assertNotContains(response, 'href="/reading/">Учебные тексты →</a>')

        self.client.get("/news/?category=not-a-category")
        self.news_mock.assert_called_with(category=None)

    def test_library_searches_local_text_titles_and_descriptions(self):
        response = self.client.get("/reading/?level=A1&q=KOLEJOWA")

        self.assertContains(response, "Długa podróż")
        self.assertNotContains(response, "Krótka historia")
        self.assertContains(response, "Найдено учебных текстов: <strong>1</strong>")
        self.news_mock.assert_not_called()

    def test_library_filters_by_topic_and_duration(self):
        response = self.client.get(
            "/reading/?level=A1&topic=test-reading-life&duration=short"
        )

        self.assertContains(response, "Krótka historia")
        self.assertNotContains(response, "Długa podróż")
        self.assertContains(response, '<option value="test-reading-life" selected>')
        self.assertContains(response, '<option value="short" selected>')

    def test_library_keeps_search_filters_in_level_navigation(self):
        response = self.client.get(
            "/reading/?level=A1&q=historia&topic=test-reading-life"
            "&duration=short"
        )

        self.news_mock.assert_not_called()
        self.assertContains(response, "Krótka historia")
        self.assertContains(
            response,
            'href="?level=A2&amp;q=historia&amp;topic=test-reading-life&amp;duration=short#texts-title"',
        )

    def test_news_tab_has_navigation_state_and_source_attribution(self):
        self.news_mock.return_value = [{
            "title": "Wiadomość dnia",
            "url": "https://example.com/news",
            "source": "Przykład",
            "published": "1 września",
            "category": "politics",
            "category_label": "Политика",
        }]

        response = self.client.get("/news/")

        self.assertContains(response, "Новости на польском")
        self.assertContains(response, "Wiadomość dnia")
        self.assertContains(response, "Przykład")
        self.assertContains(response, 'target="_blank" rel="noopener noreferrer"')
        self.assertContains(response, 'href="/reading/" class="nav-link active"')
        self.assertNotContains(response, '<span>Новости</span>')
        self.assertContains(response, 'href="/reading/">Учебные тексты</a>')

    def test_news_tab_preserves_unavailable_feed_behavior(self):
        response = self.client.get("/news/")

        self.assertContains(response, "Лента временно недоступна")
        self.assertContains(response, "Читать учебные тексты")

    def test_library_ignores_unknown_reading_filters(self):
        response = self.client.get(
            "/reading/?level=A1&topic=unknown&duration=week"
        )

        self.assertContains(response, "Krótka historia")
        self.assertContains(response, "Długa podróż")
        self.assertNotContains(response, "Подходящих текстов не найдено")

    def test_reader_marks_only_glossary_words_as_interactive(self):
        response = self.client.get("/reading/test-story/")

        self.assertContains(response, 'data-word="kota"')

    def test_reader_offers_private_system_speech_controls(self):
        response = self.client.get("/reading/test-story/")

        self.assertContains(response, "Послушай текст по-польски")
        self.assertContains(response, 'data-audio-play')
        self.assertContains(response, "SpeechSynthesisUtterance")
        self.assertContains(response, "pl-PL")
        self.assertNotContains(response, "audio src=")

    def test_reader_links_saved_words_to_sm2_practice(self):
        response = self.client.get("/reading/test-story/")

        self.assertContains(response, "Закрепи сохранённую лексику")
        self.assertContains(
            response,
            'href="/dictionary/practice/?source=test-story&amp;mode=lemma"',
        )

    @patch("polskiflow.reading_views.load_collection_summaries", return_value=[{"id": "11111111-1111-4111-8111-111111111112", "name": "Czytanie"}])
    def test_reader_exposes_owned_collection_picker(self, load_collections):
        response = self.client.get("/reading/test-story/")
        self.assertContains(response, 'class="card content-tools reader-tools"')
        self.assertContains(response, "Сохранить и организовать")
        self.assertContains(response, 'id="reading-collection-select"')
        self.assertContains(response, "Czytanie")
        self.assertContains(response, 'action="/collections/add/reading/test-story/"')
        load_collections.assert_called_once_with(
            "access", "00000000-0000-0000-0000-000000000123"
        )

        open_response = self.client.get("/reading/test-story/?collection=added")
        self.assertContains(open_response, 'class="card content-tools reader-tools" open')
        self.assertContains(response, 'data-lemma="kot"')
        self.assertContains(response, 'data-translation="кот"')
        self.assertContains(response, 'data-part-of-speech="существительное"')
        self.assertContains(response, 'class="reader-word"', count=3)

    @patch("polskiflow.reading_views.save_personal_word", return_value=True)
    def test_glossary_word_can_be_saved(self, save_word):
        response = self.client.post(
            "/reading/test-story/save/",
            {"word": "KOTA", "translation": "кот", "context": "Ala ma kota."},
            headers={"HX-Request": "true"},
        )

        self.assertContains(response, "теперь в словаре")
        self.assertContains(
            response,
            'href="/dictionary/practice/?source=test-story&amp;mode=lemma"',
        )
        save_word.assert_called_once_with(
            "access",
            "00000000-0000-0000-0000-000000000123",
            "kot",
            "кот",
            "Ala ma kota.",
            "test-story",
        )

    @patch("polskiflow.reading_views.save_personal_word", return_value=True)
    def test_glossary_save_redirects_to_full_reader_without_htmx(self, _save_word):
        response = self.client.post(
            "/reading/test-story/save/",
            {"word": "kota", "translation": "кот", "context": "Ala ma kota."},
        )

        self.assertRedirects(
            response,
            "/reading/test-story/?word=saved#dictionary-status",
            fetch_redirect_response=False,
        )
        page = self.client.get(response["Location"])
        self.assertContains(page, "Слово добавлено в словарь")
        self.assertContains(page, 'method="post" action="/reading/test-story/save/"')

    @patch("polskiflow.reading_views.save_personal_word", return_value=True)
    def test_legacy_glossary_value_still_saves_surface_form(self, save_word):
        response = self.client.post(
            "/reading/test-story/save/",
            {"word": "mleko", "translation": "молоко", "context": "Kot lubi mleko."},
            headers={"HX-Request": "true"},
        )

        self.assertEqual(response.status_code, 200)
        save_word.assert_called_once_with(
            "access",
            "00000000-0000-0000-0000-000000000123",
            "mleko",
            "молоко",
            "Kot lubi mleko.",
            "test-story",
        )

    @patch("polskiflow.reading_views.save_personal_word")
    def test_unknown_translation_is_rejected(self, save_word):
        response = self.client.post(
            "/reading/test-story/save/",
            {"word": "kota", "translation": "подменённый перевод"},
        )

        self.assertEqual(response.status_code, 400)
        save_word.assert_not_called()

    @patch("polskiflow.reading_views.load_personal_words")
    def test_dictionary_lists_user_words(self, load_words):
        load_words.return_value = [
            {
                "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "word": "mleko",
                "translation": "молоко",
                "context": "Kot lubi mleko.",
            }
        ]

        response = self.client.get("/dictionary/")

        self.assertContains(response, "mleko")
        self.assertContains(response, "молоко")

    @patch("polskiflow.reading_views.load_personal_words")
    def test_dictionary_searches_lemma_translation_and_context(self, load_words):
        load_words.return_value = [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "word": "pociąg",
                "translation": "поезд",
                "context": "Pociąg jedzie do Gdańska.",
                "next_review_date": "2999-01-01",
            },
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "word": "dom",
                "translation": "дом",
                "context": "Wracam wieczorem.",
                "next_review_date": "2999-01-01",
            },
        ]

        for query in ("POCIĄG", "поезд", "gdańska"):
            with self.subTest(query=query):
                response = self.client.get("/dictionary/", {"q": query})
                self.assertContains(response, "pociąg")
                self.assertNotContains(response, ">dom<")
                self.assertContains(response, "Найдено слов:")
                self.assertContains(response, "<strong>1</strong>", html=True)

    @patch("polskiflow.reading_views.load_personal_words")
    def test_dictionary_filters_words_by_sm2_due_status(self, load_words):
        load_words.return_value = [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "word": "dziś",
                "translation": "сегодня",
                "context": "",
                "next_review_date": "2000-01-01",
            },
            {
                "id": "22222222-2222-2222-2222-222222222222",
                "word": "jutro",
                "translation": "завтра",
                "context": "",
                "next_review_date": "2999-01-01",
            },
        ]

        due = self.client.get("/dictionary/?review=due")
        self.assertContains(due, "dziś")
        self.assertNotContains(due, ">jutro<")
        upcoming = self.client.get("/dictionary/?review=upcoming")
        self.assertContains(upcoming, "jutro")
        self.assertNotContains(upcoming, ">dziś<")

    @patch("polskiflow.reading_views.load_personal_words")
    def test_dictionary_validates_filters_and_caps_query(self, load_words):
        load_words.return_value = []

        response = self.client.get("/dictionary/", {"q": "x" * 100, "review": "other"})

        self.assertEqual(response.context["dictionary_query"], "x" * 80)
        self.assertEqual(response.context["review_filter"], "")

    @patch("polskiflow.reading_views.load_personal_words")
    def test_dictionary_has_filtered_empty_state_without_hiding_practice(self, load_words):
        load_words.return_value = [
            {
                "id": f"00000000-0000-0000-0000-{index:012d}",
                "word": f"word-{index}",
                "translation": "перевод",
                "context": "",
            }
            for index in range(4)
        ]

        response = self.client.get("/dictionary/?q=missing")

        self.assertContains(response, "Ничего не найдено")
        self.assertContains(response, "▶ Тренировать")
        self.assertNotContains(response, "Словарь пока пуст")

    def test_unknown_text_returns_404(self):
        self.assertEqual(self.client.get("/reading/no-story/").status_code, 404)

    def test_a2_reader_links_to_comprehension_activity(self):
        response = self.client.get("/reading/weekend-kasi-i-pawla/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Проверь понимание текста")
        self.assertContains(response, "5 вопросов · A2")
        self.assertContains(response, 'href="/lesson/weekend-reading-check/"')

        activity = self.client.get("/lesson/weekend-reading-check/")
        self.assertContains(activity, "Dokąd Kasia pojechała po pracy?")
        self.assertContains(activity, "Do Wrocławia")

    def test_travel_reader_links_to_its_comprehension_activity(self):
        response = self.client.get("/reading/plan-wyjazdu-do-gdanska/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/lesson/travel-reading-check/"')
        activity = self.client.get("/lesson/travel-reading-check/")
        self.assertContains(activity, "Kiedy Marta i Kuba wyjadą z Krakowa?")
        self.assertContains(activity, "W piątek wieczorem")

    def test_housing_reader_links_to_its_comprehension_activity(self):
        response = self.client.get("/reading/usterka-w-mieszkaniu/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/lesson/housing-reading-check/"')
        activity = self.client.get("/lesson/housing-reading-check/")
        self.assertContains(activity, "Jaki problem zauważyła Lena?")
        self.assertContains(activity, "Nie działało ogrzewanie")

    def test_work_reader_links_to_its_comprehension_activity(self):
        response = self.client.get("/reading/pierwszy-tydzien-mai/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/lesson/a2work-reading-check/"')
        activity = self.client.get("/lesson/a2work-reading-check/")
        self.assertContains(activity, "Gdzie zaczęła pracować Maja?")

    def test_returns_reader_links_to_comprehension_activity(self):
        response = self.client.get("/reading/reklamacja-natalii/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/lesson/returns-reading-check/"')
        activity = self.client.get("/lesson/returns-reading-check/")
        self.assertContains(activity, "Dlaczego Natalia wróciła do sklepu?")

    def test_medical_reader_links_to_comprehension_activity(self):
        response = self.client.get("/reading/adam-u-lekarza-i-w-aptece/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/lesson/med-reading-check/"')
        activity = self.client.get("/lesson/med-reading-check/")
        self.assertContains(activity, "Jak długo Adam miał objawy?")

    def test_relationships_reader_links_to_comprehension_activity(self):
        response = self.client.get("/reading/szczera-rozmowa-marty-i-ani/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/lesson/rel-reading-check/"')
        self.assertContains(response, 'data-word="przyjaźnią"')
        activity = self.client.get("/lesson/rel-reading-check/")
        self.assertContains(activity, "Dlaczego Marta była rozczarowana?")

    def test_culture_reader_links_to_comprehension_activity(self):
        response = self.client.get("/reading/wieczor-krotkich-filmow/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/lesson/culture-reading-check/"')
        self.assertContains(response, 'data-word="reżyserów"')
        activity = self.client.get("/lesson/culture-reading-check/")
        self.assertContains(activity, "Na jakie wydarzenie poszli Lena i Paweł?")

    def test_institutions_reader_links_to_comprehension_activity(self):
        response = self.client.get("/reading/natalia-sklada-wniosek/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/lesson/office-reading-check/"')
        self.assertContains(response, 'data-word="ważności"')
        activity = self.client.get("/lesson/office-reading-check/")
        self.assertContains(activity, "Po co Natalia przyszła do urzędu?")

    def test_weather_reader_links_to_comprehension_activity(self):
        response = self.client.get("/reading/weather-wycieczka-przed-burza/")
        self.assertContains(response, 'href="/lesson/weather-reading-check/"')
        self.assertContains(response, 'data-word="wzgórza"')
        activity = self.client.get("/lesson/weather-reading-check/")
        self.assertContains(activity, "Dokąd pojechali Lena i Kuba?")

    def test_poland_reader_links_to_comprehension_activity(self):
        response = self.client.get("/reading/poland-maja-odkrywa-torun/")
        self.assertContains(response, 'href="/lesson/poland-reading-check/"')
        self.assertContains(response, 'data-word="przewodniczką"')
        activity = self.client.get("/lesson/poland-reading-check/")
        self.assertContains(activity, "Dokąd pojechała grupa Mai?")

    def test_final_a2_reader_links_to_comprehension_activity(self):
        response = self.client.get("/reading/a2final-weekend-leny/")
        self.assertContains(response, 'href="/lesson/a2final-reading-check/"')
        self.assertContains(response, 'data-word="kłótni"')
        activity = self.client.get("/lesson/a2final-reading-check/")
        self.assertContains(activity, "Dlaczego Lena pojechała do Torunia?")

    def test_b1_biography_reader_links_to_comprehension_activity(self):
        response = self.client.get("/reading/bio-droga-joanny/")
        self.assertContains(response, 'href="/lesson/bio-reading-check/"')
        self.assertContains(response, 'data-word="dorastała"')
        activity = self.client.get("/lesson/bio-reading-check/")
        self.assertContains(activity, "Gdzie dorastała Joanna?")

    def test_b1_travel_reader_links_to_comprehension_activity(self):
        response = self.client.get("/reading/b1trip-nieplanowana-przesiadka/")
        self.assertContains(response, 'href="/lesson/b1trip-reading-check/"')
        self.assertContains(response, 'data-word="zdążą"')
        activity = self.client.get("/lesson/b1trip-reading-check/")
        self.assertContains(activity, "Dokąd jechali Marta i Paweł?")

    @patch("polskiflow.reading_views.load_personal_words")
    def test_practice_builds_quiz_from_personal_words(self, load_words):
        load_words.return_value = self._practice_words()

        response = self.client.get("/dictionary/practice/")

        self.assertContains(response, "Выбери перевод")
        self.assertContains(response, "dom")
        self.assertContains(response, "дом")
        self.assertContains(response, "молоко")

    @patch("polskiflow.reading_views.load_personal_words")
    def test_reader_practice_asks_for_lemma_and_scopes_questions_to_text(
        self, load_words
    ):
        words = self._practice_words()
        words[0]["source_text_id"] = "test-story"
        load_words.return_value = words

        response = self.client.get(
            "/dictionary/practice/?source=test-story&mode=lemma"
        )

        self.assertContains(response, "Выбери польскую лемму")
        self.assertContains(response, ">дом<")
        self.assertContains(response, ">dom<")
        self.assertContains(response, "Слово 1 из 1")
        self.assertNotContains(response, ">молоко<")
        self.assertEqual(
            self.client.session["dictionary_practice_word_ids"], ["word-1"]
        )

    @patch("polskiflow.reading_views.load_personal_words")
    def test_reader_practice_has_honest_empty_state_for_unsaved_text(
        self, load_words
    ):
        load_words.return_value = self._practice_words()

        response = self.client.get("/dictionary/practice/?source=test-story")

        self.assertContains(response, "Слова этого текста ещё не сохранены")
        self.assertContains(response, "добавь их в личный словарь")

    @patch("polskiflow.reading_views.load_personal_words")
    def test_reader_practice_keeps_sm2_due_filter(self, load_words):
        words = self._practice_words()
        words[0].update(
            source_text_id="test-story", next_review_date="2999-01-01"
        )
        load_words.return_value = words

        response = self.client.get("/dictionary/practice/?source=test-story")

        self.assertContains(response, "На сегодня всё")
        self.assertNotContains(response, "Выбери польскую лемму")

    def test_reader_practice_rejects_unknown_source(self):
        response = self.client.get("/dictionary/practice/?source=unknown-story")

        self.assertEqual(response.status_code, 404)

    @patch("polskiflow.reading_views.save_personal_word_review", return_value=True)
    @patch("polskiflow.reading_views.save_lesson_completion", return_value=True)
    @patch("polskiflow.reading_views.load_personal_words")
    def test_reader_practice_preserves_scoped_mode_and_updates_sm2(
        self, load_words, _save_completion, save_review
    ):
        words = self._practice_words()
        words[0]["source_text_id"] = "test-story"
        load_words.return_value = words
        session = self.client.session
        session["dictionary_practice_word_ids"] = ["word-1"]
        session["dictionary_practice_mode"] = "lemma"
        session["dictionary_practice_source"] = "test-story"
        session.save()

        response = self.client.post(
            "/dictionary/practice/step/",
            {
                "action": "next",
                "index": 0,
                "score": 0,
                "selected": 0,
                "quality": "good",
            },
        )

        self.assertContains(
            response,
            'href="/dictionary/practice/?source=test-story&amp;mode=lemma"',
        )
        self.assertEqual(save_review.call_args.args[2], "word-1")
        self.assertEqual(save_review.call_args.args[3].repetitions, 1)

    @patch("polskiflow.reading_views.load_personal_words")
    def test_practice_requires_four_distinct_translations(self, load_words):
        load_words.return_value = self._practice_words()[:3]

        response = self.client.get("/dictionary/practice/")

        self.assertContains(response, "Нужно минимум 4 слова")
        self.assertContains(response, "Сейчас в словаре: 3")

    @patch("polskiflow.reading_views.load_personal_words")
    def test_practice_answer_shows_feedback(self, load_words):
        load_words.return_value = self._practice_words()

        response = self.client.post(
            "/dictionary/practice/step/",
            {"action": "answer", "index": 0, "score": 0, "choice": 0},
        )

        self.assertContains(response, "Верно!")
        self.assertContains(response, "Насколько легко вспомнилось слово?")
        self.assertContains(response, "Трудно")
        self.assertContains(response, "<!doctype html>")
        self.assertContains(response, "Режим тренировки")

    @patch("polskiflow.reading_views.load_personal_words")
    def test_htmx_practice_step_still_returns_only_fragment(self, load_words):
        load_words.return_value = self._practice_words()

        response = self.client.post(
            "/dictionary/practice/step/",
            {"action": "answer", "index": 0, "score": 0, "choice": 0},
            headers={"HX-Request": "true"},
        )

        self.assertContains(response, "Верно!")
        self.assertNotContains(response, "<!doctype html>")
        self.assertNotContains(response, "Режим тренировки")

    @patch("polskiflow.reading_views.load_personal_words")
    def test_context_practice_accepts_typed_lemma_case_insensitively(self, load_words):
        load_words.return_value = self._practice_words()
        start = self.client.get("/dictionary/practice/?mode=context")
        self.assertContains(start, "В контексте")
        self.assertContains(start, "To jest _____")
        self.assertContains(start, 'name="answer"')

        response = self.client.post(
            "/dictionary/practice/step/",
            {"action": "answer", "index": 0, "score": 0, "answer": " DOM "},
        )
        self.assertContains(response, "Верно!")
        self.assertContains(response, "Насколько легко вспомнилось слово?")

    @patch("polskiflow.reading_views.save_personal_word_review", return_value=True)
    @patch("polskiflow.reading_views.load_personal_words")
    def test_wrong_typed_answer_forces_again_schedule(self, load_words, save_review):
        load_words.return_value = self._practice_words()
        self.client.get("/dictionary/practice/?mode=context")
        self.client.post(
            "/dictionary/practice/step/",
            {"action": "answer", "index": 0, "score": 0, "answer": "okno"},
        )
        response = self.client.post(
            "/dictionary/practice/step/",
            {"action": "next", "index": 0, "score": 0, "quality": "easy"},
        )
        self.assertEqual(response.status_code, 200)
        result = save_review.call_args.args[3]
        self.assertEqual(result.repetitions, 0)
        self.assertEqual(result.interval_days, 1)

    @patch("polskiflow.reading_views.load_personal_words")
    def test_context_practice_works_with_one_due_word(self, load_words):
        words = self._practice_words()
        for word in words[1:]:
            word["next_review_date"] = "2999-01-01"
        load_words.return_value = words
        response = self.client.get("/dictionary/practice/?mode=context")
        self.assertContains(response, "Слово 1 из 1")

    @patch("polskiflow.reading_views.save_personal_word_review", return_value=True)
    @patch("polskiflow.reading_views.save_lesson_completion", return_value=True)
    @patch("polskiflow.reading_views.load_personal_words")
    def test_practice_completion_is_saved(
        self, load_words, save_completion, save_review
    ):
        load_words.return_value = self._practice_words()

        response = self.client.post(
            "/dictionary/practice/step/",
            {
                "action": "next",
                "index": 3,
                "score": 3,
                "selected": 3,
                "quality": "easy",
            },
        )

        self.assertContains(response, "4 / 4")
        self.assertContains(response, "Результат добавлен")
        save_completion.assert_called_once_with(
            "access",
            "00000000-0000-0000-0000-000000000123",
            "dictionary-practice",
            4,
            4,
        )
        self.assertEqual(save_review.call_args.args[2], "word-4")
        self.assertEqual(save_review.call_args.args[3].repetitions, 1)
        self.assertEqual(save_review.call_args.args[3].ease_factor, 2.6)

    @patch("polskiflow.reading_views.save_personal_word_review", return_value=True)
    @patch("polskiflow.reading_views.load_personal_words")
    def test_wrong_answer_forces_again_schedule(self, load_words, save_review):
        load_words.return_value = self._practice_words()

        response = self.client.post(
            "/dictionary/practice/step/",
            {
                "action": "next",
                "index": 0,
                "score": 0,
                "selected": 1,
                "quality": "easy",
            },
        )

        self.assertEqual(response.status_code, 200)
        result = save_review.call_args.args[3]
        self.assertEqual(result.repetitions, 0)
        self.assertEqual(result.interval_days, 1)

    @patch("polskiflow.reading_views.load_personal_words")
    def test_practice_selects_only_due_words(self, load_words):
        words = self._practice_words()
        words[0]["next_review_date"] = "2999-01-01"
        load_words.return_value = words

        response = self.client.get("/dictionary/practice/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, ">dom<")
        self.assertContains(response, "Слово 1 из 3")

    @patch("polskiflow.reading_views.load_personal_words")
    def test_practice_reports_when_no_words_are_due(self, load_words):
        words = self._practice_words()
        for word in words:
            word["next_review_date"] = "2999-01-01"
        load_words.return_value = words

        response = self.client.get("/dictionary/practice/")

        self.assertContains(response, "На сегодня всё")

    @staticmethod
    def _practice_words():
        return [
            {"id": "word-1", "word": "dom", "translation": "дом", "context": "To jest dom."},
            {"id": "word-2", "word": "mleko", "translation": "молоко", "context": "Lubię mleko."},
            {"id": "word-3", "word": "chleb", "translation": "хлеб", "context": "Jem chleb."},
            {"id": "word-4", "word": "okno", "translation": "окно", "context": "Otwieram okno."},
        ]


class B1NewReadingRoutesTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        self.auth_patch = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser(
                "00000000-0000-0000-0000-000000000123", "reader@example.com"
            ),
        )
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)

    def test_new_b1_readings_link_to_their_comprehension_lessons(self):
        expectations = (
            ("b1rel-weekend-na-dwa-sposoby", "b1rel-reading-check"),
            ("b1health-maly-krok-kuby", "b1health-reading-check"),
            ("b1media-wiadomosc-ktora-wymagala-sprawdzenia", "b1media-reading-check"),
            ("b1culture-wieczor-z-ksiazka-i-filmem", "b1culture-reading-check"),
            ("b1soc-sasiedzki-ogrod", "b1soc-reading-check"),
            ("b1eco-rzeka-wraca-do-miasta", "b1eco-reading-check"),
            ("b1region-dwa-spojrzenia-na-beskid", "b1region-reading-check"),
            ("b1final-projekt-marty", "b1final-reading-check"),
        )
        for reading_id, lesson_id in expectations:
            with self.subTest(reading_id=reading_id):
                response = self.client.get(f"/reading/{reading_id}/")
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'href="/lesson/{lesson_id}/"')
                self.assertContains(response, "Добавить в словарь")
