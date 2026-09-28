"""Browser views for the transitional Django authentication flow."""

from dataclasses import replace
from datetime import datetime
from functools import wraps
from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from polskiflow.auth import (
    SupabaseAuthError,
    clear_auth_cookies,
    set_auth_cookies,
    sign_in,
    sign_out,
    sign_up,
    request_password_reset,
    resend_signup_confirmation,
    update_password,
)
from polskiflow.content import course_topics, tasks
from polskiflow.dictionary_store import load_personal_words
from polskiflow.lesson_draft_store import load_latest_lesson_draft
from polskiflow.lesson_bookmark_store import load_lesson_bookmarks
from polskiflow.domain.achievements import build_achievements
from polskiflow.domain.auth_rate_limit import consume_auth_attempt
from polskiflow.domain.b1_exam_prep import build_b1_exam_prep
from polskiflow.domain.daily_plan import build_daily_plan
from polskiflow.domain.daily_goal_insights import build_daily_goal_insight
from polskiflow.domain.password_policy import password_error
from polskiflow.domain.course_catalog import (
    COMPLETION_FILTERS,
    DURATION_FILTERS,
    LESSON_KINDS,
    filter_course_topics,
)
from polskiflow.progress_store import load_dashboard_progress, save_profile_settings
from polskiflow.privacy_export_store import load_privacy_export
from polskiflow.reading_bookmark_store import load_reading_bookmarks
from polskiflow.reminder_preference_store import load_reminder_preferences, save_reminder_preferences


PROFILE_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
WRITING_PROMPTS = {
    "B1": (
    {
        "id": "formal-request",
        "title": "Официальная просьба",
        "task": "Напиши 80–100 слов администратору курса: объясни, почему пропустишь занятие, попроси материалы и предложи новый срок сдачи задания.",
        "hint": "Начни с «Szanowna Pani / Szanowny Panie», раздели причины и просьбы на абзацы.",
        "min_words": 80, "min_paragraphs": 2, "markers": ("proszę", "termin"),
        "checklist": (
            "Я указал причину отсутствия, просьбу о материалах и новый срок.",
            "Обращение, просьба и завершение выдержаны в официальном регистре.",
            "Причина и просьбы разделены на понятные абзацы.",
            "Я проверил вежливые конструкции, окончания и формы будущего времени.",
        ),
    },
    {
        "id": "recommendation",
        "title": "Рекомендация места",
        "task": "Посоветуй другу польский город или место для выходных в 90–120 словах. Приведи минимум два аргумента и одно практическое предостережение.",
        "hint": "Используй связки «po pierwsze», «poza tym», «jednak» и заверши ясной рекомендацией.",
        "min_words": 90, "min_paragraphs": 2, "markers": ("po pierwsze", "polecam"),
        "checklist": (
            "Я назвал место, привёл два разных аргумента и одно предостережение.",
            "Каждый аргумент объясняет, почему место подходит другу.",
            "Связки помогают перейти от преимуществ к ограничению и рекомендации.",
            "Я проверил формы прилагательных, местный падеж и понятность совета.",
        ),
    },
    {
        "id": "opinion",
        "title": "Личное мнение",
        "task": "Ответь в 100–120 словах: лучше учиться самостоятельно или на курсах? Обозначь позицию, аргумент, контраргумент и вывод.",
        "hint": "Полезные рамки: «moim zdaniem», «z jednej strony», «z drugiej strony», «dlatego uważam, że…».",
        "min_words": 100, "min_paragraphs": 2, "markers": ("moim zdaniem", "z drugiej strony"),
        "checklist": (
            "Моя позиция сформулирована ясно и поддержана конкретным аргументом.",
            "Контраргумент представлен честно, а вывод отвечает на исходный вопрос.",
            "Абзацы отделяют позицию, аргументы и итог друг от друга.",
            "Я проверил управление после связок и не повторяю одну формулировку.",
        ),
    },
    {
        "id": "story",
        "title": "Короткая история",
        "task": "Опиши в 100–130 словах ситуацию, когда планы неожиданно изменились. Покажи последовательность событий, реакцию и итог.",
        "hint": "Свяжи события словами «najpierw», «nagle», «wtedy», «w końcu» и проверь формы прошедшего времени.",
        "min_words": 100, "min_paragraphs": 2, "markers": ("najpierw", "w końcu"),
        "checklist": (
            "История показывает исходный план, неожиданное изменение, реакцию и итог.",
            "События расположены в понятной временной последовательности.",
            "Связки времени разнообразны и не заменяют описание самих событий.",
            "Я проверил вид, род и согласование глаголов прошедшего времени.",
        ),
    },
    ),
    "B2": (
        {
            "id": "source-comparison",
            "title": "Сравнение двух сообщений",
            "task": "Напиши 180–220 слов: сопоставь два сообщения об одном событии, отдели подтверждённые факты от оценок и сформулируй осторожный вывод.",
            "hint": "Укажи источники и степень уверенности: «według», «źródło podaje», «prawdopodobnie», «nie można wykluczyć». ",
            "min_words": 180, "min_paragraphs": 3, "markers": ("według", "prawdopodobnie"),
            "checklist": (
                "Я сопоставил оба сообщения, а не пересказал их по очереди.",
                "Факты, оценки источников и мой осторожный вывод явно разделены.",
                "Степень уверенности соответствует доступным данным.",
                "Я проверил ссылки на источники, связность и нейтральный регистр.",
            ),
        },
        {
            "id": "reasoned-recommendation",
            "title": "Обоснованная рекомендация",
            "task": "Подготовь 180–220 слов для городской консультации: представь решение, два аргумента, существенное ограничение и ответ на возможное возражение.",
            "hint": "Организуй позицию связками «wprawdzie», «jednak», «co więcej», «biorąc to pod uwagę». ",
            "min_words": 180, "min_paragraphs": 3, "markers": ("wprawdzie", "biorąc to pod uwagę"),
            "checklist": (
                "Предложение содержит два самостоятельных аргумента и существенное ограничение.",
                "Я ответил на вероятное возражение, не искажая чужую позицию.",
                "Вывод следует из аргументов и подходит городской консультации.",
                "Я проверил сложные связки, управление и официальный регистр.",
            ),
        },
        {
            "id": "formal-summary",
            "title": "Итог деловой встречи",
            "task": "Напиши 160–200 слов участникам встречи: нейтрально подведи итог обсуждения, зафиксируй решение, ответственных и следующие сроки.",
            "hint": "Соблюдай официальный регистр и отделяй принятые решения от предложений, которые ещё обсуждаются.",
            "min_words": 160, "min_paragraphs": 3, "markers": ("ustalono", "termin"),
            "checklist": (
                "Я отделил обсуждавшиеся предложения от окончательно принятых решений.",
                "Для каждого действия понятны ответственный и срок.",
                "Итог легко просмотреть благодаря абзацам и ясному порядку информации.",
                "Я проверил безличные конструкции, даты и нейтральный деловой тон.",
            ),
        },
        {
            "id": "critical-review",
            "title": "Критическая рецензия",
            "task": "Напиши 200–240 слов о книге или фильме: кратко представь произведение, интерпретируй один приём, оцени его эффект и обоснуй рекомендацию.",
            "hint": "Не пересказывай весь сюжет; связывай наблюдение и интерпретацию через «dzięki temu», «można odczytać jako», «sugeruje». ",
            "min_words": 200, "min_paragraphs": 3, "markers": ("dzięki temu", "polecam"),
            "checklist": (
                "Краткое введение даёт контекст, но не пересказывает весь сюжет.",
                "Я назвал конкретный приём и объяснил его эффект на примере.",
                "Итоговая рекомендация опирается на проведённый анализ.",
                "Я проверил оценочную лексику, связность и единый регистр рецензии.",
            ),
        },
    ),
}

LISTENING_ITEMS = (
    {"id": "tecza", "audio": "polskiflow/audio/tecza.ogg", "options": ("tęcza", "część", "ciężar"), "answer": "tęcza", "hint": "Слышны носовое ę и сочетание cz: tę-cza."},
    {"id": "wrobel", "audio": "polskiflow/audio/wrobel.ogg", "options": ("wróbel", "wybór", "wrona"), "answer": "wróbel", "hint": "Начальное wr- и ó /u/ помогают узнать слово wróbel."},
    {"id": "mysz", "audio": "polskiflow/audio/mysz.ogg", "options": ("my", "mysz", "miś"), "answer": "mysz", "hint": "Финальный шипящий sz отличает mysz от my и miś."},
)

LISTENING_DIALOGUE = {
    "title": "Встреча перед поездкой",
    "level": "A1–A2",
    "lines": (
        "Cześć, Aniu! O której jedziemy jutro do Krakowa?",
        "Pociąg odjeżdża o ósmej piętnaście. Spotkajmy się o ósmej przed kasą numer trzy.",
        "Dobrze. Kupię bilety przez internet i przyniosę kawę.",
        "Świetnie, a ja wezmę kanapki. Do zobaczenia rano!",
    ),
    "questions": (
        {
            "id": "dialogue_main",
            "prompt": "О чём договорились собеседники?",
            "options": ("Встретиться перед поездкой в Краков", "Купить продукты вечером", "Посетить кассу после работы"),
            "answer": "Встретиться перед поездкой в Краков",
            "explanation": "Они уточняют поезд, время и место встречи перед поездкой в Краков.",
        },
        {
            "id": "dialogue_detail",
            "prompt": "Где они встретятся?",
            "options": ("В поезде", "Перед кассой номер три", "В кафе на вокзале"),
            "answer": "Перед кассой номер три",
            "explanation": "Аня говорит: «Spotkajmy się o ósmej przed kasą numer trzy».",
        },
    ),
}

LISTENING_B1 = {
    "title": "Zmiana planu sąsiedzkiego spotkania",
    "level": "B1",
    "lines": (
        "Dzień dobry, tu Marta z rady osiedla. Dzwonię w sprawie sobotniego spotkania mieszkańców.",
        "Ponieważ prognoza zapowiada silny deszcz, nie spotkamy się w parku, lecz w sali biblioteki przy ulicy Lipowej.",
        "Zaczynamy bez zmian o jedenastej. Najpierw porozmawiamy o nowym placu zabaw, a potem podzielimy się zadaniami przy organizacji pikniku.",
        "Proszę przynieść swoje propozycje i, jeśli to możliwe, potwierdzić udział do piątku wieczorem. Dziękuję i do zobaczenia.",
    ),
    "questions": (
        {
            "id": "b1_listening_reason",
            "prompt": "Почему изменили место встречи?",
            "options": ("Из-за прогноза сильного дождя", "Из-за ремонта библиотеки", "Из-за изменения времени"),
            "answer": "Из-за прогноза сильного дождя",
            "explanation": "Марта связывает перенос из парка с прогнозом сильного дождя.",
        },
        {
            "id": "b1_listening_plan",
            "prompt": "Что участники обсудят сначала?",
            "options": ("Новый детский игровой комплекс", "Распределение задач на пикнике", "Расписание библиотеки"),
            "answer": "Новый детский игровой комплекс",
            "explanation": "Слово «najpierw» вводит первый пункт встречи — новый plac zabaw.",
        },
        {
            "id": "b1_listening_action",
            "prompt": "Что Марта просит сделать до вечера пятницы?",
            "options": ("Подтвердить участие", "Принести еду на пикник", "Позвонить в библиотеку"),
            "answer": "Подтвердить участие",
            "explanation": "Фраза «potwierdzić udział do piątku wieczorem» прямо задаёт действие и срок.",
        },
    ),
}

LISTENING_B2 = {
    "title": "Pilotaż pracy hybrydowej",
    "level": "B2",
    "lines": (
        "Choć część zespołu proponowała całkowitą pracę zdalną, kierownictwo zdecydowało się na trzymiesięczny pilotaż modelu hybrydowego.",
        "We wtorki wszyscy będą spotykać się w biurze, żeby wspólnie planować projekty, natomiast w pozostałe dni miejsce pracy będzie można wybrać samodzielnie.",
        "Warunkiem udziału jest przestrzeganie zasad bezpieczeństwa danych, zwłaszcza podczas korzystania z sieci poza firmą.",
        "Po zakończeniu pilotażu pracownicy wypełnią anonimową ankietę, a zarząd podejmie ostateczną decyzję na podstawie jej wyników.",
    ),
    "questions": (
        {
            "id": "b2_listening_model",
            "prompt": "Какой формат работы будет тестировать компания?",
            "options": ("Гибридный формат в течение трёх месяцев", "Полностью удалённую работу без срока", "Четырёхдневную рабочую неделю"),
            "answer": "Гибридный формат в течение трёх месяцев",
            "explanation": "Руководство выбрало трёхмесячный пилот гибридного формата, а не полностью удалённую работу.",
        },
        {
            "id": "b2_listening_tuesday",
            "prompt": "Для чего вся команда будет приезжать в офис по вторникам?",
            "options": ("Для индивидуальных собеседований", "Для совместного планирования проектов", "Для обучения правилам безопасности"),
            "answer": "Для совместного планирования проектов",
            "explanation": "Оборот «żeby wspólnie planować projekty» прямо называет цель встреч по вторникам.",
        },
        {
            "id": "b2_listening_decision",
            "prompt": "На чём будет основано окончательное решение руководства?",
            "options": ("На результатах анонимного опроса", "На количестве дней в офисе", "На отчёте службы безопасности"),
            "answer": "На результатах анонимного опроса",
            "explanation": "После пилота сотрудники заполнят анонимную анкету, и её результаты станут основанием решения.",
        },
    ),
}


def select_cefr_level(request: HttpRequest, profile_level: str) -> str:
    """Prefer an explicit valid filter, otherwise use the learner's level."""

    fallback_level = (
        profile_level.upper()
        if isinstance(profile_level, str) and profile_level.upper() in PROFILE_LEVELS
        else "A1"
    )
    requested_level = request.GET.get("level")
    if requested_level is None:
        return fallback_level
    requested_level = requested_level.upper()
    return requested_level if requested_level in PROFILE_LEVELS else fallback_level


def require_browser_user(view):
    @wraps(view)
    def protected(request: HttpRequest, *args, **kwargs):
        if request.supabase_user is None:
            login_url = reverse("login")
            query = urlencode({"next": request.get_full_path()})
            return redirect(f"{login_url}?{query}")
        return view(request, *args, **kwargs)

    return protected


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.supabase_user is not None:
        return redirect("home")

    next_url = _safe_next(request)
    context = {"mode": "login", "next": next_url}
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        if not email or not password:
            context["error"] = "Укажите email и пароль"
        elif not (rate := consume_auth_attempt(request, "login", email))[0]:
            return _auth_rate_limit_response(request, context, "auth/form.html", rate[1])
        else:
            try:
                session = sign_in(email, password)
            except SupabaseAuthError as error:
                context["error"] = str(error)
            else:
                response = redirect(next_url)
                set_auth_cookies(response, session)
                return response
    return render(request, "auth/form.html", context)


@require_http_methods(["GET", "POST"])
def register_view(request: HttpRequest) -> HttpResponse:
    if request.supabase_user is not None:
        return redirect("home")

    context = {"mode": "register", "next": "/"}
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        context["email"] = email
        if not email or not password:
            context["error"] = "Укажите email и пароль"
        elif error := password_error(password):
            context["error"] = error
        elif not (rate := consume_auth_attempt(request, "register", email))[0]:
            return _auth_rate_limit_response(request, context, "auth/form.html", rate[1])
        else:
            try:
                welcome_login = request.build_absolute_uri(
                    f"{reverse('login')}?{urlencode({'next': reverse('onboarding')})}"
                )
                session = sign_up(
                    email, password, email_redirect_to=welcome_login
                )
            except SupabaseAuthError as error:
                context["error"] = str(error)
            else:
                if session is None:
                    context["message"] = (
                        "Аккаунт создан. Подтвердите email, затем войдите."
                    )
                else:
                    response = redirect("onboarding")
                    set_auth_cookies(response, session)
                    return response
    return render(request, "auth/form.html", context)


@require_http_methods(["GET", "POST"])
def forgot_password(request: HttpRequest) -> HttpResponse:
    context = {"mode": "forgot"}
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        context["email"] = email
        if not email:
            context["error"] = "Укажите email"
        elif not (rate := consume_auth_attempt(request, "forgot", email))[0]:
            return _auth_rate_limit_response(request, context, "auth/recovery.html", rate[1])
        else:
            try:
                request_password_reset(email, request.build_absolute_uri(reverse("reset-password")))
            except SupabaseAuthError:
                pass
            context["message"] = "Если аккаунт существует, ссылка для сброса уже отправлена."
    return _no_store(render(request, "auth/recovery.html", context))


@require_http_methods(["GET", "POST"])
def reset_password(request: HttpRequest) -> HttpResponse:
    context = {"mode": "reset"}
    if request.method == "POST":
        token = request.POST.get("recovery_token", "")
        context["recovery_token"] = token
        password = request.POST.get("password", "")
        confirmation = request.POST.get("password_confirmation", "")
        if not token:
            context["error"] = "Ссылка восстановления недействительна или устарела"
        elif password != confirmation:
            context["error"] = "Пароли не совпадают"
        elif error := password_error(password):
            context["error"] = error
        else:
            try:
                update_password(token, password)
            except SupabaseAuthError as error:
                context["error"] = str(error)
            else:
                response = redirect(f"{reverse('login')}?password_reset=1")
                clear_auth_cookies(response)
                response["Cache-Control"] = "private, no-store"
                return response
    return _no_store(render(request, "auth/recovery.html", context))


@require_http_methods(["GET", "POST"])
def resend_confirmation(request: HttpRequest) -> HttpResponse:
    context = {"mode": "resend"}
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        context["email"] = email
        if not email:
            context["error"] = "Укажите email"
        elif not (rate := consume_auth_attempt(request, "resend", email))[0]:
            return _auth_rate_limit_response(request, context, "auth/recovery.html", rate[1])
        else:
            try:
                welcome_login = request.build_absolute_uri(
                    f"{reverse('login')}?{urlencode({'next': reverse('onboarding')})}"
                )
                resend_signup_confirmation(email, welcome_login)
            except SupabaseAuthError:
                pass
            context["message"] = "Если подтверждение ожидается, новое письмо уже отправлено."
    return _no_store(render(request, "auth/recovery.html", context))


@require_POST
def logout_view(request: HttpRequest) -> HttpResponse:
    if request.supabase_access_token:
        try:
            sign_out(request.supabase_access_token)
        except SupabaseAuthError:
            pass
    response = redirect("login")
    clear_auth_cookies(response)
    return response


@require_browser_user
def home(request: HttpRequest) -> HttpResponse:
    dashboard, lesson_tasks, completed_count, progress_percent = _daily_plan(request)
    draft = load_latest_lesson_draft(request.supabase_access_token, request.supabase_user.id)
    lesson_map = {item["id"]: item for item in tasks()}
    draft_lesson = lesson_map.get(draft.get("lesson_id")) if isinstance(draft, dict) else None
    resume_lesson = None
    if draft_lesson and draft_lesson["id"] not in dashboard.all_completed_lesson_ids:
        try:
            step = max(1, int(draft.get("step_index", 0)) + 1)
        except (TypeError, ValueError):
            step = 1
        resume_lesson = {**draft_lesson, "step": step}
    return render(
        request,
        "home.html",
        {
            "user": request.supabase_user,
            "dashboard": dashboard,
            "tasks": lesson_tasks,
            "completed_count": completed_count,
            "progress_percent": progress_percent,
            "resume_lesson": resume_lesson,
            "b1_exam_prep": build_b1_exam_prep(timezone.localdate())
            if dashboard.level == "B1"
            else None,
        },
    )


@require_browser_user
def daily_tasks(request: HttpRequest) -> HttpResponse:
    query = request.GET.urlencode()
    target = reverse("home")
    if query:
        target = f"{target}?{query}"
    return redirect(f"{target}#daily-tasks")


@require_browser_user
def practice_hub(request: HttpRequest) -> HttpResponse:
    """Keep optional training modes discoverable without bloating the course catalog."""
    return render(request, "practice.html")


@require_browser_user
def b1_exam_prep(request: HttpRequest) -> HttpResponse:
    """Show an honest study surface aligned with the official adult B1 format."""
    return render(
        request,
        "b1_exam_prep.html",
        {"exam_prep": build_b1_exam_prep(timezone.localdate())},
    )


@require_browser_user
@require_http_methods(["GET", "POST"])
def onboarding(request: HttpRequest) -> HttpResponse:
    """Give a new learner one short, reversible setup step."""
    fallback_name = (request.supabase_user.email or "ученик").split("@", 1)[0]
    dashboard = load_dashboard_progress(
        request.supabase_access_token, request.supabase_user.id, fallback_name
    )
    form = {
        "display_name": request.POST.get("display_name", dashboard.display_name).strip(),
        "level": request.POST.get("level", dashboard.level).upper(),
        "daily_goal_lessons": request.POST.get(
            "daily_goal_lessons", str(dashboard.daily_goal_lessons)
        ),
    }
    error = ""
    if request.method == "POST":
        if not form["display_name"] or len(form["display_name"]) > 80:
            error = "Укажи имя длиной до 80 символов."
        elif form["level"] not in PROFILE_LEVELS:
            error = "Выбери уровень от A1 до C2."
        else:
            try:
                daily_goal = int(form["daily_goal_lessons"])
            except (TypeError, ValueError):
                daily_goal = 0
            if daily_goal not in (1, 2, 3, 4):
                error = "Выбери дневную цель от одного до четырёх уроков."
            elif save_profile_settings(
                request.supabase_access_token,
                request.supabase_user.id,
                form["display_name"],
                form["level"],
                daily_goal,
            ):
                return redirect(f"{reverse('home')}?welcome=1")
            else:
                error = "Не удалось сохранить настройки. Попробуй ещё раз."
    return render(
        request,
        "onboarding.html",
        {
            "onboarding_form": form,
            "onboarding_levels": PROFILE_LEVELS,
            "onboarding_error": error,
        },
        status=400 if error else 200,
    )


@require_browser_user
@require_http_methods(["GET", "POST"])
def profile(request: HttpRequest) -> HttpResponse:
    fallback_name = (request.supabase_user.email or "ученик").split("@", 1)[0]
    dashboard = load_dashboard_progress(
        request.supabase_access_token,
        request.supabase_user.id,
        fallback_name,
    )
    lesson_ids = {lesson_task["id"] for lesson_task in tasks()}
    completed_lessons = len(dashboard.all_completed_lesson_ids & lesson_ids)
    total_lessons = len(lesson_ids)
    progress_percent = (
        round(completed_lessons / total_lessons * 100) if total_lessons else 0
    )
    personal_words = load_personal_words(
        request.supabase_access_token,
        request.supabase_user.id,
    )
    dictionary_count = len(personal_words or [])
    achievements = build_achievements(
        completed_lessons=completed_lessons,
        streak_days=dashboard.streak_days,
        dictionary_count=dictionary_count,
        active_days=dashboard.active_days,
    )
    profile_form = {
        "display_name": dashboard.display_name,
        "level": dashboard.level,
        "daily_goal_lessons": dashboard.daily_goal_lessons,
    }
    profile_message = ""
    profile_error = ""
    reminder_preferences = load_reminder_preferences(
        request.supabase_access_token,
        request.supabase_user.id,
    )
    reminder_available = reminder_preferences is not None
    if reminder_preferences is None:
        reminder_preferences = {
            "daily_reminder_enabled": False,
            "reminder_time": "19:00",
            "timezone": "Europe/Warsaw",
        }
    reminder_message = ""
    reminder_error = ""
    form_action = request.POST.get("form_action") if request.method == "POST" else None
    if request.method == "POST" and form_action == "reminders":
        reminder_time = request.POST.get("reminder_time", "")
        try:
            datetime.strptime(reminder_time, "%H:%M")
        except ValueError:
            reminder_error = "Укажите корректное время напоминания"
        else:
            reminder_preferences = {
                "daily_reminder_enabled": request.POST.get("daily_reminder_enabled") == "on",
                "reminder_time": reminder_time,
                "timezone": "Europe/Warsaw",
            }
            if save_reminder_preferences(
                request.supabase_access_token,
                request.supabase_user.id,
                reminder_preferences["daily_reminder_enabled"],
                reminder_preferences["reminder_time"],
                reminder_preferences["timezone"],
            ):
                reminder_message = "Настройки напоминаний сохранены"
                reminder_available = True
            else:
                reminder_error = "Не удалось сохранить настройки напоминаний. Попробуйте ещё раз."
    elif request.method == "POST":
        profile_form = {
            "display_name": request.POST.get("display_name", "").strip(),
            "level": request.POST.get("level", "").upper(),
            "daily_goal_lessons": request.POST.get("daily_goal_lessons", str(dashboard.daily_goal_lessons)),
        }
        if not profile_form["display_name"]:
            profile_error = "Укажите имя"
        elif len(profile_form["display_name"]) > 80:
            profile_error = "Имя должно быть не длиннее 80 символов"
        elif profile_form["level"] not in PROFILE_LEVELS:
            profile_error = "Выберите уровень от A1 до C2"
        elif not profile_form["daily_goal_lessons"].isdigit() or not 1 <= int(profile_form["daily_goal_lessons"]) <= 10:
            profile_error = "Цель должна быть от 1 до 10 уроков в день"
        elif save_profile_settings(
            request.supabase_access_token,
            request.supabase_user.id,
            profile_form["display_name"],
            profile_form["level"],
            int(profile_form["daily_goal_lessons"]),
        ):
            dashboard = replace(
                dashboard,
                display_name=profile_form["display_name"],
                level=profile_form["level"],
                daily_goal_lessons=int(profile_form["daily_goal_lessons"]),
            )
            profile_message = "Профиль сохранён"
        else:
            profile_error = "Не удалось сохранить профиль. Попробуйте ещё раз."
    daily_goal_insight = build_daily_goal_insight(
        dashboard.recent_daily_completion_counts,
        dashboard.daily_goal_lessons,
    )
    return render(
        request,
        "profile.html",
        {
            "dashboard": dashboard,
            "email": request.supabase_user.email or "Email не указан",
            "completed_lessons": completed_lessons,
            "total_lessons": total_lessons,
            "progress_percent": progress_percent,
            "dictionary_count": dictionary_count,
            "dictionary_available": personal_words is not None,
            "achievements": achievements,
            "unlocked_achievements": sum(item.unlocked for item in achievements),
            "profile_levels": PROFILE_LEVELS,
            "profile_form": profile_form,
            "profile_message": profile_message,
            "profile_error": profile_error,
            "daily_goal_insight": daily_goal_insight,
            "reminder_preferences": reminder_preferences,
            "reminder_available": reminder_available,
            "reminder_message": reminder_message,
            "reminder_error": reminder_error,
        },
    )


def sources(request: HttpRequest) -> HttpResponse:
    """Show the public attribution and content-source policy summary."""
    return render(request, "sources.html")


def privacy(request: HttpRequest) -> HttpResponse:
    """Show a public, factual inventory of current data handling."""
    response = render(request, "privacy.html")
    response["Cache-Control"] = (
        "private, no-store" if request.supabase_user else "public, max-age=300"
    )
    return response


@require_browser_user
def profile_data_export(request: HttpRequest) -> HttpResponse:
    """Download an owner-scoped, token-free learning-data snapshot."""
    export = load_privacy_export(
        request.supabase_access_token, request.supabase_user.id
    )
    if not export.available:
        response = JsonResponse({"error": "Данные временно недоступны. Попробуйте экспорт позже."}, status=503)
    else:
        response = JsonResponse({
            "schema_version": "2.0",
            "exported_at": timezone.now().isoformat(),
            "account": {"email": request.supabase_user.email},
            **export.datasets,
        }, json_dumps_params={"ensure_ascii": False, "indent": 2})
        response["Content-Disposition"] = 'attachment; filename="polskiflow-data.json"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_browser_user
def writing_practice(request: HttpRequest) -> HttpResponse:
    """Offer honest, browser-local B1/B2 writing practice without auto-grading."""
    selected_level = request.GET.get("level", "B1").upper()
    if selected_level not in WRITING_PROMPTS:
        selected_level = "B1"
    return render(
        request,
        "writing.html",
        {
            "writing_prompts": WRITING_PROMPTS[selected_level],
            "writing_levels": tuple(WRITING_PROMPTS),
            "selected_writing_level": selected_level,
        },
    )


@require_browser_user
@require_http_methods(["GET", "POST"])
def listening_practice(request: HttpRequest) -> HttpResponse:
    """Small listening pilot; results stay in this response only."""
    submitted = request.method == "POST"
    answers = {item["id"]: request.POST.get(item["id"], "") for item in LISTENING_ITEMS}
    display_items = tuple(
        {
            **item,
            "selected": answers[item["id"]],
            "is_correct": submitted and answers[item["id"]] == item["answer"],
        }
        for item in LISTENING_ITEMS
    )
    score = sum(item["is_correct"] for item in display_items) if submitted else None
    dialogue_answers = {
        question["id"]: request.POST.get(question["id"], "")
        for question in LISTENING_DIALOGUE["questions"]
    }
    dialogue_questions = tuple(
        {
            **question,
            "selected": dialogue_answers[question["id"]],
            "is_correct": submitted
            and dialogue_answers[question["id"]] == question["answer"],
        }
        for question in LISTENING_DIALOGUE["questions"]
    )
    dialogue_submitted = submitted and any(dialogue_answers.values())
    dialogue_score = (
        sum(question["is_correct"] for question in dialogue_questions)
        if dialogue_submitted
        else None
    )
    dialogue = {**LISTENING_DIALOGUE, "questions": dialogue_questions}
    b1_answers = {
        question["id"]: request.POST.get(question["id"], "")
        for question in LISTENING_B1["questions"]
    }
    b1_questions = tuple(
        {
            **question,
            "selected": b1_answers[question["id"]],
            "is_correct": submitted
            and b1_answers[question["id"]] == question["answer"],
        }
        for question in LISTENING_B1["questions"]
    )
    b1_submitted = submitted and any(b1_answers.values())
    b1_listening = {**LISTENING_B1, "questions": b1_questions}
    b2_answers = {
        question["id"]: request.POST.get(question["id"], "")
        for question in LISTENING_B2["questions"]
    }
    b2_questions = tuple(
        {
            **question,
            "selected": b2_answers[question["id"]],
            "is_correct": submitted
            and b2_answers[question["id"]] == question["answer"],
        }
        for question in LISTENING_B2["questions"]
    )
    b2_submitted = submitted and any(b2_answers.values())
    b2_listening = {**LISTENING_B2, "questions": b2_questions}
    return render(
        request,
        "listening.html",
        {
            "listening_items": display_items,
            "score": score,
            "submitted": submitted,
            "dialogue": dialogue,
            "dialogue_submitted": dialogue_submitted,
            "dialogue_score": dialogue_score,
            "b1_listening": b1_listening,
            "b1_submitted": b1_submitted,
            "b1_score": sum(question["is_correct"] for question in b1_questions)
            if b1_submitted
            else None,
            "b2_listening": b2_listening,
            "b2_submitted": b2_submitted,
            "b2_score": sum(question["is_correct"] for question in b2_questions)
            if b2_submitted
            else None,
        },
    )


def _daily_plan(request: HttpRequest):
    fallback_name = (request.supabase_user.email or "ученик").split("@", 1)[0]
    dashboard = load_dashboard_progress(
        request.supabase_access_token,
        request.supabase_user.id,
        fallback_name,
    )
    personal_words = load_personal_words(
        request.supabase_access_token, request.supabase_user.id
    )
    lesson_tasks = build_daily_plan(
        tasks(),
        level=dashboard.level,
        completed_all_time=dashboard.all_completed_lesson_ids,
        completed_today=dashboard.completed_lesson_ids,
        personal_words=personal_words,
        today=timezone.localdate(),
        daily_task_limit=dashboard.daily_goal_lessons,
        recent_completion_results=dashboard.recent_completion_results,
    )
    completed_count = sum(task["completed"] for task in lesson_tasks)
    progress_percent = (
        round(completed_count / len(lesson_tasks) * 100) if lesson_tasks else 0
    )
    return dashboard, lesson_tasks, completed_count, progress_percent


def _no_store(response: HttpResponse) -> HttpResponse:
    response["Cache-Control"] = "private, no-store"
    return response


def _auth_rate_limit_response(request, context, template, retry_after):
    context["error"] = "Слишком много попыток. Подождите и попробуйте снова."
    response = render(request, template, context, status=429)
    response["Retry-After"] = str(retry_after)
    return _no_store(response)


@require_browser_user
def course(request: HttpRequest) -> HttpResponse:
    fallback_name = (request.supabase_user.email or "ученик").split("@", 1)[0]
    dashboard = load_dashboard_progress(
        request.supabase_access_token,
        request.supabase_user.id,
        fallback_name,
    )
    levels = PROFILE_LEVELS
    selected_level = select_cefr_level(request, dashboard.level)
    all_topics = course_topics()
    lesson_bookmarks = load_lesson_bookmarks(
        request.supabase_access_token, request.supabase_user.id
    )
    level_counts = {
        level: sum(topic["level"] == level for topic in all_topics) for level in levels
    }

    def count_label(count: int, forms: tuple[str, str, str]) -> str:
        if count % 10 == 1 and count % 100 != 11:
            suffix = forms[0]
        elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
            suffix = forms[1]
        else:
            suffix = forms[2]
        return f"{count} {suffix}"
    level_topics = [topic for topic in all_topics if topic["level"] == selected_level]
    for topic in level_topics:
        completed_count = 0
        next_lesson = None
        for lesson in topic["lessons"]:
            lesson["completed"] = lesson["id"] in dashboard.all_completed_lesson_ids
            lesson["saved"] = lesson["id"] in (lesson_bookmarks or set())
            if lesson["completed"]:
                completed_count += 1
            elif next_lesson is None:
                next_lesson = lesson
        lesson_count = len(topic["lessons"])
        topic["completed_count"] = completed_count
        topic["lesson_count"] = lesson_count
        topic["progress_percent"] = round(completed_count / lesson_count * 100)
        topic["next_lesson"] = next_lesson
        topic["completed"] = completed_count == lesson_count
    filters = {
        "q": request.GET.get("q", "").strip()[:120],
        "topic": request.GET.get("topic", ""),
        "kind": request.GET.get("kind", ""),
        "duration": request.GET.get("duration", ""),
        "completion": request.GET.get("completion", ""),
    }
    valid_topic_ids = {topic["id"] for topic in level_topics}
    if filters["topic"] not in valid_topic_ids:
        filters["topic"] = ""
    if filters["kind"] not in LESSON_KINDS:
        filters["kind"] = ""
    if filters["duration"] not in DURATION_FILTERS:
        filters["duration"] = ""
    if filters["completion"] not in COMPLETION_FILTERS:
        filters["completion"] = ""
    topics = filter_course_topics(
        level_topics,
        query=filters["q"],
        topic_id=filters["topic"],
        kind=filters["kind"],
        duration=filters["duration"],
        completion=filters["completion"],
    )
    result_lesson_count = sum(len(topic["lessons"]) for topic in topics)
    return render(
        request,
        "course.html",
        {
            "dashboard": dashboard,
            "course_topics": topics,
            "course_levels": [
                {
                    "name": level,
                    "topic_count": level_counts[level],
                    "topic_count_label": (
                        count_label(level_counts[level], ("тема", "темы", "тем"))
                        if level_counts[level]
                        else "Скоро"
                    ),
                }
                for level in levels
            ],
            "selected_level": selected_level,
            "diagnostic_level_applied": request.GET.get("diagnostic") == "applied",
            "catalog_filters": filters,
            "catalog_topic_options": level_topics,
            "catalog_kind_options": LESSON_KINDS.items(),
            "catalog_result_topic_label": count_label(
                len(topics), ("тема", "темы", "тем")
            ),
            "catalog_result_lesson_label": count_label(
                result_lesson_count, ("урок", "урока", "уроков")
            ),
            "lesson_bookmarks_available": lesson_bookmarks is not None,
        },
    )


def _safe_next(request: HttpRequest) -> str:
    candidate = request.POST.get("next") or request.GET.get("next") or "/"
    if url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return "/"
