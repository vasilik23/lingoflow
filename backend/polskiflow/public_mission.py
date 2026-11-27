"""Guest B1 mini-mission. The learner's free response stays in the browser."""

from django.shortcuts import render

from polskiflow.public_demo_store import load_demo_lesson

COPY = {
    "ru": {
        "title": "Перенести встречу",
        "intro_title": "Польский для жизни в Польше",
        "intro_body": "Попробуй перенести встречу по-польски. Разбери ответ, а затем напиши своё сообщение. Аккаунт не нужен.",
        "situation": "Вы договорились встретиться во вторник, но теперь можете только в среду. Выберите сообщение, которое предлагает новый срок.",
        "retry": "Теперь перенесите встречу с четверга на пятницу.",
        "transfer": "Просмотр квартиры назначен на субботу. Попросите перенести его на понедельник.",
        "rule": "В конструкции przełożyć spotkanie na за предлогом na указываем новый день. Старый день можно назвать после z.",
        "correct": "Верно: так вы предлагаете новый день.",
        "incorrect": "В этом варианте новый день указан неверно.",
        "check": "Проверить ответ",
        "write": "Напишите коллеге: вы не можете встретиться в понедельник и предлагаете среду.",
        "sample": "Сравнить с образцом",
        "revise": "Улучшить свой ответ",
        "checklist": "Проверьте, ясно ли указаны прежний и новый дни. Сформулируйте перенос как вежливую просьбу.",
        "revision_label": "Вторая версия сообщения",
        "listen_title": "Послушайте сообщение перед поездкой",
        "listen_question": "Где договорились встретиться?",
        "listen_check": "Показать ответ и расшифровку",
        "listen_answer": "Перед кассой номер три.",
    },
    "pl": {
        "title": "Przełóż spotkanie",
        "intro_title": "Polski na co dzień w Polsce",
        "intro_body": "Spróbuj przełożyć spotkanie po polsku. Sprawdź odpowiedź, a potem napisz własną wiadomość. Bez rejestracji.",
        "situation": "Spotkanie jest we wtorek, ale możesz dopiero w środę. Wybierz wiadomość, która proponuje nowy termin.",
        "retry": "Teraz przełóż spotkanie z czwartku na piątek.",
        "transfer": "Oglądanie mieszkania jest umówione na sobotę. Poproś o przełożenie go na poniedziałek.",
        "rule": "Po przyimku na podajemy nowy dzień spotkania, a po z możemy podać poprzedni dzień.",
        "correct": "Dobrze: ta wiadomość proponuje nowy dzień.",
        "incorrect": "W tej odpowiedzi nowy dzień jest podany nieprawidłowo.",
        "check": "Sprawdź odpowiedź",
        "write": "Napisz do kolegi: nie możesz spotkać się w poniedziałek i proponujesz środę.",
        "sample": "Porównaj z przykładem",
        "revise": "Popraw swoją odpowiedź",
        "checklist": "Sprawdź, czy jasno podajesz poprzedni i nowy dzień. Sformułuj zmianę terminu jako uprzejmą prośbę.",
        "revision_label": "Druga wersja wiadomości",
        "listen_title": "Posłuchaj wiadomości przed podróżą",
        "listen_question": "Gdzie mają się spotkać?",
        "listen_check": "Pokaż odpowiedź i transkrypcję",
        "listen_answer": "Przed kasą numer trzy.",
    },
    "en": {
        "title": "Reschedule a meeting",
        "intro_title": "Polish for everyday life in Poland",
        "intro_body": "Try rescheduling a meeting in Polish. Check your answer, then write your own message. No account needed.",
        "situation": "You agreed to meet on Tuesday, but now you can only meet on Wednesday. Choose the message proposing the new date.",
        "retry": "Now move a meeting from Thursday to Friday.",
        "transfer": "Your apartment viewing is on Saturday. Ask to move it to Monday.",
        "rule": "In przełożyć spotkanie na, the new day follows na. You can use z to name the original day.",
        "correct": "Correct: this message proposes the new day.",
        "incorrect": "This answer does not give the new day correctly.",
        "check": "Check answer",
        "write": "Write to a colleague: you cannot meet on Monday and propose Wednesday.",
        "sample": "Compare with the example",
        "revise": "Revise your answer",
        "checklist": "Check that the original and new days are clear. Phrase the change as a polite request.",
        "revision_label": "Second version of your message",
        "listen_title": "Listen to a message about a meeting before a trip",
        "listen_question": "Where are they meeting?",
        "listen_check": "Show the answer and transcript",
        "listen_answer": "In front of ticket counter number three.",
    },
}

QUESTIONS = (
    ("Czy możemy przełożyć spotkanie z wtorku na środę?",
     "Czy możemy przełożyć spotkanie ze środy na wtorek?"),
    ("Czy możemy przełożyć spotkanie z piątku na czwartek?",
     "Czy możemy przełożyć spotkanie z czwartku na piątek?"),
    ("Czy możemy przełożyć oglądanie mieszkania z soboty na poniedziałek?",
     "Czy możemy przełożyć oglądanie mieszkania z poniedziałku na sobotę?"),
)
CORRECT_OPTIONS = (0, 1, 0)
LISTENING_TRANSCRIPT = (
    "Pociąg odjeżdża o ósmej piętnaście. Spotkajmy się o ósmej przed kasą numer trzy."
)


def meeting_mission_copy(request):
    return COPY.get(getattr(request, "LANGUAGE_CODE", "ru"), COPY["ru"])


def meeting_mission(request):
    copy = meeting_mission_copy(request)
    step = 0
    feedback = None
    passed = False
    status = 200
    if request.method == "POST":
        steps, answers = request.POST.getlist("step"), request.POST.getlist("answer")
        if steps in (["0"], ["1"], ["2"]) and answers in (["0"], ["1"]):
            attempted = int(steps[0])
            passed = int(answers[0]) == CORRECT_OPTIONS[attempted]
            feedback = copy["correct" if passed else "incorrect"]
            if passed:
                step = 3 if attempted == 2 else 2
            else:
                step = 1
        else:
            status = 400
    return render(request, "public_mission.html", {
        "mission": copy, "step": step, "feedback": feedback,
        "next_lesson": load_demo_lesson("B1") if step == 3 else None,
        "listening_transcript": LISTENING_TRANSCRIPT if step == 3 else None,
        "options": QUESTIONS[step] if step < len(QUESTIONS) else (),
    }, status=status)
