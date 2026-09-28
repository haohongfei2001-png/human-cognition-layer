"""Actual composed source comparison, without psychological or temporal promotion."""
from dataclasses import replace
import json
import unittest
from hcl.v1 import (CognitionRequest, HCLCognitionLayer, PerspectiveMode,
    prepare_composed_answer, answer_composed)
from hcl.v1.cg05 import prepare_concept_narrative

D = 'Alice: In team, by fair I mean consent is true.'
F = 'Narrator: In team, proposal has consent false.'
B = 'Alice: In team, I believe proposal is fair.'
HEAR = 'Narrator: Alice and Bob heard the previous statement.'


def reqs(text, **kwargs):
    return (CognitionRequest('Explain expressed belief', narrative=text, target_actor='Alice',
        belief_analysis=True, **kwargs), CognitionRequest('Interpret fair', narrative=text, target_actor='Alice',
        concept_analysis=True, concept_context='team', concept_term='fair', concept_item='proposal', **kwargs))


def wire(p):
    return json.loads(p.messages[-1]['content'])['composed_cognition']


class BeliefConceptComparisonTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda _: '')

    def prepare(self, text, **kwargs):
        return prepare_composed_answer(self.layer, 'Compare source claims cautiously', reqs(text, **kwargs),
            compare_belief_concepts=True)

    def test_actual_model_input_explains_source_difference_with_both_bases(self):
        text = '\n'.join((D, F, B))
        calls = []
        result = answer_composed(HCLCognitionLayer(lambda m: calls.append(m) or 'local source difference'),
            'Compare source claims', reqs(text), compare_belief_concepts=True, pool_sources=True, debug=True)
        rows = wire(result.prepared)['belief_concept_comparison']['rows']
        self.assertEqual(rows[0]['relation'], 'DIFFERS_FROM_LOCAL_SOURCE_CRITERIA')
        self.assertEqual(len(rows[0]['concept_source_event_ids']), 2)
        self.assertEqual(len(rows[0]['belief_source_event_ids']), 1)
        self.assertEqual(calls, [list(result.prepared.messages)])
        self.assertEqual(result.prepared.preparation_receipt['extraction_provider_calls'], 0)
        self.assertIn('never whether a private belief is true', calls[0][0]['content'])

    def test_consistency_does_not_establish_world_or_moral_truth(self):
        state = wire(self.prepare('\n'.join((D, F.replace('false', 'true'), B))))['belief_concept_comparison']
        self.assertEqual(state['rows'][0]['relation'], 'CONSISTENT_WITH_LOCAL_SOURCE_CRITERIA')
        self.assertIn('moral truth', state['unsupported_inferences'])
        self.assertEqual(state['rows'][0]['scope'], 'SOURCE_COMPARISON_NOT_PRIVATE_WORLD_OR_MORAL_TRUTH')

    def test_later_property_or_definition_cannot_diagnose_earlier_belief(self):
        for text in ('\n'.join((D, B, F)), '\n'.join((F, B, D))):
            row = wire(self.prepare(text))['belief_concept_comparison']['rows'][0]
            self.assertEqual(row['relation'], 'LATER_CONTEXT_NOT_EVIDENCE_OF_EARLIER_BELIEF')

    def test_later_indirect_report_never_moves_self_report_time(self):
        text = '\n'.join((D, B, F, 'Bob: In team, Alice believes proposal is fair.'))
        row = wire(self.prepare(text))['belief_concept_comparison']['rows'][0]
        self.assertEqual(row['relation'], 'LATER_CONTEXT_NOT_EVIDENCE_OF_EARLIER_BELIEF')

    def test_backdated_property_recorded_later_cannot_diagnose_prior_report(self):
        parsed = prepare_concept_narrative('\n'.join((D, F, B)), 'Alice', 'team', 'fair', 'proposal')
        events = tuple(replace(e, recorded_at='2026-01-03T00:00:00+00:00') if e.raw_text == F else e
            for e in parsed.events)
        requests = (CognitionRequest('Explain belief', target_actor='Alice', evidence=events, belief_analysis=True),
            CognitionRequest('Interpret fair', target_actor='Alice', evidence=events, concept_case=parsed.case))
        p = prepare_composed_answer(self.layer, 'Compare source claims', requests, compare_belief_concepts=True)
        self.assertEqual(wire(p)['belief_concept_comparison']['rows'][0]['relation'],
            'LATER_CONTEXT_NOT_EVIDENCE_OF_EARLIER_BELIEF')
        cutoff = tuple(replace(r, knowledge_cutoff=events[-1].recorded_at) for r in requests)
        p = prepare_composed_answer(self.layer, 'Compare source claims', cutoff, compare_belief_concepts=True)
        self.assertEqual(wire(p)['belief_concept_comparison']['rows'][0]['relation'], 'UNRESOLVED_SOURCE_COMPARISON')
        self.assertNotIn(F, p.messages[-1]['content'])

    def test_indirect_uncertain_denied_or_narrator_belief_does_not_assert_difference(self):
        for report in ('Bob: In team, Alice believes proposal is fair.',
            'Narrator: In team, Alice believes proposal is fair.',
            B.replace('I believe', 'I am unsure whether'), B.replace('I believe', 'I do not believe')):
            state = wire(self.prepare('\n'.join((D, F, report))))['belief_concept_comparison']
            self.assertTrue(all(r['relation'] == 'UNRESOLVED_SOURCE_COMPARISON' for r in state['rows']))

    def test_actor_context_item_term_boundaries_and_no_synonym_equivalence(self):
        for report in (B.replace('Alice:', 'Bob:'), B.replace('team', 'home'),
                       B.replace('proposal', 'policy'), B.replace('fair', 'unfair')):
            state = wire(self.prepare('\n'.join((D, F, report))))['belief_concept_comparison']
            self.assertFalse(state['rows'])
        attributed = D.replace('by fair I mean', 'Bob uses fair to mean')
        state = wire(self.prepare('\n'.join((attributed, F, B))))['belief_concept_comparison']
        self.assertFalse(state['rows'])

    def test_unknown_conflicting_or_multiple_readings_remain_local(self):
        unknown = wire(self.prepare('\n'.join((D, B))))['belief_concept_comparison']
        self.assertEqual(unknown['rows'][0]['relation'], 'UNRESOLVED_SOURCE_COMPARISON')
        conflict = wire(self.prepare('\n'.join((D, F, F.replace('false', 'true'), B))))['belief_concept_comparison']
        self.assertEqual(conflict['rows'][0]['relation'], 'UNRESOLVED_SOURCE_COMPARISON')
        multiple = wire(self.prepare('\n'.join((D, D.replace('true', 'false'), F, B))))['belief_concept_comparison']
        self.assertEqual(multiple['reading_relation'], 'MULTIPLE_LOCAL_READINGS')
        self.assertEqual({r['relation'] for r in multiple['rows']},
            {'DIFFERS_FROM_LOCAL_SOURCE_CRITERIA', 'CONSISTENT_WITH_LOCAL_SOURCE_CRITERIA'})

    def test_private_hidden_property_never_appears_as_comparison_basis(self):
        text = '\n'.join((D, HEAR, F, B, HEAR))
        p = self.prepare(text, narrative_access=True, observer_actor='Bob',
            perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET)
        state = wire(p)['belief_concept_comparison']
        self.assertEqual(state['rows'][0]['relation'], 'UNRESOLVED_SOURCE_COMPARISON')
        self.assertEqual(len(state['rows'][0]['concept_source_event_ids']), 1)
        self.assertNotIn(F, p.messages[-1]['content'])

    def test_explicit_revision_changes_only_current_comparable_proposition(self):
        text = '\n'.join((D, F, B, 'Alice: In team, I now believe proposal is safe instead of proposal is fair.'))
        rows = wire(self.prepare(text))['belief_concept_comparison']['rows']
        self.assertEqual(rows[0]['belief_status'], 'SUPERSEDED')
        self.assertEqual(rows[0]['relation'], 'UNRESOLVED_SOURCE_COMPARISON')
        self.assertEqual(len(rows), 1)

    def test_optin_bounds_and_whole_budget_drop_includes_comparison(self):
        text = '\n'.join((D, F, B))
        p = prepare_composed_answer(self.layer, 'Compare', reqs(text))
        self.assertNotIn('belief_concept_comparison', wire(p))
        with self.assertRaises(ValueError):
            prepare_composed_answer(self.layer, 'Compare', reqs(text), compare_belief_concepts=1)
        p = prepare_composed_answer(self.layer, 'Compare', reqs(text), max_context_chars=512,
            compare_belief_concepts=True)
        self.assertEqual(wire(p)['operation_contexts'], [])
        self.assertNotIn('belief_concept_comparison', wire(p))
