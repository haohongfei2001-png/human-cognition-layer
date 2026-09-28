"""CG03-A typed operation and bounded-view non-promotion checks."""
from datetime import datetime, timezone, timedelta
from dataclasses import replace
import unittest

from hcl.v04.model import EventRecord
from hcl.v1 import (CognitionRequest, CognitionRouter, HCLCognitionLayer,
                    NormativePremise, PerspectiveMode, ResponsibilityCase,
                    ResponsibilityFactor as Factor, FactorRequirement,
                    FactorClaim, ClaimAuthority, NarrativePremise,
                    check_responsibility, prepare_responsibility_narrative)
import json


BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def stamp(second):
    return (BASE + timedelta(seconds=second)).isoformat()


def event(event_id, second, text, actor=None, reader_only=False):
    time = stamp(second)
    return EventRecord(event_id, time, text, 'cg03-test', time, actor,
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
        row = prepared.context.responsibility['checked']
        self.assertEqual(row['status'], 'SOURCE_FACTORS_CHECKED')
        self.assertEqual(row['conclusion'], 'PREMISE_DEPENDENT_ONLY')
        self.assertEqual(row['premise_assessments'][0]['result'], 'UNRESOLVED_NO_STRUCTURED_RULE')
        self.assertTrue(all(f['state'] == 'UNKNOWN' for f in row['factors']))
        self.assertIn('SOURCE_FACTORS_CHECKED', prepared.messages[-1]['content'])

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


class FactorAndPremiseChecks(unittest.TestCase):
    def setUp(self):
        self.action = event('action', 0, 'Alice opened the gate.', 'Alice')
        self.outcome = event('outcome', 1, 'The animals escaped.', reader_only=True)
        self.causal = event('cause', 2, "Alice's opening caused the animals to escape.",
                            reader_only=True)
        self.knowledge = event('knowledge', 0,
            'Alice: I knew the latch was weak at the time.', 'Alice')
        self.foresee = event('foresee', 0,
            'Alice: I expected the animals to escape.', 'Alice')
        self.control = event('control', 0,
            'At the time Alice could have stopped the opening.', reader_only=True)
        self.intention = event('intention', 0,
            'Alice: I intended to open the gate.', 'Alice')
        self.events = (self.action, self.outcome, self.causal, self.knowledge,
                       self.foresee, self.control, self.intention)
        data = (
            ('causal', Factor.CAUSAL_CONTRIBUTION, self.causal, ClaimAuthority.EXPLICIT_NARRATOR),
            ('knowledge', Factor.KNOWLEDGE, self.knowledge, ClaimAuthority.DIRECT_SELF_REPORT),
            ('foresee', Factor.FORESEEABILITY, self.foresee, ClaimAuthority.DIRECT_SELF_REPORT),
            ('control', Factor.CONTROL, self.control, ClaimAuthority.EXPLICIT_NARRATOR),
            ('intention', Factor.STATED_INTENTION, self.intention, ClaimAuthority.DIRECT_SELF_REPORT),
        )
        self.claims = tuple(FactorClaim(name, kind, 'Alice', 'action', source.event_id,
            source.raw_text, stamp(0), True, authority)
            for name, kind, source, authority in data)
        self.premise = NormativePremise('rule',
            'For this case, causal contribution, knowledge and control support the stated basis.',
            tuple(e.event_id for e in self.events),
            (FactorRequirement(Factor.CAUSAL_CONTRIBUTION, True),
             FactorRequirement(Factor.KNOWLEDGE, True),
             FactorRequirement(Factor.CONTROL, True)))
        self.case = ResponsibilityCase(('Alice',), 'action', 'outcome',
                                       (self.premise,), self.claims)

    def test_five_factors_and_conditional_premise_stay_separate(self):
        checked = check_responsibility(self.case, self.events, target_actor='Alice')
        self.assertEqual([f['state'] for f in checked['factors']],
                         ['SUPPORTED_CLAIM'] * 5)
        self.assertEqual(checked['premise_assessments'][0]['result'],
                         'CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS')
        self.assertEqual(checked['conclusion'], 'PREMISE_DEPENDENT_ONLY')
        self.assertEqual(checked['other_relevant_facts'], 'OPEN_UNKNOWN')
        self.assertNotIn('liable', str(checked).lower())

    def test_later_knowledge_and_polarity_mismatch_rejected(self):
        late = event('late', 3, 'Alice: I learned about the weak latch afterward.', 'Alice')
        bad = FactorClaim('late', Factor.KNOWLEDGE, 'Alice', 'action', 'late',
                          late.raw_text, stamp(0), True, ClaimAuthority.DIRECT_SELF_REPORT)
        case = ResponsibilityCase(('Alice',), 'action', 'outcome', (self.premise,),
                                  (bad,))
        with self.assertRaisesRegex(ValueError, 'later learning'):
            check_responsibility(case, self.events + (late,), target_actor='Alice')
        inverted = FactorClaim('invert', Factor.KNOWLEDGE, 'Alice', 'action', 'knowledge',
            self.knowledge.raw_text, stamp(0), False, ClaimAuthority.DIRECT_SELF_REPORT)
        with self.assertRaisesRegex(ValueError, 'polarity'):
            check_responsibility(ResponsibilityCase(('Alice',), 'action', 'outcome',
                (self.premise,), (inverted,)), self.events, target_actor='Alice')

    def test_third_party_intention_cannot_support_premise(self):
        report = event('report', 3, 'Bob: At the time Alice said she intended to release the animals.', 'Bob')
        attributed = FactorClaim('guess', Factor.STATED_INTENTION, 'Alice', 'action',
            'report', report.raw_text, stamp(0), True, ClaimAuthority.THIRD_PARTY_ATTRIBUTION)
        scoped = NormativePremise('rule', 'Intention is required here.',
            ('action', 'outcome', 'report'), (FactorRequirement(Factor.STATED_INTENTION, True),))
        case = ResponsibilityCase(('Alice', 'Bob'), 'action', 'outcome',
                                  (scoped,), (attributed,))
        result = check_responsibility(case, (self.action, self.outcome, report),
                                      target_actor='Alice')
        self.assertEqual(result['factors'][-1]['state'], 'ATTRIBUTED_ONLY')
        self.assertEqual(result['premise_assessments'][0]['result'], 'UNRESOLVED')

    def test_counterexample_and_source_scope(self):
        no_control = event('no-control', 0,
            'At the time Alice could not control the gate.', reader_only=True)
        denied = FactorClaim('denied', Factor.CONTROL, 'Alice', 'action', 'no-control',
            no_control.raw_text, stamp(0), False, ClaimAuthority.EXPLICIT_NARRATOR)
        premise = NormativePremise('rule', 'Control is required.',
            ('action', 'outcome', 'no-control'), (FactorRequirement(Factor.CONTROL, True),))
        case = ResponsibilityCase(('Alice',), 'action', 'outcome', (premise,), (denied,))
        result = check_responsibility(case, (self.action, self.outcome, no_control),
                                      target_actor='Alice')
        self.assertEqual(result['premise_assessments'][0]['result'],
                         'CONDITIONALLY_NOT_SUPPORTED')
        self.assertEqual(result['premise_assessments'][0]['requirements'][0]['result'],
                         'COUNTEREXAMPLE_IN_SOURCE')
        self.assertEqual(check_responsibility(self.case, self.events, target_actor='Alice',
            mode='CHARACTER_PERSPECTIVE')['status'], 'SOURCE_VIEW_INSUFFICIENT')
        narrow = NormativePremise('narrow', 'Control is required.',
            ('action', 'outcome'), (FactorRequirement(Factor.CONTROL, True),))
        no_source = ResponsibilityCase(('Alice',), 'action', 'outcome',
                                       (narrow,), (self.claims[3],))
        unresolved = check_responsibility(no_source, self.events,
                                          target_actor='Alice')
        self.assertEqual(unresolved['factors'][3]['state'], 'SUPPORTED_CLAIM')
        self.assertEqual(unresolved['premise_assessments'][0]['result'], 'UNRESOLVED')

    def test_other_actor_and_later_source_do_not_enter_focal_assessment(self):
        bob = event('bob', 0, 'Bob: I knew the latch was weak.', 'Bob')
        bob_claim = FactorClaim('bob-knew', Factor.KNOWLEDGE, 'Bob', 'action',
            'bob', bob.raw_text, stamp(0), True, ClaimAuthority.DIRECT_SELF_REPORT)
        premise = NormativePremise('knowledge-rule', 'Alice knowledge is required.',
            ('action', 'outcome', 'bob'), (FactorRequirement(Factor.KNOWLEDGE, True),))
        case = ResponsibilityCase(('Alice', 'Bob'), 'action', 'outcome',
                                  (premise,), (bob_claim,))
        result = check_responsibility(case, (self.action, self.outcome, bob),
                                      target_actor='Alice')
        self.assertEqual(result['factors'][1]['state'], 'UNKNOWN')
        self.assertEqual(result['premise_assessments'][0]['result'], 'UNRESOLVED')
        cutoff = check_responsibility(self.case, self.events, target_actor='Alice',
                                      event_time=stamp(1))
        self.assertEqual(cutoff['factors'][0]['state'], 'UNKNOWN')
        self.assertEqual(cutoff['premise_assessments'], [])

    def test_competing_source_claims_remain_contested(self):
        no_control = event('no-control', 0,
            'At the time Alice could not control the gate.', reader_only=True)
        denial = FactorClaim('denial', Factor.CONTROL, 'Alice', 'action',
            'no-control', no_control.raw_text, stamp(0), False,
            ClaimAuthority.EXPLICIT_NARRATOR)
        premise = NormativePremise('control-rule', 'Control is required.',
            ('action', 'outcome', 'control', 'no-control'),
            (FactorRequirement(Factor.CONTROL, True),))
        case = ResponsibilityCase(('Alice',), 'action', 'outcome', (premise,),
                                  (self.claims[3], denial))
        result = check_responsibility(case,
            (self.action, self.outcome, self.control, no_control),
            target_actor='Alice')
        self.assertEqual(result['factors'][3]['state'], 'CONTESTED')
        self.assertEqual(result['premise_assessments'][0]['result'], 'UNRESOLVED')

    def test_quote_and_record_time_boundaries(self):
        fabricated = FactorClaim('fake', Factor.CONTROL, 'Alice', 'action',
            'control', 'Alice could have stopped a different event.', stamp(0),
            True, ClaimAuthority.EXPLICIT_NARRATOR)
        with self.assertRaisesRegex(ValueError, 'exact source span'):
            check_responsibility(ResponsibilityCase(('Alice',), 'action',
                'outcome', (self.premise,), (fabricated,)), self.events,
                target_actor='Alice')
        later_recorded = replace(self.knowledge, recorded_at=stamp(10))
        events = tuple(later_recorded if e.event_id == 'knowledge' else e
                       for e in self.events)
        checked = check_responsibility(self.case, events, target_actor='Alice',
                                       knowledge_cutoff=stamp(3))
        self.assertEqual(checked['factors'][1]['state'], 'UNKNOWN')
        self.assertEqual(checked['premise_assessments'], [])

    def test_hidden_other_actor_name_is_not_projected(self):
        public_outcome = replace(self.outcome, metadata={'public': True})
        secret = event('secret', 0, 'Bob: I knew the latch was weak.',
                       'Bob', reader_only=True)
        bob_claim = FactorClaim('bob', Factor.KNOWLEDGE, 'Bob', 'action',
            'secret', secret.raw_text, stamp(0), True,
            ClaimAuthority.DIRECT_SELF_REPORT)
        premise = NormativePremise('p', 'Alice control matters.',
            ('action', 'outcome'), (FactorRequirement(Factor.CONTROL, True),))
        case = ResponsibilityCase(('Alice', 'Bob'), 'action', 'outcome',
                                  (premise,), (bob_claim,))
        request = CognitionRequest('Assess responsibility',
            evidence=(self.action, public_outcome, secret), target_actor='Alice',
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE,
            responsibility_case=case)
        prepared = HCLCognitionLayer(lambda _: 'ok').prepare(request)
        self.assertEqual(prepared.context.responsibility['case_input']['actor_ids'],
                         ['Alice'])
        self.assertNotIn('Bob', prepared.messages[-1]['content'])
        self.assertEqual(prepared.context.responsibility['checked']['factors'][1]['state'],
                         'UNKNOWN')


class OrdinaryTextResponsibility(unittest.TestCase):
    def setUp(self):
        self.narrative = '\n'.join((
            'Alice: I opened the gate.',
            'Narrator: The animals escaped.',
            'Narrator: Alice opening the gate caused the animals to escape.',
            'Alice: At the time I knew the latch was weak.',
            'Alice: At the time I expected the animals to escape.',
            'Narrator: At the time Alice could have stopped the opening.',
            'Alice: At the time I intended to open the gate.',
        ))
        self.premises = (NarrativePremise('p1',
            'For this case, contribution and control support the stated basis.',
            (FactorRequirement(Factor.CAUSAL_CONTRIBUTION, True),
             FactorRequirement(Factor.CONTROL, True))),)

    def request(self, narrative=None, **kwargs):
        return CognitionRequest('Assess Alice responsibility', target_actor='Alice',
            narrative=self.narrative if narrative is None else narrative,
            responsibility_analysis=True,
            responsibility_premises=self.premises, **kwargs)

    def test_parser_checked_state_and_final_input_ablation(self):
        parsed = prepare_responsibility_narrative(self.narrative, 'Alice', self.premises)
        self.assertIsNone(parsed.failure)
        self.assertEqual(len(parsed.events), 7)
        self.assertEqual(len(parsed.case.claims), 5)
        self.assertTrue(all(e.raw_text in self.narrative for e in parsed.events))
        active = HCLCognitionLayer(lambda _: 'ok').answer(self.request(), debug=True)
        ablated = HCLCognitionLayer(lambda _: 'ok',
            responsibility_checker_enabled=False).answer(self.request(), debug=True)
        h = active.prepared.context.responsibility
        h_new = ablated.prepared.context.responsibility
        self.assertEqual(h['checked']['status'], 'SOURCE_FACTORS_CHECKED')
        self.assertEqual(h['checked']['premise_assessments'][0]['result'],
                         'CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS')
        self.assertEqual(h_new['checked'], {})
        self.assertEqual(h['case_input'], h_new['case_input'])
        self.assertEqual(active.prepared.preparation_receipt['input']['narrative'],
                         self.narrative)
        self.assertEqual(len(active.prepared.preparation_receipt['output']['claim_ids']), 5)
        self.assertNotEqual(active.prepared.messages, ablated.prepared.messages)
        active_payload = json.loads(active.prepared.messages[-1]['content'])
        ablated_payload = json.loads(ablated.prepared.messages[-1]['content'])
        active_payload['cognition_context']['responsibility']['checked'] = {}
        self.assertEqual(active_payload, ablated_payload)
        self.assertEqual(active.prepared.preparation_receipt['extraction_provider_calls'], 0)

    def test_failure_closes_to_uncertainty_without_source_or_rule_leak(self):
        malformed = 'Alice: I opened the gate.\nNarrator: The animals escaped.\n'
        malformed += 'Alice: I opened the gate again.'
        prepared = HCLCognitionLayer(lambda _: 'ok').prepare(self.request(malformed))
        self.assertEqual(prepared.preparation_receipt['failure'],
                         'action_or_outcome_ambiguous')
        self.assertEqual(prepared.context.responsibility, {})
        self.assertTrue(any(u.get('capability') == 'cg03_responsibility_structure'
                            for u in prepared.context.uncertainty))
        self.assertNotIn('The animals escaped', prepared.messages[-1]['content'])
        self.assertNotIn('contribution and control', prepared.messages[-1]['content'])

    def test_later_learning_is_rejected_not_promoted(self):
        narrative = self.narrative.replace(
            'Alice: At the time I knew the latch was weak.',
            'Alice: I learned about the weak latch afterward.')
        parsed = prepare_responsibility_narrative(narrative, 'Alice', self.premises)
        self.assertIsNone(parsed.failure)
        self.assertEqual(len(parsed.case.claims), 4)
        self.assertTrue(any(d['status'] == 'FACTOR_REJECTED'
                            for d in parsed.source_span_diagnostics))
        prepared = HCLCognitionLayer(lambda _: 'ok').prepare(self.request(narrative))
        knowledge = next(f for f in prepared.context.responsibility['checked']['factors']
                         if f['factor'] == 'KNOWLEDGE')
        self.assertEqual(knowledge['state'], 'UNKNOWN')


if __name__ == '__main__':
    unittest.main()
