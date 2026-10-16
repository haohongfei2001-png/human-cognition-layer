"""Continuous exact regret oracle plus source-bound runtime/receipt checks."""
from copy import deepcopy
from dataclasses import replace
from fractions import Fraction as F
from itertools import combinations
import unittest

from hcl.kernel.types import HCLFailure, thaw
from hcl.operators.judgment import JudgmentWork
from hcl.operators.weight_regions import solve_regions
from hcl.runtime.answer import AnswerAssembler
from tests.test_unified_weight_region_math import contains
from tests import test_unified_weight_regions as runtime


def oracle(vectors, x):
    scores = {a: {s: x*F(v['x'])+(1-x)*F(v['y']) for s,v in rows.items()} for a,rows in vectors.items()}
    best = {s: max(rows[s] for rows in scores.values()) for s in next(iter(scores.values()))}
    worst = {a: max(best[s]-value for s,value in rows.items()) for a,rows in scores.items()}
    return sorted(a for a,value in worst.items() if value == min(worst.values()))


def breakpoints(vectors):
    # Independently derive every crossing of regret affine forms, plus endpoints.
    forms = []
    for a, rows in vectors.items():
        for b, others in vectors.items():
            for s, v in rows.items():
                y = F(others[s]['y'])-F(v['y'])
                forms.append((F(others[s]['x'])-F(v['x'])-y, y))
    points = {F(0), F(1)}
    for (a,b),(c,d) in combinations(forms,2):
        if a != c and 0 <= (d-b)/(a-c) <= 1:
            points.add((d-b)/(a-c))
    ordered = sorted(points)
    return ordered + [(a+b)/2 for a,b in zip(ordered,ordered[1:])]


class MinimaxRegretMathTests(unittest.TestCase):
    def solve(self, vectors, ids=('x','y'), **kwargs):
        return solve_regions({'constraints':[]}, vectors, ids, 'MINIMAX_REGRET', JudgmentWork(3000000), **kwargs)

    def test_continuous_independent_oracle_boundaries_and_open_intervals(self):
        for seed in range(12):
            vectors = {a:{str(s):dict(x=str(F((seed*(i+2)+s*7)%13-6,3)),y=str(F((seed*3+i*5+s)%11-5,2)))
                for s in range(2)} for i,a in enumerate('AB')}
            result=self.solve(vectors)
            self.assertTrue(result['complete'], result['frontier'])
            for x in breakpoints(vectors):
                cells=[c for c in result['cells'] if contains(c['interval'],x)]
                self.assertEqual(len(cells),1)
                self.assertEqual(cells[0]['recommended'],oracle(vectors,x),(seed,x))

    def test_differs_from_maximin_and_retains_dominated_regret_ties(self):
        # Utility floors prefer B; regret prefers A. No uniform prior invented.
        v={'A':{'s':dict(x=100,y=100),'t':dict(x=0,y=0)},
           'B':{'s':dict(x=60,y=60),'t':dict(x=10,y=10)}}
        r=self.solve(v); self.assertEqual(r['unique_robust_recommended'],['A'])
        c=r['cells'][0]
        self.assertEqual(c['maximum_regrets'],{'A':'10','B':'40'})
        self.assertEqual(c['regret_scenarios'],{'A':['t'],'B':['s']})
        self.assertEqual(c['scenario_best_actions'],{'s':['A'],'t':['B']})
        v={'A':{'s':dict(x=10,y=10),'t':dict(x=0,y=0)},
           'B':{'s':dict(x=9,y=9),'t':dict(x=0,y=0)},
           'C':{'s':dict(x=0,y=0),'t':dict(x=10,y=10)}}
        r=self.solve(v);self.assertEqual(r['robust_recommended'],['A','B','C'])
        self.assertIn('B',r['cells'][0]['dominated'])

    def test_regret_crossing_missing_from_raw_utility_arrangement(self):
        v={'A':{'s':dict(x=9,y=1),'t':dict(x=0,y=3)},
           'B':{'s':dict(x=1,y=2),'t':dict(x=4,y=0)}}
        r=self.solve(v);self.assertTrue(r['complete'])
        for x in breakpoints(v):
            self.assertEqual(next(c for c in r['cells'] if contains(c['interval'],x))['recommended'],oracle(v,x))

    def test_three_dimensions_single_action_empty_set_and_resource_frontier(self):
        v={'A':{'s':dict(x=1,y=-2,z=3),'t':dict(x=3,y=1,z=-1)}}
        r=self.solve(v,('x','y','z'));self.assertTrue(r['complete']);self.assertEqual(r['unique_robust_recommended'],['A'])
        self.assertTrue(all(c['maximum_regrets']=={'A':'0'} for c in r['cells']))
        r=self.solve({});self.assertTrue(r['complete']);self.assertFalse(r['robust_recommended'])
        v={'A':{'s':dict(x=10,y=0),'t':dict(x=0,y=10)},'B':{'s':dict(x=4,y=4),'t':dict(x=4,y=4)}}
        r=self.solve(v,max_cells=1);self.assertFalse(r['complete']);self.assertFalse(r['robust_recommended'])
        for limit in (0,20,100):
            work=JudgmentWork(limit);r=solve_regions({'constraints':[]},v,('x','y'),'MINIMAX_REGRET',work)
            self.assertLessEqual(work.used,limit);self.assertFalse(r['complete']);self.assertFalse(r['possible_recommended'])


class MinimaxRegretRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.f=runtime.WeightRegionRuntimeTests();self.f.setUp();self.addCleanup(self.f.doCleanups)

    def candidate(self):
        c=self.f.candidate();c['weight_domains'][0]['decision_rule']='MINIMAX_REGRET'
        return c

    def test_real_runner_compact_delivery_and_exact_replay(self):
        c=self.candidate();value,result,port,proof=self.f.run_candidate(c)
        self.assertTrue(value['complete']);self.assertIn('MINIMAX_REGRET',result.answer)
        self.assertIn('maximum_regrets',str(AnswerAssembler().compact_claim(proof).used_result_fields))
        replay,_,_,_=self.f.run_candidate(c);self.assertEqual(value,replay)
        for field in ('maximum_regrets','witness_regrets','regret_scenarios','scenario_best_actions'):
            forged=thaw(proof.values);forged['analyses'][0]['branches'][0]['regions']['cells'][0][field]={}
            with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(proof,values=forged))

    def test_hard_norm_excludes_utility_benchmark_and_unknown_guard_blocks_robustness(self):
        c=self.candidate();f=c['models'][0]['decisions'][0]['frameworks'][0]
        f['norms']=[dict(id='duty',label='protect',permitted_actions=['Y'],guard_fact_ids=[],argument_query_id=None,segment_ids=f['segment_ids'])]
        v=thaw(self.f.pure(c).values);a=v['analyses'][0]
        self.assertEqual(a['unique_robust_recommended'],['Y'])
        self.assertTrue(all(cell['maximum_regrets']=={'Y':'0'} for cell in a['branches'][0]['regions']['cells']))
        c['models'][0]['mental']['variables'][1]['initial']=None
        f['norms'][0]['guard_fact_ids']=['promise']
        v=thaw(self.f.pure(c).values);self.assertFalse(v['complete']);self.assertFalse(v['analyses'][0]['robust_recommended'])

    def test_joint_uncertainty_is_not_converted_into_expected_probabilities(self):
        c=self.candidate();m=c['models'][0];m['mental']['variables'][0]['initial']=None
        m['mental']['events']=[];m['mental']['active_assumptions']=['interpretation']
        v=thaw(self.f.pure(c).values)
        self.assertTrue(v['complete']);self.assertEqual(v['analyses'][0]['decision_rule'],'MINIMAX_REGRET')
        self.assertNotIn('EXPECTED_PROBABILITIES_UNSPECIFIED',v['issues'])


if __name__=='__main__':unittest.main()
