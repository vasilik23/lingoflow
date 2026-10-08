"""A bounded curriculum starting-point check, not a CEFR assessment."""

from dataclasses import dataclass

LEVELS = ("A1", "A2", "B1", "B2")
# Reuse original course items; never depend on database-generated question IDs.
SOURCES = (("quiz", (1, 3, 4)), ("work-quiz", (1, 2, 4)),
           ("bio-quiz", (1, 3, 4)), ("b2view-quiz", (2, 5, 8)))


@dataclass(frozen=True)
class PlacementResult:
    level: str
    blocks: tuple
    strong_b2: bool


def evaluate(questions, answers):
    if len(questions) != 12 or len(answers) != 12:
        raise ValueError("A complete check requires twelve answers")
    scores = []
    for offset in range(0, 12, 3):
        scores.append(sum(answers[i] == questions[i]["correct"] for i in range(offset, offset + 3)))
    # The first uncertain foundation determines the safe entry point. Advanced
    # answers cannot compensate for missing basics in this uncalibrated check.
    level = "B2"
    for name, score in zip(LEVELS, scores):
        if score < 2:
            level = name
            break
    return PlacementResult(level, tuple(zip(LEVELS, scores)), all(score >= 2 for score in scores))
