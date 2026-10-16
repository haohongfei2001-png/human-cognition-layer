"""Exhaustive policy oracles and real HCL consumption, revisions and recovery."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
import itertools
import unittest
from unittest.mock import patch

from hcl.kernel.types import HCLFailure, thaw
from hcl.operators.bounded_policy import joint_policy_outcomes
from hcl.operators.judgment import JudgmentWork, compare_framework
from hcl.runtime.answer import AnswerAssembler
from tests import test_unified_s4_judgment as legacy


from scripts.witness_unified_bounded_policies import two_step


class BoundedPolicyExecutionTests(unittest.TestCase):
    setUp = legacy.JudgmentExecutionTests.setUp
    tearDown = legacy.JudgmentExecutionTests.tearDown
    run_candidate = legacy.JudgmentExecutionTests.run_candidate
    inference = legacy.JudgmentExecutionTests.inference
    decision = legacy.JudgmentExecutionTests.decision

    def candidate(self, request=None):
        return two_step(legacy.JudgmentExecutionTests.candidate(self, request))

    def winning_policies(self):
        decision = self.decision()
        return [thaw(row['policy']) for row in decision['outcomes'] if row['action_id'] in decision['robust_across_frameworks']]

    def test_hcl_consumes_policy_and_checks_each_reachable_norm(self):
        result, port = self.run_candidate()
        self.assertEqual(result.status, 'PARTIAL', result.diagnostics)
        self.assertEqual(port.attempts, 1)
        self.assertEqual(self.winning_policies(), [dict(root_action_id='inspect', continuations={'r': 'protect'})])
        self.assertIn("'r': 'protect'", result.answer)
        decision = self.decision()
        prohibited = next(row for row in decision['outcomes'] if row['policy'] == dict(root_action_id='inspect', continuations={'r': 'ignore'}))
        eligibility = decision['frameworks'][0]['branches'][0]['result']['eligibility']
        self.assertEqual(next(r['status'] for r in eligibility if r['action_id'] == prohibited['action_id']), 'PROHIBITED')
        self.assertEqual(len(prohibited['step_checks']), 2)
        AnswerAssembler()._claim(self.inference())

    def test_fact_and_norm_revision_change_policy_without_hindsight(self):
        self.run_candidate()
        candidate = self.candidate()
        for key in ('received_by', 'understood_by', 'trusted_by'):
            candidate['models'][0]['mental']['events'][0][key] = []
        result, _ = self.run_candidate(candidate, replace(self.request, request_id='fact-change'))
        self.assertEqual(result.status, 'PARTIAL', result.diagnostics)
        self.assertTrue(self.winning_policies())
        self.assertTrue(all(p['root_action_id'] == 'inspect' and p['continuations']['r'] == 'ignore' for p in self.winning_policies()))
        candidate = self.candidate()
        candidate['models'][0]['argument']['priorities'][0].update(better='liberty', worse='care-duty')
        self.run_candidate(candidate, replace(self.request, request_id='norm-change'))
        self.assertTrue(self.winning_policies())
        self.assertTrue(all(p['root_action_id'] == 'inspect' and p['continuations']['r'] == 'ignore' for p in self.winning_policies()))

    def test_later_actual_infeasibility_cannot_be_compensated(self):
        candidate = self.candidate()
        candidate['models'][0]['mental']['plans'][0]['graph']['actions'][1]['feasible'] = []
        self.run_candidate(candidate)
        self.assertEqual(self.winning_policies(), [dict(root_action_id='safe', continuations={})])

    def test_unknown_guard_keeps_second_step_permission_unresolved(self):
        candidate = self.candidate()
        model = candidate['models'][0]
        model['mental']['variables'][1]['initial'] = None
        model['decisions'][0]['frameworks'][0]['norms'][0].update(guard_fact_ids=['promise'], argument_query_id=None)
        self.run_candidate(candidate)
        branch = self.decision()['frameworks'][0]['branches'][0]
        self.assertEqual(branch['states']['protect-known-risk'], 'UNRESOLVED')
        self.assertEqual(self.winning_policies(), [dict(root_action_id='inspect', continuations={'r': 'protect'})])
        self.assertIn('PERMISSION_UNRESOLVED', [r['status'] for r in branch['result']['eligibility']])

    def test_policy_tampering_and_unenumerated_frontier_are_not_certified(self):
        self.run_candidate()
        original = self.inference()
        for mutate in (
            lambda v: v['models'][0]['decisions'][0]['outcomes'][0]['policy'].update(continuations={'r': 'ignore'}),
            lambda v: v['models'][0]['decisions'][0]['outcomes'][0]['step_checks'][1].update(world_feasible=True),
        ):
            data = thaw(original.values); mutate(data)
            with self.assertRaises(HCLFailure):
                AnswerAssembler()._claim(replace(original, values=data))
        # A deterministic work cut during enumeration, independently of upstream costs.
        from hcl.operators import bounded_policy
        original_solver = bounded_policy.joint_policy_outcomes
        def interrupted(*args):
            return original_solver(*args[:-1], JudgmentWork(15))
        with patch.object(bounded_policy, 'joint_policy_outcomes', side_effect=interrupted):
            # Direct operator only: delivery replay must reject a patched computation.
            from hcl.operators.judgment_model import JudgmentModelOperator
            from hcl.kernel.types import Issue
            snapshot = self.store.snapshot('s', self.owner, self.request.source_handles)
            result = JudgmentModelOperator()._run(snapshot, Issue('cut', 'judgment.evaluate'), self.request.budget, thaw(original.values['program']))
        row = result.candidate_delta.new_inferences[0].values['models'][0]['decisions'][0]
        self.assertEqual(row['status'], 'UNCOMPUTED')
        self.assertFalse(row['robust_across_frameworks'])
        self.assertIn('JUDGMENT_WORK_FRONTIER', row['frontier'])

    def test_reopen_stream_and_recovery_keep_policy_bytes(self):
        # Reuse the existing real ledger seams with the explicit two-step candidate.
        legacy.JudgmentExecutionTests.test_run_stream_reopen_exact_replay_and_source_version_rejection(self)

    def test_returned_computed_committed_policy_recovery(self):
        legacy.JudgmentExecutionTests.test_returned_computed_committed_recovery_never_resends(self)

    def test_higher_schema_compositions_reject_policy_opt_in(self):
        for version in (2, 3, 4, 5):
            candidate = self.candidate()
            candidate['schema'] = 'hcl-judgment-candidates-' + str(version)
            if version == 5:
                candidate['weight_domains'] = []
            else:
                candidate['concepts'] = {}
                candidate['models'][0]['concept_bindings'] = []
                if version == 3:
                    candidate['repairs'] = [{}]
                if version == 4:
                    candidate['joint_changes'] = {}
            result, _ = self.run_candidate(candidate, replace(self.request, request_id='composition-' + str(version)))
            self.assertEqual(result.status, 'INVALID_REQUEST', result.diagnostics)
            self.assertFalse(result.claim_records)

    def test_only_explicit_two_step_contract_is_accepted(self):
        for index, value in enumerate((True, 1, 3, '2')):
            candidate = self.candidate()
            candidate['models'][0]['decisions'][0]['policy_horizon'] = value
            result, _ = self.run_candidate(candidate, replace(self.request, request_id='bad-'+str(index)))
            self.assertEqual(result.status, 'INVALID_REQUEST', result.diagnostics)


class PolicyMathTests(unittest.TestCase):
    def fixture(self, observed=True):
        states = ['a', 'b', 'x', 'y', 'good', 'bad']
        terminal = ['good', 'bad']
        actions = []
        for key, enabled, changes in [('look', ['a', 'b'], dict(a='x', b='y')),
                                      ('left', ['x', 'y'], dict(x='good', y='bad')),
                                      ('right', ['x', 'y'], dict(x='bad', y='good'))]:
            actions.append(dict(id=key, enabled=enabled, feasible=enabled[:], cost='0',
                transitions={s: changes.get(s, s) for s in states},
                observations={s: s if observed else 'same' for s in states}))
        graph = dict(states=states, terminal=terminal, actions=actions, horizon=2)
        dimensions = [dict(id='value', state_values={s: '10' if s == 'good' else '0' for s in states},
                           action_costs={a['id']: '0' for a in actions})]
        scenarios = [dict(id=s, distribution={s: '1'}) for s in ['a', 'b']]
        framework = dict(norms=[], weights={'value': '1'}, decision_rule='MAXIMIN')
        return graph, dimensions, scenarios, framework

    def solve(self, observed=True):
        graph, dims, scenarios, frame = self.fixture(observed)
        rows = joint_policy_outcomes(graph, dims, scenarios, ['a', 'b'], ['a', 'b'], JudgmentWork(100000))
        result = compare_framework(frame, rows, {}, dims, JudgmentWork(100000))
        return rows, result

    def test_observation_adapts_but_hidden_scenarios_cannot_choose_separate_successors(self):
        rows, result = self.solve(True)
        winners = [r for r in rows if r['action_id'] in result['recommended']]
        self.assertEqual(len(winners), 1)
        self.assertEqual(winners[0]['policy']['continuations'], {'x': 'left', 'y': 'right'})
        self.assertEqual(list(result['worst_scores'][a] for a in result['recommended']), ['10'])
        rows, result = self.solve(False)
        winners = [r for r in rows if r['action_id'] in result['recommended']]
        self.assertEqual(len(winners), 2)
        self.assertEqual({result['worst_scores'][r['action_id']] for r in winners}, {'0'})

    def test_dimensions_cannot_pick_different_continuations(self):
        graph, dims, scenarios, frame = self.fixture(False)
        opposite = deepcopy(dims[0]); opposite['id'] = 'opposite'
        opposite['state_values'] = {s: '10' if s == 'bad' else '0' for s in graph['states']}
        dims.append(opposite)
        rows = joint_policy_outcomes(graph, dims, scenarios, ['a', 'b'], ['a', 'b'], JudgmentWork(100000))
        for row in rows:
            if row['feasible']:
                for scenario in row['scenarios']:
                    self.assertEqual(sum(map(Fraction, scenario['vector'].values())), 10)

    def test_independent_bruteforce_oracle_checks_every_joint_vector(self):
        graph, dims, scenarios, _ = self.fixture(True)
        dims[0]['action_costs'].update(look='1/3', left='2/3', right='1/2')
        scenarios = [dict(id='mixed', distribution={'a': '1/4', 'b': '3/4'})]
        rows = joint_policy_outcomes(graph, dims, scenarios, ['a', 'b'], ['a', 'b'], JudgmentWork(100000))
        feasible = [r for r in rows if r['feasible']]
        self.assertEqual(len(feasible), 4)
        for left, right in itertools.product(('left', 'right'), repeat=2):
            row = next(r for r in feasible if r['policy']['continuations'] == {'x': left, 'y': right})
            expected = (Fraction(1, 4) * (10 * (left == 'left') - Fraction(dims[0]['action_costs'][left]))
                        + Fraction(3, 4) * (10 * (right == 'right') - Fraction(dims[0]['action_costs'][right])) - Fraction(1, 3))
            self.assertEqual(Fraction(row['scenarios'][0]['vector']['value']), expected)

    def test_budget_and_policy_count_limit_never_return_partial_enumeration(self):
        graph, dims, scenarios, _ = self.fixture()
        with self.assertRaises(OverflowError):
            joint_policy_outcomes(graph, dims, scenarios, ['a', 'b'], ['a', 'b'], JudgmentWork(10))
        with patch('hcl.operators.bounded_policy.MAX_POLICIES', 2), self.assertRaises(OverflowError):
            joint_policy_outcomes(graph, dims, scenarios, ['a', 'b'], ['a', 'b'], JudgmentWork(100000))

    def test_maximin_keeps_dominated_equal_worst_policy_ties(self):
        graph, dims, scenarios, frame = self.fixture(False)
        # left=(10,0), right=(0,0): both have worst zero, despite dominance.
        graph['actions'][2]['transitions']['y'] = 'bad'
        rows = joint_policy_outcomes(graph, dims, scenarios, ['a', 'b'], ['a', 'b'], JudgmentWork(100000))
        result = compare_framework(frame, rows, {}, dims, JudgmentWork(100000))
        self.assertEqual(len(result['recommended']), 2)
        self.assertEqual(len(result['pareto']), 1)

    def test_terminal_branches_stop_without_second_cost_or_norm(self):
        graph, dims, scenarios, frame = self.fixture(True)
        graph['actions'][0]['transitions']['b'] = 'good'
        dims[0]['action_costs'].update(look='1', left='2', right='3')
        rows = joint_policy_outcomes(graph, dims, scenarios, ['a', 'b'], ['a', 'b'], JudgmentWork(100000))
        row = next(r for r in rows if r['policy'] == dict(root_action_id='look', continuations={'x': 'left'}))
        self.assertEqual(row['scenarios'][0]['vector']['value'], '7')
        self.assertEqual(row['scenarios'][1]['vector']['value'], '9')
        self.assertEqual(row['scenarios'][1]['paths']['b']['actions'], ['look'])
        self.assertEqual(row['reachable_actions'], ['left', 'look'])

    def test_zero_probability_world_still_constrains_actual_feasibility(self):
        graph, dims, _, _ = self.fixture(False)
        graph['actions'][1]['feasible'] = ['x']
        rows = joint_policy_outcomes(graph, dims, [dict(id='one', distribution={'a': '1', 'b': '0'})],
                                    ['a', 'b'], ['a', 'b'], JudgmentWork(100000))
        left = next(r for r in rows if r['policy'] == dict(root_action_id='look', continuations={'same': 'left'}))
        self.assertFalse(left['world_feasible'])


if __name__ == '__main__': unittest.main()
