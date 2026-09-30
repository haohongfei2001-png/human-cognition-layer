import json
from pathlib import Path
import tempfile
import unittest
from scripts.i02_obp_metaethics_preflight import SOURCE, OBLIGATIONS
from scripts.run_i02_obp_metaethics_cpg_once import load_package, preflight, execute

class ConceptCalibrationTests(unittest.TestCase):
    def test_ordinary_source_fairness_and_absent_h_treatment(self):
        p=load_package();gate,arms=preflight(p);item=json.loads(SOURCE.read_text())
        self.assertLess(gate['all_phase_peak_reservation_usd'],p['budget_cap_usd'])
        for phase in ['C','P','G_map']:
            payload=json.loads(arms[phase][-1]['content'])
            self.assertEqual(payload['sources'],[dict(source_id=item['source_id'],text=item['source_text'])])
            self.assertEqual(payload['question'],item['ordinary_question'])
        self.assertFalse(gate['source_gate']['independent_confirmation_qualified'])
        self.assertFalse(gate['source_gate']['h_specialized_treatment_present'])
        self.assertTrue(all(s['thinking']['type']=='enabled' and s['max_tokens']==16384 for s in p['call_specs'].values()))
        self.assertEqual(p['maximum_provider_calls'],4)
        self.assertFalse(p['historical_budget_transfer'])

    def test_local_cap_revision_fails_frozen_contract(self):
        p=load_package();p['budget_cap_usd']=1
        with self.assertRaises(ValueError):preflight(p)

    def test_source_map_composition_and_one_shot_ledger(self):
        p=load_package();item=json.loads(SOURCE.read_text());calls=[]
        quote=json.loads(OBLIGATIONS.read_text())['obligations'][0]['source_quotes'][0]['quote']
        def provider(req):
            calls.append(req)
            content=json.dumps(dict(source_index=[dict(id='e1',source_id=item['source_id'],quote=quote)],relations=[],answer_plan=[],open_questions=[])) if len(calls)==3 else json.dumps(dict(answer='Under the reported theory, moral truth is denied.',uncertainty='Individual motives unknown.',assumptions='Exposition of source theory.',source_citations=[]))
            return dict(model=p['model'],created=1790746100,usage=dict(prompt_tokens=100,completion_tokens=100,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=100),choices=[dict(finish_reason='stop',message=dict(content=content))])
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'receipt.json';r=execute(p,provider,out)
            self.assertEqual(len(calls),4);self.assertEqual(r['authorization_remaining_usd'],0)
            self.assertEqual(r['budget_state'],'CLOSED_NO_TRANSFER_NO_RERUN')
            self.assertEqual(json.loads(calls[-1]['messages'][-1]['content'])['sources'],[dict(source_id=item['source_id'],text=item['source_text'])])
            with self.assertRaises(ValueError):execute(p,provider,out)
            self.assertEqual(len(calls),4)

    def test_interface_failure_closes_without_retry_or_semantic_claim(self):
        p=load_package();calls=[]
        def fail(req):calls.append(req);raise RuntimeError('simulated unavailable')
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'receipt.json'
            with self.assertRaises(RuntimeError):execute(p,fail,out)
            r=json.loads(out.read_text());self.assertEqual(len(calls),1)
            self.assertEqual(r['status'],'FAILED_NO_RETRY');self.assertEqual(r['authorization_remaining_usd'],0)
            self.assertNotIn('semantic_scores',r)

if __name__=='__main__':unittest.main()
