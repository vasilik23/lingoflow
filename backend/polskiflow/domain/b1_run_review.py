"""Rebuild run feedback from its pinned content and completed objective answers."""

from polskiflow.domain.b1_training_content import score_training_part, training_reading_blocks
from polskiflow.domain.b1_training_writing import training_writing_tasks
from polskiflow.domain.b1_training_speaking import training_speaking_tasks


def theory_lesson(question):
    """Link to existing theory, using the item's editorial explanation only."""
    if question.module != "grammar":
        return "b1media-grammar"
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
        review["details"] = tuple({**detail, "theory_lesson": theory_lesson(detail["question"])} for detail in score["details"])
        if part["id"] == "listening":
            if version >= 10:
                from polskiflow.domain.b1_training_listening_draft import LISTENING_DRAFTS
                review["sources"] = tuple({"title": block.id, "text": block.transcript} for block in LISTENING_DRAFTS)
            else:
                review["sources"] = ({"title": "Transkrypcja", "text": variant.listening_transcript},)
        elif part["id"] == "reading":
            review["sources"] = tuple({"title": block.title, "text": block.text} for block in training_reading_blocks(variant, version)) if version >= 3 else ({"title": "Tekst", "text": variant.reading_text},)
    elif result["status"] == "self_review":
        review["tasks"] = training_writing_tasks(variant, version) if part["id"] == "writing" else training_speaking_tasks(variant, version)
        review["theory_lesson"] = "b1work-grammar" if part["id"] == "writing" else "b1media-grammar"
    return review
