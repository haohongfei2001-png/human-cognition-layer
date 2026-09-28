"""Frozen fairness, presence and strict scorer; all model calls are absent."""
import json
from pathlib import Path
import unittest
from scripts.cg05_external_package import build_package, PACKAGE, score_answer, STATES, CRITERIA, RELATIONS
from scripts.frozen_cg05_replay import replay_frozen_cg05


class ConceptPackageTests(unittest.TestCase):
    def test_exact_certified_freeze_and_current_default_input_compatibility(self):
        frozen = replay_frozen_cg05()
        current = build_package()
        self.assertEqual(frozen, json.loads(PACKAGE.read_text()))
        self.assertEqual(current['cases'], frozen['cases'])
        self.assertEqual(current['frozen_engineering_sha256'], frozen['frozen_engineering_sha256'])
        self.assertEqual(len(frozen['cases']), 4)
        self.assertEqual(frozen['arms'], ['C', 'P', 'G', 'H', 'H-new'])
        self.assertFalse(frozen['execution_authorized'])
        self.assertEqual(frozen['owner_execution'], 'DEFERRED_OWNER_AUTHORIZATION')
        self.assertEqual(frozen['provider_calls_executed'], 0)
        self.assertLessEqual(frozen['estimated_worst_case_usd_at_repository_frozen_rate'], .30)

    def test_same_vocabulary_schema_and_actual_mechanism_only_ablation(self):
        for c in replay_frozen_cg05()['cases']:
            self.assertTrue(all(c['preflight'].values()))
            h, hn = [json.loads(c['messages'][a][1]['content']) for a in ('H', 'H-new')]
            self.assertTrue(h['cognition_context']['concepts']['checked'])
            h['cognition_context']['concepts']['checked'] = {}
            self.assertEqual(h, hn)
            self.assertEqual(c['messages']['H'][0], c['messages']['H-new'][0])
            for arm in ('C', 'P', 'G', 'H', 'H-new'):
                text = json.dumps(c['messages'][arm])
                for label in STATES + CRITERIA + RELATIONS:
                    self.assertIn(label, text)
                for field in c['gold']:
                    self.assertIn(field, text)

    def test_source_first_mechanism_coverage(self):
        cases = replay_frozen_cg05()['cases']
        readings = [r for c in cases for r in c['checked_state']['readings']]
        self.assertTrue({'ATTRIBUTED_ONLY', 'SUPERSEDED_LOCAL', 'OTHER_SCOPE', 'CRITERIA_UNRESOLVED',
            'CRITERIA_NOT_MET', 'CRITERIA_MET', 'DECLARED_COUNTEREXAMPLE'} <= {r['state'] for r in readings})
        self.assertTrue(any(r['counterexample_conflicts_with_criteria'] for r in readings))
        self.assertTrue(any(c['checked_state']['reading_relation'] == 'MULTIPLE_LOCAL_READINGS' for c in cases))
        self.assertTrue(all(c['preparation_receipt']['extraction_provider_calls'] == 0 for c in cases))

    def test_strict_nested_types_missing_fields_and_added_truth(self):
        c = replay_frozen_cg05()['cases'][-1]
        self.assertEqual(score_answer(c, json.dumps(c['gold']))['exact_fields'], 7)
        wrong = dict(c['gold'], counterexample_conflicts={'def-1': 1})
        self.assertEqual(score_answer(c, json.dumps(wrong))['exact_fields'], 6)
        self.assertEqual(score_answer(c, json.dumps(dict(c['gold'], universal_fairness=True)))['exact_fields'], 0)
        self.assertFalse(score_answer(c, 'not JSON')['valid'])


if __name__ == '__main__':
    unittest.main()
