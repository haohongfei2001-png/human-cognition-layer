"""Reproduced ordinary usability and full-source grounding failures, NI10–14."""
from dataclasses import replace
import json
import unittest
from hcl.v1 import (HCLCognitionLayer, PerspectiveMode, prepare_person_context,
    answer_person_context, AuthorizedSourceRecord, NarrativePremise, FactorRequirement,
    ResponsibilityFactor, ResponsibilityCase, FactorClaim, ClaimAuthority,
    check_responsibility, expand_cognition_context, expand_composed_sources)
from tests.test_v1_belief_responsibility import premise, ACTION, OUTCOME, SOURCE, checked, factors
from tests.test_v1_narrative_question import SOURCE as EVENTS, QUERY as EVENT_QUERY
from tests.test_v1_perspective_contrast import SOURCE as VIEWS, QUERY as VIEW_QUERY
from tests import test_v1_cg03 as _cg03

B = 'Alice: In team, I believe proposal is fair.'
D = 'Alice: In team, by fair I mean consent is true.'
F = 'Narrator: In team, proposal has consent true.'
P = 'Alice: As medic in team, I prefer safety over speed.'


class IntegratedQuestionTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda _: '')

    def responsibility(self, claim, factor='STATED_INTENTION'):
        return prepare_person_context(self.layer, "Explain Alice's conditional responsibility.",
            '\n'.join((ACTION, OUTCOME, claim)), responsibility_premises=premise(factor))

    def test_chinese_existing_responsibility_and_concept_forms_are_usable(self):
        p = prepare_person_context(self.layer, '解释 Alice 的条件责任依据。', SOURCE,
            responsibility_premises=premise('CONTROL'))
        self.assertEqual(factors(p)['CONTROL'], 'CONTRADICTED_CLAIM')
        p = prepare_person_context(self.layer, '解释 Alice 在 team 中对 proposal 的 fair 词义。', D + '\n' + F)
        self.assertEqual(p.context.concepts['checked']['readings'][0]['state'], 'CRITERIA_MET')
        self.assertFalse(p.plan.belief_preparation)

    def test_chinese_role_preferences_and_meaning_combination_keep_minimum_operations(self):
        source = '\n'.join((B, D, F, P))
        p = prepare_person_context(self.layer, '解释 Alice 在 team 中的 medic 角色偏好。', source)
        self.assertEqual(p.context.preferences['checked']['statements'][0]['state'], 'APPLICABLE_SOURCE_CLAIM')
        self.assertFalse(p.plan.belief_preparation)
        self.assertFalse(p.plan.concept_interpretation)
        p = prepare_person_context(self.layer, '解释 Alice 在 team 中对 proposal 的 fair 词义与 medic 角色偏好。', source)
        self.assertEqual(p.preparation_receipt['operations'], ['concepts', 'preferences'])

    def test_one_entrypoint_dispatches_authorized_source_revision_without_operation_flags(self):
        r = 'Alice: In team, I now believe proposal is unfair instead of proposal is fair.'
        source = (AuthorizedSourceRecord('old', B, 'CALLER_AUTHORIZED'),
                  AuthorizedSourceRecord('new', r, 'CALLER_AUTHORIZED', 'old'))
        p = prepare_person_context(self.layer, '按来源变化，解释 Alice 的信念。', source)
        state = json.loads(p.messages[-1]['content'])['source_revision_cognition']
        a, b = [expand_cognition_context(s['state']) for s in state['snapshots']]
        self.assertEqual(a['belief'][0]['status'], 'AFFIRMED')
        self.assertEqual({r['status'] for r in b['belief']}, {'SUPERSEDED', 'AFFIRMED'})
        bad = prepare_person_context(self.layer, "Across sources, Explain Alice's belief.",
            (source[0], AuthorizedSourceRecord('new', r, after_source_id='old')))
        self.assertFalse(bad.context.evidence)
        self.assertNotIn(B, bad.messages[-1]['content'])

    def test_one_entrypoint_dispatches_two_views_and_preserves_private_opt_in(self):
        p = prepare_person_context(self.layer, VIEW_QUERY, VIEWS)
        self.assertEqual(json.loads(p.messages[-1]['content'])['perspective_contrast']['relation'],
                         'DIFFERENT_EXPLICIT_SELF_REPORT_STANCES')
        kw = dict(perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Carol')
        refusal = prepare_person_context(self.layer, VIEW_QUERY, VIEWS, **kw)
        self.assertFalse(refusal.context.evidence)
        self.assertEqual(refusal.preparation_receipt['failure'], 'private_question_requires_explicit_source_access_preparation')
        p = prepare_person_context(self.layer, VIEW_QUERY, VIEWS, narrative_access=True, **kw)
        self.assertNotIn(B, p.messages[-1]['content'])
        state = json.loads(p.messages[-1]['content'])['perspective_contrast']
        self.assertTrue(all(not expand_cognition_context(r['cognition_context'])['evidence'] for r in state['participants']))

    def test_one_entrypoint_dispatches_named_event_scope_and_excludes_future(self):
        p = prepare_person_context(self.layer, EVENT_QUERY, EVENTS)
        self.assertEqual(len(json.loads(p.messages[-1]['content'])['narrative_cognition']['snapshots']), 2)
        q = "截至事件 briefing，解释 Alice 在 team 中的信念与 medic 角色偏好。"
        p = prepare_person_context(self.layer, q, EVENTS)
        state = json.loads(p.messages[-1]['content'])['narrative_cognition']
        self.assertEqual(state['event_selection']['selected_event_ids'], ['briefing'])
        self.assertNotIn('I now believe', p.messages[-1]['content'])

    def test_one_entrypoint_statement_scoped_contrast_keeps_earlier_view(self):
        p = prepare_person_context(self.layer, 'At statement 2, ' + VIEW_QUERY, VIEWS)
        state = json.loads(p.messages[-1]['content'])['perspective_contrast']
        self.assertEqual(state['source_order_scope']['through_statement'], 2)
        self.assertFalse(expand_cognition_context(state['participants'][1]['cognition_context'])['belief'])
        self.assertNotIn('Bob: In team, I do not believe', p.messages[-1]['content'])

    def test_mixed_nested_source_tasks_refuse_instead_of_decoder_crash_or_reader_fallback(self):
        source = (AuthorizedSourceRecord('old', B, 'CALLER_AUTHORIZED'),
                  AuthorizedSourceRecord('new', B, 'CALLER_AUTHORIZED', 'old'))
        for inner in (VIEW_QUERY, 'Across events, ' + EVENT_QUERY, 'At statement 1, Explain Alice\'s belief.'):
            p = prepare_person_context(self.layer, 'Across sources, ' + inner, source)
            self.assertFalse(p.context.evidence)
            self.assertNotIn(B, p.messages[-1]['content'])

    def test_subject_header_cannot_promote_another_person_for_each_factor(self):
        rows = [('KNOWLEDGE', 'Bob knew the latch was weak.'),
            ('FORESEEABILITY', 'Bob expected the animals to escape.'),
            ('CONTROL', 'Bob could have stopped the opening.'),
            ('STATED_INTENTION', 'Bob intended to open the gate.')]
        for factor, clause in rows:
            p = self.responsibility('Alice: At the time ' + clause, factor)
            self.assertEqual(factors(p)[factor], 'UNKNOWN')
            self.assertEqual(checked(p)['premise_assessments'][0]['result'], 'UNRESOLVED')

    def test_report_quote_and_hypothesis_do_not_become_direct_intention(self):
        for body in ('I said Bob intended to open the gate.',
            'if I intended to open the gate, it would happen.',
            'I would intend to open the gate.',
            '"I intended to open the gate."',
            'I intended to open the gate but never intended to let animals escape.'):
            p = self.responsibility('Alice: At the time ' + body)
            self.assertEqual(factors(p)['STATED_INTENTION'], 'UNKNOWN')

    def test_narrator_actor_object_is_not_asserted_factor_subject(self):
        for clause in ('Narrator: At the time Bob knew Alice was nearby.',
                       'Narrator: At the time Bob expected Alice to open the gate.',
                       'Narrator: At the time Bob could control Alice.'):
            p = self.responsibility(clause)
            self.assertTrue(all(s == 'UNKNOWN' for s in factors(p).values()))

    def test_positive_negative_self_and_explicit_indirect_reports_remain_distinct(self):
        for claim, expected in (
            ('Alice: At the time I intended to open the gate.', 'SUPPORTED_CLAIM'),
            ('Alice: At the time I did not intend to open the gate.', 'CONTRADICTED_CLAIM'),
            ('Bob: At the time Alice said she intended to open the gate.', 'ATTRIBUTED_ONLY')):
            p = self.responsibility(claim)
            self.assertEqual(factors(p)['STATED_INTENTION'], expected)
        p = self.responsibility('Alice: At the time I had no control over the opening.', 'CONTROL')
        self.assertEqual(factors(p)['CONTROL'], 'CONTRADICTED_CLAIM')

    def test_object_negation_does_not_silently_become_actor_lack_of_knowledge(self):
        p = self.responsibility('Alice: At the time I knew the latch was not weak.', 'KNOWLEDGE')
        self.assertEqual(factors(p)['KNOWLEDGE'], 'UNKNOWN')
        self.assertEqual(checked(p)['premise_assessments'][0]['result'], 'UNRESOLVED')

    def test_wrong_actor_or_hypothetical_action_outcome_cannot_anchor_episode(self):
        for text in ('Alice: Bob opened the gate.\n' + OUTCOME,
            'Alice: I said Bob opened the gate.\n' + OUTCOME,
            ACTION + '\nNarrator: If the animals escaped, it would matter.',
            ACTION + '\nNarrator: Bob said the animals escaped.'):
            p = prepare_person_context(self.layer, "Explain Alice's conditional responsibility.", text,
                responsibility_premises=premise('CAUSAL_CONTRIBUTION'))
            self.assertFalse(p.context.responsibility)
            self.assertEqual(p.preparation_receipt['failure'], 'action_or_outcome_ambiguous')

    def test_typed_selected_quote_cannot_hide_hypothesis_other_subject_or_forged_header(self):
        fixture = _cg03.FactorAndPremiseChecks(); fixture.setUp()
        for text, quote in (
            ('Alice: At the time if I intended to open the gate, it would happen.', 'I intended to open the gate'),
            ('Alice: At the time Bob intended to open the gate.', 'intended to open the gate'),
            ('Bob: I intended to open the gate.', 'I intended to open the gate'),
            ('Alice: At the time I did not intend to open the gate.', 'intend to open the gate')):
            source = replace(fixture.intention, raw_text=text)
            claim = replace(fixture.claims[-1], quote=quote)
            case = replace(fixture.case, claims=(claim,))
            events = tuple(source if e.event_id == source.event_id else e for e in fixture.events)
            with self.assertRaises(ValueError):
                check_responsibility(case, events, target_actor='Alice')

    def test_bounded_chinese_source_and_question_ground_real_explicit_knowledge(self):
        text = 'Alice: 我打开了门。\nNarrator: 动物逃走了。\nAlice: 当时我知道门闩有问题。'
        p = prepare_person_context(self.layer, '解释 Alice 的条件责任依据。', text,
            responsibility_premises=premise('KNOWLEDGE'))
        self.assertEqual(factors(p)['KNOWLEDGE'], 'SUPPORTED_CLAIM')
        self.assertEqual(factors(p)['STATED_INTENTION'], 'UNKNOWN')

    def test_unified_entrypoint_has_one_final_call_and_zero_extraction_for_all_integrated_paths(self):
        source = (AuthorizedSourceRecord('a', B, 'CALLER_AUTHORIZED'),
                  AuthorizedSourceRecord('b', B, 'CALLER_AUTHORIZED', 'a'))
        for q, data in ((VIEW_QUERY, VIEWS), (EVENT_QUERY, EVENTS), ("Across sources, Explain Alice's belief.", source)):
            calls = []
            def adapter(messages):
                calls.append(messages)
                return 'grounded integrated answer'
            receipt = answer_person_context(HCLCognitionLayer(adapter), q, data, debug=True)
            self.assertEqual(calls, [list(receipt.prepared.messages)])
            self.assertEqual(receipt.prepared.preparation_receipt['extraction_provider_calls'], 0)
            self.assertEqual(receipt.prepared.preparation_receipt['actual_final_messages'], list(receipt.prepared.messages))

    def test_unified_invalid_and_budget_refusals_do_not_leak_private_or_whole_sources(self):
        for q, source, key, field in ((VIEW_QUERY, VIEWS, 'perspective_contrast', 'participants'),
            (EVENT_QUERY, EVENTS, 'narrative_cognition', 'snapshots'),
            ("Across sources, Explain Alice's belief.", (AuthorizedSourceRecord('a', B, 'CALLER_AUTHORIZED'),
                AuthorizedSourceRecord('b', B, 'CALLER_AUTHORIZED', 'a')), 'source_revision_cognition', 'snapshots')):
            p = prepare_person_context(self.layer, q, source, max_context_chars=512)
            state = json.loads(p.messages[-1]['content'])[key]
            self.assertEqual(state[field], [])
            self.assertLessEqual(len(json.dumps(state, ensure_ascii=False, sort_keys=True)), 512)
        p = prepare_person_context(self.layer, 'At event absent, ' + EVENT_QUERY, EVENTS,
            perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET, observer_actor='Carol', narrative_access=True)
        self.assertFalse(p.context.evidence)
        self.assertNotIn(B, p.messages[-1]['content'])


    def test_explicit_focal_episode_cannot_use_other_action_object_or_outcome_factors(self):
        examples = [('FORESEEABILITY', 'I expected the kettle to boil.', 'I expected the animals to escape.'),
            ('CONTROL', 'I could have stopped the bus.', 'I could have stopped the opening.'),
            ('STATED_INTENTION', 'I intended to close the gate.', 'I intended to open the gate.'),
            ('KNOWLEDGE', 'I knew the bus was late.', 'I knew the gate had a weak latch.')]
        for factor, wrong, right in examples:
            for text, expected in ((wrong, 'UNKNOWN'), (right, 'SUPPORTED_CLAIM')):
                p = prepare_person_context(self.layer, "Explain Alice's conditional responsibility.",
                    '\n'.join((ACTION, OUTCOME, 'Alice: At the time ' + text)),
                    responsibility_premises=premise(factor), premise_scope='FOCAL_EPISODE')
                self.assertEqual(factors(p)[factor], expected)
                if expected == 'UNKNOWN':
                    self.assertEqual(checked(p)['premise_assessments'][0]['result'], 'UNRESOLVED')
