"""Original narration drafts; not enabled in guided runs or approved as audio.

Created for PolskiFlow, origin original, internally reviewed 2026-10-06.
Independent Polish review and rights-cleared recordings are still required.
"""
from dataclasses import dataclass
from polskiflow.domain.b1_weekly_mock import MockQuestion


@dataclass(frozen=True)
class ListeningDraft:
    id: str
    title: str
    genre: str
    transcript: str
    questions: tuple[MockQuestion, ...]
    voice_notes: str


LISTENING_DRAFTS = (
    ListeningDraft(
        'station', 'Zmiana planu podróży', 'announcement',
        'Uwaga, podróżni. Pociąg do Torunia, który miał odjechać o godzinie czternastej dwadzieścia, '
        'odjedzie dziś o czternastej pięćdziesiąt. Przyczyną opóźnienia jest awaria na wcześniejszym odcinku trasy. '
        'Prosimy nie przechodzić na peron drugi. Pociąg zostanie podstawiony na peron czwarty. '
        'Bilety zachowują ważność i nie trzeba ich wymieniać. Osoby, które rezygnują z podróży, '
        'mogą zgłosić się do kasy po zwrot pieniędzy. Kasa znajduje się w głównym budynku, obok informacji. '
        'Przypominamy, że wejście od ulicy Ogrodowej jest dziś zamknięte z powodu remontu. '
        'Do budynku można wejść od placu przed dworcem. Kolejna informacja o odjeździe zostanie podana za dziesięć minut.',
        (
            MockQuestion('tl06', 'listening', 'O której ma dziś odjechać pociąg?', ('14:20', '14:50', '15:20'), 1, 'Nowa godzina odjazdu to 14:50, a nie pierwotna 14:20.'),
            MockQuestion('tl07', 'listening', 'Z którego peronu odjedzie pociąg?', ('Z czwartego', 'Z drugiego', 'Z pierwszego'), 0, 'Komunikat odwołuje peron drugi i wskazuje peron czwarty.'),
            MockQuestion('tl08', 'listening', 'Co musi zrobić osoba, która nadal chce jechać?', ('Wymienić bilet', 'Kupić dopłatę', 'Zachować obecny bilet'), 2, 'Bilety zachowują ważność i nie wymagają wymiany.'),
            MockQuestion('tl09', 'listening', 'Gdzie można otrzymać zwrot pieniędzy?', ('Na peronie', 'W kasie obok informacji', 'Przy zamkniętym wejściu'), 1, 'Zwrot pieniędzy jest dostępny w kasie w głównym budynku obok informacji.'),
            MockQuestion('tl10', 'listening', 'Którym wejściem można wejść do budynku?', ('Od placu przed dworcem', 'Od ulicy Ogrodowej', 'Tylko przez peron drugi'), 0, 'Wejście od ulicy Ogrodowej jest zamknięte; dostępne jest wejście od placu.'),
        ),
        'One announcer. Preserve the correction of the time and platform; do not emphasize answers artificially.',
    ),
    ListeningDraft(
        'course', 'Telefon do pracowni', 'dialogue',
        'Dzień dobry, chciałbym zapisać się na warsztaty gotowania. Czy są jeszcze miejsca w sobotę?\n\n'
        'Dzień dobry. Sobotnia grupa jest już pełna. Mamy dwa wolne miejsca w niedzielę od jedenastej do czternastej.\n\n'
        'Niedziela mi odpowiada. Czy trzeba przynieść produkty albo własny fartuch?\n\n'
        'Produkty i fartuchy zapewniamy. Proszę tylko zabrać pojemnik, jeśli chce pan zabrać przygotowane danie do domu. '
        'Udział kosztuje osiemdziesiąt złotych.\n\n'
        'Chętnie przyjdę. Mogę zapłacić na miejscu? I czy muszę już teraz podać, że nie jem mięsa?\n\n'
        'Płatność przyjmujemy przelewem najpóźniej do piątku. Rezerwację potwierdzimy po otrzymaniu pieniędzy. '
        'Informację o diecie proszę wpisać w formularzu zgłoszeniowym, żebyśmy mogli wcześniej przygotować odpowiednie produkty.',
        (
            MockQuestion('tl11', 'listening', 'Dlaczego klient wybiera niedzielę?', ('W sobotę nie ma już miejsc', 'W niedzielę jest taniej', 'W sobotę pracownia jest zamknięta'), 0, 'Sobotnia grupa jest pełna, a w niedzielnej są wolne miejsca.'),
            MockQuestion('tl12', 'listening', 'Co uczestnik ma przynieść, aby zabrać danie do domu?', ('Produkty', 'Fartuch', 'Pojemnik'), 2, 'Pracownia zapewnia produkty i fartuch, ale prosi o własny pojemnik.'),
            MockQuestion('tl13', 'listening', 'Jak trzeba zapłacić?', ('Gotówką po zajęciach', 'Przelewem do piątku', 'Kartą w niedzielę'), 1, 'Płatność jest przelewem najpóźniej do piątku, a nie na miejscu.'),
            MockQuestion('tl14', 'listening', 'Kiedy rezerwacja zostanie potwierdzona?', ('Po otrzymaniu pieniędzy', 'Od razu po telefonie', 'Po zakończeniu warsztatów'), 0, 'Potwierdzenie nastąpi po otrzymaniu płatności.'),
            MockQuestion('tl15', 'listening', 'Po co trzeba wcześniej podać informację o diecie?', ('Żeby dostać niższą cenę', 'Żeby zmienić godzinę zajęć', 'Żeby pracownia przygotowała odpowiednie produkty'), 2, 'Informacja w formularzu pozwala wcześniej przygotować produkty odpowiednie dla uczestnika.'),
        ),
        'Two voices, alternating at each blank line: male customer, staff member. Paragraph boundaries are speaker changes; do not read role labels.',
    ),
    ListeningDraft(
        'interview', 'Rozmowa o wymianie książek', 'interview',
        'Pani Marto, od czego zaczęła się sąsiedzka wymiana książek?\n\n'
        'Po przeprowadzce znalazłam w kartonach wiele książek, do których już nie wracałam. '
        'Nie chciałam ich sprzedawać, więc zaprosiłam sąsiadów do wymiany. Pierwsze spotkanie odbyło się na podwórku.\n\n'
        'Czy trzeba przynieść książkę, żeby coś wybrać?\n\n'
        'Nie, można też przyjść bez niej. Prosimy jednak o zabieranie tylko dwóch książek podczas jednego spotkania, '
        'żeby wystarczyło dla innych. Przyjmujemy wyłącznie książki w dobrym stanie, bez brakujących stron.\n\n'
        'Jak organizujecie spotkania zimą i kto zajmuje się książkami, które zostają?\n\n'
        'Od listopada spotykamy się w sali domu kultury w ostatnią sobotę miesiąca. '
        'Nie zwiększamy częstotliwości spotkań. Książki, które zostają, przechowujemy do kolejnego spotkania; '
        'nie przekazujemy ich automatycznie bibliotece. Dwóch wolontariuszy pomaga nam je uporządkować. '
        'Najbardziej cieszy mnie to, że sąsiedzi, którzy wcześniej się nie znali, zaczęli ze sobą rozmawiać.',
        (
            MockQuestion('tl16', 'listening', 'Co było powodem zorganizowania pierwszej wymiany?', ('Prośba biblioteki', 'Znalezienie własnych nieużywanych książek po przeprowadzce', 'Zamknięcie domu kultury'), 1, 'Marta znalazła po przeprowadzce książki, do których już nie wracała.'),
            MockQuestion('tl17', 'listening', 'Ile książek można zabrać na jednym spotkaniu?', ('Dwie', 'Dowolną liczbę', 'Tylko jedną'), 0, 'Limit wynosi dwie książki, aby wystarczyło dla innych.'),
            MockQuestion('tl18', 'listening', 'Co zmienia się od listopada?', ('Spotkania odbywają się co tydzień', 'Trzeba kupić bilet', 'Spotkania przenoszą się do sali domu kultury'), 2, 'Od listopada zmienia się miejsce, ale nie częstotliwość spotkań.'),
            MockQuestion('tl19', 'listening', 'Co dzieje się z książkami, które zostają?', ('Są automatycznie oddawane bibliotece', 'Czekają na kolejne spotkanie', 'Są sprzedawane przez wolontariuszy'), 1, 'Pozostałe książki są przechowywane do kolejnego spotkania.'),
            MockQuestion('tl20', 'listening', 'Co Marta uważa za najważniejszy efekt wymiany?', ('Nowe rozmowy i znajomości między sąsiadami', 'Zarobione pieniądze', 'Większą liczbę spotkań w miesiącu'), 0, 'Marta najbardziej cieszy się z rozmów między sąsiadami, którzy wcześniej się nie znali.'),
        ),
        'Two voices alternating at blank lines: interviewer and Marta. Natural interview pace; keep explicit negations and limits.',
    ),
)
