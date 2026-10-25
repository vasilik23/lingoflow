"""Aggregate only received observations; never manufacture readiness evidence."""

import math
import re
from collections import Counter
from datetime import datetime


def summarize(snapshot):
    if not isinstance(snapshot, dict) or snapshot.get('schema_version') != 1:
        raise ValueError('Unsupported metrics schema')
    if snapshot.get('coverage') != 'best_effort_received_only':
        raise ValueError('Missing coverage declaration')
    if snapshot.get('latency_scope') != 'django_app_before_collector':
        raise ValueError('Unsupported latency scope')
    bounds = []
    for field in ('since','until'):
        try:
            value = datetime.fromisoformat(snapshot[field].replace('Z','+00:00'))
            if value.tzinfo is None:
                raise ValueError('Timezone required')
            bounds.append(value)
        except (KeyError, AttributeError, TypeError) as error:
            raise ValueError('Invalid observation window') from error
    if bounds[0] >= bounds[1]:
        raise ValueError('Invalid observation window')
    groups = {}
    for row in snapshot.get('requests', []):
        if set(row) != {'cohort', 'release_sha', 'route_group', 'method', 'status', 'app_ms', 'count'}:
            raise ValueError('Invalid aggregate dimensions')
        if (not isinstance(row['cohort'], str) or not re.fullmatch(r'[a-z0-9-]{1,40}', row['cohort'])
                or not isinstance(row['release_sha'], str) or not re.fullmatch(r'[0-9a-f]{40}', row['release_sha'])
                or row['route_group'] not in {'today','lesson','result'} or row['method'] not in {'GET','POST'}):
            raise ValueError('Invalid aggregate dimensions')
        for field in ('status','app_ms','count'):
            if type(row[field]) is not int:
                raise ValueError('Integer frequency required')
        if not 100 <= row['status'] <= 599 or row['app_ms'] < 0 or row['count'] <= 0:
            raise ValueError('Invalid frequency')
        key = (row['cohort'], row['release_sha'], row['route_group'], row['method'], row['status'])
        groups.setdefault(key, Counter())[row['app_ms']] += row['count']
    output = []
    for key, histogram in sorted(groups.items()):
        count = sum(histogram.values())
        rank, cumulative, p95 = math.ceil(count * .95), 0, None
        for duration, frequency in sorted(histogram.items()):
            cumulative += frequency
            if cumulative >= rank:
                p95 = duration
                break
        output.append(dict(zip(('cohort','release_sha','route_group','method','status'),key),
                           count=count, app_p95_ms=p95))
    # Do not copy arbitrary input fields/IDs into the operator's final output.
    attempts = []
    for row in snapshot.get('attempts', []):
        fields = {'cohort','release_sha','started','finish_requested','saved','pending_confirmation'}
        if set(row) != fields or any(type(row[f]) is not int or row[f] < 0 for f in fields-{'cohort','release_sha'}):
            raise ValueError('Invalid attempt aggregates')
        if (not isinstance(row['cohort'], str) or not re.fullmatch(r'[a-z0-9-]{1,40}',row['cohort'])
                or not isinstance(row['release_sha'], str) or not re.fullmatch(r'[0-9a-f]{40}',row['release_sha'])):
            raise ValueError('Invalid attempt dimensions')
        attempts.append(row)
    return {'schema_version':1, 'latency_scope':'django_app_before_collector',
            'since':bounds[0].isoformat(), 'until':bounds[1].isoformat(),
            'coverage':'best_effort_received_only', 'beta_readiness_evidence':False,
            'end_to_end_ms':None, 'field_inp_ms':None, 'lost_results':None,
            'duplicates':None, 'requests':output, 'attempts':attempts}
