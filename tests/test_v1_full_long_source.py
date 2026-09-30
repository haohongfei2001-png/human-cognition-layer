import json,unittest
from hcl.v1 import HCLCognitionLayer,prepare_person_context,PerspectiveMode
from hcl.cognition.semantic import AuthorizedText,prepare_semantics
SOURCE='Mina said: "I believe the plan is safe."\r\n'+('Neutral complete-source office record.\r\n'*5000)+'Mina said: "I am unsure whether the plan is safe."'
Q='How did the reported position change and what is unproved?'
class FullLongSourceTests(unittest.TestCase):
    def layer(self):return HCLCognitionLayer(lambda _: 'stub only')
    def test_ordinary_complete_long_input_reported_states_not_private_truth(self):
        p=prepare_person_context(self.layer(),Q,SOURCE);u=json.loads(p.messages[-1]['content'])
        self.assertEqual(u['query'],Q);self.assertEqual(u['sources'][0]['text'],SOURCE)
        self.assertEqual(sum(r['kind']=='event' for r in u['cognitive_candidates']),2)
        self.assertGreaterEqual(p.preparation_receipt['candidate_count'],2)
        self.assertTrue(p.preparation_receipt['specialized_cognition_treatment']);self.assertEqual(p.preparation_receipt['extraction_provider_calls'],0)
        self.assertEqual(p.preparation_receipt['method'],'complete_long_source_local_evidence_v2')
        self.assertIn('not sincerity',p.messages[0]['content']);self.assertIn('private belief',p.messages[0]['content'])
    def test_default_semantic_bound_unchanged_and_explicit_local_bound_composes(self):
        with self.assertRaises(ValueError):prepare_semantics(Q,(AuthorizedText('s',SOURCE),))
        p=prepare_semantics(Q,(AuthorizedText('s',SOURCE),),max_source_chars=250000)
        self.assertEqual(p.backend_calls,0);self.assertEqual(json.loads(p.messages[-1]['content'])['sources'][0]['text'],SOURCE)
    def test_source_utf8_context_and_candidate_bounds_refuse_without_truncation(self):
        for source in ('x'*250001,'文'*200000):
            with self.assertRaises(ValueError):prepare_person_context(self.layer(),Q,source)
        with self.assertRaises(ValueError):prepare_person_context(self.layer(),Q,SOURCE,max_context_chars=64000)
        many='\r\n'.join('Mina said: "Report '+str(i)+'."' for i in range(100))+'x'*50000
        with self.assertRaises(ValueError):prepare_person_context(self.layer(),Q,many)
    def test_private_access_and_time_norm_scope_never_receive_raw_long_source(self):
        for kwargs in (dict(perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET,observer_actor='Mina'),dict(as_of_statement=1),dict(premise_scope='FOCAL_EPISODE')):
            p=prepare_person_context(self.layer(),Q,SOURCE,**kwargs)
            self.assertNotIn(SOURCE,json.dumps(p.messages,ensure_ascii=False))
    def test_local_revision_does_not_mutate_prior_request_and_old_small_budget_remains(self):
        before=prepare_person_context(self.layer(),Q,SOURCE);revised=SOURCE.replace('the plan is safe','the plan is uncertain')
        after=prepare_person_context(self.layer(),Q,revised)
        self.assertEqual(json.loads(before.messages[-1]['content'])['sources'][0]['text'],SOURCE)
        self.assertEqual(json.loads(after.messages[-1]['content'])['sources'][0]['text'],revised)
        with self.assertRaises(ValueError):prepare_person_context(self.layer(),Q,'Mina: report.',max_context_chars=512000)
    def test_amendment_chain_fails_drift_and_historical_link(self):
        from scripts.development_runtime_amendment_v15 import validate_current
        self.assertTrue(validate_current())
if __name__=='__main__':unittest.main()
