"""Disposable lab: Django test client -> loopback RPC bridge -> PostgreSQL.

Not a production probe. Requires an empty fixture database at 127.0.0.1:55440
with supabase/tests/beta_metrics_fixture.sql and metrics migrations applied.
Input SQLite is copied; no original course file is modified. No real credentials.
"""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
os.environ.update(DJANGO_SETTINGS_MODULE='polskiflow.settings', DJANGO_DEBUG='true',
                  SUPABASE_URL='', SUPABASE_ANON_KEY='', ACCOUNT_ACTIVITY_ENABLED='false',
                  DJANGO_SECURE_SSL_REDIRECT='false', BETA_METRICS_ENABLED='false')
os.environ.pop('DATABASE_URL', None)
import django
import psycopg

django.setup()
from django.conf import settings
from django.test import Client, override_settings
from polskiflow.auth import ACCESS_COOKIE, SupabaseUser
from polskiflow.content import flashcards
from polskiflow.domain.lesson_state import load_lesson_state, sign_lesson_state
from polskiflow.progress_store import CompletionSaveResult, DashboardProgress
from polskiflow.beta_metrics_report import summarize

DSN = 'host=127.0.0.1 port=55440 user=postgres dbname=postgres connect_timeout=3'
CALLS = {
    'beta_reserve_attempt': ['p_owner','p_lesson','p_release'],
    'beta_finish_attempt': ['p_owner','p_attempt','p_release'],
    'beta_observe_request': ['p_owner','p_request','p_release','p_route','p_method','p_status',
                            'p_duration','p_attempt','p_finished','p_saved','p_total','p_known'],
}


def sql(query, args=()):
    with psycopg.connect(DSN, autocommit=True) as connection:
        return connection.execute(query, args).fetchone()


class Bridge(BaseHTTPRequestHandler):
    delay = 0
    calls = 0

    def log_message(self, *args):
        pass

    def do_POST(self):
        name = self.path.removeprefix('/rest/v1/rpc/')
        if name not in CALLS or self.headers.get('apikey') != 'local-fixture-not-a-secret':
            self.send_error(403)
            return
        try:
            data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            fields = CALLS[name]
            if set(data) != set(fields):
                raise ValueError('Unexpected fields')
            time.sleep(self.delay)
            with psycopg.connect(DSN, autocommit=True) as connection:
                connection.execute('set role service_role')
                value = connection.execute('select public.' + name + '(' + ','.join(['%s']*len(fields)) + ')',
                                           [data[field] for field in fields]).fetchone()[0]
            Bridge.calls += 1
            body = json.dumps(value, default=str).encode()
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception:
            self.send_error(500, 'Fixture RPC failed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content-db', required=True)
    parser.add_argument('--pairs', type=int, default=10)
    args = parser.parse_args()
    if not 5 <= args.pairs <= 30:
        parser.error('Use 5..30 pairs')
    source = Path(args.content_db).resolve()
    if not str(source).startswith('/private/tmp/'):
        parser.error('Use a disposable course fixture under /private/tmp')
    if sql('select count(*) from private.beta_members')[0] != 0:
        raise RuntimeError('Lab requires empty diagnostic membership')
    owner = str(uuid4())
    server = ThreadingHTTPServer(('127.0.0.1',0),Bridge)
    thread = threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    with tempfile.TemporaryDirectory(prefix='lf-metrics-lab-') as directory, ExitStack() as stack:
        stack.callback(server.server_close)
        stack.callback(server.shutdown)
        def cleanup():
            with psycopg.connect(DSN,autocommit=True) as connection:
                connection.execute('delete from private.beta_requests where cohort=%s',('operator-lab',))
                connection.execute('delete from private.beta_members where user_id=%s',(owner,))
                connection.execute('delete from public.lesson_completions where user_id=%s',(owner,))
                connection.execute('delete from auth.users where id=%s',(owner,))
        stack.callback(cleanup)
        target = Path(directory)/'content.sqlite3'
        shutil.copyfile(source,target)
        settings.DATABASES['default']['NAME'] = str(target)
        sql('insert into auth.users(id) values(%s) returning id',(owner,))
        sql("insert into private.beta_members(user_id,cohort,expires_at) values(%s,'operator-lab',now()+interval '1 hour') returning user_id",(owner,))
        # Only this fixture is touched. Learning writes use real local PostgreSQL.
        with psycopg.connect(DSN,autocommit=True) as connection:
            connection.execute('create unique index if not exists lab_completion_key on public.lesson_completions(user_id,lesson_id,plan_date)')
        def save(token,user,lesson,total,known):
            sql("insert into public.lesson_completions values(%s,%s,(now() at time zone 'UTC')::date,%s,%s) on conflict(user_id,lesson_id,plan_date) do update set cards_total=excluded.cards_total,cards_known=excluded.cards_known returning user_id",(user,lesson,total,known))
            return CompletionSaveResult(True,False)

        stack.enter_context(patch('polskiflow.auth.authenticate_access_token',return_value=SupabaseUser(owner,'fixture@example.test')))
        stack.enter_context(patch('polskiflow.auth_views.load_dashboard_progress',return_value=DashboardProgress('Fixture','A1',0,frozenset(),True)))
        stack.enter_context(patch('polskiflow.lesson_views.save_lesson_completion_result',side_effect=save))
        client = Client()
        client.cookies[ACCESS_COOKIE] = 'fixture-access'
        total = len(flashcards('words'))
        assert total > 0
        rows = []
        expected_requests = 0
        expected_attempts = 0
        for delay in [0,.05]:
            Bridge.delay = delay
            for pair in range(-2 if delay == 0 else 0,args.pairs):
                for enabled in ([False,True] if pair%2==0 else [True,False]):
                    with override_settings(BETA_METRICS_ENABLED=enabled,BETA_METRICS_SERVICE_KEY='local-fixture-not-a-secret',
                                           BETA_METRICS_RELEASE='a'*40,SUPABASE_URL=f'http://127.0.0.1:{server.server_port}',
                                           SUPABASE_ANON_KEY='',ALLOWED_HOSTS=['testserver'],SECURE_SSL_REDIRECT=False):
                        actions = []
                        for route in ['/','/lesson/words/']:
                            start = time.perf_counter()
                            response = client.get(route)
                            assert response.status_code == 200
                            actions.append((route,(time.perf_counter()-start)*1000))
                        import re
                        from html import unescape
                        token = unescape(re.search(r'name="state" value="([^"]+)"',response.content.decode())[1])
                        state = load_lesson_state(token,owner,'words','words')
                        start = time.perf_counter()
                        response = client.post('/lesson/words/step/',{'action':'reveal','state':token})
                        assert response.status_code == 200
                        actions.append(('reveal',(time.perf_counter()-start)*1000))
                        final = sign_lesson_state(owner,'words','words',total-1,total-1,attempt_id=state.attempt_id)
                        start = time.perf_counter()
                        response = client.post('/lesson/words/step/',{'action':'know','state':final})
                        assert response.status_code == 200
                        actions.append(('finish',(time.perf_counter()-start)*1000))
                        if enabled and pair >= 0:
                            expected_requests += 4
                            expected_attempts += 1
                        if pair >= 0:
                            rows.extend({'delay_ms':round(delay*1000),'enabled':enabled,'action':action,'ms':round(ms,3)} for action,ms in actions)
                if pair == -1:
                    with psycopg.connect(DSN,autocommit=True) as connection:
                        connection.execute('delete from private.beta_requests where cohort=%s',('operator-lab',))
                        connection.execute('delete from private.beta_attempts where user_id=%s',(owner,))
        snapshot = sql("select private.beta_report(now()-interval '1 hour',clock_timestamp()+interval '1 second')")[0]
        report = summarize(snapshot)
        received = sum(row['count'] for row in report['requests'])
        attempts = report['attempts'][0]
        assert received == expected_requests, (received,expected_requests)
        assert attempts['started'] == expected_attempts
        assert attempts['finish_requested'] == expected_attempts
        assert attempts['saved'] == expected_attempts
        assert attempts['pending_confirmation'] == 0
        summary = []
        for delay in [0,50]:
            for action in ['/','/lesson/words/','reveal','finish']:
                item={'delay_ms':delay,'action':action,'n_per_mode':args.pairs}
                for enabled,label in [(False,'off'),(True,'on')]:
                    values=sorted(row['ms'] for row in rows if row['delay_ms']==delay and row['action']==action and row['enabled']==enabled)
                    item[label+'_p50_ms']=values[math.ceil(len(values)*.5)-1]
                    item[label+'_p95_ms']=values[math.ceil(len(values)*.95)-1]
                summary.append(item)
        print(json.dumps({'kind':'local_django_client_http_postgres_lab','not_production_latency':True,
                          'requests_expected':expected_requests,'requests_received':received,
                          'attempts_expected':expected_attempts,'attempts':attempts,
                          'rpc_calls':Bridge.calls,'timings':summary},sort_keys=True))


if __name__ == '__main__':
    main()
