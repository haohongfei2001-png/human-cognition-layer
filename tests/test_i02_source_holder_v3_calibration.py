import copy,json
from pathlib import Path
import tempfile
import unittest
from scripts.i02_source_holder_v3_calibration_fixture import load_fixture,fixture_anchor_witness
from scripts import run_i02_source_holder_v3_calibration_once as run
from scripts.i02_source_holder_line_index_v3 import resolve_review,index_source


def literal_review(f):
    return dict(source_id=f['source_id'],source_sha256=f['source_sha256'],question_sha256=f['question_sha256'],family_judgment='PASS',answerability_judgment='PASS',
        episodes=[dict(id='e'+str(i),start_line=n,end_line=n,evidence_kind='REPORTED_SPEECH',time_basis='EXPLICIT_STORY_TIME',analysis='Mina reported a view; reporting date is not the episode date.') for i,n in enumerate(f['expected_episode_lines'])],
        obligations=[dict(id='o'+str(i),start_line=n,end_line=n,expectation=e,audit_question='Keep source report, uncertainty and unsupported intention separate.') for i,(n,e) in enumerate(zip(f['expected_episode_lines'],['STATE','QUALIFY','AVOID']))],
        serious_unsupported_upgrades=['Private intention or normative moral truth.'],unresolved_limits=['Only authored fixture literal records are available.'],judge_limits='This is not independent source or H efficacy evidence.')

class LongInterfaceCalibrationTests(unittest.TestCase):
    def test_long_ordinary_input_native_budget_and_gold_firewall(self):
        f=load_fixture();p=run.load_package();request,gate=run.preflight(p);payload=json.loads(request['messages'][-1]['content'])
        self.assertGreaterEqual(gate['source_characters'],80958)
        self.assertEqual(''.join(row['text'] for row in payload['sources'][0]['lines']),f['source_text'])
        self.assertNotIn('expected_episode_lines',json.dumps(payload))
        self.assertEqual(payload['question'],f['ordinary_question'])
        self.assertEqual(request['reasoning_effort'],'high');self.assertEqual(request['max_tokens'],16384)
        self.assertLessEqual(gate['peak_reservation_usd'],.38)
        self.assertFalse(gate['independent_source']);self.assertFalse(gate['confirmation_qualified'])
    def test_fixture_revision_and_source_question_contract_drift_denied(self):
        p=run.load_package();p['budget_cap_usd']=1
        with self.assertRaises(ValueError):run.preflight(p)
        f=load_fixture();v=literal_review(f);v['question_sha256']='0'*64
        with self.assertRaises(ValueError):resolve_review(v,f['ordinary_question'],f['source_id'],f['source_text'],index_source(f['source_id'],f['source_text']))
        v=literal_review(f);v['episodes'][1]['start_line']=9999
        with self.assertRaises(ValueError):resolve_review(v,f['ordinary_question'],f['source_id'],f['source_text'],index_source(f['source_id'],f['source_text']))
    def test_native_raw_receipt_resolution_fixture_witness_and_closed_no_second_call(self):
        f=load_fixture();p=run.load_package();calls=[]
        def provider(req):
            calls.append(req);return dict(model=p['model'],created=1790760000,usage=dict(prompt_tokens=1000,completion_tokens=1000,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=1000),choices=[dict(finish_reason='stop',message=dict(content=json.dumps(literal_review(f)),reasoning_content='authored fixture reasoning'))])
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'receipt.json';r=run.execute(p,provider,out)
            self.assertEqual(r['status'],'COMPLETED_LONG_INTERFACE_ONLY');self.assertEqual(len(calls),1)
            self.assertTrue(r['literal_fixture_witness']['all_declared_literal_episode_anchors_present'])
            self.assertFalse(r['literal_fixture_witness']['semantic_time_actor_normative_review_verified'])
            self.assertFalse(r['resolved_review']['semantic_truth_verified'])
            self.assertIn('request_raw',r);self.assertIn('response_raw',r)
            self.assertEqual(r['authorization_remaining_usd'],0);self.assertFalse(r['confirmation_qualified'])
            with self.assertRaises(ValueError):run.execute(p,provider,out)
            self.assertEqual(len(calls),1)
    def test_transport_or_incomplete_output_is_closed_without_retry(self):
        p=run.load_package()
        for kind in ['transport','incomplete']:
            calls=[]
            def provider(req):
                calls.append(req)
                if kind=='transport':raise RuntimeError('simulated unavailable')
                return dict(model=p['model'],usage=dict(prompt_tokens=1,completion_tokens=16384),choices=[dict(finish_reason='length',message=dict(content='{}'))])
            with tempfile.TemporaryDirectory() as d:
                out=Path(d)/'receipt.json';r=run.execute(p,provider,out)
                self.assertEqual(r['status'],'FAILED_NO_RETRY');self.assertEqual(len(calls),1)
                self.assertEqual(r['budget_state'],'CLOSED_NO_TRANSFER_NO_RERUN');self.assertEqual(r['authorization_remaining_usd'],0)
    def test_shape_success_without_declared_episodes_does_not_gain_literal_credit(self):
        f=load_fixture();v=literal_review(f)
        for i,row in enumerate(v['episodes']):row.update(start_line=i+2,end_line=i+2)
        got=resolve_review(v,f['ordinary_question'],f['source_id'],f['source_text'],index_source(f['source_id'],f['source_text']))
        self.assertFalse(fixture_anchor_witness(got,f)['all_declared_literal_episode_anchors_present'])
if __name__=='__main__':unittest.main()
