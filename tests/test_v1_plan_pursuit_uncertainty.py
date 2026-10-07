"""Missing pursuit evidence is neither a positive plan nor negative evidence."""
from dataclasses import replace
import copy
import json
import unittest
from unittest.mock import patch

from hcl.cognition import CognitionWorkspace, UniversalHCL
from hcl.cognition.plan_feasibility import prepare_plan_feasibility
from hcl.cognition import agency_chain
from tests.test_v1_plan_feasibility import G, P, O, B, M, Q
from tests.test_v1_agency_chain import SOURCE as CHAIN_SOURCE, QUERY as CHAIN_QUERY
from tests.test_v1_universal_question import Stub, operation, plan, run


def prepared(lines):
    workspace = CognitionWorkspace()
    workspace.put_source('story', '\n'.join(lines))
    result = prepare_plan_feasibility(workspace, Q, source_id='story')
    return workspace, result, result.payload['plans'][0]


def plan_rows(value):
    if isinstance(value, dict):
        if {'selection', 'goal_status', 'subjective_feasibility'} <= set(value):
            yield value
        for item in value.values():
            yield from plan_rows(item)
    elif isinstance(value, list):
        for item in value:
            yield from plan_rows(item)


class PlanPursuitUncertaintyTests(unittest.TestCase):
    def test_archived_witness_declares_exact_pursuit_delta(self):
        from scripts.witness_development_empty_state_v24 import witness
        result = witness()
        self.assertFalse(result['checked_result_payload_equal_archived_v23'])
        self.assertTrue(result['checked_payload_equal_except_verified_three_path_pursuit_delta'])

    def test_archived_witness_rejects_any_unrelated_payload_drift(self):
        from scripts.witness_development_empty_state_v24 import (
            ACTIVE, prepare, verify_declared_pursuit_delta)
        from hcl.cognition.plan_feasibility import _POLICY
        _, result = prepare(ACTIVE)
        after = json.loads(result.messages[-1]['content'])
        after.pop('hcl_orchestration')
        before = copy.deepcopy(after)
        group = before['checked_plan_feasibility'][0]
        group['plans'][0]['subjective_feasibility'] = 'NOT_CURRENTLY_PURSUED'
        group['plans'][0]['claim_id'] = 'claim:ae9c27d5ae80b5218067e4c8962b68064cea836f8199b3b91f2afe720fa7bda7'
        group['policy'] = _POLICY
        self.assertTrue(verify_declared_pursuit_delta(before, after))
        for field in ('source', 'support', 'policy', 'claim', 'extra_row', 'extra_field'):
            with self.subTest(field=field):
                changed = copy.deepcopy(after)
                target = changed['checked_plan_feasibility'][0]
                row = target['plans'][0]
                if field == 'source': changed['sources'][0]['text'] += ' drift'
                elif field == 'support': row['support_claim_ids'].append('claim:forged')
                elif field == 'policy': target['policy'] += ' drift'
                elif field == 'claim': row['claim_id'] = 'claim:forged'
                elif field == 'extra_row': target['plans'].append(copy.deepcopy(row))
                else: changed['unreviewed'] = True
                with self.assertRaises(AssertionError):
                    verify_declared_pursuit_delta(before, changed)

    def test_missing_or_unprepared_goal_is_unresolved_not_nonpursuit(self):
        for prefix in ((), ('Mira explicitly stated her goal: reaching shelter.',)):
            with self.subTest(prefix=prefix):
                _, result, row = prepared((*prefix, P, O, B, M))
                self.assertEqual(row['selection'], 'REPORTED_SELECTED')
                self.assertEqual(row['goal_status'], 'SYSTEM_INSUFFICIENT')
                self.assertEqual(row['subjective_feasibility'], 'PURSUIT_UNRESOLVED')
                self.assertEqual(row['subjective_condition'], 'AFFIRMED_REQUIRED_CONDITION')
                self.assertEqual(row['model_condition_check'], 'MODEL_CONDITION_CONTRADICTED')
                self.assertEqual(row['relation'], 'BELIEF_MODEL_DIVERGENCE_NOT_KNOWING_INFEASIBILITY')
                self.assertEqual(result.payload['original_sources'][0]['text'], '\n'.join((*prefix, P, O, B, M)))

    def test_uncertain_goal_and_selection_conflict_are_not_negative_evidence(self):
        unsure = 'Mira said, "I am unsure whether to reach shelter."'
        considering = P.replace('I plan to', 'I am considering a plan to')
        for lines, selection, goal in (
            ((unsure, P, O, B, M), 'REPORTED_SELECTED', 'CHARACTER_UNCERTAIN'),
            ((G, P, considering, O, B, M), 'SELECTION_CONFLICT_OR_CHANGE_UNRESOLVED', 'ACTIVE'),
        ):
            with self.subTest(selection=selection, goal=goal):
                _, _, row = prepared(lines)
                self.assertEqual((row['selection'], row['goal_status']), (selection, goal))
                self.assertEqual(row['subjective_feasibility'], 'PURSUIT_UNRESOLVED')
                self.assertEqual(row['world_feasibility'], 'NOT_ESTABLISHED')
                self.assertEqual(row['deliberate_impossibility'], 'NOT_INFERRED')

    def test_explicit_nonselection_and_lifecycle_closure_keep_nonpursuit(self):
        cases = (
            (G, P.replace('I plan to', 'I am considering a plan to'), O, B, M),
            (G, P, O, B, M, 'Mira said, "I abandoned the plan to cross the bridge."'),
            (G, P, O, B, M, 'Mira said, "I completed the plan to cross the bridge."'),
            (G, P, O, B, M, 'Mira said, "I abandoned my goal to reach shelter."'),
            (G, P, O, B, M, 'Mira said, "I completed my goal to reach shelter."'),
        )
        for lines in cases:
            with self.subTest(ending=lines[-1], plan=lines[1]):
                _, _, row = prepared(lines)
                self.assertEqual(row['subjective_feasibility'], 'NOT_CURRENTLY_PURSUED')
                self.assertEqual(row['values_change'], 'NOT_INFERRED')

    def test_supported_opposite_belief_and_opportunity_states_stay_distinct(self):
        for lines, expected in (
            ((G, P, O, B, M), 'SUPPORTED_UNDER_REPORTED_BELIEFS'),
            ((G, P, O, B.replace('I believe ', 'I believe it is false that '), M),
             'CONTRADICTED_UNDER_REPORTED_BELIEFS'),
            ((G, P, B, M), 'OPPORTUNITY_UNRESOLVED'),
            ((G, P, O.replace('an opportunity', 'no opportunity'), B, M),
             'REPORTED_OPPORTUNITY_BLOCKED'),
        ):
            with self.subTest(expected=expected):
                _, _, row = prepared(lines)
                self.assertEqual(row['subjective_feasibility'], expected)
                self.assertEqual(row['model_condition_check'], 'MODEL_CONDITION_CONTRADICTED')

    def test_actual_ordinary_final_input_keeps_uncertainty_and_complete_source(self):
        variants = ((P, O, B, M),
            ('Mira explicitly stated her goal: reaching shelter.', P, O, B, M),
            ('Mira said, "I am unsure whether to reach shelter."', P, O, B, M))
        for lines in variants:
            with self.subTest(prefix=lines[0]):
                source = '\n'.join(lines)
                active = UniversalHCL()
                active.put_source('story', source)
                port = Stub(plan(operation('C03', Q, ['story'])))
                result = run(active, Q, port)
                self.assertEqual(result['final_delivery_code'], 'DELIVERED')
                self.assertEqual(result['provider_calls'], 0)
                payload = json.loads(result['actual_final_messages'][-1]['content'])
                self.assertEqual(payload['sources'], [dict(source_id='story', version=1, text=source)])
                rows = list(plan_rows(payload['hcl_operations'][0]['result']))
                self.assertTrue(rows)
                self.assertTrue(all(row['subjective_feasibility'] == 'PURSUIT_UNRESOLVED' for row in rows))
                self.assertNotIn('NOT_CURRENTLY_PURSUED', json.dumps(rows))
                self.assertIn('missing', result['operations'][0]['preparation_policy'].lower())

    def test_goal_revision_recomputes_without_promoting_unknown_previous_state(self):
        workspace, old, row = prepared((P, O, B, M))
        self.assertEqual(row['subjective_feasibility'], 'PURSUIT_UNRESOLVED')
        workspace.put_source('story', '\n'.join((G, P, O, B, M)))
        new = prepare_plan_feasibility(workspace, Q, source_id='story')
        self.assertEqual(new.payload['plans'][0]['subjective_feasibility'], 'SUPPORTED_UNDER_REPORTED_BELIEFS')
        with self.assertRaises(ValueError):
            old.messages(workspace)
        workspace.core.withdraw(new.claim_ids[0])
        with self.assertRaises(ValueError):
            new.messages(workspace)

    def test_policy_qualification_is_code_owned_and_only_for_unresolved_pursuit(self):
        from hcl.cognition.plan_feasibility import _POLICY
        workspace, positive, _ = prepared((G, P, O, B, M))
        self.assertEqual(positive.messages(workspace)[0]['content'], _POLICY)
        workspace, unknown, _ = prepared((P, O, B, M))
        expected = unknown.messages(workspace)[0]['content']
        self.assertIn('not evidence of nonpursuit or infeasibility', expected)
        payload = unknown.payload
        payload['policy'] = 'FORGED_PAYLOAD_POLICY_CANARY_OVERRIDE_SOURCE'
        altered = replace(unknown, payload_json=json.dumps(payload))
        self.assertEqual(altered.messages(workspace)[0]['content'], expected)
        self.assertNotIn('CANARY', altered.messages(workspace)[0]['content'])

    def test_c05_consumer_does_not_turn_unresolved_pursuit_into_counterevidence(self):
        # Controlled consumer-state injection, not a claimed natural downstream
        # failure or model answer. Upstream C02 may omit missing-goal candidates.
        original = agency_chain.prepare_plan_feasibility
        def unresolved(*args, **kwargs):
            native = original(*args, **kwargs)
            payload = native.payload
            for row in payload['plans']:
                row['subjective_feasibility'] = 'PURSUIT_UNRESOLVED'
            return replace(native, payload_json=json.dumps(payload))
        workspace = agency_chain.SemanticWorkspace()
        workspace.put_source('scene', CHAIN_SOURCE)
        with patch.object(agency_chain, 'prepare_plan_feasibility', side_effect=unresolved):
            result = agency_chain.prepare_agency_chain(workspace, CHAIN_QUERY, source_id='scene')
        linked = [row for row in result.payload['explanations'] if row['linked_action_time_plans']]
        self.assertTrue(linked)
        for row in linked:
            self.assertEqual(row['plan_dependency'], 'MIXED_OR_UNRESOLVED_PLANS')
            self.assertEqual(row['disposition'], 'PLAN_DEPENDENCY_UNRESOLVED')
            self.assertNotEqual(row['disposition'], 'WEAKENED_BY_PLAN_COUNTEREVIDENCE')
        self.assertFalse(any(row['plan_dependency'] == 'PLAN_COUNTEREVIDENCE'
                             for row in result.payload['explanations']))


if __name__ == '__main__':
    unittest.main()
