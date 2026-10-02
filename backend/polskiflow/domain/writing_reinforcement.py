"""Deterministic B1 lesson links for browser-local writing self-review."""


_LESSONS = {
    "bio": ("bio-grammar", "Вид и прошедшее время"),
    "travel": ("b1trip-grammar", "Падежи и направление движения"),
    "work": ("b1work-grammar", "Условные формы и официальный регистр"),
    "education": ("b1edu-grammar", "Союзы и косвенная речь"),
    "relationships": ("b1rel-grammar", "Сравнение и относительные конструкции"),
    "health": ("b1health-grammar", "Рекомендации и вид глагола"),
    "media": ("b1media-grammar", "Ясный пересказ и глаголы речи"),
    "society": ("b1soc-grammar", "Аргумент и уступка"),
    "final": ("b1final-grammar", "Связный проект B1"),
}

_FOCUS_TO_LESSON = {
    "вежливая просьба": "work",
    "будущее время": "final",
    "официальное обращение": "work",
    "окончания падежей": "travel",
    "местный падеж": "travel",
    "согласование прилагательных": "relationships",
    "формы совета": "health",
    "связки аргументации": "society",
    "управление после связок": "society",
    "условные конструкции": "work",
    "сравнение": "relationships",
    "связность абзацев": "final",
    "дательный падеж": "relationships",
    "управление gratulować": "relationships",
    "формы предложения": "health",
    "неофициальное обращение": "relationships",
    "безличные конструкции": "health",
    "винительный падеж": "travel",
    "предлоги времени": "bio",
    "лаконичный регистр": "media",
    "творительный падеж": "relationships",
    "относительные предложения": "relationships",
    "прошедшее время": "bio",
    "вид глагола": "bio",
    "род глагольных форм": "bio",
    "временные связки": "bio",
}


def writing_focus_recommendation(focus: str) -> dict:
    """Map a public self-review label to one stable B1 grammar lesson."""
    lesson_key = _FOCUS_TO_LESSON.get(focus, "final")
    lesson_id, lesson_title = _LESSONS[lesson_key]
    return {
        "label": focus,
        "lesson_id": lesson_id,
        "lesson_title": lesson_title,
    }


def enrich_writing_prompts(prompts: tuple[dict, ...]) -> tuple[dict, ...]:
    """Add links metadata without changing the shared/API prompt contract."""
    return tuple({
        **prompt,
        "grammar_recommendations": tuple(
            writing_focus_recommendation(focus)
            for focus in prompt.get("grammar_focus", ())
        ),
    } for prompt in prompts)
