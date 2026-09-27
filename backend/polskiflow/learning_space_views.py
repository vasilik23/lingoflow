"""Entry point for the learner's owner-scoped materials and review tools."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from polskiflow.auth_views import require_browser_user


@require_browser_user
@require_GET
def learning_space(request: HttpRequest) -> HttpResponse:
    return render(request, "learning_space.html")
