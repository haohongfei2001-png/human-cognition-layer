"""Explicit narrated exposure, chronological receipts and no psychological promotion."""
from copy import deepcopy
from dataclasses import replace
import json
import unittest
from hcl.v1 import (CognitionRequest, HCLCognitionLayer, PerspectiveMode, prepare_source_access,
    scope_source_access, prepare_preference_narrative, prepare_concept_narrative,
    check_preferences, check_concepts, prepare_composed_answer, expand_cognition_context)

P = 'Alice: As medic in team, I prefer safety over speed if rain is true.'
D = 'Alice: In team, by fair I mean consent is true.'
HEAR = 'Narrator: Alice heard the previous statement.'
RAIN = 'Narrator: In team, rain is true.'
PROP = 'Narrator: In team, proposal has consent true.'


def preference(text, **kwargs):
    return CognitionRequest('Explain preference', target_actor='Alice', narrative=text,
        preference_analysis=True, preference_role='medic', preference_context='team',
        narrative_access=True, **kwargs)


def concept(text, **kwargs):
    return CognitionRequest('Interpret fair', target_actor='Alice', narrative=text,
        concept_analysis=True, concept_context='team', concept_term='fair', concept_item='proposal',
        narrative_access=True, **kwargs)


class NarrativeAccessTests(unittest.TestCase):
    def test_ordinary_character_gets_only_explicitly_received_source_claims(self):
        text = '\n'.join((P, HEAR, RAIN, HEAR))
        p = HCLCognitionLayer(lambda _: '').prepare(preference(text,
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        self.assertEqual(p.context.preferences['checked']['statements'][0]['state'], 'APPLICABLE_SOURCE_CLAIM')
        self.assertEqual(len(p.context.evidence), 2)
        self.assertNotIn(HEAR, p.messages[1]['content'])
        receipt = p.preparation_receipt['output']['source_access']
        self.assertFalse(receipt['exposure_implies_belief'])
        self.assertEqual(len(receipt['basis']), 2)

    def test_unheard_condition_stays_unknown_and_hidden(self):
        p = HCLCognitionLayer(lambda _: '').prepare(preference(P + '\n' + HEAR + '\n' + RAIN,
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        self.assertEqual(p.context.preferences['checked']['statements'][0]['state'], 'CONDITION_UNRESOLVED')
        self.assertNotIn(RAIN, p.messages[1]['content'])

    def test_other_receiver_does_not_give_target_narrator_property(self):
        text = '\n'.join((D, HEAR, PROP, 'Narrator: Bob heard the previous statement.'))
        p = HCLCognitionLayer(lambda _: '').prepare(concept(text,
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        self.assertEqual(p.context.concepts['checked']['readings'][0]['state'], 'CRITERIA_UNRESOLVED')
        self.assertNotIn(PROP, p.messages[1]['content'])

    def test_no_cue_does_not_invent_access_even_with_actor_name(self):
        p = HCLCognitionLayer(lambda _: '').prepare(concept(D,
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        self.assertEqual(p.context.concepts['case_input']['definitions'], [])
        self.assertNotIn(D, p.messages[1]['content'])

    def test_negated_embedded_and_missing_previous_cues_fail_closed(self):
        for text in (D + '\nNarrator: It is false that Alice heard the previous statement.',
            D + '\nNarrator: Alice may have heard the previous statement.', HEAR + '\n' + D,
            D + '\nNarrator: Alice and Alice heard the previous statement.'):
            with self.subTest(text=text):
                p = HCLCognitionLayer(lambda _: '').prepare(concept(text,
                    perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
                self.assertEqual(p.preparation_receipt['source_access_status'], 'INVALID_ACCESS_SOURCE')
                self.assertEqual(p.context.concepts['case_input']['definitions'], [])

    def test_later_access_receipt_cannot_fill_earlier_event_or_record_view(self):
        parsed = prepare_concept_narrative(D + '\n' + HEAR, 'Alice', 'team', 'fair', 'proposal')
        evidence, receipt = prepare_source_access(parsed.events)
        for scope in ({'event_time': evidence[0].valid_time}, {'knowledge_cutoff': evidence[0].recorded_at}):
            r = check_concepts(parsed.case, evidence, mode='CHARACTER_PERSPECTIVE', **scope)
            self.assertEqual(r['readings'], [])
            req = CognitionRequest('Interpret fair', target_actor='Alice', evidence=evidence,
                concept_case=parsed.case, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE, **scope)
            p = HCLCognitionLayer(lambda _: '').prepare(req)
            self.assertNotIn(D, p.messages[1]['content'])
        self.assertEqual(check_concepts(parsed.case, evidence, mode='CHARACTER_PERSPECTIVE')['readings'][0]['state'],
                         'CRITERIA_UNRESOLVED')

    def test_observer_requires_access_to_target_source_channel(self):
        text = D + '\n' + HEAR + '\n' + PROP + '\nNarrator: Alice and Bob heard the previous statement.'
        p = HCLCognitionLayer(lambda _: '').prepare(concept(text,
            perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Bob'))
        self.assertEqual(p.context.concepts['case_input']['definitions'], [])
        self.assertTrue(p.context.concepts['case_input']['properties'])
        both = text.replace(HEAR, 'Narrator: Alice and Bob heard the previous statement.')
        p = HCLCognitionLayer(lambda _: '').prepare(concept(both,
            perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Bob'))
        self.assertEqual(p.context.concepts['checked']['readings'][0]['state'], 'CRITERIA_MET')

    def test_forged_anchor_receiver_and_public_promotion_rejected(self):
        parsed = prepare_concept_narrative(D + '\n' + HEAR, 'Alice', 'team', 'fair', 'proposal')
        evidence, _ = prepare_source_access(parsed.events)
        proof = deepcopy(evidence[0].metadata['narrative_access_basis'])
        proof['quote'] = 'unanchored access'
        bads = (replace(evidence[0], metadata=dict(evidence[0].metadata, narrative_access_basis=proof)),
            replace(evidence[0], recipient_ids=('Bob',)),
            replace(evidence[0], metadata=dict(evidence[0].metadata, public=True)))
        for bad in bads:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                scope_source_access((bad, evidence[1]))

    def test_previous_clause_cannot_chain_through_an_access_clause(self):
        parsed = prepare_concept_narrative(D + '\n' + HEAR + '\n' + HEAR, 'Alice', 'team', 'fair', 'proposal')
        evidence, receipt = prepare_source_access(parsed.events)
        self.assertEqual(receipt['status'], 'INVALID_ACCESS_SOURCE')
        self.assertEqual(check_concepts(parsed.case, evidence, mode='CHARACTER_PERSPECTIVE')['readings'], [])

    def test_scope_replay_is_idempotent_and_keeps_reader_raw_evidence(self):
        parsed = prepare_concept_narrative(D + '\n' + HEAR, 'Alice', 'team', 'fair', 'proposal')
        evidence, _ = prepare_source_access(parsed.events)
        scope = {'event_time': evidence[0].valid_time}
        restricted = scope_source_access(evidence, **scope)
        self.assertEqual(scope_source_access(restricted, **scope), restricted)
        row = check_concepts(parsed.case, evidence, mode='READER_ANALYSIS', **scope)
        self.assertEqual(len(row['readings']), 1)

    def test_character_composition_from_one_ordinary_input_without_manual_state(self):
        text = '\n'.join((P, HEAR, RAIN, HEAR, D, HEAR, PROP, HEAR))
        reqs = (preference(text, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE),
                concept(text, perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE))
        p = prepare_composed_answer(HCLCognitionLayer(lambda _: ''), 'Explain preferences and fair separately', reqs)
        rows = json.loads(p.messages[1]['content'])['composed_cognition']['operation_contexts']
        contexts = {r['operation']: expand_cognition_context(r['cognition_context']) for r in rows}
        self.assertEqual(contexts['preferences']['preferences']['checked']['statements'][0]['state'], 'APPLICABLE_SOURCE_CLAIM')
        self.assertEqual(contexts['concepts']['concepts']['checked']['readings'][0]['state'], 'CRITERIA_MET')
        self.assertNotIn(HEAR, p.messages[1]['content'])
        self.assertTrue(all(r['answer_provider_calls'] == 0 for r in p.preparation_receipt['stage_preparation']))

    def test_invalid_flag_and_unrelated_operation_not_activated(self):
        with self.assertRaises(ValueError):
            CognitionRequest('Hello', narrative_access=True)
        with self.assertRaises(ValueError):
            replace(concept(D), narrative_access=1)
