"""Pure helpers for filtering the server-rendered course catalog."""

from collections.abc import Iterable


LESSON_KINDS = {
    "words": "Слова",
    "grammar": "Грамматика",
    "review": "Повторение",
    "quiz": "Тесты",
}
DURATION_FILTERS = {
    "short": (0, 10),
    "medium": (11, 20),
    "long": (21, None),
}
COMPLETION_FILTERS = {"not-started", "completed"}


def filter_course_topics(
    topics: Iterable[dict],
    *,
    query: str = "",
    topic_id: str = "",
    kind: str = "",
    duration: str = "",
    completion: str = "",
    localize=None,
) -> list[dict]:
    """Return topics containing lessons matching the validated catalog filters."""
    needle = query.strip().casefold()
    result = []
    for topic in topics:
        if topic_id and topic["id"] != topic_id:
            continue
        topic_matches = needle and needle in _search_text(
            topic.get("title", ""), topic.get("description", ""), localize=localize
        )
        matching_lessons = [
            lesson
            for lesson in topic["lessons"]
            if (topic_matches or not needle or needle in _search_text(
                lesson.get("title", ""), lesson.get("description", ""), localize=localize
            ))
            and (not kind or lesson.get("kind") == kind)
            and _matches_duration(lesson.get("minutes", 0), duration)
            and _matches_completion(lesson.get("completed", False), completion)
        ]
        if matching_lessons:
            result.append({**topic, "lessons": matching_lessons})
    return result


def _search_text(*parts: str, localize=None) -> str:
    translated = [localize(part) for part in parts] if localize else []
    return " ".join([*parts, *translated]).casefold()


def _matches_duration(minutes: int, duration: str) -> bool:
    if not duration:
        return True
    minimum, maximum = DURATION_FILTERS[duration]
    return minutes >= minimum and (maximum is None or minutes <= maximum)


def _matches_completion(completed: bool, completion: str) -> bool:
    if completion == "completed":
        return completed
    if completion == "not-started":
        return not completed
    return True
