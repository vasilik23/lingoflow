from unittest.mock import patch

from django.test import TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.lesson_state import sign_lesson_state
from polskiflow.learning.models import Course, Flashcard, Lesson, LessonFlashcard, Question, Topic
from polskiflow.progress_store import CompletionSaveResult, DashboardProgress


class LessonViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Lesson.objects.all().delete()
        Flashcard.objects.all().delete()
        course = Course.objects.create(id="lesson-test-course", title="A1", level="A1")
        topic = Topic.objects.create(id="lesson-test-topic", course=course, title="Основы")
        lesson_data = [
            ("words", "Słówka dnia", "Новые слова"),
            ("grammar", "Gramatyka", "Грамматика"),
            ("review", "Powtórka", "Повторение"),
            ("quiz", "Quiz", "Мини-тест"),
        ]
        for position, (lesson_id, title, plan_title) in enumerate(lesson_data):
            Lesson.objects.create(
                id=lesson_id,
                topic=topic,
                kind=lesson_id,
                title=title,
                plan_title=plan_title,
                subtitle="5 заданий",
                description="Описание",
                position=position,
                theory_title="Rodzajnik i ród rzeczownika" if lesson_id == "grammar" else "",
                theory_sections=[["Род существительных", "Короткая теория"]] if lesson_id == "grammar" else [],
            )
        cards = [
            ("czesc", "cześć", "привет"),
            ("dziekuje", "dziękuję", "спасибо"),
            ("prosze", "proszę", "пожалуйста"),
            ("tak", "tak", "да"),
            ("nie", "nie", "нет"),
        ]
        for position, (card_id, polish, translation) in enumerate(cards):
            card = Flashcard.objects.create(id=card_id, polish=polish, translation=translation, position=position)
            LessonFlashcard.objects.create(
                lesson_id="words", flashcard=card, position=position
            )
        review_card = Flashcard.objects.create(
            id="jestem", polish="jestem", translation="я есть", position=5
        )
        LessonFlashcard.objects.create(
            lesson_id="review", flashcard=review_card, position=0
        )
        grammar_prompts = ["Слово «kawa»", "Слово «dom»", "Слово «miasto»"]
        for position, prompt in enumerate(grammar_prompts):
            Question.objects.create(lesson_id="grammar", prompt=prompt, options=["мужской", "женский", "средний"], correct=position % 3, explanation="Пояснение", position=position)
        Question.objects.create(
            lesson_id="grammar",
            prompt="Составьте: Марек работает сегодня дома.",
            options=[
                "Marek dzisiaj pracuje w domu.",
                "Marek pracuje dzisiaj w domu.",
                "Dzisiaj dom Marek w pracuje.",
            ],
            correct=1,
            explanation="Нейтральный порядок: подлежащее, сказуемое, время и место.",
            position=3,
        )
        quiz_prompts = ["Как переводится «cześć»?", "Что значит «dziękuję»?", "Выберите перевод", "Как будет «да»?", "Как будет «нет»?"]
        for position, prompt in enumerate(quiz_prompts):
            Question.objects.create(lesson_id="quiz", prompt=prompt, options=["нет", "привет", "спасибо"], correct=1, explanation="Cześć — неформальное «привет».", position=position)
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        self.auth_patch = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser("user-123", "learner@example.com"),
        )
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)

    def lesson_state(self, lesson_id, index=0, score=0, phase="ready"):
        return sign_lesson_state("user-123", lesson_id, lesson_id, index, score, phase)

    def test_home_combines_daily_goal_with_default_fifteen_minute_plan(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Цель на сегодня")
        self.assertContains(response, "Начать занятия")
        self.assertContains(response, 'role="progressbar"')
        self.assertContains(response, 'aria-label="Выполнение цели на сегодня"')
        self.assertContains(response, 'aria-valuenow="0"')
        self.assertContains(response, "Задания на сегодня")
        self.assertContains(response, 'aria-label="Длительность плана"')
        self.assertContains(response, 'href="?minutes=15#daily-plan" aria-current="page"')
        self.assertContains(response, "Słówka dnia")
        self.assertContains(response, "Gramatyka")
        self.assertContains(response, "Powtórka")
        self.assertNotContains(response, "Quiz")
        self.assertEqual(len(response.context["tasks"]), 3)

    @patch("polskiflow.auth_views.load_latest_lesson_draft", return_value={"lesson_id": "quiz", "step_index": 2})
    def test_home_discovers_latest_unfinished_lesson(self, _draft):
        response = self.client.get("/")
        self.assertContains(response, "Незавершённый урок")
        self.assertContains(response, "продолжим с шага 3")
        self.assertContains(response, 'href="/lesson/quiz/">Продолжить')

    @patch("polskiflow.auth_views.load_dashboard_progress")
    @patch("polskiflow.auth_views.load_latest_lesson_draft", return_value={"lesson_id": "quiz", "step_index": 2})
    def test_home_hides_stale_draft_for_completed_lesson(self, _draft, progress):
        progress.return_value = DashboardProgress("Learner", "A1", 1, frozenset({"quiz"}), True, all_completed_lesson_ids=frozenset({"quiz"}))
        response = self.client.get("/")
        self.assertNotContains(response, "Незавершённый урок")

    def test_legacy_tasks_url_redirects_to_home_plan(self):
        response = self.client.get("/tasks/?source=bookmark")

        self.assertRedirects(
            response,
            "/?source=bookmark#daily-tasks",
            fetch_redirect_response=False,
        )

    def test_listening_pilot_scores_public_domain_clips(self):
        page = self.client.get("/listening/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Узнай слово на слух")
        self.assertContains(page, "polskiflow/audio/tecza.ogg")
        self.assertContains(page, "polskiflow/audio/wrobel.ogg")
        self.assertContains(page, "polskiflow/audio/mysz.ogg")
        self.assertContains(page, "public domain")
        self.assertContains(page, "Текстовая альтернатива записи 1")
        self.assertContains(page, '<span lang="pl">tęcza</span>')

        result = self.client.post(
            "/listening/", {"tecza": "tęcza", "wrobel": "wybór", "mysz": "mysz"}
        )
        self.assertEqual(result.status_code, 200)
        self.assertContains(result, "2 / 3")
        self.assertContains(result, "Правильный ответ")
        self.assertContains(result, "wróbel")

    def test_listening_pilot_includes_original_dialogue_with_accessible_controls(self):
        page = self.client.get("/listening/")

        self.assertContains(page, "Встреча перед поездкой")
        self.assertContains(page, "Cześć, Aniu!")
        self.assertContains(page, "текстовую альтернативу")
        self.assertContains(page, "data-dialogue-rate")
        self.assertContains(page, "data-dialogue-repeat")
        self.assertContains(page, "системный польский голос браузера")

        result = self.client.post(
            "/listening/",
            {
                "tecza": "tęcza",
                "wrobel": "wróbel",
                "mysz": "mysz",
                "dialogue_main": "Встретиться перед поездкой в Краков",
                "dialogue_detail": "В поезде",
            },
        )
        self.assertContains(result, "1 / 2")
        self.assertContains(result, "Перед кассой номер три")
        self.assertContains(result, "Они уточняют поезд, время и место встречи")

    def test_listening_pilot_includes_original_b1_speech_with_permanent_transcript(self):
        page = self.client.get("/listening/")

        self.assertContains(page, "Zmiana planu sąsiedzkiego spotkania")
        self.assertContains(page, 'aria-label="Постоянный транскрипт B1"')
        self.assertContains(page, "Ponieważ prognoza zapowiada silny deszcz")
        self.assertContains(page, "data-b1-play")
        self.assertContains(page, "systemowy głos", count=0)
        self.assertContains(page, "это не студийная запись")

        result = self.client.post(
            "/listening/",
            {
                "tecza": "tęcza",
                "wrobel": "wróbel",
                "mysz": "mysz",
                "b1_listening_reason": "Из-за прогноза сильного дождя",
                "b1_listening_plan": "Распределение задач на пикнике",
                "b1_listening_action": "Подтвердить участие",
            },
        )
        self.assertContains(result, "2 / 3")
        self.assertContains(result, "Новый детский игровой комплекс")
        self.assertContains(result, "Слово «najpierw» вводит первый пункт встречи")

    def test_listening_pilot_includes_original_b2_speech_with_permanent_transcript(self):
        page = self.client.get("/listening/")

        self.assertContains(page, "Pilotaż pracy hybrydowej")
        self.assertContains(page, 'aria-label="Постоянный транскрипт B2"')
        self.assertContains(page, "Choć część zespołu proponowała całkowitą pracę zdalną")
        self.assertContains(page, "data-b2-play")
        self.assertContains(page, "не студийная запись")

        result = self.client.post(
            "/listening/",
            {
                "tecza": "tęcza",
                "wrobel": "wróbel",
                "mysz": "mysz",
                "b2_listening_model": "Гибридный формат в течение трёх месяцев",
                "b2_listening_tuesday": "Для индивидуальных собеседований",
                "b2_listening_decision": "На результатах анонимного опроса",
            },
        )
        self.assertContains(result, "2 / 3")
        self.assertContains(result, "Для совместного планирования проектов")
        self.assertContains(result, "Оборот «żeby wspólnie planować projekty»")

    def test_practice_hub_collects_optional_training_modes(self):
        page = self.client.get("/course/?level=A1")
        self.assertContains(page, 'href="/practice/"')
        self.assertNotContains(page, "Аудиопилот A1")
        hub = self.client.get("/practice/")
        self.assertContains(hub, "Практика без лишнего")
        self.assertContains(hub, 'class="practice-hub-card', count=7)
        self.assertContains(hub, "Подготовка к B1")
        self.assertContains(hub, "Аналитика обучения")
        for href in ("/exam/b1/", "/dictionary/practice/", "/listening/", "/writing/", "/interaction/", "/diagnostic/", "/history/"):
            self.assertContains(hub, f'href="{href}"')

    def test_course_marks_one_topic_for_compact_mobile_catalog(self):
        response = self.client.get("/course/?level=A1")
        topic_count = len(response.context["course_topics"])

        self.assertGreater(topic_count, 0)
        self.assertContains(response, '<details class="topic-card"', count=topic_count)
        self.assertContains(response, 'data-course-topic-primary="true"', count=1)
        self.assertContains(response, "Показать уроки", count=topic_count)

    def test_home_keeps_daily_plan_focused_and_course_page_lists_topics(self):
        course = Course.objects.create(id="catalog-test", title="A1", level="A1")
        topic = Topic.objects.create(id="catalog-topic", course=course, title="Новая тема")
        extra = Lesson.objects.create(id="extra-lesson", topic=topic, title="Extra", plan_title="Extra", subtitle="A1", description="Каталог", position=5)

        response = self.client.get("/?minutes=30")

        self.assertContains(response, "0 из 4")
        self.assertNotContains(response, "Новая тема")
        self.assertContains(response, "Задания на сегодня")

        course_page = self.client.get("/course/")
        self.assertContains(course_page, "Новая тема")
        self.assertContains(course_page, extra.title)

    def test_course_catalog_separates_topics_by_cefr_level(self):
        a2_course = Course.objects.create(
            id="a2-catalog-test", title="A2", level="A2", position=2
        )
        a2_topic = Topic.objects.create(
            id="a2-catalog-topic", course=a2_course, title="Прошедшие выходные"
        )
        Lesson.objects.create(
            id="a2-extra-lesson",
            topic=a2_topic,
            title="Miniony weekend",
            plan_title="Weekend",
            subtitle="A2",
            description="Прошедшее время",
            position=50,
        )

        a1_page = self.client.get("/course/")
        self.assertContains(a1_page, 'aria-label="Уровни курса"')
        self.assertContains(a1_page, 'href="?level=A1" aria-current="page"')
        self.assertNotContains(a1_page, "Miniony weekend")

        a2_page = self.client.get("/course/?level=A2")
        self.assertContains(a2_page, 'href="?level=A2" aria-current="page"')
        self.assertContains(a2_page, "1 тема")
        self.assertContains(a2_page, "Прошедшие выходные")
        self.assertContains(a2_page, "Miniony weekend")
        self.assertNotContains(a2_page, "Новая тема")

    def test_course_catalog_falls_back_to_a1_for_unknown_level(self):
        response = self.client.get("/course/?level=Z9")
        self.assertContains(response, 'href="?level=A1" aria-current="page"')

    def test_course_catalog_searches_topics_and_lessons(self):
        by_topic = self.client.get("/course/?level=A1&q=основы")
        self.assertContains(by_topic, "Słówka dnia")
        self.assertContains(by_topic, "1 тема · 4 урока")

        by_lesson = self.client.get("/course/?level=A1&q=Gramatyka")
        self.assertContains(by_lesson, "Gramatyka")
        self.assertNotContains(by_lesson, "Słówka dnia")
        self.assertContains(by_lesson, "1 тема · 1 урок")

        missing = self.client.get("/course/?level=A1&q=несуществующее")
        self.assertContains(missing, "Ничего не найдено")
        self.assertContains(missing, 'href="?level=A1">Сбросить фильтры</a>')

    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_course_catalog_filters_kind_duration_and_completion(self, mocked_progress):
        Lesson.objects.filter(id="grammar").update(minutes=15)
        mocked_progress.return_value = DashboardProgress(
            display_name="Василий",
            level="A1",
            streak_days=0,
            completed_lesson_ids=frozenset(),
            available=True,
            all_completed_lesson_ids=frozenset({"grammar"}),
        )

        response = self.client.get(
            "/course/?level=A1&kind=grammar&duration=medium&completion=completed"
        )

        self.assertContains(response, "Gramatyka")
        self.assertNotContains(response, "Słówka dnia")
        self.assertContains(response, 'option value="grammar" selected')
        self.assertContains(response, 'option value="medium" selected')
        self.assertContains(response, 'option value="completed" selected')

        not_started = self.client.get("/course/?level=A1&completion=not-started")
        self.assertNotContains(not_started, "Gramatyka")
        self.assertContains(not_started, "Słówka dnia")

    def test_course_catalog_ignores_invalid_filter_values(self):
        response = self.client.get(
            "/course/?level=A1&topic=missing&kind=video&duration=week&completion=maybe"
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Słówka dnia")
        self.assertEqual(response.context["catalog_filters"]["topic"], "")
        self.assertEqual(response.context["catalog_filters"]["kind"], "")

    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_course_catalog_defaults_to_profile_level(self, mocked_progress):
        mocked_progress.return_value = DashboardProgress(
            display_name="Василий",
            level="A2",
            streak_days=0,
            completed_lesson_ids=frozenset(),
            available=True,
        )

        response = self.client.get("/course/")

        self.assertContains(response, 'href="?level=A2" aria-current="page"')

    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_course_catalog_explicit_level_overrides_profile_level(self, mocked_progress):
        mocked_progress.return_value = DashboardProgress(
            display_name="Василий",
            level="A2",
            streak_days=0,
            completed_lesson_ids=frozenset(),
            available=True,
        )

        response = self.client.get("/course/?level=A1")

        self.assertContains(response, 'href="?level=A1" aria-current="page"')

    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_course_catalog_invalid_level_falls_back_to_profile_level(self, mocked_progress):
        mocked_progress.return_value = DashboardProgress(
            display_name="Василий",
            level="A2",
            streak_days=0,
            completed_lesson_ids=frozenset(),
            available=True,
        )

        response = self.client.get("/course/?level=Z9")

        self.assertContains(response, 'href="?level=A2" aria-current="page"')

    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_course_catalog_invalid_profile_level_falls_back_to_a1(self, mocked_progress):
        mocked_progress.return_value = DashboardProgress(
            display_name="Василий",
            level="Z9",
            streak_days=0,
            completed_lesson_ids=frozenset(),
            available=True,
        )

        response = self.client.get("/course/")

        self.assertContains(response, 'href="?level=A1" aria-current="page"')

    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_course_topic_shows_all_time_progress_and_next_lesson(self, mocked_progress):
        mocked_progress.return_value = DashboardProgress(
            display_name="Василий",
            level="A1",
            streak_days=4,
            completed_lesson_ids=frozenset(),
            available=True,
            all_completed_lesson_ids=frozenset({"words", "grammar"}),
        )

        response = self.client.get("/course/")

        self.assertContains(response, "2 / 4 уроков")
        self.assertContains(response, 'aria-label="Прогресс темы «Основы»"')
        self.assertContains(response, 'aria-valuenow="2"')
        self.assertContains(response, 'href="/lesson/review/">Продолжить')

    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_course_topic_shows_completed_status(self, mocked_progress):
        mocked_progress.return_value = DashboardProgress(
            display_name="Василий",
            level="A1",
            streak_days=4,
            completed_lesson_ids=frozenset(),
            available=True,
            all_completed_lesson_ids=frozenset(
                {"words", "grammar", "review", "quiz"}
            ),
        )

        response = self.client.get("/course/")

        self.assertContains(response, "4 / 4 уроков")
        self.assertContains(response, "Все уроки пройдены")
        self.assertNotContains(response, 'href="/lesson/words/">Продолжить')

    def test_user_menu_contains_logout(self):
        response = self.client.get("/")
        content = response.content.decode()

        self.assertContains(response, "Открыть меню пользователя")
        self.assertContains(response, 'class="user-menu app-user-menu"')
        self.assertContains(response, 'action="/logout/"')
        self.assertContains(response, 'href="/profile/"')
        self.assertContains(response, 'class="user-menu-group"', count=2)
        self.assertContains(response, "Учёба и материалы")
        self.assertContains(response, "Настройки и помощь")
        self.assertGreater(content.index("</nav>"), content.index('class="nav-links"'))
        self.assertLess(content.index("</nav>"), content.index('class="user-menu app-user-menu"'))

    def test_primary_navigation_promotes_practice(self):
        home = self.client.get("/")
        practice = self.client.get("/practice/")

        self.assertContains(home, 'href="/practice/" class="nav-link ')
        self.assertContains(home, "<span>Практика</span>", html=True)
        self.assertNotContains(home, '<span>Новости</span>')
        self.assertContains(practice, 'href="/practice/" class="nav-link active"')

    def test_base_template_offers_persisted_accessible_theme_selection(self):
        response = self.client.get("/")

        self.assertContains(response, 'data-theme-select')
        self.assertContains(response, 'aria-label="Цветовая тема"')
        self.assertContains(response, 'value="system"')
        self.assertContains(response, 'value="light"')
        self.assertContains(response, 'value="dark"')
        self.assertContains(response, 'localStorage.setItem(theme.storageKey')
        self.assertContains(response, 'prefers-color-scheme: dark')

    def test_base_template_has_no_render_blocking_external_font(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "fonts.googleapis.com")
        self.assertNotContains(response, "fonts.gstatic.com")

    def test_base_template_has_no_external_javascript_runtime(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "cdn.jsdelivr.net")
        self.assertNotContains(response, "unpkg.com")
        self.assertNotContains(response, "hx-post")

    def test_base_template_has_keyboard_skip_link_and_main_target(self):
        response = self.client.get("/")

        self.assertContains(response, 'class="skip-link" href="#main-content"')
        self.assertContains(response, 'id="main-content"')
        self.assertContains(response, 'tabindex="-1"')

    @patch("polskiflow.auth_views.load_reminder_preferences", return_value={"daily_reminder_enabled": False, "reminder_time": "19:00", "timezone": "Europe/Warsaw"})
    @patch("polskiflow.auth_views.load_personal_words")
    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_profile_shows_identity_progress_and_settings(
        self, mocked_progress, mocked_words, _mocked_reminders
    ):
        mocked_progress.return_value = DashboardProgress(
            display_name="Василий",
            level="A2",
            streak_days=4,
            completed_lesson_ids=frozenset({"words"}),
            available=True,
            all_completed_lesson_ids=frozenset({"words", "grammar"}),
            active_days=7,
            weekly_active_days=4,
            weekly_completed_count=6,
            previous_week_active_days=2,
            previous_week_completed_count=3,
            daily_goal_lessons=2,
            recent_daily_completion_counts=(2,) * 14 + (0,) * 14,
        )
        mocked_words.return_value = [{"word": "dom"}, {"word": "dzień"}]

        response = self.client.get("/profile/")
        self.assertContains(response, "Недельная активность")
        self.assertContains(response, "Месячный обзор")
        self.assertContains(response, "6")
        self.assertContains(response, "4 / 7")
        self.assertContains(response, "на 3 больше")
        self.assertContains(response, "на 2 больше")
        self.assertContains(response, "В прошлый период: 3 уроков за 2 активных дней")
        self.assertContains(response, "Насколько подходит нагрузка")
        self.assertContains(response, "14 / 28")
        self.assertContains(response, "50%")
        self.assertContains(response, "Нагрузка выглядит посильной")
        self.assertContains(response, "это ориентир, а не оценка")
        self.assertContains(response, 'data-goal-status="sustainable"')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Василий")
        self.assertContains(response, "learner@example.com")
        self.assertContains(response, "2 / 4")
        self.assertContains(response, "50%")
        self.assertContains(response, "7")
        self.assertContains(response, "слов в словаре")
        self.assertContains(response, "Достижения")
        self.assertContains(response, "Первый шаг")
        self.assertContains(response, "Три дня подряд")
        self.assertContains(response, "4 / 7")
        self.assertContains(response, 'aria-label="Неделя в ритме"')
        self.assertContains(response, "Настройки")
        self.assertContains(response, 'role="progressbar"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'name="display_name"')
        self.assertContains(response, 'name="level"')
        self.assertContains(response, "Сохранить профиль")
        self.assertContains(response, "плане на день, курсе и библиотеке")
        self.assertNotContains(response, "Сейчас используется светлая тема")
        self.assertNotContains(response, 'class="settings-list"')
        self.assertContains(response, "Напоминания")
        self.assertContains(response, "ещё ничего не отправляем")
        self.assertContains(response, 'name="daily_reminder_enabled"')
        self.assertNotContains(response, 'name="daily_reminder_enabled" type="checkbox" checked')

    @patch("polskiflow.auth_views.save_reminder_preferences", return_value=True)
    @patch("polskiflow.auth_views.load_reminder_preferences", return_value={"daily_reminder_enabled": False, "reminder_time": "19:00", "timezone": "Europe/Warsaw"})
    @patch("polskiflow.auth_views.load_personal_words", return_value=[])
    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_profile_explicitly_opts_into_daily_reminder(self, mocked_progress, _words, _load, save):
        mocked_progress.return_value = DashboardProgress("Learner", "A1", 0, frozenset(), True)

        response = self.client.post("/profile/", {
            "form_action": "reminders",
            "daily_reminder_enabled": "on",
            "reminder_time": "08:30",
        })

        self.assertEqual(response.status_code, 200)
        save.assert_called_once_with("access", "user-123", True, "08:30", "Europe/Warsaw")
        self.assertContains(response, "Настройки напоминаний сохранены")
        self.assertContains(response, 'name="daily_reminder_enabled" type="checkbox" checked')

    @patch("polskiflow.auth_views.save_reminder_preferences")
    @patch("polskiflow.auth_views.load_reminder_preferences", return_value={"daily_reminder_enabled": False, "reminder_time": "19:00", "timezone": "Europe/Warsaw"})
    @patch("polskiflow.auth_views.load_personal_words", return_value=[])
    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_profile_rejects_invalid_reminder_time(self, mocked_progress, _words, _load, save):
        mocked_progress.return_value = DashboardProgress("Learner", "A1", 0, frozenset(), True)

        response = self.client.post("/profile/", {"form_action": "reminders", "reminder_time": "25:90"})

        self.assertContains(response, "Укажите корректное время напоминания")
        save.assert_not_called()

    def test_profile_requires_authentication(self):
        self.auth_patch.stop()
        self.client.cookies.clear()

        response = self.client.get("/profile/")

        self.assertRedirects(response, "/login/?next=%2Fprofile%2F", fetch_redirect_response=False)

    def test_course_keeps_optional_practice_out_of_topic_catalog(self):
        response = self.client.get("/course/?level=B1")
        self.assertNotContains(response, "Письменная практика B1")
        self.assertNotContains(response, "Договорись и передай смысл")
        self.assertContains(response, 'href="/practice/"')

    def test_writing_practice_has_local_drafts_and_honest_self_check(self):
        response = self.client.get("/writing/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Письменные ответы")
        self.assertContains(response, "не оценивает грамотность, уровень или качество ответа")
        self.assertContains(response, 'data-writing-draft="formal-request"')
        self.assertContains(response, "Самопроверка для этого жанра", count=7)
        self.assertContains(response, "Я указал причину отсутствия, просьбу о материалах и новый срок.")
        self.assertContains(response, "История показывает исходный план, неожиданное изменение, реакцию и итог.")
        self.assertContains(response, '<label><input type="checkbox">', count=28)
        self.assertContains(response, 'localStorage.setItem(key, textarea.value)')
        self.assertContains(response, 'window.confirm("Удалить черновик этого задания?')
        self.assertContains(response, "Проверить по критериям", count=7)
        self.assertContains(response, 'data-min-words="80"')
        self.assertContains(response, 'data-min-paragraphs="2"')
        self.assertContains(response, 'data-markers="proszę|termin"')
        self.assertContains(response, "Это техническая подсказка, а не оценка преподавателя")
        self.assertContains(response, "Что обязательно раскрыть", count=7)
        self.assertContains(response, "Разбор после черновика", count=7)
        self.assertContains(response, "Показать пример ответа после своей попытки", count=7)
        self.assertContains(response, "E-mail formalny")
        self.assertContains(response, "Opowiadanie")
        self.assertContains(response, "Gratulacje")
        self.assertContains(response, "Ogłoszenie")
        self.assertContains(response, "Opis osoby")
        self.assertContains(response, "7 заданий")
        self.assertContains(response, "data-writing-requirement>", count=21)
        self.assertContains(response, "data-writing-error value=", count=28)
        self.assertContains(response, 'localStorage.setItem(reviewKey, JSON.stringify(checked))')
        self.assertContains(response, "Персональное закрепление")
        self.assertContains(response, "data-writing-focus-list")
        self.assertContains(response, "updateFocusSummary();", count=3)
        self.assertContains(response, 'data-writing-href="/lesson/bio-grammar/"')
        self.assertContains(response, 'data-writing-href="/lesson/b1work-grammar/"')
        self.assertContains(response, "Открыть урок:")
        self.assertContains(response, 'href="/course/?level=B1&kind=grammar"')
        self.assertContains(response, "Это один возможный ответ")

    def test_writing_practice_supports_b2_and_separates_local_storage(self):
        response = self.client.get("/writing/?level=B2")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Практика B2")
        self.assertContains(response, "Сравнение двух сообщений")
        self.assertContains(response, "Я сопоставил оба сообщения, а не пересказал их по очереди.")
        self.assertContains(response, "Я отделил обсуждавшиеся предложения от окончательно принятых решений.")
        self.assertContains(response, '<label><input type="checkbox">', count=16)
        self.assertContains(response, 'data-writing-draft="source-comparison"')
        self.assertContains(response, "polskiflow-writing-b2:")
        self.assertContains(response, 'href="?level=B2" aria-current="page"')
        self.assertContains(response, "4 заданий")

    def test_b1_writing_examples_respect_their_own_word_limits(self):
        from polskiflow.auth_views import WRITING_PROMPTS

        for prompt in WRITING_PROMPTS["B1"]:
            word_count = len(prompt["sample_answer"].split())
            self.assertGreaterEqual(word_count, prompt["min_words"], prompt["id"])
            self.assertLessEqual(word_count, int(prompt["task"].split("–", 1)[1].split()[0]), prompt["id"])

    def test_writing_practice_falls_back_to_b1_for_unknown_level(self):
        response = self.client.get("/writing/?level=C1")

        self.assertContains(response, "Практика B1")
        self.assertNotContains(response, "Сравнение двух сообщений")

    def test_writing_practice_requires_authentication(self):
        self.auth_patch.stop()
        self.client.cookies.clear()

        response = self.client.get("/writing/")

        self.assertRedirects(response, "/login/?next=%2Fwriting%2F", fetch_redirect_response=False)

    @patch("polskiflow.auth_views.save_profile_settings", return_value=True)
    @patch("polskiflow.auth_views.load_personal_words", return_value=[])
    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_profile_updates_name_and_level(
        self, mocked_progress, _mocked_words, mocked_save
    ):
        mocked_progress.return_value = DashboardProgress(
            "learner", "A1", 0, frozenset(), True
        )

        response = self.client.post(
            "/profile/", {"display_name": "  Анна  ", "level": "b1", "daily_goal_lessons": "6"}
        )

        self.assertEqual(response.status_code, 200)
        mocked_save.assert_called_once_with("access", "user-123", "Анна", "B1", 6)
        self.assertContains(response, "Профиль сохранён")
        self.assertContains(response, "Анна")
        self.assertContains(response, 'value="B1" selected')

    @patch("polskiflow.auth_views.save_profile_settings")
    @patch("polskiflow.auth_views.load_personal_words", return_value=[])
    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_profile_rejects_invalid_name_and_level(
        self, mocked_progress, _mocked_words, mocked_save
    ):
        mocked_progress.return_value = DashboardProgress(
            "learner", "A1", 0, frozenset(), True
        )

        empty_name = self.client.post(
            "/profile/", {"display_name": " ", "level": "A2"}
        )
        invalid_level = self.client.post(
            "/profile/", {"display_name": "Анна", "level": "C3"}
        )
        invalid_goal = self.client.post(
            "/profile/", {"display_name": "Анна", "level": "A2", "daily_goal_lessons": "11"}
        )

        self.assertContains(empty_name, "Укажите имя")
        self.assertContains(invalid_level, "Выберите уровень от A1 до C2")
        self.assertContains(invalid_goal, "Цель должна быть от 1 до 10")
        mocked_save.assert_not_called()

    @patch("polskiflow.auth_views.load_personal_words", return_value=[])
    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_course_catalog_offers_c2_and_profile_can_select_it(self, mocked_progress, _words):
        mocked_progress.return_value = DashboardProgress(
            "Learner", "C2", 0, frozenset(), True
        )

        course_response = self.client.get("/course/")
        profile_response = self.client.get("/profile/")

        self.assertContains(course_response, "Траектория A1 → C2")
        self.assertContains(course_response, 'href="?level=C2"')
        self.assertContains(profile_response, '<option value="C2" selected>')

    @patch("polskiflow.auth_views.save_profile_settings", return_value=False)
    @patch("polskiflow.auth_views.load_personal_words", return_value=[])
    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_profile_reports_store_failure(
        self, mocked_progress, _mocked_words, _mocked_save
    ):
        mocked_progress.return_value = DashboardProgress(
            "learner", "A1", 0, frozenset(), True
        )

        response = self.client.post(
            "/profile/", {"display_name": "Анна", "level": "A2"}
        )

        self.assertContains(response, "Не удалось сохранить профиль")
        self.assertContains(response, 'value="A2" selected')

    def test_sources_explains_original_content_feeds_and_references(self):
        response = self.client.get("/sources/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "создаются специально для PolskiFlow")
        self.assertContains(response, "Внешние новостные ленты")
        self.assertContains(response, "Główny Urząd Statystyczny")
        self.assertContains(response, "RMF24")
        self.assertContains(response, "Polsat Sport")
        self.assertContains(response, "Лингвистические и методические ориентиры")
        self.assertContains(response, "Wielki słownik języka polskiego PAN")
        self.assertContains(response, "не копируем статьи")

    def test_sources_is_publicly_available(self):
        self.auth_patch.stop()
        self.client.cookies.clear()

        response = self.client.get("/sources/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Источники и лицензии")

    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_home_marks_today_progress(self, mocked_progress):
        mocked_progress.return_value = DashboardProgress(
            display_name="Василий",
            level="A2",
            streak_days=4,
            completed_lesson_ids=frozenset({"words", "grammar"}),
            available=True,
        )

        response = self.client.get("/?minutes=30")

        self.assertContains(response, "Cześć, Василий!")
        self.assertContains(response, "Уровень A2")
        self.assertContains(response, "4 дн. подряд")
        self.assertContains(response, "2 из 4")

        self.assertContains(response, 'class="task-complete"', count=2)

    @patch("polskiflow.auth_views.load_personal_words", return_value=[])
    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_home_keeps_a_newly_completed_lesson_in_daily_progress(
        self, mocked_progress, _mocked_words
    ):
        mocked_progress.return_value = DashboardProgress(
            display_name="Василий",
            level="A1",
            streak_days=1,
            completed_lesson_ids=frozenset({"words"}),
            available=True,
            all_completed_lesson_ids=frozenset({"words"}),
        )

        home = self.client.get("/?minutes=30")
        self.assertContains(home, "1 из 4")
        self.assertContains(home, "25%")
        self.assertContains(home, "1 из 4 выполнено")
        self.assertContains(home, 'class="task-complete"', count=1)

    @patch("polskiflow.auth_views.load_personal_words")
    @patch("polskiflow.auth_views.load_dashboard_progress")
    def test_daily_plan_includes_due_dictionary_review(
        self, mocked_progress, mocked_words
    ):
        mocked_progress.return_value = DashboardProgress(
            display_name="Василий",
            level="A1",
            streak_days=1,
            completed_lesson_ids=frozenset(),
            available=True,
        )
        mocked_words.return_value = [
            {
                "id": str(index),
                "word": f"word-{index}",
                "translation": f"слово-{index}",
                "next_review_date": "2026-01-01" if index == 0 else "2999-01-01",
            }
            for index in range(4)
        ]

        response = self.client.get("/")

        self.assertContains(response, "Повторение словаря")
        self.assertContains(response, "1 слово по расписанию SM-2")
        self.assertContains(response, 'href="/dictionary/practice/"')
        self.assertEqual(len(response.context["tasks"]), 3)
        self.assertLessEqual(response.context["plan_estimated_minutes"], 15)

    def test_unknown_lesson_returns_404(self):
        self.assertEqual(self.client.get("/lesson/unknown/").status_code, 404)

    @patch("polskiflow.lesson_views.load_lesson_draft", return_value={"lesson_kind": "quiz", "step_index": 2, "score": 1})
    def test_lesson_resumes_valid_owner_scoped_draft(self, load):
        response = self.client.get("/lesson/quiz/")
        self.assertContains(response, "Продолжаем с сохранённого шага")
        self.assertContains(response, "Вопрос 3 из 5")
        load.assert_called_once_with("access", "user-123", "quiz")

    @patch("polskiflow.lesson_views.save_lesson_draft")
    def test_advancing_lesson_saves_next_step(self, save):
        response = self.client.post("/lesson/quiz/step/", {
            "action": "next", "state": self.lesson_state("quiz", 0, 1, "answered"), "selected": 1,
            "index": 4, "score": 4,
        })
        self.assertContains(response, "Вопрос 2 из 5")
        save.assert_called_once_with("access", "user-123", "quiz", "quiz", 1, 1)

    def test_signed_state_cannot_be_replayed_for_another_lesson(self):
        response = self.client.post("/lesson/grammar/step/", {
            "action": "start", "state": self.lesson_state("quiz"),
        })
        self.assertEqual(response.status_code, 400)

    @patch("polskiflow.lesson_views.delete_lesson_draft")
    def test_completed_lesson_clears_draft(self, delete):
        self.client.post("/lesson/quiz/step/", {"action": "next", "state": self.lesson_state("quiz", 4, 4, "answered"), "selected": 1})
        delete.assert_called_once_with("access", "user-123", "quiz")

    def test_flashcard_can_be_revealed_and_completed(self):
        revealed = self.client.post(
            "/lesson/words/step/", {"action": "reveal", "state": self.lesson_state("words")}
        )
        self.assertContains(revealed, "привет")

        response = None
        for index in range(5):
            response = self.client.post(
                "/lesson/words/step/",
                {"action": "know", "state": self.lesson_state("words", index, index)},
            )
        self.assertContains(response, "5 / 5")
        self.assertContains(response, "Урок завершён")
        self.assertContains(response, "Следующий урок темы")
        self.assertContains(response, 'href="/lesson/grammar/"', count=2)
        self.assertContains(response, "Вернуться к плану")

    def test_lesson_forms_work_as_html_without_htmx(self):
        page = self.client.get("/lesson/words/")
        self.assertContains(page, 'method="post" action="/lesson/words/step/"')

        response = self.client.post(
            "/lesson/words/step/",
            {"action": "reveal", "state": self.lesson_state("words")},
        )
        self.assertContains(response, "<!doctype html>")
        self.assertContains(response, "привет")
        self.assertContains(response, "Инструменты урока")

    def test_htmx_lesson_step_still_returns_only_flow_fragment(self):
        response = self.client.post(
            "/lesson/words/step/",
            {"action": "reveal", "state": self.lesson_state("words")},
            headers={"HX-Request": "true"},
        )
        self.assertContains(response, "привет")
        self.assertNotContains(response, "<!doctype html>")
        self.assertNotContains(response, "Инструменты урока")

    def test_final_topic_lesson_returns_to_its_course_topic(self):
        response = self.client.post(
            "/lesson/quiz/step/",
            {"action": "next", "state": self.lesson_state("quiz", 4, 4, "answered"), "selected": 1},
        )

        self.assertContains(response, "Тема завершена")
        self.assertContains(response, "Основы")
        self.assertContains(
            response,
            'href="/course/?level=A1#topic-lesson-test-topic"',
        )
        self.assertNotContains(response, "Продолжить тему")

    @patch("polskiflow.lesson_views.save_lesson_completion_result")
    def test_words_transient_failure_exposes_token_free_offline_handoff(self, mocked_save):
        mocked_save.return_value = CompletionSaveResult(saved=False, retryable=True)

        response = self.client.post(
            "/lesson/words/step/",
            {"action": "know", "state": self.lesson_state("words", 4, 4)},
            headers={"HX-Request": "true"},
        )

        self.assertContains(response, "data-lesson-result-sync")
        self.assertContains(response, "data-sync-retry")
        self.assertContains(response, '&quot;lesson_id&quot;:&quot;words&quot;')
        self.assertNotContains(response, "user-123")
        self.assertNotContains(response, "learner@example.com")
        self.assertNotContains(response, "access_token")

    @patch("polskiflow.lesson_views.save_lesson_completion_result")
    def test_quiz_transient_failure_joins_controlled_offline_pilot(self, mocked_save):
        mocked_save.return_value = CompletionSaveResult(saved=False, retryable=True)

        response = self.client.post(
            "/lesson/quiz/step/",
            {"action": "next", "state": self.lesson_state("quiz", 4, 4, "answered"), "selected": 1},
            headers={"HX-Request": "true"},
        )

        self.assertContains(response, "data-lesson-result-sync")
        self.assertContains(response, '&quot;lesson_id&quot;:&quot;quiz&quot;')
        self.assertNotContains(response, "access_token")

    @patch("polskiflow.lesson_views.save_lesson_completion_result")
    def test_grammar_transient_failure_joins_controlled_offline_pilot(self, mocked_save):
        mocked_save.return_value = CompletionSaveResult(saved=False, retryable=True)

        response = self.client.post(
            "/lesson/grammar/step/",
            {
                "action": "next",
                "state": self.lesson_state("grammar", 3, 2, "answered"),
                "answer_order": "[0,1,2,3,4]",
            },
            headers={"HX-Request": "true"},
        )

        self.assertContains(response, "data-lesson-result-sync")
        self.assertContains(response, '&quot;lesson_id&quot;:&quot;grammar&quot;')
        self.assertContains(response, '&quot;cards_total&quot;:4')
        self.assertNotContains(response, "user-123")
        self.assertNotContains(response, "learner@example.com")
        self.assertNotContains(response, "access_token")

    @patch("polskiflow.lesson_views.save_lesson_completion_result")
    def test_review_transient_failure_joins_controlled_offline_pilot(self, mocked_save):
        mocked_save.return_value = CompletionSaveResult(saved=False, retryable=True)

        response = self.client.post(
            "/lesson/review/step/",
            {"action": "know", "state": self.lesson_state("review")},
            headers={"HX-Request": "true"},
        )

        self.assertContains(response, "data-lesson-result-sync")
        self.assertContains(response, '&quot;lesson_id&quot;:&quot;review&quot;')
        self.assertNotContains(response, "access_token")

    @patch("polskiflow.lesson_views.save_lesson_completion_result")
    def test_permanent_words_failure_is_not_queued(self, mocked_save):
        mocked_save.return_value = CompletionSaveResult(saved=False, retryable=False)

        response = self.client.post(
            "/lesson/words/step/",
            {"action": "know", "state": self.lesson_state("words", 4, 4)},
        )

        self.assertNotContains(response, "data-lesson-result-sync")

    def test_quiz_answer_shows_explanation_and_next_question(self):
        answered = self.client.post(
            "/lesson/quiz/step/",
            {"action": "answer", "state": self.lesson_state("quiz"), "choice": 1},
        )
        self.assertContains(answered, "Cześć — неформальное")
        next_question = self.client.post(
            "/lesson/quiz/step/",
            {"action": "next", "state": self.lesson_state("quiz", 0, 1, "answered"), "selected": 1},
        )
        self.assertContains(next_question, "Что значит")

    def test_grammar_theory_starts_exercises(self):
        page = self.client.get("/lesson/grammar/")
        self.assertContains(page, "Род существительных")
        exercise = self.client.post(
            "/lesson/grammar/step/", {"action": "start", "state": self.lesson_state("grammar")}
        )
        self.assertContains(exercise, "Слово «kawa»")

    def test_grammar_sentence_builder_is_accessible_and_server_validated(self):
        question = self.client.post(
            "/lesson/grammar/step/",
            {"action": "next", "state": self.lesson_state("grammar", 2, 1, "answered"), "selected": 2},
        )
        self.assertContains(question, "Составь предложение")
        self.assertContains(question, "data-sentence-builder")
        self.assertContains(question, 'type="button" class="sentence-token"')
        self.assertContains(question, "Сбросить")
        self.assertContains(question, "Проверить")

        missing_word = self.client.post(
            "/lesson/grammar/step/",
            {"action": "answer", "state": self.lesson_state("grammar", 3, 0), "answer_order": "[0]"},
        )
        self.assertEqual(missing_word.status_code, 400)

        question_context = question.context
        shuffled = question_context["builder_tokens"]
        correct_words = "Marek pracuje dzisiaj w domu.".split()
        correct_order = [shuffled.index(word) for word in correct_words]
        answered = self.client.post(
            "/lesson/grammar/step/",
            {
                "action": "answer",
                "state": self.lesson_state("grammar", 3, 0),
                "answer_order": __import__("json").dumps(correct_order),
            },
        )
        self.assertContains(answered, "Верно")
        self.assertContains(answered, "Нейтральный порядок")

        tampered_next = self.client.post(
            "/lesson/grammar/step/",
            {"action": "next", "state": self.lesson_state("grammar", 3, 0, "answered"), "answer_order": "[0, 0, 1, 2, 3]"},
        )
        self.assertEqual(tampered_next.status_code, 400)

    def test_review_uses_only_its_linked_flashcards(self):
        page = self.client.get("/lesson/review/")

        self.assertContains(page, "jestem")
        self.assertContains(page, "Карточка 1 из 1")
        self.assertNotContains(page, "cześć")

    def test_invalid_lesson_state_is_rejected(self):
        response = self.client.post(
            "/lesson/quiz/step/",
            {"action": "answer", "state": "tampered", "choice": 0},
        )
        self.assertEqual(response.status_code, 400)
