import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import run_narrative_torque_dev_v01 as r
class TorqueTests(unittest.TestCase):
    text='alpha before beta.'
    def item(self,i='fixture'):return {'id':i,'source':{'passage':self.text,'scope':'PUBLIC'},'question':'What occurred after alpha?','source_sha256':'s','question_sha256':'q'}
    def graph(self):return json.dumps({'events':[{'id':'a','quote':'alpha','occurrence':0},{'id':'b','quote':'beta','occurrence':0}],'before':[{'earlier':'a','later':'b','quote':self.text,'occurrence':0}]})
    def native(self,empty=False):return {'question_answer_pairs':{self.item()['question']:{'answer':{'indices':[] if empty else ['(13,17)'],'spans':[] if empty else ['beta'],'agreed_by':[0,1]}}},'events':'POISON'}
    def test_quote_occurrences_distinguish_same_word_events(self):
        _,v=r.parse(json.dumps({'events':[{'quote':'go','occurrence':1}], 'reason':'Later mention.'}),'go then go');self.assertEqual(v,[(8,10)])
        for bad in [{'quote':'gone','occurrence':0},{'quote':'go','occurrence':True}]:
            with self.assertRaises(ValueError):r.parse(json.dumps({'events':[bad],'reason':'x'}),'go')
    def test_graph_fidelity_and_support_links(self):
        g=r.graph_parse(self.graph(),self.text);self.assertEqual(g.compare('a','b')['relation'],'BEFORE');self.assertEqual(r.compact(g)['derived_relations'][0]['support_edge_indices'],[0]);self.assertNotIn('What occurred',json.dumps(r.graph_messages(self.item())))
        for key,value in [('quote','missing'),('id','b')]:
            broken=json.loads(self.graph());broken['events'][0][key]=value
            with self.assertRaises(ValueError):r.graph_parse(json.dumps(broken),self.text)
    def test_all_states_before_questions_and_gold_delayed(self):
        calls=[];read_gold=[];parent=self
        class Delayed(dict):
            def __getitem__(self,k):read_gold.append(len(calls));return super().__getitem__(k)
        class Fake:
            def complete_json(self,messages,**kwargs):
                calls.append(messages);return parent.graph() if messages[0]['content']==r.GRAPH else json.dumps({'events':[{'quote':'beta','occurrence':0}],'reason':'beta follows alpha.'})
        rows,fail=r.execute([self.item(str(i)) for i in range(4)],Delayed({str(i):self.native() for i in range(4)}),{a:Fake() for a in r.CAPS});self.assertFalse(fail);self.assertEqual(len(calls),16);self.assertTrue(all(m[0]['content']==r.GRAPH for m in calls[:4]));self.assertTrue(all(n==16 for n in read_gold));self.assertNotIn('POISON',json.dumps(calls));self.assertTrue(all(v['agrees_with_native_reference'] for row in rows for v in row['arms'].values()))
        for row in rows:
            c=json.loads(row['arms']['C']['actual_messages'][1]['content']);p=json.loads(row['arms']['P']['actual_messages'][1]['content']);t=json.loads(row['arms']['T']['actual_messages'][1]['content']);self.assertEqual(c,p);self.assertEqual(c['source'],t['source']);self.assertEqual(c['question'],t['question'])
    def test_partial_transport_preserves_first_arm_without_retry(self):
        calls=[];parent=self
        class Fake:
            def __init__(self,a):self.arm=a
            def complete_json(self,messages,**kwargs):
                graph=messages[0]['content']==r.GRAPH;calls.append('graph' if graph else self.arm)
                if graph:return parent.graph()
                if self.arm=='P':raise RuntimeError('uncertain transport')
                return json.dumps({'events':[{'quote':'beta','occurrence':0}],'reason':'x'})
        rows,fail=r.execute([self.item()],{'fixture':self.native()},{a:Fake(a) for a in r.CAPS});self.assertEqual(calls,['graph','C','P']);self.assertTrue(fail);self.assertIn('C',rows[0]['arms']);self.assertNotIn('P',rows[0]['arms'])
    def test_invalid_graph_has_no_silent_direct_fallback(self):
        class Fake:
            def complete_json(self,messages,**kwargs):return '{}' if messages[0]['content']==r.GRAPH else json.dumps({'events':[],'reason':'No supported event.'})
        rows,fail=r.execute([self.item()],{'fixture':self.native(True)},{a:Fake() for a in r.CAPS});self.assertFalse(fail);self.assertFalse(rows[0]['arms']['T']['agrees_with_native_reference']);self.assertIn('no direct fallback',rows[0]['arms']['T']['invalid_reason'])
    def test_old_budget_does_not_authorize_new_scope(self):
        with tempfile.TemporaryDirectory() as d:
            m=Path(d)/'manifest';m.write_text(json.dumps(r.manifest([])))
            with patch.object(r,'MANIFEST',m),patch.object(r,'select',return_value=[]),patch('sys.argv',['run','--source-file','unused','--execute']),patch.dict(r.os.environ,{'GITHUB_ACTIONS':'true','GITHUB_RUN_ATTEMPT':'1','HCL_NARRATIVE_TORQUE_DEV_RUN_ONCE_TOKEN':r.TOKEN,'HCL_VALUE_CLASH_DEV_COST_AUTHORIZED_USD':'100'},clear=True):
                with self.assertRaisesRegex(RuntimeError,'separate narrative'):r.main()
