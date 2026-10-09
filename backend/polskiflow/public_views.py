"""Public introduction and session-free, read-only course mini-lessons."""
from urllib.parse import urlencode

from django.core import signing
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from polskiflow.domain.public_demo import DEMO_SALT, checked_answer, demo_version
from polskiflow.public_demo_store import DEMO_LESSONS, load_demo_lesson


def _private(response):
    response['Cache-Control'] = 'private, no-store'
    return response


@require_http_methods(['GET', 'HEAD'])
def public_intro(request):
    sample = load_demo_lesson('A2')
    return _private(render(request, 'public_intro.html', {'sample': sample}))


@require_http_methods(['GET', 'HEAD', 'POST'])
def public_demo(request):
    level = request.GET.get('level', 'A1')
    if level not in DEMO_LESSONS:
        level = 'A1'
    lesson = load_demo_lesson(level)
    context = {'lesson': lesson, 'level': level, 'levels': tuple(DEMO_LESSONS), 'unavailable': not lesson}
    status = 200 if lesson else 503
    if lesson:
        step = 'exercise' if request.GET.get('step') == 'exercise' else 'theory'
        context['state'] = signing.dumps({'version': demo_version(lesson)}, salt=DEMO_SALT)
        try:
            if request.method == 'POST':
                states, answers = request.POST.getlist('state'), request.POST.getlist('answer')
                if len(states) != 1 or len(answers) != 1:
                    raise ValueError('Missing or repeated fields')
                state = signing.loads(states[0], salt=DEMO_SALT, max_age=1800)
                if state != {'version': demo_version(lesson)} or answers[0] not in [str(i) for i in range(len(lesson['question']['options']))]:
                    raise ValueError('Changed lesson or invalid answer')
                review = signing.dumps({'version': demo_version(lesson), 'answer': int(answers[0])}, salt=DEMO_SALT)
                return _private(redirect(reverse('public-demo') + '?' + urlencode({'level': level, 'review': review})))
            reviews = request.GET.getlist('review')
            if reviews:
                if len(reviews) != 1:
                    raise ValueError('Repeated review')
                result = checked_answer(lesson, signing.loads(reviews[0], salt=DEMO_SALT, max_age=1800))
                context.update(result, review=reviews[0])
                step = 'result' if request.GET.get('step') == 'result' else 'explanation'
        except (signing.BadSignature, ValueError, TypeError):
            context['demo_error'] = 'Не удалось проверить ответ. Попробуй ещё раз.'
            step, status = 'exercise', 400
        context.update(step=step, step_number={'theory': 1, 'exercise': 2, 'explanation': 3, 'result': 4}[step])
    return _private(render(request, 'public_demo.html', context, status=status))
