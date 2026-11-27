"""Review topics for questions with a known, specific construction."""

from django.utils.translation import gettext_noop

REVIEW_FOCUS = {
    "byc-present": (gettext_noop("Формы глагола być в настоящем времени"), (
        "Как сказать «Я Анна»?",
    )),
    "nie-ma-genitive": (gettext_noop("Родительный падеж после nie ma"), (
        "W mieszkaniu nie ma ___.",
        "Nie ma ___.",
    )),
    "szukac-genitive": (gettext_noop("Родительный падеж после szukać"), (
        "Szukamy małego ___.",
    )),
    "z-instrumental": (gettext_noop("Творительный падеж после z в значении «с»"), (
        "Mamy problem z ___.",
        "Problem z ___.",
        "Разговариваю с владельцем.",
    )),
    "potrzebowac-genitive": (gettext_noop("Родительный падеж после potrzebować"), (
        "Potrzebujemy ___.",
    )),
    "reason-concession": (gettext_noop("Союзы причины и уступки"), (
        "Uczę się regularnie, ___ chcę dobrze zdać egzamin.",
        "___ kurs jest wymagający, daje mi dużo satysfakcji.",
    )),
    "past-singular": (gettext_noop("Род глагола в прошедшем времени (единственное число)"), (
        "В субботу Марек работал дома.",
        "Ania ___ do kina.",
        "Ja (женщина) długo ___.",
        "Paweł ___ film.",
        "Ewa ___ książkę.",
        "Ja (мужчина) ___ weekend w domu.",
    )),
    "past-plural": (gettext_noop("Формы прошедшего времени для разных групп людей"), (
        "My (мужчина и женщина) ___ w Krakowie.",
        "Kasia i Ola ___ muzeum.",
        "Tomek i Adam ___ na koncert.",
        "Mama i córka ___ w domu.",
        "My (смешанная группа) ___ późno.",
    )),
    "reported-statements": (gettext_noop("Утверждения в косвенной речи"), (
        "Nauczyciel powiedział: «Projekt oddajemy w piątek». W mowie zależnej: Nauczyciel powiedział, ___.",
    )),
    "reported-questions": (gettext_noop("Общие вопросы в косвенной речи"), (
        "Prowadząca zapytała: «Czy rozumiecie zadanie?». Prowadząca zapytała, ___.",
    )),
}

FOCUS_ID_BY_PROMPT = {
    prompt: focus_id
    for focus_id, (_, prompts) in REVIEW_FOCUS.items()
    for prompt in prompts
}
