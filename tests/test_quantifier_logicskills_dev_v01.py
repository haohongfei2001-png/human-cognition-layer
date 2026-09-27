import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from scripts import run_quantifier_logicskills_dev_v01 as r
from scripts.reasoning_probe_backend import ReasoningBackend,BudgetLedger
class QuantifierProbeTests(unittest.TestCase):
 def item(self,i=0):return {'id':i,'source':{'input':'Sentence:\n\nAll birds fly.\n\nAbbreviations:\n\nF: [1] is a bird\nG: [1] flies\n','scope':'PUBLIC'},'source_sha256':'h'}
 def test_gold_delayed_input_parity_and_semantic_equivalence(self):
  calls=[];gold=[];parent=self
  class Row(dict):
   def __getitem__(self,k):
    if k=='form':gold.append(len(calls))
    return super().__getitem__(k)
  class B:
   def complete(self,m):
    calls.append(m);return {'raw_response':json.dumps({'formula':'¬∃x(Fx∧¬Gx)'}),'reasoning_chars':10}
  rows,fail=r.execute([self.item(i) for i in range(4)],[Row(id=i,form='∀x(Fx→Gx)') for i in range(4)],{a:B() for a in ['C','P']})
  self.assertFalse(fail);self.assertEqual(gold,[8]*4);self.assertTrue(all(v['semantic_verification']['status']=='EQUIVALENT' for row in rows for v in row['arms'].values()));self.assertTrue(all(row['arms']['C']['actual_messages'][1]==row['arms']['P']['actual_messages'][1] for row in rows));self.assertTrue(all('reference_formula' not in json.loads(ms[1]['content']) for ms in calls));self.assertNotIn('∀x(Fx→Gx)',json.dumps(calls,ensure_ascii=False))
 def test_partial_failure_preserves_first_actual_response_and_no_retry(self):
  calls=[]
  class B:
   def __init__(self,a):self.a=a
   def complete(self,m):
    calls.append(self.a)
    if self.a=='P':raise RuntimeError('uncertain transport')
    return {'raw_response':'{"formula":"∀x(Fx→Gx)"}','reasoning_chars':1}
  rows,fail=r.execute([self.item()],[{'id':0,'form':'∀x(Fx→Gx)'}],{a:B(a) for a in ['C','P']});self.assertEqual(calls,['C','P']);self.assertTrue(fail);self.assertEqual(rows[0]['arms']['C']['answer']['formula'],'∀x(Fx→Gx)');self.assertIsNone(rows[0]['arms']['P']['response']);self.assertEqual(rows[0]['arms']['P']['actual_messages'],r.messages(self.item(),'P'))
 def test_invented_predicate_and_unbound_variable_rejected(self):
  for f in ['∀xHx','Fx','∀xFxy']:
   with self.assertRaises(ValueError):r.parse_answer(json.dumps({'formula':f}),self.item())
 def test_new_scope_cannot_use_old_budget(self):
  items=[self.item(i) for i in range(4)]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'f';p.write_text(json.dumps(r.manifest(items)))
   with patch.object(r,'MANIFEST',p),patch.object(r,'load',return_value=[]),patch.object(r,'select',return_value=items),patch('sys.argv',['r','--source-file','none','--execute']),patch.dict(r.os.environ,{'GITHUB_ACTIONS':'true','GITHUB_RUN_ATTEMPT':'1','HCL_QUANTIFIER_LOGICSKILLS_DEV_RUN_ONCE_TOKEN':r.TOKEN,'HCL_NARRATIVE_TORQUE_DEV_V02_COST_AUTHORIZED_USD':'100'},clear=True):
    with self.assertRaisesRegex(RuntimeError,'separate quantifier'):r.main()
 def backend(self,reason_tokens=30):
  b=ReasoningBackend.__new__(ReasoningBackend);b.ledger=BudgetLedger(.05);b.calls=0;b.cost=b.wall=0;requests=[]
  def create(**kw):
   requests.append(kw);return NS(model='alias',usage=NS(prompt_tokens=100,completion_tokens=40,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=100,completion_tokens_details=NS(reasoning_tokens=reason_tokens)),choices=[NS(message=NS(content='{"formula":"∀xFx"}',reasoning_content='PRIVATE_REASONING'),finish_reason='stop')])
  b.client=NS(chat=NS(completions=NS(create=create)));return b,requests
 def test_actual_thinking_shape_and_total_reasoning_token_charge(self):
  b,requests=self.backend();v=b.complete(r.messages(self.item(),'C'));self.assertEqual(requests[0]['extra_body']['thinking']['type'],'enabled');self.assertEqual(requests[0]['reasoning_effort'],'high');self.assertNotIn('temperature',requests[0]);self.assertNotIn('seed',requests[0]);self.assertEqual(requests[0]['max_tokens'],4096);self.assertEqual(v['usage']['reasoning_tokens'],30);self.assertAlmostEqual(b.cost,(100*.3+40*1.2)/1e6);self.assertNotIn('PRIVATE_REASONING',json.dumps(v));self.assertEqual(v['reasoning_chars'],17)
 def test_absent_reasoning_usage_stops_and_reserves_maximum(self):
  b,requests=self.backend(None)
  with self.assertRaises(RuntimeError):b.complete(r.messages(self.item(),'C'))
  self.assertEqual(len(requests),1);self.assertGreater(b.cost,.004);self.assertEqual(b.cost,b.ledger.spent_usd);self.assertEqual(b.last_attempt['raw_response'],'{"formula":"∀xFx"}');self.assertEqual(b.last_attempt['accounting'],'FULL_RESERVATION_AFTER_FAILURE')
 def test_unknown_is_preserved_and_not_scored_as_false(self):
  class B:
   def complete(self,m):return {'raw_response':'{"formula":"∀x(Fx→Gx)"}','reasoning_chars':1}
  with patch.object(r,'equivalent',return_value={'status':'UNKNOWN'}):rows,fail=r.execute([self.item()],[{'id':0,'form':'∀x(Fx→Gx)'}],{a:B() for a in ['C','P']})
  self.assertFalse(fail);self.assertEqual(rows[0]['arms']['C']['semantic_verification']['status'],'UNKNOWN')

 def test_scorer_exception_preserves_every_paid_final(self):
  calls=[]
  class B:
   def complete(self,m):calls.append(m);return {'raw_response':'{"formula":"∀x(Fx→Gx)"}','reasoning_chars':1}
  with patch.object(r,'equivalent',side_effect=RuntimeError('NEVER_ARCHIVE_ERROR_BODY')):
   rows,fail=r.execute([self.item()],[{'id':0,'form':'∀x(Fx→Gx)'}],{a:B() for a in ['C','P']})
  self.assertFalse(fail);self.assertEqual(len(calls),2);self.assertTrue(all(v['response']['raw_response'] and v['semantic_verification']['status']=='SCORER_ERROR' for v in rows[0]['arms'].values()));self.assertNotIn('NEVER_ARCHIVE_ERROR_BODY',json.dumps(rows))
