"""Original pilot corrections from EDITOR-001–028; no independent approval."""
import json
from django.db import migrations

PATCH = json.loads(r'''{
  "questions": [
    {
      "lesson_id": "bio-grammar",
      "position": 1,
      "before": {
        "prompt": "W 2020 roku Marta ___ kurs i dostała certyfikat.",
        "options": [
          "ukończyła",
          "kończy",
          "kończyła"
        ],
        "correct": 0,
        "explanation": "Forma ukończyła nazywa zakończoną czynność z wyraźnym rezultatem: Marta otrzymała certyfikat."
      },
      "after": {
        "prompt": "Выбери форму совершенного вида, подчёркивающую завершение курса: W 2020 roku Marta ___ kurs i dostała certyfikat.",
        "options": [
          "ukończyła",
          "kończy",
          "kończyła"
        ],
        "correct": 0,
        "explanation": "Ukończyła подчёркивает завершённый курс и результат. Kończyła описывает процесс завершения: это другая точка зрения, а не ошибка сама по себе."
      }
    },
    {
      "lesson_id": "bio-grammar",
      "position": 2,
      "before": {
        "prompt": "Kiedy ___ studia, przeprowadził się do Gdańska.",
        "options": [
          "ukończy",
          "kończył",
          "ukończył"
        ],
        "correct": 2,
        "explanation": "Одно завершённое событие предшествует другому: ukończył."
      },
      "after": {
        "prompt": "Выбери форму совершенного вида: учёба завершилась до переезда. Kiedy ___ studia, przeprowadził się do Gdańska.",
        "options": [
          "ukończy",
          "kończył",
          "ukończył"
        ],
        "correct": 2,
        "explanation": "Ukończył обозначает завершение учёбы до переезда. Kończył тоже грамматично, но описывает переезд во время завершения учёбы и не выполняет условие задания."
      }
    },
    {
      "lesson_id": "housing-reading-check",
      "position": 4,
      "before": {
        "prompt": "Co Lena zrobi, jeśli naprawa się opóźni?",
        "options": [
          "Wyprowadzi się natychmiast",
          "Ponownie skontaktuje się z administracją",
          "Podpisze nową umowę"
        ],
        "correct": 1,
        "explanation": "Если специалист не придёт вовремя, она снова свяжется с администрацией."
      },
      "after": {
        "prompt": "Co Lena zrobi, jeśli fachowiec się spóźni?",
        "options": [
          "Wyprowadzi się natychmiast",
          "Ponownie skontaktuje się z administracją",
          "Podpisze nową umowę"
        ],
        "correct": 1,
        "explanation": "Если специалист не придёт вовремя, она снова свяжется с администрацией."
      }
    },
    {
      "lesson_id": "housing-quiz",
      "position": 5,
      "before": {
        "prompt": "Rozmawiam z ___.",
        "options": [
          "hydraulikiem",
          "hydraulika",
          "hydraulik"
        ],
        "correct": 0,
        "explanation": "Лицо после z ставится в творительном падеже: z hydraulikiem."
      },
      "after": {
        "prompt": "Rozmawiam z ___.",
        "options": [
          "hydraulikiem",
          "hydraulika",
          "hydraulik"
        ],
        "correct": 0,
        "explanation": "В конструкции rozmawiać z kimś («разговаривать с кем-то») z требует творительного падежа: z hydraulikiem."
      }
    },
    {
      "lesson_id": "bio-quiz",
      "position": 1,
      "before": {
        "prompt": "Po studiach Anna ___ karierę w mediach.",
        "options": [
          "dorastała",
          "wspominała się",
          "rozpoczęła"
        ],
        "correct": 2,
        "explanation": "Rozpocząć karierę — начать профессиональный путь."
      },
      "after": {
        "prompt": "Выбери глагол со значением «начала»: Po studiach Anna ___ karierę w mediach.",
        "options": [
          "zakończyła",
          "przerwała",
          "rozpoczęła"
        ],
        "correct": 2,
        "explanation": "Rozpocząć karierę — начать профессиональный путь."
      }
    },
    {
      "lesson_id": "bio-quiz",
      "position": 3,
      "before": {
        "prompt": "Pracował nad projektem rok i wreszcie ___ cel.",
        "options": [
          "osiągał się",
          "dorósł na",
          "osiągnął"
        ],
        "correct": 2,
        "explanation": "Wyrażenie osiągnął cel oznacza uzyskanie zamierzonego rezultatu po roku pracy nad projektem."
      },
      "after": {
        "prompt": "Выбери завершённый результат «достиг цели»: Po roku pracy wreszcie ___.",
        "options": [
          "zbliżył się do celu",
          "pracował nad celem",
          "osiągnął cel"
        ],
        "correct": 2,
        "explanation": "Osiągnął cel означает достигнутый результат. Zbliżył się do celu — приблизился, pracował nad celem — работал над целью; они не обозначают её достижения."
      }
    },
    {
      "lesson_id": "bio-quiz",
      "position": 6,
      "before": {
        "prompt": "___ było trudno, lecz z czasem wszystko się zmieniło.",
        "options": [
          "Osiągnięcie",
          "Początkowo",
          "Na końcu wczoraj"
        ],
        "correct": 1,
        "explanation": "Słowo początkowo wprowadza pierwszy etap historii i zapowiada późniejszą zmianę sytuacji."
      },
      "after": {
        "prompt": "Выбери слово, которое вводит начальный этап истории: ___ było trudno, lecz z czasem wszystko się zmieniło.",
        "options": [
          "Ostatecznie",
          "Początkowo",
          "Następnie"
        ],
        "correct": 1,
        "explanation": "Słowo początkowo wprowadza pierwszy etap historii i zapowiada późniejszą zmianę sytuacji."
      }
    },
    {
      "lesson_id": "bio-quiz",
      "position": 8,
      "before": {
        "prompt": "Что лучше связывает биографический рассказ?",
        "options": [
          "wczoraj, jutro, teraz, nigdy",
          "najpierw, następnie, z czasem, w końcu",
          "bo, albo, czy, lecz że"
        ],
        "correct": 1,
        "explanation": "Markery najpierw, następnie, z czasem i w końcu porządkują kolejne etapy biografii."
      },
      "after": {
        "prompt": "Какая последовательность обозначает начало, следующий этап, постепенное изменение и завершение?",
        "options": [
          "wczoraj, dziś, jutro, pojutrze",
          "najpierw, następnie, z czasem, w końcu",
          "dlatego, ponieważ, jednak, chociaż"
        ],
        "correct": 1,
        "explanation": "Markery najpierw, następnie, z czasem i w końcu porządkują kolejne etapy biografii."
      }
    },
    {
      "lesson_id": "housing-grammar",
      "position": 5,
      "before": null,
      "after": {
        "prompt": "Выбери вежливую просьбу помочь с ремонтом отопления.",
        "options": [
          "Proszę o pomoc w naprawie ogrzewania.",
          "Dziękuję za naprawę ogrzewania.",
          "Potwierdzam termin naprawy ogrzewania."
        ],
        "correct": 0,
        "explanation": "Proszę o pomoc w naprawie ogrzewania — просьба помочь с ремонтом. Dziękuję — благодарность, Potwierdzam — подтверждение."
      }
    },
    {
      "lesson_id": "housing-grammar",
      "position": 6,
      "before": null,
      "after": {
        "prompt": "Предложи визит во вторник после 16:00 и спроси владелицу, подходит ли время.",
        "options": [
          "Czy fachowiec może przyjść w środę po szesnastej? Czy ten termin Pani odpowiada?",
          "Czy fachowiec może przyjść we wtorek przed szesnastą? Czy ten termin Pani odpowiada?",
          "Czy fachowiec może przyjść we wtorek po szesnastej? Czy ten termin Pani odpowiada?"
        ],
        "correct": 2,
        "explanation": "We wtorek — во вторник; po szesnastej — после 16:00. Pani odpowiada — вежливое обращение к владелице; владельцу пишем Panu odpowiada."
      }
    }
  ],
  "lessons": [
    {
      "id": "housing-grammar",
      "before": {
        "theory_sections": [
          [
            "Родительный после отрицания",
            "После nie ma: nie ma prądu, ciepłej wody, ogrzewania."
          ],
          [
            "Глагольное управление",
            "Szukać и potrzebować требуют родительного: szukam mieszkania, potrzebuję hydraulika."
          ],
          [
            "Творительный после z",
            "Когда z означает «с»: problem z ogrzewaniem, rozmowa z właścicielem."
          ]
        ]
      },
      "after": {
        "theory_sections": [
          [
            "Родительный после отрицания",
            "После nie ma: nie ma prądu, ciepłej wody, ogrzewania."
          ],
          [
            "Глагольное управление",
            "Szukać и potrzebować требуют родительного: szukam mieszkania, potrzebuję hydraulika."
          ],
          [
            "Творительный после z",
            "Когда z означает «с»: problem z ogrzewaniem, rozmowa z właścicielem."
          ],
          [
            "Вежливая просьба и время визита",
            "Proszę o pomoc w naprawie ogrzewania. Czy fachowiec może przyjść we wtorek po szesnastej? Czy ten termin Panu odpowiada? / Czy ten termin Pani odpowiada? Panu — владельцу, Pani — владелице."
          ]
        ],
        "subtitle": "7 заданий · A2"
      }
    },
    {
      "id": "a1read-kurs-check",
      "before": {
        "description": "Проверь понимание прочитанного текста"
      },
      "after": {
        "description": "Проверь понимание прочитанного текста"
      }
    },
    {
      "id": "grammar",
      "before": {
        "theory_sections": [
          [
            "Формы настоящего времени",
            "ja jestem · ty jesteś · on/ona/ono jest · my jesteśmy · wy jesteście · oni/one są"
          ],
          [
            "Представляемся",
            "Jestem Anna. — Я Анна. Jestem z Polski. — Я из Польши."
          ],
          [
            "Вежливое обращение",
            "С pan и pani используется третье лицо: Czy pan jest z Polski? Czy pani jest nauczycielką?"
          ]
        ]
      },
      "after": {
        "theory_sections": [
          [
            "Формы настоящего времени",
            "ja jestem · ty jesteś · on/ona/ono jest · my jesteśmy · wy jesteście · oni/one są"
          ],
          [
            "Представляемся",
            "Jestem Anna. — Я Анна. Jestem z Polski. — Я из Польши."
          ],
          [
            "Вежливое обращение",
            "С pan и pani используется третье лицо: Czy pan jest z Polski? Czy pani jest nauczycielką?"
          ],
          [
            "Перед чтением: слова о классе",
            "Сначала повтори базовые слова о классе: sala — аудитория; nauczyciel — преподаватель; obok — рядом; na początku — в начале; przedstawiać się — представляться; znajomy — знакомый. В тексте był означает «был»."
          ]
        ]
      }
    }
  ],
  "readings": [
    {
      "id": "bio-droga-joanny",
      "before": {
        "glossary": {
          "maturze": {
            "lemma": "matura",
            "translation": "выпускной экзамен",
            "part_of_speech": "существительное"
          },
          "punktem": {
            "lemma": "punkt zwrotny",
            "translation": "поворотный момент",
            "part_of_speech": "словосочетание"
          },
          "rozwoju": {
            "lemma": "rozwój",
            "translation": "развитие",
            "part_of_speech": "существительное"
          },
          "prowadzi": {
            "lemma": "prowadzić",
            "translation": "вести; руководить",
            "part_of_speech": "глагол"
          },
          "zdobyła": {
            "lemma": "zdobyć",
            "translation": "приобрести",
            "part_of_speech": "глагол"
          },
          "dorastała": {
            "lemma": "dorastać",
            "translation": "взрослеть",
            "part_of_speech": "глагол"
          },
          "niewielkim": {
            "lemma": "niewielki",
            "translation": "небольшой",
            "part_of_speech": "прилагательное"
          },
          "wpłynąć": {
            "lemma": "wpłynąć na",
            "translation": "повлиять на",
            "part_of_speech": "глагол"
          },
          "ukończeniu": {
            "lemma": "ukończenie",
            "translation": "окончание",
            "part_of_speech": "существительное"
          },
          "mieszkańcami": {
            "lemma": "mieszkaniec",
            "translation": "житель",
            "part_of_speech": "существительное"
          },
          "przyzwyczaić": {
            "lemma": "przyzwyczaić się",
            "translation": "привыкнуть",
            "part_of_speech": "глагол"
          },
          "przestrzeniami": {
            "lemma": "przestrzeń",
            "translation": "пространство",
            "part_of_speech": "существительное"
          }
        }
      },
      "after": {
        "glossary": {
          "maturze": {
            "lemma": "matura",
            "translation": "выпускной экзамен",
            "part_of_speech": "существительное"
          },
          "rozwoju": {
            "lemma": "rozwój",
            "translation": "развитие",
            "part_of_speech": "существительное"
          },
          "prowadzi": {
            "lemma": "prowadzić",
            "translation": "вести; руководить",
            "part_of_speech": "глагол"
          },
          "zdobyła": {
            "lemma": "zdobyć",
            "translation": "приобрести",
            "part_of_speech": "глагол"
          },
          "dorastała": {
            "lemma": "dorastać",
            "translation": "взрослеть",
            "part_of_speech": "глагол"
          },
          "niewielkim": {
            "lemma": "niewielki",
            "translation": "небольшой",
            "part_of_speech": "прилагательное"
          },
          "ukończeniu": {
            "lemma": "ukończenie",
            "translation": "окончание",
            "part_of_speech": "существительное"
          },
          "mieszkańcami": {
            "lemma": "mieszkaniec",
            "translation": "житель",
            "part_of_speech": "существительное"
          },
          "przestrzeniami": {
            "lemma": "przestrzeń",
            "translation": "пространство",
            "part_of_speech": "существительное"
          },
          "punktem zwrotnym": {
            "lemma": "punkt zwrotny",
            "translation": "поворотный момент",
            "part_of_speech": "словосочетание"
          },
          "przyzwyczaić się": {
            "lemma": "przyzwyczaić się",
            "translation": "привыкнуть",
            "part_of_speech": "глагол"
          },
          "wpłynąć na": {
            "lemma": "wpłynąć na",
            "translation": "повлиять на",
            "part_of_speech": "глагол"
          }
        }
      }
    },
    {
      "id": "usterka-w-mieszkaniu",
      "before": {
        "paragraphs": [
          "Lena wynajmuje małe mieszkanie w Poznaniu. W poniedziałek rano zauważyła, że ogrzewanie nie działa, a w sypialni jest bardzo zimno. Najpierw zadzwoniła do właściciela. Powiedziała, że od wieczora nie ma ciepłych kaloryferów i potrzebuje szybkiej pomocy.",
          "Właściciel poprosił Lenę o krótką wiadomość z opisem usterki i zdjęciem licznika. Potem zgłosił problem administracji. Po godzinie administracja odpowiedziała, że fachowiec może przyjść we wtorek między szesnastą a osiemnastą. Lena potwierdziła termin i zapytała, czy naprawa będzie płatna.",
          "Zgodnie z umową właściciel zapłaci za naprawę ogrzewania. Lena będzie rozmawiać z fachowcem i pokaże mu kaloryfer w sypialni. Jeśli fachowiec się spóźni, ponownie skontaktuje się z administracją. Lena ma nadzieję, że wieczorem mieszkanie znów będzie ciepłe."
        ],
        "glossary": {
          "płatna": {
            "lemma": "płatny",
            "translation": "платный",
            "part_of_speech": "прилагательное"
          },
          "usterki": {
            "lemma": "usterka",
            "translation": "неисправность",
            "part_of_speech": "существительное"
          },
          "zgodnie": {
            "lemma": "zgodnie z",
            "translation": "согласно",
            "part_of_speech": "выражение"
          },
          "licznika": {
            "lemma": "licznik",
            "translation": "счётчик",
            "part_of_speech": "существительное"
          },
          "ponownie": {
            "lemma": "ponownie",
            "translation": "повторно",
            "part_of_speech": "наречие"
          },
          "spóźni": {
            "lemma": "spóźnić się",
            "translation": "опоздать",
            "part_of_speech": "глагол"
          },
          "fachowiec": {
            "lemma": "fachowiec",
            "translation": "специалист",
            "part_of_speech": "существительное"
          },
          "wynajmuje": {
            "lemma": "wynajmować",
            "translation": "снимать",
            "part_of_speech": "глагол"
          },
          "ogrzewanie": {
            "lemma": "ogrzewanie",
            "translation": "отопление",
            "part_of_speech": "существительное"
          },
          "zauważyła": {
            "lemma": "zauważyć",
            "translation": "заметить",
            "part_of_speech": "глагол"
          },
          "kaloryferów": {
            "lemma": "kaloryfer",
            "translation": "радиатор",
            "part_of_speech": "существительное"
          },
          "potwierdziła": {
            "lemma": "potwierdzić",
            "translation": "подтвердить",
            "part_of_speech": "глагол"
          }
        }
      },
      "after": {
        "paragraphs": [
          "Lena wynajmuje małe mieszkanie w Poznaniu. W poniedziałek rano zauważyła, że ogrzewanie nie działa, a w sypialni jest bardzo zimno. Najpierw zadzwoniła do właściciela. Powiedziała, że kaloryfery są zimne i potrzebuje szybkiej pomocy.",
          "Właściciel poprosił Lenę o krótką wiadomość z opisem usterki i zdjęciem licznika. Potem zgłosił problem administracji. Po godzinie administracja odpowiedziała, że fachowiec może przyjść we wtorek między szesnastą a osiemnastą. Lena potwierdziła termin i zapytała, czy naprawa będzie płatna.",
          "Zgodnie z umową właściciel zapłaci za naprawę ogrzewania. Lena będzie rozmawiać z fachowcem i pokaże mu kaloryfer w sypialni. Jeśli fachowiec się spóźni, ponownie skontaktuje się z administracją. Lena ma nadzieję, że wieczorem mieszkanie znów będzie ciepłe."
        ],
        "glossary": {
          "płatna": {
            "lemma": "płatny",
            "translation": "платный",
            "part_of_speech": "прилагательное"
          },
          "usterki": {
            "lemma": "usterka",
            "translation": "неисправность",
            "part_of_speech": "существительное"
          },
          "zgodnie": {
            "lemma": "zgodnie z",
            "translation": "согласно",
            "part_of_speech": "выражение"
          },
          "licznika": {
            "lemma": "licznik",
            "translation": "счётчик",
            "part_of_speech": "существительное"
          },
          "ponownie": {
            "lemma": "ponownie",
            "translation": "повторно",
            "part_of_speech": "наречие"
          },
          "spóźni": {
            "lemma": "spóźnić się",
            "translation": "опоздать",
            "part_of_speech": "глагол"
          },
          "fachowiec": {
            "lemma": "fachowiec",
            "translation": "специалист",
            "part_of_speech": "существительное"
          },
          "wynajmuje": {
            "lemma": "wynajmować",
            "translation": "снимать",
            "part_of_speech": "глагол"
          },
          "ogrzewanie": {
            "lemma": "ogrzewanie",
            "translation": "отопление",
            "part_of_speech": "существительное"
          },
          "zauważyła": {
            "lemma": "zauważyć",
            "translation": "заметить",
            "part_of_speech": "глагол"
          },
          "potwierdziła": {
            "lemma": "potwierdzić",
            "translation": "подтвердить",
            "part_of_speech": "глагол"
          },
          "kaloryfery": {
            "lemma": "kaloryfer",
            "translation": "радиатор",
            "part_of_speech": "существительное"
          }
        }
      }
    },
    {
      "id": "pierwszy-dzien-na-kursie",
      "before": {
        "glossary": {
          "nowy": "новый",
          "obok": "рядом",
          "pyta": "спрашивает",
          "sali": "аудитории",
          "mówi": {
            "lemma": "mówić",
            "translation": "говорить",
            "part_of_speech": "глагол"
          },
          "potem": "потом",
          "dzień": "день",
          "każdy": "каждый",
          "kolega": "знакомый / одногруппник",
          "kursie": "курсе",
          "lekcji": "урока",
          "siedzi": "сидит",
          "krótko": "кратко",
          "mieszka": {
            "lemma": "mieszkać",
            "translation": "жить",
            "part_of_speech": "глагол"
          },
          "wchodzi": "входит",
          "pierwszy": "первый",
          "pochodzi": {
            "lemma": "pochodzić",
            "translation": "быть родом",
            "part_of_speech": "глагол"
          },
          "znajomym": "знакомым",
          "odpowiada": "отвечает",
          "początek": "начало",
          "początku": "начале",
          "uśmiecha": "улыбается",
          "zapraszam": "прошу / проходите",
          "nauczyciel": "преподаватель",
          "przedstawia": {
            "lemma": "przedstawiać",
            "translation": "представляться",
            "part_of_speech": "глагол"
          }
        }
      },
      "after": {
        "glossary": {
          "nowy": "новый",
          "obok": "рядом",
          "pyta": {
            "lemma": "pytać",
            "translation": "спрашивает"
          },
          "sali": {
            "lemma": "sala",
            "translation": "аудитории"
          },
          "mówi": {
            "lemma": "mówić",
            "translation": "говорить",
            "part_of_speech": "глагол"
          },
          "potem": "потом",
          "dzień": "день",
          "każdy": "каждый",
          "kolega": "знакомый / одногруппник",
          "kursie": {
            "lemma": "kurs",
            "translation": "курсе"
          },
          "lekcji": {
            "lemma": "lekcja",
            "translation": "урока"
          },
          "siedzi": {
            "lemma": "siedzieć",
            "translation": "сидит"
          },
          "krótko": "кратко",
          "wchodzi": {
            "lemma": "wchodzić",
            "translation": "входит"
          },
          "pierwszy": "первый",
          "pochodzi": {
            "lemma": "pochodzić",
            "translation": "быть родом",
            "part_of_speech": "глагол"
          },
          "znajomym": {
            "lemma": "znajomy",
            "translation": "знакомым"
          },
          "odpowiada": {
            "lemma": "odpowiadać",
            "translation": "отвечает"
          },
          "początek": "начало",
          "początku": {
            "lemma": "początek",
            "translation": "начале"
          },
          "uśmiecha": {
            "lemma": "uśmiechać się",
            "translation": "улыбается"
          },
          "zapraszam": "прошу / проходите",
          "nauczyciel": "преподаватель",
          "przedstawia": {
            "lemma": "przedstawiać się",
            "translation": "представляться",
            "part_of_speech": "глагол"
          }
        }
      }
    }
  ]
}''')

def seed(apps, schema_editor):
    if schema_editor.connection.vendor != 'sqlite':
        return
    Question = apps.get_model('learning', 'Question')
    Lesson = apps.get_model('learning', 'Lesson')
    Reading = apps.get_model('learning', 'ReadingText')
    for row in PATCH['questions']:
        Question.objects.update_or_create(lesson_id=row['lesson_id'], position=row['position'], defaults={**row['after'], 'is_active': True})
    for row in PATCH['lessons']:
        Lesson.objects.filter(pk=row['id']).update(**row['after'])
    for row in PATCH['readings']:
        Reading.objects.filter(pk=row['id']).update(**row['after'])

class Migration(migrations.Migration):
    dependencies = [('learning', '0125_b2_listening_attempts')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
