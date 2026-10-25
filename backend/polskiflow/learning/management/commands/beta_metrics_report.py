import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from polskiflow.beta_metrics_report import summarize


class Command(BaseCommand):
    help = 'Summarize a private.beta_report JSON snapshot; no network or database writes.'

    def add_arguments(self, parser):
        parser.add_argument('--input', required=True)

    def handle(self, *args, **options):
        try:
            path = Path(options['input'])
            if path.stat().st_size > 5 * 1024 * 1024:
                raise ValueError('Snapshot exceeds 5 MiB')
            result = summarize(json.loads(path.read_text()))
        except (OSError, ValueError, TypeError, KeyError) as error:
            raise CommandError('Invalid metrics snapshot') from error
        self.stdout.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
