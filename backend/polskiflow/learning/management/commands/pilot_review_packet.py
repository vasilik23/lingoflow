"""Export the three existing pilots without reading learner data or publishing."""
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError
from polskiflow.pilot_review import ReviewPacketError, build_packet, write_packet


class Command(BaseCommand):
    help = 'Export a read-only RU/PL/EN editorial packet for the three published pilot definitions.'

    def add_arguments(self, parser):
        parser.add_argument('--source-commit', required=True)
        parser.add_argument('--output-directory', required=True)

    def handle(self, *args, **options):
        try:
            artifacts = build_packet(options['source_commit'])
            write_packet(artifacts, options['output_directory'])
        except (ReviewPacketError, OSError, DatabaseError) as error:
            if isinstance(error, ReviewPacketError):
                raise CommandError(str(error)) from None
            if isinstance(error, DatabaseError):
                raise CommandError('Content database unavailable; no packet was completed.') from None
            raise CommandError('Cannot write the packet; check the external output directory.') from None
        self.stdout.write('Exported 3 pilots, 15 lessons and RU/PL/EN review pages. Review status: not_reviewed; release_authorized=false.')
