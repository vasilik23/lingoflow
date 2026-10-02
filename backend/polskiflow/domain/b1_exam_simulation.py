"""Timed, original B1 section practice without claiming official assessment."""

from polskiflow.domain.b1_weekly_mock import MockVariant


B1_SIMULATION_PARTS = (
    {"id": "listening", "title": "Аудирование", "polish_title": "Rozumienie ze słuchu", "minutes": 25, "accent": "blue", "mode": "objective"},
    {"id": "reading", "title": "Чтение", "polish_title": "Rozumienie tekstów pisanych", "minutes": 45, "accent": "green", "mode": "objective"},
    {"id": "grammar", "title": "Грамматика", "polish_title": "Poprawność gramatyczna", "minutes": 45, "accent": "violet", "mode": "objective"},
    {"id": "writing", "title": "Письмо", "polish_title": "Pisanie", "minutes": 75, "accent": "rose", "mode": "self_review"},
    {"id": "speaking", "title": "Говорение", "polish_title": "Mówienie", "minutes": 15, "accent": "amber", "mode": "self_review"},
)


def get_simulation_part(part_id: str) -> dict | None:
    return next((dict(part) for part in B1_SIMULATION_PARTS if part["id"] == part_id), None)


def simulation_questions(variant: MockVariant, part_id: str) -> tuple:
    return tuple(question for question in variant.questions if question.module == part_id)


def score_simulation_part(variant: MockVariant, part_id: str, answers: dict[str, int]) -> dict:
    """Score exactly one objective section; free production is never graded."""
    part = get_simulation_part(part_id)
    if part is None or part["mode"] != "objective":
        raise ValueError("Эта часть доступна только для самопроверки.")
    questions = simulation_questions(variant, part_id)
    if set(answers) != {question.id for question in questions}:
        raise ValueError("Ответь на все вопросы выбранной части.")
    details = []
    for question in questions:
        selected = answers[question.id]
        if selected not in range(len(question.options)):
            raise ValueError("Выбран недопустимый вариант ответа.")
        details.append({
            "question": question,
            "selected": selected,
            "selected_text": question.options[selected],
            "correct_text": question.options[question.correct],
            "is_correct": selected == question.correct,
        })
    correct = sum(item["is_correct"] for item in details)
    return {
        "correct": correct,
        "total": len(questions),
        "percent": round(correct * 100 / len(questions)),
        "details": tuple(details),
    }
