"""Provider-free integration checks for the shared private mechanics.

Synthetic transport labels below test projection only, never live admission.
All actual transport is the exact deterministic FakeClient.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import hcl_offline_diagnostic_export_v1 as r
from scripts import hcl_offline_diagnostic_public_v1 as p
from tests.test_hcl_offline_diagnostic_export_v1 import NOW, ROOT, packet, plan, op, review


class SharedDiagnosticCore(unittest.TestCase):
    def fixture(self):
        package = r.OfflinePackage.build(packet(), ROOT)
        client = r.FakeClient([json.dumps(plan(op()))])
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'run'
            receipt = r.run_offline(client, package, 1, directory,
                                    clock=lambda: NOW, monotonic=lambda: 0.0)
            native = json.loads((directory / 'native-review-private.json').read_text())
            evidence = p.export(receipt, package, native_bundle=native)
        return package, receipt, native, evidence

    def test_trusted_ledger_owns_port_and_allowance_identity(self):
        observed = []

        class RecordingPort(r.BoundedPort):
            def journal(self, snapshot):
                observed.append(snapshot['authorization_ref'])
                super().journal(snapshot)

        class RecordingLedger(r.Ledger):
            authorization_ref = 'SYNTHETIC_SHARED_CORE_NO_LIVE_AUTHORITY'

            def make_port(self, client, arm_id):
                self.port_created = arm_id
                return RecordingPort(client, self, arm_id)

        package = r.OfflinePackage.build(packet(), ROOT)
        client = r.FakeClient([json.dumps(plan(op()))])
        with tempfile.TemporaryDirectory() as temporary:
            ledger = RecordingLedger(Path(temporary) / 'run', package, 1,
                                     lambda: NOW, lambda: 0.0)
            receipt = r._run_with_ledger(ledger, client)
            self.assertEqual(receipt, json.loads(ledger.path.read_text()))
        self.assertEqual(ledger.port_created, package.cases[0]['case_id'] + ':HCL')
        self.assertTrue(observed)
        self.assertEqual(set(observed), {RecordingLedger.authorization_ref})
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(receipt['status'], 'COMPLETED_ONE_PASS')
        self.assertEqual(receipt['arms'][0]['checked_treatment'], ['B01'])
        self.assertEqual(receipt['budget_state'], 'CLOSED_NO_TRANSFER_NO_RETRY')

    def test_synthetic_transport_projection_separates_cost_and_authority(self):
        package, receipt, _, _ = self.fixture()
        projected = copy.deepcopy(receipt)
        projected.update(schema='SYNTHETIC_RECEIPT', mode='SYNTHETIC_LIVE_LABEL',
                         authorization_ref='SYNTHETIC_NO_AUTHORITY')
        for call in projected['calls']:
            call.update(provider_call=True, offline_transport_call=False)
        output = p._export_ordinary(projected, package,
            receipt_schema='SYNTHETIC_RECEIPT', public_schema='SYNTHETIC_PUBLIC',
            mode='SYNTHETIC_LIVE_LABEL', authorization_ref='SYNTHETIC_NO_AUTHORITY',
            offline=False)
        self.assertEqual(output['provider_calls'], 2)
        self.assertEqual(output['offline_transport_calls'], 0)
        self.assertEqual(output['usage_rated_cny'], '0.0072')
        for name in ('simulated_usage_rated_cny', 'actual_spend_cny',
                     'live_execution_authorized', 'approved_native_evidence'):
            self.assertNotIn(name, output)
        self.assertEqual(output['arms'], p.export(receipt, package)['arms'])
        with self.assertRaises(ValueError):
            p.export(projected, package)
        projected['calls'][0]['offline_transport_call'] = True
        with self.assertRaisesRegex(ValueError, 'EXACT_OFFLINE_CALL_STATE_REQUIRED'):
            p._export_ordinary(projected, package,
                receipt_schema='SYNTHETIC_RECEIPT', public_schema='SYNTHETIC_PUBLIC',
                mode='SYNTHETIC_LIVE_LABEL', authorization_ref='SYNTHETIC_NO_AUTHORITY',
                offline=False)

    def test_shared_original_binding_requires_complete_unchanged_export(self):
        package, receipt, native, evidence = self.fixture()
        self.assertTrue(p._validate_original_binding(evidence,
            original_receipt=receipt, original_native_bundle=native,
            original_export=p.export(receipt, package, native_bundle=native)))
        changed = copy.deepcopy(evidence)
        changed['arms'][0]['orchestration_failure'] = dict(
            code='ORCHESTRATION_FAILURE', stage='NATIVE_DISPATCH')
        with self.assertRaisesRegex(ValueError, 'EXACT_ORIGINAL_DURABLE_EXPORT_REQUIRED'):
            p._validate_original_binding(changed, original_receipt=receipt,
                original_native_bundle=native, original_export=evidence)
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_DURABLE_RECEIPT_AND_CAPTURE_REQUIRED'):
            p._validate_original_binding(evidence, original_receipt=receipt,
                original_native_bundle=None, original_export=evidence)

    def test_shared_success_retains_semantic_and_failure_requirements(self):
        package, _, _, evidence = self.fixture()
        binding = review(package, evidence)
        self.assertTrue(p._validate_success_contents(package, evidence, binding, offline=True))
        binding['gates'][p.GATES[0]] = False
        with self.assertRaisesRegex(ValueError, 'ALL_STRICT_SEMANTIC_AND_DELIVERY_GATES_REQUIRED'):
            p._validate_success_contents(package, evidence, binding, offline=True)
        binding = review(package, evidence)
        evidence['arms'][0]['capture_failure'] = 'POST_RUNTIME_CAPTURE_FAILED'
        with self.assertRaisesRegex(ValueError, 'SUCCESS_CANNOT_CONTAIN_FAILURE_DIAGNOSTIC'):
            p._validate_success_contents(package, evidence, binding, offline=True)

    def test_terminal_export_commits_ordinary_facts_before_native_projection(self):
        package = r.OfflinePackage.build(packet(), ROOT)
        client = r.FakeClient(['{invalid planning'])
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary) / 'run'
            receipt = r.run_offline(client, package, 1, directory,
                                    clock=lambda: NOW, monotonic=lambda: 0.0)
            def reject_native(*args):
                saved = json.loads((directory / 'public.json').read_text())
                self.assertEqual(saved['arms'][0]['orchestration_failure'],
                                 receipt['arms'][0]['orchestration_failure'])
                self.assertEqual(saved['reserved_cny'], receipt['reserved_cny'])
                self.assertEqual(saved['budget_state'], 'CLOSED_NO_TRANSFER_NO_RETRY')
                self.assertIsNone(saved['approved_native_evidence'])
                raise ValueError('SYNTHETIC_PRIVATE_CAPTURE_ERROR')
            with patch.object(p, 'export_native_bundle', side_effect=reject_native):
                output = p.export_terminal(directory, package)
            self.assertEqual(output['native_publication_status'],
                             'OFFLINE_NATIVE_EXPORT_REJECTED_GATE_CLOSED')
            self.assertNotIn('SYNTHETIC_PRIVATE_CAPTURE_ERROR',
                             (directory / 'public.json').read_text())
            self.assertEqual(len(client.calls), 1)


if __name__ == '__main__':
    unittest.main()
