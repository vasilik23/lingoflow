"""Static, reviewable scenarios for interaction and mediation practice."""

from dataclasses import dataclass
from types import SimpleNamespace
from polskiflow.domain.b1_training_speaking import training_speaking_tasks


@dataclass(frozen=True)
class ScenarioOption:
    id: str
    text: str


@dataclass(frozen=True)
class InteractionScenario:
    id: str
    level: str
    mode: str
    title: str
    situation: str
    prompt: str
    options: tuple[ScenarioOption, ...]
    correct_option_id: str
    explanation: str


@dataclass(frozen=True)
class SequenceBlock:
    id: str
    text: str


@dataclass(frozen=True)
class SequenceScenario:
    id: str
    level: str
    mode: str
    title: str
    situation: str
    prompt: str
    blocks: tuple[SequenceBlock, ...]
    correct_order: tuple[str, ...]
    explanation: str


@dataclass(frozen=True)
class FreeProductionScenario:
    id: str
    level: str
    mode: str
    title: str
    situation: str
    task: str
    checklist: tuple[str, ...]


@dataclass(frozen=True)
class SpeakingScenario:
    id: str
    level: str
    title: str
    situation: str
    task: str
    preparation_seconds: int
    response_seconds: int
    outline: tuple[str, ...]
    checklist: tuple[str, ...]
    sample_answer: str
    image: str = ""
    image_alt: str = ""
    image_description: str = ""
    dialogue_turns: tuple[str, ...] = ()


SCENARIOS = (
    InteractionScenario(
        id="weekend-plan",
        level="B1",
        mode="Взаимодействие",
        title="Договориться о плане",
        situation="Вы с другом выбираете: поехать в субботу за город или остаться в городе. Друг предпочитает город, а ты — поездку.",
        prompt="Как поддержать разговор и приблизиться к общему решению?",
        options=(
            ScenarioOption("a", "Jedziemy za miasto. Nie ma o czym rozmawiać."),
            ScenarioOption("b", "Rozumiem, że wolisz zostać w mieście. Może pojedziemy rano za miasto, a wieczorem wrócimy na koncert?"),
            ScenarioOption("c", "Skoro nie chcesz jechać, sam wszystko zaplanuj."),
        ),
        correct_option_id="b",
        explanation="Ответ признаёт предпочтение собеседника и предлагает конкретный компромисс. Остальные варианты закрывают обсуждение или перекладывают решение.",
    ),
    InteractionScenario(
        id="meeting-position",
        level="B2",
        mode="Медиация",
        title="Нейтрально передать позицию",
        situation="На встрече Анна говорит: «Ten termin jest absurdalny, nikt nie zdąży». Нужно кратко передать её позицию руководителю.",
        prompt="Какая формулировка сохраняет смысл без лишней эмоциональности?",
        options=(
            ScenarioOption("a", "Anna uważa, że zaproponowany termin może być zbyt krótki, aby zespół zakończył pracę."),
            ScenarioOption("b", "Anna powiedziała, że kierownik wyznacza absurdalne terminy."),
            ScenarioOption("c", "Anna nie chce pracować nad tym zadaniem."),
        ),
        correct_option_id="a",
        explanation="Нейтральная версия сохраняет главное опасение — недостаток времени — но не приписывает Анне критику человека или отказ от работы.",
    ),
    InteractionScenario(
        id="clinic-message",
        level="B1",
        mode="Медиация",
        title="Объяснить информацию проще",
        situation="В сообщении клиники написано: «Pacjenci są zobowiązani stawić się na czczo». Знакомый пока слабо читает по-польски.",
        prompt="Как просто и точно объяснить сообщение?",
        options=(
            ScenarioOption("a", "Musisz przyjść wcześniej niż zwykle."),
            ScenarioOption("b", "Przed wizytą nie jedz ani nie pij tego, czego zabroniła klinika; sprawdź też jej dokładne zalecenia."),
            ScenarioOption("c", "Wizyta została odwołana."),
        ),
        correct_option_id="b",
        explanation="Ответ объясняет выражение «na czczo» простыми словами и предлагает сверить точные медицинские указания, не добавляя неподтверждённых деталей.",
    ),
    InteractionScenario(
        id="formal-reply",
        level="B2",
        mode="Взаимодействие",
        title="Выбрать подходящий регистр",
        situation="Преподаватель официально просит прислать исправленную работу до пятницы. Нужно ответить по электронной почте.",
        prompt="Какой ответ соответствует ситуации?",
        options=(
            ScenarioOption("a", "Spoko, ogarnę to."),
            ScenarioOption("b", "Szanowna Pani, dziękuję za wiadomość. Prześlę poprawioną pracę do piątku. Z poważaniem, Marta Nowak"),
            ScenarioOption("c", "Praca będzie, kiedy będzie gotowa."),
        ),
        correct_option_id="b",
        explanation="Вариант подтверждает срок и использует уместные приветствие и завершение. Остальные ответы слишком разговорные или резкие для официальной переписки.",
    ),
    InteractionScenario(
        id="community-summary",
        level="B2",
        mode="Медиация",
        title="Свести две позиции",
        situation="Жители хотят больше деревьев на площади, а владельцы магазинов боятся потерять парковочные места. Ты подводишь итог обсуждения.",
        prompt="Как обозначить обе позиции и следующий шаг?",
        options=(
            ScenarioOption("a", "Mieszkańcy mają rację, więc parking trzeba usunąć."),
            ScenarioOption("b", "Jedni chcą więcej zieleni, drudzy potrzebują dostępu dla klientów. Sprawdźmy wariant z drzewami i krótkim postojem przy sklepach."),
            ScenarioOption("c", "Nie da się pogodzić tych oczekiwań."),
        ),
        correct_option_id="b",
        explanation="Ответ видимо представляет обе стороны и предлагает проверяемый компромисс, не объявляя одну позицию единственно правильной.",
    ),
)


SCENARIOS_BY_ID = {scenario.id: scenario for scenario in SCENARIOS}


SEQUENCE_SCENARIOS = (
    SequenceScenario(
        id="library-request",
        level="B1",
        mode="Взаимодействие",
        title="Собрать вежливую просьбу",
        situation="В библиотеке нужная книга выдана. Ты хочешь узнать о возврате и попросить забронировать её.",
        prompt="Расставь смысловые блоки в естественном порядке.",
        blocks=(
            SequenceBlock("request", "Czy mogłaby pani zarezerwować ją dla mnie?"),
            SequenceBlock("context", "Widzę, że książka jest teraz wypożyczona."),
            SequenceBlock("question", "Czy wiadomo, kiedy zostanie zwrócona?"),
        ),
        correct_order=("context", "question", "request"),
        explanation="Сначала обозначаем общую ситуацию, затем уточняем факт и только после этого формулируем просьбу. Так сотруднику понятно, к чему относится бронирование.",
    ),
    SequenceScenario(
        id="delay-mediation",
        level="B2",
        mode="Медиация",
        title="Передать сообщение о задержке",
        situation="Коллега не видел письма: поставщик задерживает доставку на два дня, поэтому монтаж начнётся позже, но итоговый срок пока не меняется.",
        prompt="Собери нейтральное и логичное резюме.",
        blocks=(
            SequenceBlock("effect", "W rezultacie montaż zacznie się później."),
            SequenceBlock("reservation", "Na razie nie zmienia to jednak końcowego terminu projektu."),
            SequenceBlock("cause", "Dostawca poinformował o dwudniowym opóźnieniu dostawy."),
        ),
        correct_order=("cause", "effect", "reservation"),
        explanation="Последовательность «причина → последствие → важная оговорка» передаёт все факты и не создаёт ложного впечатления, что конечный срок уже перенесён.",
    ),
    SequenceScenario(
        id="neighbour-compromise",
        level="B2",
        mode="Взаимодействие",
        title="Предложить соседям компромисс",
        situation="Одни жильцы хотят тишины во дворе, другие просят оставить место для вечерних встреч.",
        prompt="Выстрой ответ, который ведёт к проверяемому решению.",
        blocks=(
            SequenceBlock("proposal", "Możemy wyznaczyć miejsce spotkań i ustalić ciszę po godzinie 21."),
            SequenceBlock("check", "Po miesiącu sprawdźmy, czy takie rozwiązanie działa dla obu stron."),
            SequenceBlock("positions", "Jedni potrzebują spokojnego odpoczynku, a drudzy miejsca do spotkań."),
        ),
        correct_order=("positions", "proposal", "check"),
        explanation="Ответ сначала признаёт обе потребности, затем предлагает конкретное правило и срок проверки. Компромисс можно оценить и при необходимости изменить.",
    ),
)


SEQUENCE_SCENARIOS_BY_ID = {
    scenario.id: scenario for scenario in SEQUENCE_SCENARIOS
}


FREE_PRODUCTION_SCENARIOS = (
    FreeProductionScenario(
        id="schedule-compromise",
        level="B1",
        mode="Взаимодействие",
        title="Предложить компромисс в переписке",
        situation="Друг хочет встретиться в пятницу вечером, но ты можешь только в субботу до обеда.",
        task="Напиши по-польски короткий ответ: признай предложение, объясни ограничение и предложи конкретную альтернативу.",
        checklist=(
            "Я отреагировал на предложение собеседника, а не начал новую тему.",
            "Я кратко и вежливо объяснил своё ограничение.",
            "Я предложил конкретное время или попросил выбрать из вариантов.",
        ),
    ),
    FreeProductionScenario(
        id="event-mediation",
        level="B2",
        mode="Медиация",
        title="Передать важное из объявления",
        situation="Организатор сообщил: встреча переносится с 18:00 на 19:30 из-за задержки поезда; место не меняется, регистрацию продлили до 19:15.",
        task="Передай по-польски эту информацию знакомому нейтрально и понятно, не копируя исходную формулировку.",
        checklist=(
            "Я сохранил причину переноса, новое время и прежнее место.",
            "Я упомянул новый срок регистрации и не добавил своих догадок.",
            "Текст понятен человеку, который не видел исходного объявления.",
        ),
    ),
)


SPEAKING_SCENARIOS = (
    SpeakingScenario(
        id="neighbourhood-change",
        level="B1",
        title="Zmiana w twojej okolicy",
        situation="W twojej okolicy otwarto nowe miejsce, które wpłynęło na życie mieszkańców.",
        task="Opowiedz, co się zmieniło, podaj dwie korzyści albo trudności i wyraź swoją opinię.",
        preparation_seconds=45,
        response_seconds=180,
        outline=("назови место и изменение", "приведи два конкретных последствия", "заверши своим мнением"),
        checklist=(
            "Я выполнил все три пункта задания, а не только описал место.",
            "Ответ имеет понятное начало, развитие и завершение.",
            "Я использовал связки и не повторял постоянно одни слова.",
            "Я заметил ошибки в формах, но они не разрушили смысл.",
            "Речь в основном понятна без чтения текста перед глазами.",
        ),
        sample_answer=(
            "Niedawno w mojej okolicy otwarto małą bibliotekę z kawiarnią. Wcześniej brakowało nam spokojnego "
            "miejsca do nauki i spotkań. Teraz uczniowie mogą tam pracować po lekcjach, a starsi mieszkańcy "
            "uczestniczą w bezpłatnych zajęciach. Z drugiej strony wieczorem trudno znaleźć miejsce do parkowania. "
            "Moim zdaniem zmiana jest korzystna, ale miasto powinno lepiej zorganizować ruch w tej części dzielnicy."
        ),
    ),
    SpeakingScenario(
        id="group-decision",
        level="B1",
        title="Wspólna decyzja",
        situation="Grupa znajomych planuje wolny weekend. Część chce odpocząć, a część aktywnie spędzić czas.",
        task="Przedstaw oba stanowiska, zaproponuj kompromis i uzasadnij, dlaczego może zadziałać.",
        preparation_seconds=45,
        response_seconds=180,
        outline=("przedstaw obie potrzeby", "zaproponuj konkretny plan", "wyjaśnij zaletę kompromisu"),
        checklist=(
            "Я ясно представил обе позиции без оценки людей.",
            "Я предложил конкретный, выполнимый компромисс.",
            "Аргумент объясняет, почему решение подходит обеим сторонам.",
            "Связки помогают слушателю следить за ходом ответа.",
            "Темп и произношение позволяют понять ключевые мысли.",
        ),
        sample_answer=(
            "Jedna część grupy chce odpocząć po trudnym tygodniu, a druga woli wycieczkę rowerową. Proponuję, "
            "żebyśmy w sobotę rano pojechali na krótką trasę, a po południu odpoczęli nad jeziorem. Osoby, które "
            "nie chcą jechać rowerem, mogłyby spotkać się z nami dopiero nad wodą. Dzięki temu każdy wybierze "
            "odpowiedni poziom aktywności, a mimo to spędzimy część dnia razem."
        ),
    ),
)


SPEAKING_SCENARIOS += tuple(
    SpeakingScenario(id="visual-" + task.id, level="B1", title=task.title,
        situation="", task=task.prompt, preparation_seconds=45, response_seconds=180,
        outline=task.checklist, checklist=task.checklist, sample_answer="",
        image=task.image, image_alt=task.image_alt, image_description=task.image_description,
        dialogue_turns=task.dialogue_turns)
    for task in training_speaking_tasks(SimpleNamespace(speaking_prompt=""), 9, interactive=True)[1:]
)


def validate_answer(scenario_id: str, option_id: str) -> tuple[InteractionScenario, bool]:
    """Validate identifiers and return the selected scenario and result."""
    scenario = SCENARIOS_BY_ID.get(scenario_id)
    if scenario is None:
        raise ValueError("Неизвестный сценарий.")
    allowed_options = {option.id for option in scenario.options}
    if option_id not in allowed_options:
        raise ValueError("Выберите один из предложенных ответов.")
    return scenario, option_id == scenario.correct_option_id


def validate_sequence_answer(
    scenario_id: str, block_ids: tuple[str, ...]
) -> tuple[SequenceScenario, bool]:
    """Validate a complete permutation of blocks and compare it with the answer."""
    scenario = SEQUENCE_SCENARIOS_BY_ID.get(scenario_id)
    if scenario is None:
        raise ValueError("Неизвестное задание на последовательность.")
    allowed_ids = {block.id for block in scenario.blocks}
    if len(block_ids) != len(scenario.blocks) or set(block_ids) != allowed_ids:
        raise ValueError("Используйте каждый предложенный блок ровно один раз.")
    return scenario, block_ids == scenario.correct_order
