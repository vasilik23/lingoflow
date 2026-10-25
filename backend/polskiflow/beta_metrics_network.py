"""Operator-only HTTPS preflight; no enrollment and no learning-result writes."""

import base64
import json
import math
import os
import stat
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from polskiflow.beta_metrics import service_headers


RPC_URL = 'https://habcghygjaynknkcbirz.supabase.co/rest/v1/rpc/beta_collect_request'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def read_operator_key(path):
    """Read one private local variable; never echo a malformed secret."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'r', encoding='utf-8') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077 or info.st_size > 8192):
            raise ValueError('Use an owner-only regular file')
        values = []
        for line in stream:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            name, separator, value = line.partition('=')
            if not separator or name.strip() != 'BETA_METRICS_SERVICE_KEY':
                raise ValueError('Unexpected configuration')
            values.append(value.strip().strip('"\''))
    if len(values) != 1 or not values[0] or any(c.isspace() for c in values[0]):
        raise ValueError('Server key required')
    key = values[0]
    if key.startswith('sb_secret_') and len(key) > len('sb_secret_'):
        return key
    try:
        encoded = key.split('.')[1]
        claims = json.loads(base64.urlsafe_b64decode(encoded + '=' * (-len(encoded) % 4)))
        if len(key.split('.')) == 3 and isinstance(claims, dict) and claims.get('role') == 'service_role':
            return key
    except (ValueError, IndexError, TypeError):
        pass
    raise ValueError('A secret key or legacy service-role key is required')


def read_qa_owner(path):
    """Only an existing QA identity; no CLI argument for arbitrary learners."""
    fd=os.open(path,os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd,'r',encoding='utf-8') as stream:
        info=os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)&0o077 or info.st_size>16384:
            raise ValueError('Private QA file required')
        owners=[]
        for line in stream:
            name,separator,value=line.strip().partition('=')
            if separator and name=='QA_USER_ID':
                owners.append(value.strip().strip('"\''))
    if len(owners)!=1:
        raise ValueError('QA identity required')
    owner=uuid.UUID(owners[0])
    if owner.int==0:
        raise ValueError('QA identity required')
    return str(owner)


def probe(key, release, runs=5, *, qa_owner=None, opener=None, clock=time.perf_counter):
    if not isinstance(release,str) or len(release) != 40 or any(c not in '0123456789abcdef' for c in release):
        raise ValueError('Full release SHA required')
    if type(runs) is not int or not 2 <= runs <= 10:
        raise ValueError('Use 2..10 requests')
    owner=str(uuid.UUID(qa_owner)) if qa_owner is not None else '00000000-0000-0000-0000-000000000000'
    if qa_owner is not None and uuid.UUID(owner).int==0:
        raise ValueError('QA identity required')
    opener = opener or build_opener(NoRedirect())
    samples = []
    for _ in range(runs):
        # This UUID is a non-account sentinel. Operator must first verify that
        # it is not enrolled. NULL is authenticated no-op, not transport failure.
        payload = dict(p_owner=owner,
                       p_request=str(uuid.uuid4()),p_release=release,
                       p_route='today',p_method='GET',p_status=200,p_duration=0)
        request = Request(RPC_URL,data=json.dumps(payload).encode(),method='POST',headers=service_headers(key))
        started = clock()
        status, error = None, None
        try:
            with opener.open(request,timeout=1) as response:
                status = response.status
                raw = response.read(1025)
                expected={'attempt_id':None,'finished_at':None} if qa_owner is not None else None
                if status != 200 or len(raw) > 1024 or json.loads(raw) != expected:
                    error = 'unexpected_response'
        except HTTPError as response:
            status, error = response.code, 'http'
            response.close()
        except (URLError, TimeoutError, OSError):
            error = 'transport'
        except (ValueError, TypeError):
            error = 'unexpected_response'
        samples.append(dict(status=status,error=error,elapsed_ms=math.ceil((clock()-started)*1000)))
        # An authenticated non-NULL response could indicate unexpected state;
        # stop instead of continuing to issue potentially mutating calls.
        if error == 'unexpected_response':
            break
    successful = sorted(s['elapsed_ms'] for s in samples if s['status']==200 and s['error'] is None)
    percentile = lambda p: successful[math.ceil(len(successful)*p)-1] if successful else None
    return dict(schema_version=1,kind='operator_https_rpc_preflight',origin='operator_machine',
                release=release,latency_scope='https_qa_observation' if qa_owner else 'https_nonmember_short_circuit',
                diagnostic_writes_expected=qa_owner is not None,vercel_to_supabase_ms=None,
                lesson_reserve_finish_cost_ms=None,
                beta_readiness_evidence=False,enrollment_performed=False,
                requested_runs=runs,samples=samples,successful=len(successful),
                p50_ms=percentile(.5),p95_ms=percentile(.95))
