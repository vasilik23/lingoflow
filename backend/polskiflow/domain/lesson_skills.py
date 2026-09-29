"""Deterministic, privacy-safe skill labels derived from public lesson metadata."""


def lesson_skill(lesson: dict) -> dict:
    """Return one stable skill tag without inspecting a learner's answer text."""
    lesson_id = str(lesson.get("id") or "")
    kind = str(lesson.get("kind") or "")
    topic = str(lesson.get("topic_title") or lesson.get("title") or "Тема").strip()
    theory = str(lesson.get("theory_title") or "").strip()
    if kind == "grammar":
        return {"id": f"grammar:{lesson_id}", "label": theory or f"Грамматика: {topic}", "group": "grammar"}
    if lesson_id.endswith(("-reading-check", "-check")):
        return {"id": f"reading-detail:{lesson_id}", "label": f"Понимание деталей: {topic}", "group": "reading"}
    if kind == "words":
        return {"id": f"vocabulary:{lesson_id}", "label": f"Лексика: {topic}", "group": "vocabulary"}
    if kind == "quiz":
        return {"id": f"topic-review:{lesson_id}", "label": f"Применение темы: {topic}", "group": "integrated"}
    if kind == "review":
        return {"id": f"recall:{lesson_id}", "label": f"Активное вспоминание: {topic}", "group": "recall"}
    return {"id": f"lesson:{lesson_id}", "label": topic, "group": "general"}
