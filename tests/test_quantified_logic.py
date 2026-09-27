import itertools,unittest
from hcl.quantified_logic import parse,evaluate,check_countermodel,find_countermodel,equivalent,FormulaError
class QuantifiedLogicTests(unittest.TestCase):
 def test_quantifier_order_against_all_two_element_relations(self):
  pairs=list(itertools.product(range(2),repeat=2));a=parse('∀x∃yRxy');b=parse('∃y∀xRxy')
  for bits in itertools.product([False,True],repeat=4):
   ext=[list(t) for t,v in zip(pairs,bits) if v];m={'domain':[0,1],'constants':{},'predicates':{'R':ext}}
   self.assertEqual(evaluate(a,m),all(any([x,y] in ext for y in range(2)) for x in range(2)))
   self.assertEqual(evaluate(b,m),any(all([x,y] in ext for x in range(2)) for y in range(2)))
 def test_countermodel_is_independently_verified(self):
  ps=[parse('∀x(Fx→Gx)'),parse('Ga')];c=parse('Fa');r=find_countermodel(ps,c)
  self.assertEqual(r['status'],'VERIFIED_FINITE_COUNTERMODEL');self.assertTrue(check_countermodel(ps,c,r['model'])['is_countermodel'])
 def test_bounded_absence_is_not_validity(self):
  p=parse('∀x∃yRxy');c=parse('∃y∀xRxy');r=find_countermodel([p],c,1)
  self.assertEqual(r['status'],'NO_COUNTERMODEL_IN_THIS_DOMAIN');self.assertEqual(r['entailment'],'UNRESOLVED');self.assertEqual(find_countermodel([p],c,2)['status'],'VERIFIED_FINITE_COUNTERMODEL')
 def test_full_equivalence_and_non_equivalence(self):
  self.assertEqual(equivalent(parse('∀x(Fx→Gx)'),parse('¬∃x(Fx∧¬Gx)'))['status'],'EQUIVALENT')
  self.assertEqual(equivalent(parse('∀x∃yRxy'),parse('∃y∀xRxy'))['status'],'NOT_EQUIVALENT')
 def test_shadowing_and_constants_need_not_be_distinct(self):
  m={'domain':[0,1],'constants':{'a':0,'b':0},'predicates':{'F':[0]}}
  self.assertTrue(evaluate(parse('(Fa↔Fb)'),m))
  self.assertTrue(evaluate(parse('∀x∃xFx'),{'domain':[0,1],'constants':{},'predicates':{'F':[1]}}))
 def test_invalid_signature_domain_and_unbound_terms(self):
  for f in ['Fx','∀x(Fx∧Fxy)','∀xFxxx','__import__(x)','∀x(Fx→Gx','∀xFx trailing','∀xFx=Ga']:
   with self.assertRaises(FormulaError):parse(f)
  for m in [{'domain':[],'constants':{},'predicates':{'F':[]}},{'domain':[False],'constants':{},'predicates':{'F':[]}},{'domain':[0],'constants':{},'predicates':{'F':[[0]]}},{'domain':[0],'constants':{},'predicates':{'F':[0,0]}}]:
   with self.assertRaises(FormulaError):evaluate(parse('∀xFx'),m)
 def test_false_premise_never_counts_as_countermodel(self):
  m={'domain':[0],'constants':{'a':0},'predicates':{'F':[]}}
  self.assertFalse(check_countermodel([parse('Fa')],parse('Fa'),m)['is_countermodel'])
 def test_syntax_and_work_limits_fail_closed(self):
  with self.assertRaises(FormulaError):parse('¬'*70+'∀xFx')
  with self.assertRaises(FormulaError):parse('F'+'a'*4001)
