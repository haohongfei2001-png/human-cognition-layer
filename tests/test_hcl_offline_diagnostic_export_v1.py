"""Real fake transport -> UniversalHCL -> durable receipt -> export -> hash binding.

Synthetic source-review booleans exercise gates only; no independent semantic
assessment, model quality, live permission or historical diagnosis is claimed.
"""
import copy
from contextlib import nullcontext
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from hcl.cognition import universal_entry
from scripts import hcl_offline_diagnostic_export_v1 as r
from scripts import hcl_offline_diagnostic_public_v1 as p
from scripts import hcl_offline_diagnostic_reference as refs
from scripts.hcl_offline_diagnostic_reference import _reference as reference, _native as native

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 8, 1, tzinfo=timezone.utc)
SID = 'control-source-0-0'
CANARY = 'PRIVATE_EXCEPTION_SOURCE_PLANNER_CANARY'


def packet(text='Mira: I believe the box is blue.\nMira: I want to inspect the box.', question='What does Mira explicitly report?', family='B01', extra_sources=()):
    rows = []
    for index in range(5):
        materials = [(f'control-source-{index}-0', text)] + (list(extra_sources) if index == 0 else [])
        sources = [dict(source_id=sid, text=body, version=1, complete=True,
                        text_sha256=hashlib.sha256(body.encode()).hexdigest()) for sid, body in materials]
        evaluation = dict(key_fact_obligations=[dict(id=f'K{x}', obligation='CONTROL_RUBRIC') for x in range(1, 5)],
            inference_boundary_obligations=[dict(id=f'I{x}', obligation='CONTROL_RUBRIC') for x in range(1, 4)],
            citation_source_obligations=[dict(id=f'C{x}', obligation='CONTROL_RUBRIC') for x in range(1, 4)],
            scores_and_results=None, predeclared_acceptable_relevant_native_operation_families=[dict(capability_id=family)])
        if index == 0:
            evaluation.update(smoke_semantic_requirements=[dict(id=f'S{x}', requirement='CONTROL_SEMANTIC') for x in range(1, 5)], smoke_semantic_results=None)
        rows.append(dict(case_id=f'control-{index}', role='smoke' if index == 0 else 'comparison',
                         model_input=dict(question=question, sources=sources), private_evaluation=evaluation))
    return dict(authored_at_utc='2026-10-07T03:42:00Z', cases=rows)


def op(capability='B01', question='What does Mira explicitly report?', bindings=(), source_ids=None, **extra):
    value = dict(capability=capability, question=question, source_ids=source_ids or [SID], bindings=list(bindings))
    if capability in ('B01', 'C01', 'C02', 'C03'): value['input_mode'] = 'literal'
    value.update(extra)
    return value


def plan(*operations):
    return dict(task='OFFLINE_PRIVATE_PLANNER_TASK_CANARY', operations=list(operations), limitations=['OFFLINE_PRIVATE_LIMITATION_CANARY'])


def actor(quote='Mira', source_id=SID, **extra):
    return dict(role='actor', source_id=source_id, quote=quote, **extra)


def review(package, evidence):
    arm = evidence['arms'][0]
    def checks(ids):
        return [dict(id=i, passed=True, source_evidence='SYNTHETIC CONTROL ONLY', answer_evidence='SYNTHETIC CONTROL ONLY') for i in ids]
    return dict(schema=p.REVIEW_SCHEMA, authorization_ref=r.AUTH, package_sha256=r.digest(package.value),
        packet_sha256=r.digest(package.packet), evidence_sha256=r.digest(evidence), final_answer_sha256=arm['final_answer_sha256'],
        request_diagnostics_sha256=r.digest(arm['request_diagnostics']), native_review_sha256=arm['native_review_sha256'],
        reviewer_role='INDEPENDENT_SOURCE_FIRST_AFTER_OUTPUT', same_smoke_and_rules_fixed_before_entry_contract_smoke_output=True,
        gates={key: True for key in p.GATES}, obligations=checks(p.obligation_ids(package.packet['cases'][0])),
        smoke_semantics=checks(['S1', 'S2', 'S3', 'S4']), relevant_native_capability_ids=['B01'], critical_failure_tags=[], overall_pass=True)


class CompleteChain(unittest.TestCase):
    def chain(self, proposal=None, *, source_packet=None, final=None, responses=None, context=None):
        package = r.OfflinePackage.build(source_packet or packet(), ROOT)
        if responses is None:
            responses = () if proposal is None else (proposal if type(proposal) is str else json.dumps(proposal),)
            if final is not None: responses += (final if type(final) is str else json.dumps(final),)
        client = r.FakeClient(responses)
        with tempfile.TemporaryDirectory() as parent:
            directory = Path(parent) / 'run'
            with context or nullcontext():
                result = r.run_offline(client, package, 1, directory, clock=lambda: NOW)
            receipt = json.loads((directory / 'receipt.json').read_text())
            self.assertEqual(receipt, result)
            evidence = p.export_terminal(directory, package)
            self.assertEqual(evidence, json.loads((directory / 'public.json').read_text()))
            native_path = directory / 'native-review-private.json'
            bundle = json.loads(native_path.read_text()) if native_path.exists() else None
            for path in directory.iterdir():
                body = path.read_text()
                for private in (CANARY, 'OFFLINE_PRIVATE_REASONING_CANARY', 'OFFLINE_PRIVATE_ENVELOPE_CANARY',
                                'OFFLINE_PRIVATE_PLANNER_TASK_CANARY', 'OFFLINE_PRIVATE_LIMITATION_CANARY'):
                    self.assertNotIn(private, body)
        binding = review(package, evidence)
        self.assertTrue(p.validate_review_binding(package, evidence, binding))
        self.assertEqual(evidence['receipt_sha256'], r.digest(receipt))
        self.assertEqual(evidence['actual_spend_cny'], '0')
        self.assertEqual(evidence['provider_calls'], 0)
        self.assertFalse(evidence['live_execution_authorized'])
        self.assertEqual(evidence['remaining_authorized_calls'], 0)
        self.assertEqual(evidence['remaining_authorized_cny'], '0')
        self.assertEqual(evidence['budget_state'], 'CLOSED_NO_TRANSFER_NO_RETRY')
        self.assertEqual(evidence['reserved_cny'], str(sum((r.HOLD_CNY[c['phase']] for c in receipt['calls']), Decimal(0))))
        return receipt, evidence, package, client, binding, bundle

    def assert_failure(self, chain, code, stage, calls=1):
        receipt, evidence, package, client, binding, bundle = chain
        expected = dict(code=code, stage=stage)
        self.assertEqual(receipt['arms'][0]['orchestration_failure'], expected)
        self.assertEqual(evidence['arms'][0]['orchestration_failure'], expected)
        self.assertEqual(evidence['status'], 'STOPPED_NO_RETRY')
        self.assertEqual(len(client.calls), calls)
        self.assertEqual(evidence['offline_transport_calls'], calls)
        self.assertTrue(p.validate_review_binding(package, evidence, binding))
        with self.assertRaisesRegex(ValueError, 'PHASE1_EXACT_COMPLETE_KNOWN_CLOSED_REQUIRED'):
            p.validate_phase1_gate(package, evidence, binding, original_receipt=receipt, original_native_bundle=bundle)
        return evidence['arms'][0]

    def test_real_malformed_json_and_valid_empty_plan_keep_distinct_diagnoses(self):
        for proposal, code, stage in [('{'+CANARY, 'INVALID_PLANNING_JSON', 'PLANNING_RESPONSE_VALIDATION'),
                                      (plan(), 'NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER', 'NATIVE_RESULT_ADMISSION')]:
            with self.subTest(code=code):
                chain = self.chain(proposal)
                self.assert_failure(chain, code, stage)
                self.assertEqual(chain[0]['arms'][0]['status'], 'BOUNDED_HCL_SCHEMA_SELECTION_OR_ADAPTER_FAILURE')
                self.assertEqual(chain[0]['reserved_cny'], str(r.HOLD_CNY['planning']))
                self.assertEqual([row['phase'] for row in chain[0]['calls']], ['planning'])
                self.assertEqual(chain[1]['arms'][0]['native_results'], 0)

    def test_shape_modes_and_anchors_fail_before_all_dispatch(self):
        missing_mode = op(); del missing_mode['input_mode']
        values = [(dict(plan(), extra=True), 'invalid bounded task plan'),
                  (plan(missing_mode), 'EXPLICIT_READER_INPUT_MODE_REQUIRED'),
                  (plan(op(input_mode='private-'+CANARY)), 'INVALID_READER_INPUT_MODE'),
                  (plan(op(), op('G02', bindings=[actor(start=1)])), 'invented or stale source anchor')]
        for value, code in values:
            with self.subTest(code=code):
                chain = self.chain(value, context=patch.object(universal_entry.UniversalHCL, '_execute', side_effect=AssertionError('MUST_NOT_DISPATCH')))
                arm = self.assert_failure(chain, code, 'PLANNING_RESPONSE_VALIDATION')
                self.assertEqual(arm['executed_capabilities'], [])
                self.assertEqual(chain[5]['reviews'][0]['native_outputs'], [])

    def test_entry_rejection_and_unchecked_actual_native_are_distinct(self):
        entry = self.chain(plan(op()), source_packet=packet('The observer left a plain note.'))
        arm = self.assert_failure(entry, 'LITERAL_ENTRY_NECESSARY_CONDITION_FAILED_BEFORE_NATIVE', 'ENTRY_ADMISSION')
        self.assertEqual(arm['executed_capabilities'], [])
        unchecked = self.chain(plan(op(question='What does Other believe?')))
        arm = self.assert_failure(unchecked, 'REQUIRED_CHECKED_NATIVE_TREATMENT_ABSENT_BEFORE_ANSWER', 'NATIVE_RESULT_ADMISSION')
        self.assertEqual(arm['executed_capabilities'], ['B01'])
        self.assertEqual(arm['checked_treatment'], [])
        self.assertEqual(arm['native_results'], 1)

    def test_every_remaining_orchestration_stage_uses_real_runtime_failure(self):
        reserve = r.BoundedPort.reservation_usd
        def reject_final(port, phase, prompt):
            if phase == 'answer': raise RuntimeError(CANARY)
            return reserve(port, phase, prompt)
        trials = [('PLANNING_ADMISSION', 'METERED_BACKEND_OR_JOURNAL_FAILED', 0,
                   patch.object(r.BoundedPort, 'reservation_usd', side_effect=RuntimeError(CANARY))),
                  ('NATIVE_DISPATCH', 'ORCHESTRATION_FAILURE', 1,
                   patch.object(universal_entry.UniversalHCL, '_execute', side_effect=RuntimeError(CANARY))),
                  ('FINAL_CONTEXT_CONSTRUCTION', 'ORCHESTRATION_FAILURE', 1,
                   patch.object(universal_entry, '_share_identical_native_reader_contexts', side_effect=RuntimeError(CANARY))),
                  ('FINAL_PROVIDER_ADMISSION', 'METERED_BACKEND_OR_JOURNAL_FAILED', 1,
                   patch.object(r.BoundedPort, 'reservation_usd', reject_final))]
        for stage, code, calls, context in trials:
            with self.subTest(stage=stage):
                self.assert_failure(self.chain(plan(op()), context=context), code, stage, calls)
        blank = dict(answer='', source_citations=[], uncertainty='', assumptions='')
        self.assert_failure(self.chain(plan(op()), final=blank), 'NONBLANK_FINAL_ANSWER_REQUIRED', 'FINAL_RESPONSE_VALIDATION', 2)
        # A final malformed response is deliberately retained byte-for-byte.
        self.assert_failure(self.chain(plan(op()), final='{malformed final'), 'ORCHESTRATION_FAILURE', 'FINAL_RESPONSE_VALIDATION', 2)

    def test_success_null_preserves_final_native_lineage_requests_and_semantic_gate(self):
        receipt, evidence, package, client, binding, bundle = self.chain(plan(op()))
        arm = evidence['arms'][0]
        self.assertIsNone(arm['orchestration_failure']); self.assertIsNone(arm['capture_failure'])
        self.assertEqual(arm['status'], 'ANSWER_ACCEPTED')
        self.assertEqual(arm['final_answer_sha256'], hashlib.sha256(arm['final_text'].encode()).hexdigest())
        self.assertEqual(arm['final_fields'], json.loads(arm['final_text']))
        self.assertTrue(arm['citations_accepted'])
        self.assertEqual(arm['selected_capabilities'], arm['executed_capabilities'])
        self.assertEqual(arm['checked_treatment'], ['B01'])
        self.assertEqual([call['reasoning_effort'] for call in client.calls], ['high', 'low'])
        self.assertEqual([call['max_tokens'] for call in client.calls], [16384, 16384])
        for sent, call in zip(client.calls, evidence['calls']):
            request = dict(sent); request['thinking'] = request.pop('extra_body')['thinking']
            self.assertEqual(r.digest(request), call['request_sha256'])
            self.assertEqual(len(r.canonical(request)), call['request_bytes'])
            self.assertEqual(Decimal(call['reserved_cny']), r.HOLD_CNY[call['phase']])
            self.assertEqual(Decimal(call['exact_request_reservation_cny']), r.quote(call['request_bytes'], call['phase']))
            source = json.loads(sent['messages'][-1]['content'])['sources'][0]
            self.assertEqual(source['text'], package.cases[0]['sources'][0]['text'])
        self.assertTrue(p.validate_phase1_gate(package, evidence, binding, original_receipt=receipt, original_native_bundle=bundle))
        record = evidence['approved_native_evidence']['records'][0]
        self.assertEqual(record['native_projection_sha256'], receipt['arms'][0]['native_projection_sha256'])
        self.assertEqual(record['private_native_review_sha256'], r.digest(bundle['reviews'][0]))

    def test_native_capture_failure_cannot_erase_diagnosis_or_counts(self):
        chain = self.chain(plan(op(question='What does Other believe?')),
                           context=patch.object(r.Ledger, 'native_review', side_effect=RuntimeError(CANARY)))
        arm = self.assert_failure(chain, 'REQUIRED_CHECKED_NATIVE_TREATMENT_ABSENT_BEFORE_ANSWER', 'NATIVE_RESULT_ADMISSION')
        self.assertEqual(arm['capture_failure'], 'POST_RUNTIME_CAPTURE_FAILED')
        self.assertEqual(arm['native_results'], 1)
        self.assertEqual(arm['executed_capabilities'], ['B01'])
        self.assertIsNone(chain[5])

    def test_success_capture_failure_stays_null_and_keeps_returned_final(self):
        chain = self.chain(plan(op()), context=patch.object(r.Ledger, 'native_review', side_effect=RuntimeError(CANARY)))
        arm = chain[1]['arms'][0]
        self.assertIsNone(arm['orchestration_failure'])
        self.assertEqual(arm['capture_failure'], 'POST_RUNTIME_CAPTURE_FAILED')
        self.assertIsNotNone(arm['final_text'])
        self.assertEqual(len(chain[3].calls), 2)
        self.assertEqual(chain[1]['status'], 'STOPPED_NO_RETRY')

    def test_export_interrupt_preserves_saved_receipt_and_retry_only_exports(self):
        package = r.OfflinePackage.build(packet(), ROOT); client = r.FakeClient(['not JSON'])
        with tempfile.TemporaryDirectory() as parent:
            directory = Path(parent)/'run'
            result = r.run_offline(client, package, 1, directory, clock=lambda: NOW)
            raw_before = (directory/'receipt.json').read_bytes()
            save = r.save
            def interrupt(path, value):
                if Path(path).name == 'public.json': raise OSError(CANARY)
                return save(path, value)
            with patch.object(r, 'save', interrupt), self.assertRaises(OSError): p.export_terminal(directory, package)
            self.assertEqual(raw_before, (directory/'receipt.json').read_bytes())
            output = p.export_terminal(directory, package)
            self.assertEqual(output['arms'][0]['orchestration_failure'], result['arms'][0]['orchestration_failure'])
            self.assertEqual(len(client.calls), 1)

    def test_real_process_interruption_before_and_after_runtime_return(self):
        package = r.OfflinePackage.build(packet(), ROOT)
        for after in (False, True):
            with self.subTest(after=after), tempfile.TemporaryDirectory() as parent:
                directory = Path(parent)/'run'; packet_path = Path(parent)/'input.json'
                packet_path.write_text(json.dumps(package.packet))
                # Hard exit guarantees no Python finally block closes the receipt.
                code = """
import json, os, sys
from pathlib import Path
from scripts import hcl_offline_diagnostic_export_v1 as r
package = r.OfflinePackage.build(json.loads(Path(sys.argv[1]).read_text()), Path.cwd())
if sys.argv[3] == 'after':
    r.Ledger.native_review = lambda *args: os._exit(43)
else:
    r.BoundedPort.complete = lambda *args: os._exit(43)
r.run_offline(r.FakeClient(['not JSON']), package, 1, sys.argv[2])
"""
                completed = subprocess.run([sys.executable, '-c', code, str(packet_path), str(directory), 'after' if after else 'before'], cwd=ROOT, capture_output=True, timeout=30)
                self.assertEqual(completed.returncode, 43, completed.stderr)
                original = json.loads((directory/'receipt.json').read_text())
                self.assertEqual(original['status'], 'RUNNING')
                expected = dict(code='INVALID_PLANNING_JSON', stage='PLANNING_RESPONSE_VALIDATION') if after else None
                self.assertEqual(original['arms'][0]['orchestration_failure'], expected)
                output = p.export_terminal(directory, package)
                self.assertEqual(output['arms'][0]['orchestration_failure'], expected)
                self.assertEqual(output['status'], 'STOPPED_NO_RETRY')
                self.assertEqual(output['reserved_cny'], str(r.HOLD_CNY['planning']))
                self.assertTrue(p.validate_review_binding(package, output, review(package, output)))

    def test_new_enums_reject_malformed_unknown_or_spoofed_values(self):
        receipt, evidence, package, _, binding, _ = self.chain('not JSON')
        class Spoof(str):
            def __hash__(self): return hash('INVALID_PLANNING_JSON')
            def __eq__(self, other): return True
        class Unhashable(str): __hash__ = None
        good = receipt['arms'][0]['orchestration_failure']
        values = [False, [], {}, dict(good, extra=CANARY), dict(code=CANARY, stage=good['stage']),
                  dict(code=good['code'], stage=CANARY)]
        for field in ('code', 'stage'):
            for value in (None, [], 7, Spoof(CANARY), Unhashable(CANARY)):
                row = dict(good); row[field] = value; values.append(row)
        for value in values:
            with self.subTest(value=repr(value)):
                changed = copy.deepcopy(receipt); changed['arms'][0]['orchestration_failure'] = value
                with self.assertRaises(ValueError): p.export(changed, package)
        missing = copy.deepcopy(receipt); del missing['arms'][0]['orchestration_failure']
        with self.assertRaisesRegex(ValueError, 'REQUIRED_NULLABLE'): p.export(missing, package)
        old = copy.deepcopy(receipt); old['schema'] = 'hcl-entry-contract-smoke-offline-receipt-v1'
        with self.assertRaises(ValueError): p.export(old, package)

    def test_runtime_helper_subclass_fallback_survives_capture_without_raw_text(self):
        class Spoof(str):
            def __hash__(self): return hash('INVALID_PLANNING_JSON')
            def __eq__(self, other): return True
        class ForgedBoundary(universal_entry.HCLBoundaryError):
            pass
        error = ForgedBoundary('ORCHESTRATION_FAILURE'); error.code = Spoof(CANARY)
        chain = self.chain(plan(op()), context=patch.object(universal_entry.UniversalHCL, '_validate_plan', side_effect=error))
        self.assert_failure(chain, 'ORCHESTRATION_FAILURE', 'PLANNING_RESPONSE_VALIDATION')

    def test_review_binding_rejects_changed_missing_null_and_swapped_diagnostics(self):
        receipt, evidence, package, _, binding, _ = self.chain('not JSON')
        for replacement in (None, dict(code='ORCHESTRATION_FAILURE', stage='PLANNING_RESPONSE_VALIDATION'),
                            dict(code='INVALID_PLANNING_JSON', stage='ENTRY_ADMISSION')):
            changed = copy.deepcopy(evidence); changed['arms'][0]['orchestration_failure'] = replacement
            with self.assertRaisesRegex(ValueError, 'EXACT_REVIEW_HASH_BINDING_REQUIRED'):
                p.validate_review_binding(package, changed, binding)
        changed = copy.deepcopy(evidence); del changed['arms'][0]['orchestration_failure']
        with self.assertRaisesRegex(ValueError, 'REQUIRED_NULLABLE'): p.validate_review_binding(package, changed, binding)
        for key in ('schema', 'authorization_ref', 'package_sha256', 'packet_sha256'):
            changed = copy.deepcopy(binding); changed[key] = 'WRONG'
            with self.assertRaises(ValueError): p.validate_review_binding(package, evidence, changed)
        for key, value in (('stage', True), ('receipt_sha256', None), ('runtime_sha256', 'c'*64)):
            changed = copy.deepcopy(evidence); changed[key] = value
            with self.assertRaises(ValueError): p.validate_review_binding(package, changed, review(package, changed))

    def test_native_capture_tampering_and_stale_receipt_commitments_reject(self):
        receipt, evidence, package, _, binding, bundle = self.chain(plan(op()))
        changed = copy.deepcopy(bundle); changed['reviews'][0]['validated_operation_arguments'][0]['question'] += ' changed'
        with self.assertRaisesRegex(ValueError, 'EXACT_RECEIPT_NATIVE_CAPTURE_HASH_REQUIRED'):
            p.export(receipt, package, native_bundle=changed)
        changed_receipt = copy.deepcopy(receipt); changed_receipt['arms'][0]['native_projection_sha256'] = 'a'*64
        with self.assertRaisesRegex(ValueError, 'EXACT_RECEIPT_NATIVE_PROJECTION_REQUIRED'):
            p.export(changed_receipt, package, native_bundle=bundle)
        changed = copy.deepcopy(evidence); changed['approved_native_evidence']['receipt_sha256'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'EXACT_NATIVE_EVIDENCE_RECEIPT_LINK_REQUIRED'):
            p.validate_review_binding(package, changed, binding)
        # Rehashing the review cannot make stale native receipt links consistent.
        with self.assertRaisesRegex(ValueError, 'EXACT_NATIVE_EVIDENCE_RECEIPT_LINK_REQUIRED'):
            p.validate_review_binding(package, changed, review(package, changed))

    def test_success_gate_requires_actual_native_bundle_even_with_affirmative_rehashed_review(self):
        receipt, evidence, package, _, _, bundle = self.chain(plan(op()))
        unavailable = p.export(receipt, package)
        rejected = copy.deepcopy(unavailable)
        rejected['native_publication_status'] = 'OFFLINE_NATIVE_EXPORT_REJECTED_GATE_CLOSED'
        for value in (unavailable, rejected):
            affirmative = review(package, value)
            self.assertTrue(p.validate_review_binding(package, value, affirmative))
            with self.assertRaisesRegex(ValueError, 'EXACT_ORIGINAL_DURABLE_EXPORT_REQUIRED'):
                p.validate_phase1_gate(package, value, affirmative, original_receipt=receipt, original_native_bundle=bundle)
        trials = []
        missing = copy.deepcopy(evidence); del missing['approved_native_evidence']; trials.append(missing)
        missing_records = copy.deepcopy(evidence); del missing_records['approved_native_evidence']['records']; trials.append(missing_records)
        empty = copy.deepcopy(evidence); empty['approved_native_evidence'].update(records=[], record_count=0); trials.append(empty)
        missing_operations = copy.deepcopy(evidence); missing_operations['approved_native_evidence']['records'][0]['operations'] = []; trials.append(missing_operations)
        substituted = copy.deepcopy(evidence)
        substituted['approved_native_evidence']['records'][0]['case_id'] = 'control-1'; trials.append(substituted)
        extra = copy.deepcopy(evidence)
        unscheduled = copy.deepcopy(extra['approved_native_evidence']['records'][0]); unscheduled['case_id'] = 'control-1'
        extra['approved_native_evidence']['records'].append(unscheduled)
        extra['approved_native_evidence']['record_count'] = 2; trials.append(extra)
        wrong_count = copy.deepcopy(evidence); wrong_count['approved_native_evidence']['record_count'] = True; trials.append(wrong_count)
        wrong_state = copy.deepcopy(evidence); wrong_state['native_publication_status'] = 'OFFLINE_NATIVE_EXPORT_REJECTED_GATE_CLOSED'; trials.append(wrong_state)
        for value in trials:
            with self.subTest(value=value.get('native_publication_status')):
                with self.assertRaises(ValueError): p.validate_phase1_gate(package, value, review(package, value), original_receipt=receipt, original_native_bundle=bundle)
        self.assertTrue(p.validate_phase1_gate(package, evidence, review(package, evidence), original_receipt=receipt, original_native_bundle=bundle))

    def test_affirmative_rehash_cannot_substitute_native_arguments_results_or_sources(self):
        receipt, evidence, package, _, _, bundle = self.chain(plan(op()))
        def recommit(value):
            record = value['approved_native_evidence']['records'][0]
            operations = record['operations']
            for operation in operations:
                operation['arguments_sha256'] = r.digest(operation['source_validated_arguments'])
                operation['native_output_sha256'] = r.digest(operation['native_result_and_policy'])
            capture = reference.private_native_review(package.cases[0], dict(
                plan={'operations': [operation['source_validated_arguments'] for operation in operations]},
                operations=[operation['native_result_and_policy'] for operation in operations]))
            record['private_native_review_sha256'] = r.digest(capture)
            record['native_projection_sha256'] = native.published_projection_sha256(record)
            value['arms'][0].update(native_review_sha256=record['private_native_review_sha256'],
                                    native_projection_sha256=record['native_projection_sha256'])
        mutations = [lambda rec: rec['operations'][0]['native_result_and_policy'].update(status='FORGED_NATIVE_SUCCESS'),
                     lambda rec: rec['operations'][0]['source_validated_arguments'].update(question='What does Other believe?'),
                     lambda rec: rec['source_roots'][0].update(text_sha256='d'*64),
                     lambda rec: rec['source_roots'][0].update(version=2),
                     lambda rec: rec.update(original_question_sha256='d'*64),
                     lambda rec: rec.update(runtime_sha256='d'*64),
                     lambda rec: rec.update(actual_operation_count=2),
                     lambda rec: rec.update(actual_executed_count=2)]
        for mutate in mutations:
            value = copy.deepcopy(evidence); mutate(value['approved_native_evidence']['records'][0]); recommit(value)
            with self.assertRaises(ValueError): p.validate_phase1_gate(package, value, review(package, value), original_receipt=receipt, original_native_bundle=bundle)

    def test_success_requires_separately_supplied_original_receipt_and_capture(self):
        receipt, evidence, package, _, binding, bundle = self.chain(plan(op()))
        with self.assertRaises(TypeError): p.validate_phase1_gate(package, evidence, binding)
        for originals in (dict(original_receipt=None, original_native_bundle=bundle),
                          dict(original_receipt=receipt, original_native_bundle=None)):
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_DURABLE_RECEIPT_AND_CAPTURE_REQUIRED'):
                p.validate_phase1_gate(package, evidence, binding, **originals)
        changed_receipt = copy.deepcopy(receipt); changed_receipt['elapsed_seconds'] += 0.01
        with self.assertRaisesRegex(ValueError, 'EXACT_ORIGINAL_DURABLE_RECEIPT_HASH_REQUIRED'):
            p.validate_phase1_gate(package, evidence, binding, original_receipt=changed_receipt, original_native_bundle=bundle)
        changed_capture = copy.deepcopy(bundle)
        changed_capture['reviews'][0]['validated_operation_arguments'][0]['question'] = 'What does Mira believe?'
        with self.assertRaisesRegex(ValueError, 'EXACT_RECEIPT_NATIVE_CAPTURE_HASH_REQUIRED'):
            p.validate_phase1_gate(package, evidence, binding, original_receipt=receipt, original_native_bundle=changed_capture)
        boolean_stage = copy.deepcopy(bundle); boolean_stage['stage'] = True
        with self.assertRaisesRegex(ValueError, 'EXACT_OFFLINE_NATIVE_BUNDLE_REQUIRED'):
            p.export(receipt, package, native_bundle=boolean_stage)
        self.assertTrue(p.validate_phase1_gate(package, evidence, binding,
            original_receipt=receipt, original_native_bundle=bundle))

    def test_legitimate_native_swap_cannot_rewrite_original_durable_execution(self):
        receipt, evidence, package, _, _, bundle = self.chain(plan(op()))
        for question in ('What does Mira believe?', 'What does Mira want?',
                         'What does Mira explicitly report? Different operation question.'):
            with self.subTest(question=question):
                changed = copy.deepcopy(evidence)
                old_record = changed['approved_native_evidence']['records'][0]
                argument = copy.deepcopy(old_record['operations'][0]['source_validated_arguments'])
                argument['question'] = question
                session = native._session(package.cases[0])
                result = session._execute(argument, package.cases[0]['question'])
                capture = reference.private_native_review(package.cases[0],
                    dict(plan={'operations': [argument]}, operations=[result]))
                record = native.validate_captured_native_record(capture, package.cases[0], package.value['runtime_sha256'])
                changed['approved_native_evidence']['records'] = [record]
                changed['arms'][0].update(native_review_sha256=record['private_native_review_sha256'],
                    native_projection_sha256=record['native_projection_sha256'],
                    entry_requirements=reference.entry_requirements_from_actual(package, package.cases[0], [argument], capture['native_outputs']),
                    selected_capabilities=[argument['capability']],
                    executed_capabilities=[out['capability'] for out in capture['native_outputs'] if out['executed']],
                    checked_treatment=[out['capability'] for out in capture['native_outputs'] if out.get('checked_treatment_present')],
                    native_results=sum(out['executed'] and isinstance(out.get('result'), dict) for out in capture['native_outputs']))
                self.assertNotEqual(record, old_record)
                self.assertEqual(changed['receipt_sha256'], evidence['receipt_sha256'])
                self.assertEqual(changed['calls'][1]['request_sha256'], evidence['calls'][1]['request_sha256'])
                affirmative = review(package, changed)
                # A self-consistent hash link is deliberately not a success proof.
                self.assertTrue(p.validate_review_binding(package, changed, affirmative))
                with self.assertRaisesRegex(ValueError, 'EXACT_ORIGINAL_DURABLE_EXPORT_REQUIRED'):
                    p.validate_phase1_gate(package, changed, affirmative,
                        original_receipt=receipt, original_native_bundle=bundle)

    def test_offline_authority_spend_and_certification_flags_are_exact_at_each_scope(self):
        receipt, evidence, package, _, _, bundle = self.chain(plan(op()))
        false_fields = ('live_execution_authorized', 'efficacy_verified', 'i02_certified')
        mutations = [(key, value) for key in false_fields for value in (True, 0, None)]
        mutations += [('actual_spend_cny', value) for value in ('2.00', 0, None)]
        mutations += [('semantic_certification', False)]  # Wrong output scope.
        for key, value in mutations:
            with self.subTest(scope='public', key=key, value=value):
                changed = copy.deepcopy(evidence); changed[key] = value
                with self.assertRaisesRegex(ValueError, 'EXACT_OFFLINE_FLAGS_AND_SCOPE_REQUIRED'):
                    p.validate_review_binding(package, changed, review(package, changed))
                with self.assertRaisesRegex(ValueError, 'EXACT_OFFLINE_FLAGS_AND_SCOPE_REQUIRED'):
                    p.validate_phase1_gate(package, changed, review(package, changed),
                        original_receipt=receipt, original_native_bundle=bundle)
        for key, value in (('live_execution_authorized', True), ('live_execution_authorized', 0),
                           ('actual_spend_cny', '2.00'), ('actual_spend_cny', 0),
                           ('efficacy_verified', False), ('i02_certified', True)):
            changed = copy.deepcopy(receipt); changed[key] = value
            with self.assertRaisesRegex(ValueError, 'EXACT_OFFLINE_FLAGS_AND_SCOPE_REQUIRED'):
                p.export(changed, package, native_bundle=bundle)
        for key in ('live_execution_authorized', 'actual_spend_cny'):
            changed = copy.deepcopy(receipt); del changed[key]
            with self.assertRaisesRegex(ValueError, 'EXACT_OFFLINE_FLAGS_AND_SCOPE_REQUIRED'):
                p.export(changed, package)
        for key, value in (('live_execution_authorized', True), ('live_execution_authorized', 0),
                           ('semantic_certification', True), ('semantic_certification', 0),
                           ('actual_spend_cny', '0'), ('efficacy_verified', False), ('i02_certified', False)):
            changed = copy.deepcopy(evidence); changed['approved_native_evidence'][key] = value
            with self.assertRaisesRegex(ValueError, 'EXACT_OFFLINE_FLAGS_AND_SCOPE_REQUIRED'):
                p.validate_review_binding(package, changed, review(package, changed))
            with self.assertRaises(ValueError):
                p.validate_phase1_gate(package, changed, review(package, changed),
                    original_receipt=receipt, original_native_bundle=bundle)

    def test_live_like_clients_subclasses_and_old_packages_refuse_before_io(self):
        package = r.OfflinePackage.build(packet(), ROOT)
        class TouchesAccount:
            offline_synthetic = True
            @property
            def chat(self): raise AssertionError('ACCOUNT_OR_SDK_MUST_NOT_BE_TOUCHED')
            def __getattribute__(self, name):
                raise AssertionError('CLIENT_ATTRIBUTES_MUST_NOT_BE_READ')
        class FakeSubclass(r.FakeClient): pass
        with tempfile.TemporaryDirectory() as directory:
            for client in (TouchesAccount(), FakeSubclass(), object(), None):
                with self.assertRaisesRegex(ValueError, 'EXACT_DETERMINISTIC_FAKE_CLIENT_REQUIRED'):
                    r.run_offline(client, package, 1, Path(directory)/'never')
                self.assertFalse((Path(directory)/'never').exists())
            old_package = reference.OfflinePackage.build(packet(), ROOT)
            with self.assertRaisesRegex(ValueError, 'EXACT_OFFLINE_DIAGNOSTIC_PACKAGE_REQUIRED'):
                r.run_offline(r.FakeClient(), old_package, 1, Path(directory)/'never')
            self.assertFalse((Path(directory)/'never').exists())
        self.assertNotEqual(r.AUTH, reference.AUTH)
        self.assertNotIn(reference.AUTH, json.dumps(package.value))
        self.assertFalse(hasattr(r, 'run'))

    def test_fresh_complete_chain_never_imports_sdk_account_or_live_cli(self):
        # Isolate the assertion from other suites legitimately importing their
        # own account test module during unittest discovery.
        code = """
import json, sys
from pathlib import Path
class DenyLiveImports:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] == 'openai' or fullname in ('scripts.two_stage_account', 'scripts.two_stage_price', 'hcl_entry_contract_smoke_cli'):
            raise AssertionError('NO_SDK_ACCOUNT_OR_LIVE_CLI_IMPORT')
sys.meta_path.insert(0, DenyLiveImports())
from scripts import hcl_offline_diagnostic_export_v1 as r, hcl_offline_diagnostic_public_v1 as p
package = r.OfflinePackage.build(json.loads(sys.argv[1]), Path.cwd())
client = r.FakeClient(['not JSON'])
r.run_offline(client, package, 1, sys.argv[2])
evidence = p.export_terminal(sys.argv[2], package)
assert evidence['provider_calls'] == 0 and evidence['offline_transport_calls'] == 1
assert evidence['actual_spend_cny'] == '0'
"""
        with tempfile.TemporaryDirectory() as parent:
            completed = subprocess.run([sys.executable, '-c', code, json.dumps(packet()), str(Path(parent)/'run')],
                                       cwd=ROOT, capture_output=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_reference_loader_rejects_unknown_names_before_filesystem_access(self):
        class Spoof(str): pass
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('MUST_NOT_READ_UNKNOWN_PATH')) as read:
            for name in ('unknown', '../hcl_entry_contract_smoke_candidate', '/tmp/private',
                         Spoof('hcl_entry_contract_smoke_candidate'), None, []):
                with self.assertRaisesRegex(ValueError, 'EXACT_ARCHIVED_HELPER_NAME_REQUIRED'):
                    refs._load(name)
            read.assert_not_called()

    def test_unique_implicit_actor_offset_matches_explicit_capture_without_repair(self):
        source = packet('Mira: I opened the gate.\nNarrator: The animals escaped.',
                        'For this analysis, responsibility requires causal contribution. Was Mira responsible?',
                        'B01', (('belief', 'Mira: I believe the box is blue.'),))
        outputs = []
        for binding in (actor(), actor(start=0)):
            chain = self.chain(plan(op(source_ids=['belief']), op('G02', question='Assess the original caller rule.', bindings=[binding])), source_packet=source)
            receipt, evidence, package, client, review_value, bundle = chain
            self.assertEqual(evidence['arms'][0]['status'], 'ANSWER_ACCEPTED')
            self.assertIsNone(evidence['arms'][0]['orchestration_failure'])
            argument = bundle['reviews'][0]['validated_operation_arguments'][1]
            self.assertEqual(argument['bindings'][0]['start'], 0)
            final = json.loads(client.calls[1]['messages'][-1]['content'])
            self.assertEqual(final['hcl_plan']['operations'][1], argument)
            record = evidence['approved_native_evidence']['records'][0]
            self.assertEqual(record['operations'][1]['source_validated_arguments'], argument)
            outputs.append((argument, bundle['reviews'][0]['native_outputs'], record))
        self.assertEqual(outputs[0], outputs[1])
        # Even with recomputed capture hash, omission fails the unchanged exporter;
        # source normalization belongs solely to runtime plan admission.
        changed = copy.deepcopy(bundle)
        del changed['reviews'][0]['validated_operation_arguments'][1]['bindings'][0]['start']
        with self.assertRaises(ValueError): native.validate_captured_native_record(changed['reviews'][0], package.cases[0], package.value['runtime_sha256'])

    def test_ambiguous_overlapping_wrong_source_and_invalid_offsets_never_dispatch(self):
        trials = [('Mira met Mira.', actor()), ('aaaa', actor(quote='aaa')),
                  ('Mira left.', actor(source_id='wrong')),
                  ('\U0001f33fe\u0301\r\nMira left.', actor(quote='é')),
                  ('Mira left.', actor(quote=' Mira')), ('Mira left.', actor(quote='mira'))]
        trials += [('Mira left.', actor(start=value)) for value in (None, False, True, 0.0, '0', -1, 1, 999999)]
        for text, binding in trials:
            with self.subTest(text=text, binding=binding):
                source = packet(text, 'Was Mira responsible?', 'G02')
                chain = self.chain(plan(op('G02', bindings=[binding])), source_packet=source)
                expected = 'unsupported binding or source' if binding['source_id'] == 'wrong' else 'invented or stale source anchor'
                self.assert_failure(chain, expected, 'PLANNING_RESPONSE_VALIDATION')
                self.assertEqual(chain[1]['arms'][0]['executed_capabilities'], [])

    def test_explicit_repeated_offsets_unicode_and_named_source_only(self):
        for text, binding, extra in [('Mira met Mira.', actor(start=9), ()),
                                      ('\U0001f33fe\u0301\r\nMira left.', actor(), (('other', 'Mira arrived.'),))]:
            source = packet(text, 'For this analysis, responsibility requires causal contribution. Was Mira responsible?', 'G02', extra)
            chain = self.chain(plan(op('G02', bindings=[binding])), source_packet=source)
            argument = chain[5]['reviews'][0]['validated_operation_arguments'][0]
            normalized = argument['bindings'][0]
            self.assertEqual(normalized['start'], 9 if text.startswith('Mira') else 5)
            self.assertEqual(text[normalized['start']:normalized['start']+len(normalized['quote'])], 'Mira')
        chain = self.chain(plan(op('G02', bindings=[actor()])), source_packet=packet('Someone left.', family='G02', extra_sources=(('other', 'Mira left.'),)))
        self.assert_failure(chain, 'invented or stale source anchor', 'PLANNING_RESPONSE_VALIDATION')

    def test_exact_36000_planning_request_full_sources_and_quotes_survive_chain(self):
        base = packet(); package = r.OfflinePackage.build(base, ROOT)
        initial = next(iter(package.value['requests'].values()))['full_request_utf8_bytes']
        source = base['cases'][0]['model_input']['sources'][0]
        source['text'] += 'x'*(36000-initial)
        # Source entry blocker descriptions may change with the larger complete
        # source. Measure the actual prompt again; never assume additive sizes.
        source['text_sha256'] = hashlib.sha256(source['text'].encode()).hexdigest()
        actual_case = reference.normalized_cases(base)[0]
        actual = len(r.request_and_metrics('planning', r.messages(actual_case, 'HCL'))[1])
        if actual > 36000: source['text'] = source['text'][:-(actual-36000)]
        source['text_sha256'] = hashlib.sha256(source['text'].encode()).hexdigest()
        chain = self.chain(plan(), source_packet=base)
        self.assert_failure(chain, 'NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER', 'NATIVE_RESULT_ADMISSION')
        call = chain[0]['calls'][0]
        self.assertEqual(call['request_bytes'], 36000)
        self.assertEqual(Decimal(call['reserved_cny']), r.quote(36000, 'planning'))
        self.assertEqual(json.loads(chain[3].calls[0]['messages'][-1]['content'])['sources'][0]['text'], source['text'])
        source['text'] += 'x'; source['text_sha256'] = hashlib.sha256(source['text'].encode()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'STATIC_REQUEST_EXCEEDS_BOUND'): r.OfflinePackage.build(base, ROOT)

    def test_package_drift_and_second_stage_cannot_create_output(self):
        package = r.OfflinePackage.build(packet(), ROOT)
        with tempfile.TemporaryDirectory() as parent:
            for stage in (2, True):
                with self.assertRaisesRegex(ValueError, 'SINGLE_SMOKE_NO_SECOND_STAGE'):
                    r.run_offline(r.FakeClient(), package, stage, Path(parent)/'never')
                self.assertFalse((Path(parent)/'never').exists())
            package.value['phase_holds_cny']['planning'] = '0'
            with self.assertRaisesRegex(ValueError, 'OFFLINE_PACKAGE_OR_RUNTIME_DRIFT'):
                r.run_offline(r.FakeClient(), package, 1, Path(parent)/'never')
            self.assertFalse((Path(parent)/'never').exists())

    def test_real_large_native_context_stops_before_final_reservation(self):
        source = packet('\n'.join('Mira: I believe item '+str(i)+' is blue.' for i in range(10)))
        chain = self.chain(plan(op()), source_packet=source)
        arm = self.assert_failure(chain, 'METERED_BACKEND_OR_JOURNAL_FAILED', 'FINAL_PROVIDER_ADMISSION')
        self.assertEqual(arm['status'], 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION')
        self.assertEqual(arm['native_results'], 1)
        self.assertEqual(arm['checked_treatment'], ['B01'])
        self.assertGreater(arm['final_request_full_utf8_bytes'], 36000)
        self.assertEqual(arm['request_bound_failure_phase'], 'answer')
        self.assertEqual([row['phase'] for row in chain[0]['calls']], ['planning'])
        self.assertEqual(chain[0]['reserved_cny'], str(r.HOLD_CNY['planning']))
        self.assertEqual(chain[5]['reviews'][0]['source_roots'][0]['text_sha256'], hashlib.sha256(source['cases'][0]['model_input']['sources'][0]['text'].encode()).hexdigest())

    def test_source_changes_and_withdrawals_keep_runtime_stops_after_real_fake_calls(self):
        answer = universal_entry.UniversalHCL.answer
        complete = r.BoundedPort.complete
        for phase in ('planning', 'answer'):
            for withdrawn in (False, True):
                with self.subTest(phase=phase, withdrawn=withdrawn):
                    def change_during_answer(session, *args, **kwargs):
                        def send(port, current, prompt):
                            value = complete(port, current, prompt)
                            if current == phase:
                                if withdrawn: session.workspace.core.withdraw(session.workspace._spans[SID])
                                else: session.put_source(SID, 'Mira stayed outside.')
                            return value
                        with patch.object(r.BoundedPort, 'complete', send):
                            return answer(session, *args, **kwargs)
                    chain = self.chain(plan(op()), context=patch.object(universal_entry.UniversalHCL, 'answer', change_during_answer))
                    self.assert_failure(chain, 'SOURCE_SUPPORT_CHANGED' if withdrawn else 'SOURCE_CHANGED_DURING_ORCHESTRATION',
                        'PLANNING_RESPONSE_VALIDATION' if phase == 'planning' else 'FINAL_RESPONSE_VALIDATION',
                        1 if phase == 'planning' else 2)

    def test_nonrecyclable_holds_and_call_accounting_reject_mutation(self):
        receipt, evidence, package, *_ = self.chain(plan(op()))
        for mutate in (lambda x: x.update(reserved_cny='0'),
                       lambda x: x['calls'][0].update(reserved_cny='0'),
                       lambda x: x['calls'][0].update(exact_request_reservation_cny='0'),
                       lambda x: x['calls'][0].update(provider_call=True),
                       lambda x: x['calls'][0].update(usage_rated_cny='0'),
                       lambda x: x['calls'].append(dict(x['calls'][0])),
                       lambda x: x['calls'][0].update(request_sha256='0'*64)):
            changed = copy.deepcopy(receipt); mutate(changed)
            with self.assertRaises(ValueError): p.export(changed, package)

    def test_privacy_scope_keeps_approved_sources_but_never_copies_them_into_diagnostics(self):
        public_source = 'APPROVED_SYNTHETIC_SOURCE_CANARY'
        chain = self.chain('{'+CANARY, source_packet=packet(public_source))
        self.assertIn(public_source, json.dumps(chain[1]['cases']))
        self.assertNotIn(public_source, json.dumps(chain[1]['arms'][0]['orchestration_failure']))
        self.assertNotIn(CANARY, json.dumps(chain[1]))


if __name__ == '__main__': unittest.main()
