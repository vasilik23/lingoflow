"""Authenticated, CSRF-protected speech-to-text and confirmed transcript review."""
import json
from django.core import signing
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from polskiflow.ai_writing import WritingAIUnavailable
from polskiflow.ai_writing_views import _response
from polskiflow.ai_speaking import (SALT, MAX_AUDIO_BYTES, AUDIO_ERROR, speaking_ai_available, audio_container, transcribe_audio, review_speaking)
from polskiflow.api_rate_limit_store import consume_distributed_api_mutation

UNAVAILABLE = "ИИ речи временно недоступен. Запись и самопроверка доступны без отправки."


def _assignment(token, owner, stage):
    if not isinstance(token, str) or len(token) > 12000:
        raise ValueError
    signed = signing.loads(token, salt=SALT, max_age=4 * 60 * 60)
    if not isinstance(signed, dict) or signed.get("owner") != owner or signed.get("stage") != stage or not isinstance(signed.get("assignment"), dict):
        raise ValueError
    return signed["assignment"]


def _quota(request):
    if not speaking_ai_available():
        return _response({"error": _(UNAVAILABLE)}, 503)
    # Speech and writing share the existing owner-bound 10-call daily budget.
    quota = consume_distributed_api_mutation(request.supabase_access_token, "ai_writing")
    if quota is None:
        return _response({"error": _(UNAVAILABLE)}, 503)
    if not quota[0]:
        response = _response({"error": _("Лимит проверок ИИ достигнут. Продолжи самопроверку и попробуй позже.")}, 429)
        response["Retry-After"] = str(quota[1])
        return response
    return None


@require_POST
@sensitive_post_parameters()
@sensitive_variables("audio", "data", "text", "assignment")
def ai_speech_transcribe(request):
    if request.supabase_user is None:
        return _response({"error": _("Войди снова, чтобы проверить текст с ИИ.")}, 401)
    try:
        if request.content_type != "multipart/form-data" or set(request.POST) != {"token", "consent"} or request.POST.get("consent") != "true" or set(request.FILES) != {"audio"}:
            raise ValueError
        if any(len(request.POST.getlist(key)) != 1 for key in request.POST) or len(request.FILES.getlist("audio")) != 1:
            raise ValueError
        assignment = _assignment(request.POST["token"], request.supabase_user.id, "recording")
        audio = request.FILES["audio"]
        if not 1 <= audio.size <= MAX_AUDIO_BYTES:
            return _response({"error": _(AUDIO_ERROR)}, 413)
        data = audio.read(MAX_AUDIO_BYTES + 1)
        extension, mime = audio_container(data, audio.content_type or "")
    except (ValueError, TypeError, KeyError, signing.BadSignature):
        return _response({"error": _("Подтверди отправку записи и обнови страницу задания.")}, 400)
    blocked = _quota(request)
    if blocked is not None:
        return blocked
    try:
        text = transcribe_audio(data, extension, mime)
    except WritingAIUnavailable:
        return _response({"error": _(UNAVAILABLE)}, 503)
    receipt = signing.dumps({"owner": request.supabase_user.id, "assignment": assignment, "stage": "transcript"}, salt=SALT, compress=True)
    return _response({"text": text, "token": receipt, "persisted": False})


@require_POST
@sensitive_post_parameters()
@sensitive_variables("payload", "text", "assignment")
def ai_speech_review(request):
    if request.supabase_user is None:
        return _response({"error": _("Войди снова, чтобы проверить текст с ИИ.")}, 401)
    if request.content_type != "application/json":
        return _response({"error": _("Некорректный запрос проверки.")}, 415)
    if len(request.body) > 40000:
        return _response({"error": _("Для проверки напиши от 1 до 6000 символов.")}, 413)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or set(payload) != {"token", "text", "consent", "confirmed"} or payload["consent"] is not True or payload["confirmed"] is not True:
            raise ValueError
        text = payload["text"]
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 6000 or len(text) > 6000:
            raise ValueError
        assignment = _assignment(payload["token"], request.supabase_user.id, "transcript")
    except (ValueError, TypeError, KeyError, signing.BadSignature, UnicodeDecodeError):
        return _response({"error": _("Проверь расшифровку и подтверди отправку текста в Groq.")}, 400)
    blocked = _quota(request)
    if blocked is not None:
        return blocked
    try:
        result = review_speaking(assignment, text, getattr(request, "LANGUAGE_CODE", "ru"))
    except WritingAIUnavailable:
        return _response({"error": _(UNAVAILABLE)}, 503)
    return _response({"result": result})
