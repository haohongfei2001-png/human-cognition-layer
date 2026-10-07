"""Whitespace-only transport and size diagnostics; no model calls or efficacy test."""
import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from hcl.cognition import CallAllowance, UniversalHCL
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort, MAX_REQUEST_BYTES, MeteredPortError
from hcl.cognition.universal_entry import _final_context_metrics
from tests.test_v1_conditional_reader_entry import SOURCE, QUERY, proposals
from tests.test_v1_universal_appraisal import RequestBoundedStub
from tests.test_v1_universal_question import Stub, operation, plan, run


def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def session():
    value = UniversalHCL()
    value.put_source('meeting', SOURCE)
    return value


def translated():
    return dict(operation('B01', QUERY, ['meeting']), input_mode='semantic',semantic_candidates=proposals())


class FinalContextTransportTests(unittest.TestCase):
    def test_compact_payload_preserves_all_values_and_real_native_results(self):
        active = session()
        source_before = copy.deepcopy(active.sources)
        selected = plan(translated(), operation('B02', QUERY, ['meeting']))
        selected['limitations'] = ['Keep spaces  : , and Unicode 灯😀;\n\tno shortening.']
        port = Stub(selected)
        result = run(active, QUERY, port)
        self.assertEqual(result['status'], 'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertEqual([phase for phase, _ in port.calls], ['planning', 'answer'])
        self.assertEqual(result['hcl_execution']['native_results'], 2)
        self.assertEqual([row['executed'] for row in result['operations']], [True, True])
        final = port.calls[-1][1]
        payload = json.loads(final[-1]['content'])
        expected = dict(question=QUERY,
            sources=[dict(source_id='meeting', version=1, text=SOURCE)],
            hcl_plan=selected, hcl_operations=result['operations'],
            hcl_execution=result['hcl_execution'],
            knowledge_basis='SUPPLIED_SOURCES_AND_EXPLICIT_INTERPRETATION')
        legacy = json.dumps(expected, ensure_ascii=False, sort_keys=True)
        self.assertEqual(payload, json.loads(legacy))
        self.assertEqual(final[-1]['content'], compact(expected))
        self.assertLess(len(final[-1]['content'].encode()), len(legacy.encode()))
        self.assertEqual(active.sources, source_before)
        self.assertTrue(all(active.workspace.core.support_statuses()[claim] == 'SUPPORT_AVAILABLE'
            for row in result['operations'] for claim in row['support_claim_ids']))
        self.assertFalse(result['base_bypass'])
        self.assertFalse(result['answer_gain_established'])
        self.assertEqual(result['provider_calls'], 0)
        self.assertEqual(result['reserved_usd'], '0')

    def test_metrics_are_size_only_exact_and_not_added_to_model_input(self):
        selected = plan(translated())
        selected['limitations'] = ['PRIVATE_METRIC_CANARY 灯😀 "quoted" \\']
        port = Stub(selected)
        result = run(session(), QUERY, port)
        messages = result['actual_final_messages']
        payload = json.loads(messages[-1]['content'])
        metrics = result['final_context_metrics']
        self.assertEqual(set(metrics), {'payload_utf8_bytes', 'serialized_messages_utf8_bytes',
                                      'payload_value_utf8_bytes'})
        self.assertEqual(metrics['payload_utf8_bytes'], len(messages[-1]['content'].encode('utf-8')))
        self.assertEqual(metrics['serialized_messages_utf8_bytes'], len(compact(messages).encode('utf-8')))
        self.assertEqual(metrics['payload_value_utf8_bytes'],
                         {key: len(compact(value).encode('utf-8')) for key, value in payload.items()})
        self.assertGreater(metrics['payload_utf8_bytes'], len(messages[-1]['content']))
        self.assertNotIn('PRIVATE_METRIC_CANARY', json.dumps(metrics))
        self.assertNotIn('灯', json.dumps(metrics, ensure_ascii=False))
        self.assertNotIn('final_context_metrics', payload)
        self.assertTrue(all(type(value) is int for value in metrics['payload_value_utf8_bytes'].values()))

    def test_metrics_survive_provider_request_refusal_with_no_answer_or_retry(self):
        selected = plan(translated(), operation('C01', QUERY, ['meeting']),
                        operation('C03', QUERY, ['meeting']))
        port = RequestBoundedStub(selected)
        result = run(session(), QUERY, port)
        self.assertEqual([phase for phase, _ in port.calls], ['planning'])
        self.assertEqual(result['hcl_execution']['native_results'], 3)
        self.assertNotIn('answer', result)
        self.assertGreater(result['final_context_metrics']['serialized_messages_utf8_bytes'], MAX_REQUEST_BYTES)
        self.assertEqual(len(result['plan']['operations'][0]['semantic_candidates']), 5)
        self.assertEqual(result['provider_calls'], 0)

    def test_metrics_precede_local_character_gate_without_changing_it(self):
        def large(_session, op, _question):
            return dict(capability=op['capability'], executed=True,
                        result={'test_padding': 'x' * 40000}, support_claim_ids=[])
        port = Stub(plan(operation('B01', QUERY, ['meeting'])))
        with patch.object(UniversalHCL, '_execute', large):
            result = session().answer(QUERY, planner_backend=port, answer_backend=port,
                allowance=CallAllowance(2, 0, 'OFFLINE_TEST_ONLY'), maximum_context_chars=35000)
        self.assertEqual(result['failure_reason'], 'complete context exceeds budget; no truncation')
        self.assertGreater(result['final_context_metrics']['payload_utf8_bytes'], 40000)
        self.assertEqual([phase for phase, _ in port.calls], ['planning'])
        self.assertNotIn('actual_final_messages', result)
        self.assertNotIn('answer', result)

    def test_original_exact_citation_contract_is_unchanged(self):
        class CitingStub(Stub):
            def complete(self, phase, messages):
                value = super().complete(phase, messages)
                if phase == 'answer':
                    value['text'] = json.dumps(dict(answer='The source reports a conditional plan.',
                        source_citations=[dict(source_id='meeting', version=1, quote=SOURCE)],
                        uncertainty='Translation remains unverified.', assumptions='No private state established.'))
                return value
        port = CitingStub(plan(translated()))
        result = run(session(), QUERY, port)
        self.assertEqual(result['final_delivery_code'], 'DELIVERED')
        self.assertEqual(result['answer'], result['answer_raw'])
        self.assertFalse(result['source_review']['semantic_certification'])
        self.assertEqual(result['source_review']['anchors'][0]['original_quote'], SOURCE)
        self.assertEqual(result['source_review']['anchors'][0]['version'], 1)

    def test_unchanged_request_limit_counts_utf8_exact_fit_and_one_more_byte(self):
        # A request-only validator has no SDK client/create path or credentials.
        validator = DeepSeekMeteredPort(SimpleNamespace(max_retries=0,
            base_url='https://api.deepseek.com', timeout=60))
        messages = [dict(role='user', content='灯😀')]
        _, probe = validator.request('answer', messages)
        messages[0]['content'] += 'x' * (MAX_REQUEST_BYTES - len(probe))
        _, exact = validator.request('answer', messages)
        self.assertEqual(len(exact), 36000)
        messages[0]['content'] += 'x'
        with self.assertRaisesRegex(MeteredPortError, 'REQUEST_BOUND_EXCEEDED_NO_TRUNCATION'):
            validator.request('answer', messages)
        self.assertFalse(validator._quoted)

    def test_empty_native_plan_still_stops_before_final_context(self):
        port = Stub(plan())
        result = run(session(), QUERY, port)
        self.assertEqual(result['failure_reason'], 'NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER')
        self.assertNotIn('final_context_metrics', result)
        self.assertEqual([phase for phase, _ in port.calls], ['planning'])

    def test_metrics_do_not_make_offline_non_utf8_values_a_new_admission_rule(self):
        payload = dict(question='\ud800', sources=[], hcl_plan={}, hcl_operations=[],
                       hcl_execution={}, knowledge_basis='UNSOURCED_MODEL_KNOWLEDGE')
        messages = [dict(role='user', content=compact(payload))]
        self.assertEqual(_final_context_metrics(payload, messages), {'utf8_encoding_available': False})


if __name__ == '__main__':
    unittest.main()
