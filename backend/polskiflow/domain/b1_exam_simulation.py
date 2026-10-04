"""Timed, original B1 section practice without claiming official assessment."""

from polskiflow.domain.b1_weekly_mock import MockQuestion, MockVariant


B1_SIMULATION_PARTS = (
    {"id": "listening", "title": "Аудирование", "polish_title": "Rozumienie ze słuchu", "minutes": 25, "accent": "blue", "mode": "objective"},
    {"id": "reading", "title": "Чтение", "polish_title": "Rozumienie tekstów pisanych", "minutes": 45, "accent": "green", "mode": "objective"},
    {"id": "grammar", "title": "Грамматика", "polish_title": "Poprawność gramatyczna", "minutes": 45, "accent": "violet", "mode": "objective"},
    {"id": "writing", "title": "Письмо", "polish_title": "Pisanie", "minutes": 75, "accent": "rose", "mode": "self_review"},
    {"id": "speaking", "title": "Говорение", "polish_title": "Mówienie", "minutes": 15, "accent": "amber", "mode": "self_review"},
)


# These original questions expand only the separately timed trainer. The weekly
# 15-minute mini-module deliberately keeps its smaller seven-question scope.
SIMULATION_EXTRA_QUESTIONS = {
    "b1-weekly-v1": (
        MockQuestion("sl3", "listening", "Gdzie uczestnicy mają się spotkać?", ("Przy wejściu do domu kultury", "W sali numer dwanaście", "Na przystanku obok parku"), 0, "Komunikat wyraźnie wskazuje główne wejście do domu kultury jako miejsce spotkania."),
        MockQuestion("sl4", "listening", "Co zmieni się w razie deszczu?", ("Warsztaty zostaną odwołane", "Pierwsza część odbędzie się w sali", "Trzeba przyjść godzinę później"), 1, "Deszcz zmienia jedynie miejsce pierwszej części zajęć, a nie godzinę ani termin."),
        MockQuestion("sl5", "listening", "Jaki jest główny cel komunikatu?", ("Sprzedać aparaty fotograficzne", "Zaprosić na wystawę zdjęć", "Przekazać organizacyjne szczegóły warsztatów"), 2, "Nagranie podaje nową godzinę, miejsce spotkania oraz listę potrzebnych rzeczy."),
        MockQuestion("sr3", "reading", "Jaką dodatkową korzyść zauważyła Marta?", ("Ma więcej energii", "Dostaje wyższą pensję", "Pracuje krócej"), 0, "Po rozpoczęciu dojazdów rowerem Marta zauważyła u siebie więcej energii."),
        MockQuestion("sr4", "reading", "Co firma zrobiła dla rowerzystów?", ("Kupiła wszystkim rowery", "Zamontowała stojaki rowerowe", "Zlikwidowała parking"), 1, "Tekst mówi o nowych stojakach, które zachęciły kolejnych pracowników do jazdy."),
        MockQuestion("sr5", "reading", "Które zdanie najlepiej podsumowuje tekst?", ("Marta całkowicie zrezygnowała z komunikacji miejskiej", "Rower jest zawsze najwygodniejszym środkiem transportu", "Marta łączy rower z autobusem zależnie od sytuacji"), 2, "Bohaterka zwykle wybiera rower, ale w trudniejszych warunkach korzysta z autobusu."),
        MockQuestion("sg4", "grammar", "To zadanie jest trudniejsze, ___ się spodziewałem.", ("niż", "jak", "żeby"), 0, "Stopień wyższy „trudniejsze” łączymy w takim porównaniu ze spójnikiem „niż”."),
        MockQuestion("sg5", "grammar", "Gdy wróciłem do domu, obiad już ___.", ("przygotowuje się", "był przygotowany", "przygotuje"), 1, "Strona bierna w czasie przeszłym pokazuje, że obiad był już gotowy wcześniej."),
        MockQuestion("sg6", "grammar", "Zadzwonię do ciebie, ___ tylko skończę spotkanie.", ("mimo że", "ponieważ", "jak"), 2, "W zdaniu czasowym „jak tylko” oznacza natychmiast po zakończeniu spotkania."),
    ),
    "b1-weekly-v2": (
        MockQuestion("sl3", "listening", "Gdzie odbędzie się spotkanie klubu?", ("W księgarni", "W czytelni na drugim piętrze", "W sali warsztatowej"), 1, "Uczestnicy mają przyjść do czytelni znajdującej się na drugim piętrze biblioteki."),
        MockQuestion("sl4", "listening", "O czym uczestnik ma porozmawiać?", ("O wybranym fragmencie książki", "O listopadowej pogodzie", "O pracy bibliotekarza"), 0, "Każdy zaznacza krótki fragment książki, który chce omówić podczas spotkania."),
        MockQuestion("sl5", "listening", "Co będzie możliwe po spotkaniu?", ("Wypożyczenie dowolnej nowości", "Zmiana terminu klubu", "Zapisanie się na listopadowe warsztaty"), 2, "Końcowa informacja dotyczy zapisów na warsztaty organizowane w listopadzie."),
        MockQuestion("sr3", "reading", "Co Piotr robi w przerwie obiadowej?", ("Jedzie do biura", "Idzie na krótki spacer", "Kończy pracę"), 1, "Krótki spacer podczas przerwy pomaga mu oddzielić pracę od odpoczynku."),
        MockQuestion("sr4", "reading", "Jak często Piotr pracuje z biura?", ("Dwa razy w tygodniu", "Codziennie", "Raz w miesiącu"), 0, "Tekst dokładnie podaje, że bohater pojawia się w biurze dwa razy tygodniowo."),
        MockQuestion("sr5", "reading", "Jaki kompromis znalazł Piotr?", ("Przestał pracować z domu", "Pracuje wyłącznie wieczorami", "Łączy pracę z domu z regularnymi wizytami w biurze"), 2, "Piotr zachował zalety pracy zdalnej, ale dwa razy w tygodniu spotyka współpracowników."),
        MockQuestion("sg4", "grammar", "Nie mogłem wejść, ponieważ zapomniałem ___.", ("kluczy", "klucze", "kluczami"), 0, "Czasownik „zapomnieć” w tym znaczeniu łączy się z dopełniaczem: „kluczy”."),
        MockQuestion("sg5", "grammar", "Anna zapytała, czy ___ jej w projekcie.", ("pomagam", "pomógłbym", "pomogę"), 1, "Pytanie pośrednie o hipotetyczną pomoc wymaga tutaj formy warunkowej „pomógłbym”."),
        MockQuestion("sg6", "grammar", "W przyszłym tygodniu będziemy ___ nowy plan.", ("omówili", "omawiając", "omawiać"), 2, "Czas przyszły złożony tworzymy z formy „będziemy” i bezokolicznika „omawiać”."),
    ),
    "b1-weekly-v3": (
        MockQuestion("sl3", "listening", "Dlaczego pociąg jest opóźniony?", ("Z powodu prac na torach", "Z powodu złej pogody", "Z powodu kontroli biletów"), 0, "Komunikat bezpośrednio łączy dwudziestominutowe opóźnienie z pracami na torach."),
        MockQuestion("sl4", "listening", "O ile później odjedzie pociąg?", ("O dziesięć minut", "O dwadzieścia minut", "O trzydzieści minut"), 1, "Zapowiedziane w komunikacie opóźnienie pociągu wynosi dokładnie dwadzieścia minut."),
        MockQuestion("sl5", "listening", "Co trzeba zrobić z biletem?", ("Wymienić go w kasie", "Dopłacić za zmianę peronu", "Zachować go, ponieważ nadal jest ważny"), 2, "Bilety zachowują ważność, więc podróżni nie muszą ich wymieniać."),
        MockQuestion("sr3", "reading", "Kto podlewa rośliny podczas urlopu?", ("Sąsiedzi", "Pracownicy miasta", "Właściciel sklepu"), 0, "Mieszkańcy dzielą się obowiązkami i zastępują sąsiadów podczas ich urlopu."),
        MockQuestion("sr4", "reading", "Jaką społeczną funkcję pełni ogród?", ("Jest miejscem sprzedaży", "Stał się miejscem spotkań", "Zastępuje plac zabaw"), 1, "Poza świeżymi produktami ogród daje mieszkańcom wspólną przestrzeń do spotkań."),
        MockQuestion("sr5", "reading", "Co pokazuje historia wspólnego ogrodu?", ("Wspólne inicjatywy nie wymagają zasad", "Najważniejszy jest zakup profesjonalnych narzędzi", "Współpraca daje korzyści, choć wymaga uzgodnień"), 2, "Tekst pokazuje zarówno korzyści wspólnej pracy, jak i trudne rozmowy o zasadach."),
        MockQuestion("sg4", "grammar", "Nie wiedziałem, że sąsiedzi już ___ ogród.", ("założyli", "zakładają jutro", "założą wczoraj"), 0, "Dokonana forma przeszła „założyli” pasuje do czynności zakończonej przed odkryciem."),
        MockQuestion("sg5", "grammar", "To miejsce, ___ mieszkańcy często się spotykają.", ("którego", "w którym", "któremu"), 1, "Mówimy „spotykać się w miejscu”, dlatego potrzebujemy konstrukcji „w którym”."),
        MockQuestion("sg6", "grammar", "Gdybyśmy mieli więcej miejsca, ___ też drzewa.", ("sadzimy", "posadzimy", "posadzilibyśmy"), 2, "Warunek nierealny z „gdybyśmy” wymaga formy warunkowej „posadzilibyśmy”."),
    ),
}


def get_simulation_part(part_id: str) -> dict | None:
    return next((dict(part) for part in B1_SIMULATION_PARTS if part["id"] == part_id), None)


def simulation_questions(variant: MockVariant, part_id: str) -> tuple:
    questions = (*variant.questions, *SIMULATION_EXTRA_QUESTIONS.get(variant.id, ()))
    return tuple(question for question in questions if question.module == part_id)


def score_simulation_part(variant: MockVariant, part_id: str, answers: dict[str, int]) -> dict:
    """Score exactly one objective section; free production is never graded."""
    part = get_simulation_part(part_id)
    if part is None or part["mode"] != "objective":
        raise ValueError("Эта часть доступна только для самопроверки.")
    questions = simulation_questions(variant, part_id)
    if set(answers) != {question.id for question in questions}:
        raise ValueError("Ответь на все вопросы выбранной части.")
    details = []
    for question in questions:
        selected = answers[question.id]
        if selected not in range(len(question.options)):
            raise ValueError("Выбран недопустимый вариант ответа.")
        details.append({
            "question": question,
            "selected": selected,
            "selected_text": question.options[selected],
            "correct_text": question.options[question.correct],
            "is_correct": selected == question.correct,
        })
    correct = sum(item["is_correct"] for item in details)
    return {
        "correct": correct,
        "total": len(questions),
        "percent": round(correct * 100 / len(questions)),
        "details": tuple(details),
    }
