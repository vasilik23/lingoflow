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
        "href": "/interaction/#speaking-practice",
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


def build_b1_exam_prep(today: date, module_results: tuple[dict, ...] = ()) -> dict:
    """Build a bounded plan, prioritising only honestly measured weak modules."""

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
    focus = _weak_measured_module(module_results)
    if focus is not None:
        focus_id = focus["id"]
        focus_task = next(
            (item for item in daily_plan if item["module_id"] == focus_id),
            {
                "module_id": focus_id,
                "module_title": modules_by_id[focus_id]["title"],
                "action": modules_by_id[focus_id]["action"],
                "minutes": 5,
                "href": modules_by_id[focus_id]["href"],
                "accent": modules_by_id[focus_id]["accent"],
            },
        )
        focus_task = {
            **focus_task,
            "is_focus": True,
            "focus_reason": f"{focus.get('reason_label', 'Последние тренировки')}: {focus['percent']}% — стоит закрепить",
        }
        daily_plan = (
            focus_task,
            *(item for item in daily_plan if item["module_id"] != focus_id),
        )[:3]
    return {
        "countdown": countdown,
        "modules": modules,
        "daily_plan": daily_plan,
        "daily_minutes": sum(item["minutes"] for item in daily_plan),
        "focus": focus,
        "pass_percent": 50,
        "written_minutes": 190,
    }


def _weak_measured_module(module_results: tuple[dict, ...]) -> dict | None:
    weak = [
        item
        for item in module_results
        if item.get("status") == "measured"
        and isinstance(item.get("percent"), int)
        and item["percent"] < 70
    ]
    if not weak:
        return None
    order = {module["id"]: index for index, module in enumerate(B1_EXAM_MODULES)}
    return min(weak, key=lambda item: (item["percent"], order.get(item.get("id"), 99)))


def build_b1_module_results(recent_results: tuple[dict, ...], lesson_tasks: list[dict]) -> tuple[dict, ...]:
    """Summarise measured B1 practice without presenting it as exam readiness."""

    task_by_id = {task.get("id"): task for task in lesson_tasks}
    measured = {"reading": [0, 0, 0], "grammar": [0, 0, 0]}
    for result in recent_results or ():
        task = task_by_id.get(result.get("lesson_id"))
        if not task or task.get("level") != "B1":
            continue
        lesson_id = str(task.get("id", ""))
        if task.get("kind") == "grammar":
            module_id = "grammar"
        elif lesson_id.endswith(("-reading-check", "-check")):
            module_id = "reading"
        else:
            continue
        total = result.get("cards_total")
        known = result.get("cards_known")
        if not isinstance(total, int) or isinstance(total, bool) or total <= 0:
            continue
        if not isinstance(known, int) or isinstance(known, bool) or not 0 <= known <= total:
            continue
        measured[module_id][0] += known
        measured[module_id][1] += total
        measured[module_id][2] += 1

    rows = []
    for module in B1_EXAM_MODULES:
        known, total, attempts = measured.get(module["id"], (0, 0, 0))
        if total:
            rows.append({
                **module,
                "status": "measured",
                "percent": round(known * 100 / total),
                "attempts": attempts,
                "detail": f"{known} из {total} ответов · {attempts} попыток",
            })
        elif module["id"] in measured:
            rows.append({**module, "status": "empty", "percent": None, "attempts": 0})
        else:
            rows.append({**module, "status": "unmeasured", "percent": None, "attempts": 0})
    return tuple(rows)


def overlay_latest_b1_mock(
    module_results: tuple[dict, ...], attempt: dict | None
) -> tuple[dict, ...]:
    """Prefer the latest exam-shaped aggregate for the three checked modules."""

    if not isinstance(attempt, dict):
        return module_results
    specs = {
        "listening": ("listening_correct", 2),
        "reading": ("reading_correct", 2),
        "grammar": ("grammar_correct", 3),
    }
    measured = {}
    for module_id, (field, total) in specs.items():
        correct = attempt.get(field)
        if isinstance(correct, bool) or not isinstance(correct, int) or not 0 <= correct <= total:
            return module_results
        measured[module_id] = {
            "status": "measured",
            "percent": round(correct * 100 / total),
            "attempts": 1,
            "detail": f"Последний мини‑модуль · {correct} из {total}",
            "reason_label": "Последний мини‑модуль",
            "source": "mock",
        }
    return tuple(
        {**item, **measured[item["id"]]} if item["id"] in measured else item
        for item in module_results
    )


def attach_b1_mock_trends(
    module_results: tuple[dict, ...], attempts: list[dict] | tuple[dict, ...]
) -> tuple[dict, ...]:
    """Compare the two newest valid mock points without grading production."""

    specs = {
        "listening": ("listening_correct", 2),
        "reading": ("reading_correct", 2),
        "grammar": ("grammar_correct", 3),
    }
    trends = {}
    for module_id, (field, total) in specs.items():
        points = []
        for attempt in attempts or ():
            if not isinstance(attempt, dict):
                continue
            correct = attempt.get(field)
            if (
                isinstance(correct, bool)
                or not isinstance(correct, int)
                or not 0 <= correct <= total
            ):
                continue
            points.append(round(correct * 100 / total))
            if len(points) == 2:
                break
        if not points:
            trends[module_id] = {"status": "empty"}
            continue
        if len(points) == 1:
            trends[module_id] = {
                "status": "first",
                "current_percent": points[0],
                "label": "Первая точка динамики",
            }
            continue
        delta = points[0] - points[1]
        trends[module_id] = {
            "status": "improved" if delta > 0 else "declined" if delta < 0 else "stable",
            "current_percent": points[0],
            "previous_percent": points[1],
            "delta": delta,
            "label": (
                f"+{delta} п.п. к предыдущей попытке"
                if delta > 0
                else f"{delta} п.п. к предыдущей попытке"
                if delta < 0
                else "Без изменения к предыдущей попытке"
            ),
        }
    return tuple(
        {**item, "trend": trends.get(item["id"], {"status": "unmeasured"})}
        for item in module_results
    )


def _countdown_label(days_remaining: int) -> str:
    if days_remaining == 0:
        return "Экзамен начинается сегодня"
    if days_remaining == 1:
        return "До экзамена остался 1 день"
    if days_remaining % 10 in (2, 3, 4) and days_remaining % 100 not in (12, 13, 14):
        return f"До экзамена осталось {days_remaining} дня"
    return f"До экзамена осталось {days_remaining} дней"
