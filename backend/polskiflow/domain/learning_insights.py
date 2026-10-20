"""Deterministic, presentation-ready insights from owner-scoped progress."""

from datetime import date, timedelta


KIND_LABELS = {
    "words": "Новые слова",
    "grammar": "Грамматика",
    "review": "Повторение",
    "quiz": "Проверка знаний",
    "reading-check": "Понимание текста",
}


def build_learning_insights(dashboard, lessons: list[dict], today: date | None = None) -> dict:
    """Build a bounded 30-day summary without introducing a new learner score."""
    today = today or date.today()
    counts = tuple(dashboard.recent_daily_completion_counts or ())[-28:]
    padded_counts = (0,) * (28 - len(counts)) + counts
    recent_14 = padded_counts[-14:]
    chart_max = max(recent_14, default=0) or 1
    activity = [
        {
            "date": (today - timedelta(days=13 - index)).strftime("%d.%m"),
            "count": count,
            "height": round(count / chart_max * 100),
        }
        for index, count in enumerate(recent_14)
    ]

    lesson_kinds = {lesson.get("id"): lesson.get("kind") for lesson in lessons}
    buckets: dict[str, dict[str, int]] = {}
    total_known = 0
    total_cards = 0
    self_known = self_total = 0
    for result in dashboard.recent_completion_results or ():
        kind = lesson_kinds.get(result.get("lesson_id"))
        known = result.get("cards_known")
        total = result.get("cards_total")
        if kind not in KIND_LABELS or type(known) is not int or type(total) is not int or total <= 0 or not 0 <= known <= total:
            continue
        if kind in {"words", "review"}:
            self_known += known
            self_total += total
            continue
        bucket = buckets.setdefault(kind, {"attempts": 0, "known": 0, "total": 0})
        bucket["attempts"] += 1
        bucket["known"] += known
        bucket["total"] += total
        total_known += known
        total_cards += total

    breakdown = []
    for kind, values in buckets.items():
        breakdown.append({
            "kind": kind,
            "label": KIND_LABELS[kind],
            "attempts": values["attempts"],
            "answers": values["total"],
            "accuracy": round(values["known"] / values["total"] * 100),
        })
    breakdown.sort(key=lambda item: (-item["attempts"], item["label"]))

    weakest = min(breakdown, key=lambda item: (item["accuracy"], -item["attempts"])) if breakdown else None
    if weakest and weakest["accuracy"] < 70:
        recommendation = {
            "title": f"Закрепить: {weakest['label'].lower()}",
            "reason": f"За последние 30 дней здесь {weakest['accuracy']}% правильных ответов.",
            "href": f"/course/?level={dashboard.level}&kind={weakest['kind']}",
            "action": "Выбрать урок",
        }
    else:
        recommendation = {
            "title": "Продолжай текущий план",
            "reason": "Недавние результаты не показывают явной зоны для дополнительного закрепления.",
            "href": "/#daily-tasks",
            "action": "К плану на сегодня",
        }

    return {
        "available": dashboard.available,
        "activity": activity,
        "completed_28_days": sum(padded_counts),
        "active_28_days": sum(count > 0 for count in padded_counts),
        "accuracy": round(total_known / total_cards * 100) if total_cards else None,
        "answer_count": total_cards,
        "self_known": self_known, "self_total": self_total,
        "breakdown": breakdown,
        "recommendation": recommendation,
    }
