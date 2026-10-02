import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tests.test_v1_deepseek_metered import FakeClient
from scripts.run_planning_diagnostic import build_package,require_grant,run,digest,AUTH,REQUEST_SHA,RESERVE,verify_launch,PACKAGE,GRANT,MARKER,TEMPLATE

def grant(package):return dict(schema='hcl-one-planning-diagnostic-grant-v1',status='READY',authorization_ref=AUTH,package_sha256=digest(package),maximum_calls=1,maximum_usd='0.05',historical_budget_transfer=False,retries=0)

class PlanningDiagnosticTests(unittest.TestCase):
    def test_exact_original_request_one_planning_no_answer_and_closed(self):
        package=build_package();client=FakeClient()
        self.assertEqual(package['request_sha256'],REQUEST_SHA);self.assertEqual(package['reservation_usd'],RESERVE)
        with tempfile.TemporaryDirectory()as root:
            out=Path(root)/'one';r=run(client,package,grant(package),out)
            self.assertEqual(len(client.calls),1);self.assertEqual(client.calls[0]['max_tokens'],4096)
            self.assertEqual(r['status'],'PLANNING_RETURNED_SCHEMA_VALID');self.assertEqual(r['budget_state'],'CLOSED_NO_TRANSFER_NO_RETRY')
            self.assertEqual(digest(r['request']),REQUEST_SHA);self.assertNotIn('HIDDEN_',json.dumps(r))
            self.assertEqual(json.loads((out/'receipt.json').read_text()),r)
            with self.assertRaises(FileExistsError):run(client,package,grant(package),out)
            self.assertEqual(len(client.calls),1)
    def test_pending_old_closed_and_enlarged_grants_admit_no_calls(self):
        package=build_package();client=FakeClient()
        bad=[dict(grant(package),status=x)for x in ('PENDING_OWNER_APPROVAL','CLOSED_NO_TRANSFER_NO_RETRY')]
        bad += [dict(grant(package),maximum_calls=2),dict(grant(package),maximum_usd='0.06'),dict(grant(package),authorization_ref='OWNER_APPROVED_2026_10_02_NEW_2_50_18_CALLS'),dict(grant(package),historical_budget_transfer=True)]
        with tempfile.TemporaryDirectory()as root:
            for g in bad:
                with self.assertRaises(ValueError):run(client,package,g,Path(root)/'one')
            with self.assertRaises(ValueError):run(client,dict(package,max_output=8192),grant(package),Path(root)/'one')
        self.assertEqual(client.calls,[])
    def test_failed_transport_safe_cause_unknown_cost_and_no_retry(self):
        package=build_package();client=FakeClient();client.failure='PRIVATE_BODY_CANARY'
        with tempfile.TemporaryDirectory()as root:
            r=run(client,package,grant(package),Path(root)/'one')
        self.assertEqual(len(client.calls),1);self.assertEqual(r['failure_code'],'PROVIDER_TRANSPORT_FAILURE_NO_RETRY')
        self.assertEqual(r['reserved_usd'],RESERVE);self.assertNotIn('actual_usd',r['attempts'][0]);self.assertNotIn('PRIVATE_BODY_CANARY',json.dumps(r))
    def test_incomplete_output_has_allowlisted_code_not_a_fake_plan(self):
        class Truncated(FakeClient):
            def create(self,**request):
                r=super().create(**request);r['choices'][0]['finish_reason']='length';return r
        client=Truncated();package=build_package()
        with tempfile.TemporaryDirectory()as root:r=run(client,package,grant(package),Path(root)/'one')
        self.assertEqual(len(client.calls),1);self.assertEqual(r['failure_code'],'INCOMPLETE_ANSWER_NO_RETRY');self.assertNotIn('response_content',r);self.assertEqual(r['attempts'][0]['finish_reasons'],['length']);self.assertIn('actual_usd',r['attempts'][0])
    def test_bad_plan_schema_is_distinct_from_transport_failure(self):
        class Invalid(FakeClient):
            def create(self,**request):
                r=super().create(**request);r['choices'][0]['message']['content']='{}';return r
        package=build_package();client=Invalid()
        with tempfile.TemporaryDirectory()as root:r=run(client,package,grant(package),Path(root)/'one')
        self.assertEqual(r['status'],'PLANNING_RETURNED_SCHEMA_REJECTED');self.assertIn('actual_usd',r['attempts'][0]);self.assertEqual(len(client.calls),1)
    def test_initial_and_precall_journal_failure_prevent_transport(self):
        package=build_package()
        for fail_at in (1,2):
            client=FakeClient();count=0
            from scripts.run_planning_diagnostic import save as real_save
            def fail(path,value):
                nonlocal count
                count+=1
                if count==fail_at:raise OSError('PRIVATE_DISK_CANARY')
                real_save(path,value)
            with tempfile.TemporaryDirectory()as root,patch('scripts.run_planning_diagnostic.save',side_effect=fail):
                try:r=run(client,package,grant(package),Path(root)/'one')
                except OSError:pass
            self.assertEqual(client.calls,[])
    def test_history_and_marker_binding_reject_duplicates_or_other_files(self):
        package=build_package();g=grant(package);parent='a'*40
        marker=dict(schema='hcl-one-planning-diagnostic-marker-v1',authorization_ref=AUTH,package_sha256=digest(package),grant_sha256=digest(g),executor_commit=parent)
        history=[dict(id=1,event='push',created_at='2026-10-02T00:00:00Z')]
        def read(p):return json.dumps(package if p==PACKAGE else g)
        with patch.object(Path,'read_text',lambda p,*a,**kw:read(p)),patch('scripts.run_planning_diagnostic.build_package',return_value=package):
            self.assertTrue(verify_launch(1,1,history,'push',parent,[str(MARKER)],marker))
            for kwargs in [dict(run_id=2,attempt=1),dict(run_id=1,attempt=2)]:
                with self.assertRaises(ValueError):verify_launch(**kwargs,history=history,event='workflow_dispatch')
            with self.assertRaises(ValueError):verify_launch(1,1,history,'push',parent,['other'],marker)
            with self.assertRaises(ValueError):verify_launch(1,1,history,'push',parent,[str(MARKER)],dict(marker,package_sha256='bad'))
    def test_workflow_uploads_ciphertext_only(self):
        s=TEMPLATE.read_text();self.assertIn('path: planning-diagnostic.enc.json',s);self.assertNotIn('path: planning-diagnostic-private',s)
        self.assertIn('--paginate --slurp',s);self.assertIn('scripts.run_planning_diagnostic --check-launch',s)
