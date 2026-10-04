"""Provider-free four-case bounds, identity, failure retention and public whitelist tests."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tests.test_v1_deepseek_metered import FakeClient
from scripts import run_four_comparison as r
from scripts import four_comparison_public as public

NOW = datetime(2026, 10, 4, 13, tzinfo=timezone.utc)


class Client(FakeClient):
    timeout = 180
    def __init__(self, mutate=None, empty=False): super().__init__(); self.mutate = mutate; self.empty = empty
    def create(self, **request):
        value = super().create(**request); payload = json.loads(request['messages'][-1]['content'])
        if request['max_tokens'] == 16384:
            # Test-only native operation, never a condition on live model selection.
            answer = dict(task='Test native result', operations=[] if self.empty else [dict(capability='G01', question='Check premises.', source_ids=[payload['sources'][0]['source_id']], bindings=[])], limitations=[])
        else:
            source = payload['sources'][0]
            answer = dict(answer='A bounded test answer.', source_citations=[dict(source_id=source['source_id'], version=1, quote=source['text'], start=0)], uncertainty='Limits remain.', assumptions='No extra facts.')
        value['choices'][0]['message']['content'] = json.dumps(answer)
        if self.mutate: self.mutate(value, len(self.calls), request)
        return value


def execute(client, **kwargs):
    package = r.build_package()
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)/'run'; result = r.run(client, package, r.expected_grant(package, True), path, clock=lambda: NOW, **kwargs)
        assert json.loads((path/'receipt.json').read_text()) == result
    return result, package


def exported(result, package):
    identity = dict(run_id='42', head_sha='a'*40)
    return public.export(result, package, r.expected_grant(package, True), identity, dict(identity, existing_provider_secret='PRESENT'))


class FourComparisonTests(unittest.TestCase):
    def test_frozen_requests_caps_and_zero_grant(self):
        package = r.build_package()
        self.assertEqual(len(package['requests']), 8)
        self.assertEqual(package['maximum_schedule_reservation_usd'], '1.27791840')
        self.assertEqual(package['production_planning_tokens'], 4096)
        with self.assertRaisesRegex(ValueError, 'EXACT_NEW_OWNER_GRANT'):
            r.require_grant(package, r.expected_grant(package), NOW)
        for when in (NOW - timedelta(days=1), NOW + timedelta(days=1)):
            with self.assertRaises(ValueError): r.require_grant(package, r.expected_grant(package, True), when)

    def test_full_schedule_same_source_contract_no_rubric_and_latency(self):
        client = Client(); result, package = execute(client)
        self.assertEqual(result['status'], 'COMPLETED_ONE_PASS'); self.assertEqual(len(client.calls), 12)
        self.assertEqual([(a['case_id'], a['arm']) for a in result['arms']], r.ORDER)
        self.assertTrue(all(a['status'] == 'ANSWER_ACCEPTED' for a in result['arms']))
        self.assertEqual(Decimal(result['reserved_usd']), r.MAX_SCHEDULE)
        self.assertEqual(result['remaining_authorized_calls'], 0)
        for row in result['calls']:
            self.assertLessEqual(Decimal(row['usage_rated_usd']), Decimal(row['reserved_usd']))
            self.assertGreaterEqual(row['sdk_seconds'], 0)
        for arm in result['arms']:
            self.assertGreaterEqual(arm['arm_seconds'], arm['sdk_seconds'])
            self.assertEqual(arm['checked_treatment'], [])
        inputs, _ = r.load_frozen()
        for q in client.calls:
            payload = json.loads(q['messages'][-1]['content'])
            case = next(c for c in inputs['cases'] if c['question'] == payload['question'])
            self.assertEqual(payload['sources'][0]['text'], case['sources'][0]['text'])
            self.assertNotIn('rubric', payload); self.assertNotIn('case_id', payload)
        output = exported(result, package)
        self.assertNotIn('HIDDEN_', json.dumps(output)); self.assertNotIn('hcl_plan', json.dumps(output))
        self.assertEqual(output['provider_calls'], 12)

    def test_empty_and_unavailable_selection_continue_and_stay_in_denominator(self):
        for empty in (True, False):
            def mutate(value, index, request):
                if request['max_tokens'] == 16384 and not empty:
                    plan = json.loads(value['choices'][0]['message']['content']); plan['operations'][0]['capability'] = 'E05'
                    value['choices'][0]['message']['content'] = json.dumps(plan)
            client = Client(mutate, empty=empty); result, package = execute(client)
            self.assertEqual(len(client.calls), 8); self.assertEqual(result['status'], 'COMPLETED_ONE_PASS')
            self.assertEqual(len(exported(result, package)['arms']), 8)
            self.assertEqual(sum(a['status'] == 'ANSWER_ACCEPTED' for a in result['arms']), 4)
            self.assertTrue(all(a['final_fields'] is None for a in result['arms'] if a['arm'] == 'HCL'))

    def test_known_schema_length_and_citation_failures_continue_without_repair(self):
        for edge in ('schema', 'malformed_json', 'length', 'citation', 'blank'):
            def mutate(value, index, request):
                if index != 2: return
                if edge == 'schema': value['choices'][0]['message']['content'] = '{}'
                elif edge == 'malformed_json': value['choices'][0]['message']['content'] = '{bad'
                elif edge == 'length': value['choices'][0]['finish_reason'] = 'length'
                else:
                    # First Base answer is independently made invalid below.
                    pass
            if edge in ('citation', 'blank'):
                def mutate(value, index, request):
                    if index != 1: return
                    answer = json.loads(value['choices'][0]['message']['content'])
                    if edge == 'citation': answer['source_citations'][0]['end'] = 1
                    else: answer['answer'] = '   '
                    value['choices'][0]['message']['content'] = json.dumps(answer)
            client = Client(mutate); result, package = execute(client)
            self.assertEqual(result['status'], 'COMPLETED_ONE_PASS')
            self.assertEqual(len(client.calls), 11 if edge in ('schema', 'malformed_json', 'length') else 12)
            output = exported(result, package)
            if edge == 'citation': self.assertEqual(output['arms'][0]['final_fields']['source_citations'][0]['end'], 1)
            if edge == 'blank': self.assertEqual(output['arms'][0]['final_fields']['answer'], '   ')

    def test_both_arms_malformed_final_json_remains_unavailable_and_continues(self):
        def mutate(value, index, request):
            if request['max_tokens'] == 8192: value['choices'][0]['message']['content'] = '{broken'
        client = Client(mutate); result, package = execute(client)
        self.assertEqual(result['status'], 'COMPLETED_ONE_PASS'); self.assertEqual(len(client.calls), 12)
        self.assertTrue(all(a['final_fields'] is None for a in exported(result, package)['arms']))
        self.assertTrue(all(a['status'] == 'FINAL_SCHEMA_OR_CITATIONS_REJECTED' for a in result['arms']))

    def test_dynamic_hcl_answer_overflow_continues_without_truncation(self):
        def oversized(session, operation, question):
            return dict(capability=operation['capability'], executed=True, result={'large': 'x'*40000}, support_claim_ids=[])
        with patch.object(r.UniversalHCL, '_execute', oversized):
            client = Client(); result, package = execute(client)
        self.assertEqual(result['status'], 'COMPLETED_ONE_PASS'); self.assertEqual(len(client.calls), 8)
        self.assertTrue(all(a['status'] == 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION' for a in result['arms'] if a['arm'] == 'HCL'))
        self.assertEqual(len(exported(result, package)['arms']), 8)

    def test_unknown_transport_usage_and_model_stop_whole_batch(self):
        for edge in ('transport', 'usage', 'model', 'cost'):
            def mutate(value, index, request):
                if edge == 'usage': value['usage'] = {}
                elif edge == 'model': value['model'] = 'different-model'
                elif edge == 'cost': value['usage']['completion_tokens'] = 100000
            client = Client(mutate)
            if edge == 'transport': client.failure = 'PRIVATE_TRANSPORT_CANARY'
            result, package = execute(client)
            self.assertEqual(len(client.calls), 1); self.assertEqual(result['status'], 'STOPPED_NO_RETRY')
            self.assertEqual(sum(a['status'] == 'NOT_ATTEMPTED' for a in result['arms']), 7)
            output = exported(result, package)
            self.assertFalse(output['usage_complete']); self.assertIsNone(output['usage_rated_usd'])
            self.assertNotIn('PRIVATE_TRANSPORT_CANARY', json.dumps(output))
            self.assertEqual(Decimal(output['reserved_usd']), Decimal(package['requests']['D01:Base:answer']['reservation_usd']))

    def test_deadline_unknown_stops_with_full_reservation(self):
        import time
        client = Client(); original = client.chat.completions.create
        def slow(**kwargs): time.sleep(.03); return original(**kwargs)
        client.chat.completions.create = slow
        original_init = r.OutputLimitPort.__init__
        def init(port, *args, **kwargs): original_init(port, *args, **kwargs); port.maximum_wait_seconds = .001
        with patch.object(r.OutputLimitPort, '__init__', init): result, package = execute(client)
        self.assertEqual(result['status'], 'STOPPED_NO_RETRY'); self.assertFalse(exported(result, package)['usage_complete'])

    def test_duplicate_request_and_identity_drift_admission_fail_closed(self):
        package = r.build_package(); case = r.load_frozen()[0]['cases'][0]
        with tempfile.TemporaryDirectory() as temp:
            ledger = r.Ledger(Path(temp)/'run', package, r.expected_grant(package, True), lambda: NOW, __import__('time').monotonic)
            ledger.active = 'D01:Base'; port = r.Port(Client(), ledger, ledger.active)
            port.reservation_usd('answer', r.messages(case, 'Base'))
            with self.assertRaisesRegex(ValueError, 'DUPLICATE'): port.reservation_usd('answer', r.messages(case, 'Base'))
            self.assertTrue(ledger.stopped)
        changed = copy.deepcopy(case); changed['question'] += '!'
        with tempfile.TemporaryDirectory() as temp:
            ledger = r.Ledger(Path(temp)/'run', package, r.expected_grant(package, True), lambda: NOW, __import__('time').monotonic)
            ledger.active = 'D01:Base'; port = r.Port(Client(), ledger, ledger.active)
            with self.assertRaisesRegex(ValueError, 'FROZEN_REQUEST'): port.reservation_usd('answer', r.messages(changed, 'Base'))
            self.assertTrue(ledger.stopped)

    def test_batch_elapsed_stops_before_any_send(self):
        values = iter([0, 0, 2600] + [2600]*20)
        client = Client(); result, _ = execute(client, monotonic=lambda: next(values))
        self.assertEqual(client.calls, []); self.assertEqual(result['status'], 'STOPPED_NO_RETRY')

    def test_one_run_history_and_marker_only(self):
        package = r.build_package(); grant = r.expected_grant(package, True)
        marker = dict(schema='hcl-four-comparison-marker-v1', authorization_ref=r.AUTH, package_sha256=r.digest(package), grant_sha256=r.digest(grant), executor_commit='a'*40)
        history = [dict(id=42, event='push', created_at='2026-10-04T13:00:00Z')]
        args = ['42', '1', history, 'push', 'a'*40, [str(r.MARKER)], marker, package, grant, NOW]
        r.verify_launch(*args)
        for index, value in [(1, '2'), (2, history+[dict(id=1, event='push', created_at='2026-10-04T12:00:00Z')]), (5, [str(r.MARKER), 'other'])]:
            altered = args[:]; altered[index] = value
            with self.assertRaises(ValueError): r.verify_launch(*altered)

    def test_public_allowlist_excludes_private_keys_and_checks_canonical_fields(self):
        result, package = execute(Client())
        result['PRIVATE_CANARY'] = 'SECRET'; result['calls'][0]['request_body'] = 'PRIVATE_CANARY'
        output = exported(result, package)
        self.assertNotIn('PRIVATE_CANARY', json.dumps(output)); self.assertNotIn('SECRET', json.dumps(output))
        self.assertIsNone(r.final_fields(json.dumps(dict(answer='x', source_citations=[], uncertainty='', assumptions='', reasoning_content='BAD'))))
        result['calls'][0]['usage_rated_usd'] = '0.99'
        with self.assertRaises(ValueError): exported(result, package)

if __name__ == '__main__': unittest.main()
