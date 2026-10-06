"""Original additional B1 grammar items for guided-run version six.

Created for PolskiFlow; internally reviewed 2026-10-06. These multiple-choice
items practise form recognition, not all formats of an official examination.
"""
from polskiflow.domain.b1_weekly_mock import MockQuestion

GRAMMAR_EXTENSION = (
    MockQuestion('tg21', 'grammar', 'Przed wyjazdem muszę kupić ___ na pociąg.', ('biletu', 'bilet', 'biletem'), 1, 'Po „kupić” bez przeczenia używamy biernika: „kupić bilet”.'),
    MockQuestion('tg22', 'grammar', 'Nie pamiętam adresu ___, u której byłem wczoraj.', ('koleżanki', 'koleżankę', 'koleżanką'), 0, 'Rzeczownik „adres” łączy się tu z dopełniaczem osoby: „adres koleżanki”.'),
    MockQuestion('tg23', 'grammar', 'Rozmawialiśmy przez telefon z ___ sąsiadem.', ('nowego', 'nowemu', 'nowym'), 2, '„Z” w znaczeniu towarzystwa wymaga narzędnika; przymiotnik zgadza się z „sąsiadem”: „nowym”.'),
    MockQuestion('tg24', 'grammar', 'Ten prezent kupiłam dla mojej ___.', ('siostrę', 'siostry', 'siostrą'), 1, 'Przyimek „dla” wymaga dopełniacza: „dla mojej siostry”.'),
    MockQuestion('tg25', 'grammar', 'Wczoraj pomagałem ___ przygotować salę.', ('nauczycielowi', 'nauczyciela', 'nauczycielem'), 0, 'Czasownik „pomagać” wymaga celownika osoby: „pomagałem nauczycielowi”.'),
    MockQuestion('tg26', 'grammar', 'W przyszłym miesiącu Anna będzie ___ nową pracę.', ('zaczynając', 'zaczęła', 'zaczynać'), 2, '„Będzie” z bezokolicznikiem tworzy czas przyszły złożony: „będzie zaczynać”.'),
    MockQuestion('tg27', 'grammar', 'Kiedy zadzwoniłeś, właśnie ___ obiad.', ('gotuję jutro', 'gotowałem', 'ugotować'), 1, 'Czynność trwającą w chwili innego zdarzenia w przeszłości wyraża „gotowałem”.'),
    MockQuestion('tg28', 'grammar', 'Gdybym znał odpowiedź, od razu ci ___.', ('powiedziałbym', 'powiedziałem', 'powiem'), 0, 'Zdanie z „gdybym” wymaga trybu przypuszczającego: „powiedziałbym”.'),
    MockQuestion('tg29', 'grammar', 'Pani Anno, proszę ___ ten formularz.', ('wypełniła', 'wypełniając', 'wypełnić'), 2, 'W prośbie „proszę” łączy się z bezokolicznikiem: „proszę wypełnić”.'),
    MockQuestion('tg30', 'grammar', 'Nie mogę teraz wyjść, bo jeszcze ___ zadania.', ('skończyłem', 'nie skończyłem', 'skończę wczoraj'), 1, '„Jeszcze nie skończyłem” oznacza, że zadanie nadal nie jest ukończone.'),
    MockQuestion('tg31', 'grammar', 'To książka, ___ poleciła mi nauczycielka.', ('którą', 'której', 'którzy'), 0, 'Zaimek jest dopełnieniem „poleciła”; dla „książka” potrzebny jest biernik: „którą”.'),
    MockQuestion('tg32', 'grammar', 'Pójdziemy na spacer, ___ przestanie padać.', ('pomimo', 'dlatego', 'kiedy'), 2, '„Kiedy” wprowadza zdanie określające czas wyjścia na spacer.'),
    MockQuestion('tg33', 'grammar', 'Wybierz spójnik wyrażający przeciwstawienie: Byłem zmęczony, ___ dokończyłem pracę.', ('ponieważ', 'ale', 'żeby'), 1, '„Ale” łączy przeciwstawne informacje: zmęczenie i ukończenie pracy.'),
    MockQuestion('tg34', 'grammar', 'Zapisałem numer, ___ go nie zapomnieć.', ('żeby', 'chociaż', 'więc'), 0, '„Żeby” z bezokolicznikiem wyraża cel zapisania numeru.'),
    MockQuestion('tg35', 'grammar', 'Wybierz spójnik wyrażający przyczynę: Nie poszliśmy na koncert, ___ zabrakło biletów.', ('mimo że', 'żeby', 'ponieważ'), 2, '„Ponieważ” wprowadza przyczynę; brak biletów wyjaśnia rezygnację z koncertu.'),
    MockQuestion('tg36', 'grammar', 'Ten autobus jedzie ___ niż tramwaj.', ('szybkie', 'szybciej', 'szybszą'), 1, 'Opisujemy sposób jazdy, więc potrzebny jest stopień wyższy przysłówka: „szybciej”.'),
    MockQuestion('tg37', 'grammar', 'W pokoju stały dwa ___ fotele.', ('wygodne', 'wygodnych', 'wygodnym'), 0, 'Przy liczebniku „dwa” i rzeczowniku „fotele” używamy formy „wygodne”.'),
    MockQuestion('tg38', 'grammar', 'Na spotkanie przyszło pięć ___.', ('osobami', 'osoby', 'osób'), 2, 'Po liczebniku „pięć” potrzebny jest dopełniacz liczby mnogiej: „pięć osób”.'),
    MockQuestion('tg39', 'grammar', 'Które zdanie jest poprawne?', ('Te dwie kobiety był zmęczony.', 'Te dwie kobiety były zmęczone.', 'Te dwie kobiety byli zmęczeni.'), 1, 'Podmiot „dwie kobiety” wymaga niemęskoosobowych form „były zmęczone”.'),
    MockQuestion('tg40', 'grammar', 'Wybierz poprawną odpowiedź: Czy możesz mi pomóc? — Tak, ___ pomogę.', ('chętnie', 'chętny', 'chętna'), 0, 'Przysłówek „chętnie” określa sposób wykonania czynności „pomogę”.'),
)
