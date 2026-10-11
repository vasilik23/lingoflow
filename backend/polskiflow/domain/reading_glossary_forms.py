"""Explicit forms reviewed against each original reading, never stemming rules."""

READING_GLOSSARY_FORMS = {
    "c11-tekst": {"potoczna": "potoczny", "adresata": "adresat"},
    "c12-tekst": {"przesłanki": "przesłanka", "zważył argumenty": "ważyć argumenty", "nie przesądzał": "nie przesądza"},
    "c13-tekst": {"ramę interpretacyjną": "rama interpretacyjna", "pozornie neutralnie": "pozornie neutralny"},
    "c14-tekst": {"podała analogię": "podać analogię"},
    "c15-tekst": {"zdaniu tematycznym": "zdanie tematyczne", "hierarchię informacji": "hierarchia informacji", "doprecyzowała własną tezę": "doprecyzować tezę"},
    "c16-tekst": {"warunków brzegowych": "warunek brzegowy", "zakresu odpowiedzialności": "zakres odpowiedzialności", "ryzyka operacyjne": "ryzyko operacyjne", "oszacowała nakład": "oszacować nakład", "wariantu awaryjnego": "wariant awaryjny", "odpowiedzialność końcową": "odpowiedzialność końcowa"},
    "c17-tekst": {"metafory": "metafora", "interpretacji": "interpretacja", "ironię dramatyczną": "ironia dramatyczna", "perspektyw": "perspektywa"},
    "c18-tekst": {"interesariuszy": "interesariusz", "oddała sprawiedliwość argumentowi": "oddać sprawiedliwość argumentowi", "eskalowała konflikt": "eskalować konflikt", "warunki konieczne": "warunek konieczny"},
    "c19-tekst": {"depeszę": "depesza", "leadu": "lead", "wyostrzał tezę": "wyostrzyć tezę"},
    "c110-tekst": {"odpowiedział na zarzut": "odpowiedzieć na zarzut", "uznał ograniczenie": "uznać ograniczenie", "dalszym kierunkiem": "dalszy kierunek"},
    "c22-tekst": {"puenty": "puenta", "gradacji": "gradacja", "antytezy": "antyteza", "uczciwości argumentacyjnej": "uczciwość argumentacyjna", "odwrócenie perspektywy": "odwrócić perspektywę"},
    "c23-tekst": {"przesłankę": "przesłanka", "konkluzję": "konkluzja", "uczciwą rekonstrukcję": "uczciwa rekonstrukcja"},
    "c24-tekst": {"rozluźniła składnię": "rozluźnić składnię", "ujednoliciła naukowy rejestr": "ujednolicić rejestr"},
    "c25-tekst": {"hierarchię faktów": "hierarchia faktów"},
    "c26-tekst": {"horyzontach oczekiwań": "horyzont oczekiwań"},
    "c27-tekst": {"wspólnym mianownikiem": "wspólny mianownik", "asymetrię wiedzy": "asymetria wiedzy", "uzgodnienia definicji": "uzgodnić definicję"},
    "c210-tekst": {"informacji zwrotnej": "informacja zwrotna", "arkuszu samooceny": "arkusz samooceny"},
}


def with_reading_forms(entries, text_id):
    """Only reuse an existing entry; an updated glossary remains authoritative."""
    result = dict(entries)
    for surface, canonical in READING_GLOSSARY_FORMS.get(text_id, {}).items():
        if canonical in entries and surface not in entries:
            result[surface] = {**entries[canonical], "glossary_word": canonical}
    return result
