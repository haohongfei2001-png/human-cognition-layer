import unittest
from unittest.mock import patch
from hcl.argument_readings import classify_reading,compare_readings
from hcl.quantified_logic import FormulaError

class ReadingTests(unittest.TestCase):
 def test_chained_implication_and_counterexample(self):
  self.assertEqual(classify_reading(['∀x(Ax→Bx)','∀x(Bx→Cx)','Aa'],'Ca')['label'],'True')
  self.assertEqual(classify_reading(['Aa','¬Ba'],'∀x(Ax→Bx)')['label'],'False')
 def test_open_world_both_possibilities(self):
  x=classify_reading(['Aa'],'Ba');self.assertEqual(x['label'],'Uncertain')
  self.assertEqual(x['entailment_check']['status'],'NOT_EQUIVALENT');self.assertEqual(x['refutation_check']['status'],'NOT_EQUIVALENT')
 def test_inconsistency_does_not_become_true(self):
  x=classify_reading(['Aa','¬Aa'],'Ba');self.assertEqual(x['status'],'INCONSISTENT_PREMISES');self.assertIsNone(x['label'])
 def test_alternative_conjunction_and_disjunction(self):
  def row(rid,p):return {'id':rid,'source_sha256':'a'*64,'premises':[p],'conclusion':'Aa'}
  x=compare_readings([row('conjunction','(Aa∧Ba)'),row('disjunction','(Aa∨Ba)')]);self.assertEqual(x['status'],'READING_DEPENDENT');self.assertIsNone(x['label']);self.assertEqual([r['label'] for r in x['readings']],['True','Uncertain'])
 def test_agreement_is_limited_to_supplied_readings(self):
  x=compare_readings([{'id':'given','source_sha256':'a'*64,'premises':['Aa'],'conclusion':'Aa'}]);self.assertEqual(x['label'],'True');self.assertEqual(x['nl_reading_completeness'],'NOT_ESTABLISHED');self.assertEqual(x['provider_calls'],0)
 def test_timeout_not_uncertainty_or_entailment(self):
  with patch('hcl.argument_readings.equivalent',return_value={'status':'UNKNOWN'}):
   x=classify_reading(['Aa'],'Ba');self.assertEqual(x['status'],'UNKNOWN');self.assertIsNone(x['label'])
 def test_bounds_and_provenance_rejected(self):
  for premises in ([],['Aa']*17):
   with self.assertRaises(FormulaError):classify_reading(premises,'Ba')
  with self.assertRaises(FormulaError):classify_reading(['Aa'],'Ba',0)
  with self.assertRaises(FormulaError):compare_readings([{'id':'a','source_sha256':'x','premises':['Aa'],'conclusion':'Aa'}])
  a={'id':'a','source_sha256':'a'*64,'premises':['Aa'],'conclusion':'Aa'}
  with self.assertRaises(FormulaError):compare_readings([a,a])
  with self.assertRaises(FormulaError):compare_readings([a,{**a,'id':'b','source_sha256':'b'*64}])
 def test_named_constants_may_corefer(self):
  self.assertEqual(classify_reading(['Aa'],'Ab')['label'],'Uncertain')

if __name__=='__main__':unittest.main()
