"""Retained belief ordinary input, actual composition and source boundaries."""
from dataclasses import replace
import json
import unittest

from hcl.v04.model import EventRecord
from hcl.v1 import (CognitionRequest, HCLCognitionLayer, PerspectiveMode,
    answer_composed, expand_cognition_context, expand_composed_sources)
from hcl.v1.belief_preparation import (belief_narrative_events, prepare_belief_sources,
    SourceBeliefBackend)
from hcl.v07 import HCLV07Runtime

SELF = 'Alice: In team, I believe proposal is fair.'
UNCERTAIN = 'Alice: In team, I am unsure whether proposal is safe.'
REVISION = 'Alice: In team, I now believe proposal is unfair instead of proposal is fair.'
REPORT = 'Bob: In team, Alice believes proposal is fair.'
DEFINITION = 'Alice: In team, by fair I mean consent is true.'
HEAR = 'Narrator: Alice and Bob heard the previous statement.'


def request(text=SELF, **kwargs):
    return CognitionRequest('Explain the expressed belief', target_actor='Alice',
        narrative=text, belief_analysis=True, **kwargs)


def statuses(prepared):
    return {row['proposition_key']: row['status'] for row in prepared.context.belief}


class BeliefPreparationTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda _: 'source explanation')

    def test_explicit_self_report_and_uncertainty_enter_actual_retained_state(self):
        p = self.layer.prepare(request(SELF + '\n' + UNCERTAIN))
        self.assertEqual(statuses(p), {'team/proposal/fair': 'AFFIRMED', 'team/proposal/safe': 'CHARACTER_UNCERTAIN'})
        wire = json.loads(p.messages[-1]['content'])['cognition_context']
        self.assertEqual(wire['belief'], p.context.belief)
        self.assertEqual(p.preparation_receipt['extraction_provider_calls'], 0)
        self.assertEqual(p.preparation_receipt['local_validator_calls'], 2)
        self.assertEqual(p.context.provenance[-1]['evidence_level'], 'DIRECT_SELF_REPORT')
        self.assertNotIn('intention', p.plan.capabilities)

    def test_indirect_attribution_and_narrator_assertion_remain_distinct(self):
        report = self.layer.prepare(request(REPORT))
        self.assertEqual(statuses(report), {'team/proposal/fair': 'SYSTEM_INSUFFICIENT'})
        self.assertTrue(report.context.belief[0]['indirect_support_evidence_ids'])
        self.assertEqual(report.context.provenance[-1]['evidence_level'], 'THIRD_PARTY_REPORT')
        narrator = self.layer.prepare(request(REPORT.replace('Bob:', 'Narrator:')))
        self.assertEqual(statuses(narrator), {'team/proposal/fair': 'AFFIRMED'})
        self.assertEqual(narrator.context.provenance[-1]['evidence_level'], 'EXPLICIT_NARRATOR_REPORT')
        character = self.layer.prepare(request(REPORT.replace('Bob:', 'Narrator:'),
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        self.assertFalse(character.context.belief)
        self.assertFalse(character.context.evidence)

    def test_denial_is_distinct_from_positive_opposite_and_world_truth(self):
        p = self.layer.prepare(request(SELF.replace('I believe', 'I do not believe')))
        self.assertEqual(statuses(p), {'team/proposal/fair': 'DENIED'})
        self.assertNotIn('unfair', str(p.context.belief))
        self.assertIn('not verified private', p.messages[0]['content'])

    def test_exposure_does_not_create_acceptance_or_character_uncertainty(self):
        p = self.layer.prepare(request(DEFINITION + '\n' + HEAR,
            narrative_access=True, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        self.assertFalse(p.context.belief)
        self.assertEqual(p.context.uncertainty[0]['status'], 'SYSTEM_INSUFFICIENT')
        self.assertEqual(p.context.evidence[0]['raw_text'], DEFINITION)

    def test_explicit_revision_local_actor_and_context(self):
        text = '\n'.join((SELF, 'Bob: In team, I believe proposal is fair.',
            'Alice: In home, I believe proposal is fair.', REVISION))
        p = self.layer.prepare(request(text))
        self.assertEqual(statuses(p), {'team/proposal/fair': 'SUPERSEDED',
            'team/proposal/unfair': 'AFFIRMED', 'home/proposal/fair': 'AFFIRMED'})
        bob = self.layer.prepare(replace(request(text), target_actor='Bob'))
        self.assertEqual(statuses(bob), {'team/proposal/fair': 'AFFIRMED'})

    def test_revision_without_visible_anchor_never_manufactures_old_state(self):
        p = self.layer.prepare(request(SELF + '\n' + REVISION + '\n' + HEAR,
            narrative_access=True, observer_actor='Bob',
            perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET))
        self.assertEqual(statuses(p), {'team/proposal/unfair': 'AFFIRMED'})
        self.assertIsNone(p.context.belief[0]['superseded_by_proposition_key'])
        self.assertIn('REVISION_ANCHOR_UNAVAILABLE', str(p.preparation_receipt['output']))

    def test_actor_prefix_mismatch_and_unanchored_backend_fail_closed(self):
        events = belief_narrative_events(SELF)
        forged = replace(events[0], actor_id='Bob')
        p = self.layer.prepare(CognitionRequest('Explain belief', target_actor='Alice',
            belief_analysis=True, evidence=(forged,)))
        self.assertFalse(p.context.belief)
        self.assertEqual(p.preparation_receipt['failure'], 'belief_source_actor_mismatch')
        payload = prepare_belief_sources(events).payloads[0][1]
        with self.assertRaises(ValueError):
            SourceBeliefBackend(events[0], payload).complete_json([{'content': json.dumps({'event': {
                'event_id': events[0].event_id, 'raw_text': 'unanchored', 'actor_id': 'Alice'}})}], max_tokens=1)

    def test_event_and_record_cutoffs_do_not_use_later_revision(self):
        events = belief_narrative_events(SELF + '\n' + REVISION)
        late = replace(events[1], recorded_at='2026-01-02T00:00:00+00:00')
        for scope in ({'event_time': events[0].valid_time}, {'knowledge_cutoff': events[0].recorded_at}):
            p = self.layer.prepare(CognitionRequest('Explain belief', target_actor='Alice',
                belief_analysis=True, evidence=(events[0], late), **scope))
            self.assertEqual(statuses(p), {'team/proposal/fair': 'AFFIRMED'})
            self.assertNotIn(REVISION, p.messages[-1]['content'])
            self.assertNotIn('unfair', p.messages[-1]['content'])

    def test_partial_embedded_action_and_ambiguous_sources_never_infer_belief(self):
        for line in ('Alice: In team, I believe perhaps proposal is fair.',
                     'Bob said "Alice: In team, I believe proposal is fair."',
                     'Alice: In team, I believe proposal is fair and safe.'):
            p = self.layer.prepare(request(SELF + '\n' + line))
            self.assertFalse(p.context.belief)
            self.assertEqual(p.preparation_receipt['failure'], 'unsupported_or_ambiguous_belief_source')
            self.assertIn(line, str(p.context.evidence))
        p = self.layer.prepare(request('Alice: In team, I chose proposal.'))
        self.assertFalse(p.context.belief)
        self.assertEqual(p.preparation_receipt['failure'], 'no_explicit_belief')

    def test_private_receiver_boundaries_and_reader_only_evidence(self):
        text = SELF + '\n' + 'Narrator: Bob heard the previous statement.'
        bob = self.layer.prepare(request(text, narrative_access=True, observer_actor='Bob',
            perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET))
        self.assertEqual(statuses(bob), {'team/proposal/fair': 'AFFIRMED'})
        carol = self.layer.prepare(request(text, narrative_access=True, observer_actor='Carol',
            perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET))
        self.assertFalse(carol.context.belief)
        self.assertNotIn('team/proposal/fair', carol.messages[-1]['content'])
        self.assertNotIn(SELF, carol.messages[-1]['content'])

    def test_one_composed_call_keeps_belief_definition_and_preference_separate(self):
        text = '\n'.join((SELF, HEAR, REVISION, HEAR, DEFINITION, HEAR,
            'Narrator: In team, proposal has consent true.', HEAR,
            'Alice: As medic in team, I prefer safety over speed.', HEAR))
        reqs = (request(text, narrative_access=True, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE),
            CognitionRequest('Interpret fair', target_actor='Alice', narrative=text,
                concept_analysis=True, concept_context='team', concept_term='fair', concept_item='proposal',
                narrative_access=True, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE),
            CognitionRequest('Explain preference', target_actor='Alice', narrative=text,
                preference_analysis=True, preference_role='medic', preference_context='team',
                narrative_access=True, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        calls = []
        result = answer_composed(HCLCognitionLayer(lambda m: calls.append(m) or 'separate source claims'),
            'Compare expressed belief with local criteria and preference', reqs, pool_sources=True, debug=True)
        self.assertEqual(calls, [list(result.prepared.messages)])
        state = expand_composed_sources(json.loads(calls[0][-1]['content'])['composed_cognition'])
        rows = {r['operation']: expand_cognition_context(r['cognition_context']) for r in state['operation_contexts']}
        self.assertEqual(rows['belief']['belief'][-1]['status'], 'AFFIRMED')
        self.assertEqual(rows['concepts']['concepts']['checked']['readings'][0]['state'], 'CRITERIA_MET')
        self.assertEqual(rows['preferences']['preferences']['checked']['statements'][0]['state'], 'APPLICABLE_SOURCE_CLAIM')
        self.assertEqual(result.prepared.preparation_receipt['extraction_provider_calls'], 0)
        self.assertTrue(all(r['answer_provider_calls'] == 0 for r in result.prepared.preparation_receipt['stage_preparation']))
        self.assertTrue(all(not r['explicit_intention'] for r in rows.values()))

    def test_bounded_optin_and_no_injected_persistent_state(self):
        with self.assertRaises(ValueError):
            request(SELF, preference_analysis=True, preference_role='medic', preference_context='team')
        with self.assertRaises(ValueError):
            replace(request(), belief_analysis=1)
        with self.assertRaises(ValueError):
            HCLCognitionLayer(lambda _: '', intentions=HCLV07Runtime()).prepare(request())
        many = '\n'.join(f'Alice: In team, I believe proposal is label{i}.' for i in range(9))
        p = self.layer.prepare(request(many))
        self.assertFalse(p.context.belief)
        self.assertEqual(p.preparation_receipt['failure'], 'belief_semantic_bounds')
