"""Public product introduction and one isolated course exercise."""

import hashlib
import json

from django.core import signing
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_http_methods

from polskiflow.learning.models import Question

DEMO_SALT = "lingoflow-public-demo-v1"


@require_GET
def public_intro(request):
    return render(request, "public_intro.html")


def load_demo_question():
    return Question.objects.filter(
        lesson_id="quiz", position=0, is_active=True, lesson__is_active=True,
        lesson__topic__is_active=True, lesson__topic__course__is_active=True,
    ).values("prompt", "options", "correct", "explanation").first()


@require_http_methods(["GET", "POST"])
def public_demo(request):
    question = load_demo_question()
    context = {"question": question, "unavailable": not question}
    status = 200 if question else 503
    if question:
        version = hashlib.sha256(json.dumps(question, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        context["state"] = signing.dumps({"version": version}, salt=DEMO_SALT)
        if request.method == "POST":
            try:
                states, answers = request.POST.getlist("state"), request.POST.getlist("answer")
                if len(states) != 1 or len(answers) != 1:
                    raise ValueError("Missing or repeated fields")
                state = signing.loads(states[0], salt=DEMO_SALT, max_age=1800)
                if state != {"version": version} or answers[0] not in [str(index) for index in range(len(question["options"]))]:
                    raise ValueError("Changed question or invalid answer")
                answer = int(answers[0])
                context.update(answered=True, correct=answer == question["correct"],
                               selected_text=question["options"][answer], correct_text=question["options"][question["correct"]])
            except (signing.BadSignature, ValueError, TypeError):
                context["demo_error"] = "Не удалось проверить ответ. Попробуй ещё раз."
                status = 400
    response = render(request, "public_demo.html", context, status=status)
    response["Cache-Control"] = "private, no-store"
    return response
