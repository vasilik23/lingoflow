"""Translations for the exam entry, review and aggregate-only writing history."""
import json
from pathlib import Path

from django.conf import settings
from django.template import Context, Template
from django.template.loader import render_to_string
from django.test import SimpleTestCase
from django.utils.translation import override


MESSAGES = [
    [
        "Один комплект, два текста, 75 минут. Отдельная попытка письма.",
        "Jeden zestaw, dwa teksty, 75 minut. Osobna próba pisania.",
        "One set, two texts, 75 minutes. A separate writing attempt."
    ],
    [
        "Сравни ответы и прочитай объяснения.",
        "Porównaj odpowiedzi i przeczytaj wyjaśnienia.",
        "Compare your answers and read the explanations."
    ],
    [
        "Теория открывается в новой вкладке, прогон остаётся здесь.",
        "Teoria otwiera się w nowej karcie; próba pozostaje tutaj.",
        "Theory opens in a new tab; your practice run stays here."
    ],
    [
        "Показать ответы",
        "Pokaż odpowiedzi",
        "Show answers"
    ],
    [
        "Все",
        "Wszystkie",
        "All"
    ],
    [
        "Ошибки",
        "Błędy",
        "Mistakes"
    ],
    [
        "Пропуски",
        "Brak odpowiedzi",
        "Unanswered"
    ],
    [
        "В этой категории нет ответов.",
        "W tej kategorii nie ma odpowiedzi.",
        "There are no answers in this category."
    ],
    [
        "Вернуться к тексту",
        "Wróć do tekstu",
        "Return to the text"
    ],
    [
        "Прочитать расшифровку",
        "Przeczytaj transkrypcję",
        "Read the transcript"
    ],
    [
        "Тексты и таймер хранятся в этом браузере. В аккаунт отправляется только сводка завершённой попытки, без текстов.",
        "Teksty i dane minutnika są przechowywane w tej przeglądarce. Na konto wysyłane jest tylko podsumowanie zakończonej próby, bez tekstów.",
        "Texts and timer data are stored in this browser. Only a summary of the completed attempt is sent to your account, without the texts."
    ],
    [
        "Эта старая попытка доступна только в браузере; сводка в аккаунт не отправляется.",
        "Ta starsza próba jest dostępna tylko w przeglądarce; podsumowanie nie jest wysyłane na konto.",
        "This older attempt is available only in the browser; its summary is not sent to your account."
    ],
    [
        "Сводка попытки сохранена в аккаунте. Тексты не отправлялись.",
        "Podsumowanie próby zostało zapisane na koncie. Teksty nie zostały wysłane.",
        "The attempt summary is saved in your account. The texts were not sent."
    ],
    [
        "Сохраняем сводку попытки в аккаунт…",
        "Zapisywanie podsumowania próby na koncie…",
        "Saving the attempt summary to your account…"
    ],
    [
        "Сводка пока не сохранена в аккаунте. Проверь соединение и повтори отправку; тексты остаются в браузере.",
        "Podsumowanie nie zostało jeszcze zapisane na koncie. Sprawdź połączenie i wyślij je ponownie; teksty pozostają w przeglądarce.",
        "The summary is not saved in your account yet. Check your connection and try sending it again; the texts remain in the browser."
    ],
    [
        "Повторить сохранение сводки",
        "Ponów zapis podsumowania",
        "Retry saving the summary"
    ],
    [
        "История экзаменационного письма B1",
        "Historia prób pisania egzaminacyjnego B1",
        "B1 exam writing history"
    ],
    [
        "Последние 12 письменных попыток за выбранный период. Данные таймера и число слов переданы браузером; это не экзаменационная оценка. Тексты не сохраняются в аккаунте.",
        "Ostatnie 12 prób pisania z wybranego okresu. Dane minutnika i liczba słów pochodzą z przeglądarki; nie jest to ocena egzaminacyjna. Teksty nie są zapisywane na koncie.",
        "The latest 12 writing attempts in the selected period. Timer data and word counts are reported by the browser; they are not an exam grade. Texts are not saved in your account."
    ],
    [
        "История письма временно недоступна.",
        "Historia pisania jest chwilowo niedostępna.",
        "Writing history is temporarily unavailable."
    ],
    [
        "Завершено до истечения времени",
        "Zakończono przed upływem czasu",
        "Finished before time ran out"
    ],
    [
        "Без автоматического балла",
        "Bez automatycznej oceny punktowej",
        "No automated score"
    ],
    [
        "Открыть комплект",
        "Otwórz zestaw",
        "Open the set"
    ],
    [
        "В этом периоде ещё нет сохранённых письменных попыток.",
        "W tym okresie nie ma jeszcze zapisanych prób pisania.",
        "There are no saved writing attempts in this period yet."
    ],
    [
        "Отдельное экзаменационное письмо B1 сохраняет в аккаунте дату, комплект, число слов и данные таймера. Тексты остаются в браузере; история не содержит экзаменационного балла. Эти итоги входят в экспорт и удаляются вместе с аккаунтом.",
        "Osobny tryb pisania egzaminacyjnego B1 zapisuje na koncie datę, zestaw, liczbę słów i dane minutnika. Teksty pozostają w przeglądarce; historia nie zawiera oceny egzaminacyjnej. Te wyniki są uwzględniane w eksporcie i usuwane wraz z kontem.",
        "The separate B1 exam writing mode saves the date, set, word counts and timer data in your account. Texts remain in the browser; the history does not contain an exam score. These summaries are included in your export and deleted with your account."
    ]
]


class ExamPathLocalizationTests(SimpleTestCase):
    def test_actual_writing_history_distinguishes_saved_empty_and_unavailable(self):
        attempt = {'date_display': '18.10.2026 10:00', 'set_id': '1',
                   'words_a': 35, 'words_b': 160, 'unanswered': 0, 'timed_out': False}
        for language, index in (('ru', 0), ('pl', 1), ('en', 2)):
            expected = {row[0]: row[index] for row in MESSAGES}
            for attempts, label in (([attempt], 'Без автоматического балла'),
                                    ([], 'В этом периоде ещё нет сохранённых письменных попыток.'),
                                    (None, 'История письма временно недоступна.')):
                with self.subTest(language=language, label=label), override(language):
                    html = render_to_string('partials/b1_writing_history.html', {
                        'b1_writings': attempts,
                    })
                    self.assertIn(expected['История экзаменационного письма B1'], html)
                    self.assertIn(expected[label], html)
                    if attempts:
                        self.assertIn(expected['Открыть комплект'], html)
                        self.assertIn('35', html)
                        self.assertIn('160', html)

    def test_messages_are_localized_in_server_templates_and_browser_catalogues(self):
        template = Template('{% load i18n %}{% translate source %}')
        for language, index in (('pl', 1), ('en', 2)):
            path = (Path(settings.BASE_DIR) /
                    f'polskiflow/learning/static/polskiflow/i18n-{language}.js')
            catalogue = json.loads(path.read_text().split(' = ', 1)[1].removesuffix(';\n'))
            with override(language):
                for row in MESSAGES:
                    with self.subTest(language=language, source=row[0]):
                        self.assertEqual(template.render(Context({'source': row[0]})), row[index])
                        self.assertEqual(catalogue[row[0]], row[index])

    def test_actual_review_controls_and_source_links_render_in_all_three_languages(self):
        detail = {'unanswered': True, 'is_correct': False, 'correct_text': 'tak',
                  'question': {'prompt': 'Pytanie', 'explanation': 'Wyjaśnienie'},
                  'source_anchor': 'source-fixture'}
        for language in ('ru', 'pl', 'en'):
            index = {'ru': 0, 'pl': 1, 'en': 2}[language]
            expected = {row[0]: row[index] for row in MESSAGES}
            for part, label in (('reading', 'Вернуться к тексту'),
                                ('listening', 'Прочитать расшифровку')):
                with self.subTest(language=language, part=part), override(language):
                    html = render_to_string('partials/b1_run_review.html', {'review': {
                        'id': part, 'title': 'Fixture', 'status': 'scored',
                        'details': [detail], 'sources': [],
                    }})
                    for source in ('Показать ответы', 'Все', 'Ошибки', 'Пропуски',
                                   'В этой категории нет ответов.', label):
                        self.assertIn(expected[source], html)
                    self.assertIn('href="#source-fixture"', html)
                    self.assertNotIn('b1media-grammar', html)
