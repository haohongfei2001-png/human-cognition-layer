import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import run_argument_countermodel_dev_v01 as r
class ArgumentCountermodelTests(unittest.TestCase):
 def item(self,i='example'):
  text='Argument:\n\n∀x(Fx→Gx), Fa |= Ga';p,c,_,_=r.argument(text)
  return {'id':i,'source':{'public_task':text,'premises':p,'conclusion':c,'domain':[0,1,2],'scope':'FORMAL'},'source_sha256':'x'}
 def test_top_level_premise_separation_and_scope(self):
  p,c,a,b=r.argument('Argument:\n\n∀x(Fx→(Gx∨Hx)), ∃xFx |= ∃xGx');self.assertEqual(len(p),2);self.assertEqual(c,'∃xGx')
  for text in ['Argument:\n\nFx |= Ga','Argument:\n\n(Fa→Ga |= Ga','Argument:\n\nFa |= Ga |= Ha']:
   with self.assertRaises(ValueError):r.argument(text)
 def test_countermodel_independent_check_and_false_premise(self):
  x=self.item();x['source']['conclusion']='Ha'
  model={'domain':[0,1,2],'constants':{'a':0},'predicates':{'F':[0],'G':[0],'H':[]}}
  _,v=r.model_answer(json.dumps(model),x);self.assertTrue(v['is_countermodel']);model['predicates']['G']=[];_,v=r.model_answer(json.dumps(model),x);self.assertFalse(v['is_countermodel']);self.assertEqual(v['premises'],[False,True]);self.assertFalse(v['conclusion'])
 def test_exact_domain_symbol_arity_and_output_contract(self):
  model={'domain':[0,1,2],'constants':{'a':0},'predicates':{'F':[0],'G':[0]}}
  for b in [model|{'domain':[0,1]},model|{'extra':'x'},model|{'predicates':{'F':[0],'G':[0],'H':[]}},model|{'predicates':{'F':[[0,1]],'G':[0]}}]:
   with self.assertRaises(ValueError):r.model_answer(json.dumps(b),self.item())
 def test_scoring_and_tool_after_all_calls_no_hidden_reference(self):
  calls=[];events=[]
  class B:
   def complete(self,m):calls.append(m);return {'raw_response':'{"domain":[0,1,2],"constants":{"a":0},"predicates":{"F":[0],"G":[0]}}','reasoning_chars':0}
  original=r.model_answer
  def score(*a):events.append(len(calls));return original(*a)
  with patch.object(r,'model_answer',side_effect=score),patch.object(r,'find_countermodel',side_effect=lambda *a:events.append(len(calls)) or {'status':'NO_COUNTERMODEL_IN_THIS_DOMAIN','entailment':'UNRESOLVED'}):rows,fail=r.execute([self.item(str(i)) for i in range(4)],{a:B() for a in ['C','P']})
  self.assertFalse(fail);self.assertEqual(len(calls),8);self.assertEqual(set(events),{8});self.assertTrue(all(row['arms']['C']['actual_messages'][1]==row['arms']['P']['actual_messages'][1] for row in rows));self.assertTrue(all(row['arms']['T']['provider_calls']==0 for row in rows))
 def test_partial_keeps_paid_response_no_retries(self):
  calls=[]
  class B:
   def __init__(self,a):self.a=a;self.last_attempt={'actual_request':{'messages':[]},'raw_response':None}
   def complete(self,m):
    calls.append(self.a)
    if self.a=='P':raise RuntimeError('DO_NOT_ARCHIVE_ERROR_BODY')
    return {'raw_response':'','reasoning_chars':0}
  rows,fail=r.execute([self.item()],{a:B(a) for a in ['C','P']});self.assertEqual(calls,['C','P']);self.assertTrue(fail);self.assertEqual(rows[0]['arms']['C']['response']['raw_response'],'');self.assertIsNone(rows[0]['arms']['P']['response']['raw_response']);self.assertNotIn('DO_NOT_ARCHIVE_ERROR_BODY',json.dumps(fail))
 def test_scoring_exception_retains_all_final_replies(self):
  class B:
   def complete(self,m):return {'raw_response':'{}','reasoning_chars':0}
  with patch.object(r,'model_answer',side_effect=RuntimeError('DO_NOT_ARCHIVE')),patch.object(r,'find_countermodel',side_effect=RuntimeError('DO_NOT_ARCHIVE')):rows,fail=r.execute([self.item()],{a:B() for a in ['C','P']})
  self.assertFalse(fail);self.assertTrue(all(v['verification']['status']=='SCORER_ERROR' and v['response']['raw_response']=='{}' for a,v in rows[0]['arms'].items() if a!='T'));self.assertEqual(rows[0]['arms']['T']['tool']['status'],'SCORER_ERROR');self.assertNotIn('DO_NOT_ARCHIVE',json.dumps(rows))
 def test_separate_budget_old_authorization_cannot_execute(self):
  items=[self.item(str(i)) for i in range(4)]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'manifest';p.write_text(json.dumps(r.manifest(items)))
   with patch.object(r,'MANIFEST',p),patch.object(r,'load',return_value={}),patch.object(r,'select',return_value=items),patch('sys.argv',['r','--source-file','none','--execute']),patch.dict(r.os.environ,{'GITHUB_ACTIONS':'true','GITHUB_RUN_ATTEMPT':'1','HCL_ARGUMENT_COUNTERMODEL_DEV_RUN_ONCE_TOKEN':r.TOKEN,'HCL_QUANTIFIER_LOGICSKILLS_DEV_COST_AUTHORIZED_USD':'100'},clear=True):
    with self.assertRaisesRegex(RuntimeError,'independent authorization'):r.main()
