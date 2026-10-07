"""Analyze a local consented CSV without uploading observations or changing limits."""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from polskiflow.domain.b1_calibration import read_observations, calibration_report


class Command(BaseCommand):
    help = 'Print aggregate B1 calibration statistics from a local pseudonymous CSV.'

    def add_arguments(self, parser):
        parser.add_argument('input', type=Path)
        parser.add_argument('--minimum-participants', type=int, default=10)

    def handle(self, *args, **options):
        try:
            with options['input'].open(encoding='utf-8-sig', newline='') as source:
                observations = read_observations(source)
            report = calibration_report(observations, options['minimum_participants'])
        except OSError:
            raise CommandError('Cannot read the local calibration CSV.') from None
        except (ValueError, UnicodeError) as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
