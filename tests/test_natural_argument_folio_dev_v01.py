import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import run_natural_argument_folio_dev_v01 as r
class NaturalArgumentTests(unittest.TestCase):
 def item(self,i=0):return {'row_index':i,'story_sha256':str(i),'source_sha256':str(i),'source':{'premises':['All birds fly.','Ava is a bird.'],'conclusion':'Ava flies.','scope':'CONDITIONAL'}}
 def test_reference_access_after_all_calls_and_input_parity(self):
  calls=[];access=[]
  class Native(dict):
   def __getitem__(self,k):
    if k=='label':access.append(len(calls))
    return super().__getitem__(k)
  class B:
   def complete(self,m):calls.append(m);return {'raw_response':'{"label":"True"}','reasoning_chars':0}
  rows,fail=r.execute([self.item(i) for i in range(4)],[Native(label='True',**{'premises-FOL':['SECRET_FORM']}) for i in range(4)],{a:B() for a in ['C','P']})
  self.assertEqual(access,[8]*4);self.assertFalse(fail);self.assertNotIn('SECRET',json.dumps(calls));self.assertTrue(all(v['native_agreement'] for row in rows for v in row['arms'].values()));self.assertTrue(all(row['arms']['C']['actual_messages'][1]==row['arms']['P']['actual_messages'][1] for row in rows))
 def test_selection_story_grouping_and_public_exposure_not_labels(self):
  class Source(dict):
   def __getitem__(self,k):
    if k not in ['premises','conclusion']:raise AssertionError('reference access')
    return super().__getitem__(k)
  rows=[Source(premises=['Premise '+str(i//2)],conclusion='Conclusion '+str(i)) for i in range(12)]+[Source(premises=[r.EXPOSED[0]],conclusion='excluded')]
  chosen=r.select(rows);self.assertEqual(len({x['story_sha256'] for x in chosen}),4);self.assertTrue(all(x['row_index']<12 for x in chosen));self.assertEqual(chosen,r.select(rows))
 def test_strict_three_label_contract_no_rewrite(self):
  for label in r.LABELS:self.assertEqual(r.parse_answer(json.dumps({'label':label}))['label'],label)
  for raw in ['{"label":"unknown"}','{"label":"True","type":"json_object"}','true','', '{"label":true}']:
   with self.assertRaises((ValueError,TypeError)):r.parse_answer(raw)
 def test_partial_keeps_raw_reply_no_retry(self):
  calls=[]
  class B:
   def __init__(self,a):self.a=a;self.last_attempt={'raw_response':None}
   def complete(self,m):
    calls.append(self.a)
    if self.a=='P':raise RuntimeError('DO_NOT_ARCHIVE_ERROR_BODY')
    return {'raw_response':'{"label":"Uncertain"}','reasoning_chars':0}
  rows,fail=r.execute([self.item()],[{'label':'True'}],{a:B(a) for a in ['C','P']});self.assertEqual(calls,['C','P']);self.assertTrue(fail);self.assertEqual(rows[0]['arms']['C']['answer']['label'],'Uncertain');self.assertNotIn('DO_NOT_ARCHIVE',json.dumps(fail))
 def test_bad_native_reference_preserves_responses(self):
  class B:
   def complete(self,m):return {'raw_response':'{"label":"True"}','reasoning_chars':0}
  rows,fail=r.execute([self.item()],[{'label':'INVALID_REFERENCE'}],{a:B() for a in ['C','P']});self.assertFalse(fail);self.assertTrue(all(v['response']['raw_response'] and v['reference_error']=='ValueError' and v['native_agreement'] is None for v in rows[0]['arms'].values()))
 def test_old_budget_cannot_execute_new_scope(self):
  items=[self.item(i) for i in range(4)]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'manifest';p.write_text(json.dumps(r.manifest(items)))
   with patch.object(r,'MANIFEST',p),patch.object(r,'load',return_value=[]),patch.object(r,'select',return_value=items),patch('sys.argv',['r','--source-file','none','--execute']),patch.dict(r.os.environ,{'GITHUB_ACTIONS':'true','GITHUB_RUN_ATTEMPT':'1','HCL_NATURAL_ARGUMENT_FOLIO_DEV_RUN_ONCE_TOKEN':r.TOKEN,'HCL_ARGUMENT_COUNTERMODEL_DEV_COST_AUTHORIZED_USD':'100'},clear=True):
    with self.assertRaisesRegex(RuntimeError,'independent financial'):r.main()
