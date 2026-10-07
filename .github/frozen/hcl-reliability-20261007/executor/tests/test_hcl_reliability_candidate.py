"""Provider-free control-flow/adversarial tests. No model quality conclusions."""
from contextlib import ExitStack
import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import hcl_reliability_candidate as r
import hcl_reliability_public as p
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort, MeteredPortError

RUNTIME = Path(__import__('hcl').__file__).resolve().parent.parent
NOW = datetime(2026, 10, 7, 4, tzinfo=timezone.utc)


def fixture_packet():
    """Unrelated synthetic harness fixture, never one of the authored live cases."""
    rows = []
    for index in range(5):
        sources = []
        for j in range(2 if index == 1 else 1):
            text = 'Mira: I believe the box is blue.\nMira: I want to inspect the box.' + ('\nNo receipt of the update is recorded.' if j else '')
            sources.append(dict(source_id=f'control-source-{index}-{j}', version=1, text=text, title='Control fixture', complete=True, text_sha256=hashlib.sha256(text.encode()).hexdigest()))
        evaluation = dict(key_fact_obligations=[dict(id=f'K{x}', obligation='CONTROL_RUBRIC_NEVER_MODEL') for x in range(1, 5)], inference_boundary_obligations=[dict(id=f'I{x}', obligation='CONTROL_RUBRIC_NEVER_MODEL') for x in range(1, 4)], citation_source_obligations=[dict(id=f'C{x}', obligation='CONTROL_RUBRIC_NEVER_MODEL') for x in range(1, 4)], scores_and_results=None, predeclared_acceptable_relevant_native_operation_families=[dict(capability_id='B01')])
        if index == 0:
            evaluation.update(smoke_semantic_requirements=[dict(id=f'S{x}', requirement='CONTROL_SEMANTIC_NEVER_MODEL') for x in range(1, 5)], smoke_semantic_results=None)
        rows.append(dict(case_id=f'control-{index}', role='smoke' if index == 0 else 'comparison', model_input=dict(question='What does Mira explicitly report?', sources=sources), private_evaluation=evaluation))
    return dict(authored_at_utc='2026-10-07T03:42:00Z', cases=rows)


class Client:
    offline_synthetic = True
    base_url = 'https://api.deepseek.com'
    max_retries = 0
    timeout = 180
    def __init__(self, mutate=None, empty=False):
        self.calls = []; self.mutate = mutate; self.empty = empty
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
    def create(self, **request):
        self.calls.append(copy.deepcopy(request))
        payload = json.loads(request['messages'][-1]['content']); source = payload['sources'][0]
        if request['max_tokens'] == 4096:
            content = dict(task='Interpret the ordinary control question.', operations=[] if self.empty else [dict(capability='B01', question='What does Mira explicitly report?', source_ids=[source['source_id']], bindings=[])], limitations=[])
        else:
            content = dict(answer='Mira reports that the box is blue. This is a stated belief, not an independent inspection.', source_citations=[dict(source_id=s['source_id'], version=s['version'], quote=s['text'], start=0) for s in payload['sources']], uncertainty='The actual color is not independently established.', assumptions='No extra evidence.')
        result = dict(model=r.MODEL, usage=dict(prompt_tokens=100, completion_tokens=100, total_tokens=200), choices=[dict(finish_reason='stop', message=dict(content=json.dumps(content), reasoning_content='SECRET_REASONING_CANARY'))], envelope_private='ENVELOPE_PRIVATE_CANARY')
        if self.mutate:
            self.mutate(result, len(self.calls), request)
        return result


def native_permission_fixture(package):
    from hcl_reliability_native_public import DESTINATION, PERMISSION_SCOPE
    return dict(schema='hcl-reliability-native-public-permission-v1', authorization_ref=r.AUTH, approval_message_ref='OFFLINE_TEST_ONLY_NOT_OWNER_APPROVAL', destination=DESTINATION, packet_sha256=package.value['packet_sha256'], scope=PERMISSION_SCOPE, maximum_case_records=5, maximum_operations_per_record=3, maximum_record_utf8_bytes=1048576)


def review_fixture(package, evidence):
    """Synthetic pass booleans only exercise gate mechanics; not real review."""
    arm = evidence['arms'][0]
    def checks(ids):
        return [dict(id=i, passed=True, source_evidence='SYNTHETIC_CONTROL_SOURCE_REVIEW_ONLY', answer_evidence='SYNTHETIC_CONTROL_ANSWER_REVIEW_ONLY') for i in ids]
    value = dict(schema='hcl-reliability-source-review-candidate-v1', authorization_ref=r.AUTH, package_sha256=r.digest(package.value), packet_sha256=r.digest(package.packet), evidence_sha256=r.digest(evidence), final_answer_sha256=arm['final_answer_sha256'], request_diagnostics_sha256=r.digest(arm['request_diagnostics']), native_review_sha256=arm['native_review_sha256'], reviewer_role='INDEPENDENT_SOURCE_FIRST_AFTER_OUTPUT', all_five_cases_and_rubrics_frozen_before_any_output=True, gates={key: True for key in p.GATES}, obligations=checks(p.obligation_ids(package.packet['cases'][0])), smoke_semantics=checks(['S1', 'S2', 'S3', 'S4']), relevant_native_capability_ids=['B01'], critical_failure_tags=[], overall_pass=True)
    if type(package) is r.FrozenPackage: value['approved_native_evidence_sha256'] = r.digest(evidence['approved_native_evidence'])
    return value


def write_review_fixture_artifacts(package):
    """Actual byte-hashed target-bound artifacts for unrelated offline controls."""
    import hcl_reliability_reviews as reviews
    root = Path(package.runtime_root); value = package.value
    r.save(root / reviews.CASE_FILE, package.packet)
    value['case_raw_file_sha256'] = r.file_sha(root / reviews.CASE_FILE)
    targets = dict(case_raw_file_sha256=value['case_raw_file_sha256'], case_canonical_packet_sha256=value['packet_sha256'], runtime_sha256=value['runtime_sha256'], runtime_commit=value['runtime_commit'])
    case = dict(schema='hcl-reliability-independent-case-review-v1', verdict='PASS_FOR_BOUNDED_DEVELOPMENT_ONLY', reviewer_role='INDEPENDENT_SOURCE_FIRST_PRE_OUTPUT', **targets, checks={key: True for key in reviews.CASE_CHECKS}, evidence_sha256={'offline_control_fixture_only': 'd' * 64}, provider_calls=0, live_execution_authorized=False, efficacy_claimed=False)
    r.save(root / reviews.CASE_REVIEW, case)
    value['independent_case_review_sha256'] = r.file_sha(root / reviews.CASE_REVIEW)
    executor = dict(schema='hcl-reliability-independent-executor-approval-v1', verdict='PASS_FOR_BOUNDED_EXECUTOR_PACKAGE', reviewer_role='INDEPENDENT_READ_ONLY_SECURITY_REVIEW', **targets, case_review_file_sha256=value['independent_case_review_sha256'], executor_files_sha256=value['configuration']['executor_files'], workflow_files_sha256=value['workflow_files'], read_only_reader_files_sha256=value['read_only_reader_files'], checks={key: True for key in reviews.EXECUTOR_CHECKS}, verification=dict(provider_calls=0, account_queries=0, credentials_read=False, sdk_constructed=False, provider_free_tests_passed=62), live_execution_authorized=False)
    r.save(root / reviews.EXECUTOR_REVIEW, executor)
    value['independent_executor_review_sha256'] = r.file_sha(root / reviews.EXECUTOR_REVIEW)
    return package


def execute(client=None, stage=1, package=None, **kwargs):
    package = package or r.OfflinePackage.build(fixture_packet(), RUNTIME)
    if stage == 2:
        first, _ = execute(Client(), 1, package)
        evidence = p.export(first, package); review = review_fixture(package, evidence)
        kwargs.update(phase1_evidence=evidence, phase1_review=review, phase1_review_sha256=r.digest(review))
    with tempfile.TemporaryDirectory() as directory:
        result = r.run_offline(client or Client(), package, stage, Path(directory) / 'run', clock=lambda: NOW, **kwargs)
        assert result == json.loads((Path(directory) / 'run' / 'receipt.json').read_text())
    return result, package


class RequestParity(unittest.TestCase):
    def test_exact_ordinary_request_for_unicode_escaping_phases_and_lengths(self):
        client = Client(); ordinary = DeepSeekMeteredPort(client, maximum_wait_seconds=180)
        samples = ['', 'ASCII', '中文🧠é', 'quote"\\\n\r\t', '\u2028\u2029', 'é' * 1000, 'a' * 35000, '𠜎' * 2000]
        for phase in ('planning', 'answer'):
            for text in samples:
                prompt = [dict(role='system', content='Trusted policy'), dict(role='user', content=json.dumps(dict(question=text, sources=[]), ensure_ascii=False, sort_keys=True))]
                with self.subTest(phase=phase, textlen=len(text)):
                    expected, encoded = ordinary.request(phase, prompt)
                    actual, actual_bytes, metrics = r.request_and_metrics(phase, prompt)
                    self.assertEqual(actual, expected); self.assertEqual(actual_bytes, encoded)
                    self.assertEqual(metrics['full_request_utf8_bytes'], len(encoded))
                    self.assertEqual(metrics['full_request_sha256'], hashlib.sha256(encoded).hexdigest())
                    self.assertGreater(len(encoded), metrics['serialized_messages_utf8_bytes'])

    def test_exact_36000_byte_boundary_and_oversized_actual_hash(self):
        ordinary = DeepSeekMeteredPort(Client())
        for phase in r.TOKENS:
            base = [dict(role='user', content='')]
            overhead = len(r.request_and_metrics(phase, base)[1])
            for n in (35999, 36000, 36001, 52000):
                prompt = [dict(role='user', content='x' * (n - overhead))]
                request, encoded, metric = r.request_and_metrics(phase, prompt)
                self.assertEqual(len(encoded), n); self.assertEqual(metric['within_request_bound'], n <= 36000)
                if n <= 36000:
                    self.assertEqual(ordinary.request(phase, prompt), (request, encoded))
                else:
                    with self.assertRaisesRegex(MeteredPortError, 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION'):
                        ordinary.request(phase, prompt)
                    self.assertEqual(metric['full_request_sha256'], hashlib.sha256(encoded).hexdigest())

    def test_schema_rejection_matches_ordinary_for_missing_extra_and_invalid_messages(self):
        ordinary = DeepSeekMeteredPort(Client())
        trials = [('wrong', []), ('answer', None), ('answer', []), ('answer', ()), ('planning', [{}]), ('answer', [dict(role='user')]), ('answer', [dict(content='a')]), ('answer', [dict(role='tool', content='a')]), ('answer', [dict(role='user', content=None)]), ('answer', [dict(role='user', content='a', extra='secret')]), ('answer', ['text'])]
        for phase, prompt in trials:
            with self.subTest(phase=phase, prompt=prompt):
                with self.assertRaises(MeteredPortError) as expected: ordinary.request(phase, prompt)
                with self.assertRaises(MeteredPortError) as actual: r.request_and_metrics(phase, prompt)
                self.assertEqual(expected.exception.args, actual.exception.args)

    def test_frozen_planner_prompt_exactly_matches_current_ordinary_runtime(self):
        for case in r.normalized_cases(fixture_packet()):
            captured = []
            class CaptureOnly:
                provider_free = True
                def reservation_usd(self, phase, prompt):
                    captured.append((phase, copy.deepcopy(prompt)))
                    raise ValueError('OFFLINE_CAPTURE_NO_CALL')
            session = r.UniversalHCL()
            for source in case['sources']:
                session.put_source(source['source_id'], source['text']); session.sources[source['source_id']] = dict(source)
            port = CaptureOnly()
            session.answer(case['question'], planner_backend=port, answer_backend=port, allowance=r.CallAllowance(2, 1, 'OFFLINE_CONTROL_ONLY'))
            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0], ('planning', r.messages(case, 'HCL')))

    def test_unpaired_surrogate_never_repaired_or_transmitted(self):
        prompt = [dict(role='user', content='\ud800')]
        for fn in (r.request_and_metrics, DeepSeekMeteredPort(Client()).request):
            with self.assertRaises(UnicodeEncodeError): fn('answer', prompt)

    def test_price_reserves_true_usd_and_cny_units(self):
        for phase in r.TOKENS:
            self.assertEqual(r.quote(36000, phase), r.HOLD_CNY[phase])
            self.assertEqual(r.quote(36000, phase, currency='USD'), r.HOLD_USD[phase])
            self.assertNotEqual(r.HOLD_CNY[phase], r.HOLD_USD[phase])
        self.assertEqual(sum(r.SCHEDULE_CNY.values()), Decimal('11.885760'))
        self.assertLess(r.SCHEDULE_CNY[1], Decimal('1.70'))
        self.assertLess(r.SCHEDULE_CNY[2], Decimal('10.30'))


class RunTests(unittest.TestCase):
    def test_five_cases_whole_rubric_packet_frozen_and_multi_source_retained(self):
        package = r.OfflinePackage.build(fixture_packet(), RUNTIME)
        self.assertEqual(len(package.cases), 5); self.assertEqual(len(package.cases[1]['sources']), 2)
        self.assertEqual(len(package.value['requests']), 9)
        self.assertEqual(package.value['planning_tokens'], 4096)
        self.assertIn('final_runtime_sha256', package.value['unresolved_final_freeze_fields'])
        package.packet['cases'][1]['private_evaluation']['key_fact_obligations'][0]['obligation'] += ' drift'
        with self.assertRaisesRegex(ValueError, 'DRIFT'): package.verify()

    def test_frozen_preparation_time_is_explicitly_not_actual_ingestion_or_event_time(self):
        package = r.OfflinePackage.build(fixture_packet(), RUNTIME)
        for case in package.cases:
            for source in case['sources']:
                self.assertEqual(source['recorded_at'], package.packet['authored_at_utc'])
                self.assertEqual(source['record_time_basis'], r.FROZEN_SOURCE_TIME_BASIS)
                self.assertNotEqual(source['record_time_basis'], 'ACTUAL_INGESTION_NOT_EVENT_TIME')
        self.assertEqual(package.value['source_recorded_at_basis'], r.FROZEN_SOURCE_TIME_BASIS)

    def test_live_client_rejected_before_ledger_or_call(self):
        client = Client(); client.offline_synthetic = False
        package = r.OfflinePackage.build(fixture_packet(), RUNTIME)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run'
            with self.assertRaisesRegex(ValueError, 'LIVE_EXECUTION_UNAVAILABLE'):
                r.run_offline(client, package, 1, path, clock=lambda: NOW)
            self.assertFalse(path.exists()); self.assertEqual(client.calls, [])

    def test_complete_one_then_fixed_four_pairs_same_input_no_evaluator_leak(self):
        for stage, n in ((1, 2), (2, 12)):
            client = Client(); result, package = execute(client, stage)
            self.assertEqual(len(client.calls), n)
            self.assertEqual(result['status'], 'COMPLETED_ONE_PASS')
            self.assertTrue(all(a['status'] == 'ANSWER_ACCEPTED' for a in result['arms']))
            output = p.export(result, package)
            self.assertEqual(output['provider_calls'], 0); self.assertEqual(output['actual_spend_cny'], '0')
            self.assertEqual(output['offline_transport_calls'], n)
            self.assertEqual(Decimal(output['reserved_cny']), r.SCHEDULE_CNY[stage])
            self.assertEqual([tuple(x) for x in package.value['stage_orders'][str(stage)]], [(a['case_id'], a['arm']) for a in output['arms']])
            for request in client.calls:
                serialized = json.dumps(request)
                self.assertNotIn('CONTROL_RUBRIC_NEVER_MODEL', serialized); self.assertNotIn('CONTROL_SEMANTIC_NEVER_MODEL', serialized)
                self.assertEqual(request['reasoning_effort'], 'high'); self.assertEqual(request['extra_body'], {'thinking': {'type': 'enabled'}})
                self.assertIn(request['max_tokens'], (4096, 8192))
                payload = json.loads(request['messages'][-1]['content'])
                case = next(x for x in package.cases if x['sources'][0]['source_id'] == payload['sources'][0]['source_id'])
                self.assertEqual([(s['source_id'], s['version'], s['text']) for s in payload['sources']], [(s['source_id'], s['version'], s['text']) for s in case['sources']])
            serialized = json.dumps(output)
            self.assertNotIn('SECRET_REASONING_CANARY', serialized); self.assertNotIn('ENVELOPE_PRIVATE_CANARY', serialized)
            self.assertNotIn('raw_plan', serialized)

    def test_invalid_final_json_retained_without_retry(self):
        def mutate(result, i, request):
            if request['max_tokens'] == 8192: result['choices'][0]['message']['content'] = '{original bad JSON'
        for stage, n in ((1, 2), (2, 12)):
            client = Client(mutate); result, package = execute(client, stage); output = p.export(result, package)
            self.assertEqual(len(client.calls), n)
            self.assertTrue(all(a['final_text'] == '{original bad JSON' and a['final_fields'] is None for a in output['arms']))
            self.assertEqual(output['status'], 'STOPPED_NO_RETRY' if stage == 1 else 'COMPLETED_ONE_PASS')

    def test_finish_length_stays_failure_even_complete_looking_json(self):
        def mutate(result, i, request):
            if request['max_tokens'] == 8192: result['choices'][0]['finish_reason'] = 'length'
        result, package = execute(Client(mutate)); output = p.export(result, package)
        self.assertEqual(output['arms'][0]['status'], 'INCOMPLETE_ANSWER_NO_RETRY')
        self.assertIsNotNone(output['arms'][0]['final_text']); self.assertNotEqual(output['arms'][0]['final_delivery_code'], 'DELIVERED')
        self.assertTrue(output['usage_complete'])

    def test_missing_usage_preserves_original_final_full_hold_and_unattempted_slots(self):
        def mutate(result, i, request):
            result['choices'][0]['message']['content'] = '{visible but no usage'
            result.pop('usage')
        client = Client(mutate); result, package = execute(client, 2); output = p.export(result, package)
        self.assertEqual(len(client.calls), 1); self.assertEqual(output['reserved_cny'], str(r.HOLD_CNY['answer']))
        self.assertFalse(output['usage_complete']); self.assertIsNone(output['simulated_usage_rated_cny'])
        self.assertEqual(output['arms'][0]['final_text'], '{visible but no usage')
        self.assertTrue(all(a['status'] == 'NOT_ATTEMPTED' for a in output['arms'][1:]))
        positions = p.fixed_denominator_positions(output)
        self.assertEqual(positions['fixed_pair_denominator'], 4); self.assertEqual(len(positions['positions']), 8)
        self.assertTrue(all(x['semantic_score'] == 0 for x in positions['positions']))

    def test_dynamic_oversize_captures_full_metrics_and_runtime_fields_no_answer_call(self):
        def large(session, operation, question):
            return dict(capability=operation['capability'], executed=True, result={'large': '中' * 20000}, support_claim_ids=[])
        with patch.object(r.UniversalHCL, '_execute', large):
            client = Client(); result, package = execute(client)
        output = p.export(result, package); arm = output['arms'][0]
        self.assertEqual(len(client.calls), 1); self.assertEqual(arm['status'], 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION')
        answer = next(x for x in arm['request_diagnostics'] if x['phase'] == 'answer')
        self.assertGreater(answer['full_request_utf8_bytes'], 36000)
        self.assertGreater(answer['full_request_utf8_bytes'], answer['serialized_messages_utf8_bytes'])
        self.assertEqual(answer['payload_value_utf8_bytes'], arm['runtime_final_context_metrics']['payload_value_utf8_bytes'])
        self.assertEqual(len(answer['full_request_sha256']), 64)
        self.assertNotIn('中' * 10, json.dumps(output, ensure_ascii=False))

    def test_final_retention_exact_64000_no_truncation(self):
        for size in (64000, 64001):
            def mutate(result, i, request):
                if request['max_tokens'] == 8192: result['choices'][0]['message']['content'] = 'x' * size
            result, package = execute(Client(mutate)); output = p.export(result, package)
            self.assertEqual(output['arms'][0]['final_text'], 'x' * size if size == 64000 else None)
            self.assertEqual(output['arms'][0]['status'], 'FINAL_SCHEMA_OR_CITATIONS_REJECTED' if size == 64000 else 'CONTENT_BOUND_EXCEEDED')

    def test_empty_native_selection_keeps_failed_positions_without_replacement(self):
        client = Client(empty=True); result, package = execute(client, 2); output = p.export(result, package)
        self.assertEqual(len(client.calls), 8); self.assertEqual(len(output['arms']), 8)
        self.assertEqual(sum(x['status'] == 'ANSWER_ACCEPTED' for x in output['arms']), 4)
        positions = p.fixed_denominator_positions(output)
        self.assertEqual(sum(x['semantic_score'] is None for x in positions['positions']), 4)
        self.assertEqual(sum(x['semantic_score'] == 0 for x in positions['positions']), 4)

    def test_late_timeout_cannot_write_memory_or_terminal_file(self):
        client = Client(); release, done = threading.Event(), threading.Event()
        original = client.chat.completions.create
        def slow(**request):
            if request['max_tokens'] == 8192: release.wait(timeout=2)
            value = original(**request)
            if request['max_tokens'] == 8192:
                value['choices'][0]['message']['content'] = 'LATE_PRIVATE_FINAL'; done.set()
            return value
        client.chat.completions.create = slow
        original_init = r.BoundedPort.__init__
        def short_wait(port, *args): original_init(port, *args); port.maximum_wait_seconds = .03
        package = r.OfflinePackage.build(fixture_packet(), RUNTIME)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run'
            try:
                with patch.object(r.BoundedPort, '__init__', short_wait): result = r.run_offline(client, package, 1, path, clock=lambda: NOW)
                snapshot = copy.deepcopy(result); bytes_before = (path / 'receipt.json').read_bytes()
                self.assertEqual(result['status'], 'STOPPED_NO_RETRY')
                release.set(); self.assertTrue(done.wait(timeout=2)); time.sleep(.03)
                self.assertEqual(result, snapshot); self.assertEqual((path / 'receipt.json').read_bytes(), bytes_before)
                self.assertNotIn(b'LATE_PRIVATE_FINAL', bytes_before)
            finally: release.set()

    def test_known_planning_limit_closes_smoke_no_16k_upgrade(self):
        def mutate(result, i, request): result['choices'][0]['finish_reason'] = 'length'
        client = Client(mutate); result, package = execute(client)
        self.assertEqual(len(client.calls), 1); self.assertEqual(client.calls[0]['max_tokens'], 4096)
        self.assertEqual(result['status'], 'STOPPED_NO_RETRY'); self.assertEqual(result['remaining_authorized_calls'], 0)
        self.assertEqual(p.export(result, package)['reserved_cny'], str(r.HOLD_CNY['planning']))

    def test_source_payload_tamper_is_refused_before_dynamic_send(self):
        original = r.BoundedPort.reservation_usd
        def tamper(port, phase, prompt):
            if phase == 'answer':
                prompt = copy.deepcopy(prompt); payload = json.loads(prompt[-1]['content']); payload['sources'][0]['text'] = 'shortened'; prompt[-1]['content'] = json.dumps(payload)
            return original(port, phase, prompt)
        client = Client()
        with patch.object(r.BoundedPort, 'reservation_usd', tamper): result, package = execute(client)
        self.assertEqual(len(client.calls), 1); self.assertEqual(result['status'], 'STOPPED_NO_RETRY')

    def test_duplicate_directory_cannot_resume_or_reuse_authority(self):
        package = r.OfflinePackage.build(fixture_packet(), RUNTIME)
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'run'; r.run_offline(Client(), package, 1, path, clock=lambda: NOW)
            client = Client()
            with self.assertRaises(FileExistsError): r.run_offline(client, package, 1, path, clock=lambda: NOW)
            self.assertEqual(client.calls, [])

    def test_time_and_stage_send_margin(self):
        for value in (r.timestamp(r.APPROVED) - timedelta(seconds=1), r.timestamp(r.EXPIRES) - timedelta(seconds=180), r.timestamp(r.EXPIRES)):
            with self.assertRaises(ValueError): r.require_time(value)
        r.require_time(r.timestamp(r.EXPIRES) - timedelta(seconds=181))
        client = Client(); ticks = iter([0, 421, 421, 421, 421, 421, 421])
        result, _ = execute(client, monotonic=lambda: next(ticks, 421))
        self.assertEqual(client.calls, []); self.assertEqual(result['status'], 'STOPPED_NO_RETRY')


class GateAndExportTests(unittest.TestCase):
    def setUp(self):
        self.result, self.package = execute()
        self.evidence = p.export(self.result, self.package)
        self.review = review_fixture(self.package, self.evidence)

    def test_linked_gate_requires_every_semantic_obligation_and_native_relevance(self):
        self.assertTrue(p.validate_phase1_gate(self.package, self.evidence, self.review))
        mutations = [lambda x: x.update(overall_pass=False), lambda x: x.update(evidence_sha256='f' * 64), lambda x: x.update(reviewer_role='IMPLEMENTER'), lambda x: x.update(all_five_cases_and_rubrics_frozen_before_any_output=False), lambda x: x['gates'].update(all_key_facts_preserved=False), lambda x: x['gates'].update(relevant_native_execution_passed=False), lambda x: x['obligations'].pop(), lambda x: x['smoke_semantics'][0].update(passed=False), lambda x: x.update(relevant_native_capability_ids=['B02']), lambda x: x.update(critical_failure_tags=['NESTED_POSITION_LOST']), lambda x: x.update(request_diagnostics_sha256='a' * 64)]
        for mutate in mutations:
            review = copy.deepcopy(self.review); mutate(review)
            with self.assertRaises(ValueError): p.validate_phase1_gate(self.package, self.evidence, review)

    def test_stage2_requires_exact_review_hash_and_no_automatic_review(self):
        client = Client()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                r.run_offline(client, self.package, 2, Path(directory) / 'run', phase1_evidence=self.evidence, phase1_review=self.review, phase1_review_sha256='0' * 64, clock=lambda: NOW)
        self.assertEqual(client.calls, [])

    def test_changed_final_fields_hash_currency_and_metric_refused(self):
        mutations = [lambda x: x.update(currency='USD'), lambda x: x.update(usd_reference_only=False), lambda x: x['arms'][0].update(final_text='edited'), lambda x: x['arms'][0].update(final_fields={}), lambda x: x['arms'][0]['request_diagnostics'][0].update(full_request_utf8_bytes=123), lambda x: x['calls'][0].update(reserved_cny=str(r.HOLD_USD['planning'])), lambda x: x['arms'].clear()]
        for mutate in mutations:
            result = copy.deepcopy(self.result); mutate(result)
            with self.assertRaises(ValueError): p.export(result, self.package)

    def test_allowlist_never_copies_private_additions(self):
        result = copy.deepcopy(self.result)
        result.update(api_key='PRIVATE_SECRET_CANARY', balance='PRIVATE_BALANCE_CANARY', raw_plan='PRIVATE_PLAN_CANARY')
        result['calls'][0]['provider_envelope'] = 'PRIVATE_ENVELOPE_CANARY'
        result['arms'][0]['actual_final_messages'] = 'PRIVATE_REQUEST_CANARY'
        exported = json.dumps(p.export(result, self.package))
        for word in ['PRIVATE_SECRET_CANARY', 'PRIVATE_BALANCE_CANARY', 'PRIVATE_PLAN_CANARY', 'PRIVATE_ENVELOPE_CANARY', 'PRIVATE_REQUEST_CANARY']:
            self.assertNotIn(word, exported)

    def test_ledger_full_hold_cannot_recycle_after_low_cost(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = r.Ledger(Path(directory) / 'run', self.package, 1, lambda: NOW, lambda: 0)
            ledger.active = 'control-0:HCL'; port = r.BoundedPort(Client(), ledger, ledger.active)
            port.reservation_usd('planning', r.messages(self.package.cases[0], 'HCL'))
            row = ledger.value['calls'][0]; row['reserved_cny'] = '0.00001'; ledger.value['reserved_cny'] = '0.00001'
            with self.assertRaisesRegex(ValueError, 'FULL_NONRECYCLABLE_HOLD_REQUIRED'): ledger.admit()

    def test_durable_reservation_and_intent_exist_before_fake_sdk_call(self):
        client = Client()
        package = self.package
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'run'; original = client.create
            def inspect(**request):
                current = json.loads((path / 'receipt.json').read_text()); call = current['calls'][-1]
                self.assertEqual(call['invocation_status'], 'INVOKED_OR_SEND_UNKNOWN')
                self.assertEqual(Decimal(call['reserved_cny']), r.HOLD_CNY[call['phase']])
                self.assertEqual(call['status'], 'RESERVED_BEFORE_CALL')
                return original(**request)
            client.chat.completions.create = inspect
            result = r.run_offline(client, package, 1, path, clock=lambda: NOW)
            self.assertEqual(result['status'], 'COMPLETED_ONE_PASS')


class LaunchAndPrecheckTests(unittest.TestCase):
    def launch(self):
        return dict(run_id=42, attempt=1, pages=[dict(total_count=1, workflow_runs=[dict(id=42, workflow_id=7, path='.github/workflows/hcl-reliability-20261007-1-once.yml', head_branch='main', run_attempt=1, head_sha='a' * 40, event='push', created_at=NOW.isoformat())])], workflow_id=7, head_sha='a' * 40, parent_sha='b' * 40, event='push', paths=['.github/HCL_RELIABILITY_20261007_1_TRIGGER.json'], marker=dict(schema='hcl-reliability-marker-proposal-v1', authorization_ref=r.AUTH, stage=1, package_sha256='c' * 64, grant_sha256='d' * 64, executor_commit='e' * 40, grant_commit='b' * 40), package_sha256='c' * 64, grant_sha256='d' * 64, stage=1, executor_commit='e' * 40, grant_commit='b' * 40, executor_ancestor_of_grant=True, grant_changed_paths=['.github/HCL_RELIABILITY_20261007_1_GRANT.json'])

    def test_exact_first_marker_and_complete_new_workflow_history(self):
        self.assertTrue(r.validate_launch_proposal(**self.launch()))
        mutations = [lambda x: x.update(attempt=2), lambda x: x.update(event='workflow_dispatch'), lambda x: x['pages'][0].update(total_count=2), lambda x: x['pages'][0]['workflow_runs'][0].update(run_attempt=2), lambda x: x['pages'][0]['workflow_runs'][0].update(workflow_id=8), lambda x: x['paths'].append('hcl/changed.py'), lambda x: x['marker'].update(authorization_ref='OLD_CONSUMED_AUTHORITY'), lambda x: x['pages'][0]['workflow_runs'].append(dict(x['pages'][0]['workflow_runs'][0])), lambda x: x['pages'][0]['workflow_runs'][0].update(head_sha='e' * 40)]
        for mutate in mutations:
            args = self.launch(); mutate(args)
            with self.assertRaises(ValueError): r.validate_launch_proposal(**args)

    def prechecks(self):
        identity = dict(run_id='42', head_sha='a' * 40)
        price = dict(identity, url='https://api-docs.deepseek.com/zh-cn/quick_start/pricing/', checked_at=NOW.isoformat(), sha256='b' * 64, rates=dict(currency='CNY', input='9.0', output='27.0', model=r.MODEL, version='DeepSeek-V4-Pro-0813'))
        account = dict(identity, schema='hcl-reliability-account-readiness-v1', checked_at=NOW.isoformat(), currency='CNY', available=True, model_calls=0, account_read_queries=1, existing_account_only=True)
        return price, account, identity

    def test_readonly_prechecks_same_identity_cny_currency_no_balance(self):
        price, account, identity = self.prechecks()
        self.assertTrue(r.validate_readonly_prechecks(price, account, identity, NOW))
        for key, value in [('balance', '900'), ('currency', 'USD'), ('head_sha', 'f' * 40), ('existing_account_only', False), ('model_calls', 1), ('account_read_queries', 0)]:
            bad = dict(account); bad[key] = value
            with self.assertRaises(ValueError): r.validate_readonly_prechecks(price, bad, identity, NOW)
        with self.assertRaises(ValueError): r.validate_readonly_prechecks(price, account, identity, NOW + timedelta(minutes=11))



class FinalContractTests(unittest.TestCase):
    def test_candidate_package_and_old_grant_never_admit_reusable_live_entry(self):
        package = r.OfflinePackage.build(fixture_packet(), RUNTIME); client = Client()
        with tempfile.TemporaryDirectory() as directory:
            for grant in ({'stage': 1}, {'stage': 1, 'authorization_ref': 'OWNER_APPROVED_TWO_STAGE_CNY_REPLACEMENT_20261006_14_CALLS_14_CNY'}):
                with self.assertRaisesRegex(ValueError, 'OFFLINE_CANDIDATE_CANNOT_AUTHORIZE'):
                    r.run(client, package, grant, Path(directory) / 'run', launch={}, price={}, account={}, identity={}, clock=lambda: NOW)
            self.assertEqual(client.calls, [])

    def test_final_package_missing_any_resolved_pin_is_rejected(self):
        package = r.FrozenPackage(dict(schema='hcl-reliability-final-package-v1', status='FROZEN_BEFORE_ANY_OUTPUT'), fixture_packet(), RUNTIME)
        with self.assertRaisesRegex(ValueError, 'EXACT_REVIEWED_FINAL_PACKAGE_REQUIRED'): package.verify()

    def test_private_native_artifact_enables_review_but_public_is_hash_and_counts_only(self):
        package = r.OfflinePackage.build(fixture_packet(), RUNTIME)
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'run'; result = r.run_offline(Client(), package, 1, path, clock=lambda: NOW)
            private = json.loads((path / 'native-review-private.json').read_text())
            self.assertEqual(len(private['reviews']), 1)
            review = private['reviews'][0]
            self.assertEqual(review['case_id'], 'control-0')
            self.assertEqual(len(review['validated_operation_arguments']), 1)
            self.assertEqual(review['validated_operation_arguments'][0]['capability'], 'B01')
            self.assertEqual(len(review['native_outputs']), 1)
            self.assertEqual(result['arms'][0]['native_review_sha256'], r.digest(review))
            public = p.export(result, package)
            self.assertEqual(public['arms'][0]['native_review_sha256'], r.digest(review))
            text = json.dumps(public)
            for field in ('validated_operation_arguments', 'native_outputs', 'preparation_policy', 'reasoning_content'):
                self.assertNotIn('"' + field + '"', text)
            self.assertNotIn('SECRET_REASONING_CANARY', json.dumps(private))
            self.assertNotIn('ENVELOPE_PRIVATE_CANARY', json.dumps(private))

    def test_private_native_evidence_is_bounded_and_forbidden_keys_fail_closed(self):
        case = r.normalized_cases(fixture_packet())[0]
        large = dict(plan={'operations': []}, operations=[dict(capability='B01', executed=True, result={'x': 'a' * 1048577})])
        value = r.private_native_review(case, large)
        self.assertEqual(value['review_status'], 'NATIVE_REVIEW_BOUND_EXCEEDED_NO_SEMANTIC_PASS')
        self.assertNotIn('native_outputs', value)
        unsafe = dict(plan={'operations': []}, operations=[dict(capability='B01', executed=True, result={'api_key': 'NEVER_CAPTURE'})])
        with self.assertRaisesRegex(ValueError, 'FORBIDDEN_FIELD'): r.private_native_review(case, unsafe)

    def test_native_evidence_missing_or_changed_cannot_pass_gate(self):
        result, package = execute(); evidence = p.export(result, package); review = review_fixture(package, evidence)
        for field, value in [('native_review_sha256', 'f' * 64), ('native_review_available', False)]:
            bad = copy.deepcopy(evidence); bad['arms'][0][field] = value
            changed_review = dict(review, evidence_sha256=r.digest(bad))
            with self.assertRaises(ValueError): p.validate_phase1_gate(package, bad, changed_review)


class AdditionalFailClosedTests(unittest.TestCase):
    def test_sdk_client_timeout_retries_and_endpoint_cannot_expand_after_reservation(self):
        package = r.OfflinePackage.build(fixture_packet(), RUNTIME)
        for field, value in [('timeout', 181), ('max_retries', 1), ('base_url', 'https://example.invalid')]:
            with tempfile.TemporaryDirectory() as root:
                client = Client(); ledger = r.Ledger(Path(root) / 'run', package, 1, lambda: NOW, lambda: 0)
                ledger.active = 'control-0:HCL'; port = r.BoundedPort(client, ledger, ledger.active)
                prompt = r.messages(package.cases[0], 'HCL'); port.reservation_usd('planning', prompt)
                setattr(client, field, value)
                with self.assertRaises(Exception): port.complete('planning', prompt)
                self.assertEqual(client.calls, []); self.assertTrue(ledger.stopped)
                self.assertEqual(ledger.value['reserved_cny'], str(r.HOLD_CNY['planning']))

    def test_provider_shape_or_private_exception_is_never_retried_or_copied(self):
        for mode in ('model', 'transport', 'usage_bound'):
            def mutate(result, index, request):
                if mode == 'model': result['model'] = 'WRONG_MODEL_PRIVATE_CANARY'
                elif mode == 'transport': raise RuntimeError('PRIVATE_TRANSPORT_CANARY')
                else: result['usage'].update(prompt_tokens=999999, total_tokens=1000099)
            client = Client(mutate); result, package = execute(client, 2); output = p.export(result, package)
            self.assertEqual(len(client.calls), 1); self.assertFalse(output['usage_complete'])
            self.assertEqual(output['status'], 'STOPPED_NO_RETRY')
            self.assertTrue(all(x['status'] == 'NOT_ATTEMPTED' for x in output['arms'][1:]))
            self.assertNotIn('PRIVATE_CANARY', json.dumps(output))
            self.assertNotIn('PRIVATE_TRANSPORT_CANARY', json.dumps(output))

    def test_durable_write_failure_prevents_sdk_send(self):
        package = r.OfflinePackage.build(fixture_packet(), RUNTIME); client = Client(); original = r.save
        def refuse(path, value):
            if Path(path).name == 'receipt.json' and value.get('calls'): raise OSError('SIMULATED_DISK_FAILURE')
            return original(path, value)
        with tempfile.TemporaryDirectory() as root, patch.object(r, 'save', refuse):
            with self.assertRaises(OSError): r.run_offline(client, package, 1, Path(root) / 'run', clock=lambda: NOW)
        self.assertEqual(client.calls, [])

    def test_every_future_call_slot_is_initially_durable_not_attempted(self):
        package = r.OfflinePackage.build(fixture_packet(), RUNTIME)
        with tempfile.TemporaryDirectory() as root:
            ledger = r.Ledger(Path(root) / 'run', package, 2, lambda: NOW, lambda: 0)
            initial = json.loads(ledger.path.read_text())
            self.assertEqual(len(initial['arms']), 8)
            self.assertTrue(all(row['status'] == 'NOT_ATTEMPTED' for row in initial['arms']))
            self.assertEqual(initial['calls'], [])


class RuntimeContextBoundaryTests(unittest.TestCase):
    def test_planning_overflow_preserves_only_actual_planning_wire_and_zero_calls(self):
        package = r.OfflinePackage.build(fixture_packet(), RUNTIME)
        with tempfile.TemporaryDirectory() as root:
            client = Client(); ledger = r.Ledger(Path(root) / 'run', package, 1, lambda: NOW, lambda: 0)
            ledger.active = 'control-0:HCL'; port = r.BoundedPort(client, ledger, ledger.active)
            prompt = [dict(role='system', content='Bounded control policy'), dict(role='user', content='x' * 40000)]
            expected, encoded, metrics = r.request_and_metrics('planning', prompt)
            with self.assertRaisesRegex(MeteredPortError, 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION'):
                port.reservation_usd('planning', prompt)
            ledger.arm(ledger.active)['status'] = 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION'
            ledger.stopped = True; ledger.close()
            evidence = p.export(ledger.value, package); arm = evidence['arms'][0]
            self.assertEqual(client.calls, []); self.assertEqual(evidence['calls'], [])
            self.assertEqual(evidence['reserved_cny'], '0'); self.assertEqual(evidence['provider_calls'], 0)
            self.assertEqual(arm['request_bound_failure_phase'], 'planning')
            self.assertEqual(arm['request_diagnostics'][0]['full_request_sha256'], hashlib.sha256(encoded).hexdigest())
            self.assertEqual(arm['request_diagnostics'][0]['full_request_utf8_bytes'], len(encoded))
            self.assertIsNone(arm['final_request_full_utf8_bytes']); self.assertIsNone(arm['final_request_full_sha256'])
            self.assertEqual(arm['full_request_metrics_unavailable_reason'], 'ANSWER_PHASE_NOT_REACHED')

    def test_runtime_character_refusal_does_not_invent_a_full_provider_request(self):
        def very_large(session, operation, question):
            return dict(capability=operation['capability'], executed=True, result={'large': 'x' * 140000}, support_claim_ids=[])
        with patch.object(r.UniversalHCL, '_execute', very_large):
            client = Client(); result, package = execute(client)
        output = p.export(result, package); arm = output['arms'][0]
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(arm['full_request_metrics_unavailable_reason'], 'RUNTIME_CONTEXT_REFUSED_BEFORE_PROVIDER_REQUEST_CONSTRUCTION')
        self.assertIsNone(arm['final_request_full_utf8_bytes']); self.assertIsNone(arm['final_request_full_sha256'])
        self.assertGreater(arm['runtime_final_context_metrics']['serialized_messages_utf8_bytes'], 128000)
        self.assertTrue(all(row['phase'] != 'answer' for row in arm['request_diagnostics']))


class ReusableEntryContractTests(unittest.TestCase):
    """Future guarded entry exercised only with synthetic in-memory grant fixtures.

    No grant/marker is saved and the caller is the fake transport above. Temporary
    workflow comments are unit-test placeholders, never a production final freeze.
    """
    def frozen_fixture(self, root):
        root = Path(root); (root / 'hcl').symlink_to(RUNTIME / 'hcl', target_is_directory=True); (root / 'scripts').symlink_to(RUNTIME / 'scripts', target_is_directory=True)
        paths = [f'.github/workflows/hcl-reliability-20261007-{stage}-once.yml' for stage in (1, 2)]
        for name in paths:
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('# SYNTHETIC UNIT TEST COMMENT ONLY; NEVER A LIVE WORKFLOW\n')
        packet = fixture_packet(); offline = r.OfflinePackage.build(packet, root)
        configuration = {k: v for k, v in offline.value.items() if k not in ('schema', 'status', 'unresolved_final_freeze_fields')}
        value = dict(schema='hcl-reliability-final-package-v1', status='FROZEN_BEFORE_ANY_OUTPUT', authorization_ref=r.AUTH, currency='CNY', packet_sha256=r.digest(packet), runtime_sha256=offline.value['runtime_sha256'], runtime_commit='1' * 40, source_guard_merge_commit='2' * 40, trusted_native_policy_merge_commit='3' * 40, pursuit_uncertainty_merge_commit='6' * 40, planner_lifecycle_contracts_merge_commit='7' * 40, independent_case_review_sha256='4' * 64, independent_executor_review_sha256='5' * 64, configuration=configuration, workflow_files={name: r.file_sha(root / name) for name in paths}, read_only_reader_files=__import__('hcl_reliability_cli').read_only_reader_pins(root))
        package = r.FrozenPackage(value, packet, root); write_review_fixture_artifacts(package); package.verify(); return package

    def inputs(self, package, stage, review=None):
        grant = dict(schema='hcl-reliability-new-grant-v1', status='READY', authorization_ref=r.AUTH, currency='CNY', stage=stage, package_sha256=r.digest(package.value), approved_at_bound=r.APPROVED, expires_at=r.EXPIRES, authorized_calls=r.MAX_CALLS[stage], authorized_cny=str(r.CAP_CNY[stage]), executor_commit='e' * 40, phase1_source_review_sha256=r.digest(review) if review is not None else None, public_native_evidence_permission=native_permission_fixture(package), retries=0, historical_budget_transfer=False, other_stage_budget_transfer=False)
        launch = LaunchAndPrecheckTests().launch(); launch['stage'] = stage; launch['paths'] = [f'.github/HCL_RELIABILITY_20261007_{stage}_TRIGGER.json']; launch['grant_changed_paths'] = [f'.github/HCL_RELIABILITY_20261007_{stage}_GRANT.json']
        launch['pages'][0]['workflow_runs'][0]['path'] = f'.github/workflows/hcl-reliability-20261007-{stage}-once.yml'
        launch['package_sha256'] = r.digest(package.value); launch['grant_sha256'] = r.digest(grant)
        launch['marker'].update(stage=stage, package_sha256=r.digest(package.value), grant_sha256=r.digest(grant))
        price, account, identity = LaunchAndPrecheckTests().prechecks()
        return grant, dict(launch=launch, price=price, account=account, identity=identity, clock=lambda: NOW)

    def test_same_runner_future_entry_entire_14_call_contract_with_fake_transport_only(self):
        with tempfile.TemporaryDirectory() as root:
            package = self.frozen_fixture(root); first_grant, first_args = self.inputs(package, 1)
            client = Client()
            first = r.run(client, package, first_grant, Path(root) / 'hcl-reliability-20261007-1-private', **first_args)
            self.assertEqual(len(client.calls), 2)
            evidence = p.export(first, package, first_grant, first_args['identity'], native_bundle=json.loads((Path(root) / 'hcl-reliability-20261007-1-private/native-review-private.json').read_text()))
            self.assertEqual(evidence['provider_calls'], 2)  # Simulated live bookkeeping branch only.
            self.assertNotIn('actual_spend_cny', evidence)
            review = review_fixture(package, evidence)
            self.assertTrue(p.validate_phase1_gate(package, evidence, review, native_permission=first_grant['public_native_evidence_permission']))
            second_grant, second_args = self.inputs(package, 2, review); client2 = Client()
            second = r.run(client2, package, second_grant, Path(root) / 'hcl-reliability-20261007-2-private', phase1_evidence=evidence, phase1_review=review, **second_args)
            final = p.export(second, package, second_grant, second_args['identity'], native_bundle=json.loads((Path(root) / 'hcl-reliability-20261007-2-private/native-review-private.json').read_text()))
            self.assertEqual(len(client2.calls), 12); self.assertEqual(final['provider_calls'], 12)
            self.assertEqual(Decimal(evidence['reserved_cny']) + Decimal(final['reserved_cny']), Decimal('11.885760'))
            with self.assertRaises(FileExistsError):
                r.run(Client(), package, first_grant, Path(root) / 'hcl-reliability-20261007-1-private', **first_args)
            with self.assertRaisesRegex(ValueError, 'EXACT_ONE_USE_PRIVATE_DIRECTORY_REQUIRED'):
                r.run(Client(), package, first_grant, Path(root) / 'a-different-directory', **first_args)

    def test_future_entry_rejects_each_wrong_authority_or_same_run_precheck(self):
        with tempfile.TemporaryDirectory() as root:
            package = self.frozen_fixture(root)
            for mutation in ('cny', 'calls', 'expiry', 'old_authority', 'price', 'account', 'history', 'review_link'):
                grant, args = self.inputs(package, 1); client = Client()
                if mutation == 'cny': grant['authorized_cny'] = '12'
                elif mutation == 'calls': grant['authorized_calls'] = 14
                elif mutation == 'expiry': grant['expires_at'] = '2026-10-08T14:00:00Z'
                elif mutation == 'old_authority': grant['authorization_ref'] = 'OLD_CONSUMED_AUTHORITY'
                elif mutation == 'price': args['price']['rates']['output'] = '28.0'
                elif mutation == 'account': args['account']['currency'] = 'USD'
                elif mutation == 'history': args['launch']['pages'][0]['total_count'] = 2
                else: grant['phase1_source_review_sha256'] = 'a' * 64
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    r.run(client, package, grant, Path(root) / 'hcl-reliability-20261007-1-private', **args)
                self.assertEqual(client.calls, [])


if __name__ == '__main__':
    unittest.main()
