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
    "В субботу Марек работал дома.": gettext_noop("Род глагола в прошедшем времени (единственное число)"),
    "Ania ___ do kina.": gettext_noop("Род глагола в прошедшем времени (единственное число)"),
    "Ja (женщина) długo ___.": gettext_noop("Род глагола в прошедшем времени (единственное число)"),
    "Paweł ___ film.": gettext_noop("Род глагола в прошедшем времени (единственное число)"),
    "Ewa ___ książkę.": gettext_noop("Род глагола в прошедшем времени (единственное число)"),
    "Ja (мужчина) ___ weekend w domu.": gettext_noop("Род глагола в прошедшем времени (единственное число)"),
    "My (мужчина и женщина) ___ w Krakowie.": gettext_noop("Формы прошедшего времени для разных групп людей"),
    "Kasia i Ola ___ muzeum.": gettext_noop("Формы прошедшего времени для разных групп людей"),
    "Tomek i Adam ___ na koncert.": gettext_noop("Формы прошедшего времени для разных групп людей"),
    "Mama i córka ___ w domu.": gettext_noop("Формы прошедшего времени для разных групп людей"),
    "My (смешанная группа) ___ późno.": gettext_noop("Формы прошедшего времени для разных групп людей"),
    "Nauczyciel powiedział: «Projekt oddajemy w piątek». W mowie zależnej: Nauczyciel powiedział, ___.": gettext_noop("Утверждения в косвенной речи"),
    "Prowadząca zapytała: «Czy rozumiecie zadanie?». Prowadząca zapytała, ___.": gettext_noop("Общие вопросы в косвенной речи"),
}
