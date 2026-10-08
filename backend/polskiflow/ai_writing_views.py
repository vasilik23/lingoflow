"""CSRF-protected, explicit opt-in writing feedback for browser users."""

import json

from django.core import signing
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.views.decorators.debug import sensitive_post_parameters, sensitive_variables
from django.views.decorators.http import require_POST

from polskiflow.ai_writing import SALT, WritingAIUnavailable, review_writing, writing_ai_available
from polskiflow.api_rate_limit_store import consume_distributed_api_mutation


UNAVAILABLE = "ИИ временно недоступен или квота исчерпана. Черновик остался в редакторе; продолжи самопроверку."


def _response(payload, status=200):
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "private, no-store"
    return response


@require_POST
@sensitive_post_parameters()
@sensitive_variables("payload", "text")
def ai_writing_review(request):
    if request.supabase_user is None:
        return _response({"error": _("Войди снова, чтобы проверить текст с ИИ.")}, 401)
    if request.content_type != "application/json":
        return _response({"error": _("Некорректный запрос проверки.")}, 415)
    if len(request.body) > 40000:
        return _response({"error": _("Для проверки напиши от 1 до 6000 символов.")}, 413)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or set(payload) != {"token", "text", "consent"} or payload["consent"] is not True:
            raise ValueError
        text = payload["text"]
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 6000 or len(text) > 6000:
            return _response({"error": _("Для проверки напиши от 1 до 6000 символов.")}, 400)
        if not isinstance(payload["token"], str) or len(payload["token"]) > 12000:
            raise ValueError
        signed = signing.loads(payload["token"], salt=SALT, max_age=4 * 60 * 60)
        if signed["owner"] != request.supabase_user.id or not isinstance(signed["assignment"], dict):
            raise ValueError
    except (ValueError, TypeError, KeyError, signing.BadSignature, UnicodeDecodeError):
        return _response({"error": _("Подтверди отправку текста и обнови страницу задания.")}, 400)
    if not writing_ai_available():
        return _response({"error": _(UNAVAILABLE)}, 503)
    # Fail closed: serverless instances must share the same quota, with no
    # in-memory fallback that could spend provider quota after a cold start.
    quota = consume_distributed_api_mutation(request.supabase_access_token, "ai_writing")
    if quota is None:
        return _response({"error": _(UNAVAILABLE)}, 503)
    if not quota[0]:
        response = _response({"error": _("Лимит проверок ИИ достигнут. Продолжи самопроверку и попробуй позже.")}, 429)
        response["Retry-After"] = str(quota[1])
        return response
    try:
        result = review_writing(signed["assignment"], text, getattr(request, "LANGUAGE_CODE", "ru"))
    except WritingAIUnavailable:
        return _response({"error": _(UNAVAILABLE)}, 503)
    return _response({"result": result})
