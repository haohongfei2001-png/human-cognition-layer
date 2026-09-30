import copy,json,os,tempfile,unittest
from pathlib import Path
from scripts.i02_clifford_source import SOURCE,OBLIGATIONS,audit,reconstruct
from scripts.i02_source_qualification_v13 import require_clifford_disjoint,AUTHOR,SYSTEM,SOURCE_SHA256,RAW_SHA256
from scripts.run_i02_clifford_cpg_once import load_package,preflight,execute,require_execution_grant
from scripts.serious_eval_full_source_arms_v9 import FullSourceWorkspaceV9

class CliffordCalibrationTests(unittest.TestCase):
    def test_whole_source_equal_native_reasoning_and_no_h_effect(self):
        p=load_package();g,arms=preflight(p);item=json.loads(SOURCE.read_text())
        self.assertLess(g['all_phase_peak_reservation_usd'],p['budget_cap_usd'])
        self.assertEqual(len(item['source_text']),56817)
        for phase in ('C','P','G_map'):
            u=json.loads(arms[phase][-1]['content']);self.assertEqual(u['sources'],[dict(source_id='ordinary-source',text=item['source_text'])]);self.assertEqual(u['question'],item['ordinary_question'])
            self.assertNotIn('obligations',u);self.assertNotIn('expert_gold',u)
        self.assertTrue(all(s['thinking']=={'type':'enabled'} and s['reasoning_effort']=='high' and s['max_tokens']==32768 for s in p['call_specs'].values()))
        self.assertEqual(p['maximum_provider_calls'],4);self.assertEqual(p['h_arm_calls'],0)
        self.assertFalse(g['source_gate']['h_specialized_treatment_present']);self.assertFalse(g['source_gate']['independent_confirmation_qualified'])
    def test_pinned_complete_reconstruction_and_no_silent_normalization(self):
        rawpath=os.environ.get('HCL_CLIFFORD_RAW');rdfpath=os.environ.get('HCL_CLIFFORD_RDF')
        if not rawpath or not rdfpath:self.skipTest('pinned external edition unavailable locally; cloud required')
        raw,rdf=Path(rawpath).read_bytes(),Path(rdfpath).read_bytes()
        self.assertEqual(reconstruct(raw,rdf),json.loads(SOURCE.read_text())['source_text']);self.assertTrue(audit(raw,rdf)['publisher_reconstruction_verified'])
        for r,d in ((raw.replace(b'\r\n',b'\n'),rdf),(raw,rdf+b'x')):
            with self.assertRaises(ValueError):reconstruct(r,d)
    def test_drift_and_owner_grant_limits_fail_before_transport(self):
        p=load_package()
        for field,v in [('budget_cap_usd',1.31),('maximum_provider_calls',5),('h_arm_calls',1),('hcl_runtime_sha256','bad')]:
            q=copy.deepcopy(p);q[field]=v
            with self.assertRaises(ValueError):preflight(q)
        with self.assertRaises(ValueError):require_execution_grant(p)
    def test_development_author_and_exact_hash_excluded_under_renaming(self):
        for c in ({'author_id':AUTHOR},{'writing_system_id':SYSTEM},{'source_sha256':SOURCE_SHA256},{'source_sha256':RAW_SHA256},{'source_text':json.loads(SOURCE.read_text())['source_text'],'author_id':'renamed'}):
            with self.assertRaises(ValueError):require_clifford_disjoint(c)
        self.assertTrue(require_clifford_disjoint({'source_text':'unrelated eligible candidate still needs v12 qualification'}))
    def test_generic_map_revision_invalidates_without_adding_gold(self):
        item=json.loads(SOURCE.read_text());w=FullSourceWorkspaceV9(dict(sources=[dict(source_id='ordinary-source',text=item['source_text'])]))
        quote=json.loads(OBLIGATIONS.read_text())['obligations'][0]['source_quotes'][0]['quote']
        mapped=json.dumps(dict(source_index=[dict(id='e1',source_id='ordinary-source',quote=quote)],relations=[],answer_plan=[],open_questions=[]))
        w.ingest(mapped);w.revise_source('ordinary-source','changed source')
        with self.assertRaises(ValueError):w.ingest(mapped)
    def test_composition_one_shot_full_source_and_closed_budget(self):
        p=load_package();item=json.loads(SOURCE.read_text());calls=[]
        quote=json.loads(OBLIGATIONS.read_text())['obligations'][0]['source_quotes'][0]['quote']
        def provider(req):
            calls.append(req)
            body=json.dumps(dict(source_index=[dict(id='e1',source_id='ordinary-source',quote=quote)],relations=[],answer_plan=[],open_questions=[])) if len(calls)==3 else json.dumps(dict(answer='Stub only; not semantic evidence.',source_citations=[],uncertainty='Unreviewed.',assumptions='Source-bounded.'))
            return dict(model=p['model'],created=1790786000,usage=dict(prompt_tokens=100,completion_tokens=100,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=100),choices=[dict(finish_reason='stop',message=dict(content=body))])
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'r.json';r=execute(p,provider,out)
            self.assertEqual(len(calls),4);self.assertEqual(r['authorization_remaining_usd'],0);self.assertEqual(r['budget_state'],'CLOSED_NO_TRANSFER_NO_RERUN')
            self.assertEqual(json.loads(calls[-1]['messages'][-1]['content'])['sources'],[dict(source_id='ordinary-source',text=item['source_text'])])
            with self.assertRaises(ValueError):execute(p,provider,out)
            self.assertEqual(len(calls),4);self.assertNotIn('semantic_scores',r)
    def test_unavailable_transport_no_retry_and_preserved_request(self):
        p=load_package();calls=[]
        def provider(req):calls.append(req);raise RuntimeError('simulated unavailable')
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'r.json'
            with self.assertRaises(RuntimeError):execute(p,provider,out)
            r=json.loads(out.read_text());self.assertEqual(len(calls),1);self.assertEqual(r['authorization_remaining_usd'],0);self.assertIsNone(r['estimated_actual_cost_usd']);self.assertIn('request_raw',r['attempts'][0])
    def test_bad_generic_map_skips_final_without_retry(self):
        p=load_package();calls=[]
        def provider(req):
            calls.append(req);body='{}' if len(calls)==3 else json.dumps(dict(answer='Stub only.',source_citations=[],uncertainty='',assumptions=''))
            return dict(model=p['model'],created=1790786000,usage=dict(prompt_tokens=100,completion_tokens=100,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=100),choices=[dict(finish_reason='stop',message=dict(content=body))])
        with tempfile.TemporaryDirectory() as d:
            r=execute(p,provider,Path(d)/'r.json');self.assertEqual(len(calls),3);self.assertEqual(r['status'],'G_MAP_INVALID_G_FINAL_NOT_CALLED');self.assertEqual(r['authorization_remaining_usd'],0)
if __name__=='__main__':unittest.main()
