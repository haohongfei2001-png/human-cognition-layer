"""CG03-A typed operation and bounded-view non-promotion checks."""
from datetime import datetime, timezone, timedelta
import unittest

from hcl.v04.model import EventRecord
from hcl.v1 import (CognitionRequest, CognitionRouter, HCLCognitionLayer,
                    NormativePremise, PerspectiveMode, ResponsibilityCase)


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def event(event_id, second, text, actor=None, reader_only=False):
    stamp = (BASE + timedelta(seconds=second)).isoformat()
    return EventRecord(event_id, stamp, text, 'cg03-test', stamp, actor,
                       metadata={'reader_only': reader_only})


class TypedResponsibilityRoute(unittest.TestCase):
    def setUp(self):
        self.action = event('a', 0, 'Alice opened the gate.', 'Alice')
        self.outcome = event('o', 1, 'The animals escaped.', reader_only=True)
        self.case = ResponsibilityCase(('Alice',), 'a', 'o',
            (NormativePremise('p1',
                'Responsibility requires a causal contribution and control.', ('a', 'o')),))

    def request(self, **kwargs):
        return CognitionRequest('Assess Alice responsibility',
            evidence=(self.action, self.outcome), target_actor='Alice',
            responsibility_case=self.case, **kwargs)

    def test_explicit_case_routes_and_does_not_conclude(self):
        self.assertTrue(CognitionRouter().plan(CognitionRequest('What is 2 + 2?')).direct)
        plan = CognitionRouter().plan(self.request())
        self.assertTrue(plan.responsibility_structure)
        self.assertIn('cg03_responsibility_structure', plan.capabilities)
        self.assertFalse(plan.explanation)
        self.assertFalse(plan.social_commitment)
        prepared = HCLCognitionLayer(lambda _: 'ok').prepare(self.request())
        row = prepared.context.responsibility
        self.assertEqual(row['status'], 'INPUT_VALIDATED_FACTORS_UNCHECKED')
        self.assertEqual(row['conclusion'], 'UNRESOLVED')
        self.assertEqual(row['premises'][0]['authority'], 'CALLER_SUPPLIED_CONDITIONAL')
        self.assertEqual(len(row['unchecked_factors']), 5)
        self.assertIn('INPUT_VALIDATED_FACTORS_UNCHECKED', prepared.messages[-1]['content'])

    def test_hidden_outcome_does_not_leak_case_or_premise(self):
        prepared = HCLCognitionLayer(lambda _: 'ok').prepare(self.request(
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        self.assertEqual(prepared.context.responsibility, {})
        self.assertTrue(any(row.get('capability') == 'cg03_responsibility_structure'
                            for row in prepared.context.uncertainty))
        self.assertNotIn('Responsibility requires', prepared.messages[-1]['content'])
        self.assertNotIn('The animals escaped', prepared.messages[-1]['content'])
        observer = HCLCognitionLayer(lambda _: 'ok').prepare(self.request(
            observer_actor='Bob', perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET))
        self.assertEqual(observer.context.responsibility, {})

    def test_case_requires_bounded_typed_sources(self):
        with self.assertRaises(ValueError):
            ResponsibilityCase(('Alice',), 'a', 'a', self.case.premises)
        with self.assertRaises(ValueError):
            CognitionRequest('Assess responsibility', evidence=(self.action,),
                target_actor='Alice', responsibility_case=self.case)
        with self.assertRaises(ValueError):
            CognitionRequest('Assess responsibility',
                evidence=(self.action, self.outcome), target_actor='Bob',
                responsibility_case=self.case)
        with self.assertRaises(ValueError):
            NormativePremise('p1', 'rule', ())


if __name__ == '__main__':
    unittest.main()
