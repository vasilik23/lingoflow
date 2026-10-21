"""SM-2 scheduling rules shared by future web and background jobs."""

from dataclasses import dataclass
from datetime import date, timedelta
from math import floor
from typing import Literal

ReviewQuality = Literal["again", "hard", "good", "easy", "know"]
MIN_EASE_FACTOR = 1.3
QUALITY_SCORES: dict[ReviewQuality, int] = {
    "again": 1,
    "hard": 3,
    "good": 4,
    "easy": 5,
    # Compatibility with the first two-button flashcard MVP.
    "know": 5,
}


@dataclass(frozen=True)
class Sm2State:
    ease_factor: float
    interval_days: int
    repetitions: int


@dataclass(frozen=True)
class Sm2Result(Sm2State):
    next_review_date: date


DEFAULT_SM2_STATE = Sm2State(
    ease_factor=2.5,
    interval_days=0,
    repetitions=0,
)


def sm2_next(state: Sm2State, quality: ReviewQuality, today: date) -> Sm2Result:
    """Return the next immutable review state using the SM-2 quality scale."""

    if quality not in QUALITY_SCORES:
        raise ValueError("unknown review quality")

    score = QUALITY_SCORES[quality]
    repetitions = state.repetitions
    interval_days = state.interval_days

    if score < 3:
        repetitions = 0
        interval_days = 1
    else:
        if repetitions == 0:
            interval_days = 1
        elif repetitions == 1:
            interval_days = 6
        else:
            # JavaScript Math.round rounds positive halves upward; Python's
            # round uses bankers' rounding, so preserve the MVP behaviour.
            interval_days = max(1, floor(interval_days * state.ease_factor + 0.5))
        repetitions += 1

    ease_factor = max(
        MIN_EASE_FACTOR,
        state.ease_factor
        + (0.1 - (5 - score) * (0.08 + (5 - score) * 0.02)),
    )

    return Sm2Result(
        ease_factor=ease_factor,
        interval_days=interval_days,
        repetitions=repetitions,
        next_review_date=today + timedelta(days=interval_days),
    )


def parse_reviewed_at(value):
    """Normalize an opaque review timestamp without accepting filter syntax."""
    from datetime import datetime, timezone
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError('Invalid review timestamp')
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Review timestamp requires timezone')
    return parsed.astimezone(timezone.utc)
