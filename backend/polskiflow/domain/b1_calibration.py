"""Descriptive analysis of consented, pseudonymous B1 observations; no auto tuning."""
import csv
import math
import re
from collections import defaultdict
from statistics import median

from polskiflow.domain.b1_training_content import training_minutes, training_questions
from polskiflow.domain.b1_weekly_mock import VARIANTS

FIELDS = ('participant', 'content_version', 'variant_id', 'part_id', 'elapsed_seconds', 'outcome', 'correct', 'total')
PARTS = ('listening', 'reading', 'grammar', 'writing', 'speaking')


def read_observations(stream):
    reader = csv.DictReader(stream)
    if tuple(reader.fieldnames or ()) != FIELDS:
        raise ValueError('CSV header does not match the calibration schema.')
    observations, seen = [], set()
    variants = {v.id: v for v in VARIANTS}
    for line, row in enumerate(reader, 2):
        try:
            if None in row or any(value is None for value in row.values()):
                raise ValueError
            participant = row['participant']
            if not re.fullmatch(r'p\d{3,6}', participant):
                raise ValueError
            version = int(row['content_version'])
            part, variant_id, outcome = row['part_id'], row['variant_id'], row['outcome']
            if version not in range(1, 11) or part not in PARTS or variant_id not in variants or outcome not in {'completed', 'timed_out', 'skipped'}:
                raise ValueError
            seconds = int(row['elapsed_seconds'])
            budget = training_minutes(version, part) * 60
            if not 0 <= seconds <= 14400 or (outcome == 'completed' and not 0 < seconds <= budget) or (outcome == 'timed_out' and seconds < budget):
                raise ValueError
            key = (participant, version, variant_id, part)
            if key in seen:
                raise ValueError
            correct = total = None
            if part in {'listening', 'reading', 'grammar'} and outcome == 'completed':
                correct, total = int(row['correct']), int(row['total'])
                expected = len(training_questions(variants[variant_id], part, version))
                if total != expected or not 0 <= correct <= total:
                    raise ValueError
            elif row['correct'] or row['total']:
                raise ValueError  # Do not invent scores for production or incomplete sections.
            seen.add(key)
            observations.append(dict(participant=participant, version=version, variant=variant_id,
                                     part=part, seconds=seconds, budget=budget, outcome=outcome,
                                     correct=correct, total=total))
        except (ValueError, TypeError, KeyError):
            raise ValueError(f'Invalid observation at CSV line {line}.') from None
    return observations


def calibration_report(observations, minimum_participants=10):
    if minimum_participants < 2:
        raise ValueError('At least two participants are required for the reporting threshold.')
    grouped = defaultdict(list)
    for row in observations:
        grouped[row['version'], row['variant'], row['part']].append(row)
    groups = []
    for (version, variant, part), rows in sorted(grouped.items()):
        attempted = [r for r in rows if r['outcome'] != 'skipped']
        completed = [r for r in attempted if r['outcome'] == 'completed']
        durations = sorted(r['seconds'] for r in completed)
        scores = [r['correct'] / r['total'] * 100 for r in completed if r['total']]
        participants = len({r['participant'] for r in attempted})
        groups.append(dict(content_version=version, variant_id=variant, part_id=part,
                           budget_seconds=training_minutes(version, part) * 60,
                           participants=participants, completed=len(completed),
                           timed_out=len(attempted) - len(completed), skipped=len(rows) - len(attempted),
                           completion_rate=round(len(completed) / len(attempted), 3) if attempted else None,
                           completed_duration_median=median(durations) if durations else None,
                           completed_duration_p90=durations[math.ceil(.9 * len(durations)) - 1] if durations else None,
                           completed_score_median=round(median(scores), 1) if scores else None,
                           status='needs_editorial_review' if participants >= minimum_participants else 'insufficient_observations'))
    return dict(format='b1-calibration-v1', minimum_participants=minimum_participants,
                automatic_limit_changes=False, groups=groups,
                limitations=[
                    'Descriptive observations only; thresholds do not establish statistical power or CEFR/exam validity.',
                    'Duration percentiles include completed attempts only and exclude timeouts; inspect both together.',
                    'Skipped parts do not count as attempts. Repeated participant/version/variant/part rows are rejected.',
                    'Input requires consent and pseudonyms. Output omits participant identifiers and individual rows.',
                    'Writing and speaking never receive automatic scores. No scores are inferred for incomplete parts.',
                ])
