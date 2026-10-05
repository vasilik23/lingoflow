"""Original writing prompts for the guided run, without automated assessment."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WritingTask:
    id: str
    title: str
    prompt: str
    minimum: int
    maximum: int


LONG_WRITING_PROMPTS = {
    "b1-weekly-v1": "Napisz tekst do gazetki kursu językowego o miejscu, do którego lubisz wracać. Opisz to miejsce, przedstaw związane z nim wspomnienie i wyjaśnij, dlaczego jest dla Ciebie ważne. Zakończ radą dla osoby, która chce je odwiedzić. 140–170 słów.",
    "b1-weekly-v2": "Napisz relację z wydarzenia kulturalnego, w którym uczestniczyłeś lub uczestniczyłaś. Podaj miejsce i okazję, opisz przebieg wydarzenia oraz jedną sytuację, która szczególnie Cię zainteresowała. Oceń wydarzenie i wyjaśnij, komu polecasz udział w podobnym spotkaniu. 140–170 słów.",
    "b1-weekly-v3": "Napisz tekst do gazetki osiedlowej o wspólnej inicjatywie sąsiadów. Wyjaśnij, skąd wziął się pomysł, opisz podział zadań i jedną trudność oraz sposób jej rozwiązania. Przedstaw efekty i zachęć innych mieszkańców do udziału. 140–170 słów.",
}


def training_writing_tasks(variant, content_version):
    short = WritingTask("short", "Krótka wiadomość lub ogłoszenie", variant.writing_prompt, 50, 80)
    if content_version < 4:
        return (short,)
    long = WritingTask("long", "Dłuższa wypowiedź", LONG_WRITING_PROMPTS[variant.id], 140, 170)
    return (short, long)
