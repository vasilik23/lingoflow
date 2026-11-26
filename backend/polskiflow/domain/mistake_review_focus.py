"""Review topics for questions with a known, specific construction."""

from django.utils.translation import gettext_noop

REVIEW_FOCUS_BY_PROMPT = {
    "Как сказать «Я Анна»?": gettext_noop("Формы глагола być в настоящем времени"),
    "W mieszkaniu nie ma ___.": gettext_noop("Родительный падеж после nie ma"),
    "Nie ma ___.": gettext_noop("Родительный падеж после nie ma"),
    "Szukamy małego ___.": gettext_noop("Родительный падеж после szukać"),
    "Mamy problem z ___.": gettext_noop("Творительный падеж после z в значении «с»"),
    "Problem z ___.": gettext_noop("Творительный падеж после z в значении «с»"),
    "Разговариваю с владельцем.": gettext_noop("Творительный падеж после z в значении «с»"),
    "Potrzebujemy ___.": gettext_noop("Родительный падеж после potrzebować"),
    "Uczę się regularnie, ___ chcę dobrze zdać egzamin.": gettext_noop("Союзы причины и уступки"),
    "___ kurs jest wymagający, daje mi dużo satysfakcji.": gettext_noop("Союзы причины и уступки"),
}
