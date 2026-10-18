"""Rebuild run feedback from its pinned content and completed objective answers."""

from polskiflow.domain.b1_training_content import score_training_part, training_reading_blocks
from polskiflow.domain.b1_training_writing import training_writing_tasks
from polskiflow.domain.b1_training_speaking import training_speaking_tasks
from polskiflow.domain.b1_exam_prep import B1_EXAM_MODULES


def run_next_step(reviews):
    """One training suggestion, never a grade for writing or speaking."""
    reviews = tuple(item for item in reviews if item is not None)
    weak = [item for item in reviews if item['status'] == 'scored' and item['percent'] < 50]
    target = min(weak, key=lambda item: item['percent']) if weak else next(
        (item for item in reviews if item['status'] == 'skipped'), None)
    if target is None:
        return {'href': '/exam/b1/?mode=today#exam-today-title',
                'action': 'Сегодня · 15 минут',
                'reason': 'Продолжи короткую практику. Самопроверка письма и речи не подтверждает экзаменационный уровень.'}
    module = next(item for item in B1_EXAM_MODULES if item['id'] == target['id'])
    suggestion = {'href': module['href'], 'action': module['action'],
                  'reason': 'Вернись к пропущенной части.' if target['status'] == 'skipped'
                  else 'Начни с части с самым низким учебным результатом.'}
    if target['id'] == 'grammar':
        detail = next((item for item in target['details'] if not item['is_correct']), None)
        if detail:
            suggestion.update(href=f"/lesson/{detail['theory_lesson']}/", action='Повторить теорию')
    return suggestion


def theory_lesson(question):
    """Link to existing theory, using the item's editorial explanation only."""
    if question.module != "grammar":
        return None
    explanation = question.explanation.casefold()
    rules = (
        (("gdyby", "przypuszcz", "warunkow"), "b1work-grammar"),
        (("zaimek", "który", "która", "której", "którą"), "b1rel-grammar"),
        (("liczebnik", "pięć", "stopień wyższy"), "returns-grammar"),
        (("celownik",), "b1rel-grammar"),
        (("miejscownik",), "home-grammar"),
        (("biernik",), "food-grammar"),
        (("dopełniacz", "narzędnik"), "housing-grammar"),
        (("przyszł",), "travel-grammar"),
        (("przeszł", "niemęskoosob", "męska forma"), "past-grammar"),
        (("prośb", "proszę", "termin"), "office-grammar"),
        (("przyczyn", "skutek"), "rel-grammar"),
        (("spójnik", "zdanie", "zdania"), "b1edu-grammar"),
    )
    return next((lesson for words, lesson in rules if any(word in explanation for word in words)), "a2work-grammar")


def run_review(state, variant, part):
    """Legacy aggregates have no answers: never fabricate a past response."""
    version = state.get("content_version", 1)
    result = next((item for item in state["results"] if item["id"] == part["id"]), None)
    if not result:
        return None
    review = {**part, **result, "details": (), "sources": (), "tasks": ()}
    answers = state.get("review_answers", {}).get(part["id"])
    if result["status"] == "scored" and answers is not None:
        score = score_training_part(variant, part["id"], answers, version, allow_missing=True)
        source_questions = ()
        if part["id"] == "listening":
            if version >= 10:
                from polskiflow.domain.b1_training_listening_draft import LISTENING_DRAFTS
                review["sources"] = tuple({"title": block.id, "text": block.transcript} for block in LISTENING_DRAFTS)
                source_questions = tuple(block.questions for block in LISTENING_DRAFTS)
            else:
                review["sources"] = ({"title": "Transkrypcja", "text": variant.listening_transcript},)
        elif part["id"] == "reading":
            blocks = training_reading_blocks(variant, version) if version >= 3 else ()
            review["sources"] = tuple({"title": block.title, "text": block.text} for block in blocks) if blocks else ({"title": "Tekst", "text": variant.reading_text},)
            source_questions = tuple(block.questions for block in blocks)
        review["sources"] = tuple({**source, "anchor": f"run-review-{part['id']}-source-{index}"}
                                  for index, source in enumerate(review["sources"]))
        details = []
        for detail in score["details"]:
            question = detail["question"]
            source_index = next((index for index, questions in enumerate(source_questions)
                                 if any(item.id == question.id for item in questions)), 0)
            source = review["sources"][source_index] if review["sources"] else None
            details.append({**detail, "theory_lesson": theory_lesson(question),
                            "source_anchor": source["anchor"] if source else None})
        review["details"] = tuple(details)
    elif result["status"] == "self_review":
        review["tasks"] = training_writing_tasks(variant, version) if part["id"] == "writing" else training_speaking_tasks(variant, version, interactive=state.get("speaking_version") == 2)
        review["theory_lesson"] = "b1work-grammar" if part["id"] == "writing" else "b1media-grammar"
    return review
