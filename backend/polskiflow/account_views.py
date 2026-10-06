"""Authenticated account-security settings."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from polskiflow.auth import SupabaseAuthError, clear_auth_cookies, delete_account, update_password
from polskiflow.auth_views import require_browser_user
from polskiflow.domain.auth_rate_limit import consume_auth_attempt
from polskiflow.domain.password_policy import password_error


@require_browser_user
@require_http_methods(["GET", "POST"])
def account_security(request: HttpRequest) -> HttpResponse:
    context = {"error": ""}
    if request.method == "POST":
        current = request.POST.get("current_password", "")
        password = request.POST.get("password", "")
        confirmation = request.POST.get("password_confirmation", "")
        if not current:
            context["error"] = "Укажите текущий пароль"
        elif password != confirmation:
            context["error"] = "Новые пароли не совпадают"
        elif current == password:
            context["error"] = "Новый пароль должен отличаться от текущего"
        elif error := password_error(password):
            context["error"] = error
        else:
            try:
                update_password(
                    request.supabase_access_token,
                    password,
                    current_password=current,
                )
            except SupabaseAuthError:
                context["error"] = (
                    "Не удалось изменить пароль. Проверьте текущий пароль или войдите заново."
                )
            else:
                response = redirect(f"{reverse('login')}?password_changed=1")
                clear_auth_cookies(response)
                response["Cache-Control"] = "private, no-store"
                return response
    response = render(request, "account/security.html", context)
    response["Cache-Control"] = "private, no-store"
    return response


@require_browser_user
@require_http_methods(["GET", "POST"])
def account_delete(request: HttpRequest) -> HttpResponse:
    context = {"error": ""}
    status = 200
    retry_after = None
    if request.method == "POST":
        password = request.POST.get("current_password", "")
        confirmation = request.POST.get("confirmation", "").strip()
        email = request.supabase_user.email or ""
        if confirmation not in {"УДАЛИТЬ", "USUŃ"}:
            context["error"] = "Введите УДАЛИТЬ без кавычек"
        elif not password:
            context["error"] = "Укажите текущий пароль"
        elif not email:
            context["error"] = "У аккаунта нет подтверждённого email"
        elif not (rate := consume_auth_attempt(request, "delete", email))[0]:
            context["error"] = "Слишком много попыток. Повторите позже."
            status = 429
            retry_after = rate[1]
        else:
            try:
                delete_account(
                    request.supabase_access_token,
                    request.supabase_user.id,
                    password,
                )
            except SupabaseAuthError:
                context["error"] = (
                    "Не удалось удалить аккаунт. Проверьте пароль или повторите позже."
                )
            else:
                response = redirect(f"{reverse('login')}?account_deleted=1")
                clear_auth_cookies(response)
                response["Cache-Control"] = "private, no-store"
                return response
    response = render(request, "account/delete.html", context, status=status)
    response["Cache-Control"] = "private, no-store"
    if retry_after is not None:
        response["Retry-After"] = str(retry_after)
    return response
