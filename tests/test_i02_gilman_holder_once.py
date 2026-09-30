import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import run_i02_gilman_holder_once as run
from scripts.i02_source_holder_review import validate_review, messages

SOURCE='Earlier Mina trusted the plan. Middle Mina challenged the plan. Later Mina declined the plan.'


def review():
    quotes=['Earlier Mina trusted the plan.','Middle Mina challenged the plan.','Later Mina declined the plan.']
    return dict(family_judgment='PASS',answerability_judgment='PASS',
        episodes=[dict(id='e'+str(i),quote=q,evidence_kind='NARRATOR_REPORT',time_basis='SOURCE_ORDER_ONLY',analysis='A reported change, not a motive.') for i,q in enumerate(quotes)],
        obligations=[dict(id='o'+str(i),expectation=e,quote=quotes[i],audit_question='Keep the reported perspective.') for i,e in enumerate(('STATE','QUALIFY','AVOID'))],
        serious_unsupported_upgrades=['Unsupported private motive.'],unresolved_limits=['Story time uncertain.'],judge_limits='Automated, not independent human truth.')


class HolderOnceTests(unittest.TestCase):
    def setUp(self):
        self.p=run.load_package();self.p['source_sha256']=run.sha(SOURCE.encode())
        self.g=dict(status='READY_FOR_SOURCE_FIRST_HOLDER_REVIEW',source_sha256=self.p['source_sha256'],
            history=dict(checkout_head='current',status='REACHABLE_HISTORY_NO_TEXT_MATCH'),
            snapshot=dict(repository_commit='current',status='TEXT_SNAPSHOT_NO_MATCH'))

    def test_exact_quote_positive_uncertainty_and_negative_inference_contract(self):
        result=validate_review(review(),SOURCE)
        self.assertFalse(result['semantic_truth_verified']);self.assertFalse(result['story_time_semantics_verified'])
        self.assertFalse(result['confirmation_qualified'])
        value=review();value['episodes'][0]['quote']='Mina intends harm.'
        with self.assertRaises(ValueError):validate_review(value,SOURCE)
        value=review();value['episodes'].reverse()
        with self.assertRaises(ValueError):validate_review(value,SOURCE)
        value=review();value['obligations'][2]['expectation']='STATE'
        with self.assertRaises(ValueError):validate_review(value,SOURCE)

    def test_ordinary_complete_input_and_no_architecture_or_gold(self):
        p=json.loads(messages('fixture-only',SOURCE)[-1]['content'])
        self.assertEqual(p['sources'],[dict(source_id='fixture-only',text=SOURCE)])
        self.assertEqual(set(p),{'question','sources'})
        revised=SOURCE.replace('Later Mina declined the plan.','Later Mina joined the plan.')
        with self.assertRaises(ValueError):validate_review(review(),revised)

    def test_stale_history_and_cap_prevent_any_call(self):
        with patch.object(run,'build_package',return_value=self.p),patch.object(run,'current_head',return_value='current'):
            bad=copy.deepcopy(self.g);bad['history']['checkout_head']='stale'
            with self.assertRaises(ValueError):run.prepare(self.p,SOURCE,bad)
            self.p['budget_cap_usd']=0.000001
            with self.assertRaises(ValueError):run.prepare(self.p,SOURCE,self.g)

    def test_single_call_raw_preserved_metadata_redacted_no_rerun(self):
        calls=[]
        def provider(request):
            calls.append(request)
            return dict(model=self.p['model'],created=1790784000,
                usage=dict(prompt_tokens=100,completion_tokens=100,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=100,other=SOURCE),
                choices=[dict(finish_reason='stop',message=dict(content=json.dumps(review()),reasoning_content=SOURCE))])
        with tempfile.TemporaryDirectory() as d, patch.object(run,'build_package',return_value=self.p),patch.object(run,'current_head',return_value='current'):
            raw=Path(d)/'raw.json';meta=Path(d)/'meta.json'
            result=run.execute(self.p,SOURCE,self.g,provider,raw,meta)
            self.assertEqual(result['status'],'COMPLETED_PRELIMINARY_ONLY')
            self.assertEqual(len(calls),1);self.assertNotIn(SOURCE,meta.read_text())
            self.assertNotIn('quote',json.dumps(result['preliminary_review']))
            self.assertIn(SOURCE,raw.read_text());self.assertEqual(result['authorization_remaining_usd'],0)
            self.assertEqual(result['raw_receipt_sha256'],run.sha(raw.read_bytes()))
            with self.assertRaises(ValueError):run.execute(self.p,SOURCE,self.g,provider,raw,meta)
            self.assertEqual(len(calls),1)

    def test_transport_and_interface_failures_close_without_retry_or_hidden_content(self):
        for kind in ('connection','shape'):
            calls=[]
            def provider(request):
                calls.append(request)
                if kind=='connection':raise RuntimeError(SOURCE)
                return dict(model=self.p['model'],usage=dict(prompt_tokens=1,completion_tokens=1),choices=[dict(finish_reason='stop',message=dict(content='{}'))])
            with tempfile.TemporaryDirectory() as d,patch.object(run,'build_package',return_value=self.p),patch.object(run,'current_head',return_value='current'):
                raw=Path(d)/'r.json';meta=Path(d)/'m.json'
                result=run.execute(self.p,SOURCE,self.g,provider,raw,meta)
                self.assertEqual(len(calls),1);self.assertEqual(result['status'],'FAILED_NO_RETRY')
                self.assertEqual(result['budget_state'],'CLOSED_NO_TRANSFER_NO_RERUN')
                self.assertNotIn(SOURCE,meta.read_text())

    def test_historical_grants_not_reused_and_execution_freeze_drift_denied(self):
        p=run.load_package()
        self.assertEqual(p['maximum_provider_calls'],1);self.assertEqual(p['budget_cap_usd'],.18)
        self.assertFalse(p['historical_budget_transfer']);self.assertEqual(p['h_calls'],0)
        with patch.object(run,'build_package',return_value={}):
            with self.assertRaises(ValueError):run.load_package()

if __name__=='__main__':unittest.main()
