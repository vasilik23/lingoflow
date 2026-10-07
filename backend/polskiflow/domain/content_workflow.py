"""Validation and release planning for course-content drafts.

This module deliberately has no database or network dependencies.  A reviewed
artifact is an input to the normal migration review, not a production writer.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}
STATUSES = {"draft", "review", "approved"}
ORIGINS = {"original", "external"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CHECKSUM_RE = re.compile(r"^[0-9a-f]{64}$")
APPROVAL_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}$")
REVIEWER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._@/-]{0,99}$")
DJANGO_MIGRATION_RE = re.compile(r"^[0-9]{4}_[a-z0-9_]+\.py$")
SUPABASE_MIGRATION_RE = re.compile(r"^[0-9]{14}_[a-z0-9_]+\.sql$")
MIGRATION_PREVIEW_FILES = (
    "migration-preview.json",
    "candidate-django-runpython.py",
    "candidate-supabase-content.sql",
)


class ManifestError(ValueError):
    """Raised when a draft cannot safely enter the editorial workflow."""


@dataclass(frozen=True)
class ValidationResult:
    manifest: dict[str, Any]
    counts: dict[str, int]
    warnings: tuple[str, ...]
    checksum: str


def load_manifest(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ManifestError(f"Не удалось прочитать JSON manifest: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestError("Корень manifest должен быть JSON-объектом.")
    return value


def _require_text(container: dict[str, Any], key: str, location: str) -> str:
    value = container.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"{location}.{key}: требуется непустая строка.")
    return value.strip()


def _require_list(container: dict[str, Any], key: str, location: str) -> list[Any]:
    value = container.get(key)
    if not isinstance(value, list):
        raise ManifestError(f"{location}.{key}: требуется список.")
    return value


def _reject_unknown_keys(container: dict[str, Any], allowed: set[str], location: str) -> None:
    unknown = sorted(set(container) - allowed)
    if unknown:
        raise ManifestError(f"{location}: неизвестные поля: {', '.join(unknown)}.")


def _validate_identified_items(items: list[Any], location: str, ids: set[str]) -> None:
    for index, item in enumerate(items):
        item_location = f"{location}[{index}]"
        if not isinstance(item, dict):
            raise ManifestError(f"{item_location}: требуется объект со стабильным id.")
        item_id = _require_text(item, "id", item_location)
        if not SLUG_RE.fullmatch(item_id):
            raise ManifestError(f"{item_location}.id: используйте lowercase kebab-case.")
        if item_id in ids:
            raise ManifestError(f"{item_location}.id: дублирующийся id {item_id!r}.")
        ids.add(item_id)


def _validate_questions(items: list[Any], location: str, ids: set[str]) -> None:
    _validate_identified_items(items, location, ids)
    for index, item in enumerate(items):
        item_location = f"{location}[{index}]"
        _reject_unknown_keys(item, {"id", "prompt", "options", "answer", "explanation"}, item_location)
        _require_text(item, "prompt", item_location)
        _require_text(item, "explanation", item_location)
        options = _require_list(item, "options", item_location)
        if len(options) < 2 or any(not isinstance(option, str) or not option.strip() for option in options):
            raise ManifestError(f"{item_location}.options: требуется минимум две непустые строки.")
        normalized = [option.strip() for option in options]
        if len(set(normalized)) != len(normalized):
            raise ManifestError(f"{item_location}.options: варианты должны быть уникальны.")
        answer = _require_text(item, "answer", item_location)
        if normalized.count(answer) != 1:
            raise ManifestError(f"{item_location}.answer: ответ должен ссылаться ровно на один вариант.")


def _valid_iso_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def validate_manifest(manifest: dict[str, Any]) -> ValidationResult:
    _reject_unknown_keys(
        manifest,
        {"schema_version", "id", "title", "level", "language", "status", "source", "content", "expected_counts", "review"},
        "manifest",
    )
    if manifest.get("schema_version") != 1:
        raise ManifestError("schema_version: поддерживается только версия 1.")

    draft_id = _require_text(manifest, "id", "manifest")
    if not SLUG_RE.fullmatch(draft_id):
        raise ManifestError("manifest.id: используйте lowercase kebab-case.")
    _require_text(manifest, "title", "manifest")
    if manifest.get("level") not in LEVELS:
        raise ManifestError("manifest.level: ожидается A1, A2, B1, B2, C1 или C2.")
    if manifest.get("language") != "pl":
        raise ManifestError("manifest.language: учебный контент должен иметь значение pl.")
    if manifest.get("status") not in STATUSES:
        raise ManifestError("manifest.status: ожидается draft, review или approved.")

    source = manifest.get("source")
    if not isinstance(source, dict):
        raise ManifestError("manifest.source: требуется карточка источника.")
    origin = source.get("origin")
    if origin not in ORIGINS:
        raise ManifestError("source.origin: ожидается original или external.")
    _require_text(source, "license", "source")
    verified_at = _require_text(source, "verified_at", "source")
    if not _valid_iso_date(verified_at):
        raise ManifestError("source.verified_at: ожидается дата YYYY-MM-DD.")
    if origin == "original":
        if _require_text(source, "created_for", "source") not in {"LingoFlow", "PolskiFlow"}:
            raise ManifestError("source.created_for: оригинал должен быть создан для LingoFlow.")
    else:
        for key in (
            "source_url",
            "source_item_id",
            "author",
            "license_url",
            "retrieved_at",
            "changes",
            "attribution",
            "reviewer",
        ):
            _require_text(source, key, "source")
        if source.get("status") != "approved":
            raise ManifestError("source.status: внешний объект можно готовить только со статусом approved.")
        if not _valid_iso_date(source["retrieved_at"]):
            raise ManifestError("source.retrieved_at: ожидается дата YYYY-MM-DD.")

    content = manifest.get("content")
    if not isinstance(content, dict):
        raise ManifestError("manifest.content: требуется объект содержимого темы.")
    _reject_unknown_keys(
        content,
        {"active_units", "card_sets", "grammar", "exercises", "reading", "final_quiz"},
        "content",
    )
    units = _require_list(content, "active_units", "content")
    card_sets = _require_list(content, "card_sets", "content")
    exercises = _require_list(content, "exercises", "content")
    final_quiz = _require_list(content, "final_quiz", "content")
    grammar = content.get("grammar")
    reading = content.get("reading")
    if not isinstance(grammar, dict) or not grammar.get("summary"):
        raise ManifestError("content.grammar.summary: требуется грамматическое объяснение.")
    _reject_unknown_keys(grammar, {"summary"}, "content.grammar")
    if not isinstance(reading, dict):
        raise ManifestError("content.reading: требуется объект чтения.")
    _reject_unknown_keys(reading, {"paragraphs", "glossary"}, "content.reading")
    paragraphs = _require_list(reading, "paragraphs", "content.reading")
    if any(not isinstance(paragraph, str) or not paragraph.strip() for paragraph in paragraphs):
        raise ManifestError("content.reading.paragraphs: требуются непустые строки.")
    glossary = reading.get("glossary")
    if not isinstance(glossary, dict) or not glossary:
        raise ManifestError("content.reading.glossary: требуется непустой glossary.")
    for form, entry in glossary.items():
        location = f"content.reading.glossary.{form}"
        if not isinstance(form, str) or not form.strip() or not isinstance(entry, dict):
            raise ManifestError("content.reading.glossary: форма и её описание обязательны.")
        _reject_unknown_keys(entry, {"lemma", "translation", "part_of_speech"}, location)
        _require_text(entry, "lemma", location)
        _require_text(entry, "translation", location)
    if any(not isinstance(item, list) for item in card_sets):
        raise ManifestError("content.card_sets: каждый набор должен быть списком карточек.")

    stable_ids: set[str] = set()
    _validate_identified_items(units, "content.active_units", stable_ids)
    for index, unit in enumerate(units):
        _reject_unknown_keys(unit, {"id", "polish", "translation"}, f"content.active_units[{index}]")
    for index, card_set in enumerate(card_sets):
        _validate_identified_items(card_set, f"content.card_sets[{index}]", stable_ids)
        for card_index, card in enumerate(card_set):
            location = f"content.card_sets[{index}][{card_index}]"
            _reject_unknown_keys(card, {"id", "polish", "translation", "example"}, location)
            for key in ("polish", "translation", "example"):
                _require_text(card, key, location)
    _validate_questions(exercises, "content.exercises", stable_ids)
    _validate_questions(final_quiz, "content.final_quiz", stable_ids)

    counts = {
        "active_units": len(units),
        "card_sets": len(card_sets),
        "flashcards": sum(len(item) for item in card_sets),
        "exercises": len(exercises),
        "reading_paragraphs": len(paragraphs),
        "glossary": len(glossary),
        "final_quiz": len(final_quiz),
    }
    expected = manifest.get("expected_counts")
    if not isinstance(expected, dict):
        raise ManifestError("manifest.expected_counts: зафиксируйте ожидаемые количества.")
    for key, actual in counts.items():
        if expected.get(key) != actual:
            raise ManifestError(
                f"expected_counts.{key}: указано {expected.get(key)!r}, фактически {actual}."
            )

    errors = []
    if not 12 <= counts["active_units"] <= 20:
        errors.append("active_units: требуется от 12 до 20 единиц.")
    if counts["card_sets"] != 2 or any(not 5 <= len(item) <= 8 for item in card_sets):
        errors.append("card_sets: требуется два набора по 5–8 карточек.")
    if counts["exercises"] < 5:
        errors.append("exercises: требуется минимум 5 заданий.")
    if counts["final_quiz"] < 8:
        errors.append("final_quiz: требуется минимум 8 вопросов.")
    if not paragraphs:
        errors.append("reading.paragraphs: чтение не может быть пустым.")
    if errors:
        raise ManifestError("\n".join(errors))

    warnings = ()
    if manifest["status"] != "approved":
        warnings = ("Черновик прошёл структурную проверку, но ещё не одобрен к публикации.",)
    canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return ValidationResult(
        manifest=manifest,
        counts=counts,
        warnings=warnings,
        checksum=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def build_preview(result: ValidationResult) -> dict[str, Any]:
    manifest = result.manifest
    return {
        "artifact_type": "polskiflow-content-preview",
        "schema_version": 1,
        "draft": {
            "id": manifest["id"],
            "title": manifest["title"],
            "level": manifest["level"],
            "status": manifest["status"],
            "checksum": result.checksum,
        },
        "source": manifest["source"],
        "counts": result.counts,
        "warnings": list(result.warnings),
        "publishable": manifest["status"] == "approved",
        "boundary": "Preview only: no database, Supabase, migration or network write was performed.",
    }


def build_publish_plan(result: ValidationResult, approval_id: str) -> dict[str, Any]:
    if result.manifest["status"] != "approved":
        raise ManifestError("План публикации доступен только для status=approved.")
    review = result.manifest.get("review")
    if not isinstance(review, dict):
        raise ManifestError("manifest.review: для публикации требуется редакторская проверка.")
    for key in ("language_reviewer", "license_reviewer", "reviewed_at"):
        _require_text(review, key, "review")
    if not _valid_iso_date(review["reviewed_at"]):
        raise ManifestError("review.reviewed_at: ожидается дата YYYY-MM-DD.")
    if not approval_id.strip():
        raise ManifestError("approval_id: требуется идентификатор одобрения.")

    draft_id = result.manifest["id"]
    return {
        "artifact_type": "polskiflow-content-publish-plan",
        "schema_version": 1,
        "draft_id": draft_id,
        "manifest_checksum": result.checksum,
        "approval_id": approval_id.strip(),
        "counts": result.counts,
        "publish_boundary": {
            "writes_performed": False,
            "required_human_steps": [
                "Generate and review one ordered Django data migration from this exact checksum.",
                "Generate and review the matching rerunnable Supabase migration.",
                "Run tests, migration drift check, RLS/grant review, and preview.",
                "Apply only the reviewed Supabase migration, then deploy the matching commit.",
            ],
        },
        "rollback_plan": {
            "strategy": "forward-only corrective migration",
            "scope_key": draft_id,
            "steps": [
                "Disable records introduced by this draft using their stable IDs.",
                "Restore replaced content from the previous reviewed migration if applicable.",
                "Deploy the corrective Django and Supabase migrations together and verify counts.",
            ],
            "note": "Do not edit an applied migration or delete production rows manually.",
        },
    }


def require_publish_approval(
    result: ValidationResult, approval_id: str, expected_checksum: str
) -> str:
    """Verify the human approval boundary against the exact reviewed payload."""
    build_publish_plan(result, approval_id)
    if not APPROVAL_ID_RE.fullmatch(approval_id.strip()):
        raise ManifestError(
            "approval_id: используйте 1–100 букв, цифр или символов . _ : / -."
        )
    checksum = expected_checksum.strip().lower()
    if not CHECKSUM_RE.fullmatch(checksum):
        raise ManifestError("expected_checksum: ожидается полный SHA-256 из 64 символов.")
    if checksum != result.checksum:
        raise ManifestError(
            "expected_checksum: manifest изменился после проверки; запросите новое одобрение."
        )
    return approval_id.strip()


def build_model_mapping(result: ValidationResult) -> dict[str, Any]:
    """Describe the reviewed manifest-to-storage mapping without touching storage."""
    return {
        "artifact_type": "polskiflow-content-model-mapping",
        "schema_version": 1,
        "manifest_checksum": result.checksum,
        "writes_performed": False,
        "targets": [
            {
                "manifest": "manifest.level",
                "django_model": "learning.Course",
                "supabase_table": "courses",
                "operation": "lookup-only",
                "fields": {"level": "level"},
                "required_resolution": "Select exactly one existing course; never create it implicitly.",
            },
            {
                "manifest": "manifest",
                "django_model": "learning.Topic",
                "supabase_table": "topics",
                "operation": "upsert-by-stable-id",
                "fields": {"id": "id", "title": "title"},
                "required_resolution": "course_id, description, emoji, position",
            },
            {
                "manifest": "content.card_sets[*][*]",
                "django_model": "learning.Flashcard",
                "supabase_table": "flashcards",
                "operation": "upsert-by-stable-id",
                "fields": {
                    "id": "id",
                    "polish": "polish",
                    "translation": "translation",
                    "example": "example",
                    "manifest.source": "source_metadata",
                    "array_index": "position",
                },
            },
            {
                "manifest": "content.card_sets[*][*]",
                "django_model": "learning.LessonFlashcard",
                "supabase_table": "lesson_flashcards",
                "operation": "replace-membership-in-manifest-order",
                "fields": {"id": "flashcard_id", "array_index": "position"},
                "required_resolution": "lesson_id for each card set",
            },
            {
                "manifest": "content.grammar",
                "django_model": "learning.Lesson",
                "supabase_table": "lessons",
                "operation": "update-reviewed-lesson",
                "fields": {"summary": "theory_sections"},
                "required_resolution": "lesson id and all required lesson presentation fields",
            },
            {
                "manifest": "content.exercises[*] and content.final_quiz[*]",
                "django_model": "learning.Question",
                "supabase_table": "questions",
                "operation": "replace-for-reviewed-lesson",
                "fields": {
                    "prompt": "prompt",
                    "options": "options",
                    "options.index(answer)": "correct",
                    "explanation": "explanation",
                    "array_index": "position",
                },
                "required_resolution": "lesson_id for exercises and final quiz",
            },
            {
                "manifest": "content.reading",
                "django_model": "learning.ReadingText",
                "supabase_table": "reading_texts",
                "operation": "upsert-by-reviewed-id",
                "fields": {
                    "paragraphs": "paragraphs",
                    "glossary": "glossary",
                    "manifest.level": "level",
                    "manifest.source": "source_metadata",
                },
                "required_resolution": "id, topic_id, title, description, minutes, emoji, position",
            },
        ],
        "unmapped": [
            {
                "manifest": "content.active_units[*]",
                "reason": "Version 1 units contain only IDs and have no lossless current model mapping.",
            }
        ],
        "boundary": (
            "Mapping contract only. Missing resolutions must be reviewed explicitly; no ORM, SQL, "
            "database or network operation is generated or performed."
        ),
    }


def validate_model_resolutions(
    result: ValidationResult,
    resolutions: dict[str, Any],
    approval_id: str,
    expected_checksum: str,
) -> dict[str, Any]:
    """Validate explicit storage decisions without importing models or touching storage."""
    approval_id = require_publish_approval(result, approval_id, expected_checksum)
    if not isinstance(resolutions, dict):
        raise ManifestError("model_resolutions: ожидается JSON-объект.")
    _reject_unknown_keys(
        resolutions,
        {
            "schema_version",
            "manifest_checksum",
            "course_id",
            "topic",
            "card_set_lesson_ids",
            "grammar_lesson",
            "question_lesson_ids",
            "reading",
        },
        "model_resolutions",
    )
    if resolutions.get("schema_version") != 1:
        raise ManifestError("model_resolutions.schema_version: поддерживается только версия 1.")
    if resolutions.get("manifest_checksum") != result.checksum:
        raise ManifestError(
            "model_resolutions.manifest_checksum: resolutions относятся к другому manifest."
        )

    def require_slug(container: dict[str, Any], key: str, location: str) -> str:
        value = _require_text(container, key, location)
        if not SLUG_RE.fullmatch(value):
            raise ManifestError(f"{location}.{key}: используйте lowercase kebab-case.")
        return value

    def require_position(container: dict[str, Any], location: str) -> int:
        value = container.get("position")
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ManifestError(f"{location}.position: ожидается целое число не меньше нуля.")
        return value

    require_slug(resolutions, "course_id", "model_resolutions")
    topic = resolutions.get("topic")
    if not isinstance(topic, dict):
        raise ManifestError("model_resolutions.topic: требуется объект.")
    _reject_unknown_keys(topic, {"description", "emoji", "position"}, "model_resolutions.topic")
    _require_text(topic, "description", "model_resolutions.topic")
    _require_text(topic, "emoji", "model_resolutions.topic")
    require_position(topic, "model_resolutions.topic")

    lesson_fields = {
        "id", "title", "plan_title", "subtitle", "description", "minutes", "emoji",
        "theory_title", "position",
    }
    grammar = resolutions.get("grammar_lesson")
    if not isinstance(grammar, dict):
        raise ManifestError("model_resolutions.grammar_lesson: требуется объект.")
    _reject_unknown_keys(grammar, lesson_fields, "model_resolutions.grammar_lesson")
    require_slug(grammar, "id", "model_resolutions.grammar_lesson")
    for key in ("title", "plan_title", "subtitle", "description", "emoji", "theory_title"):
        _require_text(grammar, key, "model_resolutions.grammar_lesson")
    minutes = grammar.get("minutes")
    if not isinstance(minutes, int) or isinstance(minutes, bool) or minutes <= 0:
        raise ManifestError("model_resolutions.grammar_lesson.minutes: ожидается положительное целое число.")
    require_position(grammar, "model_resolutions.grammar_lesson")

    card_lessons = resolutions.get("card_set_lesson_ids")
    expected_sets = result.counts["card_sets"]
    if not isinstance(card_lessons, list) or len(card_lessons) != expected_sets:
        raise ManifestError(
            f"model_resolutions.card_set_lesson_ids: требуется {expected_sets} lesson ID."
        )
    for index, lesson_id in enumerate(card_lessons):
        if not isinstance(lesson_id, str) or not SLUG_RE.fullmatch(lesson_id):
            raise ManifestError(
                f"model_resolutions.card_set_lesson_ids[{index}]: используйте lowercase kebab-case."
            )
    if len(set(card_lessons)) != len(card_lessons):
        raise ManifestError("model_resolutions.card_set_lesson_ids: lesson ID должны быть уникальны.")

    question_lessons = resolutions.get("question_lesson_ids")
    if not isinstance(question_lessons, dict):
        raise ManifestError("model_resolutions.question_lesson_ids: требуется объект.")
    _reject_unknown_keys(
        question_lessons, {"exercises", "final_quiz"}, "model_resolutions.question_lesson_ids"
    )
    require_slug(question_lessons, "exercises", "model_resolutions.question_lesson_ids")
    require_slug(question_lessons, "final_quiz", "model_resolutions.question_lesson_ids")
    if question_lessons["exercises"] == question_lessons["final_quiz"]:
        raise ManifestError(
            "model_resolutions.question_lesson_ids: exercises и final_quiz должны быть разными уроками."
        )

    reading = resolutions.get("reading")
    if not isinstance(reading, dict):
        raise ManifestError("model_resolutions.reading: требуется объект.")
    _reject_unknown_keys(
        reading,
        {"id", "topic_id", "title", "description", "minutes", "emoji", "position"},
        "model_resolutions.reading",
    )
    require_slug(reading, "id", "model_resolutions.reading")
    topic_id = require_slug(reading, "topic_id", "model_resolutions.reading")
    if topic_id != result.manifest["id"]:
        raise ManifestError("model_resolutions.reading.topic_id: должен совпадать с manifest.id.")
    for key in ("title", "description", "emoji"):
        _require_text(reading, key, "model_resolutions.reading")
    reading_minutes = reading.get("minutes")
    if not isinstance(reading_minutes, int) or isinstance(reading_minutes, bool) or reading_minutes <= 0:
        raise ManifestError("model_resolutions.reading.minutes: ожидается положительное целое число.")
    require_position(reading, "model_resolutions.reading")

    canonical = json.dumps(resolutions, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "artifact_type": "polskiflow-content-model-resolution-check",
        "schema_version": 1,
        "manifest_checksum": result.checksum,
        "resolutions_checksum": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "approval_id": approval_id,
        "complete": True,
        "writes_performed": False,
        "resolutions": resolutions,
        "unmapped": build_model_mapping(result)["unmapped"],
        "boundary": (
            "Resolution check only. IDs and presentation fields are syntactically complete but "
            "their database existence is not verified; no ORM, SQL, database or network operation "
            "was generated or performed."
        ),
    }


def build_executable_migration_preview(
    result: ValidationResult,
    resolutions: dict[str, Any],
    approval_id: str,
    expected_checksum: str,
    expected_resolutions_checksum: str,
) -> dict[str, str]:
    """Render reviewable migration candidates without importing ORM or executing SQL."""
    checked = validate_model_resolutions(
        result, resolutions, approval_id, expected_checksum
    )
    resolutions_checksum = expected_resolutions_checksum.strip().lower()
    if not CHECKSUM_RE.fullmatch(resolutions_checksum):
        raise ManifestError(
            "expected_resolutions_checksum: ожидается полный SHA-256 из 64 символов."
        )
    if resolutions_checksum != checked["resolutions_checksum"]:
        raise ManifestError(
            "expected_resolutions_checksum: resolutions изменились после проверки."
        )

    manifest_json = json.dumps(result.manifest, ensure_ascii=False, sort_keys=True)
    resolutions_json = json.dumps(resolutions, ensure_ascii=False, sort_keys=True)
    metadata = {
        "artifact_type": "polskiflow-content-executable-migration-preview",
        "schema_version": 1,
        "manifest_checksum": result.checksum,
        "resolutions_checksum": resolutions_checksum,
        "approval_id": checked["approval_id"],
        "writes_performed": False,
        "files": {
            "django": "candidate-django-runpython.py",
            "supabase": "candidate-supabase-content.sql",
        },
        "boundary": (
            "Review artifact only. These candidates were not installed, imported, executed, "
            "or written to migration directories. A developer must review schema assumptions, "
            "assign ordered filenames/dependencies, add tests, and approve each real migration."
        ),
    }
    django = f'''"""REVIEW CANDIDATE ONLY — never auto-installed or executed.
Manifest: {result.checksum}
Resolutions: {resolutions_checksum}
Approval: {checked["approval_id"]}
"""
import json

MANIFEST = json.loads({manifest_json!r})
RESOLUTIONS = json.loads({resolutions_json!r})


def forwards(apps, schema_editor):
    Course = apps.get_model("learning", "Course")
    Topic = apps.get_model("learning", "Topic")
    Lesson = apps.get_model("learning", "Lesson")
    Flashcard = apps.get_model("learning", "Flashcard")
    LessonFlashcard = apps.get_model("learning", "LessonFlashcard")
    Question = apps.get_model("learning", "Question")
    ReadingText = apps.get_model("learning", "ReadingText")
    course = Course.objects.get(pk=RESOLUTIONS["course_id"])
    topic_data = RESOLUTIONS["topic"]
    topic, _ = Topic.objects.update_or_create(
        pk=MANIFEST["id"], defaults={{"course": course, "title": MANIFEST["title"],
        "description": topic_data["description"], "emoji": topic_data["emoji"],
        "position": topic_data["position"], "is_active": True}}
    )
    grammar_data = RESOLUTIONS["grammar_lesson"]
    grammar, _ = Lesson.objects.update_or_create(
        pk=grammar_data["id"], defaults={{"topic": topic, "kind": "grammar",
        "title": grammar_data["title"], "plan_title": grammar_data["plan_title"],
        "subtitle": grammar_data["subtitle"], "description": grammar_data["description"],
        "minutes": grammar_data["minutes"], "emoji": grammar_data["emoji"],
        "theory_title": grammar_data["theory_title"],
        "theory_sections": [{{"text": MANIFEST["content"]["grammar"]["summary"]}}],
        "position": grammar_data["position"], "is_active": True}}
    )
    source = MANIFEST["source"]
    for set_position, cards in enumerate(MANIFEST["content"]["card_sets"]):
        lesson = Lesson.objects.get(pk=RESOLUTIONS["card_set_lesson_ids"][set_position])
        LessonFlashcard.objects.filter(lesson=lesson).delete()
        for position, card in enumerate(cards):
            flashcard, _ = Flashcard.objects.update_or_create(
                pk=card["id"], defaults={{"polish": card["polish"],
                "translation": card["translation"], "example": card["example"],
                "source_metadata": source, "position": position, "is_active": True}}
            )
            LessonFlashcard.objects.create(lesson=lesson, flashcard=flashcard, position=position)
    for group in ("exercises", "final_quiz"):
        lesson = Lesson.objects.get(pk=RESOLUTIONS["question_lesson_ids"][group])
        Question.objects.filter(lesson=lesson).delete()
        for position, item in enumerate(MANIFEST["content"][group]):
            Question.objects.create(lesson=lesson, prompt=item["prompt"],
                options=item["options"], correct=item["options"].index(item["answer"]),
                explanation=item["explanation"], position=position, is_active=True)
    reading = RESOLUTIONS["reading"]
    ReadingText.objects.update_or_create(pk=reading["id"], defaults={{"topic": topic,
        "title": reading["title"], "description": reading["description"],
        "level": MANIFEST["level"], "minutes": reading["minutes"], "emoji": reading["emoji"],
        "paragraphs": MANIFEST["content"]["reading"]["paragraphs"],
        "glossary": MANIFEST["content"]["reading"]["glossary"],
        "source_metadata": source, "position": reading["position"], "is_active": True}})


def reverse_noop(apps, schema_editor):
    # Forward-only correction is mandatory; reviewed content is never silently deleted.
    pass


# A developer must add migrations.RunPython(forwards, reverse_noop) manually.
'''
    sql_manifest = json.dumps(result.manifest, ensure_ascii=False, sort_keys=True).replace("'", "''")
    sql_resolutions = json.dumps(resolutions, ensure_ascii=False, sort_keys=True).replace("'", "''")
    delimiter_suffix = result.checksum
    sql_delimiter = f"$pf_{delimiter_suffix}$"
    while sql_delimiter in sql_manifest or sql_delimiter in sql_resolutions:
        delimiter_suffix += "x"
        sql_delimiter = f"$pf_{delimiter_suffix}$"
    sql = f"""-- REVIEW CANDIDATE ONLY — never auto-installed or executed.
-- Manifest: {result.checksum}
-- Resolutions: {resolutions_checksum}
-- Approval: {checked['approval_id']}
begin;
do {sql_delimiter}
declare
  manifest jsonb := '{sql_manifest}'::jsonb;
  resolutions jsonb := '{sql_resolutions}'::jsonb;
  cards jsonb;
  item jsonb;
  lesson_slug text;
  set_index integer;
  item_index integer;
begin
  if not exists (select 1 from courses where id = resolutions->>'course_id') then
    raise exception 'Resolved course does not exist';
  end if;
  insert into topics (id, course_id, title, description, emoji, position, is_active)
  values (manifest->>'id', resolutions->>'course_id', manifest->>'title',
    resolutions#>>'{{topic,description}}', resolutions#>>'{{topic,emoji}}',
    (resolutions#>>'{{topic,position}}')::integer, true)
  on conflict (id) do update set course_id=excluded.course_id, title=excluded.title,
    description=excluded.description, emoji=excluded.emoji, position=excluded.position, is_active=true;

  insert into lessons (id, topic_id, kind, title, plan_title, subtitle, description,
    minutes, emoji, theory_title, theory_sections, position, is_active, source_metadata)
  values (resolutions#>>'{{grammar_lesson,id}}', manifest->>'id', 'grammar',
    resolutions#>>'{{grammar_lesson,title}}', resolutions#>>'{{grammar_lesson,plan_title}}',
    resolutions#>>'{{grammar_lesson,subtitle}}', resolutions#>>'{{grammar_lesson,description}}',
    (resolutions#>>'{{grammar_lesson,minutes}}')::integer,
    resolutions#>>'{{grammar_lesson,emoji}}', resolutions#>>'{{grammar_lesson,theory_title}}',
    jsonb_build_array(jsonb_build_object('text', manifest#>>'{{content,grammar,summary}}')),
    (resolutions#>>'{{grammar_lesson,position}}')::integer, true, '{{}}'::jsonb)
  on conflict (id) do update set topic_id=excluded.topic_id, kind=excluded.kind,
    title=excluded.title, plan_title=excluded.plan_title, subtitle=excluded.subtitle,
    description=excluded.description, minutes=excluded.minutes, emoji=excluded.emoji,
    theory_title=excluded.theory_title, theory_sections=excluded.theory_sections,
    position=excluded.position, is_active=true;

  for cards, set_index in select value, ordinality - 1 from
    jsonb_array_elements(manifest#>'{{content,card_sets}}') with ordinality loop
    lesson_slug := resolutions#>>array['card_set_lesson_ids', set_index::text];
    if not exists (select 1 from lessons where id=lesson_slug) then
      raise exception 'Resolved card-set lesson does not exist: %', lesson_slug;
    end if;
    delete from lesson_flashcards where lesson_id=lesson_slug;
    for item, item_index in select value, ordinality - 1 from
      jsonb_array_elements(cards) with ordinality loop
      insert into flashcards (id, polish, translation, example, source_metadata, position, is_active)
      values (item->>'id', item->>'polish', item->>'translation', item->>'example',
        manifest->'source', item_index, true)
      on conflict (id) do update set polish=excluded.polish, translation=excluded.translation,
        example=excluded.example, source_metadata=excluded.source_metadata,
        position=excluded.position, is_active=true;
      insert into lesson_flashcards (lesson_id, flashcard_id, position)
      values (lesson_slug, item->>'id', item_index);
    end loop;
  end loop;

  foreach lesson_slug in array array[resolutions#>>'{{question_lesson_ids,exercises}}',
    resolutions#>>'{{question_lesson_ids,final_quiz}}'] loop
    if not exists (select 1 from lessons where id=lesson_slug) then
      raise exception 'Resolved question lesson does not exist: %', lesson_slug;
    end if;
  end loop;
  for lesson_slug, cards in select resolutions#>>'{{question_lesson_ids,exercises}}',
    manifest#>'{{content,exercises}}' union all select
    resolutions#>>'{{question_lesson_ids,final_quiz}}', manifest#>'{{content,final_quiz}}' loop
    delete from questions where lesson_id=lesson_slug;
    for item, item_index in select value, ordinality - 1 from
      jsonb_array_elements(cards) with ordinality loop
      insert into questions (lesson_id, prompt, options, correct, explanation, position, is_active)
      select lesson_slug, item->>'prompt', item->'options', answer.ordinality - 1,
        item->>'explanation', item_index, true from
        jsonb_array_elements_text(item->'options') with ordinality answer(value, ordinality)
        where answer.value=item->>'answer';
    end loop;
  end loop;

  insert into reading_texts (id, topic_id, title, description, level, minutes, emoji,
    paragraphs, glossary, source_metadata, position, is_active)
  values (resolutions#>>'{{reading,id}}', manifest->>'id', resolutions#>>'{{reading,title}}',
    resolutions#>>'{{reading,description}}', manifest->>'level',
    (resolutions#>>'{{reading,minutes}}')::integer, resolutions#>>'{{reading,emoji}}',
    manifest#>'{{content,reading,paragraphs}}', manifest#>'{{content,reading,glossary}}',
    manifest->'source', (resolutions#>>'{{reading,position}}')::integer, true)
  on conflict (id) do update set topic_id=excluded.topic_id, title=excluded.title,
    description=excluded.description, level=excluded.level, minutes=excluded.minutes,
    emoji=excluded.emoji, paragraphs=excluded.paragraphs, glossary=excluded.glossary,
    source_metadata=excluded.source_metadata, position=excluded.position, is_active=true;
end
{sql_delimiter};
commit;
"""
    return {
        "migration-preview.json": json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        "candidate-django-runpython.py": django,
        "candidate-supabase-content.sql": sql,
    }


def build_production_promotion_receipt(
    result: ValidationResult,
    resolutions: dict[str, Any],
    approval_id: str,
    expected_checksum: str,
    expected_resolutions_checksum: str,
    django_migration_filename: str,
    supabase_migration_filename: str,
    release_reviewer: str,
    migration_preview_artifacts: dict[str, str],
) -> dict[str, str]:
    """Bind reviewed inputs to exact production targets without publishing them."""
    checked = validate_model_resolutions(
        result, resolutions, approval_id, expected_checksum
    )
    resolutions_checksum = expected_resolutions_checksum.strip().lower()
    if not CHECKSUM_RE.fullmatch(resolutions_checksum):
        raise ManifestError(
            "expected_resolutions_checksum: ожидается полный SHA-256 из 64 символов."
        )
    if resolutions_checksum != checked["resolutions_checksum"]:
        raise ManifestError(
            "expected_resolutions_checksum: resolutions изменились после проверки."
        )

    django_filename = django_migration_filename.strip()
    supabase_filename = supabase_migration_filename.strip()
    reviewer = release_reviewer.strip()
    if not DJANGO_MIGRATION_RE.fullmatch(django_filename):
        raise ManifestError(
            "django_migration_filename: ожидается basename вида 0107_topic_name.py."
        )
    if not SUPABASE_MIGRATION_RE.fullmatch(supabase_filename):
        raise ManifestError(
            "supabase_migration_filename: ожидается basename вида YYYYMMDDHHMMSS_topic_name.sql."
        )
    if not REVIEWER_ID_RE.fullmatch(reviewer):
        raise ManifestError(
            "release_reviewer: используйте 1–100 букв, цифр или символов . _ @ / -."
        )

    if set(migration_preview_artifacts) != set(MIGRATION_PREVIEW_FILES):
        raise ManifestError("migration preview: ожидаются ровно три штатных файла.")
    try:
        preview_metadata = json.loads(
            migration_preview_artifacts["migration-preview.json"]
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise ManifestError("migration preview: повреждён metadata JSON.") from exc
    expected_metadata = {
        "artifact_type": "polskiflow-content-executable-migration-preview",
        "manifest_checksum": result.checksum,
        "resolutions_checksum": resolutions_checksum,
        "approval_id": checked["approval_id"],
    }
    for key, expected in expected_metadata.items():
        if preview_metadata.get(key) != expected:
            raise ManifestError(f"migration preview: {key} не совпадает с approval.")
    if preview_metadata.get("files") != {
        "django": "candidate-django-runpython.py",
        "supabase": "candidate-supabase-content.sql",
    }:
        raise ManifestError("migration preview: metadata содержит неожиданные имена файлов.")
    preview_hashes = {
        filename: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for filename, content in sorted(migration_preview_artifacts.items())
    }

    receipt = {
        "artifact_type": "polskiflow-content-production-promotion-receipt",
        "schema_version": 1,
        "draft_id": result.manifest["id"],
        "manifest_checksum": result.checksum,
        "resolutions_checksum": resolutions_checksum,
        "approval_id": checked["approval_id"],
        "reviewers": {
            "language": result.manifest["review"]["language_reviewer"],
            "license": result.manifest["review"]["license_reviewer"],
            "release": reviewer,
        },
        "migration_preview_sha256": preview_hashes,
        "promotion_order": [
            {
                "order": 1,
                "action": "apply-reviewed-supabase-migration",
                "target": f"supabase/migrations/{supabase_filename}",
            },
            {
                "order": 2,
                "action": "deploy-commit-containing-django-migration",
                "target": f"backend/polskiflow/learning/migrations/{django_filename}",
            },
        ],
        "reviewer_boundary": {
            "approved": False,
            "writes_performed": False,
            "required_confirmation": (
                "The release reviewer must confirm that both exact target files were manually "
                "reviewed, checks passed, and the Supabase migration is applied before the "
                "matching Django commit is deployed."
            ),
        },
        "boundary": (
            "Audit receipt only. It inspects and hashes the three review-preview files but does "
            "not create, copy, import, execute, apply, "
            "or deploy either target and performs no database or network writes."
        ),
    }
    canonical = json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    receipt["receipt_checksum"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "production-promotion-receipt.json": json.dumps(
            receipt, ensure_ascii=False, indent=2, sort_keys=True
        ) + "\n"
    }


def load_migration_preview_artifacts(
    directory: str | Path, project_root: str | Path
) -> dict[str, str]:
    """Read the exact preview bundle outside the repository without following symlinks."""
    root = Path(directory)
    if root.is_symlink() or not root.is_dir():
        raise ManifestError("migration preview directory: требуется обычный каталог.")
    resolved = root.resolve()
    repository = Path(project_root).resolve()
    if resolved == repository or repository in resolved.parents:
        raise ManifestError("migration preview directory должен находиться вне корня проекта.")
    if {path.name for path in root.iterdir()} != set(MIGRATION_PREVIEW_FILES):
        raise ManifestError("migration preview: ожидаются ровно три штатных файла.")
    artifacts = {}
    for filename in MIGRATION_PREVIEW_FILES:
        path = root / filename
        if path.is_symlink() or not path.is_file():
            raise ManifestError("migration preview: symlink и специальные файлы запрещены.")
        try:
            artifacts[filename] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise ManifestError(f"migration preview: не удалось прочитать {filename}.") from exc
    return artifacts


def verify_production_promotion_receipt(
    receipt: dict[str, Any], migration_preview_artifacts: dict[str, str], manifest_checksum: str
) -> dict[str, Any]:
    """Detect accidental receipt or preview drift before the manual promotion step."""
    if not isinstance(receipt, dict):
        raise ManifestError("promotion receipt: ожидается JSON-объект.")
    supplied_checksum = receipt.get("receipt_checksum")
    unsigned = {key: value for key, value in receipt.items() if key != "receipt_checksum"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    calculated = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if supplied_checksum != calculated:
        raise ManifestError("promotion receipt: checksum не совпадает.")
    if receipt.get("manifest_checksum") != manifest_checksum:
        raise ManifestError("promotion receipt: manifest checksum не совпадает.")
    expected_hashes = receipt.get("migration_preview_sha256")
    actual_hashes = {
        filename: hashlib.sha256(content.encode("utf-8")).hexdigest()
        for filename, content in sorted(migration_preview_artifacts.items())
    }
    if expected_hashes != actual_hashes:
        raise ManifestError("promotion receipt: migration preview изменился после ревью.")
    return {
        "artifact_type": "polskiflow-content-production-promotion-verification",
        "schema_version": 1,
        "receipt_checksum": supplied_checksum,
        "manifest_checksum": manifest_checksum,
        "complete": True,
        "writes_performed": False,
        "boundary": "Integrity verification only; this is not a signature or publication approval.",
    }


def build_migration_scaffold(
    result: ValidationResult, approval_id: str, expected_checksum: str
) -> dict[str, str]:
    """Build deterministic, deliberately non-executable migration review artifacts."""
    approval_id = require_publish_approval(result, approval_id, expected_checksum)
    manifest = result.manifest
    metadata = {
        "artifact_type": "polskiflow-content-migration-scaffold",
        "schema_version": 1,
        "draft_id": manifest["id"],
        "manifest_checksum": result.checksum,
        "approval_id": approval_id,
        "counts": result.counts,
        "files": {
            "payload": "approved-manifest.json",
            "mapping": "model-mapping.json",
            "django": "django-data-migration.scaffold.py",
            "supabase": "supabase-migration.scaffold.sql",
        },
        "writes_performed": False,
        "boundary": (
            "Review-only scaffold. It is not an ordered migration and contains no database "
            "operations. A developer must map the exact payload to current models/schema, "
            "review IDs, reverse/forward behavior, RLS and grants."
        ),
    }
    payload = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    mapping = json.dumps(build_model_mapping(result), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    django = (
        '"""REVIEW SCAFFOLD ONLY — do not copy into migrations without completing TODOs.\n\n'
        f"Manifest: {result.checksum}\nApproval: {approval_id}\n"
        'This file intentionally performs no ORM or database operations.\n"""\n\n'
        f'MANIFEST_CHECKSUM = "{result.checksum}"\n'
        f"APPROVAL_ID = {approval_id!r}\n"
        f"DRAFT_ID = {manifest['id']!r}\n"
        'PAYLOAD_FILE = "approved-manifest.json"\n\n'
        "# TODO: choose the next ordered Django migration and its exact dependency.\n"
        "# TODO: map every payload object to current models using stable, reviewed IDs.\n"
        "# TODO: implement deterministic forwards and a safe forward-only correction plan.\n"
        "# TODO: add count, metadata, ordering, glossary and route regression tests.\n"
    )
    sql = (
        "-- REVIEW SCAFFOLD ONLY — contains no executable SQL.\n"
        f"-- Manifest: {result.checksum}\n"
        f"-- Approval: {approval_id}\n"
        f"-- Draft: {manifest['id']}\n"
        "-- Payload: approved-manifest.json\n\n"
        "-- TODO: choose the matching ordered Supabase migration filename.\n"
        "-- TODO: map stable IDs to the reviewed schema; use rerunnable operations where safe.\n"
        "-- TODO: review conflicts, rollback/correction behavior, RLS and grants.\n"
        "-- TODO: assert expected row counts before applying the reviewed migration.\n"
    )
    return {
        "scaffold.json": metadata_json,
        "approved-manifest.json": payload,
        "model-mapping.json": mapping,
        "django-data-migration.scaffold.py": django,
        "supabase-migration.scaffold.sql": sql,
    }


def write_migration_scaffold(
    artifacts: dict[str, str], output_directory: str | Path, forbidden_directories: tuple[Path, ...]
) -> Path:
    """Write artifacts only to a new or empty directory outside real migration trees."""
    output = Path(output_directory).expanduser().resolve()
    forbidden = tuple(path.resolve() for path in forbidden_directories)
    if any(output == path or path in output.parents for path in forbidden):
        raise ManifestError("output_directory: нельзя писать scaffold в реальный каталог миграций.")
    if output.exists():
        if not output.is_dir():
            raise ManifestError("output_directory: ожидается каталог, а не файл.")
        if any(output.iterdir()):
            raise ManifestError("output_directory: каталог должен быть новым или пустым.")
    else:
        output.mkdir(parents=True)
    for filename, body in artifacts.items():
        target = (output / filename).resolve()
        if target.parent != output:
            raise ManifestError("Недопустимое имя scaffold-артефакта.")
        target.write_text(body, encoding="utf-8", newline="\n")
    return output
