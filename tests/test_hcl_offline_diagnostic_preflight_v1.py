"""Original October 8 flute inputs, fixed injected failures, zero provider use.

These are diagnostic-preservation controls, never model or semantic smoke passes.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import hcl_offline_diagnostic_preflight_v1 as f
from scripts import hcl_offline_diagnostic_export_v1 as r
from scripts import hcl_offline_diagnostic_public_v1 as p


class CurrentSmokePreflight(unittest.TestCase):
    def assert_refused_before_io(self, context, reason):
        with tempfile.TemporaryDirectory() as parent, context:
            directory = Path(parent) / 'never'
            with patch.object(r, 'FakeClient') as client, self.assertRaisesRegex(ValueError, reason):
                f.run_control('malformed_json', directory)
            client.assert_not_called()
            self.assertFalse(directory.exists())

    def read_override(self, path, data):
        read = Path.read_bytes
        return patch.object(Path, 'read_bytes', lambda current: data if current == path else read(current))

    def test_exact_original_complete_request_and_single_case_schedule(self):
        package = f.preflight()
        manifest = f._read_json(f.MANIFEST)
        original = f._read_json(f.ROOT / manifest['cases_file'])
        self.assertEqual(package.packet, original)
        self.assertEqual(len(original['cases']), 5)
        self.assertEqual(package.value, manifest['expected_package'])
        self.assertEqual(r.order(package.cases, 1), [('reliability-20261007-smoke-flute', 'HCL')])
        request, encoded, metrics = r.request_and_metrics('planning', r.messages(package.cases[0], 'HCL'))
        self.assertEqual(len(encoded), 28333)
        self.assertEqual(metrics['full_request_sha256'], '955c24a417e291e447d7723e1174945c13b1aa5a0038eaadf0aaa0e0c8bdae00')
        self.assertEqual(request['max_tokens'], 16384)
        self.assertEqual(request['reasoning_effort'], 'high')
        payload = json.loads(request['messages'][-1]['content'])
        self.assertEqual(set(payload), {'question', 'sources', 'capability_inventory', 'executable_entry_contract'})
        self.assertEqual(payload['question'], original['cases'][0]['model_input']['question'])
        self.assertEqual(payload['sources'], package.cases[0]['sources'])
        self.assertEqual(payload['sources'][0]['text'], original['cases'][0]['model_input']['sources'][0]['text'])
        for key in ('key_fact_obligations', 'smoke_semantic_requirements', 'native_relevance_review'):
            self.assertNotIn(key, encoded.decode())
        self.assertEqual(package.value['reasoning_effort'], {'planning': 'high', 'answer': 'low'})
        self.assertEqual(package.value['maximum_request_bytes'], 36000)
        self.assertEqual(package.value['answer_tokens'], 16384)

    def test_fixed_controls_persist_distinct_diagnostics_and_failed_source_bindings(self):
        package = f.preflight()
        for control, (code, stage) in f.CONTROLS.items():
            with self.subTest(control=control), tempfile.TemporaryDirectory() as parent:
                directory = Path(parent) / 'run'
                summary = f.run_control(control, directory)
                receipt = f._read_json(directory / 'receipt.json')
                native = f._read_json(directory / 'native-review-private.json')
                evidence = f._read_json(directory / 'public.json')
                review = f._read_json(directory / 'source-review-binding.json')
                self.assertEqual(summary, f._read_json(directory / 'preflight-control.json'))
                expected = dict(code=code, stage=stage)
                for value in (receipt['arms'][0], evidence['arms'][0], summary):
                    self.assertEqual(value['orchestration_failure'], expected)
                self.assertEqual(evidence, p.export(receipt, package, native_bundle=native))
                self.assertEqual(evidence['receipt_sha256'], r.digest(receipt))
                self.assertEqual(summary['original_native_bundle_sha256'], r.digest(native))
                self.assertEqual(summary['public_sha256'], r.digest(evidence))
                self.assertEqual(summary['source_review_sha256'], r.digest(review))
                self.assertEqual(summary['request_sha256'], next(iter(package.value['requests'].values()))['full_request_sha256'])
                self.assertEqual(evidence['offline_transport_calls'], 1)
                self.assertEqual(evidence['provider_calls'], 0)
                self.assertEqual(evidence['actual_spend_cny'], '0')
                self.assertEqual(evidence['status'], 'STOPPED_NO_RETRY')
                self.assertEqual(evidence['budget_state'], 'CLOSED_NO_TRANSFER_NO_RETRY')
                self.assertEqual(evidence['remaining_authorized_calls'], 0)
                self.assertEqual(evidence['remaining_authorized_cny'], '0')
                self.assertEqual(evidence['reserved_cny'], '1.109664')
                self.assertEqual([row['phase'] for row in receipt['calls']], ['planning'])
                self.assertEqual(receipt['calls'][0]['status'], 'RETURNED')
                self.assertEqual(receipt['arms'][0]['executed_capabilities'], [])
                self.assertIsNone(receipt['arms'][0]['final_text'])
                self.assertIsNone(receipt['arms'][0]['capture_failure'])
                self.assertEqual(review['reviewer_role'], 'OFFLINE_INJECTED_CONTROL_IDENTITY_ONLY')
                self.assertFalse(review['overall_pass'])
                self.assertTrue(all(value is False for value in review['gates'].values()))
                self.assertTrue(all(row['passed'] is False for row in review['obligations'] + review['smoke_semantics']))
                self.assertTrue(p.validate_review_binding(package, evidence, review))
                with self.assertRaisesRegex(ValueError, 'PHASE1_EXACT_COMPLETE_KNOWN_CLOSED_REQUIRED'):
                    p.validate_phase1_gate(package, evidence, review, original_receipt=receipt, original_native_bundle=native)
                for path in directory.iterdir():
                    for private in ('OFFLINE_INJECTED_PLANNER_CANARY', 'OFFLINE_INJECTED_MALFORMED_PLANNER_CANARY',
                                    'OFFLINE_PRIVATE_REASONING_CANARY', 'OFFLINE_PRIVATE_ENVELOPE_CANARY'):
                        self.assertNotIn(private, path.read_text())

    def test_packet_source_question_rubric_and_order_drift_stop_before_fake_or_output(self):
        manifest = f._read_json(f.MANIFEST)
        path = f.ROOT / manifest['cases_file']
        original = f._read_json(path)
        mutations = [lambda v: v['cases'][0]['model_input'].update(question='Changed question'),
            lambda v: v['cases'][0]['model_input']['sources'][0].update(text='Changed source'),
            lambda v: v['cases'][0]['model_input']['sources'][0].update(version=2),
            lambda v: v['cases'][0]['private_evaluation']['smoke_semantic_requirements'][0].update(requirement='weakened'),
            lambda v: v['cases'][0]['private_evaluation']['key_fact_obligations'][0].update(obligation='weakened'),
            lambda v: v['cases'].reverse()]
        for mutate in mutations:
            value = copy.deepcopy(original); mutate(value)
            self.assert_refused_before_io(self.read_override(path, r.canonical(value)), 'ORIGINAL_CASES_FILE_DRIFT')

    def test_manifest_config_drift_cannot_be_rebased_by_rebuilding_a_package(self):
        original = f._read_json(f.MANIFEST)
        for field, value in [('planning_tokens', 8192), ('maximum_request_bytes', 40000),
                             ('reasoning_effort', {'planning': 'low', 'answer': 'low'}),
                             ('phase_holds_cny', {'planning': '0', 'answer': '0'}),
                             ('stage_orders', {'1': []}), ('sdk_retries', 1),
                             ('live_execution_authorized', True), ('actual_spend_cny', '1')]:
            altered = copy.deepcopy(original); altered['expected_package'][field] = value
            with self.subTest(field=field):
                self.assert_refused_before_io(self.read_override(f.MANIFEST, r.canonical(altered)), 'PREFLIGHT_MANIFEST_DRIFT')

    def test_current_runtime_helper_implementation_and_request_drift_stop_before_io(self):
        self.assert_refused_before_io(patch.object(r, 'runtime_digest', return_value='0' * 64), 'CURRENT_RUNTIME_DRIFT')
        manifest = f._read_json(f.MANIFEST)
        for name in manifest['expected_package']['reference_helper_files']:
            self.assert_refused_before_io(self.read_override(f.DIRECTORY / name, b'changed helper'), 'ARCHIVED_HELPER_HASH_CHANGED')
        for name in manifest['expected_package']['implementation_files']:
            self.assert_refused_before_io(self.read_override(f.ROOT / 'scripts' / name, b'changed implementation'), 'CURRENT_REQUEST_OR_CONFIGURATION_DRIFT')
        from scripts.hcl_offline_diagnostic_reference import _reference
        ordinary = _reference.messages
        def changed(case, arm):
            result = ordinary(case, arm)
            result[0]['content'] += ' drift'
            return result
        self.assert_refused_before_io(patch.object(_reference, 'messages', changed), 'CURRENT_REQUEST_OR_CONFIGURATION_DRIFT')

    def test_trusted_originals_reload_and_fail_closed_on_mutation_or_staleness(self):
        package = f.preflight()
        with tempfile.TemporaryDirectory() as parent:
            directory = Path(parent) / 'run'
            summary = f.run_control('malformed_json', directory)
            evidence = f._read_json(directory / 'public.json')
            review = f._read_json(directory / 'source-review-binding.json')
            arguments = dict(original_receipt_path=directory / 'receipt.json',
                original_native_bundle_path=directory / 'native-review-private.json',
                original_receipt_sha256=summary['original_receipt_sha256'],
                original_native_bundle_sha256=summary['original_native_bundle_sha256'])
            self.assertTrue(f.validate_saved_binding(package, evidence, review, **arguments))
            for path in (arguments['original_receipt_path'], arguments['original_native_bundle_path']):
                original = path.read_bytes()
                for body in (b'{malformed', b'{"same":1,"same":2}', b'{"value":NaN}', b'{}', b'null'):
                    path.write_bytes(body)
                    with self.assertRaises(ValueError):
                        f.validate_saved_binding(package, evidence, review, **arguments)
                path.write_bytes(original)
            changed = copy.deepcopy(evidence)
            changed['arms'][0]['orchestration_failure'] = dict(code='ORCHESTRATION_FAILURE', stage='UNKNOWN')
            changed_review = f._unreviewed_binding(package, changed)
            self.assertTrue(p.validate_review_binding(package, changed, changed_review))
            with self.assertRaisesRegex(ValueError, 'EXACT_ORIGINAL_DURABLE_EXPORT_REQUIRED'):
                f.validate_saved_binding(package, changed, changed_review, **arguments)
            stale = Path(parent) / 'stale'
            f.run_control('valid_empty_plan', stale)
            arguments['original_receipt_path'] = stale / 'receipt.json'
            with self.assertRaisesRegex(ValueError, 'TRUSTED_ORIGINAL_HASH_CHANGED'):
                f.validate_saved_binding(package, evidence, review, **arguments)

    def test_post_runtime_capture_failure_preserves_diagnostic_without_invented_native(self):
        package = f.preflight()
        with tempfile.TemporaryDirectory() as parent:
            directory = Path(parent) / 'run'
            with patch.object(r.Ledger, 'native_review', side_effect=RuntimeError('PRIVATE_CAPTURE_CANARY')):
                summary = f.run_control('malformed_json', directory)
            evidence = f._read_json(directory / 'public.json')
            receipt = f._read_json(directory / 'receipt.json')
            review = f._read_json(directory / 'source-review-binding.json')
            self.assertEqual(evidence['arms'][0]['orchestration_failure'],
                             dict(code='INVALID_PLANNING_JSON', stage='PLANNING_RESPONSE_VALIDATION'))
            self.assertEqual(evidence['arms'][0]['capture_failure'], 'POST_RUNTIME_CAPTURE_FAILED')
            self.assertEqual(evidence['native_publication_status'], 'OFFLINE_NATIVE_UNAVAILABLE_GATE_CLOSED')
            self.assertEqual(evidence['offline_transport_calls'], 1)
            self.assertEqual(evidence['reserved_cny'], '1.109664')
            self.assertIsNone(summary['original_native_bundle_sha256'])
            self.assertIsNone(evidence['approved_native_evidence'])
            self.assertFalse((directory / 'native-review-private.json').exists())
            self.assertTrue(p.validate_review_binding(package, evidence, review))
            arguments = dict(original_receipt_path=directory / 'receipt.json',
                original_native_bundle_path=directory / 'native-review-private.json',
                original_receipt_sha256=summary['original_receipt_sha256'],
                original_native_bundle_sha256=None)
            self.assertTrue(f.validate_saved_binding(package, evidence, review, **arguments))
            arguments['original_native_bundle_path'].write_text('null')
            with self.assertRaisesRegex(ValueError, 'EXACT_ORIGINAL_NATIVE_BUNDLE_REQUIRED'):
                f.validate_saved_binding(package, evidence, review, **arguments)
            arguments['original_native_bundle_path'].unlink()
            with self.assertRaisesRegex(ValueError, 'PHASE1_EXACT_COMPLETE_KNOWN_CLOSED_REQUIRED'):
                p.validate_phase1_gate(package, evidence, review, original_receipt=receipt, original_native_bundle=None)
            for path in directory.iterdir():
                self.assertNotIn('PRIVATE_CAPTURE_CANARY', path.read_text())

    def test_declared_capture_missing_or_changed_preserves_public_diagnosis_but_rejects_binding(self):
        capture = r.Ledger.native_review
        for corrupt in (False, True):
            with self.subTest(corrupt=corrupt), tempfile.TemporaryDirectory() as parent:
                directory = Path(parent) / 'run'
                def lose_capture(ledger, case, result):
                    capture(ledger, case, result)
                    path = ledger.directory / 'native-review-private.json'
                    if corrupt:
                        path.write_text('{MALFORMED_CAPTURE_CANARY')
                    else:
                        path.unlink()
                with patch.object(r.Ledger, 'native_review', lose_capture), self.assertRaises(ValueError):
                    f.run_control('malformed_json', directory)
                evidence = f._read_json(directory / 'public.json')
                self.assertEqual(evidence['arms'][0]['orchestration_failure']['code'], 'INVALID_PLANNING_JSON')
                self.assertEqual(evidence['offline_transport_calls'], 1)
                self.assertIsNone(evidence['approved_native_evidence'])
                self.assertTrue(evidence['arms'][0]['native_review_available'])
                self.assertFalse((directory / 'source-review-binding.json').exists())
                self.assertFalse((directory / 'preflight-control.json').exists())
                self.assertNotIn('MALFORMED_CAPTURE_CANARY', (directory / 'public.json').read_text())

    def test_unknown_control_and_existing_output_cannot_start_another_fake_call(self):
        with tempfile.TemporaryDirectory() as parent:
            for control in ('unknown', [], None):
                with patch.object(r, 'FakeClient') as client, self.assertRaisesRegex(ValueError, 'FIXED_INJECTED_OFFLINE_CONTROL_REQUIRED'):
                    f.run_control(control, Path(parent) / 'never')
                client.assert_not_called()
            directory = Path(parent) / 'run'
            f.run_control('malformed_json', directory)
            original = (directory / 'receipt.json').read_bytes()
            with patch.object(r.FakeClient, 'create', side_effect=AssertionError('NO_SECOND_CALL')), self.assertRaises(FileExistsError):
                f.run_control('malformed_json', directory)
            self.assertEqual((directory / 'receipt.json').read_bytes(), original)

    def test_fresh_process_forbids_network_sdk_account_credentials_and_live_cli(self):
        code = """
import os, socket, sys
from pathlib import Path
class DenyLiveImports:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in ('openai', 'requests', 'httpx') or fullname in ('scripts.two_stage_account', 'scripts.two_stage_price', 'hcl_entry_contract_smoke_cli'):
            raise AssertionError('NO_LIVE_IMPORT')
def deny(*args, **kwargs):
    raise AssertionError('NO_NETWORK_OR_CREDENTIAL_LOOKUP')
sys.meta_path.insert(0, DenyLiveImports())
socket.socket.connect = socket.create_connection = deny
from scripts import hcl_offline_diagnostic_preflight_v1 as f
os.getenv = deny
result = f.run_control('malformed_json', Path(sys.argv[1]))
assert result['provider_calls'] == 0 and result['actual_spend_cny'] == '0'
"""
        with tempfile.TemporaryDirectory() as parent:
            result = subprocess.run([sys.executable, '-c', code, str(Path(parent) / 'run')],
                                    cwd=f.ROOT, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode())


if __name__ == '__main__':
    unittest.main()
