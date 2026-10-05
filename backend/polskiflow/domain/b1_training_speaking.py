"""Original guided speaking tasks; no claim of official assessment."""

from dataclasses import dataclass

PREPARATION_SECONDS = 120


@dataclass(frozen=True)
class SpeakingTask:
    id: str
    title: str
    prompt: str
    checklist: tuple[str, ...]


def training_speaking_tasks(variant, content_version):
    personal = SpeakingTask(
        "personal", "Wypowiedź osobista", variant.speaking_prompt,
        ("Uwzględnij wszystkie punkty polecenia.", "Podaj przykład i połącz zdania w spójną wypowiedź."),
    )
    if content_version < 5:
        return (personal,)
    situation = SpeakingTask(
        "situation", "Opis sytuacji i przewidywanie",
        "Wyobraź sobie następującą sytuację: na placu przed domem kultury kilka osób przygotowuje spotkanie sąsiedzkie. "
        "Dwie osoby ustawiają stoły, jedna rozwiesza plan wydarzenia, a rodzic z dzieckiem przynosi pudełko książek. "
        "Na niebie pojawiają się ciemne chmury. Opisz działania uczestników, wyjaśnij, po co organizują spotkanie, "
        "i zaproponuj, co mogą zrobić, jeśli zacznie padać. Mów przez 1–2 minuty.",
        ("Opisz działania osób i cel spotkania.", "Przedstaw możliwy problem i konkretne rozwiązanie."),
    )
    dialogue = SpeakingTask(
        "dialogue", "Samodzielna próba dialogu",
        "Chcesz zapisać się na kurs w domu kultury, ale pracujesz do siedemnastej. "
        "Odpowiedz na dwie wydrukowane kwestie pracownika, a następnie zadaj własne pytanie. "
        "Pracownik: „Zajęcia zaczynają się w środy o szesnastej. Czy ten termin Panu lub Pani odpowiada?” "
        "Pracownik: „Mamy również grupę sobotnią. Co jeszcze chciałby Pan lub chciałaby Pani wiedzieć?” "
        "Wyjaśnij swoją sytuację, odnieś się do drugiej propozycji i zapytaj o koszt lub materiały. Mów przez 1–2 minuty.",
        ("Odpowiedz na obie kwestie, wyjaśniając swoje ograniczenie.", "Odnieś się do alternatywy i zadaj własne pytanie."),
    )
    return (personal, situation, dialogue)
