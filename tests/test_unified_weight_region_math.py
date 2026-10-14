"""Independent continuous rational breakpoint oracle, never a sampled grid."""
from fractions import Fraction as F
from itertools import combinations, product
import unittest

from hcl.operators.judgment import JudgmentWork
from hcl.operators.weight_regions import solve_regions, feasible, verify_feasibility, inequality


def oracle(vectors, rule, lo=F(0), hi=F(1)):
    lines=[(F(v['x'])-F(v['y']),F(v['y'])) for scenarios in vectors.values() for v in scenarios.values()]
    boundaries={lo,hi}
    for (a,b),(c,d) in combinations(lines,2):
        if a!=c and lo <= (d-b)/(a-c) <= hi: boundaries.add((d-b)/(a-c))
    points=sorted(boundaries)
    def winners(x):
        scores={a:{s:x*F(v['x'])+(1-x)*F(v['y']) for s,v in scenarios.items()} for a,scenarios in vectors.items()}
        worst={a:min(values.values()) for a,values in scores.items()}
        best=max(worst.values(),default=None)
        return sorted(a for a in scores if worst[a]==best and (rule=='EXPECTED' or not any(
            b!=a and all(scores[b][s]>=scores[a][s] for s in scores[a]) and any(scores[b][s]>scores[a][s] for s in scores[a]) for b in scores)))
    return [(x,x,True,True,winners(x)) for x in points]+[(a,b,False,False,winners((a+b)/2)) for a,b in zip(points,points[1:])]


def contains(interval,x):
    a,b=F(interval['lower']),F(interval['upper'])
    return (x>a or x==a and interval['lower_closed']) and (x<b or x==b and interval['upper_closed'])


class ExactWeightMathematicsTests(unittest.TestCase):
    def solve(self,vectors,rule='EXPECTED',constraints=(),limit=1000000):
        work=JudgmentWork(limit)
        result=solve_regions(dict(constraints=list(constraints)),vectors,['x','y'],rule,work)
        self.assertLessEqual(work.used,limit)
        return result

    def test_automatic_classic_boundaries_open_closed_all_ties(self):
        v={a:{'s':dict(x=x,y=y)} for a,(x,y) in dict(X=(10,0),Y=(6,6),Z=(0,10)).items()}
        r=self.solve(v)
        self.assertTrue(r['complete']);self.assertEqual(r['robust_recommended'],[])
        p=r['recommendation_partition']
        self.assertEqual([(x['lower'],x['upper'],x['lower_closed'],x['upper_closed'],x['recommended']) for x in p],
            [('0','2/5',True,False,['Z']),('2/5','2/5',True,True,['Y','Z']),('2/5','3/5',False,False,['Y']),('3/5','3/5',True,True,['X','Y']),('3/5','1',False,True,['X'])])
        constraints=[dict(coefficients=dict(x='-1',y='0'),rhs='-9/20',relation='LE'),dict(coefficients=dict(x='1',y='0'),rhs='11/20',relation='LE')]
        bounded=self.solve(v,constraints=constraints)
        self.assertEqual(bounded['unique_robust_recommended'],['Y'])
        self.assertEqual(bounded['recommendation_partition'][0]['lower'],'9/20')

    def test_continuous_oracle_generated_expected_and_maximin(self):
        # Every rational root AND every open interval is verified; a finite
        # grid could miss both isolated ties and arbitrarily narrow intervals.
        for seed in range(28):
            for rule in ('EXPECTED','MAXIMIN'):
                vectors={a:{str(s):dict(x=str(F((seed*(i+2)+s*7)%13-6,(seed%3)+1)),y=str(F((seed*3+i*5+s)%11-5,2)))
                    for s in range(1 if rule=='EXPECTED' else 2)} for i,a in enumerate('ABC')}
                actual=self.solve(vectors,rule)
                self.assertTrue(actual['complete'],actual['frontier'])
                for lower,upper,lc,uc,winners in oracle(vectors,rule):
                    x=(lower+upper)/2
                    cells=[c for c in actual['cells'] if contains(c['interval'],x)]
                    self.assertEqual(len(cells),1)
                    self.assertEqual(cells[0]['recommended'],winners,(seed,rule,x))

    def test_maximin_switch_and_dominated_tie_boundaries(self):
        v={'A':{'s':dict(x=10,y=0),'t':dict(x=0,y=10)},'B':{'s':dict(x=4,y=4),'t':dict(x=4,y=4)}}
        r=self.solve(v,'MAXIMIN'); p=r['recommendation_partition']
        self.assertEqual([(a['lower'],a['upper'],a['lower_closed'],a['upper_closed'],a['recommended']) for a in p],
            [('0','2/5',True,False,['B']),('2/5','3/5',True,True,['A']),('3/5','1',False,True,['B'])])
        center=next(c for c in r['cells'] if contains(c['interval'],F(1,2)))
        self.assertEqual(center['worst_scenarios']['A'],['s','t'])
        self.assertTrue(any(c['dominated']==['B'] for c in r['cells']))

    def test_zero_weight_negative_values_and_all_ties(self):
        vectors={'A':{'s':dict(x=-100,y=-2)},'B':{'s':dict(x=100,y=-2)}}
        r=self.solve(vectors,constraints=[dict(coefficients=dict(x=1,y=0),rhs=0,relation='EQ')])
        self.assertEqual(r['robust_recommended'],['A','B']);self.assertEqual(r['unique_robust_recommended'],[])
        vectors={'A':{'s':dict(x=-2,y=-2)},'B':{'s':dict(x=-2,y=-2)}}
        self.assertEqual(self.solve(vectors)['recommendation_partition'][0]['recommended'],['A','B'])

    def test_empty_domain_and_strict_zero_have_dual_no_vacuous_robustness(self):
        v={'A':{'s':dict(x=1,y=1)}}
        for constraints in ([dict(coefficients=dict(x=1,y=1),rhs=0,relation='LE')],
                            [dict(coefficients=dict(x=1,y=0),rhs=0,relation='LT')]):
            r=self.solve(v,constraints=constraints)
            self.assertTrue(r['complete']);self.assertEqual(r['status'],'EMPTY_DOMAIN')
            self.assertFalse(r['robust_recommended']);self.assertEqual(r['domain_certificate']['status'],'EMPTY')

    def test_open_domain_and_narrow_interval(self):
        v={'A':{'s':dict(x=1,y=0)},'B':{'s':dict(x=0,y=1)}}
        c=[dict(coefficients=dict(x=-1,y=0),rhs='-1/2',relation='LT'),dict(coefficients=dict(x=1,y=0),rhs='500001/1000000',relation='LT')]
        r=self.solve(v,constraints=c)
        self.assertEqual(r['unique_robust_recommended'],['A'])
        self.assertFalse(r['recommendation_partition'][0]['lower_closed']);self.assertFalse(r['recommendation_partition'][0]['upper_closed'])

    def test_three_dimensions_lower_dimensional_ties_and_strict_constraints(self):
        v={'A':{'s':dict(x=1,y=0,z=0)},'B':{'s':dict(x=0,y=1,z=0)},'C':{'s':dict(x=0,y=0,z=1)}}
        r=solve_regions(dict(constraints=[]),v,['x','y','z'],'EXPECTED',JudgmentWork(1000000))
        self.assertTrue(r['complete']);self.assertEqual(r['possible_recommended'],['A','B','C'])
        self.assertTrue(any(c['recommended']==['A','B','C'] for c in r['cells']))
        for cell in r['cells']: verify_feasibility(cell['constraints'],2,cell['certificate'],JudgmentWork(100000))

    def test_one_dimension_and_no_permitted_actions(self):
        for vectors in ({'A':{'s':{'x':'-2'}}},{}):
            r=solve_regions(dict(constraints=[]),vectors,['x'],'MAXIMIN',JudgmentWork(10000))
            self.assertTrue(r['complete']);self.assertEqual(r['robust_recommended'],list(vectors))

    def test_infeasibility_certificate_tamper_rejected(self):
        rows=[inequality([1],0,True),inequality([-1],0)]
        proof=feasible(rows,1,JudgmentWork(1000));self.assertEqual(proof['status'],'EMPTY')
        proof['rhs']='-1'
        with self.assertRaises(ValueError):verify_feasibility(rows,1,proof,JudgmentWork(1000))

    def test_budget_and_cell_frontiers_never_certify_robustness(self):
        v={a:{'s':dict(x=x,y=y)} for a,(x,y) in dict(X=(10,0),Y=(6,6),Z=(0,10)).items()}
        for limit in (0,1,30,100,500,1100):
            r=self.solve(v,limit=limit);self.assertFalse(r['complete']);self.assertFalse(r['robust_recommended'])
        r=solve_regions(dict(constraints=[]),v,['x','y'],'EXPECTED',JudgmentWork(100000),max_cells=1)
        self.assertFalse(r['complete']);self.assertTrue(r['pending_cells']);self.assertFalse(r['robust_recommended'])


if __name__=='__main__':unittest.main()
