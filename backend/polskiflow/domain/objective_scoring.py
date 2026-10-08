"""Partial objective attempts reuse strict answer validation without awarding blanks."""


def score_with_missing(questions, answers, score_complete):
    if set(answers) - {question.id for question in questions}:
        raise ValueError("Unknown answers")
    supplied = {key: value for key, value in answers.items() if not isinstance(value, str) or value.strip()}
    complete = {question.id: supplied.get(question.id, question.correct) for question in questions}
    score = score_complete(complete)
    for detail in score["details"]:
        missing = detail["question"].id not in supplied
        detail["unanswered"] = missing
        if missing:
            detail.update(selected=None, selected_text="", is_correct=False)
    _counts(score, score["details"])
    for module in score.get("modules", ()):
        _counts(module, [detail for detail in score["details"] if detail["question"].module == module["id"]])
    return score


def _counts(result, details):
    result["correct"] = sum(detail["is_correct"] for detail in details)
    result["unanswered"] = sum(detail["unanswered"] for detail in details)
    result["incorrect"] = result["total"] - result["correct"] - result["unanswered"]
    result["percent"] = round(result["correct"] * 100 / result["total"]) if result["total"] else 0
