"""Bounded public-content search for the authenticated web application."""

import json
from pathlib import Path

from django.db.models import Q
from django.utils.translation import gettext, get_language

from polskiflow.learning.models import Lesson, ReadingText, Topic


LESSON_KIND_LABELS = {
    "words": "Слова",
    "grammar": "Грамматика",
    "review": "Повторение",
    "quiz": "Тест",
    "reading-check": "Чтение",
}
CATALOG_MESSAGE_IDS = json.loads((Path(__file__).resolve().parent / "localization/catalog_messages.json").read_text())


def search_learning_catalog(query: str, limit: int = 12) -> dict:
    """Search active public metadata only; no learner-owned data is queried."""
    query = " ".join(query.split())[:80]
    if len(query) < 2:
        return {"query": query, "topics": [], "lessons": [], "readings": [], "total": 0}
    # SQLite's case-insensitive lookup only folds ASCII. Including the common
    # sentence-case variant keeps local development and tests useful for
    # Cyrillic queries while PostgreSQL continues to use its native ILIKE.
    variants = tuple(dict.fromkeys((query, query[:1].upper() + query[1:])))
    lookup = Q()
    lesson_lookup = Q()
    for variant in variants:
        lookup |= Q(title__icontains=variant) | Q(description__icontains=variant)
        lesson_lookup |= (
            Q(title__icontains=variant)
            | Q(plan_title__icontains=variant)
            | Q(description__icontains=variant)
        )
    if get_language() in {"pl", "en"}:
        localized_matches = [message for message in CATALOG_MESSAGE_IDS if query.casefold() in gettext(message).casefold()]
        lookup |= Q(title__in=localized_matches) | Q(description__in=localized_matches)
        lesson_lookup |= Q(title__in=localized_matches) | Q(plan_title__in=localized_matches) | Q(description__in=localized_matches)

    topics = [
        {
            "id": topic.id,
            "title": topic.title,
            "description": topic.description,
            "emoji": topic.emoji or "◫",
            "level": topic.course.level,
        }
        for topic in Topic.objects.filter(lookup, is_active=True, course__is_active=True)
        .select_related("course")
        .order_by("course__position", "position", "id")[:limit]
    ]
    lessons = [
        {
            "id": lesson.id,
            "title": lesson.plan_title,
            "description": lesson.description,
            "emoji": lesson.emoji or "✓",
            "level": lesson.topic.course.level,
            "kind_label": LESSON_KIND_LABELS.get(lesson.kind, "Урок"),
            "minutes": lesson.minutes,
        }
        for lesson in Lesson.objects.filter(
            lesson_lookup,
            is_active=True,
            topic__is_active=True,
            topic__course__is_active=True,
        )
        .select_related("topic__course")
        .order_by("topic__course__position", "topic__position", "position", "id")[:limit]
    ]
    readings = [
        {
            "id": reading.id,
            "title": reading.title,
            "description": reading.description,
            "emoji": reading.emoji or "▤",
            "level": reading.level,
            "minutes": reading.minutes,
        }
        for reading in ReadingText.objects.filter(lookup, is_active=True)
        .order_by("level", "position", "id")[:limit]
    ]
    return {
        "query": query,
        "topics": topics,
        "lessons": lessons,
        "readings": readings,
        "total": len(topics) + len(lessons) + len(readings),
    }
