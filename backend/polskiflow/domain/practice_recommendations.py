"""Small daily practice rotation, separate from the complete catalog."""

from polskiflow.domain.b1_weekly_mock import weekly_mock_variant

B2_PRACTICE = (
    {"title": "Аудирование B2: модель гибридной работы", "href": "/listening/#b2-listening", "topics": ("remote-work",)},
    {"title": "Письмо B2: сравни два сообщения", "href": "/writing/?level=B2", "topics": ()},
    {"title": "Общение и медиация B2", "href": "/interaction/#scenario-meeting-position", "topics": ()},
)


def practice_recommendation(level, today, excluded_topics=()):
    if level == "B1":
        variant = weekly_mock_variant(today, excluded_topics)
        return {"title": f"Мини-модуль B1 · {variant.label}", "href": "/exam/b1/mock/"}
    if level == "B2":
        candidates = tuple(item for item in B2_PRACTICE if not set(item["topics"]) & set(excluded_topics))
        return dict(candidates[(today.toordinal() - 1) % len(candidates)]) if candidates else None
    return None
