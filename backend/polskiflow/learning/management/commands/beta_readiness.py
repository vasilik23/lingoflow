"""Read aggregate local beta evidence without database or provider access."""
import json
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from polskiflow.domain.beta_readiness import readiness_report


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate summary fields.")
        result[key] = value
    return result


class Command(BaseCommand):
    help = "Evaluate local aggregate beta evidence against provisional release criteria."

    def add_arguments(self, parser):
        parser.add_argument("input", type=Path)
        parser.add_argument("--expected-commit", required=True)
        parser.add_argument("--check", action="store_true", help="Exit nonzero for blockers or insufficient evidence.")

    def handle(self, *args, **options):
        try:
            with options["input"].open("rb") as source:
                raw = source.read(16385)
            if len(raw) > 16384:
                raise ValueError("Beta summary exceeds 16 KiB.")
            summary = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)
            report = readiness_report(summary, options["expected_commit"])
        except OSError:
            raise CommandError("Cannot read the local beta summary.") from None
        except (ValueError, UnicodeError):
            # Never echo raw input, unknown fields, participant details or text.
            raise CommandError("Invalid beta summary. Use the documented aggregate schema.") from None
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
        if options["check"] and report["status"] != "checks_passed":
            raise CommandError("Beta criteria are not satisfied: " + report["status"])
