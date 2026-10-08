"""Stateless, owner-bound onboarding check; no profile or progress writes."""

import hashlib
import json

from django.core import signing
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from polskiflow.auth_views import require_browser_user
from polskiflow.domain.placement import SOURCES, evaluate
from polskiflow.learning.models import Question

SALT = "lingoflow-placement-v1"


def load_questions():
    bank = []
    for lesson_id, positions in SOURCES:
        rows = {row["position"]: row for row in Question.objects.filter(
            lesson_id=lesson_id, position__in=positions, is_active=True,
            lesson__is_active=True, lesson__topic__is_active=True,
            lesson__topic__course__is_active=True,
        ).values("position", "prompt", "options", "correct", "explanation")}
        for position in positions:
            row = rows.get(position)
            if not row or len(row["options"]) < 2 or not 0 <= row["correct"] < len(row["options"]):
                return []
            row = dict(row)
            shift = len(bank) % len(row["options"])
            row["options"] = row["options"][shift:] + row["options"][:shift]
            row["correct"] = (row["correct"] - shift) % len(row["options"])
            bank.append(row)
    return bank


@require_browser_user
@require_http_methods(["GET", "POST"])
def placement_check(request):
    questions = load_questions()
    context = {"questions": [], "placement_error": "", "unavailable": not questions}
    status = 200 if questions else 503
    if questions:
        version = hashlib.sha256(json.dumps(questions, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        answers = []
        if request.method == "POST":
            try:
                state = signing.loads(request.POST.get("state", ""), salt=SALT, max_age=1800)
                if state.get("owner") != request.supabase_user.id or state.get("version") != version:
                    raise ValueError("Wrong owner or changed content")
                answers = state["answers"]
                if not isinstance(answers, list) or len(answers) not in (0, 3, 6, 9):
                    raise ValueError("Invalid step")
                if any(type(value) is not int or not -1 <= value < len(questions[i]["options"]) for i, value in enumerate(answers)):
                    raise ValueError("Invalid previous answers")
                submitted = []
                for index, question in enumerate(questions[len(answers):len(answers) + 3]):
                    values = request.POST.getlist(f"answer_{index}")
                    if len(values) != 1 or values[0] not in [str(i) for i in range(-1, len(question["options"]))]:
                        raise ValueError("Missing or invalid answer")
                    submitted.append(int(values[0]))
                answers += submitted
            except (signing.BadSignature, ValueError, KeyError, TypeError, AttributeError):
                context["placement_error"] = "Проверка не принята. Начни заново: выбери ответ на каждый вопрос."
                status = 400
                answers = []
        if len(answers) == 12:
            result = evaluate(questions, answers)
            context.update(result=result, reviews=[dict(question, chosen=answer, passed=answer == question["correct"], correct_text=question["options"][question["correct"]]) for question, answer in zip(questions, answers)])
        else:
            context.update(questions=questions[len(answers):len(answers) + 3], step=len(answers) // 3 + 1,
                           state=signing.dumps({"owner": request.supabase_user.id, "version": version, "answers": answers}, salt=SALT, compress=True))
    response = render(request, "placement.html", context, status=status)
    response["Cache-Control"] = "private, no-store"
    return response
