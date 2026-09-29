"""Presentation-ready plan for the official adult B1 exam format."""

from __future__ import annotations

from datetime import date


B1_EXAM_SESSIONS = (
    {"starts_on": date(2026, 10, 17), "ends_on": date(2026, 10, 18)},
    {"starts_on": date(2026, 12, 5), "ends_on": date(2026, 12, 6)},
    {"starts_on": date(2027, 2, 6), "ends_on": date(2027, 2, 7)},
    {"starts_on": date(2027, 4, 10), "ends_on": date(2027, 4, 11)},
    {"starts_on": date(2027, 6, 12), "ends_on": date(2027, 6, 13)},
    {"starts_on": date(2027, 10, 2), "ends_on": date(2027, 10, 3)},
    {"starts_on": date(2027, 11, 27), "ends_on": date(2027, 11, 28)},
)

B1_EXAM_MODULES = (
    {
        "id": "listening",
        "title": "Аудирование",
        "polish_title": "Rozumienie ze słuchu",
        "duration_minutes": 25,
        "task_count": "4–5 заданий",
        "points": 30,
        "href": "/listening/#b1-listening",
        "action": "Тренировать слух",
        "accent": "blue",
    },
    {
        "id": "reading",
        "title": "Чтение",
        "polish_title": "Rozumienie tekstów pisanych",
        "duration_minutes": 45,
        "task_count": "4–5 заданий",
        "points": 30,
        "href": "/reading/?level=B1",
        "action": "Читать тексты B1",
        "accent": "green",
    },
    {
        "id": "grammar",
        "title": "Грамматика",
        "polish_title": "Poprawność gramatyczna",
        "duration_minutes": 45,
        "task_count": "8 заданий",
        "points": 30,
        "href": "/course/?level=B1&kind=grammar",
        "action": "Повторить грамматику",
        "accent": "violet",
    },
    {
        "id": "writing",
        "title": "Письмо",
        "polish_title": "Pisanie",
        "duration_minutes": 75,
        "task_count": "3 задания",
        "points": 30,
        "href": "/writing/?level=B1",
        "action": "Написать ответ",
        "accent": "rose",
    },
    {
        "id": "speaking",
        "title": "Говорение",
        "polish_title": "Mówienie",
        "duration_minutes": 15,
        "task_count": "3 задания",
        "points": 40,
        "href": "/interaction/#free-production",
        "action": "Подготовить ответ",
        "accent": "amber",
    },
)

_DAILY_PLANS = (
    (
        ("listening", "Прослушай запись B1 без транскрипта", 5),
        ("grammar", "Реши короткий блок грамматики", 5),
        ("speaking", "Ответь вслух и прослушай себя", 5),
    ),
    (
        ("reading", "Прочитай один текст на время", 5),
        ("writing", "Составь план письменного ответа", 5),
        ("grammar", "Повтори одну слабую конструкцию", 5),
    ),
    (
        ("grammar", "Реши задания без подсказок", 5),
        ("speaking", "Подготовь трёхчастный устный ответ", 5),
        ("listening", "Проверь детали короткой записи", 5),
    ),
    (
        ("listening", "Прослушай запись только один раз", 5),
        ("reading", "Найди главную мысль и детали", 5),
        ("writing", "Напиши вступление и завершение", 5),
    ),
    (
        ("writing", "Напиши один экзаменационный абзац", 5),
        ("speaking", "Сформулируй мнение и два аргумента", 5),
        ("grammar", "Исправь типичные окончания", 5),
    ),
    (
        ("reading", "Пройди текст B1 в темпе экзамена", 5),
        ("listening", "Запиши услышанные ключевые факты", 5),
        ("speaking", "Сделай устное резюме текста", 5),
    ),
    (
        ("grammar", "Повтори ошибки прошедшей недели", 5),
        ("writing", "Проверь черновик по чек-листу", 5),
        ("speaking", "Расскажи, что улучшить на следующей неделе", 5),
    ),
)


def build_b1_exam_prep(today: date) -> dict:
    """Build a bounded countdown and a rotating 15-minute practice plan."""

    session = next(
        (item for item in B1_EXAM_SESSIONS if item["ends_on"] >= today),
        None,
    )
    if session is None:
        countdown = {
            "available": False,
            "days_remaining": None,
            "label": "Следующая дата будет добавлена после публикации расписания",
        }
    else:
        days_remaining = max(0, (session["starts_on"] - today).days)
        countdown = {
            "available": True,
            "days_remaining": days_remaining,
            "starts_on": session["starts_on"],
            "ends_on": session["ends_on"],
            "label": _countdown_label(days_remaining),
        }

    modules = tuple(dict(item) for item in B1_EXAM_MODULES)
    modules_by_id = {item["id"]: item for item in modules}
    daily_plan = tuple(
        {
            "module_id": module_id,
            "module_title": modules_by_id[module_id]["title"],
            "action": action,
            "minutes": minutes,
            "href": modules_by_id[module_id]["href"],
            "accent": modules_by_id[module_id]["accent"],
        }
        for module_id, action, minutes in _DAILY_PLANS[today.weekday()]
    )
    return {
        "countdown": countdown,
        "modules": modules,
        "daily_plan": daily_plan,
        "daily_minutes": sum(item["minutes"] for item in daily_plan),
        "pass_percent": 50,
        "written_minutes": 190,
    }


def _countdown_label(days_remaining: int) -> str:
    if days_remaining == 0:
        return "Экзамен начинается сегодня"
    if days_remaining == 1:
        return "До экзамена остался 1 день"
    if days_remaining % 10 in (2, 3, 4) and days_remaining % 100 not in (12, 13, 14):
        return f"До экзамена осталось {days_remaining} дня"
    return f"До экзамена осталось {days_remaining} дней"
