from unittest.mock import patch

from django.test import TestCase

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.domain.interaction_scenarios import (
    FREE_PRODUCTION_SCENARIOS,
    SPEAKING_SCENARIOS,
    SCENARIOS,
    SEQUENCE_SCENARIOS,
    validate_answer,
    validate_sequence_answer,
)


class InteractionScenarioTests(TestCase):
    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        self.auth_patch = patch(
            "polskiflow.auth.authenticate_access_token",
            return_value=SupabaseUser("user-123", "learner@example.com"),
        )
        self.auth_patch.start()
        self.addCleanup(self.auth_patch.stop)

    def test_page_shows_b1_b2_scenarios_and_honest_scope(self):
        response = self.client.get("/interaction/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(SCENARIOS), 5)
        self.assertContains(response, "Взаимодействие и медиация")
        self.assertContains(response, "Договориться о плане")
        self.assertContains(response, "Выбрать подходящий регистр")
        self.assertContains(response, "не экзамен, сертификат")
        self.assertContains(response, 'name="scenario_id"', count=8)

    def test_page_shows_sequence_tasks_beyond_multiple_choice(self):
        response = self.client.get("/interaction/")

        self.assertEqual(len(SEQUENCE_SCENARIOS), 3)
        self.assertContains(response, "Собери ответ по смысловым шагам")
        self.assertContains(response, "Собрать вежливую просьбу")
        self.assertContains(response, 'name="block_id"', count=9)

    def test_page_offers_local_ungraded_free_production(self):
        response = self.client.get("/interaction/")

        self.assertEqual(len(FREE_PRODUCTION_SCENARIOS), 2)
        self.assertContains(response, "Сформулируй ответ самостоятельно")
        self.assertContains(response, "Предложить компромисс в переписке")
        self.assertContains(response, "Передать важное из объявления")
        self.assertContains(response, "не отправляется на сервер")
        self.assertContains(response, "не оценивается автоматически")
        self.assertContains(response, "Жанровая самопроверка", count=2)
        self.assertContains(response, 'data-interaction-draft="', count=2)
        self.assertNotContains(response, 'name="free_draft')

    def test_page_offers_private_b1_speaking_recording_and_self_check(self):
        response = self.client.get("/interaction/")

        self.assertEqual(len(SPEAKING_SCENARIOS), 2)
        self.assertContains(response, "Устная часть B1")
        self.assertContains(response, "45 секунд на план")
        self.assertContains(response, "Аудио не загружается на сервер")
        self.assertContains(response, "data-speaking-card data-preparation", count=2)
        self.assertContains(response, "navigator.mediaDevices.getUserMedia")
        self.assertContains(response, "new MediaRecorder(stream)")
        self.assertContains(response, "История устных ответов")
        self.assertContains(response, 'data-save-recording hidden', count=2)
        self.assertContains(response, 'indexedDB.open("polskiflow-speaking", 1)')
        self.assertContains(response, 'owner: recordingOwner')
        self.assertContains(response, "existing.slice(9)")
        self.assertContains(response, "Аудио не загружается на сервер")
        self.assertContains(response, "Самопроверка после попытки", count=2)
        self.assertContains(response, "Показать пример ответа", count=2)
        self.assertNotContains(response, 'name="speaking')

    def test_free_production_drafts_use_per_user_local_storage(self):
        response = self.client.get("/interaction/")

        self.assertContains(response, 'storagePrefix = "polskiflow-interaction:')
        self.assertContains(
            response, 'storagePrefix = "polskiflow-interaction:user\\u002D123:'
        )
        self.assertContains(response, "localStorage.setItem(key, textarea.value)")
        self.assertContains(response, "localStorage.removeItem(key)")
        self.assertContains(response, 'type="button" data-reset-interaction-draft', count=2)

    def test_correct_answer_has_transparent_explanation(self):
        response = self.client.post(
            "/interaction/",
            {"scenario_id": "meeting-position", "option_id": "a"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Подходящий ответ")
        self.assertContains(response, "сохраняет главное опасение")

    def test_feedback_offers_ungraded_manual_self_check(self):
        response = self.client.post(
            "/interaction/",
            {"scenario_id": "meeting-position", "option_id": "a"},
        )

        self.assertContains(response, "Сравни свой ответ с удачным вариантом")
        self.assertContains(response, "не оцениваются автоматически")
        self.assertContains(response, 'class="interaction-self-check"')
        self.assertNotContains(response, 'name="self_check')

    def test_sequence_feedback_has_mediation_self_check(self):
        response = self.client.post(
            "/interaction/",
            {
                "task_type": "sequence",
                "scenario_id": "delay-mediation",
                "block_id": ["cause", "effect", "reservation"],
            },
        )

        self.assertContains(response, "Проверь собранное сообщение")
        self.assertContains(response, "без новых предположений")
        self.assertNotContains(response, 'name="self_check')

    def test_wrong_answer_shows_better_option_and_reason(self):
        response = self.client.post(
            "/interaction/",
            {"scenario_id": "formal-reply", "option_id": "a"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Есть более подходящий ответ")
        self.assertContains(response, "Szanowna Pani")
        self.assertContains(response, "слишком разговорные")

    def test_invalid_and_ambiguous_payloads_are_rejected(self):
        invalid = self.client.post(
            "/interaction/", {"scenario_id": "missing", "option_id": "a"}
        )
        unexpected = self.client.post(
            "/interaction/",
            {"scenario_id": "weekend-plan", "option_id": "b", "score": "100"},
        )
        ambiguous = self.client.post(
            "/interaction/",
            {"scenario_id": "weekend-plan", "option_id": ["a", "b"]},
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertContains(invalid, "Неизвестный сценарий", status_code=400)
        self.assertEqual(unexpected.status_code, 400)
        self.assertEqual(ambiguous.status_code, 400)

    def test_domain_validation_rejects_option_from_another_scenario(self):
        with self.assertRaisesRegex(ValueError, "Выберите один"):
            validate_answer("weekend-plan", "unknown")

    def test_sequence_answer_is_checked_and_explained(self):
        correct = self.client.post(
            "/interaction/",
            {
                "task_type": "sequence",
                "scenario_id": "delay-mediation",
                "block_id": ["cause", "effect", "reservation"],
            },
        )
        wrong = self.client.post(
            "/interaction/",
            {
                "task_type": "sequence",
                "scenario_id": "delay-mediation",
                "block_id": ["reservation", "effect", "cause"],
            },
        )

        self.assertContains(correct, "Логичная последовательность")
        self.assertContains(correct, "причина → последствие")
        self.assertContains(wrong, "Порядок стоит изменить")
        self.assertContains(wrong, "Dostawca poinformował")

    def test_sequence_payload_must_be_exact_permutation(self):
        duplicate = self.client.post(
            "/interaction/",
            {
                "task_type": "sequence",
                "scenario_id": "library-request",
                "block_id": ["context", "context", "request"],
            },
        )
        injected = self.client.post(
            "/interaction/",
            {
                "task_type": "sequence",
                "scenario_id": "library-request",
                "block_id": ["context", "question", "other"],
            },
        )

        self.assertContains(duplicate, "каждый предложенный блок", status_code=400)
        self.assertContains(injected, "каждый предложенный блок", status_code=400)
        with self.assertRaisesRegex(ValueError, "ровно один раз"):
            validate_sequence_answer(
                "library-request", ("context", "context", "request")
            )

    def test_route_requires_authentication(self):
        self.auth_patch.stop()
        self.client.cookies.clear()

        response = self.client.get("/interaction/")

        self.assertRedirects(
            response,
            "/login/?next=%2Finteraction%2F",
            fetch_redirect_response=False,
        )

    def test_practice_hub_links_to_scenarios(self):
        response = self.client.get("/practice/")

        self.assertContains(response, 'href="/interaction/"')
        self.assertContains(response, "Общение и медиация")
