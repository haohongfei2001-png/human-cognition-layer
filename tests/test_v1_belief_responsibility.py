"""Retained belief plus conditional responsibility, without cross-operation upgrades."""
import json
import unittest
from hcl.v1 import (HCLCognitionLayer, CognitionRequest, PerspectiveMode, prepare_person_context,
    answer_person_context, expand_cognition_context, expand_composed_sources,
    NarrativePremise, FactorRequirement, ResponsibilityFactor)

QUERY = "Explain Alice's belief and conditional responsibility."
B = 'Alice: In team, I believe gate is planned.'
ACTION = 'Alice: I opened the gate.'
OUTCOME = 'Narrator: The animals escaped.'
CAUSE = 'Narrator: Alice opening the gate caused the animals to escape.'
CONTROL = 'Narrator: At the time Alice could not have stopped the opening.'
HEAR = 'Narrator: Alice and Bob heard the previous statement.'
SOURCE = '\n'.join((B, ACTION, OUTCOME, CAUSE, CONTROL))


def premise(factor, value=True):
    return (NarrativePremise('caller-rule', 'For this case the named factor is required.',
        (FactorRequirement(ResponsibilityFactor(factor), value),)),)


def contexts(p):
    wire = json.loads(p.messages[-1]['content'])
    if 'composed_cognition' not in wire:
        return {'responsibility': p.context.as_dict()}
    state = expand_composed_sources(wire['composed_cognition'])
    return {r['operation']: expand_cognition_context(r['cognition_context']) for r in state['operation_contexts']}


def checked(p):
    return contexts(p)['responsibility']['responsibility']['checked']


def factors(p):
    return {row['factor']: row['state'] for row in checked(p)['factors']}


class BeliefResponsibilityTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda _: '')

    def prepare(self, text=SOURCE, factor='STATED_INTENTION', **kwargs):
        return prepare_person_context(self.layer, QUERY, text, responsibility_premises=premise(factor), **kwargs)

    def test_real_belief_state_never_becomes_stated_intention_from_planned_token(self):
        p = self.prepare()
        self.assertEqual(contexts(p)['belief']['belief'][0]['status'], 'AFFIRMED')
        self.assertEqual(factors(p)['STATED_INTENTION'], 'UNKNOWN')
        self.assertEqual(checked(p)['premise_assessments'][0]['result'], 'UNRESOLVED')
        self.assertEqual(p.preparation_receipt['extraction_provider_calls'], 0)
        malformed = self.prepare(SOURCE.replace('I believe', 'I Believe'))
        self.assertEqual(factors(malformed)['STATED_INTENTION'], 'UNKNOWN')
        self.assertFalse(contexts(malformed)['belief']['belief'])

    def test_all_incidental_belief_factor_words_stay_belief_not_responsibility(self):
        claims = [f'Alice: In team, I believe gate is {term}.' for term in ('caused', 'aware', 'expected', 'control', 'planned')]
        p = self.prepare('\n'.join(claims + [ACTION, OUTCOME]))
        self.assertTrue(all(state == 'UNKNOWN' for state in factors(p).values()))
        self.assertEqual(len(contexts(p)['belief']['belief']), 5)

    def test_local_concept_property_and_preference_are_not_control_claims(self):
        text = '\n'.join(('Narrator: In team, Alice has control true.',
            'Alice: In team, by control I mean safe is true.',
            'Alice: As medic in team, I prefer control over speed.', ACTION, OUTCOME))
        p = self.prepare(text, factor='CONTROL')
        self.assertEqual(factors(p)['CONTROL'], 'UNKNOWN')
        self.assertEqual(checked(p)['premise_assessments'][0]['result'], 'UNRESOLVED')

    def test_belief_reported_action_or_concept_outcome_cannot_anchor_episode(self):
        for text in ('Alice: I believe I opened the gate.\n' + OUTCOME,
            ACTION + '\nNarrator: In team, animals has escaped true.'):
            p = prepare_person_context(self.layer, "Explain Alice's conditional responsibility.", text,
                responsibility_premises=premise('CAUSAL_CONTRIBUTION'))
            self.assertFalse(p.context.responsibility)
            self.assertEqual(p.preparation_receipt['failure'], 'action_or_outcome_ambiguous')

    def test_private_explicit_focal_episode_scope_does_not_require_receipt_cue_as_rule_basis(self):
        source = '\n'.join(line for claim in SOURCE.splitlines() for line in (claim, HEAR))
        p = self.prepare(source, factor='CONTROL', premise_scope='FOCAL_EPISODE', narrative_access=True,
            perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Bob')
        self.assertEqual(factors(p)['CONTROL'], 'CONTRADICTED_CLAIM')
        self.assertEqual(checked(p)['premise_assessments'][0]['result'], 'CONDITIONALLY_NOT_SUPPORTED')
        scope = contexts(p)['responsibility']['responsibility']['case_input']['premises'][0]['basis_event_ids']
        raw_sources = contexts(p)['responsibility']['evidence']
        expected = {e['event_id'] for e in raw_sources if e['raw_text'] in (ACTION, OUTCOME, CONTROL)}
        self.assertEqual(set(scope), expected)
        self.assertEqual(len(scope), 3)
        self.assertNotIn(HEAR, p.messages[-1]['content'])
        self.assertIn('caller explicitly scopes', p.messages[0]['content'])

    def test_default_whole_source_scope_and_unexposed_observer_remain_blocked(self):
        source = '\n'.join(line for claim in SOURCE.splitlines() for line in (claim, HEAR))
        kwargs = dict(narrative_access=True, perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET)
        old = self.prepare(source, observer_actor='Bob', **kwargs)
        self.assertNotIn('responsibility', contexts(old)['responsibility'])
        hidden = self.prepare(source, observer_actor='Carol', premise_scope='FOCAL_EPISODE', **kwargs)
        self.assertNotIn('responsibility', contexts(hidden)['responsibility'])
        self.assertFalse(contexts(hidden)['belief']['belief'])
        self.assertNotIn(B, hidden.messages[-1]['content'])
        self.assertNotIn(OUTCOME, hidden.messages[-1]['content'])

    def test_unseen_unrelated_factor_does_not_become_rule_basis_or_visible_state(self):
        source = '\n'.join(line for claim in (B, ACTION, OUTCOME, CAUSE) for line in (claim, HEAR)) + '\n' + CONTROL
        p = self.prepare(source, factor='CAUSAL_CONTRIBUTION', premise_scope='FOCAL_EPISODE', narrative_access=True,
            perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Bob')
        self.assertEqual(factors(p)['CAUSAL_CONTRIBUTION'], 'SUPPORTED_CLAIM')
        self.assertEqual(factors(p)['CONTROL'], 'UNKNOWN')
        self.assertEqual(checked(p)['premise_assessments'][0]['result'], 'CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS')
        self.assertNotIn(CONTROL, p.messages[-1]['content'])

    def test_outcome_causality_control_and_later_learning_stay_separate(self):
        p = self.prepare(SOURCE + '\nAlice: I learned about the weak latch afterward.', factor='KNOWLEDGE')
        self.assertEqual(factors(p), {'CAUSAL_CONTRIBUTION': 'SUPPORTED_CLAIM',
            'KNOWLEDGE': 'UNKNOWN', 'FORESEEABILITY': 'UNKNOWN',
            'CONTROL': 'CONTRADICTED_CLAIM', 'STATED_INTENTION': 'UNKNOWN'})
        self.assertEqual(checked(p)['premise_assessments'][0]['result'], 'UNRESOLVED')

    def test_explicit_action_time_knowledge_supports_only_knowledge(self):
        p = self.prepare(SOURCE + '\nAlice: At the time I knew the latch was weak.', factor='KNOWLEDGE')
        self.assertEqual(factors(p)['KNOWLEDGE'], 'SUPPORTED_CLAIM')
        self.assertEqual(factors(p)['FORESEEABILITY'], 'UNKNOWN')
        self.assertEqual(factors(p)['STATED_INTENTION'], 'UNKNOWN')
        self.assertEqual(checked(p)['premise_assessments'][0]['result'], 'CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS')

    def test_indirect_intention_remains_attribution_and_direct_intention_stays_supported(self):
        indirect = self.prepare(SOURCE + '\nBob: At the time Alice said she intended to let the animals escape.')
        self.assertEqual(factors(indirect)['STATED_INTENTION'], 'ATTRIBUTED_ONLY')
        self.assertEqual(checked(indirect)['premise_assessments'][0]['result'], 'UNRESOLVED')
        direct = self.prepare(SOURCE + '\nAlice: At the time I intended to open the gate.')
        self.assertEqual(factors(direct)['STATED_INTENTION'], 'SUPPORTED_CLAIM')
        self.assertEqual(checked(direct)['premise_assessments'][0]['result'], 'CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS')

    def test_no_premise_no_normative_truth_and_invalid_scope_not_silently_selected(self):
        p = prepare_person_context(self.layer, QUERY, SOURCE)
        self.assertEqual(p.preparation_receipt['failure'], 'explicit_caller_normative_premise_required')
        self.assertFalse(p.context.responsibility)
        with self.assertRaises(ValueError):
            self.prepare(premise_scope='GLOBAL_MORAL_TRUTH')
        with self.assertRaises(ValueError):
            CognitionRequest('Explain belief', narrative=B, target_actor='Alice', belief_analysis=True,
                responsibility_premise_scope='FOCAL_EPISODE')
        with self.assertRaises(ValueError):
            prepare_person_context(self.layer, "Explain Alice's belief.", B, responsibility_premises=premise('KNOWLEDGE'))

    def test_source_order_before_action_outcome_does_not_import_future_basis(self):
        p = self.prepare(as_of_statement=1, premise_scope='FOCAL_EPISODE')
        self.assertTrue(contexts(p)['belief']['belief'])
        self.assertNotIn('responsibility', contexts(p)['responsibility'])
        self.assertNotIn(ACTION, p.messages[-1]['content'])
        self.assertNotIn(OUTCOME, p.messages[-1]['content'])

    def test_chinese_ordinary_composition_and_exact_one_final_call(self):
        calls = []
        result = answer_person_context(HCLCognitionLayer(lambda m: calls.append(m) or 'separate source claims'),
            '解释 Alice 的信念与条件责任依据。', SOURCE, responsibility_premises=premise('KNOWLEDGE'), debug=True)
        self.assertEqual(calls, [list(result.prepared.messages)])
        self.assertEqual(result.prepared.preparation_receipt['actual_final_messages'], calls[0])
        self.assertEqual(result.prepared.preparation_receipt['extraction_provider_calls'], 0)
        self.assertEqual(factors(result.prepared)['KNOWLEDGE'], 'UNKNOWN')
        self.assertIn('conditional', result.prepared.messages[0]['content'])
