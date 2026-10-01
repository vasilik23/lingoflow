"""Small, original B1 mock module with deterministic objective scoring."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MockQuestion:
    id: str
    module: str
    prompt: str
    options: tuple[str, ...]
    correct: int
    explanation: str


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
    MockQuestion("l2", "listening", "Co trzeba przynieść?", ("Tylko dokumenty", "Aparat lub telefon i napój", "Własne krzesło"), 1, "Organizator prosi o telefon lub aparat oraz coś do picia."),
    MockQuestion("r1", "reading", "Dlaczego Marta początkowo wybrała rower?", ("Chciała uniknąć korków", "Firma zabroniła jazdy autobusem", "Chciała przewozić dokumenty"), 0, "Pierwsze zdania wskazują, że początkowym powodem były korki."),
    MockQuestion("r2", "reading", "Kiedy Marta wybiera autobus?", ("Codziennie rano", "Gdy pada lub ma ciężki bagaż", "Tylko w weekend"), 1, "Tekst wymienia silny deszcz i ciężkie dokumenty."),
    MockQuestion("g1", "grammar", "Gdybym miał więcej czasu, ___ częściej po polsku.", ("czytam", "czytałbym", "przeczytam"), 1, "Po „gdybym” używamy trybu warunkowego: „czytałbym”."),
    MockQuestion("g2", "grammar", "Nie znam osoby, ___ mogłaby nam pomóc.", ("która", "której", "którą"), 0, "Zaimek jest podmiotem czasownika „mogłaby”, dlatego ma formę „która”."),
    MockQuestion("g3", "grammar", "Proszę wysłać dokumenty ___ piątku.", ("od", "do", "przez"), 1, "Termin końcowy wyrażamy konstrukcją „do piątku”."),
)

MODULE_LABELS = {"listening": "Аудирование", "reading": "Чтение", "grammar": "Грамматика"}


def score_mock_answers(answers: dict[str, int]) -> dict:
    """Score only the three objectively checked modules."""
    expected_ids = {question.id for question in QUESTIONS}
    if set(answers) != expected_ids:
        raise ValueError("Ответь на все проверяемые вопросы.")
    for question in QUESTIONS:
        if answers[question.id] not in range(len(question.options)):
            raise ValueError("Выбран недопустимый вариант ответа.")

    details = []
    module_results = []
    for module, label in MODULE_LABELS.items():
        questions = [question for question in QUESTIONS if question.module == module]
        correct = sum(answers[item.id] == item.correct for item in questions)
        module_results.append({"id": module, "label": label, "correct": correct, "total": len(questions), "percent": round(correct * 100 / len(questions))})
    for question in QUESTIONS:
        selected = answers[question.id]
        details.append({
            "question": question,
            "selected": selected,
            "selected_text": question.options[selected],
            "correct_text": question.options[question.correct],
            "is_correct": selected == question.correct,
        })
    total_correct = sum(item["correct"] for item in module_results)
    return {"correct": total_correct, "total": len(QUESTIONS), "modules": tuple(module_results), "details": tuple(details)}
