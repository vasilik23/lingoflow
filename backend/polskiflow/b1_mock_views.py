from django.core import signing
from django.core.signing import BadSignature, SignatureExpired
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from polskiflow.auth_views import require_browser_user
from polskiflow.b1_mock_store import load_b1_mock_attempts, save_b1_mock_attempt
from polskiflow.domain.b1_weekly_mock import LISTENING_TRANSCRIPT, QUESTIONS, READING_TEXT, score_mock_answers

ATTEMPT_SALT = "polskiflow.b1-weekly-mock"
ATTEMPT_MAX_AGE_SECONDS = 20 * 60


def _attempt_token(user_id: str) -> str:
    return signing.dumps({"user_id": user_id}, salt=ATTEMPT_SALT)


@require_browser_user
@require_http_methods(["GET", "POST"])
def b1_weekly_mock(request: HttpRequest) -> HttpResponse:
    result = None
    error = None
    status = 200
    saved = None
    token = _attempt_token(request.supabase_user.id)
    if request.method == "POST":
        token = request.POST.get("attempt_token", "")
        allowed = {"csrfmiddlewaretoken", "attempt_token", *(f"answer_{item.id}" for item in QUESTIONS)}
        if set(request.POST) - allowed:
            error, status = "Форма содержит неизвестные поля. Начни попытку заново.", 400
        else:
            try:
                payload = signing.loads(token, salt=ATTEMPT_SALT, max_age=ATTEMPT_MAX_AGE_SECONDS)
                if payload != {"user_id": request.supabase_user.id}:
                    raise BadSignature
                answers = {item.id: int(request.POST[f"answer_{item.id}"]) for item in QUESTIONS}
                result = score_mock_answers(answers)
                saved = save_b1_mock_attempt(
                    request.supabase_access_token, request.supabase_user.id, result
                )
            except SignatureExpired:
                error, status = "Время попытки истекло. Начни новый модуль.", 400
            except (BadSignature, KeyError, TypeError, ValueError):
                error, status = "Ответь на все проверяемые вопросы и попробуй снова.", 400
    history = load_b1_mock_attempts(
        request.supabase_access_token, request.supabase_user.id
    )
    return render(request, "b1_weekly_mock.html", {
        "questions": QUESTIONS,
        "listening_transcript": LISTENING_TRANSCRIPT,
        "reading_text": READING_TEXT,
        "attempt_token": token,
        "duration_seconds": 15 * 60,
        "result": result,
        "saved": saved,
        "history": history,
        "error": error,
    }, status=status)
