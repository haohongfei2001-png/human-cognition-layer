"""Actual v5 policy composition, source-bound delivery and independent oracles."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from itertools import combinations, product
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure, thaw
from hcl.kernel.execution import ExecutionIssue, Issue
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.judgment import JudgmentWork
from hcl.operators.weight_regions import solve_regions
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.recovery import RecoveryManager
from scripts.witness_unified_policy_weight_regions import propose
from tests import test_unified_s4_judgment as base_runtime
from tests import test_unified_weight_regions as weight_runtime
from tests.test_unified_weight_region_math import contains


def independent_policy_vectors(candidate):
    """Finite oracle: enumerate root and observation maps, then direct trajectories.

    The oracle fixture has actual/subjective risk+clear, with no active norms.
    No production outcome, feasibility, policy-ID or point solver is reused.
    """
    model = candidate['models'][0]; decision = model['decisions'][0]
    graph = model['mental']['plans'][0]['graph']
    terminal = set(graph['terminal']); states = ['risk', 'clear']
    scenarios = decision['scenarios'] or [dict(id='actual-state:'+s, distribution={s: '1'}) for s in states]
    vectors = {}
    for root in graph['actions']:
        if not set(states) <= set(root['feasible']):
            continue
        groups = {}
        for s in states:
            target = root['transitions'][s]
            if target not in terminal:
                groups.setdefault(root['observations'][target], set()).add(target)
        symbols = sorted(groups)
        for assignment in product(graph['actions'], repeat=len(symbols)):
            follow = dict(zip(symbols, assignment))
            if any(not groups[s] <= set(follow[s]['feasible']) for s in symbols):
                continue
            key = (root['id'], tuple((s, follow[s]['id']) for s in symbols))
            by_scenario = {}
            for scenario in scenarios:
                values = {d['id']: F(0) for d in decision['dimensions']}
                for state, mass in scenario['distribution'].items():
                    target = root['transitions'][state]; path = [root['id']]
                    if target not in terminal:
                        next_action = follow[root['observations'][target]]
                        target = next_action['transitions'][target]; path.append(next_action['id'])
                    for d in decision['dimensions']:
                        values[d['id']] += F(mass) * (F(d['state_values'][target])-sum(F(d['action_costs'][a]) for a in path))
                by_scenario[scenario['id']] = values
            vectors[key] = by_scenario
    return vectors


def scalar_oracle(vectors, x, rule):
    scores = {a: {s: x*v['care']+(1-x)*v['convenience'] for s, v in rows.items()} for a, rows in vectors.items()}
    if rule == 'MINIMAX_REGRET':
        best = {s: max(rows[s] for rows in scores.values()) for s in next(iter(scores.values()))}
        values = {a: max(best[s]-v for s, v in rows.items()) for a, rows in scores.items()}
        optimum = min(values.values())
    else:
        values = {a: min(rows.values()) for a, rows in scores.items()}
        optimum = max(values.values())
    return {a for a, value in values.items() if value == optimum}


def exact_crossings(vectors, rule):
    """All affine crossings and intervening rational points, not a sampling grid."""
    forms = [(v['care']-v['convenience'], v['convenience']) for rows in vectors.values() for v in rows.values()]
    if rule == 'MINIMAX_REGRET':
        for rows in vectors.values():
            for other in vectors.values():
                for s, v in rows.items():
                    b = other[s]['convenience']-v['convenience']
                    forms.append((other[s]['care']-v['care']-b, b))
    points = {F(0), F(1)}
    for (a, b), (c, d) in combinations(forms, 2):
        if a != c and 0 <= (d-b)/(a-c) <= 1:
            points.add((d-b)/(a-c))
    ordered = sorted(points)
    return ordered + [(a+b)/2 for a, b in zip(ordered, ordered[1:])]


class PolicyWeightRegionTests(unittest.TestCase):
    def setUp(self):
        self.f = base_runtime.JudgmentExecutionTests(); self.f.setUp(); self.addCleanup(self.f.tearDown)
        self.f.request = replace(self.f.request, budget=replace(self.f.request.budget, max_local_evaluations=300000))

    def candidate(self, rule='EXPECTED', **kwargs):
        return propose(self.f.store.snapshot('s', self.f.owner, self.f.request.source_handles), self.f.request.question, rule, **kwargs)

    run_candidate = weight_runtime.WeightRegionRuntimeTests.run_candidate
    pure = weight_runtime.WeightRegionRuntimeTests.pure

    def test_real_expected_policy_regions_and_readable_verified_answer(self):
        value, result, port, proof = self.run_candidate(stream=True)
        analysis = value['analyses'][0]
        self.assertTrue(value['complete']); self.assertEqual(port.attempts, 1)
        partitions = analysis['branches'][0]['regions']['recommendation_partition']
        self.assertEqual([(p['lower'],p['upper']) for p in partitions], [('0','3/10'),('3/10','3/10'),('3/10','1')])
        self.assertEqual(len(partitions[1]['recommended']), 2)
        self.assertIn('root inspect; after observation', result.answer)
        self.assertIn('dominance comparisons', result.answer)
        self.assertNotIn('dominance exclusions', result.answer)
        self.assertIn("'r': 'protect'", result.answer)
        self.assertTrue(any(f.field == 'analyses' and getattr(f, 'path', ()) == ('0', 'policy_catalog') for c in result.claim_records for f in c.used_result_fields))
        AnswerAssembler()._claim(proof)

    def test_continuous_joint_policy_oracle_for_all_rules_and_observations(self):
        for rule in ('EXPECTED','MAXIMIN','MINIMAX_REGRET'):
            for observed in (False, True):
                candidate = self.candidate(rule, uncertain=True, observable=observed)
                graph = candidate['models'][0]['mental']['plans'][0]['graph']
                for d in candidate['models'][0]['decisions'][0]['dimensions']:
                    if rule != 'MINIMAX_REGRET':
                        d['action_costs'].update(inspect='1/3', protect='1/5', ignore='1/7')
                oracle = independent_policy_vectors(candidate)
                value = thaw(self.pure(candidate, limit=3000000).values)
                self.assertTrue(value['complete'], (rule, observed, value['issues']))
                analysis = value['analyses'][0]
                keys = {a: (p['root_action_id'], tuple(sorted(p['continuations'].items()))) for a,p in analysis['policy_catalog'].items()}
                outcomes = value['actual_judgment']['models'][0]['decisions'][0]['outcomes']
                self.assertEqual({keys[row['action_id']] for row in outcomes if row['feasible']}, set(oracle))
                for row in outcomes:
                    if row['feasible']:
                        self.assertEqual({s['scenario_id']:{d:F(v) for d,v in s['vector'].items()} for s in row['scenarios']}, oracle[keys[row['action_id']]])
                regions = analysis['branches'][0]['regions']
                for x in exact_crossings(oracle, rule):
                    cells = [c for c in regions['cells'] if contains(c['interval'], x)]
                    self.assertEqual(len(cells), 1)
                    self.assertEqual({keys[a] for a in cells[0]['recommended']}, scalar_oracle(oracle,x,rule), (rule,observed,x))

    def test_policy_ties_preserved_without_changing_legacy_single_step_semantics(self):
        vectors = {'policy:A': {'s': {'x':'0'},'t':{'x':'1'}}, 'policy:B': {'s':{'x':'0'},'t':{'x':'0'}}}
        old = solve_regions({'constraints':[]}, vectors, ['x'], 'MAXIMIN', JudgmentWork(10000))
        new = solve_regions({'constraints':[]}, vectors, ['x'], 'MAXIMIN', JudgmentWork(10000), preserve_scalar_ties=True)
        self.assertEqual(old['robust_recommended'], ['policy:A'])
        self.assertNotIn('scalar_tie_semantics', old)
        self.assertEqual(new['robust_recommended'], ['policy:A','policy:B'])
        self.assertIn('policy:B', new['cells'][0]['dominated'])

    def test_weight_domain_revision_preserves_actual_policy_facts_and_paths(self):
        before = thaw(self.pure(limit=300000).values)
        candidate = self.candidate(); domain = candidate['weight_domains'][0]
        domain['constraints'] = [dict(id='care', coefficients={'care':'-1','convenience':'0'},rhs='-1/2',relation='LE',segment_ids=domain['segment_ids'])]
        after = thaw(self.pure(candidate, limit=300000).values)
        self.assertEqual(before['program']['base_program'], after['program']['base_program'])
        b=before['actual_judgment']['models'][0]; a=after['actual_judgment']['models'][0]
        self.assertEqual(b['decisions'][0]['outcomes'], a['decisions'][0]['outcomes'])
        self.assertEqual({k:v['possible_values'] for k,v in b['facts'].items()}, {k:v['possible_values'] for k,v in a['facts'].items()})
        self.assertEqual(b['actual_interaction']['values']['models'][0]['commitments'], a['actual_interaction']['values']['models'][0]['commitments'])
        analysis = after['analyses'][0]
        self.assertTrue(analysis['unique_robust_recommended'])
        self.assertEqual(analysis['policy_catalog'][analysis['unique_robust_recommended'][0]], dict(root_action_id='inspect',continuations={'r':'protect'}))

    def test_second_step_hard_norm_feasibility_and_fact_changes_recompute_regions(self):
        before = thaw(self.pure(limit=300000).values)
        def permitted(value):
            a = value['analyses'][0]
            return [a['policy_catalog'][key] for key in a['possible_recommended']]
        self.assertNotIn(dict(root_action_id='inspect',continuations={'r':'ignore'}),permitted(before))
        candidate = self.candidate()
        for key in ('received_by','understood_by','trusted_by'):
            candidate['models'][0]['mental']['events'][0][key] = []
        after = thaw(self.pure(candidate,limit=300000).values)
        self.assertTrue(any('ignore' in p['continuations'].values() for p in permitted(after)))
        candidate = self.candidate()
        candidate['models'][0]['mental']['plans'][0]['graph']['actions'][1]['feasible'] = []
        after = thaw(self.pure(candidate,limit=300000).values)
        self.assertEqual(permitted(after), [dict(root_action_id='safe',continuations={})])

    def test_unknown_norm_and_empty_domain_never_claim_robust_policy(self):
        candidate = self.candidate(); model=candidate['models'][0]
        model['mental']['variables'][1]['initial'] = None
        model['decisions'][0]['frameworks'][0]['norms'][0].update(guard_fact_ids=['promise'],argument_query_id=None)
        value=thaw(self.pure(candidate,limit=300000).values)
        self.assertFalse(value['complete']); self.assertTrue(value['analyses'][0]['branches'][0]['regions']['cells'])
        self.assertFalse(value['analyses'][0]['possible_recommended'])
        candidate = self.candidate(); domain=candidate['weight_domains'][0]
        domain['constraints']=[dict(id='empty',coefficients={'care':'1','convenience':'1'},rhs='0',relation='LE',segment_ids=domain['segment_ids'])]
        value=thaw(self.pure(candidate,limit=300000).values)
        self.assertTrue(value['complete']); self.assertFalse(value['analyses'][0]['robust_recommended'])
        self.assertEqual(value['analyses'][0]['branches'][0]['regions']['domain_status'],'EMPTY')

    def test_actual_policy_catalog_and_tie_certificate_tampering_fail_delivery(self):
        _,_,_,proof=self.run_candidate()
        for mutate in (
            lambda v: next(iter(v['analyses'][0]['policy_catalog'].values())).update(root_action_id='forged'),
            lambda v: v['analyses'][0].update(policy_horizon=1),
            lambda v: v['analyses'][0]['branches'][0]['regions'].update(scalar_tie_semantics='drop ties'),
            lambda v: v['actual_judgment']['models'][0]['decisions'][0]['outcomes'][0]['policy'].update(continuations={'r':'ignore'}),
        ):
            value=thaw(proof.values);mutate(value)
            with self.assertRaises(HCLFailure): AnswerAssembler()._claim(replace(proof,values=value))

    def test_policy_enumeration_region_and_proof_frontiers_do_not_certify(self):
        candidate = self.candidate('MINIMAX_REGRET',uncertain=True)
        value=thaw(self.pure(candidate,limit=9000).values)
        self.assertFalse(value['complete']); self.assertTrue(value['issues'])
        self.assertTrue(all(not a['robust_recommended'] and not a['possible_recommended'] for a in value['analyses']))
        with patch('hcl.operators.bounded_policy.MAX_POLICIES',1):
            value=thaw(self.pure(candidate,limit=300000).values)
        self.assertFalse(value['complete']);self.assertTrue(all(not a['robust_recommended'] for a in value['analyses']))
        complex_candidate = self.candidate('MINIMAX_REGRET', uncertain=True, observable=False)
        for d in complex_candidate['models'][0]['decisions'][0]['dimensions']:
            d['action_costs'].update(inspect='1/3', protect='1/5', ignore='1/7')
        value=thaw(self.pure(complex_candidate,limit=3000000).values)
        self.assertFalse(value['complete'])
        self.assertIn('WEIGHT_PROOF_CAPACITY_FRONTIER',value['issues'])
        self.assertFalse(value['analyses'][0]['possible_recommended'])
        from hcl.operators import weight_region_model
        original=weight_region_model.solve_regions
        for options in (dict(max_cells=1),dict(max_proof_bytes=1)):
            with patch.object(weight_region_model,'solve_regions',side_effect=lambda *a,**kw:original(*a,**kw,**options)):
                value=thaw(self.pure(candidate,limit=300000).values)
            self.assertFalse(value['complete']); self.assertFalse(value['analyses'][0]['possible_recommended'])

    def test_three_four_dimensions_and_single_scenario_requirement(self):
        for count in (3,4):
            candidate = self.candidate(); decision=candidate['models'][0]['decisions'][0]
            for i in range(count-2):
                d=deepcopy(decision['dimensions'][0]);d['id']='aux'+str(i);decision['dimensions'].append(d)
            domain=candidate['weight_domains'][0];ids=[d['id'] for d in decision['dimensions']]
            domain['constraints']=[dict(id=d,coefficients={k:'1' if k==d else '0' for k in ids},rhs='1/2' if d in ('care','convenience') else '0',relation='EQ',segment_ids=domain['segment_ids']) for d in ids]
            value=thaw(self.pure(candidate,limit=300000).values)
            self.assertTrue(value['complete']);self.assertEqual(len(value['analyses'][0]['unique_robust_recommended']),1)
        candidate = self.candidate('MAXIMIN',uncertain=True)
        candidate['weight_domains'][0]['decision_rule']='EXPECTED'
        value=thaw(self.pure(candidate,limit=300000).values)
        self.assertFalse(value['complete']);self.assertIn('EXPECTED_PROBABILITIES_UNSPECIFIED',value['analyses'][0]['frontier'])

    def test_run_replay_and_all_durable_recovery_seams(self):
        from hcl.operators.local_model import LocalModelOperator
        class Crash(BaseException): pass
        for seam in ('return_persisted','execution_computed','execution_effects_committed','send_started'):
            candidate=self.candidate('MINIMAX_REGRET')
            request=replace(self.f.request,request_id=seam,issue=ExecutionIssue('root',goals=(Issue(seam,'judgment.evaluate'),)))
            owner=self.f.store.owner_id;fired=False
            def stop(stage):
                nonlocal fired
                if stage==seam and not fired:fired=True;raise Crash()
            with patch.object(self.f.store,'_checkpoint',side_effect=stop),self.assertRaises(Crash):
                self.f.run_candidate(candidate,request)
            self.assertTrue(fired)
            self.f.store.close(); self.f.store=__import__('hcl.memory.store',fromlist=['StateStore']).StateStore.sqlite(self.f.path)
            if seam=='send_started':
                with self.assertRaises(HCLFailure):RecoveryManager(self.f.store).resume_execution(request,expected_owner_id=owner)
                result,port=self.f.run_candidate(candidate,request)
                self.assertEqual(port.attempts,0);self.assertIsNone(result.usage['mock_calls']);self.assertFalse(result.answer)
            else:
                RecoveryManager(self.f.store).resume_execution(request,expected_owner_id=owner)
                if seam=='return_persisted':
                    _,result,port,_=self.run_candidate(candidate,request)
                else:
                    with patch.object(LocalModelOperator,'run',side_effect=AssertionError('no recompute of committed effects')):
                        _,result,port,_=self.run_candidate(candidate,request)
                self.assertEqual(port.attempts,0)
                _,replay,port,_=self.run_candidate(candidate,request)
                self.assertEqual(result.answer,replay.answer);self.assertEqual(port.attempts,0)


if __name__=='__main__': unittest.main()
