import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts import run_i02_gaskell_holder_once as run
from scripts.i02_source_holder_line_index_v3 import sha,index_source
from scripts.i02_source_holder_typed_contract_v4 import messages,resolve_review_v4
SOURCE='Mina said: "I support this plan."\r\nMina said: "I am uncertain about this plan."\r\nMina said: "I decline this plan."'

def review():
    return dict(source_id=run.holder.load_package()['source_id'],source_sha256=sha(SOURCE),question_sha256=sha(run.holder.QUESTION),
        family_judgment='PASS',answerability_judgment='PASS',
        episodes=[dict(id='e'+str(i),start_line=i,end_line=i,evidence_kind='REPORTED_SPEECH',time_basis='SOURCE_ORDER_ONLY',analysis='Source report, not private motive.') for i in range(1,4)],
        obligations=[dict(id='o'+str(i),expectation=e,start_line=i,end_line=i,audit_question='Preserve report and uncertainty.') for i,e in enumerate(('STATE','QUALIFY','AVOID'),1)],
        serious_unsupported_upgrades=['Unproved intention.'],unresolved_limits=['Story time uncertain.'],judge_limits='Automated preliminary only.')

class GaskellHolderTests(unittest.TestCase):
    def setUp(self):
        self.p=run.load_package();self.p['source_sha256']=sha(SOURCE)
        self.g=dict(status='READY_FOR_DEVELOPMENT_SOURCE_HOLDER_REVIEW',source_sha256=sha(SOURCE),history=dict(checkout_head='current',status='REACHABLE_HISTORY_NO_TEXT_MATCH'),snapshot=dict(repository_commit='current',status='TEXT_SNAPSHOT_NO_MATCH'))
    def test_complete_input_no_gold_and_uncertainty_revision_refusal(self):
        payload=json.loads(messages(run.holder.QUESTION,run.holder.load_package()['source_id'],SOURCE)[-1]['content'])
        self.assertEqual(''.join(x['text'] for x in payload['sources'][0]['lines']),SOURCE)
        self.assertNotIn('expected_episode_lines',payload)
        got=resolve_review_v4(review(),run.holder.QUESTION,run.holder.load_package()['source_id'],SOURCE,index_source(run.holder.load_package()['source_id'],SOURCE))
        self.assertFalse(got['semantic_truth_verified']);self.assertFalse(got['story_time_verified'])
        with self.assertRaises(ValueError):resolve_review_v4(review(),'revised question',run.holder.load_package()['source_id'],SOURCE,index_source(run.holder.load_package()['source_id'],SOURCE))
    def test_stale_history_and_cap_stop_transport(self):
        with patch.object(run,'build_package',return_value=self.p),patch.object(run,'current_head',return_value='current'):
            g=copy.deepcopy(self.g);g['history']['checkout_head']='stale'
            with self.assertRaises(ValueError):run.prepare(self.p,SOURCE,g)
            self.p['budget_cap_usd']=.000001
            with self.assertRaises(ValueError):run.prepare(self.p,SOURCE,self.g)
    def test_single_call_raw_preserved_metadata_has_no_quote_analysis_or_reasoning(self):
        calls=[]
        def provider(request):
            calls.append(request);r=review();r['episodes'][0]['analysis']=SOURCE
            return dict(model=self.p['model'],created=1790784000,usage=dict(prompt_tokens=100,completion_tokens=100,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=100,other=SOURCE),choices=[dict(finish_reason='stop',message=dict(content=json.dumps(r),reasoning_content=SOURCE))])
        with tempfile.TemporaryDirectory() as d,patch.object(run,'build_package',return_value=self.p),patch.object(run,'current_head',return_value='current'):
            raw=Path(d)/'raw.json';meta=Path(d)/'meta.json';got=run.execute(self.p,SOURCE,self.g,provider,raw,meta)
            self.assertEqual(got['status'],'COMPLETED_PRELIMINARY_ONLY');self.assertEqual(len(calls),1)
            self.assertNotIn(SOURCE,meta.read_text());self.assertNotIn('quote',json.dumps(got['preliminary_review']));self.assertNotIn('analysis',json.dumps(got['preliminary_review']))
            self.assertIn('resolved_review',json.loads(raw.read_text()));self.assertEqual(got['raw_receipt_sha256'],sha(raw.read_text()))
            self.assertEqual(got['authorization_remaining_usd'],0)
            with self.assertRaises(ValueError):run.execute(self.p,SOURCE,self.g,provider,raw,meta)
            self.assertEqual(len(calls),1)
    def test_transport_bad_enum_and_length_close_without_rerun(self):
        for kind in ('transport','enum','length'):
            calls=[]
            def provider(request):
                calls.append(request)
                if kind=='transport':raise RuntimeError(SOURCE)
                r=review();r['obligations'][0]['expectation']='State the report in prose.'
                return dict(model=self.p['model'],usage=dict(prompt_tokens=1,completion_tokens=1),choices=[dict(finish_reason='length' if kind=='length' else 'stop',message=dict(content=json.dumps(r)))])
            with tempfile.TemporaryDirectory() as d,patch.object(run,'build_package',return_value=self.p),patch.object(run,'current_head',return_value='current'):
                got=run.execute(self.p,SOURCE,self.g,provider,Path(d)/'r',Path(d)/'m')
                self.assertEqual(got['status'],'FAILED_NO_RETRY');self.assertEqual(len(calls),1);self.assertEqual(got['authorization_remaining_usd'],0)
                self.assertNotIn(SOURCE,(Path(d)/'m').read_text())
    def test_preview_author_exclusion_before_old_history_or_rights_gate(self):
        from scripts.i02_source_qualification_v11 import require_qualified_confirmation_source_v11
        for c in ({'author_id':'elizabeth-gaskell'},{'author_id':'edith-wharton'},{'writing_system_id':'elizabeth-gaskell-original-english-framed-fiction'},{'template_id':'complete-person-other-choice-development-question-v2'}):
            with patch('scripts.i02_source_qualification_v11.require_qualified_confirmation_source_v10') as old:
                with self.assertRaises(ValueError):require_qualified_confirmation_source_v11({},c,{},'.','HEAD')
                old.assert_not_called()
    def test_fixed_new_budget_and_package_drift_not_historical_transfer(self):
        p=run.load_package();self.assertEqual(p['maximum_provider_calls'],1);self.assertEqual(p['budget_cap_usd'],1.10);self.assertFalse(p['historical_budget_transfer'])
        self.assertFalse(p['confirmation_qualified']);self.assertEqual(p['h_calls'],0)
        with patch.object(run,'build_package',return_value={}):
            with self.assertRaises(ValueError):run.load_package()
if __name__=='__main__':unittest.main()
