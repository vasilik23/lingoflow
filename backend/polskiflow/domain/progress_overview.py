"""Selected-level progress and course-wide achievements for history."""

from polskiflow.domain.achievements import build_achievements
from polskiflow.domain.daily_goal_insights import build_daily_goal_insight


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
            dashboard.recent_daily_completion_counts, dashboard.daily_goal_lessons
        ),
    }
