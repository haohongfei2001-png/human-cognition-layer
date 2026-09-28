"""A04-A05 real retained operations consume shared material and dependent updates."""
import json
import unittest

from hcl.cognition import CognitionWorkspace, ClaimKind, Scope, prepare_retained, answer_retained
from hcl.v1 import NarrativePremise, FactorRequirement, ResponsibilityFactor

D = 'Mira said, "In team, by fair I mean consent is true."'
F = 'Narrator: In team, proposal has consent false.'
B = 'Mira added, "In team, I believe proposal is fair."'
QUERY = "Compare Mira's belief and meaning of fair for proposal in team."


def comparison(result):
    return json.loads(result.messages[-1]['content'])['composed_cognition']['belief_concept_comparison']['rows'][0]


class Backend:
    def __init__(self, rows):
        self.rows, self.calls = rows, []

    def complete_json(self, messages, **kwargs):
        self.calls.append(messages)
        return json.dumps(dict(candidates=self.rows))


class SharedRetainedTests(unittest.TestCase):
    def setUp(self):
        self.w = CognitionWorkspace()
        self.w.put_source('meeting', '\n'.join((D, F, B)))

    def test_actual_belief_and_concept_checks_share_original_translation(self):
        result = prepare_retained(self.w, QUERY, source_ids=('meeting',))
        self.assertEqual(comparison(result)['relation'], 'DIFFERS_FROM_LOCAL_SOURCE_CRITERIA')
        self.assertEqual(comparison(result)['belief_status'], 'AFFIRMED')
        self.assertEqual(comparison(result)['concept_state'], 'CRITERIA_NOT_MET')
        self.assertEqual(len(result.operation_ids), 3)
        self.assertEqual(self.w.core.dependencies[result.operation_ids[-1]], {tuple(sorted(result.operation_ids[:2]))})
        wire = json.loads(result.messages[-1]['content'])
        bindings = wire['shared_semantic_binding']['translations']
        self.assertEqual(bindings[0]['original_quote'], D)
        self.assertEqual(bindings[0]['derived_line'], 'Mira: In team, by fair I mean consent is true.')
        self.assertIn('not verbatim source', result.messages[0]['content'])
        self.assertEqual(result.receipt['actual_final_messages'], result.messages)
        self.assertTrue(all(self.w.core.claims[k].kind == ClaimKind.CONDITIONAL_TOOL_RESULT for k in result.operation_ids))

    def test_preference_adapter_runs_condition_checker_not_a_new_prompt(self):
        self.w.put_source('p', '\n'.join((
            'Mira explained, "As medic in team, I prefer safety over speed if rain is true."',
            'Narrator: In team, rain is true.')))
        r = prepare_retained(self.w, "Explain Mira's preferences as medic in team.", source_ids=('p',))
        state = self.w.core.claims[r.operation_ids[0]].content['retained_state']
        self.assertEqual(state['preferences']['checked']['statements'][0]['state'], 'APPLICABLE_SOURCE_CLAIM')
        self.assertFalse(state['belief'])

    def test_responsibility_adapter_keeps_knowledge_control_intention_and_rule_distinct(self):
        text = '\n'.join((
            'Mira said, "I opened the gate."',
            'Narrator: The animals escaped.',
            'Narrator: Mira opening the gate caused the animals to escape.',
            'Mira explained, "At the time I knew the latch was weak."',
            'Mira stated, "At the time I could not control the opening."'))
        self.w.put_source('incident', text)
        rule = NarrativePremise('control-rule', 'For this analysis control is required.',
            (FactorRequirement(ResponsibilityFactor.CONTROL, True),))
        r = prepare_retained(self.w, "Explain Mira's conditional responsibility.",
            source_ids=('incident',), responsibility_premises=(rule,))
        checked = self.w.core.claims[r.operation_ids[0]].content['retained_state']['responsibility']['checked']
        factors = {x['factor']: x['state'] for x in checked['factors']}
        self.assertEqual(factors['CONTROL'], 'CONTRADICTED_CLAIM')
        self.assertEqual(factors['KNOWLEDGE'], 'SUPPORTED_CLAIM')
        self.assertEqual(factors['STATED_INTENTION'], 'UNKNOWN')
        self.assertEqual(checked['premise_assessments'][0]['result'], 'CONDITIONALLY_NOT_SUPPORTED')
        self.assertIn('control-rule', r.scope.assumptions)

    def test_source_update_propagates_through_real_checker_and_comparison_only(self):
        before = prepare_retained(self.w, QUERY, source_ids=('meeting',))
        self.w.put_source('home', 'Noor said, "In home, I believe dinner is good."')
        noor = prepare_retained(self.w, 'What does Noor believe?', source_ids=('home',))
        invalidated = self.w.put_source('meeting', '\n'.join((D, F.replace('false', 'true'), B)))
        self.assertTrue(set(before.operation_ids) <= invalidated)
        self.assertFalse(set(noor.operation_ids) & invalidated)
        after = prepare_retained(self.w, QUERY, source_ids=('meeting',))
        self.assertEqual(comparison(after)['relation'], 'CONSISTENT_WITH_LOCAL_SOURCE_CRITERIA')
        self.assertEqual(comparison(before)['belief_status'], comparison(after)['belief_status'])
        self.assertEqual(comparison(before)['concept_state'], 'CRITERIA_NOT_MET')
        self.assertEqual(comparison(after)['concept_state'], 'CRITERIA_MET')
        self.assertTrue(set(noor.operation_ids) <= self.w.core.grounded())

    def test_upstream_semantic_challenge_reaches_projection_and_both_dependents(self):
        r = prepare_retained(self.w, QUERY, source_ids=('meeting',))
        original = self.w.core.projections[r.translation_ids[0]]
        scope = self.w.core.claims[original].scope
        challenger = self.w.core.claim(scope, ClaimKind.SYSTEM_INTERPRETATION, {'challenge': 'interpretation disputed'})
        span = self.w.core.claims[original].content['source_span_id']
        self.w.core.support(challenger, span)
        self.w.core.challenge(original, challenger)
        statuses = self.w.core.support_statuses()
        self.assertTrue(all(statuses[k] == 'DEPENDENCY_CONTESTED' for k in r.operation_ids))
        with self.assertRaises(ValueError):
            r.current_messages(self.w)
        self.w.core.withdraw(challenger)
        self.assertTrue(all(self.w.core.support_statuses()[k] == 'SUPPORT_AVAILABLE' for k in r.operation_ids))

    def test_general_backend_translation_is_conditional_and_original_prose_survives(self):
        text = 'At the team meeting, Mira described a fair proposal as one with consent.'
        self.w.put_source('open', text)
        row = dict(source_id='open', quote=text, kind='event',
            content=dict(canonical_statement='Mira: In team, by fair I mean consent is true.'))
        backend = Backend([row])
        r = prepare_retained(self.w, "Interpret Mira's meaning of fair for proposal in team.",
            source_ids=('open',), backend=backend)
        self.assertEqual(len(backend.calls), 1)
        self.assertTrue(r.scope.assumptions)
        wire = json.loads(r.messages[-1]['content'])['shared_semantic_binding']
        self.assertEqual(wire['semantic_status'], 'CONDITIONAL_ON_UNVERIFIED_TRANSLATION')
        self.assertEqual(wire['original_sources'][0]['text'], text)
        state = self.w.core.claims[r.operation_ids[0]].content['retained_state']
        self.assertEqual(state['concepts']['checked']['readings'][0]['state'], 'CRITERIA_UNRESOLVED')

    def test_backend_cannot_rename_actor_or_create_unconditional_evidence(self):
        text = 'Mira spoke about fairness.'
        self.w.put_source('open', text)
        backend = Backend([dict(source_id='open', quote=text, kind='event',
            content=dict(canonical_statement='Noor: In team, by fair I mean consent is true.'))])
        with self.assertRaises(ValueError):
            prepare_retained(self.w, QUERY, source_ids=('open',), backend=backend)

    def test_unparsed_qualifier_conditional_and_ambiguous_speaker_fail_closed(self):
        for text in ('If ' + D, 'She said, "In team, I believe proposal is fair."',
                     D + ' This was an invented quotation.'):
            self.w.put_source('unsafe', text)
            with self.assertRaises(ValueError):
                prepare_retained(self.w, QUERY, source_ids=('unsafe',))

    def test_private_source_filtered_before_extraction_or_operation(self):
        backend = Backend([])
        with self.assertRaises(ValueError):
            prepare_retained(self.w, QUERY, source_ids=('meeting',), observer='Noor', backend=backend)
        self.assertFalse(backend.calls)

    def test_third_party_report_remains_indirect_and_unsupported_query_spends_no_call(self):
        self.w.put_source('report', 'Noor said, "In team, Mira believes proposal is fair."')
        r = prepare_retained(self.w, 'What does Mira believe?', source_ids=('report',))
        state = self.w.core.claims[r.operation_ids[0]].content['retained_state']
        self.assertEqual(state['belief'][0]['status'], 'SYSTEM_INSUFFICIENT')
        backend = Backend([])
        with self.assertRaises(ValueError):
            prepare_retained(self.w, 'Infer her secret motives.', source_ids=('meeting',), backend=backend)
        self.assertFalse(backend.calls)

    def test_cross_source_identity_and_unprojected_past_query_rejected(self):
        self.w.put_source('other', B)
        for query, sources in ((QUERY, ('meeting', 'other')), ('At statement 1, ' + QUERY, ('meeting',))):
            with self.assertRaises(ValueError):
                prepare_retained(self.w, query, source_ids=sources)

    def test_exact_one_answer_call_uses_actual_current_inputs_and_stale_receipt_rejects(self):
        calls = []
        answer = answer_retained(self.w, QUERY, lambda m: calls.append(m) or 'source-bounded answer',
            source_ids=('meeting',))
        self.assertEqual(calls, [answer['prepared'].messages])
        self.assertEqual(answer['answer_adapter_calls'], 1)
        self.w.put_source('meeting', '\n'.join((D, F.replace('false', 'true'), B)))
        with self.assertRaises(ValueError):
            answer['prepared'].current_messages(self.w)

    def test_context_budget_does_not_drop_original_source_or_assumptions(self):
        with self.assertRaises(ValueError):
            prepare_retained(self.w, QUERY, source_ids=('meeting',), max_chars=512)

    def test_projection_cannot_widen_observer_or_remove_assumptions(self):
        result = self.w.prepare_semantic(QUERY, source_ids=('meeting',))
        key = result.candidate_ids[0]
        with self.assertRaises(ValueError):
            self.w.core.project_claim(key, Scope(observer='Noor', source_ids=('meeting',)),
                ClaimKind.SYSTEM_INTERPRETATION, {'unsafe': True})
        with self.assertRaises(ValueError):
            self.w.core.project_claim(key, result.scope, ClaimKind.SOURCE_REPORT, {'unsafe': True})
