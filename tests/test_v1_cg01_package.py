"""No-provider checks for the frozen four-arm-plus-ablation package."""
import json
import unittest

from hcl.v1 import CognitionRequest, HCLCognitionLayer
from scripts.cg01_external_package import (BudgetLedger, arm_messages,
    load_package, parse_semantic, run_with_provider, score_output, task_query)


class PackagePreflight(unittest.TestCase):
    def test_source_and_arm_preflight_use_no_provider(self):
        package = load_package()
        self.assertEqual({case['family'] for case in package['cases']},
                         {'The Necklace', 'The Gift of the Magi'})
        for case in package['cases']:
            query = task_query(case)
            prepared = HCLCognitionLayer(lambda _: 'unused').prepare(
                CognitionRequest(query, narrative=case['excerpt'],
                                 target_actor=case['target_actor']))
            self.assertTrue(prepared.plan.explanation)
            for arm in package['arms']:
                messages = arm_messages(case, arm, prepared if arm.startswith('H') else None)
                self.assertLessEqual(len(json.dumps(messages).encode()),
                                     package['input_tokens_per_call_max'])
                serialized = json.dumps(messages)
                self.assertNotIn('expected_status', serialized)
                self.assertNotIn('source_only_audit_basis', serialized)

    def test_score_requires_exact_source_quote_and_keeps_human_audit(self):
        case = load_package()['cases'][0]
        good = json.dumps({'assessment': case['expected_status'],
            'reason': 'The source contradicts the claimed knowledge.',
            'evidence_quote': 'He had not thought of that', 'unknown_motive': True})
        score = score_output(good, case)
        self.assertTrue(score['assessment_match'])
        self.assertTrue(score['quote_anchored'])
        self.assertTrue(score['source_first_human_audit_required'])
        bad = good.replace('He had not thought of that', 'invented evidence')
        self.assertFalse(score_output(bad, case)['valid_output'])

    def test_metered_adapter_ceiling(self):
        package = load_package()
        ledger = BudgetLedger(package)
        def stub(messages, max_output_tokens, config):
            self.assertEqual(max_output_tokens, 2000)
            self.assertEqual(config['thinking']['type'], 'disabled')
            return {'model': package['model'], 'raw': '{}',
                    'input_tokens': 10, 'output_tokens': 2, 'cost_usd': 0.00001}
        for _ in range(24):
            ledger.call(stub, [{'role': 'user', 'content': 'small'}])
        self.assertEqual(ledger.calls, 24)
        with self.assertRaises(ValueError):
            ledger.call(stub, [{'role': 'user', 'content': 'small'}])

    def test_h_new_removes_only_condition_results(self):
        case = {'target_actor': 'Alice', 'action_phrase': 'miss the meeting',
                'candidate': 'Alice deliberately opposed Bob.',
                'question': 'Assess the explanation.'}
        narrative = ("Alice missed Bob's meeting. Bob thought Alice stayed away to oppose him. "
                     "Alice first learned about the meeting after it ended.")
        prepared = HCLCognitionLayer(lambda _: 'unused').prepare(
            CognitionRequest(task_query(case), narrative=narrative, target_actor='Alice'))
        h = json.loads(arm_messages(case, 'H', prepared)[-1]['content'])['cognition_context']
        ablated = json.loads(arm_messages(case, 'H-new', prepared)[-1]['content'])['cognition_context']
        self.assertEqual(h['evidence'], ablated['evidence'])
        self.assertEqual(h['perspective'], ablated['perspective'])
        self.assertEqual(h['preparation'], ablated['preparation'])
        self.assertEqual(h['explanations'][1]['status'], 'INVALIDATED')
        self.assertEqual(ablated['explanations'][1]['status'], 'NOT_CHECKED')
        self.assertEqual(ablated['explanations'][1]['conditions'], [])

    def test_full_runner_with_provider_free_stub(self):
        package = load_package()
        checkpoints = []
        def stub(messages, max_output_tokens, config):
            self.assertEqual(config['response_format']['type'], 'json_object')
            extraction = 'Extract only source-anchored conditions' in messages[0]['content']
            raw = ('{"events":[],"candidates":[],"facts":[]}' if extraction else
                   '{"assessment":"UNRESOLVED","reason":"insufficient",'
                   '"evidence_quote":"","unknown_motive":true}')
            return {'model': package['model'], 'raw': raw, 'input_tokens': 100,
                    'output_tokens': 20, 'cost_usd': 0.0}
        receipt = run_with_provider(stub, package,
                                    on_update=lambda snapshot: checkpoints.append(
                                        (snapshot['calls'], len(snapshot['rows']))))
        self.assertEqual(receipt['calls'], 24)
        self.assertEqual(len(receipt['rows']), 20)
        self.assertEqual(receipt['cost_usd'], 0.0)
        self.assertEqual(checkpoints[-1], (24, 20))
        self.assertIn((1, 0), checkpoints)

    def test_failed_provider_call_is_charged_and_checkpointed(self):
        package = load_package()
        checkpoints = []
        ledger = BudgetLedger(package, on_update=lambda current: checkpoints.append(
            (current.calls, current.cost_usd, current.attempts[-1].get('failure_type'))))
        def failed(_messages, _max_output_tokens, _config):
            raise RuntimeError('simulated provider failure')
        with self.assertRaises(RuntimeError):
            ledger.call(failed, [{'role': 'user', 'content': 'small'}])
        self.assertEqual(ledger.calls, 1)
        self.assertEqual(checkpoints[-1][2], 'RuntimeError')
        self.assertGreater(ledger.cost_usd, 0)

    def test_semantic_source_spans_align_only_whitespace_and_use_source_order(self):
        source = 'Ben\n\nentered the room.\nAda first learned about the room after it closed.'
        raw = json.dumps({'events': [
            {'event_id': 7, 'quote': 'Ada first learned about the room after it closed.',
             'actor_id': 'Ada', 'order_index': 1},
            {'event_id': 4, 'quote': 'Ben entered the room.',
             'actor_id': 'Ben', 'order_index': 0}],
            'candidates': [{'candidate_id': 1, 'target_actor': 'Ben',
                'action_event_id': 4, 'source_event_id': 4,
                'explanation': 'Ben chose to enter.', 'required': [
                    {'kind': 'OPPORTUNITY', 'key': 'enter'}]}],
            'facts': []})
        parsed = parse_semantic(raw, 'stub', 0, source)
        self.assertEqual([event.event_id for event in parsed.events], ['4', '7'])
        self.assertEqual(parsed.events[0].raw_text, 'Ben\n\nentered the room.')
        self.assertEqual(parsed.candidates[0].action_event_id, '4')
        self.assertIn('whitespace_aligned_event:4', parsed.source_span_diagnostics)

    def test_unanchored_semantic_event_and_dependent_claims_are_rejected(self):
        source = 'Ben entered the room.'
        raw = json.dumps({'events': [
            {'event_id': 'e1', 'quote': 'Ben entered the room.',
             'actor_id': 'Ben', 'order_index': 0},
            {'event_id': 'e2', 'quote': 'Ben secretly planned a theft.',
             'actor_id': 'Ben', 'order_index': 1}],
            'candidates': [{'candidate_id': 'c1', 'target_actor': 'Ben',
                'action_event_id': 'e2', 'source_event_id': 'e2',
                'explanation': 'Ben entered to steal.', 'required': []}],
            'facts': [{'fact_id': 'f1', 'source_event_id': 'e2',
                'target_actor': 'Ben', 'kind': 'GOAL', 'key': 'steal',
                'value': True, 'authority': 'EXPLICIT_NARRATOR',
                'claim_time': 'SOURCE', 'first_learning_after_action': False}]})
        parsed = parse_semantic(raw, 'stub', 0, source)
        self.assertEqual(len(parsed.events), 1)
        self.assertFalse(parsed.candidates)
        self.assertFalse(parsed.facts)
        self.assertIn('rejected_unanchored_event:e2', parsed.source_span_diagnostics)

    def test_wrapped_semantic_source_reaches_actual_cg01_context(self):
        source = ('Alice placed the\nletter on the table. '
                  'Alice said she intended to warn Bob.')
        raw = json.dumps({'events': [
            {'event_id': 'action', 'quote': 'Alice placed the letter on the table.',
             'actor_id': 'Alice', 'order_index': 0},
            {'event_id': 'report', 'quote': 'Alice said she intended to warn Bob.',
             'actor_id': 'Alice', 'order_index': 1}],
            'candidates': [{'candidate_id': 'candidate', 'target_actor': 'Alice',
                'action_event_id': 'action', 'source_event_id': 'action',
                'explanation': 'Alice placed the letter to warn Bob.',
                'required': [{'kind': 'GOAL', 'key': 'warn Bob'}]}],
            'facts': [{'fact_id': 'goal', 'source_event_id': 'report',
                'target_actor': 'Alice', 'kind': 'GOAL', 'key': 'warn Bob',
                'value': True, 'authority': 'DIRECT_SELF_REPORT',
                'claim_time': 'ACTION', 'first_learning_after_action': False}]})
        def preparer(payload):
            return parse_semantic(raw, 'stub', 0, payload['narrative'], 0)
        prepared = HCLCognitionLayer(lambda _: 'unused',
            semantic_preparer=preparer).prepare(CognitionRequest(
            'Why did Alice place the letter?', narrative=source,
            target_actor='Alice', allow_semantic_preparation=True))
        self.assertIsNone(prepared.preparation_receipt['failure'])
        self.assertTrue(prepared.context.explanations)
        self.assertIn('whitespace_aligned_event:action',
                      prepared.preparation_receipt['source_span_diagnostics'])


if __name__ == '__main__':
    unittest.main()
