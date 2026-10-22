"""Editorial pilots reuse published lessons; no new assessment or progress writes."""
from copy import deepcopy

SOURCE_METADATA = {'origin': 'original', 'created_for': 'LingoFlow', 'verified_at': '2026-10-21',
                   'verification': 'internal link/content review; independent Polish review pending'}

PILOTS = {
    'introductions': {
        'level': 'A1', 'reading_id': 'pierwszy-dzien-na-kursie',
        'lessons': ('words', 'grammar', 'review', 'a1read-kurs-check', 'quiz'),
        'ru': {'goal': 'Смогу представиться и задать два вопроса новому знакомому.',
               'scenario': 'Первый день на курсе польского: познакомься с человеком рядом.',
               'prompt': 'Напиши 3–4 предложения: представься, скажи, откуда ты, и задай два вопроса собеседнику.',
               'checks': ('Я представился.', 'Я сказал, откуда я.', 'Я задал два вопроса.' )},
        'pl': {'goal': 'Przedstawię się i zadam dwa pytania nowo poznanej osobie.',
               'scenario': 'Pierwszy dzień na kursie polskiego: poznaj osobę obok.',
               'prompt': 'Napisz 3–4 zdania: przedstaw się, powiedz, skąd jesteś, i zadaj rozmówcy dwa pytania.',
               'checks': ('Podaję swoje imię.', 'Mówię, skąd jestem.', 'Zadaję dwa pytania.')},
        'en': {'goal': 'I can introduce myself and ask a new acquaintance two questions.',
               'scenario': 'Your first day on a Polish course: get to know the person next to you.',
               'prompt': 'Write 3–4 sentences: introduce yourself, say where you are from and ask the other person two questions.',
               'checks': ('I introduced myself.', 'I said where I am from.', 'I asked two questions.')},
        'sample': 'Cześć! Mam na imię Alex i jestem z Ukrainy. Jak masz na imię? Skąd jesteś?',
    },
    'housing-services': {
        'level': 'A2', 'reading_id': 'usterka-w-mieszkaniu',
        'lessons': ('housing-words', 'housing-grammar', 'housing-review', 'housing-reading-check', 'housing-quiz'),
        'ru': {'goal': 'Смогу описать неисправность в квартире и предложить время ремонта.',
               'scenario': 'В съёмной квартире не работает отопление. Напиши владельцу.',
               'prompt': 'Напиши короткое сообщение: опиши проблему, попроси о помощи и предложи время визита мастера.',
               'checks': ('Проблема описана конкретно.', 'Я вежливо попросил о помощи.', 'Я предложил время визита.')},
        'pl': {'goal': 'Opiszę usterkę w mieszkaniu i zaproponuję termin naprawy.',
               'scenario': 'W wynajmowanym mieszkaniu nie działa ogrzewanie. Napisz do właściciela.',
               'prompt': 'Napisz krótką wiadomość: opisz problem, poproś o pomoc i zaproponuj termin wizyty fachowca.',
               'checks': ('Problem jest opisany konkretnie.', 'Uprzejmie proszę o pomoc.', 'Proponuję termin wizyty.')},
        'en': {'goal': 'I can describe a problem in my flat and suggest a repair time.',
               'scenario': 'The heating in your rented flat is not working. Write to the landlord.',
               'prompt': 'Write a short message: describe the problem, ask for help and suggest a time for the repair visit.',
               'checks': ('I described the specific problem.', 'I politely asked for help.', 'I suggested a visit time.')},
        'sample': 'Dzień dobry, w mieszkaniu nie działa ogrzewanie. Proszę o pomoc w naprawie ogrzewania. Czy fachowiec może przyjść we wtorek po szesnastej? Czy ten termin Panu odpowiada?',
    },
    'b1-biography': {
        'level': 'B1', 'reading_id': 'bio-droga-joanny',
        'lessons': ('bio-words', 'bio-grammar', 'bio-review', 'bio-reading-check', 'bio-quiz'),
        'ru': {'goal': 'Смогу рассказать о важном решении, его причине и результате.',
               'scenario': 'Новый знакомый спрашивает, почему ты начал изучать польский.',
               'prompt': 'Напиши связный ответ из 5–7 предложений: что ты делал раньше, какое решение принял, почему и что изменилось.',
               'checks': ('Есть фон и конкретное решение.', 'Я объяснил причину.', 'Я описал результат и связал события.')},
        'pl': {'goal': 'Opowiem o ważnej decyzji, jej przyczynie i rezultacie.',
               'scenario': 'Nowy znajomy pyta, dlaczego zacząłeś uczyć się polskiego.',
               'prompt': 'Napisz spójną odpowiedź w 5–7 zdaniach: co robiłeś wcześniej, jaką decyzję podjąłeś, dlaczego i co się zmieniło.',
               'checks': ('Jest tło i konkretna decyzja.', 'Wyjaśniam przyczynę.', 'Opisuję rezultat i łączę wydarzenia.')},
        'en': {'goal': 'I can explain an important decision, its reason and its outcome.',
               'scenario': 'A new acquaintance asks why you started learning Polish.',
               'prompt': 'Write a connected answer of 5–7 sentences: what you used to do, the decision you made, why and what changed.',
               'checks': ('I gave the background and a specific decision.', 'I explained the reason.', 'I described the result and connected the events.')},
        'sample': 'Przez kilka lat pracowałem w międzynarodowej firmie. Na spotkaniach mówiłem głównie po angielsku. Rok temu przeprowadziłem się do Polski i postanowiłem nauczyć się polskiego. Chciałem samodzielnie załatwiać codzienne sprawy i lepiej poznać sąsiadów. Zapisałem się na kurs i zacząłem regularnie ćwiczyć. Teraz rozumiem więcej rozmów i czuję się pewniej.',
    },
}

PILOT_LESSON_IDS = frozenset(lesson_id for pilot in PILOTS.values() for lesson_id in pilot['lessons'])


def journey(topic_id, language='ru'):
    pilot = PILOTS.get(topic_id)
    if not pilot:
        return None
    language = language.split('-')[0]
    return {'topic_id': topic_id, **{k: deepcopy(v) for k, v in pilot.items() if k not in {'ru', 'pl', 'en'}},
            **deepcopy(pilot.get(language, pilot['ru']))}


def next_target(topic_id, lesson_id):
    pilot = PILOTS.get(topic_id)
    if not pilot:
        return None
    words, grammar, review, reading_check, quiz = pilot['lessons']
    if lesson_id == review:
        return {'href': f"/reading/{pilot['reading_id']}/", 'kind': 'reading'}
    if lesson_id == reading_check:
        return {'href': f'/lesson/{quiz}/', 'kind': 'practice'}
    if lesson_id == quiz:
        return {'href': f'/course/topic/{topic_id}/#own-answer', 'kind': 'answer'}
    return None
