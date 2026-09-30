"""Pure selection logic for a learner's daily plan."""

from datetime import date

from polskiflow.domain.lesson_skills import lesson_skill


DAILY_TASK_LIMIT = 4
DAILY_TIME_MODES = (10, 15, 30)


def build_daily_plan(
    lessons: list[dict],
    *,
    level: str,
    completed_all_time: frozenset[str],
    completed_today: frozenset[str],
    personal_words: list[dict] | None,
    today: date,
    daily_task_limit: int = DAILY_TASK_LIMIT,
    recent_completion_results: tuple[dict, ...] = (),
    time_budget_minutes: int | None = None,
) -> list[dict]:
    """Choose the next lessons and, when useful, an SM-2 review."""

    level_lessons = [lesson for lesson in lessons if lesson.get("level") == level]
    candidates = level_lessons or lessons
    completed_in_plan = [
        lesson for lesson in candidates if lesson["id"] in completed_today
    ]
    unfinished = [
        lesson
        for lesson in candidates
        if lesson["id"] not in completed_all_time
        and lesson["id"] not in completed_today
    ]
    previously_completed = [
        lesson
        for lesson in candidates
        if lesson["id"] in completed_all_time
        and lesson["id"] not in completed_today
    ]
    # Keep today's completed lessons visible when the plan is rebuilt after a
    # lesson. Otherwise they fall behind unfinished lessons and the dashboard
    # appears not to update even though the completion was saved correctly.
    ordered = completed_in_plan + unfinished + previously_completed

    due_count = _due_word_count(personal_words, today)
    can_review = personal_words is not None and len(personal_words) >= 4 and due_count > 0
    lesson_limit = max(1, min(10, daily_task_limit)) - int(can_review)
    plan = [_with_skill(lesson) for lesson in ordered[:lesson_limit]]

    reinforcement = _reinforcement_task(
        candidates,
        recent_completion_results,
        completed_today=completed_today,
        today=today,
    )
    if reinforcement is not None and lesson_limit >= 2:
        plan = [task for task in plan if task["id"] != reinforcement["id"]]
        plan.insert(min(1, len(plan)), reinforcement)
        plan = plan[:lesson_limit]

    if can_review:
        plan.append(
            {
                "id": "dictionary-practice",
                "kind": "dictionary-review",
                "title": "Повторение словаря",
                "description": (
                    f"{due_count} {_russian_word_label(due_count)} по расписанию SM-2"
                ),
                "minutes": min(10, max(3, due_count)),
                "emoji": "🧠",
                "level": level,
            }
        )

    for task in plan:
        task["completed"] = task["id"] in completed_today
    if time_budget_minutes in DAILY_TIME_MODES:
        plan = _fit_time_budget(plan, time_budget_minutes)
    return plan


def _fit_time_budget(plan: list[dict], budget: int) -> list[dict]:
    """Fit pending work to a budget without hiding today's completed tasks."""
    mandatory = [
        task
        for task in plan
        if task.get("completed") is True or task.get("kind") == "dictionary-review"
    ]
    selected_ids = {task["id"] for task in mandatory}
    total = sum(_task_minutes(task) for task in mandatory)
    for task in plan:
        if task["id"] in selected_ids:
            continue
        minutes = _task_minutes(task)
        if selected_ids and total + minutes > budget:
            continue
        selected_ids.add(task["id"])
        total += minutes
    return [task for task in plan if task["id"] in selected_ids] or plan[:1]


def _task_minutes(task: dict) -> int:
    raw_minutes = task.get("minutes")
    if (
        isinstance(raw_minutes, int)
        and not isinstance(raw_minutes, bool)
        and raw_minutes > 0
    ):
        return raw_minutes
    return 5


def _with_skill(lesson: dict) -> dict:
    task = dict(lesson)
    task["skill"] = lesson_skill(task)
    return task


def _reinforcement_task(
    lessons: list[dict],
    results: tuple[dict, ...],
    *,
    completed_today: frozenset[str],
    today: date,
) -> dict | None:
    lesson_by_id = {lesson["id"]: lesson for lesson in lessons}
    candidates = []
    for result in results:
        lesson_id = result.get("lesson_id")
        lesson = lesson_by_id.get(lesson_id)
        total, known = result.get("cards_total"), result.get("cards_known")
        try:
            plan_date = date.fromisoformat(result.get("plan_date", ""))
        except (TypeError, ValueError):
            continue
        if (
            lesson is None
            or lesson_id in completed_today
            or not isinstance(total, int)
            or isinstance(total, bool)
            or total <= 0
            or not isinstance(known, int)
            or isinstance(known, bool)
            or not 0 <= known <= total
            or known / total >= 0.7
            or plan_date >= today
            or (today - plan_date).days > 29
        ):
            continue
        candidates.append((known / total, -plan_date.toordinal(), lesson_id, lesson, known, total))
    if not candidates:
        return None
    _, _, _, lesson, known, total = min(candidates)
    task = _with_skill(lesson)
    skill = task["skill"]
    task.update(
        {
            "title": f"Закрепить: {lesson['title']}",
            "description": f"{skill['label']}: результат {known} из {total} — стоит закрепить",
            "plan_type": "reinforcement",
            "reinforcement_reason": {
                "cards_known": known,
                "cards_total": total,
                "threshold_percent": 70,
                "skill": skill,
            },
        }
    )
    return task


def _due_word_count(words: list[dict] | None, today: date) -> int:
    count = 0
    for word in words or []:
        value = word.get("next_review_date")
        if value in (None, ""):
            count += 1
            continue
        try:
            if not isinstance(value, str) or date.fromisoformat(value) <= today:
                count += 1
        except ValueError:
            count += 1
    return count


def _russian_word_label(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "слово"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "слова"
    return "слов"
