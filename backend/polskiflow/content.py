"""Database-backed lesson content queries."""

from copy import deepcopy

from django.core.cache import cache
from django.db import connection
from django.db.models import Prefetch

from polskiflow.learning.models import Course, Flashcard, Lesson, ReadingText, Topic


def tasks() -> list[dict]:
    rows = Lesson.objects.filter(is_active=True).values(
        "id", "kind", "title", "plan_title", "subtitle", "description",
        "minutes", "emoji", "theory_title", "topic__title", "topic__course__level",
    )
    result = []
    for row in rows:
        level = row.pop("topic__course__level") or "A1"
        topic_title = row.pop("topic__title") or ""
        result.append({**row, "level": level, "topic_title": topic_title})
    return result


def task(lesson_id: str) -> dict | None:
    lesson = Lesson.objects.filter(id=lesson_id, is_active=True).first()
    if lesson is None:
        return None
    return {
        "id": lesson.id,
        "kind": lesson.kind,
        "title": lesson.title,
        "plan_title": lesson.plan_title,
        "subtitle": lesson.subtitle,
        "description": lesson.description,
        "minutes": lesson.minutes,
        "emoji": lesson.emoji,
    }


def lesson_navigation(lesson_id: str) -> dict | None:
    """Return public navigation metadata for a lesson and its next topic lesson."""
    lesson = (
        Lesson.objects.filter(id=lesson_id, is_active=True, topic__is_active=True)
        .select_related("topic__course")
        .first()
    )
    if lesson is None:
        return None
    next_lesson = (
        Lesson.objects.filter(
            topic_id=lesson.topic_id,
            is_active=True,
            position__gt=lesson.position,
        )
        .order_by("position", "id")
        .only("id", "plan_title", "description", "emoji", "minutes")
        .first()
    )
    return {
        "level": lesson.topic.course.level or "A1",
        "topic_id": lesson.topic_id,
        "topic_title": lesson.topic.title,
        "next_lesson": (
            {
                "id": next_lesson.id,
                "title": next_lesson.plan_title,
                "description": next_lesson.description,
                "emoji": next_lesson.emoji,
                "minutes": next_lesson.minutes,
            }
            if next_lesson
            else None
        ),
    }


def course_topics() -> list[dict]:
    """Return an isolated copy of the public catalog cached for five minutes."""
    if str(connection.settings_dict.get("NAME", "")).startswith("file:memorydb"):
        return _load_course_topics()
    return deepcopy(cache.get_or_set("course-topics:v2", _load_course_topics, 300))


def public_course_catalog() -> list[dict]:
    """Return active public catalog metadata without any learner-owned data."""
    if str(connection.settings_dict.get("NAME", "")).startswith("file:memorydb"):
        return _load_public_course_catalog()
    return deepcopy(
        cache.get_or_set("public-course-catalog:v1", _load_public_course_catalog, 300)
    )


def _load_public_course_catalog() -> list[dict]:
    active_lessons = (
        Lesson.objects.filter(is_active=True)
        .only(
            "id",
            "topic_id",
            "kind",
            "title",
            "description",
            "minutes",
            "emoji",
            "position",
        )
        .order_by("position", "id")
    )
    active_topics = (
        Topic.objects.filter(is_active=True)
        .only(
            "id",
            "course_id",
            "title",
            "description",
            "emoji",
            "position",
        )
        .prefetch_related(
            Prefetch("lessons", queryset=active_lessons, to_attr="active_lessons")
        )
        .order_by("position", "id")
    )
    courses = (
        Course.objects.filter(is_active=True)
        .only("id", "title", "description", "level", "position")
        .prefetch_related(
            Prefetch("topics", queryset=active_topics, to_attr="active_topics")
        )
        .order_by("position", "id")
    )
    return [
        {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "level": course.level,
            "position": course.position,
            "topics": [
                {
                    "id": topic.id,
                    "title": topic.title,
                    "description": topic.description,
                    "emoji": topic.emoji,
                    "position": topic.position,
                    "lessons": [
                        {
                            "id": lesson.id,
                            "title": lesson.title,
                            "description": lesson.description,
                            "kind": lesson.kind,
                            "minutes": lesson.minutes,
                            "emoji": lesson.emoji,
                            "position": lesson.position,
                        }
                        for lesson in topic.active_lessons
                    ],
                }
                for topic in course.active_topics
                if topic.active_lessons
            ],
        }
        for course in courses
        if any(topic.active_lessons for topic in course.active_topics)
    ]


def _load_course_topics() -> list[dict]:
    active_lessons = (
        Lesson.objects.filter(is_active=True)
        .only("id", "topic_id", "kind", "title", "description", "minutes", "emoji", "position")
        .order_by("position", "id")
    )
    topics = (
        Topic.objects.filter(is_active=True, course__is_active=True)
        .select_related("course")
        .only("id", "title", "description", "emoji", "position", "course__level", "course__position")
        .prefetch_related(
            Prefetch("lessons", queryset=active_lessons, to_attr="active_lessons")
        )
        .order_by("course__position", "course_id", "position", "id")
    )
    return [
        {
            "id": topic.id,
            "title": topic.title,
            "description": topic.description,
            "emoji": topic.emoji,
            "level": topic.course.level,
            "lessons": [
                {
                    "id": lesson.id,
                    "kind": lesson.kind,
                    "title": lesson.title,
                    "description": lesson.description,
                    "minutes": lesson.minutes,
                    "emoji": lesson.emoji,
                }
                for lesson in topic.active_lessons
            ],
        }
        for topic in topics
        if topic.active_lessons
    ]


def flashcards(lesson_id: str | None = None) -> list[dict]:
    queryset = Flashcard.objects.filter(is_active=True)
    if lesson_id is not None:
        queryset = queryset.filter(
            lesson_links__lesson_id=lesson_id,
            lesson_links__lesson__is_active=True,
        ).order_by("lesson_links__position", "id")
    return list(
        queryset.values(
            "id", "polish", "translation", "example"
        )
    )


def grammar(lesson_id: str = "grammar") -> dict | None:
    lesson = Lesson.objects.filter(id=lesson_id, is_active=True).first()
    if lesson is None:
        return None
    return {
        "title": lesson.theory_title,
        "sections": lesson.theory_sections,
        "questions": _questions(lesson),
    }


def quiz(lesson_id: str = "quiz") -> list[dict]:
    lesson = Lesson.objects.filter(id=lesson_id, is_active=True).first()
    return _questions(lesson) if lesson else []


def _questions(lesson: Lesson) -> list[dict]:
    return list(
        lesson.questions.filter(is_active=True).values(
            "prompt", "options", "correct", "explanation"
        )
    )


def reading_texts() -> list[dict]:
    rows = ReadingText.objects.filter(is_active=True).values(
        "id", "title", "description", "level", "minutes", "emoji",
        "topic_id", "topic__title",
    )
    return [
        {
            **{key: value for key, value in row.items() if key != "topic__title"},
            "topic_title": row["topic__title"] or "Без темы",
        }
        for row in rows
    ]


def reading_text(text_id: str) -> ReadingText | None:
    return ReadingText.objects.filter(id=text_id, is_active=True).first()
