"""Versioned original question sets for the guided B1 run."""

from datetime import date

from polskiflow.domain.b1_weekly_mock import MockQuestion
from polskiflow.domain.b1_exam_simulation import simulation_questions, score_simulation_part
from polskiflow.domain.b1_training_reading import READING_BLOCKS, ReadingBlock

CONTENT_VERSION = 5
ORIGIN = "original"
CREATED_FOR = "PolskiFlow"
VERIFIED_AT = date(2026, 10, 5)  # Internal editorial review, not independent validation.

# Shared extension across the three variants; the first six items remain variant-specific.
RUN_GRAMMAR_QUESTIONS = (
    MockQuestion("tg07", "grammar", "Przyglądam się ___, które wiszą w galerii.", ("obrazów", "obrazom", "obrazami"), 1, "Czasownik „przyglądać się” wymaga celownika: „przyglądam się obrazom”."),
    MockQuestion("tg08", "grammar", "Nie kupiłam ___, bo były za drogie.", ("tych butów", "te buty", "tymi butami"), 0, "Po zaprzeczonym czasowniku „nie kupiłam” używamy dopełniacza: „tych butów”."),
    MockQuestion("tg09", "grammar", "Interesuję się ___ nowoczesną.", ("architekturę", "architektury", "architekturą"), 2, "Czasownik „interesować się” łączy się z narzędnikiem: „architekturą nowoczesną”."),
    MockQuestion("tg10", "grammar", "To koleżanka, z ___ chodzę na kurs polskiego.", ("której", "która", "którą"), 2, "Przyimek „z” oznaczający towarzystwo wymaga narzędnika: „z którą”."),
    MockQuestion("tg11", "grammar", "Nie mam numeru do pana, ___ naprawił nam pralkę.", ("który", "którego", "którym"), 0, "Zaimek jest podmiotem zdania „naprawił nam pralkę”: „pan, który naprawił”."),
    MockQuestion("tg12", "grammar", "Te dokumenty zostały ___ przez sekretarkę.", ("podpisane", "podpisany", "podpisana"), 0, "Imiesłów zgadza się z niemęskoosobową liczbą mnogą „dokumenty”: „zostały podpisane”."),
    MockQuestion("tg13", "grammar", "Wczoraj dwaj studenci ___ na egzamin za późno.", ("przyszły", "przyszli", "przyszła"), 1, "Podmiot „dwaj studenci” wymaga męskoosobowej formy liczby mnogiej „przyszli”."),
    MockQuestion("tg14", "grammar", "Kasia poprosiła mnie, ___ zamknął okno.", ("żebym", "żebyś", "żebyśmy"), 0, "Kasia zwraca się do mnie; w zdaniu zależnym mówię o sobie: „żebym zamknął”."),
    MockQuestion("tg15", "grammar", "Ten pokój jest ___ od poprzedniego.", ("większa", "większe", "większy"), 2, "Przymiotnik zgadza się z rodzajem męskim podmiotu „pokój”: „pokój jest większy”."),
    MockQuestion("tg16", "grammar", "Chociaż padał deszcz, ___ na spacer.", ("poszliśmy", "pójść", "idąc"), 0, "Po zdaniu z „chociaż” potrzebujemy osobowej formy czasownika; tutaj poprawna jest „poszliśmy”."),
    MockQuestion("tg17", "grammar", "Proszę oddać książkę ___ tygodnia.", ("do końcu", "do końca", "do koniec"), 1, "Przyimek „do” wymaga dopełniacza: „do końca tygodnia”. Wyrażenie wyznacza termin oddania książki."),
    MockQuestion("tg18", "grammar", "Dzięki ___ szybko znaleźliśmy właściwy adres.", ("twoją pomoc", "twojej pomocy", "twoja pomoc"), 1, "Przyimek „dzięki” wymaga celownika: „dzięki twojej pomocy”."),
    MockQuestion("tg19", "grammar", "Zamiast ___ taksówką, pojechaliśmy tramwajem.", ("jazda", "jazdę", "jazdy"), 2, "Przyimek „zamiast” łączy się z dopełniaczem: „zamiast jazdy taksówką”."),
    MockQuestion("tg20", "grammar", "Wybierz spójnik wyrażający skutek: Spotkanie skończyło się wcześniej, ___ mogliśmy zdążyć na pociąg.", ("dlatego", "chociaż", "pomimo"), 0, "„Dlatego” wskazuje skutek wcześniejszego zakończenia spotkania; „pomimo” nie wprowadza tutaj zdania, a „chociaż” nie wyraża skutku."),
)


def _extra_questions(part_id, content_version):
    if part_id == "grammar" and content_version >= 2:
        return RUN_GRAMMAR_QUESTIONS
    if part_id == "reading" and content_version >= 3:
        return tuple(question for block in READING_BLOCKS for question in block.questions)
    return ()


def training_reading_blocks(variant, content_version=CONTENT_VERSION):
    title = {"b1-weekly-v1": "Dojazdy rowerem", "b1-weekly-v2": "Praca w domu i w biurze", "b1-weekly-v3": "Wspólny ogród"}.get(variant.id, "Krótki artykuł")
    first = ReadingBlock("variant", title, variant.reading_text, simulation_questions(variant, "reading"))
    return (first, *READING_BLOCKS) if content_version >= 3 else (first,)


def training_questions(variant, part_id, content_version=CONTENT_VERSION):
    extra = _extra_questions(part_id, content_version)
    return (*simulation_questions(variant, part_id), *extra)


def score_training_part(variant, part_id, answers, content_version=CONTENT_VERSION):
    extra = _extra_questions(part_id, content_version)
    return score_simulation_part(variant, part_id, answers, extra_questions=extra)
