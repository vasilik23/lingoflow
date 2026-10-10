"""Run the read-only production synthetic smoke from an operator shell."""

import os
from contextlib import nullcontext

from django.core.management.base import BaseCommand, CommandError

from polskiflow.domain.synthetic_smoke import SmokeFailure, run_synthetic_smoke
from polskiflow.domain.smoke_session import fresh_smoke_session


class Command(BaseCommand):
    help = "Check public probes and the authenticated mobile cold-start path without writes"

    def add_arguments(self, parser):
        parser.add_argument("base_url", help="Production or Preview HTTPS origin")
        parser.add_argument(
            "--token-env",
            default="POLSKIFLOW_SMOKE_ACCESS_TOKEN",
            help="Environment variable containing a short-lived learner access token",
        )
        parser.add_argument("--fresh-session", action="store_true",
                            help="Use an ephemeral dedicated production learner session")
        parser.add_argument("--timeout", type=float, default=10)
        parser.add_argument(
            "--public-only",
            action="store_true",
            help="Check public contracts without a learner token",
        )

    def handle(self, *args, **options):
        public_only = options["public_only"]
        fresh = options["fresh_session"]
        if fresh and public_only:
            raise CommandError("fresh-session and public-only cannot be combined")
        token = os.environ.get(options["token_env"], "") if not public_only and not fresh else ""
        if not public_only and not fresh and not token:
            raise CommandError(f"Missing access token in {options['token_env']}")
        try:
            session = fresh_smoke_session(options["base_url"]) if fresh else nullcontext(token)
            with session as access_token:
                results = run_synthetic_smoke(
                    options["base_url"], access_token, timeout=options["timeout"],
                    include_private=not public_only,
                )
        except SmokeFailure as error:
            raise CommandError(str(error)) from error
        for result in results:
            self.stdout.write(f"PASS {result.name} status={result.status} request_id={result.request_id}")
        self.stdout.write(self.style.SUCCESS(f"Synthetic smoke passed ({len(results)} checks)"))
