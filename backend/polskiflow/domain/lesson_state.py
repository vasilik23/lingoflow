"""Signed, user-bound state for server-rendered lesson flows."""

from dataclasses import dataclass
from uuid import UUID

from django.core import signing
from django.utils.crypto import salted_hmac


SALT = "polskiflow.lesson-state.v1"
MAX_AGE_SECONDS = 12 * 60 * 60


class InvalidLessonState(ValueError):
    pass


@dataclass(frozen=True)
class LessonState:
    index: int
    score: int
    phase: str
    attempt_id: str | None = None


def _owner_binding(user_id: str) -> str:
    return salted_hmac(SALT, user_id).hexdigest()[:32]


def sign_lesson_state(user_id: str, lesson_id: str, lesson_kind: str, index: int, score: int, phase: str = "ready", *, attempt_id: str | None = None) -> str:
    payload = {"v": 1, "owner": _owner_binding(user_id), "lesson": lesson_id, "kind": lesson_kind, "index": index, "score": score, "phase": phase}
    if attempt_id:
        payload["attempt_id"] = str(UUID(attempt_id))
    return signing.dumps(
        payload,
        salt=SALT,
        compress=True,
    )


def load_lesson_state(token: str, user_id: str, lesson_id: str, lesson_kind: str) -> LessonState:
    try:
        payload = signing.loads(token, salt=SALT, max_age=MAX_AGE_SECONDS)
    except signing.BadSignature as error:
        raise InvalidLessonState from error
    fields = {"v", "owner", "lesson", "kind", "index", "score", "phase"}
    if not isinstance(payload, dict) or set(payload) not in (fields, fields | {"attempt_id"}):
        raise InvalidLessonState
    attempt_id = payload.get("attempt_id")
    if "attempt_id" in payload:
        try:
            attempt_id = str(UUID(attempt_id))
        except (ValueError, TypeError, AttributeError) as error:
            raise InvalidLessonState from error
    index, score = payload["index"], payload["score"]
    if (
        payload["v"] != 1 or payload["owner"] != _owner_binding(user_id)
        or payload["lesson"] != lesson_id or payload["kind"] != lesson_kind
        or type(index) is not int or type(score) is not int
        or index < 0 or score < 0 or score > index + (payload["phase"] == "answered")
        or payload["phase"] not in {"ready", "answered"}
    ):
        raise InvalidLessonState
    return LessonState(index=index, score=score, phase=payload["phase"], attempt_id=attempt_id)
