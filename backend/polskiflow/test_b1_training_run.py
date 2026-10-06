import time
import subprocess
from pathlib import Path
from unittest.mock import patch

from django.test import Client, TestCase
from django.core import signing

from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.b1_run_views import BREAK_SECONDS, RUN_MAX_AGE, RUN_SALT
from polskiflow.domain.b1_training_content import training_questions, score_training_part, training_reading_blocks
from polskiflow.domain.b1_weekly_mock import VARIANTS
from polskiflow.domain.b1_training_writing import training_writing_tasks
from polskiflow.domain.b1_training_speaking import PREPARATION_SECONDS, training_speaking_tasks


class B1TrainingRunTests(TestCase):
    def test_recording_metadata_and_pinned_asset_are_rendered_only_for_matching_run(self):
        from polskiflow.test_b1_listening_recordings import B1RecordingChecksTests
        fixture = B1RecordingChecksTests()
        fixture.setUp()
        with patch("polskiflow.b1_run_views.weekly_mock_variant", return_value=VARIANTS[0]), patch(
            "polskiflow.domain.b1_listening_recordings.RECORDINGS", (fixture.item,)
        ):
            intro = self.client.get("/exam/b1/run/")
            self.assertEqual(intro.context["state"]["listening_recording_id"], fixture.item.id)
            opened = self.advance(intro, "start")
            self.assertContains(opened, "data-run-audio preload=\"none\"")
            self.assertContains(opened, "Test narrator")
            self.assertContains(opened, fixture.item.license_url)
            self.assertNotContains(opened, "Системный польский голос устройства")
        resumed = self.advance(opened, "resume")
        self.assertContains(resumed, "data-missing-recording=\"1\"")
        self.assertNotContains(resumed, "Системный польский голос устройства")

    def test_extended_speaking_tasks_and_legacy_three_minute_budget(self):
        for variant in VARIANTS:
            self.assertEqual(len(training_speaking_tasks(variant, 5)), 3)
            self.assertTrue(all(task.prompt and task.checklist for task in training_speaking_tasks(variant, 5)))
            for version in (1, 2, 3, 4):
                self.assertEqual(len(training_speaking_tasks(variant, version)), 1)
        opened = self.client.get("/exam/b1/run/")
        for version in (1, 2, 3, 4):
            state = dict(opened.context["state"], content_version=version, phase="break", step=4, break_until=self.now)
            legacy = self.client.post("/exam/b1/run/", {"run_token": signing.dumps(state, salt=RUN_SALT), "action": "start"})
            self.assertEqual(legacy.context["timer_seconds"], 180)
            self.assertEqual(legacy.context["speaking_preparation_seconds"], 0)
            self.assertNotContains(legacy, "data-speaking-prep-timer")
            self.assertEqual(len(legacy.context["speaking_tasks"]), 1)

    def test_speaking_preparation_cannot_be_skipped_by_finish_or_reload(self):
        opened = self.client.get("/exam/b1/run/")
        state = dict(opened.context["state"], phase="break", step=4, break_until=self.now)
        speaking = self.client.post("/exam/b1/run/", {"run_token": signing.dumps(state, salt=RUN_SALT), "action": "start"})
        self.assertEqual(speaking.context["timer_seconds"], 11 * 60)
        self.assertEqual(self.advance(speaking, "finish", reviewed="on").status_code, 400)
        self.now += 30
        resumed = self.advance(speaking, "resume")
        self.assertEqual(resumed.context["speaking_preparation_seconds"], PREPARATION_SECONDS - 30)
        self.assertEqual(resumed.context["state"]["deadline"], speaking.context["state"]["deadline"])
        self.now += PREPARATION_SECONDS - 30
        result = self.advance(resumed, "finish", reviewed="on")
        self.assertEqual(result.status_code, 200)
        self.assertNotIn("speaking_ready_at", result.context["state"])
        self.assertNotIn("percent", result.context["state"]["results"][-1])

    def test_new_writing_has_two_original_tasks_without_changing_legacy_runs(self):
        for variant in VARIANTS:
            tasks = training_writing_tasks(variant, 4)
            self.assertEqual(len(tasks), 2)
            self.assertEqual([(task.minimum, task.maximum) for task in tasks], [(50, 80), (140, 170)])
            self.assertEqual(tasks[0].prompt, variant.writing_prompt)
            self.assertTrue(tasks[1].prompt and tasks[1].title)
            for version in (1, 2, 3):
                self.assertEqual(len(training_writing_tasks(variant, version)), 1)

    def test_legacy_writing_keeps_one_draft_and_fifteen_minutes(self):
        for version in (1, 2, 3):
            opened = self.client.get("/exam/b1/run/")
            state = dict(opened.context["state"], content_version=version, phase="break", step=3, break_until=self.now)
            opened = self.client.post("/exam/b1/run/", {"run_token": signing.dumps(state, salt=RUN_SALT), "action": "start"})
            self.assertEqual(opened.context["timer_seconds"], 15 * 60)
            self.assertEqual(len(opened.context["writing_tasks"]), 1)
            self.assertNotContains(opened, 'id="run-writing-2"')

    def test_extended_reading_has_four_grouped_texts_and_twenty_questions(self):
        for variant in VARIANTS:
            blocks = training_reading_blocks(variant, 7)
            questions = training_questions(variant, "reading", 7)
            self.assertEqual(len(blocks), 4)
            self.assertEqual([len(block.questions) for block in blocks], [5] * 4)
            self.assertEqual(tuple(q for block in blocks for q in block.questions), questions)
            self.assertEqual(len({q.id for q in questions}), 20)
            self.assertTrue(all(block.text and block.title for block in blocks))
            correct = {q.id: q.correct for q in questions}
            score = score_training_part(variant, "reading", correct, 7)
            self.assertEqual((score["correct"], score["total"], score["percent"]), (20, 20, 100))
            with self.assertRaises(ValueError):
                score_training_part(variant, "reading", dict(list(correct.items())[:-1]), 7)
            for version in (1, 2):
                self.assertEqual(len(training_questions(variant, "reading", version)), 5)
                self.assertEqual(len(training_reading_blocks(variant, version)), 1)

    def test_legacy_reading_run_keeps_its_text_count_and_deadline(self):
        for version in (1, 2):
            with self.subTest(version=version):
                opened = self.client.get("/exam/b1/run/")
                state = dict(opened.context["state"], content_version=version)
                opened = self.client.post("/exam/b1/run/", {"run_token": signing.dumps(state, salt=RUN_SALT), "action": "start"})
                opened = self.advance(opened, "skip")
                self.now += BREAK_SECONDS
                opened = self.advance(opened, "start")
                self.assertEqual(len(opened.context["questions"]), 5)
                self.assertEqual(len(opened.context["reading_blocks"]), 1)
                self.assertEqual(opened.context["timer_seconds"], 7 * 60)
                self.assertNotContains(opened, "Ogłoszenie biblioteki")

    def test_mutation_navigation_preserves_new_signed_state_before_resume(self):
        result = subprocess.run(
            ["node", str(Path(__file__).with_name("test_b1_run_navigation.cjs"))],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_extended_grammar_all_variants_and_existing_short_sets(self):
        for variant in VARIANTS:
            questions = training_questions(variant, "grammar")
            self.assertEqual(len(questions), 40)
            self.assertEqual(len({q.id for q in questions}), 40)
            score = score_training_part(variant, "grammar", {q.id: q.correct for q in questions})
            self.assertEqual((score["correct"], score["total"], score["percent"]), (40, 40, 100))
            self.assertEqual(len(training_questions(variant, "grammar", 1)), 6)
            self.assertEqual(len(variant.questions), 7)
            with self.assertRaises(ValueError):
                score_training_part(variant, "grammar", {q.id: q.correct for q in questions[:-1]})

    def test_old_signed_run_keeps_six_questions_and_six_minute_limit(self):
        response = self.client.get("/exam/b1/run/")
        state = dict(response.context["state"])
        state.pop("content_version")
        response = self.client.post("/exam/b1/run/", {"run_token": signing.dumps(state, salt=RUN_SALT), "action": "start"})
        for _ in range(2):
            response = self.advance(response, "skip")
            self.now += BREAK_SECONDS
            response = self.advance(response, "start")
        self.assertEqual(len(response.context["questions"]), 6)
        self.assertEqual(response.context["timer_seconds"], 360)
        response = self.advance(response, "finish", **{f"answer_{q.id}": q.correct for q in response.context["questions"]})
        self.assertEqual(response.context["state"]["results"][-1]["total"], 6)

    def test_local_recording_lifecycle(self):
        result = subprocess.run(
            ["node", str(Path(__file__).with_name("test_b1_run_recorder.cjs"))],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_listening_limits_pause_and_resume(self):
        result = subprocess.run(
            ["node", str(Path(__file__).with_name("test_b1_run_listening.cjs"))],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        opened = self.advance(self.client.get("/exam/b1/run/"), "start")
        self.assertContains(opened, "data-run-audio-stop")
        self.assertContains(opened, "два прослушивания")

    def setUp(self):
        self.client.cookies[ACCESS_COOKIE] = "access"
        self.now = int(time.time())
        for target, kwargs in (
            ("polskiflow.auth.authenticate_access_token", {"return_value": SupabaseUser("user-123", "learner@example.com")}),
            ("polskiflow.b1_run_views.time.time", {"side_effect": lambda: self.now}),
        ):
            mocked = patch(target, **kwargs)
            mocked.start()
            self.addCleanup(mocked.stop)

    def advance(self, response, action, **fields):
        return self.client.post("/exam/b1/run/", {
            "run_token": response.context["run_token"], "action": action, **fields,
        })

    def test_complete_run_has_five_results_without_grading_free_production(self):
        response = self.advance(self.client.get("/exam/b1/run/"), "start")
        run_id = response.context["state"]["run_id"]
        for index in range(5):
            self.assertEqual(response.context["state"]["step"], index)
            part = response.context["part"]
            if part["id"] == "grammar":
                self.assertEqual(response.context["timer_seconds"], 45 * 60)
            if part["id"] == "reading":
                self.assertEqual(response.context["timer_seconds"], 45 * 60)
                self.assertContains(response, "Ogłoszenie biblioteki")
            fields = {f"answer_{q.id}": q.correct for q in response.context["questions"]}
            if part["mode"] == "self_review":
                fields = {"reviewed": "on"}
            if part["id"] == "speaking":
                self.now += PREPARATION_SECONDS
            response = self.advance(response, "finish", **fields)
            self.assertEqual(response.status_code, 200)
            if index < 4:
                self.assertEqual(response.context["state"]["phase"], "break")
                self.now += BREAK_SECONDS
                response = self.advance(response, "start")
        self.assertEqual(response.context["state"]["phase"], "report")
        self.assertEqual(response.context["state"]["run_id"], run_id)
        report = response.context["report"]
        self.assertEqual([item["status"] for item in report], ["scored"] * 3 + ["self_review"] * 2)
        self.assertEqual([item["total"] for item in report[:3]], [5, 30, 40])
        self.assertTrue(all(item["percent"] == 100 for item in report[:3]))
        self.assertTrue(all("percent" not in item for item in report[3:]))
        self.assertTrue(all("details" not in item for item in response.context["state"]["results"]))
        self.assertContains(response, "Итог по пяти модулям")
        self.assertContains(response, "Общего балла нет")
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_break_and_part_deadline_cannot_be_bypassed_by_post(self):
        opened = self.advance(self.client.get("/exam/b1/run/"), "start")
        self.assertTrue(opened.context["normalize_navigation"])
        fields = {f"answer_{q.id}": q.correct for q in opened.context["questions"]}
        self.now = opened.context["state"]["deadline"]
        late = self.advance(opened, "finish", **fields)
        self.assertEqual(late.status_code, 400)
        self.assertEqual(late.context["state"]["results"], [])
        skipped = self.advance(opened, "skip", **fields)
        self.assertEqual(skipped.context["state"]["results"][0]["status"], "skipped")
        early = self.advance(skipped, "start")
        self.assertEqual(early.status_code, 400)
        self.assertEqual(early.context["state"]["phase"], "break")
        self.now += BREAK_SECONDS
        self.assertEqual(self.advance(skipped, "start").context["part"]["id"], "reading")

    def test_resume_preserves_deadline_variant_and_result_without_answers(self):
        opened = self.advance(self.client.get("/exam/b1/run/"), "start")
        self.now += 20
        resumed = self.advance(opened, "resume")
        self.assertFalse(resumed.context["normalize_navigation"])
        self.assertEqual(resumed.context["state"], opened.context["state"])
        self.assertEqual(resumed.context["run_token"], opened.context["run_token"])
        self.assertEqual(resumed.context["timer_seconds"], 8 * 60 - 20)
        denied = self.advance(opened, "resume", answer_l1="0")
        self.assertEqual(denied.status_code, 400)

    def test_tampering_foreign_account_and_overall_expiry_are_rejected(self):
        opened = self.client.get("/exam/b1/run/")
        tampered = self.client.post("/exam/b1/run/", {"run_token": opened.context["run_token"] + "tampered", "action": "start"})
        self.assertEqual(tampered.status_code, 400)
        with patch("polskiflow.auth.authenticate_access_token", return_value=SupabaseUser("other-user", "other@example.com")):
            self.assertEqual(self.advance(opened, "resume").status_code, 400)
        self.now += RUN_MAX_AGE
        expired = self.advance(opened, "resume")
        self.assertEqual(expired.status_code, 400)
        self.assertTrue(expired.context["discard_draft"])
        self.assertEqual(expired.context["state"]["phase"], "intro")

    def test_free_text_is_never_accepted_and_self_review_requires_confirmation(self):
        response = self.advance(self.client.get("/exam/b1/run/"), "start")
        for _ in range(3):
            response = self.advance(response, "skip")
            self.now += BREAK_SECONDS
            response = self.advance(response, "start")
        self.assertEqual(response.context["part"]["id"], "writing")
        self.assertEqual(response.context["timer_seconds"], 35 * 60)
        self.assertContains(response, '<textarea id="run-writing"')
        self.assertContains(response, '<textarea id="run-writing-2"')
        self.assertNotContains(response, 'name="writing"')
        self.assertEqual(self.advance(response, "finish").status_code, 400)
        self.assertEqual(self.advance(response, "finish", reviewed="on", writing="private text").status_code, 400)
        self.assertEqual(self.advance(response, "finish", reviewed="on", writing2="private text").status_code, 400)
        completed = self.advance(response, "finish", reviewed="on")
        self.assertEqual(completed.context["state"]["results"][-1], {"id": "writing", "status": "self_review"})
        self.now += BREAK_SECONDS
        speaking = self.advance(completed, "start")
        self.assertContains(speaking, "data-run-recorder")
        self.assertEqual(self.advance(speaking, "finish", reviewed="on", audio="private audio").status_code, 400)
        self.now += PREPARATION_SECONDS
        self.assertEqual(self.advance(speaking, "finish", reviewed="on").status_code, 200)

    def test_guest_and_csrf_boundaries(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.cookies[ACCESS_COOKIE] = "access"
        self.assertEqual(csrf.post("/exam/b1/run/", {"action": "start"}).status_code, 403)
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/exam/b1/run/").status_code, 302)

    def test_versions_two_to_five_keep_their_original_grammar_and_deadline(self):
        for version in (2, 3, 4, 5):
            state = dict(self.client.get('/exam/b1/run/').context['state'], content_version=version,
                         phase='break', step=2, break_until=self.now)
            response = self.client.post('/exam/b1/run/', {'run_token': signing.dumps(state, salt=RUN_SALT), 'action': 'start'})
            self.assertEqual(len(response.context['questions']), 20)
            self.assertEqual(response.context['grammar_blocks'], ())
            self.assertEqual(response.context['timer_seconds'], 1200)
            deadline = response.context['state']['deadline']
            self.now += 19
            resumed = self.advance(response, 'resume')
            self.assertEqual(resumed.context['state']['deadline'], deadline)
            self.assertEqual(resumed.context['timer_seconds'], 1181)
            fields = {f'answer_{q.id}': q.correct for q in resumed.context['questions']}
            finished = self.advance(resumed, 'finish', **fields)
            self.assertEqual(finished.context['state']['results'][-1]['total'], 20)

    def test_version_six_groups_all_answers_and_preserves_them_on_resume(self):
        for variant in VARIANTS:
            state = dict(self.client.get('/exam/b1/run/').context['state'], variant_id=variant.id, content_version=6,
                         phase='break', step=2, break_until=self.now)
            response = self.client.post('/exam/b1/run/', {'run_token': signing.dumps(state, salt=RUN_SALT), 'action': 'start'})
            blocks = response.context['grammar_blocks']
            self.assertEqual([len(block) for block in blocks], [5] * 8)
            self.assertEqual(tuple(q for block in blocks for q in block), response.context['questions'])
            self.assertEqual(response.context['timer_seconds'], 2700)
            self.assertContains(response, 'id="grammar-block-', count=8)
            self.assertContains(response, 'name="answer_tg40"', count=3)
            self.now += 11
            restored = self.advance(response, 'resume')
            self.assertEqual(restored.context['timer_seconds'], 2689)
            self.assertEqual(restored.context['run_token'], response.context['run_token'])
            self.assertEqual(restored.context['grammar_blocks'], blocks)
            fields = {f'answer_{q.id}': q.correct for q in restored.context['questions']}
            rejected = self.advance(restored, 'finish', **dict(list(fields.items())[:-1]))
            self.assertEqual(rejected.status_code, 400)
            self.assertEqual(rejected.context['state']['results'], [])
            result = self.advance(restored, 'finish', **fields)
            self.assertEqual(result.context['state']['results'][-1]['total'], 40)
            self.assertEqual(result.context['state']['results'][-1]['percent'], 100)


    def test_written_grammar_validation_and_private_aggregate(self):
        state = dict(self.client.get('/exam/b1/run/').context['state'], phase='break', step=2, break_until=self.now)
        response = self.client.post('/exam/b1/run/', {'run_token': signing.dumps(state, salt=RUN_SALT), 'action': 'start'})
        questions = response.context['questions']
        self.assertEqual(sum(bool(getattr(q, 'written', False)) for q in questions), 10)
        self.assertContains(response, 'data-run-written', count=10)
        self.assertNotContains(response, 'value="pomógłbyś"')
        fields = {f'answer_{q.id}': q.correct for q in questions}
        for invalid in ('', '   ', 'x' * 121):
            self.assertEqual(self.advance(response, 'finish', **dict(fields, answer_tw31=invalid)).status_code, 400)
        self.assertEqual(self.advance(response, 'finish', **dict(fields, answer_unknown='test')).status_code, 400)
        result = self.advance(response, 'finish', **dict(fields, answer_tw31='  CZASU  ', answer_tw40='pomoglbyś'))
        aggregate = result.context['state']['results'][-1]
        self.assertEqual(aggregate, {'id': 'grammar', 'status': 'scored', 'correct': 39, 'total': 40, 'percent': 98})
        self.assertNotIn('pomoglbyś', str(result.context['state']))

    def test_written_answers_normalize_unicode_but_not_polish_letters(self):
        import unicodedata
        from polskiflow.domain.b1_training_content import score_training_part, training_questions
        variant = VARIANTS[0]
        answers = {q.id: q.correct for q in training_questions(variant, 'grammar')}
        answers['tw40'] = unicodedata.normalize('NFD', 'POMÓGŁBYŚ')
        self.assertEqual(score_training_part(variant, 'grammar', answers)['correct'], 40)
        answers['tw40'] = 'pomoglbyś'
        self.assertEqual(score_training_part(variant, 'grammar', answers)['correct'], 39)

    def test_reading_matching_version_eight_and_legacy_deadlines(self):
        for version in range(3, 9):
            state = dict(self.client.get('/exam/b1/run/').context['state'], content_version=version,
                         phase='break', step=1, break_until=self.now)
            response = self.client.post('/exam/b1/run/', {'run_token': signing.dumps(state, salt=RUN_SALT), 'action': 'start'})
            total, minutes, blocks = (30, 45, 5) if version == 8 else (20, 22, 4)
            self.assertEqual(len(response.context['questions']), total)
            self.assertEqual(len(response.context['reading_blocks']), blocks)
            self.assertEqual(response.context['timer_seconds'], minutes * 60)
            self.now += 13
            restored = self.advance(response, 'resume')
            self.assertEqual(restored.context['timer_seconds'], minutes * 60 - 13)
            self.assertEqual(restored.context['run_token'], response.context['run_token'])
            fields = {f'answer_{q.id}': q.correct for q in restored.context['questions']}
            self.assertEqual(self.advance(restored, 'finish', **dict(list(fields.items())[:-1])).status_code, 400)
            if version == 8:
                self.assertContains(restored, 'id="reading-matching"')
                self.assertContains(restored, 'name="answer_tr30"', count=6)
                self.assertEqual(self.advance(restored, 'finish', **dict(fields, answer_tr30=6)).status_code, 400)
            finished = self.advance(restored, 'finish', **fields)
            self.assertEqual(finished.context['state']['results'][-1],
                             {'id': 'reading', 'status': 'scored', 'correct': total, 'total': total, 'percent': 100})

    def test_reading_matching_order_and_distractor_for_each_variant(self):
        for variant in VARIANTS:
            blocks = training_reading_blocks(variant)
            questions = training_questions(variant, 'reading')
            self.assertEqual([len(b.questions) for b in blocks], [5, 5, 5, 5, 10])
            self.assertEqual(tuple(q for b in blocks for q in b.questions), questions)
            self.assertEqual(len({q.id for q in questions}), 30)
            matching = blocks[-1]
            self.assertEqual([q.correct for q in matching.questions], [0, 1, 2, 3, 4] * 2)
            self.assertTrue(all(q.options == ('A', 'B', 'C', 'D', 'E', 'F') for q in matching.questions))
            self.assertIn('To samo ogłoszenie może pasować do kilku osób.', matching.text)
            answers = {q.id: q.correct for q in questions}
            answers['tr30'] = 5
            self.assertEqual(score_training_part(variant, 'reading', answers)['correct'], 29)
