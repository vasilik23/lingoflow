"""Canonical minute goals, with a bounded bridge for older clients."""

DAILY_GOAL_MINUTES = (10, 15, 30)


def minutes_from_legacy_lessons(lessons):
    return 10 if lessons <= 2 else 15 if lessons <= 4 else 30


def legacy_lessons_from_minutes(minutes):
    return minutes // 5
