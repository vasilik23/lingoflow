"""Translate presentation labels without altering learning data or user text."""

import json
import re
from pathlib import Path

from django import template
from django.utils.translation import gettext, get_language, ngettext

register = template.Library()
_PATTERNS = []
for _message in json.loads((Path(__file__).resolve().parents[2] / "localization/server_patterns.json").read_text()):
    _parts = re.split(r"(%\(v\d+\)s)", _message)
    _regex = "".join(f"(?P<{part[2:-2]}>.+?)" if part.startswith("%(v") else re.escape(part) for part in _parts)
    _PATTERNS.append((re.compile(_regex), _message))


@register.filter
def ui_text(value):
    if not isinstance(value, str) or get_language() != "pl":
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
        return f"{count} {ngettext(*forms, int(count))}{suffix}"
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
