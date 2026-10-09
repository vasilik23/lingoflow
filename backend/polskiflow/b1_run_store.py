"""Owner-scoped aggregate run history, excluding responses, essays and audio."""
import json
from datetime import datetime, timezone, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from django.conf import settings
from django.utils import timezone as django_timezone
from polskiflow.b1_mock_store import _configured, _request, ATTEMPT_LABELS
from polskiflow.domain.b1_exam_simulation import B1_SIMULATION_PARTS


def aggregate_results(results):
    if not isinstance(results, list) or len(results) != 5:
        raise ValueError("Incomplete run")
    aggregates = []
    for part, result in zip(B1_SIMULATION_PARTS, results):
        if not isinstance(result, dict) or result.get("id") != part["id"]:
            raise ValueError("Unexpected part")
        status = result.get("status")
        if status not in (("scored", "skipped") if part["mode"] == "objective" else ("self_review", "skipped")):
            raise ValueError("Unexpected status")
        timed_out = result.get("timed_out")
        if timed_out is not None and type(timed_out) is not bool:
            raise ValueError("Unexpected timing")
        row = {"id": part["id"], "status": status, "timed_out": timed_out}
        if status == "scored":
            correct, total = result["correct"], result["total"]
            unanswered = result.get("unanswered", 0)
            incorrect = result.get("incorrect", total - correct - unanswered)
            values = (correct, total, unanswered, incorrect)
            if any(type(n) is not int for n in values) or not 1 <= total <= 64 or min(values) < 0 or correct + unanswered + incorrect != total:
                raise ValueError("Invalid aggregate")
            row.update(correct=correct, total=total, incorrect=incorrect, unanswered=unanswered)
        aggregates.append(row)
    return aggregates


def save_b1_run_attempt(token, user_id, state):
    if not _configured(token) or state.get("phase") != "report" or state.get("user_id") != user_id:
        return False
    try:
        payload = {
            "user_id": user_id, "run_id": state["run_id"], "variant_id": state["variant_id"],
            "content_version": state.get("content_version", 1),
            "started_at": datetime.fromtimestamp(state.get("started_at", state["created_at"]), timezone.utc).isoformat(),
            "finished_at": datetime.fromtimestamp(state["finished_at"], timezone.utc).isoformat(),
            "results": aggregate_results(state["results"]),
        }
        with urlopen(_request("b1_run_attempts?on_conflict=user_id%2Crun_id", token, "POST", payload, ignore_duplicates=True), timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            return response.status in (200, 201, 204)
    except (HTTPError, URLError, TimeoutError, KeyError, TypeError, ValueError, OverflowError):
        return False


def load_b1_run_attempts(token, user_id, *, days=None):
    if not _configured(token):
        return []
    query = {"select": "run_id,variant_id,content_version,started_at,finished_at,results", "user_id": f"eq.{user_id}", "order": "finished_at.desc,run_id.desc", "limit": "12"}
    if days is not None:
        query["finished_at"] = "gte." + (django_timezone.now() - timedelta(days=days)).isoformat()
    try:
        with urlopen(_request("b1_run_attempts?" + urlencode(query), token), timeout=settings.SUPABASE_AUTH_TIMEOUT) as response:
            rows = json.load(response)
        if not isinstance(rows, list):
            return None
        history = []
        for row in rows:
            try:
                aggregates = aggregate_results(row["results"])
                date = datetime.fromisoformat(row["finished_at"].replace("Z", "+00:00"))
                history.append({**row, "variant_label": ATTEMPT_LABELS.get(row["variant_id"], "Версия задания"), "date_display": django_timezone.localtime(date).strftime("%d.%m.%Y %H:%M"), "parts": tuple({**part, **result} for part, result in zip(B1_SIMULATION_PARTS, aggregates))})
            except (KeyError, TypeError, ValueError, AttributeError):
                continue
        return history
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None
