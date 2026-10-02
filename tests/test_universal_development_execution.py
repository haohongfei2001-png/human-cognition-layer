import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_v1_deepseek_metered import FakeClient
from scripts.run_universal_development import build_package,run,digest,Ledger,CAP
from scripts.universal_development_protocol import CASES,ordinary


def grant(package):return dict(schema='hcl-universal-development-grant-v1',status='READY',package_sha256=digest(package),authorization_ref='OWNER_APPROVED_2026_10_02_NEW_2_50_18_CALLS',maximum_usd='2.50',maximum_calls=18,historical_budget_transfer=False,retries=0)

class DevelopmentExecutionTests(unittest.TestCase):
    def test_all_six_cases_use_internal_planner_with_every_phase_recorded(self):
        package=build_package();client=FakeClient()
        with tempfile.TemporaryDirectory()as root:
            directory=Path(root)/'one-run';result=run(client,package,grant(package),directory)
            self.assertEqual(len(client.calls),18);self.assertEqual(len(result['calls']),18)
            self.assertEqual(sum(c['phase']=='planning'for c in result['calls']),6)
            self.assertEqual(result['budget_state'],'CLOSED_NO_TRANSFER_NO_RETRY')
            self.assertLessEqual(float(result['reserved_usd']),2.5)
            self.assertEqual(len(result['results']),12)
            self.assertEqual(json.loads((directory/'receipt.json').read_text()),json.loads(json.dumps(result)))
            self.assertNotIn('HIDDEN_',json.dumps(result))
            for row in result['calls']:
                self.assertEqual(row['request_sha256'],digest(row['request']))
                request=json.dumps(row['request'])
                for forbidden in ('expected_label','review_criteria','scoring'):
                    self.assertNotIn(forbidden,request)
            with self.assertRaises(FileExistsError):run(client,package,grant(package),directory)
            self.assertEqual(len(client.calls),18)

    def test_unknown_call_closes_entire_batch_and_never_retries(self):
        package=build_package();client=FakeClient();client.failure='PRIVATE_UPSTREAM_CANARY'
        with tempfile.TemporaryDirectory()as root:
            directory=Path(root)/'one-run'
            with self.assertRaises(Exception):run(client,package,grant(package),directory)
            receipt=json.loads((directory/'receipt.json').read_text())
            self.assertEqual(len(client.calls),1);self.assertEqual(len(receipt['calls']),1)
            self.assertEqual(receipt['status'],'FAILED_OR_INCOMPLETE_NO_RETRY')
            self.assertGreater(float(receipt['reserved_usd']),0)
            self.assertNotIn('PRIVATE_UPSTREAM_CANARY',json.dumps(receipt))
            self.assertEqual(receipt['calls'][0]['failure_code'],'PROVIDER_TRANSPORT_FAILURE_NO_RETRY')

    def test_bad_grant_and_code_or_source_drift_prevent_calls(self):
        package=build_package();client=FakeClient()
        with tempfile.TemporaryDirectory()as root:
            for changed in [dict(grant(package),maximum_calls=19),dict(grant(package),maximum_usd='3.00'),dict(grant(package),historical_budget_transfer=True),dict(grant(package),status='CLOSED_NO_TRANSFER_NO_RETRY')]:
                with self.assertRaises(ValueError):run(client,package,changed,Path(root)/'one-run')
            with self.assertRaises(ValueError):run(client,dict(package,maximum_calls=19),grant(package),Path(root)/'one-run')
            self.assertEqual(client.calls,[])

    def test_pre_call_persistence_failure_prevents_baseline_transport(self):
        package=build_package();client=FakeClient()
        with tempfile.TemporaryDirectory()as root:
            with patch('scripts.run_universal_development.Ledger.record',side_effect=OSError('private disk failure')):
                with self.assertRaises(Exception):run(client,package,grant(package),Path(root)/'one-run')
            self.assertEqual(client.calls,[])

    def test_fixed_authored_mix_includes_no_source_and_multiple_sources(self):
        self.assertEqual(len(CASES),6);self.assertEqual(sum(not c['sources']for c in CASES),1)
        self.assertTrue(any(len(c['sources'])>1 for c in CASES))
        for case in CASES:self.assertEqual(set(ordinary(case)),{'question','sources'})
        self.assertEqual(build_package()['all_call_maximum_reservation_usd'],'2.24826624')

    def test_runtime_deadline_call_cap_and_cost_cap_block_new_transport(self):
        import time
        from scripts.run_universal_development import RecordedPort
        package=build_package()
        for edge in ('deadline','calls','cost'):
            with self.subTest(edge=edge),tempfile.TemporaryDirectory()as root:
                ledger=Ledger(Path(root)/'run',package,grant(package));client=FakeClient()
                if edge=='deadline':ledger.deadline=time.monotonic()-1
                elif edge=='calls':ledger.value['calls']=[dict(case_id=str(i),arm='Base',phase='answer')for i in range(18)]
                else:ledger.value['reserved_usd']='2.50'
                count=len(ledger.value['calls']);held=ledger.value['reserved_usd']
                port=RecordedPort(client,ledger,'new-case','Base')
                reserve=port.reservation_usd('answer',[dict(role='user',content='Synthetic JSON task')])
                attempt=dict(phase='answer',reserved_usd=reserve,status='RESERVED_BEFORE_CALL',provider_call=False,invocation_status='NOT_INVOKED')
                with self.assertRaises(ValueError):port.journal(dict(attempts=[attempt]))
                self.assertEqual(client.calls,[]);self.assertEqual(len(ledger.value['calls']),count)
                self.assertEqual(ledger.value['reserved_usd'],held)

    def test_ciphertext_only_workflow_upload_and_first_run_gate(self):
        from scripts.run_universal_development import TEMPLATE
        text=TEMPLATE.read_text()
        self.assertIn('path: universal-development-receipt.enc.json',text)
        self.assertNotIn('path: universal-development-private',text)
        self.assertIn('test "$GITHUB_RUN_ATTEMPT" = 1',text)
        self.assertIn('scripts.universal_launch_guard --run-history',text)
        self.assertIn('--paginate --slurp',text)
        self.assertIn('paths: [".github/HCL_UNIVERSAL_DEVELOPMENT_TRIGGER.json"]',text)
        self.assertNotIn('PRIVATE KEY',text)
