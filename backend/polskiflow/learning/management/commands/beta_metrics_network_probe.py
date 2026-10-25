import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from polskiflow.beta_metrics_network import probe, read_operator_key, read_qa_owner


class Command(BaseCommand):
    help = 'Bounded operator HTTPS probe; QA mode requires operator-verified temporary membership.'

    def add_arguments(self,parser):
        parser.add_argument('--release',required=True)
        parser.add_argument('--runs',type=int,default=5)
        parser.add_argument('--context',choices=['nonmember','qa'],default='nonmember')

    def handle(self,*args,**options):
        try:
            key = read_operator_key(settings.BASE_DIR / '.env.metrics-probe.local')
            owner=read_qa_owner(settings.BASE_DIR / '.env.qa-20261014.local') if options['context']=='qa' else None
            result = probe(key,options['release'],options['runs'],qa_owner=owner)
        except (OSError,ValueError,TypeError) as error:
            # No credential, raw request, response body or provider error text.
            raise CommandError('Network preflight unavailable: check the private key file and arguments.') from None
        self.stdout.write(json.dumps(result,sort_keys=True))
