import copy,json,os,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
from scripts import development_reality_check as drc
from scripts.development_confirmation_firewall import require_final_development_disjoint,require_final_confirmation_source

class DevelopmentRealityChecks(unittest.TestCase):
    def test_actual_ordinary_entry_all_cases_full_input_no_gold_or_route_hints(self):
        for row in drc.load_cases()['cases']:
            with self.subTest(case=row['case_id']):
                arms,receipt=drc.prepare_case(row)
                self.assertEqual(set(arms),{'Base','HCL'})
                self.assertEqual(json.loads(arms['Base'][-1]['content'])['source'],row['source'])
                self.assertEqual(json.loads(arms['HCL'][-1]['content']),{'question':row['question'],'choices':row['choices']})
                self.assertEqual(receipt['actual_final_messages'],arms['HCL'])
                text=json.dumps(arms)
                self.assertNotIn('"gold"',text);self.assertNotIn(row['case_id'],text)
                self.assertEqual(drc.request(arms['Base'])['thinking'],{'type':'enabled'})
                self.assertEqual(drc.request(arms['HCL'])['max_tokens'],8192)

    def test_scorer_counts_native_label_only_and_invalid_truncated_missing_wrong(self):
        row={'choices':{'A':'one','B':'two'},'gold':'B'}
        def response(answer,finish='stop'):
            return {'choices':[{'finish_reason':finish,'message':{'content':json.dumps(dict(answer=answer,source_citations=[],uncertainty='',assumptions='dataset judgment, not moral truth'))}}]}
        self.assertTrue(drc.score(row,response('B'))['correct'])
        for raw in (response('A'),response('B','length'),response('b'),{},response('C')):
            self.assertFalse(drc.score(row,raw)['correct'])

    def test_final_isolation_system_url_and_renamed_exact_text(self):
        row=drc.load_cases()['cases'][0]
        for candidate in ({'dataset_id':'allenai/SimpleToM'},
                          {'source_url':'https://maartensap.com/social-iqa/data/socialIQa_v1.4.tgz'},
                          {'dataset_id':'renamed','source_text':row['source']}):
            with self.assertRaises(ValueError):require_final_development_disjoint(candidate)
        self.assertTrue(require_final_development_disjoint({'dataset_id':'unseen-other-system'}))
        with patch('scripts.i02_source_qualification_v14.require_qualified_confirmation_source_v14',side_effect=ValueError('old final gate')):
            with self.assertRaisesRegex(ValueError,'old final gate'):
                require_final_confirmation_source({}, {'dataset_id':'unseen-other-system'}, {}, '/tmp', 'revision')

    def test_frozen_source_local_revision_changes_only_local_receipt(self):
        row=copy.deepcopy(drc.load_cases()['cases'][0]);arms,before=drc.prepare_case(row)
        row['source']+=' A later correction is explicitly recorded.'
        revised,after=drc.prepare_case(row)
        self.assertNotEqual(arms,revised)
        self.assertIn(row['source'],json.loads(revised['Base'][-1]['content']).values())
        self.assertNotEqual(before['actual_final_messages'],after['actual_final_messages'])

    def test_no_retry_and_budget_closes_after_transport_failure(self):
        package={'arms':['Base','HCL'],'inputs':{'case':{'Base':[{'role':'user','content':'authorized source'}],'HCL':[{'role':'user','content':'same authorized source'}]}},'maximum_provider_calls':2,'budget_cap_usd':1,'model':'deepseek-v4-pro','maximum_output_tokens':8192,'runtime_sha256':'stub','evidence_level':'DEVELOPMENT_ONLY'}
        calls=[]
        def fail(req):calls.append(req);raise RuntimeError('transport failed')
        with tempfile.TemporaryDirectory() as tmp,patch.object(drc,'load_cases',return_value={'cases':[{'case_id':'case'}]}):
            output=Path(tmp)/'receipt.json'
            with self.assertRaises(RuntimeError):drc.execute(package,fail,output,{})
            receipt=json.loads(output.read_text())
            self.assertEqual(len(calls),1);self.assertEqual(receipt['authorization_remaining_usd'],0)
            self.assertEqual(receipt['status'],'FAILED_NO_RETRY')
            with self.assertRaises(ValueError):drc.execute(package,fail,output,{})

    def test_hard_cap_prevents_any_provider_call(self):
        package={'arms':['Base','HCL'],'inputs':{'case':{'Base':[{'role':'user','content':'source'}]}},'maximum_provider_calls':2,'budget_cap_usd':0,'model':'deepseek-v4-pro','runtime_sha256':'stub','evidence_level':'DEVELOPMENT_ONLY'}
        with tempfile.TemporaryDirectory() as tmp,patch.object(drc,'load_cases',return_value={'cases':[{'case_id':'case'}]}):
            with self.assertRaises(ValueError):drc.execute(package,lambda req:self.fail('must not call'),Path(tmp)/'r.json',{})

    def test_historical_clifford_consumed_grant_and_runtime_unchanged(self):
        old=json.loads(Path('.github/HCL_I02_CLIFFORD_CPG_GRANT.json').read_text())
        self.assertEqual(old['status'],'CLOSED');self.assertEqual(old['maximum_calls'],0)
        self.assertEqual(drc.runtime_digest(),'aa7fc08c1937ffef7eeb4dfa762c1f0e06eeb2bd414dcea71cde582b7b43e0c9')

    def test_history_inventory_does_not_materialize_checkout_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)/'source';repo.mkdir()
            def git(*args):
                return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL)
            git('init');(repo/'ordinary-public-file.txt').write_text('a harmless public fixture')
            git('add','ordinary-public-file.txt')
            git('-c','user.name=HCL Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture')
            baseline=git('rev-parse','HEAD').decode().strip()
            def audit(inventory,source):
                self.assertEqual({p.name for p in Path(inventory).iterdir()},{'.git'})
                self.assertEqual(subprocess.check_output(['git','-C',str(inventory),'config','core.abbrev']).decode().strip(),'40')
                self.assertEqual(subprocess.check_output(['git','-C',str(inventory),'rev-parse','HEAD']).decode().strip(),baseline)
                return {'matches':[],'status':'REACHABLE_HISTORY_NO_TEXT_MATCH'}
            case={'prior_history_baseline':baseline,'cases':[{'source':'ordinary authored source fixture'}]}
            with patch.object(drc,'load_cases',return_value=case),patch('scripts.i02_exposure_history.audit_history',side_effect=audit):
                result=drc.history_check(repo)
                self.assertEqual(result['matches'],[])

    def test_foreign_model_gold_source_or_message_drift_refused(self):
        p=drc.build_package();self.assertFalse(p['independent_reviewer_required'])
        self.assertEqual(p['maximum_provider_calls'],40);self.assertLess(p['all_call_peak_reservation_usd'],p['budget_cap_usd'])
        changed=copy.deepcopy(p);changed['inputs'][next(iter(changed['inputs']))]['Base'][0]['content']='hint'
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'changed.json';path.write_text(json.dumps(changed))
            with patch.object(drc,'PACKAGE',path):
                with self.assertRaises(ValueError):drc.load_package()

if __name__=='__main__':unittest.main()
