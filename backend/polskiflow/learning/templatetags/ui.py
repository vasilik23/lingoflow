"""Translate presentation labels without altering learning data or user text."""

import json
import re
from functools import lru_cache
from pathlib import Path

from django import template
from django.utils.html import escape, format_html, format_html_join
from django.utils.translation import gettext, get_language, ngettext

register = template.Library()


@register.filter
def navigation_section(route):
    if route == "home":
        return "today"
    if route in {"learn-hub", "course", "lesson", "reading-library", "reader", "news-library", "dictionary", "global-search"}:
        return "learn"
    if isinstance(route, str) and (route.startswith("b1-") or route.startswith("dictionary-practice") or route in {"practice-hub", "listening-practice", "writing-practice", "interaction-practice", "diagnostic"}):
        return "practice"
    return ""
_PATTERNS = []
for _message in json.loads((Path(__file__).resolve().parents[2] / "localization/server_patterns.json").read_text()):
    _parts = re.split(r"(%\(v\d+\)s)", _message)
    _regex = "".join(f"(?P<{part[2:-2]}>.+?)" if part.startswith("%(v") else re.escape(part) for part in _parts)
    _PATTERNS.append((re.compile(_regex), _message))


@register.filter
def ui_text(value):
    if not isinstance(value, str) or get_language() not in {"pl", "en"}:
        return value
    translated = gettext(value)
    if translated != value:
        return translated
    normalized = " ".join(value.split())
    translated = gettext(normalized)
    if translated != normalized:
        return translated
    counted = re.fullmatch(r"(\d+) (урок|урока|уроков|тема|темы|тем|слово|слова|слов|попытка|попытки|попыток)\b(.*)", value)
    if counted:
        count, unit, suffix = counted.groups()
        forms = next(pair for words, pair in (
            (("урок", "урока", "уроков"), ("урок", "уроков")),
            (("тема", "темы", "тем"), ("тема", "тем")),
            (("слово", "слова", "слов"), ("слово", "слов")),
            (("попытка", "попытки", "попыток"), ("попытка", "попыток")),
        ) if unit in words)
        return f"{count} {ngettext(*forms, int(count))}{ui_text(suffix)}"
    for pattern, message in _PATTERNS:
        matched = pattern.fullmatch(value)
        if matched:
            translated = gettext(message)
            if translated != message:
                return re.sub(r"%\((v\d+)\)s", lambda part: str(ui_text(matched.group(part[1]))), translated)
    return value


@register.filter
def ui_items(values):
    return [ui_text(value) for value in values]


@register.filter
def learning_text(value):
    """Localized study support; untranslated content remains canonical."""
    return ui_text(value) if get_language() in {"pl", "en"} else value


@lru_cache(maxsize=1)
def _polish_study_quotes():
    return frozenset(json.loads((Path(__file__).resolve().parents[2] / "localization/polish_study_quotes.json").read_text()))


@register.filter
def learning_markup(value):
    """Escaped display-only markup for explicitly reviewed Polish quotations.

    Never use in attributes, form values, or user-authored content.
    Translation remains plain text everywhere outside this filter.
    """
    localized = learning_text(value)
    if not isinstance(localized, str) or not isinstance(value, str):
        return localized
    pieces = []
    cursor = 0
    for match in re.finditer(r'[«„“"]([^»”"]+)[»”"]', localized):
        fragment = match.group(1)
        if fragment not in _polish_study_quotes() or fragment not in value:
            continue
        pieces.append(escape(localized[cursor:match.start(1)]))
        pieces.append(format_html('<span lang="pl">{}</span>', escape(fragment)))
        cursor = match.end(1)
    pieces.append(escape(localized[cursor:]))
    return format_html_join("", "{}", ((piece,) for piece in pieces))


@lru_cache(maxsize=1)
def _english_readings():
    return json.loads((Path(__file__).resolve().parents[2] / "localization/reading_english.json").read_text())


@register.filter
def english_reading(paragraphs):
    """Only show a complete study translation beside the Polish original."""
    if get_language() != "en" or not isinstance(paragraphs, list):
        return []
    translations = _english_readings()
    if not all(isinstance(paragraph, str) and translations.get(paragraph) for paragraph in paragraphs):
        return []
    return [translations[paragraph] for paragraph in paragraphs]


@register.filter
def learning_language(value, source_language="pl"):
    """Language of a study fragment, preserving the Russian fallback.

    The caller supplies the language of untranslated Latin-script content;
    this is not a general-purpose language detector or a label for user text.
    """
    localized = learning_text(value)
    if isinstance(localized, str) and re.search(r"[А-Яа-яЁё]", localized):
        return "ru"
    if localized != value:
        return get_language() if get_language() in {"ru", "pl", "en"} else "ru"
    return source_language if source_language in {"ru", "pl", "en"} else "ru"
