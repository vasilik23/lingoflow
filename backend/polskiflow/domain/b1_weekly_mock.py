"""Small, original B1 mock module with deterministic objective scoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class MockQuestion:
    id: str
    module: str
    prompt: str
    options: tuple[str, ...]
    correct: int
    explanation: str


@dataclass(frozen=True)
class MockVariant:
    id: str
    label: str
    listening_transcript: str
    reading_text: str
    writing_prompt: str
    speaking_prompt: str
    questions: tuple[MockQuestion, ...]
    origin: str = "original"
    created_for: str = "PolskiFlow"
    verified_at: date = date(2026, 10, 1)


LISTENING_TRANSCRIPT = (
    "Dzień dobry. Informujemy, że sobotnie warsztaty fotograficzne rozpoczną się "
    "o jedenastej, a nie o dziesiątej. Spotykamy się przy głównym wejściu do domu "
    "kultury. Prosimy przynieść telefon lub aparat oraz coś do picia. W razie deszczu "
    "pierwsza część zajęć odbędzie się w sali numer dwanaście."
)

READING_TEXT = (
    "Marta od kilku miesięcy dojeżdża do pracy rowerem. Początkowo chciała tylko "
    "uniknąć korków, ale szybko zauważyła, że ma więcej energii. Nie zrezygnowała "
    "jednak całkowicie z autobusu: wybiera go podczas silnego deszczu albo gdy musi "
    "przewieźć ciężkie dokumenty. Jej firma niedawno zamontowała stojaki rowerowe, "
    "dlatego kilku kolegów także zaczęło przyjeżdżać na dwóch kółkach."
)

QUESTIONS = (
    MockQuestion("l1", "listening", "O której rozpoczną się warsztaty?", ("O 10:00", "O 11:00", "O 12:00"), 1, "Nagranie mówi, że warsztaty rozpoczną się o jedenastej."),
    MockQuestion("l2", "listening", "Co trzeba przynieść?", ("Tylko dokumenty", "Własne krzesło", "Aparat lub telefon i napój"), 2, "Organizator prosi o telefon lub aparat oraz coś do picia."),
    MockQuestion("r1", "reading", "Dlaczego Marta początkowo wybrała rower?", ("Chciała uniknąć korków", "Firma zabroniła jazdy autobusem", "Chciała przewozić dokumenty"), 0, "Pierwsze zdania wskazują, że początkowym powodem były korki."),
    MockQuestion("r2", "reading", "Kiedy Marta wybiera autobus?", ("Codziennie rano", "Gdy pada lub ma ciężki bagaż", "Tylko w weekend"), 1, "Tekst wymienia silny deszcz i ciężkie dokumenty."),
    MockQuestion("g1", "grammar", "Gdybym miał więcej czasu, ___ częściej po polsku.", ("czytam", "przeczytam", "czytałbym"), 2, "Po „gdybym” używamy trybu warunkowego: „czytałbym”."),
    MockQuestion("g2", "grammar", "Nie znam osoby, ___ mogłaby nam pomóc.", ("która", "której", "którą"), 0, "Zaimek jest podmiotem czasownika „mogłaby”, dlatego ma formę „która”."),
    MockQuestion("g3", "grammar", "Proszę wysłać dokumenty ___ piątku.", ("od", "przez", "do"), 2, "Termin końcowy wyrażamy konstrukcją „do piątku”."),
)

VARIANTS = (
    MockVariant(
        "b1-weekly-v1", "Вариант 1", LISTENING_TRANSCRIPT, READING_TEXT,
        "Napisz krótką wiadomość do kolegi. Wyjaśnij, dlaczego nie możesz przyjść na spotkanie, zaproponuj inny termin i zapytaj o jego plany. 50–80 słów.",
        "Opowiedz o zmianie, która ułatwiła twoje codzienne życie. Podaj przyczynę, przykład i rezultat. Mów przez 1–2 minuty.",
        QUESTIONS,
    ),
    MockVariant(
        "b1-weekly-v2", "Вариант 2",
        "Uwaga, uczestnicy klubu książki. Najbliższe spotkanie odbędzie się w czwartek o osiemnastej trzydzieści, a nie w środę. Czekamy w czytelni na drugim piętrze biblioteki. Każdy uczestnik powinien przynieść książkę i zaznaczyć krótki fragment, o którym chce porozmawiać. Po spotkaniu będzie można zapisać się na listopadowe warsztaty.",
        "Kiedy Piotr zaczął pracować z domu, sądził, że zaoszczędzi dużo czasu. Po kilku tygodniach zauważył jednak, że prawie nie wychodzi i trudno mu zakończyć dzień pracy. Ustalił więc stałe godziny, a podczas przerwy obiadowej chodzi na krótki spacer. Dwa razy w tygodniu pracuje też z biura. Dzięki temu częściej spotyka kolegów, ale nadal unika codziennych dojazdów.",
        "Napisz e-mail do organizatora kursu. Wyjaśnij, dlaczego opuściłeś zajęcia, poproś o materiały i zapytaj o termin następnego spotkania. 50–80 słów.",
        "Opowiedz o sposobie organizacji czasu, który ci pomaga. Wyjaśnij, jak działa, podaj przykład i oceń rezultat. Mów przez 1–2 minuty.",
        (
            MockQuestion("l1", "listening", "Kiedy odbędzie się spotkanie?", ("W środę o 18:30", "W czwartek o 18:30", "W czwartek o 17:30"), 1, "Komunikat przenosi spotkanie na czwartek na godzinę osiemnastą trzydzieści."),
            MockQuestion("l2", "listening", "Co powinien przygotować uczestnik?", ("Gotową prezentację", "Formularz na warsztaty", "Książkę z zaznaczonym fragmentem"), 2, "Każdy ma przynieść książkę i zaznaczyć fragment do rozmowy."),
            MockQuestion("r1", "reading", "Jaki problem zauważył Piotr?", ("Dojazdy trwały dłużej", "Rzadko wychodził i pracował zbyt długo", "Nie miał przerwy obiadowej"), 1, "Tekst łączy pracę z domu z brakiem wyjść i trudnością w zakończeniu dnia."),
            MockQuestion("r2", "reading", "Dlaczego Piotr czasem pracuje z biura?", ("Żeby częściej widzieć współpracowników", "Ponieważ nie ma internetu", "Żeby codziennie dojeżdżać"), 0, "Praca z biura pozwala mu częściej spotykać kolegów."),
            MockQuestion("g1", "grammar", "Zanim zacząłem pracę, ___ plan na cały dzień.", ("przygotuję", "przygotowywałbym", "przygotowałem"), 2, "Obie czynności dotyczą przeszłości; dokonane „przygotowałem” wskazuje wcześniejsze zakończenie."),
            MockQuestion("g2", "grammar", "To jest firma, w ___ pracuje moja siostra.", ("której", "którą", "która"), 0, "Przyimek „w” w znaczeniu miejsca wymaga miejscownika: „w której”."),
            MockQuestion("g3", "grammar", "Mimo ___ pogody poszliśmy na spacer.", ("zła", "złej", "złą"), 1, "Przyimek „mimo” łączy się z dopełniaczem: „mimo złej pogody”."),
        ),
    ),
    MockVariant(
        "b1-weekly-v3", "Вариант 3",
        "Pociąg do Gdańska odjedzie dziś z peronu piątego zamiast trzeciego. Z powodu prac na torach wyjazd jest opóźniony o dwadzieścia minut. Podróżni z rowerami powinni zająć miejsca w ostatnim wagonie. Bilety zachowują ważność i nie trzeba ich wymieniać. Przepraszamy za zmianę i prosimy uważnie słuchać kolejnych komunikatów.",
        "Mieszkańcy osiedla stworzyli wspólny ogród na nieużywanym placu. Na początku brakowało narzędzi, dlatego każdy przyniósł coś z domu. Jedni sadzą warzywa, inni dbają o kwiaty albo podlewają rośliny podczas urlopu sąsiadów. Ogród nie tylko daje świeże produkty. Stał się też miejscem spotkań, chociaż ustalenie wspólnych zasad wymagało kilku długich rozmów.",
        "Napisz ogłoszenie dla mieszkańców domu. Poinformuj o wspólnej akcji, podaj termin i miejsce oraz wyjaśnij, co należy przynieść. 50–80 słów.",
        "Opowiedz o inicjatywie, która może poprawić życie w twojej okolicy. Przedstaw pomysł, korzyść i możliwą trudność. Mów przez 1–2 minuty.",
        (
            MockQuestion("l1", "listening", "Z którego peronu odjedzie pociąg?", ("Z trzeciego", "Z czwartego", "Z piątego"), 2, "Komunikat zmienia peron z trzeciego na piąty."),
            MockQuestion("l2", "listening", "Co mają zrobić osoby z rowerami?", ("Wymienić bilet", "Wsiąść do ostatniego wagonu", "Poczekać na inny pociąg"), 1, "Dla podróżnych z rowerami wskazano ostatni wagon."),
            MockQuestion("r1", "reading", "Jak mieszkańcy rozwiązali brak narzędzi?", ("Kupili je od miasta", "Przynieśli je z domów", "Zrezygnowali z warzyw"), 1, "Każdy przyniósł z domu część potrzebnych narzędzi."),
            MockQuestion("r2", "reading", "Co było trudne podczas tworzenia ogrodu?", ("Ustalenie wspólnych zasad", "Znalezienie jakichkolwiek roślin", "Sprzedaż świeżych produktów"), 0, "Końcowe zdanie wskazuje na długie rozmowy o wspólnych zasadach."),
            MockQuestion("g1", "grammar", "Gdy mieszkańcy ___ zasady, rozpoczęli pracę.", ("ustalają", "ustaliliby", "ustalili"), 2, "Dokonane „ustalili” opisuje zakończoną czynność wcześniejszą od rozpoczęcia pracy."),
            MockQuestion("g2", "grammar", "Potrzebujemy osób, ___ mogą podlewać rośliny.", ("które", "których", "którym"), 0, "Zaimek jest podmiotem liczby mnogiej: „osób, które mogą”."),
            MockQuestion("g3", "grammar", "Narzędzia zostały przyniesione ___ mieszkańców.", ("dla", "wobec", "przez"), 2, "W stronie biernej wykonawcę czynności wskazuje konstrukcja „przez mieszkańców”."),
        ),
    ),
)

MODULE_LABELS = {"listening": "Аудирование", "reading": "Чтение", "grammar": "Грамматика"}


def weekly_mock_variant(today: date) -> MockVariant:
    """Rotate predictably by ISO week without user-specific tracking."""
    return VARIANTS[(today.isocalendar().week - 1) % len(VARIANTS)]


def get_mock_variant(variant_id: str) -> MockVariant | None:
    return next((variant for variant in VARIANTS if variant.id == variant_id), None)


def score_mock_answers(answers: dict[str, int], variant: MockVariant | None = None) -> dict:
    """Score only the three objectively checked modules."""
    variant = variant or VARIANTS[0]
    questions = variant.questions
    expected_ids = {question.id for question in questions}
    if set(answers) != expected_ids:
        raise ValueError("Ответь на все проверяемые вопросы.")
    for question in questions:
        if answers[question.id] not in range(len(question.options)):
            raise ValueError("Выбран недопустимый вариант ответа.")

    details = []
    module_results = []
    for module, label in MODULE_LABELS.items():
        module_questions = [question for question in questions if question.module == module]
        correct = sum(answers[item.id] == item.correct for item in module_questions)
        module_results.append({"id": module, "label": label, "correct": correct, "total": len(module_questions), "percent": round(correct * 100 / len(module_questions))})
    for question in questions:
        selected = answers[question.id]
        details.append({
            "question": question,
            "selected": selected,
            "selected_text": question.options[selected],
            "correct_text": question.options[question.correct],
            "is_correct": selected == question.correct,
        })
    total_correct = sum(item["correct"] for item in module_results)
    return {"correct": total_correct, "total": len(questions), "modules": tuple(module_results), "details": tuple(details), "attempt_version": variant.id}
