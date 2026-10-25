import base64
import json
import os
from pathlib import Path
import tempfile
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from polskiflow.beta_metrics import rpc, service_headers
from polskiflow.beta_metrics_network import NoRedirect, RPC_URL, probe, read_operator_key, read_qa_owner


class MetricsServiceKeyTests(SimpleTestCase):
    def test_secret_api_key_is_not_sent_as_a_bearer_jwt(self):
        headers=service_headers('sb_secret_test_only')
        self.assertEqual(headers['apikey'],'sb_secret_test_only')
        self.assertNotIn('Authorization',headers)

    def test_legacy_key_keeps_bearer_compatibility(self):
        self.assertEqual(service_headers('fixture-legacy')['Authorization'],'Bearer fixture-legacy')

    @override_settings(BETA_METRICS_ENABLED=True,BETA_METRICS_SERVICE_KEY='sb_secret_test_only',
                       BETA_METRICS_RELEASE='a'*40,SUPABASE_URL='https://project.test')
    @patch('polskiflow.beta_metrics.urlopen')
    def test_actual_collector_uses_shared_secret_headers(self, opened):
        opened.return_value.__enter__.return_value.read.return_value=b'null'
        self.assertIsNone(rpc('beta_collect_request',{}))
        request=opened.call_args.args[0]
        self.assertEqual(request.get_header('Apikey'),'sb_secret_test_only')
        self.assertIsNone(request.get_header('Authorization'))


class MetricsPrivateKeyFileTests(SimpleTestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path=Path(directory.name)/'key.env'

    def write(self,text):
        self.path.write_text(text)
        self.path.chmod(0o600)

    def test_reads_secret_key_without_evaluating_shell(self):
        self.write('# ignored comment\nBETA_METRICS_SERVICE_KEY="sb_secret_test_only"\n')
        self.assertEqual(read_operator_key(self.path),'sb_secret_test_only')

    def test_legacy_service_role_format_is_checked_but_not_trusted_as_auth(self):
        encoded=base64.urlsafe_b64encode(json.dumps({'role':'service_role'}).encode()).decode().rstrip('=')
        key='header.'+encoded+'.signature'
        self.write('BETA_METRICS_SERVICE_KEY='+key)
        self.assertEqual(read_operator_key(self.path),key)

    def test_empty_publishable_anon_and_duplicate_values_are_rejected(self):
        anon=base64.urlsafe_b64encode(b'{"role":"anon"}').decode().rstrip('=')
        for value in ['', 'sb_publishable_test_only', 'a.'+anon+'.sig', 'not-a-key']:
            self.write('BETA_METRICS_SERVICE_KEY='+value)
            with self.assertRaises(ValueError):
                read_operator_key(self.path)
        self.write('BETA_METRICS_SERVICE_KEY=sb_secret_one\nBETA_METRICS_SERVICE_KEY=sb_secret_two')
        with self.assertRaises(ValueError):
            read_operator_key(self.path)

    def test_symlink_and_group_readable_files_are_rejected(self):
        self.write('BETA_METRICS_SERVICE_KEY=sb_secret_test_only')
        self.path.chmod(0o640)
        with self.assertRaises(ValueError):
            read_operator_key(self.path)
        self.path.chmod(0o600)
        link=self.path.parent/'link'
        link.symlink_to(self.path)
        with self.assertRaises(OSError):
            read_operator_key(link)

    def test_missing_key_command_returns_generic_error_without_secret_echo(self):
        from io import StringIO
        self.write('BETA_METRICS_SERVICE_KEY=private-value-not-valid')
        output=StringIO()
        with override_settings(BASE_DIR=self.path.parent),patch(
                'polskiflow.learning.management.commands.beta_metrics_network_probe.read_operator_key',
                side_effect=ValueError('private-value-not-valid')):
            with self.assertRaises(CommandError) as error:
                call_command('beta_metrics_network_probe',release='a'*40,stdout=output)
        self.assertNotIn('private-value',str(error.exception))
        self.assertEqual(output.getvalue(),'')

    def test_qa_identity_is_read_without_exporting_other_values(self):
        self.write('QA_USER_ID=00000000-0000-0000-0000-000000000001\nQA_PASSWORD=unused-private-value')
        self.assertEqual(read_qa_owner(self.path),'00000000-0000-0000-0000-000000000001')
        self.write('QA_USER_ID=00000000-0000-0000-0000-000000000000')
        with self.assertRaises(ValueError):
            read_qa_owner(self.path)


class MetricsNetworkProbeTests(SimpleTestCase):
    def opener(self,body=b'null'):
        opener=MagicMock()
        response=opener.open.return_value.__enter__.return_value
        response.status=200
        response.read.return_value=body
        return opener

    def test_fixed_host_no_enrollment_and_aggregate_only_output(self):
        opener=self.opener()
        result=probe('sb_secret_test_only','a'*40,2,opener=opener,clock=iter([0,.01,.1,.13]).__next__)
        self.assertEqual(result['successful'],2)
        self.assertEqual(result['p50_ms'],10)
        self.assertEqual(result['p95_ms'],30)
        self.assertFalse(result['enrollment_performed'])
        self.assertFalse(result['beta_readiness_evidence'])
        self.assertIsNone(result['vercel_to_supabase_ms'])
        self.assertIsNone(result['lesson_reserve_finish_cost_ms'])
        self.assertFalse(result['diagnostic_writes_expected'])
        self.assertNotIn('sb_secret_test_only',json.dumps(result))
        identities=[]
        for call in opener.open.call_args_list:
            request=call.args[0]
            self.assertEqual(request.full_url,RPC_URL)
            self.assertEqual(request.method,'POST')
            self.assertEqual(call.kwargs['timeout'],1)
            self.assertIsNone(request.get_header('Authorization'))
            payload=json.loads(request.data)
            self.assertEqual(payload['p_owner'],'00000000-0000-0000-0000-000000000000')
            self.assertNotIn('p_reserve_lesson',payload)
            identities.append(payload['p_request'])
        self.assertEqual(len(set(identities)),2)

    def test_unexpected_nonnull_response_stops_immediately(self):
        opener=self.opener(b'{"attempt_id":"unexpected"}')
        result=probe('sb_secret_test_only','a'*40,5,opener=opener)
        self.assertEqual(opener.open.call_count,1)
        self.assertEqual(result['successful'],0)
        self.assertIsNone(result['p95_ms'])
        self.assertEqual(result['samples'][0]['error'],'unexpected_response')

    def test_qa_observation_uses_only_existing_fixture_owner_and_no_lesson_fields(self):
        opener=self.opener(b'{"attempt_id":null,"finished_at":null}')
        owner='00000000-0000-0000-0000-000000000001'
        result=probe('sb_secret_test_only','a'*40,2,qa_owner=owner,opener=opener)
        self.assertEqual(result['successful'],2)
        self.assertTrue(result['diagnostic_writes_expected'])
        self.assertNotIn(owner,json.dumps(result))
        self.assertEqual(result['latency_scope'],'https_qa_observation')
        self.assertEqual(json.loads(opener.open.call_args.args[0].data)['p_owner'],owner)

    def test_http_and_transport_failures_are_not_success_latency(self):
        opener=self.opener()
        opener.open.side_effect=[HTTPError(RPC_URL,401,'private provider text',{},None),URLError('private cause')]
        result=probe('sb_secret_test_only','a'*40,2,opener=opener)
        self.assertEqual(result['successful'],0)
        self.assertIsNone(result['p95_ms'])
        self.assertEqual([s['error'] for s in result['samples']],['http','transport'])
        self.assertNotIn('private',json.dumps(result))

    def test_redirects_are_not_followed(self):
        self.assertIsNone(NoRedirect().redirect_request(None,None,None,None,None,None))

    def test_limits_are_checked_before_network(self):
        opener=self.opener()
        for runs in [0,1,11,True]:
            with self.assertRaises(ValueError):
                probe('sb_secret_test_only','a'*40,runs,opener=opener)
        with self.assertRaises(ValueError):
            probe('sb_secret_test_only','unknown',2,opener=opener)
        opener.open.assert_not_called()
