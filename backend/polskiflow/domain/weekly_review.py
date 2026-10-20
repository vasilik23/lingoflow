"""Transparent weekly review derived from owner-scoped lesson results."""

from datetime import date, datetime, timedelta


def build_weekly_review(dashboard, lessons: list[dict], today: date | None = None) -> dict:
    today = today or date.today()
    cutoff = today - timedelta(days=6)
    lesson_map = {lesson.get("id"): lesson for lesson in lessons}
    latest: dict[str, dict] = {}
    for result in dashboard.recent_completion_results or ():
        lesson_id = result.get("lesson_id")
        try:
            plan_date = datetime.strptime(result.get("plan_date", ""), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            continue
        known, total = result.get("cards_known"), result.get("cards_total")
        if (
            lesson_id not in lesson_map or not cutoff <= plan_date <= today
            or isinstance(known, bool) or isinstance(total, bool)
            or not isinstance(known, int) or not isinstance(total, int)
            or total <= 0 or not 0 <= known <= total
        ):
            continue
        previous = latest.get(lesson_id)
        if previous is None or plan_date > previous["date"]:
            latest[lesson_id] = {"date": plan_date, "known": known, "total": total}

    items = []
    self_known = self_total = 0
    for lesson_id, result in latest.items():
        lesson = lesson_map[lesson_id]
        if lesson.get("kind") in {"words", "review"}:
            self_known += result["known"]
            self_total += result["total"]
            continue
        if lesson.get("kind") not in {"grammar", "quiz", "reading-check"}:
            continue
        accuracy = round(result["known"] / result["total"] * 100)
        items.append({
            "id": lesson_id,
            "title": lesson.get("plan_title") or lesson.get("title") or "Урок",
            "emoji": lesson.get("emoji") or "✓",
            "level": lesson.get("level") or dashboard.level,
            "known": result["known"], "total": result["total"], "accuracy": accuracy,
        })
    strongest = sorted(
        (item for item in items if item["accuracy"] >= 80),
        key=lambda item: (-item["accuracy"], item["title"], item["id"]),
    )[:3]
    reinforcement = sorted(
        (item for item in items if item["accuracy"] < 70),
        key=lambda item: (item["accuracy"], item["title"], item["id"]),
    )[:3]
    known = sum(item["known"] for item in items)
    total = sum(item["total"] for item in items)
    return {
        "available": dashboard.available, "has_results": bool(items),
        "accuracy": round(known / total * 100) if total else None,
        "answer_count": total, "self_known": self_known, "self_total": self_total,
        "reviewed_lessons": len(items), "active_days": dashboard.weekly_active_days,
        "completed_lessons": dashboard.weekly_completed_count,
        "completed_delta": dashboard.weekly_completed_delta,
        "strongest": strongest, "reinforcement": reinforcement,
    }
