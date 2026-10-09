from datetime import date

from django.test import SimpleTestCase

from polskiflow.domain.daily_plan import build_daily_plan


class DailyPlanTests(SimpleTestCase):
    def test_minutes_override_legacy_lesson_cap_and_keep_completed_work(self):
        lessons = [{"id": str(i), "kind": "words", "level": "A1", "minutes": 5} for i in range(8)]
        plan = build_daily_plan(lessons, level="A1", completed_all_time=frozenset({"0"}), completed_today=frozenset({"0"}), personal_words=[], today=date(2026, 10, 7), daily_task_limit=1, time_budget_minutes=30)
        self.assertEqual(len(plan), 6)
        self.assertTrue(plan[0]["completed"])
        self.assertEqual(sum(item["minutes"] for item in plan), 30)

    def setUp(self):
        self.lessons = [
            {
                "id": lesson_id,
                "kind": "words",
                "title": lesson_id,
                "description": "Описание",
                "minutes": 5,
                "emoji": "📘",
                "level": level,
            }
            for lesson_id, level in (
                ("a1-one", "A1"),
                ("a2-one", "A2"),
                ("a2-two", "A2"),
                ("a2-three", "A2"),
                ("a2-four", "A2"),
            )
        ]

    def test_plan_prefers_unfinished_lessons_at_current_level(self):
        plan = build_daily_plan(
            self.lessons,
            level="A2",
            completed_all_time=frozenset({"a2-one"}),
            completed_today=frozenset({"a2-two"}),
            personal_words=[],
            today=date(2026, 8, 28),
        )

        self.assertEqual(
            [task["id"] for task in plan],
            ["a2-two", "a2-three", "a2-four", "a2-one"],
        )
        self.assertTrue(plan[0]["completed"])

    def test_completed_today_stays_in_plan_after_it_enters_history(self):
        plan = build_daily_plan(
            self.lessons,
            level="A2",
            completed_all_time=frozenset({"a2-one"}),
            completed_today=frozenset({"a2-one"}),
            personal_words=[],
            today=date(2026, 8, 28),
        )

        self.assertEqual(
            [task["id"] for task in plan],
            ["a2-one", "a2-two", "a2-three", "a2-four"],
        )
        self.assertTrue(plan[0]["completed"])
        self.assertEqual(sum(task["completed"] for task in plan), 1)

    def test_due_dictionary_review_replaces_fourth_lesson(self):
        words = [
            {
                "id": str(index),
                "next_review_date": "2026-08-28" if index < 2 else "2026-09-10",
            }
            for index in range(4)
        ]

        plan = build_daily_plan(
            self.lessons,
            level="A2",
            completed_all_time=frozenset(),
            completed_today=frozenset({"dictionary-practice"}),
            personal_words=words,
            today=date(2026, 8, 28),
        )

        self.assertEqual(len(plan), 4)
        self.assertEqual(plan[-1]["id"], "dictionary-practice")
        self.assertEqual(plan[-1]["description"], "2 слова по расписанию SM-2")
        self.assertTrue(plan[-1]["completed"])

    def test_review_is_not_offered_until_four_words_exist(self):
        plan = build_daily_plan(
            self.lessons,
            level="A2",
            completed_all_time=frozenset(),
            completed_today=frozenset(),
            personal_words=[{"next_review_date": None}] * 3,
            today=date(2026, 8, 28),
        )

        self.assertNotIn("dictionary-practice", {task["id"] for task in plan})

    def test_profile_goal_controls_plan_size(self):
        plan = build_daily_plan(
            self.lessons,
            level="A2",
            completed_all_time=frozenset(),
            completed_today=frozenset(),
            personal_words=[],
            today=date(2026, 8, 28),
            daily_task_limit=2,
        )
        self.assertEqual(len(plan), 2)

    def test_time_modes_use_real_task_minutes_and_keep_at_least_one(self):
        lessons = [
            {**self.lessons[1], "minutes": 7},
            {**self.lessons[2], "minutes": 8},
            {**self.lessons[3], "minutes": 12},
        ]
        ten = build_daily_plan(
            lessons, level="A2", completed_all_time=frozenset(), completed_today=frozenset(),
            personal_words=[], today=date(2026, 8, 28), time_budget_minutes=10,
        )
        fifteen = build_daily_plan(
            lessons, level="A2", completed_all_time=frozenset(), completed_today=frozenset(),
            personal_words=[], today=date(2026, 8, 28), time_budget_minutes=15,
        )
        thirty = build_daily_plan(
            lessons, level="A2", completed_all_time=frozenset(), completed_today=frozenset(),
            personal_words=[], today=date(2026, 8, 28), time_budget_minutes=30,
        )
        self.assertEqual([item["id"] for item in ten], ["a2-one"])
        self.assertEqual([item["id"] for item in fifteen], ["a2-one", "a2-two"])
        self.assertEqual(len(thirty), 3)

    def test_time_mode_keeps_lessons_completed_today_visible(self):
        lessons = [
            {**self.lessons[1], "minutes": 7},
            {**self.lessons[2], "minutes": 8},
            {**self.lessons[3], "minutes": 12},
        ]
        plan = build_daily_plan(
            lessons,
            level="A2",
            completed_all_time=frozenset({"a2-one", "a2-two"}),
            completed_today=frozenset({"a2-one", "a2-two"}),
            personal_words=[],
            today=date(2026, 8, 28),
            time_budget_minutes=10,
        )
        self.assertEqual([item["id"] for item in plan], ["a2-one", "a2-two"])
        self.assertTrue(all(item["completed"] for item in plan))

    def test_low_recent_result_adds_one_transparent_reinforcement(self):
        plan = build_daily_plan(
            self.lessons,
            level="A2",
            completed_all_time=frozenset({"a2-one"}),
            completed_today=frozenset(),
            personal_words=[],
            today=date(2026, 8, 28),
            recent_completion_results=(
                {"lesson_id": "a2-one", "plan_date": "2026-08-27", "cards_total": 5, "cards_known": 3},
            ),
        )
        self.assertEqual(plan[0]["id"], "a2-two")
        self.assertEqual(plan[1]["id"], "a2-one")
        self.assertEqual(plan[1]["plan_type"], "reinforcement")
        self.assertEqual(plan[1]["title"], "Закрепить: a2-one")
        self.assertEqual(plan[1]["description"], "Лексика: a2-one: результат 3 из 5 — стоит закрепить")
        self.assertEqual(plan[1]["reinforcement_reason"]["threshold_percent"], 70)
        self.assertEqual(plan[1]["reinforcement_reason"]["skill"]["group"], "vocabulary")
        self.assertEqual(len(plan), 4)

    def test_reinforcement_is_not_added_for_high_score_or_completed_today(self):
        cases = (
            ({"lesson_id": "a2-one", "plan_date": "2026-08-27", "cards_total": 5, "cards_known": 4}, frozenset(), 4),
            ({"lesson_id": "a2-one", "plan_date": "2026-08-27", "cards_total": 5, "cards_known": 2}, frozenset({"a2-one"}), 4),
        )
        for result, completed_today, goal in cases:
            with self.subTest(result=result, completed_today=completed_today, goal=goal):
                plan = build_daily_plan(
                    self.lessons, level="A2",
                    completed_all_time=frozenset({"a2-one"}),
                    completed_today=completed_today, personal_words=[],
                    today=date(2026, 8, 28), daily_task_limit=goal,
                    recent_completion_results=(result,),
                )
                self.assertFalse(any(task.get("plan_type") == "reinforcement" for task in plan))

    def test_reinforcement_keeps_dictionary_review_and_daily_limit(self):
        plan = build_daily_plan(
            self.lessons, level="A2",
            completed_all_time=frozenset({"a2-one"}), completed_today=frozenset(),
            personal_words=[{"next_review_date": "2026-08-27"}] * 4,
            today=date(2026, 8, 28), daily_task_limit=3,
            recent_completion_results=(
                {"lesson_id": "a2-one", "plan_date": "2026-08-27", "cards_total": 10, "cards_known": 2},
            ),
        )
        self.assertEqual(len(plan), 3)
        self.assertEqual(plan[1]["plan_type"], "reinforcement")
        self.assertEqual(plan[-1]["kind"], "dictionary-review")

    def test_plan_exposes_stable_privacy_safe_skill_tags(self):
        lessons = [
            {**self.lessons[1], "kind": "grammar", "topic_title": "Работа", "theory_title": "Tryb warunkowy"},
            {**self.lessons[2], "id": "a2-story-reading-check", "kind": "quiz", "topic_title": "Путешествия"},
        ]
        plan = build_daily_plan(
            lessons, level="A2", completed_all_time=frozenset(),
            completed_today=frozenset(), personal_words=[], today=date(2026, 8, 28),
        )
        self.assertEqual(plan[0]["skill"], {"id": "grammar:a2-one", "label": "Tryb warunkowy", "group": "grammar"})
        self.assertEqual(plan[1]["skill"]["label"], "Понимание деталей: Путешествия")
