"""Original, shared B1 reading blocks for guided-run content version three."""

from dataclasses import dataclass

from polskiflow.domain.b1_weekly_mock import MockQuestion


@dataclass(frozen=True)
class ReadingBlock:
    id: str
    title: str
    text: str
    questions: tuple[MockQuestion, ...]


READING_BLOCKS = (
    ReadingBlock(
        "library", "Ogłoszenie biblioteki",
        "Od poniedziałku biblioteka osiedlowa będzie remontowana. Prace potrwają dwa tygodnie. "
        "W tym czasie książki można oddawać do skrzynki przy bocznym wejściu, także po zamknięciu budynku. "
        "Skrzynka służy wyłącznie do zwrotów; nie należy wkładać do niej książek przeznaczonych na darowiznę. "
        "Termin zwrotu książek wypożyczonych przed remontem zostanie automatycznie przedłużony o dwa tygodnie. "
        "Czytelnicy mogą zamawiać dostępne książki przez internet i odbierać je w bibliotece przy ulicy Leśnej. "
        "Odbiór będzie możliwy dopiero po otrzymaniu wiadomości z potwierdzeniem. "
        "Zaplanowane spotkanie z autorką odbędzie się w domu kultury w pierwotnym terminie. "
        "Osoby zapisane na spotkanie nie muszą zgłaszać się ponownie.",
        (
            MockQuestion("tr06", "reading", "Jak długo potrwa remont?", ("Tydzień", "Dwa tygodnie", "Miesiąc"), 1, "Ogłoszenie podaje, że prace potrwają dwa tygodnie."),
            MockQuestion("tr07", "reading", "Do czego służy skrzynka przy bocznym wejściu?", ("Do zamawiania książek", "Do przekazywania darowizn", "Wyłącznie do zwrotu wypożyczonych książek"), 2, "Skrzynka służy do zwrotów, a nie do przekazywania książek na darowiznę."),
            MockQuestion("tr08", "reading", "Co trzeba zrobić, aby przedłużyć termin zwrotu?", ("Nic, termin zostanie przedłużony automatycznie", "Wysłać wiadomość do biblioteki", "Zgłosić się przy ulicy Leśnej"), 0, "Dla książek wypożyczonych przed remontem przedłużenie następuje automatycznie."),
            MockQuestion("tr09", "reading", "Kiedy można odebrać zamówioną książkę?", ("Natychmiast po złożeniu zamówienia", "Po otrzymaniu potwierdzenia", "Dopiero po zakończeniu remontu"), 1, "Odbiór w bibliotece przy ulicy Leśnej jest możliwy dopiero po wiadomości z potwierdzeniem."),
            MockQuestion("tr10", "reading", "Co zmieni się w organizacji spotkania z autorką?", ("Trzeba ponownie się zapisać", "Spotkanie odbędzie się później", "Zmieni się miejsce, ale nie termin"), 2, "Spotkanie przeniesiono do domu kultury, zachowując termin i wcześniejsze zapisy."),
        ),
    ),
    ReadingBlock(
        "trip", "Wiadomość do koleżanki",
        "Cześć Aniu! Piszę w sprawie naszej sobotniej wycieczki. Sprawdziłam rozkład: "
        "poranny autobus nie kursuje w weekendy, dlatego proponuję pociąg o dziewiątej. "
        "Będziemy na miejscu przed dziesiątą. Możemy najpierw zostawić plecaki w przechowalni "
        "na dworcu, bo do muzeum nie wolno wchodzić z dużym bagażem. "
        "Nie kupuj jeszcze biletu do muzeum. Zarezerwowałam dla nas dwa miejsca na zwiedzanie "
        "z przewodnikiem, ale płaci się dopiero przy wejściu. Rezerwacja jest ważna do jedenastej. "
        "Po zwiedzaniu chciałabym zjeść obiad w małej restauracji przy rynku. Jeśli będzie dobra "
        "pogoda, później pójdziemy nad rzekę; w razie deszczu zostaniemy dłużej w centrum. "
        "Daj znać do piątku wieczorem, czy odpowiada Ci ten plan. Ola",
        (
            MockQuestion("tr11", "reading", "Dlaczego Ola proponuje podróż pociągiem?", ("Poranny autobus nie kursuje w weekendy", "Pociąg jest bezpłatny", "Ania nie lubi autobusów"), 0, "Powodem zmiany środka transportu jest weekendowy rozkład autobusów."),
            MockQuestion("tr12", "reading", "Dlaczego koleżanki mają zostawić plecaki na dworcu?", ("Nie chcą płacić za przewóz bagażu", "Nie wolno wejść do muzeum z dużym bagażem", "Przechowalnia znajduje się w muzeum"), 1, "Ola wskazuje zakaz wchodzenia do muzeum z dużym bagażem."),
            MockQuestion("tr13", "reading", "Co Ola już zrobiła?", ("Zapłaciła za bilety do muzeum", "Kupiła bilety autobusowe", "Zarezerwowała zwiedzanie dla dwóch osób"), 2, "Miejsca na zwiedzanie są zarezerwowane, lecz opłata nastąpi dopiero przy wejściu."),
            MockQuestion("tr14", "reading", "Od czego zależy spacer nad rzekę?", ("Od pogody", "Od godziny odjazdu autobusu", "Od dostępności przewodnika"), 0, "Spacer jest planowany przy dobrej pogodzie; deszcz oznacza dłuższy pobyt w centrum."),
            MockQuestion("tr15", "reading", "Po co Ola prosi o odpowiedź do piątku?", ("Aby zmienić termin zwiedzania", "Aby potwierdzić, czy Ania zgadza się na plan", "Aby odebrać pieniądze za bilet"), 1, "Końcowa prośba dotyczy akceptacji przedstawionego planu."),
        ),
    ),
    ReadingBlock(
        "repair", "Nowa inicjatywa sąsiadów",
        "Kiedy w bloku Pawła zepsuł się kolejny drobny sprzęt, ktoś zaproponował wspólne "
        "spotkania naprawcze. Początkowo mieszkańcy obawiali się, że nikt nie przyjdzie. "
        "Na pierwsze spotkanie zgłosiło się jednak kilkanaście osób. Jedna sąsiadka umiała "
        "szyć, inny sąsiad naprawiał rowery, a Paweł pomagał organizować stanowiska. "
        "Ustalili, że nie będą przyjmować urządzeń elektrycznych, ponieważ nie mają "
        "odpowiednich kwalifikacji. Udział w spotkaniach jest bezpłatny, ale każdy "
        "przynosi potrzebne części do swojego przedmiotu. Nie wszystkie naprawy się udają. "
        "Organizatorzy podkreślają jednak, że równie ważne jest dzielenie się "
        "umiejętnościami. Po trzech miesiącach do grupy dołączyli mieszkańcy sąsiedniej "
        "ulicy. Zamiast spotykać się częściej, grupa przeniosła zajęcia do większej "
        "sali, aby zachować dotychczasowy miesięczny rytm.",
        (
            MockQuestion("tr16", "reading", "Czego obawiali się mieszkańcy przed pierwszym spotkaniem?", ("Zbyt wysokich opłat", "Braku sali dla wszystkich", "Braku zainteresowania"), 2, "Początkowo mieszkańcy sądzili, że na spotkanie może nikt nie przyjść."),
            MockQuestion("tr17", "reading", "Dlaczego grupa nie przyjmuje urządzeń elektrycznych?", ("Nie ma odpowiednich kwalifikacji", "Naprawy są zbyt drogie", "Takie urządzenia nigdy się nie psują"), 0, "Decyzja wynika z braku odpowiednich kwalifikacji, a nie z kosztów."),
            MockQuestion("tr18", "reading", "Jakie koszty może ponieść uczestnik?", ("Opłatę za wejście", "Koszt części do własnego przedmiotu", "Obowiązkową miesięczną składkę"), 1, "Udział jest bezpłatny, lecz uczestnik sam dostarcza potrzebne części."),
            MockQuestion("tr19", "reading", "Co organizatorzy uznają za wartość spotkań poza naprawą?", ("Sprzedaż nowych urządzeń", "Możliwość pracy zarobkowej", "Dzielenie się umiejętnościami"), 2, "Tekst podkreśla znaczenie wymiany umiejętności nawet wtedy, gdy naprawa się nie uda."),
            MockQuestion("tr20", "reading", "Jak grupa zareagowała na wzrost liczby uczestników?", ("Przeniosła spotkania do większej sali", "Zaczęła spotykać się co tydzień", "Przestała przyjmować nowych sąsiadów"), 0, "Zmieniono salę, zachowując miesięczną częstotliwość spotkań."),
        ),
    ),
)
