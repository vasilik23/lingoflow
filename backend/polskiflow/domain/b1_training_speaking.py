"""Original guided speaking tasks; no claim of official assessment."""

from dataclasses import dataclass

PREPARATION_SECONDS = 120


@dataclass(frozen=True)
class SpeakingTask:
    id: str
    title: str
    prompt: str
    checklist: tuple[str, ...]
    image: str = ""
    image_alt: str = ""
    image_description: str = ""
    dialogue_turns: tuple[str, ...] = ()


def training_speaking_tasks(variant, content_version, *, interactive=False):
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
    if interactive:
        situation = SpeakingTask(
            "situation", "Opis ilustracji i przewidywanie",
            "Spójrz na ilustrację. Opisz miejsce i działania osób. Wyjaśnij, jaki może być cel spotkania, "
            "i zaproponuj, co uczestnicy mogą zrobić, jeśli zacznie padać. Mów przez 1–2 minuty.",
            situation.checklist, image="polskiflow/speaking-neighbourhood-v1.png",
            image_alt="Учебная иллюстрация: подготовка соседской встречи у дома культуры.",
            image_description="Na placu przed domem kultury ludzie przygotowują spotkanie. Dwie osoby ustawiają stół, "
            "jedna wiesza plakat, a rodzic i dziecko niosą pudełka książek. Obok stoją krzesła. "
            "Drzwi budynku są otwarte; na niebie widać ciemne chmury.",
        )
        dialogue = SpeakingTask(
            "dialogue", "Rozmowa w domu kultury",
            "Chcesz zapisać się na kurs w domu kultury, ale pracujesz do siedemnastej. "
            "Odpowiadaj na kolejne pytania pracownika. Wyjaśnij swoje ograniczenie, odnieś się do alternatywy "
            "i zapytaj o koszt lub materiały. Mów przez 1–2 minuty.",
            dialogue.checklist, dialogue_turns=(
                "Dzień dobry. Zajęcia zaczynają się w środy o szesnastej. Czy ten termin Pani/Panu odpowiada?",
                "Rozumiem. Mamy również grupę sobotnią, która spotyka się o dziesiątej. Czy pasowałby Pani/Panu taki termin?",
                "Co jeszcze chciałaby Pani / chciałby Pan wiedzieć przed zapisaniem się na kurs?",
            ),
        )
    return (personal, situation, dialogue)
