"""No-provider checks for the frozen four-arm-plus-ablation package."""
import json
import unittest

from hcl.v1 import CognitionRequest, HCLCognitionLayer
from scripts.cg01_external_package import (BudgetLedger, arm_messages,
    load_package, run_with_provider, score_output, task_query)


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
        def stub(messages, max_output_tokens):
            self.assertEqual(max_output_tokens, 2000)
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
        def stub(messages, max_output_tokens):
            extraction = 'Extract only source-anchored conditions' in messages[0]['content']
            raw = ('{"events":[],"candidates":[],"facts":[]}' if extraction else
                   '{"assessment":"UNRESOLVED","reason":"insufficient",'
                   '"evidence_quote":"","unknown_motive":true}')
            return {'model': package['model'], 'raw': raw, 'input_tokens': 100,
                    'output_tokens': 20, 'cost_usd': 0.0}
        receipt = run_with_provider(stub, package)
        self.assertEqual(receipt['calls'], 24)
        self.assertEqual(len(receipt['rows']), 20)
        self.assertEqual(receipt['cost_usd'], 0.0)


if __name__ == '__main__':
    unittest.main()
