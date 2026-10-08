from unittest.mock import patch
from pathlib import Path
import subprocess

from django.core import signing
from django.test import SimpleTestCase, TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.b1_exam_simulation import (
    B1_SIMULATION_PARTS,
    SIMULATION_EXTRA_QUESTIONS,
    get_simulation_part,
    score_simulation_part,
    simulation_questions,
    simulation_timing,
)
from polskiflow.domain.b1_weekly_mock import VARIANTS


class B1ExamSimulationDomainTests(SimpleTestCase):
    def test_short_budget_tracks_question_count_and_preserves_full_limits(self):
        for variant in VARIANTS:
            for part_id, minutes in (("listening", 8), ("reading", 7), ("grammar", 6)):
                part = get_simulation_part(part_id)
                self.assertEqual(simulation_timing(variant, part)["timer_minutes"], minutes)
                self.assertEqual(simulation_timing(variant, part, "full")["timer_minutes"], part["minutes"])
            self.assertEqual(simulation_timing(variant, get_simulation_part("writing"))["timer_minutes"], 75)
        with self.assertRaises(ValueError):
            simulation_timing(VARIANTS[0], get_simulation_part("reading"), "invalid")

    def test_browser_draft_lifecycle_and_elapsed_timer(self):
        completed = subprocess.run(
            ["node", str(Path(__file__).with_name("test_b1_simulation_resume.cjs"))],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)

    def test_five_parts_keep_official_time_and_honest_modes(self):
        self.assertEqual(
            [(part["id"], part["minutes"]) for part in B1_SIMULATION_PARTS],
            [("listening", 25), ("reading", 45), ("grammar", 45), ("writing", 75), ("speaking", 15)],
        )
        self.assertEqual(get_simulation_part("writing")["mode"], "self_review")
        self.assertIsNone(get_simulation_part("unknown"))

    def test_scores_exactly_one_objective_part(self):
        variant = VARIANTS[0]
        questions = simulation_questions(variant, "grammar")
        result = score_simulation_part(
            variant, "grammar", {question.id: question.correct for question in questions}
        )

        self.assertEqual((result["correct"], result["total"], result["percent"]), (6, 6, 100))
        self.assertEqual(len(result["details"]), 6)
        with self.assertRaises(ValueError):
            score_simulation_part(variant, "grammar", {})
        with self.assertRaises(ValueError):
            score_simulation_part(variant, "writing", {})

    def test_each_variant_has_expanded_balanced_original_objective_pack(self):
        self.assertEqual(set(SIMULATION_EXTRA_QUESTIONS), {variant.id for variant in VARIANTS})
        for variant in VARIANTS:
            counts = {
                module: len(simulation_questions(variant, module))
                for module in ("listening", "reading", "grammar")
            }
            self.assertEqual(counts, {"listening": 5, "reading": 5, "grammar": 6})
            questions = tuple(
                question
                for module in counts
                for question in simulation_questions(variant, module)
            )
            self.assertEqual(len({question.id for question in questions}), 16)
            self.assertTrue(all(len(question.options) == 3 for question in questions))
            self.assertTrue(all(question.correct in range(3) for question in questions))
            self.assertTrue(all(question.explanation.strip() for question in questions))
            self.assertTrue(all(
                len(question.explanation.split()) >= 8
                for question in SIMULATION_EXTRA_QUESTIONS[variant.id]
            ))


class B1ExamSimulationViewTests(TestCase):
    def test_shared_listening_is_scoped_to_the_active_listening_part(self):
        response = self.client.get("/exam/b1/simulation/", {"part": "listening"})
        self.assertContains(response, 'data-b1-listening')
        self.assertContains(response, 'data-listening-form="simulation-form"')
        self.assertContains(response, 'data-listening-transcript="simulation-listening-transcript"')
        self.assertContains(response, 'data-run-audio-stop disabled')
        self.assertContains(response, 'root.dataset.runId = String(state.startedAt)')
        self.assertContains(response, 'два прослушивания и пауза 30 секунд')
        self.assertNotContains(response, 'id="simulation-play"')
        for part in ("reading", "grammar", "writing", "speaking"):
            self.assertNotContains(self.client.get("/exam/b1/simulation/", {"part": part}), 'data-b1-listening')

    @patch("polskiflow.b1_mock_views.save_b1_section_attempt", return_value=True)
    def test_timeout_scores_partial_and_empty_without_awarding_missing_answers(self, save_attempt):
        from types import SimpleNamespace
        opened = self.client.get("/exam/b1/simulation/?part=reading")
        token = opened.context["simulation_token"]
        questions = opened.context["questions"]
        deadline = opened.context["attempt_started_at_ms"] / 1000 + opened.context["duration_seconds"]
        fields = {"simulation_token": token, f"answer_{questions[0].id}": questions[0].correct,
                  f"answer_{questions[1].id}": (questions[1].correct + 1) % len(questions[1].options)}
        with patch("polskiflow.b1_mock_views.time", SimpleNamespace(time=lambda: deadline - 1)):
            early = self.client.post("/exam/b1/simulation/", fields)
            self.assertEqual(early.status_code, 400)
            save_attempt.assert_not_called()
        with patch("polskiflow.b1_mock_views.time", SimpleNamespace(time=lambda: deadline)):
            response = self.client.post("/exam/b1/simulation/", fields)
            self.assertEqual(response.status_code, 200)
            score = response.context["result"]
            self.assertEqual((score["correct"], score["incorrect"], score["unanswered"]), (1, 1, len(questions) - 2))
            self.assertTrue(score["timed_out"])
            self.assertContains(response, "Без ответа")
            self.assertEqual(score["percent"], round(100 / len(questions)))
            empty = self.client.post("/exam/b1/simulation/", {"simulation_token": token})
            self.assertEqual(empty.context["result"]["unanswered"], len(questions))
            self.assertEqual(empty.context["result"]["correct"], 0)
            invalid = self.client.post("/exam/b1/simulation/", {"simulation_token": token, f"answer_{questions[0].id}": 999})
            self.assertEqual(invalid.status_code, 400)

    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        auth = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser("user-123", "learner@example.com"),
        )
        auth.start()
        self.addCleanup(auth.stop)

    def test_each_part_has_polish_directions_and_optional_russian_help(self):
        for part in B1_SIMULATION_PARTS:
            with self.subTest(part=part["id"]):
                response = self.client.get("/exam/b1/simulation/", {"part": part["id"]})
                self.assertEqual(response.status_code, 200)
                instruction = response.context["instruction"]
                self.assertContains(response, f'<p lang="pl">{instruction["polish"]}</p>', html=True)
                self.assertContains(response, '<details lang="ru">')
                self.assertNotContains(response, '<details lang="ru" open')
                if part["mode"] == "self_review":
                    self.assertIn("nie otrzymuje automatycznej oceny", instruction["polish"])

    def test_hub_lists_five_separate_parts_and_limits(self):
        response = self.client.get("/exam/b1/simulation/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Тренажёр частей экзамена")
        self.assertContains(response, "Начать часть", count=5)
        self.assertContains(response, "75 мин")
        self.assertContains(response, "самопроверка", count=2)
        self.assertContains(response, "5 заданий", count=2)
        self.assertContains(response, "6 заданий", count=1)
        self.assertContains(
            response,
            '<p class="simulation-progress muted" data-simulation-progress>',
            count=5,
        )
        self.assertNotContains(response, "user-123")

    @patch("polskiflow.b1_mock_views.save_b1_section_attempt", return_value=True)
    def test_objective_part_has_signed_state_timer_and_aggregate_history(self, save_attempt):
        opened = self.client.get("/exam/b1/simulation/?part=grammar")
        self.assertContains(opened, "6:00")
        self.assertContains(opened, '<main ', count=1)
        self.assertContains(opened, 'role="timer" aria-live="off"')
        self.assertContains(opened, 'id="simulation-timer-status" role="status"')
        self.assertContains(opened, "Объём этого оригинального набора LingoFlow меньше")
        questions = opened.context["questions"]
        payload = {"simulation_token": opened.context["simulation_token"]}
        payload.update({f"answer_{question.id}": question.correct for question in questions})

        result = self.client.post("/exam/b1/simulation/", payload)

        self.assertEqual(result.status_code, 200)
        self.assertContains(result, "6 из 6 · 100%")
        self.assertContains(result, "не оценка официальной части B1")
        self.assertContains(result, "Агрегированный результат сохранён между устройствами")
        self.assertContains(result, 'data-result-percent="100"')
        saved_result = save_attempt.call_args.args[4]
        self.assertEqual(saved_result["section_id"], "grammar")
        self.assertEqual((saved_result["correct"], saved_result["total"]), (6, 6))
        self.assertNotIn("answers", saved_result)

    @patch("polskiflow.b1_mock_views.load_b1_section_attempts")
    def test_hub_shows_cross_device_aggregate_history(self, load_history):
        load_history.return_value = [{
            "section_label": "Чтение",
            "attempted_at": "2026-10-04T08:00:00Z",
            "attempt_version": "b1-weekly-v2",
            "correct": 4,
            "total": 5,
            "percent": 80,
            "variant_label": "Вариант 2",
            "attempted_at_display": "04.10.2026 08:00",
        }]

        response = self.client.get("/exam/b1/simulation/")

        self.assertContains(response, "Последние проверяемые части")
        self.assertContains(response, "Чтение")
        self.assertContains(response, "4 / 5 · 80%")
        self.assertContains(response, "04.10.2026 08:00 · Вариант 2")
        self.assertContains(response, "Ответы, письмо и речь не сохраняются")

    def test_writing_and_speaking_have_no_automatic_score_or_server_text_field(self):
        writing = self.client.get("/exam/b1/simulation/?part=writing")
        speaking = self.client.get("/exam/b1/simulation/?part=speaking")

        self.assertContains(writing, "75:00")
        self.assertContains(writing, "Текст восстанавливается после перезагрузки в этой вкладке")
        self.assertContains(writing, '<textarea id="simulation-writing" rows="14"')
        self.assertNotContains(writing, 'name="simulation-writing"')
        self.assertContains(speaking, "15:00")
        self.assertContains(speaking, "Речь не записывается")
        self.assertContains(writing, "Завершить самопроверку")
        self.assertContains(speaking, "Завершить самопроверку")

    def test_browser_resume_keeps_draft_in_tab_and_progress_in_local_storage(self):
        response = self.client.get("/exam/b1/simulation/?part=reading")

        self.assertContains(response, "localStorage.getItem(statePrefix + partId)")
        self.assertContains(response, "startedAt")
        self.assertContains(response, "completedAt")
        self.assertContains(response, "sessionStorage.setItem(draftKey")
        self.assertContains(response, "draft.startedAt === state.startedAt")
        self.assertContains(response, "sessionStorage.removeItem(draftKey)")
        self.assertNotContains(response, "selectedAnswers")
        self.assertNotContains(response, "simulation-writing', textarea")

    def test_rejects_unknown_part_fields_and_forged_state(self):
        opened = self.client.get("/exam/b1/simulation/?part=reading")
        unknown = self.client.post("/exam/b1/simulation/", {
            "simulation_token": opened.context["simulation_token"], "extra": "1"
        })
        forged = signing.dumps(
            {"user_id": "another", "variant_id": "b1-weekly-v1", "part_id": "reading"},
            salt="polskiflow.b1-exam-simulation",
        )
        foreign = self.client.post("/exam/b1/simulation/", {"simulation_token": forged})

        self.assertEqual(unknown.status_code, 400)
        self.assertContains(unknown, "неизвестные поля", status_code=400)
        self.assertEqual(foreign.status_code, 400)

    @patch("polskiflow.b1_mock_views.save_b1_section_attempt", return_value=True)
    def test_full_timing_is_signed_and_survives_post(self, _save):
        opened = self.client.get("/exam/b1/simulation/?part=grammar&timing=full")
        self.assertContains(opened, "45:00")
        token = opened.context["simulation_token"]
        payload = signing.loads(token, salt="polskiflow.b1-exam-simulation")
        self.assertEqual(payload["timing_mode"], "full")
        submitted = self.client.post("/exam/b1/simulation/", {
            "simulation_token": token,
            **{f"answer_{q.id}": q.correct for q in opened.context["questions"]},
        })
        self.assertEqual(submitted.context["duration_seconds"], 45 * 60)

    def test_guest_is_redirected_to_login(self):
        self.client.cookies.clear()
        self.assertRedirects(
            self.client.get("/exam/b1/simulation/"),
            "/login/?next=%2Fexam%2Fb1%2Fsimulation%2F",
            fetch_redirect_response=False,
        )
