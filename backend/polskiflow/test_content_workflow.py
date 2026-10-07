import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase

from polskiflow.domain.content_workflow import (
    ManifestError,
    build_executable_migration_preview,
    build_migration_scaffold,
    build_model_mapping,
    build_preview,
    build_production_promotion_receipt,
    build_publish_plan,
    validate_model_resolutions,
    validate_manifest,
    verify_production_promotion_receipt,
    write_migration_scaffold,
)


def sample_resolutions(checksum):
    return {
        "schema_version": 1,
        "manifest_checksum": checksum,
        "course_id": "b1-main",
        "topic": {"description": "Opis tematu", "emoji": "🧭", "position": 8},
        "card_set_lesson_ids": ["example-words-one", "example-words-two"],
        "grammar_lesson": {
            "id": "example-grammar", "title": "Gramatyka", "plan_title": "Poznaj regułę",
            "subtitle": "Praktyczne użycie", "description": "Opis lekcji", "minutes": 8,
            "emoji": "🧩", "theory_title": "Jak działa reguła", "position": 3,
        },
        "question_lesson_ids": {"exercises": "example-grammar", "final_quiz": "example-quiz"},
        "reading": {
            "id": "example-reading", "topic_id": "test-editorial-topic", "title": "Tekst",
            "description": "Opis tekstu", "minutes": 6, "emoji": "📖", "position": 4,
        },
    }


def sample_manifest(*, status="draft", origin="original"):
    card_sets = [
        [{"id": f"card-a-{index}", "polish": f"wyraz {index}", "translation": f"слово {index}", "example": f"To jest wyraz {index}."} for index in range(5)],
        [{"id": f"card-b-{index}", "polish": f"zwrot {index}", "translation": f"фраза {index}", "example": f"To jest zwrot {index}."} for index in range(5)],
    ]
    source = {
        "origin": origin,
        "license": "PolskiFlow original content",
        "verified_at": "2026-09-01",
        "created_for": "PolskiFlow",
    }
    if origin == "external":
        source = {
            "origin": "external",
            "source_url": "https://primary.example/item",
            "source_item_id": "item-42",
            "author": "Example Author",
            "license": "CC BY 4.0",
            "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "verified_at": "2026-09-01",
            "retrieved_at": "2026-09-01",
            "changes": "Adapted into short exercises.",
            "attribution": "Example Author, CC BY 4.0.",
            "reviewer": "editor@example.invalid",
            "status": "approved",
        }
    return {
        "schema_version": 1,
        "id": "test-editorial-topic",
        "title": "Temat testowy",
        "level": "B1",
        "language": "pl",
        "status": status,
        "source": source,
        "content": {
            "active_units": [{"id": f"unit-{index}"} for index in range(12)],
            "card_sets": card_sets,
            "grammar": {"summary": "Krótkie i sprawdzalne wyjaśnienie."},
            "exercises": [{"id": f"exercise-{index}", "prompt": f"Pytanie {index}", "options": ["Tak", "Nie"], "answer": "Tak", "explanation": "Odpowiedź wynika z reguły."} for index in range(5)],
            "reading": {
                "paragraphs": ["Pierwszy akapit.", "Drugi akapit."],
                "glossary": {"akapit": {"lemma": "akapit", "translation": "абзац"}},
            },
            "final_quiz": [{"id": f"quiz-{index}", "prompt": f"Quiz {index}", "options": ["A", "B"], "answer": "A", "explanation": "Wariant A spełnia warunek."} for index in range(8)],
        },
        "expected_counts": {
            "active_units": 12,
            "card_sets": 2,
            "flashcards": 10,
            "exercises": 5,
            "reading_paragraphs": 2,
            "glossary": 1,
            "final_quiz": 8,
        },
    }


class ContentWorkflowDomainTests(SimpleTestCase):
    def test_new_brand_and_legacy_original_manifests_remain_supported(self):
        for brand in ("LingoFlow", "PolskiFlow"):
            manifest = sample_manifest()
            manifest["source"]["created_for"] = brand
            validate_manifest(manifest)


    def test_draft_preview_is_validated_but_not_publishable(self):
        result = validate_manifest(sample_manifest())
        preview = build_preview(result)

        self.assertFalse(preview["publishable"])
        self.assertEqual(preview["counts"]["active_units"], 12)
        self.assertEqual(len(preview["draft"]["checksum"]), 64)
        self.assertIn("no database", preview["boundary"])

    def test_declared_counts_must_match_payload(self):
        manifest = sample_manifest()
        manifest["expected_counts"]["final_quiz"] = 9

        with self.assertRaisesRegex(ManifestError, "фактически 8"):
            validate_manifest(manifest)

    def test_external_source_requires_approved_object_card(self):
        manifest = sample_manifest(origin="external")
        manifest["source"]["status"] = "review"

        with self.assertRaisesRegex(ManifestError, "status.*approved"):
            validate_manifest(manifest)

    def test_rejects_duplicate_ids_and_unknown_fields(self):
        manifest = sample_manifest()
        manifest["content"]["card_sets"][1][0]["id"] = "card-a-0"
        with self.assertRaisesRegex(ManifestError, "дублирующийся id"):
            validate_manifest(manifest)

        manifest = sample_manifest()
        manifest["content"]["surprise"] = True
        with self.assertRaisesRegex(ManifestError, "неизвестные поля: surprise"):
            validate_manifest(manifest)

    def test_questions_require_unique_options_and_exact_referenced_answer(self):
        manifest = sample_manifest()
        manifest["content"]["final_quiz"][0]["options"] = ["A", "A"]
        with self.assertRaisesRegex(ManifestError, "варианты должны быть уникальны"):
            validate_manifest(manifest)

        manifest = sample_manifest()
        manifest["content"]["exercises"][0]["answer"] = "Brak"
        with self.assertRaisesRegex(ManifestError, "ровно на один вариант"):
            validate_manifest(manifest)

    def test_reading_and_glossary_require_explicit_supported_fields(self):
        manifest = sample_manifest()
        manifest["content"]["reading"]["paragraphs"][0] = " "
        with self.assertRaisesRegex(ManifestError, "paragraphs"):
            validate_manifest(manifest)

        manifest = sample_manifest()
        manifest["content"]["reading"]["glossary"]["akapit"]["note"] = "unknown"
        with self.assertRaisesRegex(ManifestError, "неизвестные поля: note"):
            validate_manifest(manifest)

    def test_publish_plan_requires_editorial_review_and_approval_id(self):
        manifest = sample_manifest(status="approved")
        result = validate_manifest(manifest)

        with self.assertRaisesRegex(ManifestError, "manifest.review"):
            build_publish_plan(result, "ED-101")

        manifest["review"] = {
            "language_reviewer": "language-editor",
            "license_reviewer": "rights-editor",
            "reviewed_at": "2026-09-01",
        }
        plan = build_publish_plan(validate_manifest(manifest), "ED-101")
        self.assertFalse(plan["publish_boundary"]["writes_performed"])
        self.assertEqual(plan["approval_id"], "ED-101")
        self.assertEqual(plan["rollback_plan"]["strategy"], "forward-only corrective migration")

    def test_scaffold_requires_exact_checksum_and_keeps_database_todos_explicit(self):
        manifest = sample_manifest(status="approved")
        manifest["review"] = {
            "language_reviewer": "language-editor",
            "license_reviewer": "rights-editor",
            "reviewed_at": "2026-09-01",
        }
        result = validate_manifest(manifest)

        with self.assertRaisesRegex(ManifestError, "manifest изменился"):
            build_migration_scaffold(result, "ED-102", "0" * 64)
        with self.assertRaisesRegex(ManifestError, "approval_id"):
            build_migration_scaffold(result, "ED-102\nDROP", result.checksum)

        artifacts = build_migration_scaffold(result, "ED-102", result.checksum)
        self.assertEqual(
            set(artifacts),
            {
                "scaffold.json",
                "approved-manifest.json",
                "model-mapping.json",
                "django-data-migration.scaffold.py",
                "supabase-migration.scaffold.sql",
            },
        )
        self.assertIn("performs no ORM", artifacts["django-data-migration.scaffold.py"])
        self.assertIn("contains no executable SQL", artifacts["supabase-migration.scaffold.sql"])

    def test_model_mapping_is_deterministic_and_exposes_unresolved_fields(self):
        result = validate_manifest(sample_manifest())

        mapping = build_model_mapping(result)

        self.assertEqual(mapping, build_model_mapping(result))
        self.assertFalse(mapping["writes_performed"])
        self.assertEqual(mapping["manifest_checksum"], result.checksum)
        targets = {(item["django_model"], item["supabase_table"]) for item in mapping["targets"]}
        self.assertIn(("learning.Flashcard", "flashcards"), targets)
        self.assertIn(("learning.Question", "questions"), targets)
        self.assertEqual(mapping["unmapped"][0]["manifest"], "content.active_units[*]")

    def test_model_resolutions_are_checksum_bound_deterministic_and_write_free(self):
        manifest = sample_manifest(status="approved")
        manifest["review"] = {
            "language_reviewer": "language-editor", "license_reviewer": "rights-editor",
            "reviewed_at": "2026-09-01",
        }
        result = validate_manifest(manifest)
        resolutions = sample_resolutions(result.checksum)

        artifact = validate_model_resolutions(result, resolutions, "ED-103", result.checksum)

        self.assertEqual(artifact, validate_model_resolutions(result, resolutions, "ED-103", result.checksum))
        self.assertTrue(artifact["complete"])
        self.assertFalse(artifact["writes_performed"])
        self.assertEqual(len(artifact["resolutions_checksum"]), 64)

    def test_model_resolutions_reject_missing_or_stale_decisions(self):
        manifest = sample_manifest(status="approved")
        manifest["review"] = {
            "language_reviewer": "language-editor", "license_reviewer": "rights-editor",
            "reviewed_at": "2026-09-01",
        }
        result = validate_manifest(manifest)
        resolutions = sample_resolutions(result.checksum)
        resolutions.pop("course_id")
        with self.assertRaisesRegex(ManifestError, "course_id"):
            validate_model_resolutions(result, resolutions, "ED-103", result.checksum)

        resolutions = sample_resolutions("0" * 64)
        with self.assertRaisesRegex(ManifestError, "другому manifest"):
            validate_model_resolutions(result, resolutions, "ED-103", result.checksum)

        resolutions = sample_resolutions(result.checksum)
        resolutions["card_set_lesson_ids"][0] = {"unexpected": "object"}
        with self.assertRaisesRegex(ManifestError, r"card_set_lesson_ids\[0\]"):
            validate_model_resolutions(result, resolutions, "ED-103", result.checksum)

        resolutions = sample_resolutions(result.checksum)
        resolutions["question_lesson_ids"]["final_quiz"] = "example-grammar"
        with self.assertRaisesRegex(ManifestError, "должны быть разными"):
            validate_model_resolutions(result, resolutions, "ED-103", result.checksum)

    def test_executable_preview_is_deterministic_checksum_bound_and_review_only(self):
        manifest = sample_manifest(status="approved")
        manifest["review"] = {
            "language_reviewer": "language-editor", "license_reviewer": "rights-editor",
            "reviewed_at": "2026-09-01",
        }
        result = validate_manifest(manifest)
        resolutions = sample_resolutions(result.checksum)
        checked = validate_model_resolutions(result, resolutions, "ED-104", result.checksum)

        artifacts = build_executable_migration_preview(
            result, resolutions, "ED-104", result.checksum, checked["resolutions_checksum"]
        )

        self.assertEqual(artifacts, build_executable_migration_preview(
            result, resolutions, "ED-104", result.checksum, checked["resolutions_checksum"]
        ))
        metadata = json.loads(artifacts["migration-preview.json"])
        self.assertFalse(metadata["writes_performed"])
        compile(artifacts["candidate-django-runpython.py"], "candidate.py", "exec")
        self.assertIn("RunPython", artifacts["candidate-django-runpython.py"])
        self.assertIn("on conflict", artifacts["candidate-supabase-content.sql"].lower())
        self.assertNotIn("rollback;", artifacts["candidate-supabase-content.sql"].lower())

        with self.assertRaisesRegex(ManifestError, "resolutions изменились"):
            build_executable_migration_preview(
                result, resolutions, "ED-104", result.checksum, "0" * 64
            )

    def test_promotion_receipt_binds_checksums_reviewers_targets_and_order(self):
        manifest = sample_manifest(status="approved")
        manifest["review"] = {
            "language_reviewer": "language-editor", "license_reviewer": "rights-editor",
            "reviewed_at": "2026-09-01",
        }
        result = validate_manifest(manifest)
        resolutions = sample_resolutions(result.checksum)
        checked = validate_model_resolutions(result, resolutions, "ED-105", result.checksum)
        preview = build_executable_migration_preview(
            result, resolutions, "ED-105", result.checksum, checked["resolutions_checksum"]
        )

        artifacts = build_production_promotion_receipt(
            result, resolutions, "ED-105", result.checksum,
            checked["resolutions_checksum"], "0107_example_topic.py",
            "20260914123000_example_topic.sql", "release-reviewer", preview,
        )
        repeated = build_production_promotion_receipt(
            result, resolutions, "ED-105", result.checksum,
            checked["resolutions_checksum"], "0107_example_topic.py",
            "20260914123000_example_topic.sql", "release-reviewer", preview,
        )

        self.assertEqual(artifacts, repeated)
        receipt = json.loads(artifacts["production-promotion-receipt.json"])
        self.assertEqual(receipt["manifest_checksum"], result.checksum)
        self.assertEqual(receipt["resolutions_checksum"], checked["resolutions_checksum"])
        self.assertEqual(receipt["approval_id"], "ED-105")
        self.assertEqual(receipt["reviewers"]["release"], "release-reviewer")
        self.assertEqual(set(receipt["migration_preview_sha256"]), set(preview))
        self.assertEqual([item["order"] for item in receipt["promotion_order"]], [1, 2])
        self.assertTrue(receipt["promotion_order"][0]["target"].endswith(".sql"))
        self.assertTrue(receipt["promotion_order"][1]["target"].endswith(".py"))
        self.assertFalse(receipt["reviewer_boundary"]["writes_performed"])
        self.assertFalse(receipt["reviewer_boundary"]["approved"])
        self.assertEqual(len(receipt["receipt_checksum"]), 64)
        verification = verify_production_promotion_receipt(
            receipt, preview, result.checksum
        )
        self.assertTrue(verification["complete"])
        self.assertFalse(verification["writes_performed"])

        changed_preview = dict(preview)
        changed_preview["candidate-supabase-content.sql"] += "\n-- changed"
        with self.assertRaisesRegex(ManifestError, "изменился после ревью"):
            verify_production_promotion_receipt(
                receipt, changed_preview, result.checksum
            )

    def test_promotion_receipt_rejects_stale_or_unsafe_inputs(self):
        manifest = sample_manifest(status="approved")
        manifest["review"] = {
            "language_reviewer": "language-editor", "license_reviewer": "rights-editor",
            "reviewed_at": "2026-09-01",
        }
        result = validate_manifest(manifest)
        resolutions = sample_resolutions(result.checksum)
        checked = validate_model_resolutions(result, resolutions, "ED-105", result.checksum)
        preview = build_executable_migration_preview(
            result, resolutions, "ED-105", result.checksum, checked["resolutions_checksum"]
        )
        args = (result, resolutions, "ED-105", result.checksum, checked["resolutions_checksum"])

        with self.assertRaisesRegex(ManifestError, "django_migration_filename"):
            build_production_promotion_receipt(
                *args, "../0107_escape.py", "20260914123000_example.sql", "reviewer", preview
            )
        with self.assertRaisesRegex(ManifestError, "supabase_migration_filename"):
            build_production_promotion_receipt(
                *args, "0107_example.py", "/tmp/20260914123000_example.sql", "reviewer", preview
            )
        with self.assertRaisesRegex(ManifestError, "resolutions изменились"):
            build_production_promotion_receipt(
                result, resolutions, "ED-105", result.checksum, "0" * 64,
                "0107_example.py", "20260914123000_example.sql", "reviewer", preview,
            )

        tampered = dict(preview)
        metadata = json.loads(tampered["migration-preview.json"])
        metadata["approval_id"] = "ED-TAMPERED"
        tampered["migration-preview.json"] = json.dumps(metadata)
        with self.assertRaisesRegex(ManifestError, "approval_id"):
            build_production_promotion_receipt(
                *args, "0107_example.py", "20260914123000_example.sql", "reviewer", tampered
            )

    def test_scaffold_writer_rejects_nonempty_and_forbidden_directories(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            nonempty = root / "occupied"
            nonempty.mkdir()
            (nonempty / "keep.txt").write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ManifestError, "новым или пустым"):
                write_migration_scaffold({"safe.txt": "ok"}, nonempty, ())

            forbidden = root / "migrations"
            with self.assertRaisesRegex(ManifestError, "реальный каталог"):
                write_migration_scaffold({"safe.txt": "ok"}, forbidden / "draft", (forbidden,))
            with self.assertRaisesRegex(ManifestError, "Недопустимое имя"):
                write_migration_scaffold({"../escape.txt": "no"}, root / "safe", ())


class ContentWorkflowCommandTests(SimpleTestCase):
    def test_command_writes_preview_artifact_without_database(self):
        with TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "draft.json"
            output_path = Path(directory) / "preview.json"
            manifest_path.write_text(
                json.dumps(sample_manifest(), ensure_ascii=False), encoding="utf-8"
            )

            stdout = StringIO()
            call_command(
                "content_workflow",
                str(manifest_path),
                output=str(output_path),
                stdout=stdout,
            )

            artifact = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(artifact["artifact_type"], "polskiflow-content-preview")
            self.assertIn("Artifact written", stdout.getvalue())

    def test_prepare_publish_rejects_unapproved_draft(self):
        with TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "draft.json"
            manifest_path.write_text(json.dumps(sample_manifest()), encoding="utf-8")

            with self.assertRaisesRegex(CommandError, "status=approved"):
                call_command(
                    "content_workflow",
                    str(manifest_path),
                    prepare_publish=True,
                    approval_id="ED-101",
                )

    def test_generate_scaffold_writes_only_review_artifacts_to_explicit_empty_directory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = sample_manifest(status="approved")
            manifest["review"] = {
                "language_reviewer": "language-editor",
                "license_reviewer": "rights-editor",
                "reviewed_at": "2026-09-01",
            }
            manifest_path = root / "approved.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            checksum = validate_manifest(manifest).checksum
            output = root / "scaffold"

            call_command(
                "content_workflow",
                str(manifest_path),
                generate_scaffold=True,
                approval_id="ED-102",
                expected_checksum=checksum,
                output_directory=str(output),
            )

            metadata = json.loads((output / "scaffold.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["manifest_checksum"], checksum)
            self.assertFalse(metadata["writes_performed"])
            self.assertEqual(len(list(output.iterdir())), 5)
            mapping = json.loads((output / "model-mapping.json").read_text(encoding="utf-8"))
            self.assertFalse(mapping["writes_performed"])

    def test_generate_scaffold_requires_explicit_output_and_checksum(self):
        with TemporaryDirectory() as directory:
            manifest_path = Path(directory) / "approved.json"
            manifest_path.write_text(json.dumps(sample_manifest(status="approved")), encoding="utf-8")
            with self.assertRaisesRegex(CommandError, "требует"):
                call_command("content_workflow", str(manifest_path), generate_scaffold=True)

    def test_check_resolutions_writes_deterministic_report(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = sample_manifest(status="approved")
            manifest["review"] = {
                "language_reviewer": "language-editor", "license_reviewer": "rights-editor",
                "reviewed_at": "2026-09-01",
            }
            result = validate_manifest(manifest)
            manifest_path = root / "approved.json"
            resolutions_path = root / "resolutions.json"
            output_path = root / "resolution-check.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            resolutions_path.write_text(json.dumps(sample_resolutions(result.checksum)), encoding="utf-8")

            call_command(
                "content_workflow", str(manifest_path), check_resolutions=str(resolutions_path),
                approval_id="ED-103", expected_checksum=result.checksum, output=str(output_path),
            )

            artifact = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(artifact["complete"])
            self.assertFalse(artifact["writes_performed"])

    def test_generate_migration_preview_requires_and_writes_review_artifacts(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = sample_manifest(status="approved")
            manifest["review"] = {
                "language_reviewer": "language-editor", "license_reviewer": "rights-editor",
                "reviewed_at": "2026-09-01",
            }
            result = validate_manifest(manifest)
            resolutions = sample_resolutions(result.checksum)
            checked = validate_model_resolutions(result, resolutions, "ED-104", result.checksum)
            manifest_path = root / "approved.json"
            resolutions_path = root / "resolutions.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            resolutions_path.write_text(json.dumps(resolutions), encoding="utf-8")
            output = root / "migration-preview"

            call_command(
                "content_workflow", str(manifest_path), generate_migration_preview=True,
                model_resolutions=str(resolutions_path), approval_id="ED-104",
                expected_checksum=result.checksum,
                expected_resolutions_checksum=checked["resolutions_checksum"],
                output_directory=str(output),
            )

            metadata = json.loads((output / "migration-preview.json").read_text())
            self.assertEqual(metadata["resolutions_checksum"], checked["resolutions_checksum"])
            self.assertEqual(len(list(output.iterdir())), 3)

    def test_generate_promotion_receipt_writes_only_to_external_empty_directory(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = sample_manifest(status="approved")
            manifest["review"] = {
                "language_reviewer": "language-editor", "license_reviewer": "rights-editor",
                "reviewed_at": "2026-09-01",
            }
            result = validate_manifest(manifest)
            resolutions = sample_resolutions(result.checksum)
            checked = validate_model_resolutions(result, resolutions, "ED-105", result.checksum)
            manifest_path = root / "approved.json"
            resolutions_path = root / "resolutions.json"
            output = root / "receipt"
            preview_output = root / "migration-preview"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            resolutions_path.write_text(json.dumps(resolutions), encoding="utf-8")
            write_migration_scaffold(
                build_executable_migration_preview(
                    result, resolutions, "ED-105", result.checksum,
                    checked["resolutions_checksum"],
                ),
                preview_output,
                (),
            )

            call_command(
                "content_workflow", str(manifest_path), generate_promotion_receipt=True,
                model_resolutions=str(resolutions_path), approval_id="ED-105",
                expected_checksum=result.checksum,
                expected_resolutions_checksum=checked["resolutions_checksum"],
                django_migration_filename="0107_example_topic.py",
                supabase_migration_filename="20260914123000_example_topic.sql",
                release_reviewer="release-reviewer", output_directory=str(output),
                migration_preview_directory=str(preview_output),
            )

            receipt = json.loads((output / "production-promotion-receipt.json").read_text())
            self.assertEqual(receipt["approval_id"], "ED-105")
            self.assertEqual(len(receipt["migration_preview_sha256"]), 3)
            self.assertEqual(len(list(output.iterdir())), 1)

            verification_output = StringIO()
            call_command(
                "content_workflow", str(manifest_path),
                verify_promotion_receipt=str(
                    output / "production-promotion-receipt.json"
                ),
                migration_preview_directory=str(preview_output),
                stdout=verification_output,
            )
            self.assertIn('"complete": true', verification_output.getvalue())
