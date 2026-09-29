"""Authenticated interaction and mediation practice."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from polskiflow.auth_views import require_browser_user
from polskiflow.domain.interaction_scenarios import (
    FREE_PRODUCTION_SCENARIOS,
    SPEAKING_SCENARIOS,
    SCENARIOS,
    SEQUENCE_SCENARIOS,
    validate_answer,
    validate_sequence_answer,
)


@require_browser_user
@require_http_methods(["GET", "POST"])
def interaction_practice(request: HttpRequest) -> HttpResponse:
    result = None
    error = ""
    status = 200

    if request.method == "POST":
        task_type = request.POST.get("task_type", "choice")
        allowed_fields = {"csrfmiddlewaretoken", "scenario_id", "task_type"}
        allowed_fields.add("block_id" if task_type == "sequence" else "option_id")
        unexpected_fields = set(request.POST) - allowed_fields
        has_single_values = (
            len(request.POST.getlist("scenario_id")) == 1
            and len(request.POST.getlist("task_type")) <= 1
        )
        if unexpected_fields or not has_single_values:
            error = "Не удалось проверить ответ. Обновите страницу и попробуйте снова."
            status = 400
        else:
            scenario_id = request.POST.get("scenario_id", "")
            try:
                if task_type == "choice":
                    option_id = request.POST.get("option_id", "")
                    if len(request.POST.getlist("option_id")) != 1:
                        raise ValueError("Выберите один из предложенных ответов.")
                    scenario, is_correct = validate_answer(scenario_id, option_id)
                elif task_type == "sequence":
                    scenario, is_correct = validate_sequence_answer(
                        scenario_id, tuple(request.POST.getlist("block_id"))
                    )
                else:
                    raise ValueError("Неизвестный формат задания.")
            except ValueError as exc:
                error = str(exc)
                status = 400
            else:
                result = {
                    "scenario": scenario,
                    "is_correct": is_correct,
                    "task_type": task_type,
                }
                if task_type == "choice":
                    result["selected_option"] = next(
                        option for option in scenario.options if option.id == option_id
                    )
                    result["correct_option"] = next(
                        option
                        for option in scenario.options
                        if option.id == scenario.correct_option_id
                    )
                else:
                    blocks_by_id = {block.id: block for block in scenario.blocks}
                    result["correct_blocks"] = tuple(
                        blocks_by_id[block_id] for block_id in scenario.correct_order
                    )

    return render(
        request,
        "interaction.html",
        {
            "scenarios": SCENARIOS,
            "sequence_scenarios": SEQUENCE_SCENARIOS,
            "free_production_scenarios": FREE_PRODUCTION_SCENARIOS,
            "speaking_scenarios": SPEAKING_SCENARIOS,
            "result": result,
            "error": error,
        },
        status=status,
    )
