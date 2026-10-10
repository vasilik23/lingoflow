"""Evaluate local aggregate beta evidence; never authorize a public release."""
import re
from datetime import date
from fractions import Fraction

POLICY = {"id": "closed-beta-v1", "minimum_days": 7, "minimum_participants": 20,
          "minimum_attempts": 50, "minimum_requests": 500,
          "completion_percent": 95, "server_error_percent": 0.5, "response_p95_ms": 2000,
          "maximum_age_days": 7}
MANUAL = ("iphone_audio", "mac_audio", "password_recovery", "account_deletion",
          "accessibility", "privacy_approved", "content_reviewed")


def _keys(value, expected):
    if not isinstance(value, dict) or set(value) != set(expected):
        raise ValueError("Invalid beta summary schema.")


def _counter(value):
    if value is not None and (type(value) is not int or not 0 <= value <= 10**9):
        raise ValueError("Invalid aggregate counter.")


def _day(value):
    if value is None:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Invalid observation window.")
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise ValueError("Invalid observation window.") from None


def readiness_report(summary, expected_commit, today=None):
    today = today or date.today()
    if not isinstance(expected_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", expected_commit):
        raise ValueError("Expected commit must be a full lowercase Git SHA.")
    _keys(summary, ("schema_version", "commit", "window", "participants", "journey", "runtime", "feedback", "manual"))
    if type(summary["schema_version"]) is not int or summary["schema_version"] != 1:
        raise ValueError("Unsupported beta summary version.")
    commit = summary["commit"]
    if commit is not None and (not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit)):
        raise ValueError("Invalid evidence commit.")
    _keys(summary["window"], ("start", "end"))
    start, end = (_day(summary["window"][key]) for key in ("start", "end"))
    if (start and end and start > end) or (end and end > today) or (start and start > today):
        raise ValueError("Invalid observation window.")
    _counter(summary["participants"])
    for section, keys in (("journey", ("started", "completed", "lost_results", "duplicate_results")),
                          ("runtime", ("requests", "server_errors", "response_p95_ms")),
                          ("feedback", ("open_blocking", "open_high"))):
        _keys(summary[section], keys)
        for value in summary[section].values():
            _counter(value)
    _keys(summary["manual"], MANUAL)
    if any(value is not None and type(value) is not bool for value in summary["manual"].values()):
        raise ValueError("Manual evidence must be true, false or null.")
    journey, runtime = summary["journey"], summary["runtime"]
    for section, denominator, numerators in ((journey, "started", ("completed", "lost_results", "duplicate_results")),
                                            (runtime, "requests", ("server_errors",))):
        for key in numerators:
            if section[key] is not None and section[denominator] is not None and section[key] > section[denominator]:
                raise ValueError("Inconsistent aggregate counters.")
    checks = []
    def check(identifier, status, observed=None, target=None):
        checks.append({"id": identifier, "status": status, "observed": observed, "target": target})
    def enough(identifier, value, target):
        check(identifier, "pass" if value is not None and value >= target else "insufficient_data", value, target)
    def zero(identifier, value):
        check(identifier, "insufficient_data" if value is None else "pass" if value == 0 else "fail", value, 0)
    check("commit", "insufficient_data" if commit is None else "pass" if commit == expected_commit else "fail", commit, expected_commit)
    days = (end - start).days + 1 if start and end else None
    fresh = end is not None and (today - end).days <= POLICY["maximum_age_days"]
    check("window", "pass" if days is not None and days >= POLICY["minimum_days"] and fresh else "insufficient_data",
          summary["window"], {"minimum_days": POLICY["minimum_days"], "maximum_age_days": POLICY["maximum_age_days"]})
    enough("participants", summary["participants"], POLICY["minimum_participants"])
    enough("lesson_attempts", journey["started"], POLICY["minimum_attempts"])
    enough("runtime_requests", runtime["requests"], POLICY["minimum_requests"])
    attempts, complete = journey["started"], journey["completed"]
    check("completion", "insufficient_data" if attempts is None or attempts < POLICY["minimum_attempts"] or complete is None else
          "pass" if complete * 100 >= attempts * POLICY["completion_percent"] else "fail",
          {"completed": complete, "started": attempts}, {"minimum_percent": POLICY["completion_percent"]})
    requests, errors = runtime["requests"], runtime["server_errors"]
    check("server_errors", "insufficient_data" if requests is None or requests < POLICY["minimum_requests"] or errors is None else
          "pass" if errors * 100 <= requests * Fraction(str(POLICY["server_error_percent"])) else "fail", {"errors": errors, "requests": requests}, {"maximum_percent": POLICY["server_error_percent"]})
    latency = runtime["response_p95_ms"]
    check("response_p95", "insufficient_data" if requests is None or requests < POLICY["minimum_requests"] or latency is None else
          "pass" if latency <= POLICY["response_p95_ms"] else "fail", latency, {"maximum_ms": POLICY["response_p95_ms"]})
    for key in ("lost_results", "duplicate_results"):
        zero(key, journey[key])
    for key in ("open_blocking", "open_high"):
        zero(key, summary["feedback"][key])
    for key in MANUAL:
        value = summary["manual"][key]
        check(key, "insufficient_data" if value is None else "pass" if value else "fail", value, True)
    statuses = {item["status"] for item in checks}
    return {"policy": dict(POLICY), "status": "blocked" if "fail" in statuses else "insufficient_data" if "insufficient_data" in statuses else "checks_passed",
            "release_authorized": False, "checks": checks,
            "limits": ["Operator-supplied aggregate evidence; the report does not verify its source.",
                       "Provisional beta thresholds do not establish CEFR validity, statistical confidence or release approval.",
                       "Response latency is not field INP. No telemetry is collected by this command."]}
