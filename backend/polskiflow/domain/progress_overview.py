"""Selected-level progress and course-wide achievements for history."""

from polskiflow.domain.achievements import build_achievements
from polskiflow.domain.daily_goal_insights import build_daily_goal_insight
from datetime import date, timedelta


def build_progress_overview(dashboard, lesson_tasks, personal_words):
    lesson_ids = {lesson["id"] for lesson in lesson_tasks}
    completed = len(dashboard.all_completed_lesson_ids & lesson_ids)
    level_ids = {lesson["id"] for lesson in lesson_tasks if lesson.get("level") == dashboard.level}
    level_completed = len(dashboard.all_completed_lesson_ids & level_ids)
    achievements = build_achievements(
        completed_lessons=completed,
        streak_days=dashboard.streak_days,
        dictionary_count=len(personal_words or []),
        active_days=dashboard.active_days,
    )
    # Duration is the published lesson estimate, not measured time on task.
    minutes_by_id = {lesson["id"]: lesson.get("minutes") or 5 for lesson in lesson_tasks}
    daily_minutes = {}
    seen = set()
    for result in dashboard.recent_completion_results:
        day, lesson_id = result.get("plan_date"), result.get("lesson_id")
        if (day, lesson_id) in seen:
            continue
        seen.add((day, lesson_id))
        minutes = 5 if lesson_id == "dictionary-practice" else minutes_by_id.get(lesson_id, 0)
        daily_minutes[day] = daily_minutes.get(day, 0) + minutes
    minute_counts = [daily_minutes.get((date.today() - timedelta(days=offset)).isoformat(), 0) for offset in range(27, -1, -1)]
    return {
        "dashboard": dashboard,
        "completed_lessons": level_completed,
        "total_lessons": len(level_ids),
        "progress_percent": round(level_completed / len(level_ids) * 100) if level_ids else 0,
        "course_completed_lessons": completed,
        "course_total_lessons": len(lesson_ids),
        "course_progress_percent": round(completed / len(lesson_ids) * 100) if lesson_ids else 0,
        "dictionary_count": len(personal_words or []),
        "dictionary_available": personal_words is not None,
        "achievements": achievements,
        "unlocked_achievements": sum(item.unlocked for item in achievements),
        "daily_goal_insight": build_daily_goal_insight(
            minute_counts, dashboard.daily_goal_minutes
        ),
    }
