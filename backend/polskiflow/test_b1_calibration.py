import csv
import json
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from polskiflow.domain.b1_calibration import FIELDS, read_observations, calibration_report


class CalibrationTests(SimpleTestCase):
    def csv(self, rows):
        stream = StringIO()
        writer = csv.writer(stream)
        writer.writerow(FIELDS)
        writer.writerows(rows)
        stream.seek(0)
        return stream

    def row(self, participant='p001', version=9, seconds=100, outcome='completed', correct=20, total=30):
        return [participant, version, 'b1-weekly-v1', 'reading', seconds, outcome, correct, total]

    def test_report_separates_versions_handles_timeouts_and_omits_identifiers(self):
        rows = [self.row('p001', seconds=100), self.row('p002', seconds=200),
                self.row('p003', seconds=2700, outcome='timed_out', correct='', total=''),
                self.row('p004', seconds=0, outcome='skipped', correct='', total=''),
                self.row('p001', version=7, seconds=300, correct=15, total=20)]
        report = calibration_report(read_observations(self.csv(rows)), minimum_participants=3)
        old, current = report['groups']
        self.assertEqual(old['budget_seconds'], 1320)
        self.assertEqual(current['budget_seconds'], 2700)
        self.assertEqual(current['participants'], 3)
        self.assertEqual((current['completed'], current['timed_out'], current['skipped']), (2, 1, 1))
        self.assertEqual(current['completion_rate'], .667)
        self.assertEqual(current['completed_duration_median'], 150)
        self.assertEqual(current['completed_duration_p90'], 200)
        self.assertEqual(current['status'], 'needs_editorial_review')
        self.assertEqual(old['status'], 'insufficient_observations')
        self.assertFalse(report['automatic_limit_changes'])
        self.assertNotIn('p001', json.dumps(report))

    def test_skips_do_not_satisfy_threshold_and_production_has_no_score(self):
        row = ['p002', 9, 'b1-weekly-v1', 'writing', 500, 'completed', '', '']
        report = calibration_report(read_observations(self.csv([self.row(outcome='skipped', correct='', total=''), row])))
        reading, writing = report['groups']
        self.assertIsNone(reading['completion_rate'])
        self.assertIsNone(reading['completed_duration_p90'])
        self.assertEqual(reading['participants'], 0)
        self.assertIsNone(writing['completed_score_median'])
        self.assertEqual(writing['status'], 'insufficient_observations')

    def test_invalid_rows_and_duplicates_fail_without_echoing_input(self):
        invalid = [self.row(participant='private@example.org'), self.row(version=11),
                   self.row(seconds=2701), self.row(seconds=-1), self.row(total=20),
                   self.row(correct=31), self.row(outcome='timed_out', seconds=100, correct='', total='')]
        for row in invalid:
            with self.assertRaisesRegex(ValueError, 'Invalid observation at CSV line 2'):
                read_observations(self.csv([row]))
        with self.assertRaisesRegex(ValueError, 'line 3'):
            read_observations(self.csv([self.row(), self.row()]))
        with self.assertRaises(ValueError):
            read_observations(StringIO('email,elapsed_seconds\nprivate@example.org,10\n'))
        with self.assertRaises(ValueError):
            calibration_report([], 1)

    def test_command_reports_local_file_and_safe_errors(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'observations.csv'
            path.write_text(self.csv([self.row()]).getvalue())
            output = StringIO()
            call_command('b1_calibration_report', str(path), stdout=output)
            report = json.loads(output.getvalue())
            self.assertEqual(len(report['groups']), 1)
            self.assertNotIn(str(path), output.getvalue())
            with self.assertRaises(CommandError):
                call_command('b1_calibration_report', str(path), minimum_participants=1, stdout=StringIO())
            with self.assertRaisesRegex(CommandError, 'Cannot read the local calibration CSV'):
                call_command('b1_calibration_report', str(path.parent / 'missing.csv'))

    def test_coverage_exposes_missing_skipped_and_underrepresented_cells(self):
        rows = [self.row('p001'), self.row('p002'),
                self.row('p003', version=7, correct=15, total=20),
                ['p001', 9, 'b1-weekly-v2', 'speaking', 0, 'skipped', '', '']]
        report = calibration_report(read_observations(self.csv(rows)), 2)
        old, current = report['coverage']
        self.assertEqual([old['content_version'], current['content_version']], [7, 9])
        self.assertEqual(current['expected_groups'], 15)
        self.assertEqual(current['groups_at_threshold'], 1)
        self.assertEqual(current['status'], 'incomplete_coverage')
        cells = {(c['variant_id'], c['part_id']): c for c in current['cells']}
        self.assertEqual(cells['b1-weekly-v1', 'reading']['additional_participants'], 0)
        self.assertEqual(cells['b1-weekly-v2', 'speaking']['status'], 'insufficient_observations')
        self.assertEqual(cells['b1-weekly-v2', 'speaking']['additional_participants'], 2)
        self.assertEqual(cells['b1-weekly-v3', 'grammar']['status'], 'missing_observations')
        self.assertEqual(old['groups_at_threshold'], 0)
        self.assertNotIn('p001', json.dumps(report))
        self.assertEqual(calibration_report([])['coverage'], [])

    def test_full_coverage_requires_every_cell_and_remains_editorial_review(self):
        from polskiflow.domain.b1_calibration import PARTS
        from polskiflow.domain.b1_training_content import training_questions
        from polskiflow.domain.b1_weekly_mock import VARIANTS
        rows = []
        for variant in VARIANTS:
            for part in PARTS:
                total = len(training_questions(variant, part, 9)) if part in {'reading', 'grammar', 'listening'} else ''
                for participant in ('p001', 'p002'):
                    rows.append([participant, 9, variant.id, part, 60, 'completed', total, total])
        report = calibration_report(read_observations(self.csv(rows)), 2)
        coverage = report['coverage'][0]
        self.assertEqual(coverage['groups_at_threshold'], 15)
        self.assertEqual(coverage['status'], 'needs_editorial_review')
        self.assertFalse(report['automatic_limit_changes'])
