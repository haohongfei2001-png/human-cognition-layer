import copy,hashlib,json,unittest
from hcl.cognition.core import Scope
from hcl.cognition.semantic import AuthorizedText
from hcl.v1 import HCLCognitionLayer,answer_person_context
from scripts.serious_eval_source_reference_v1 import SourceReferenceIndex
from scripts.serious_eval_full_source_arms_v10 import prepare_primary_arms_v10,prepare_generic_final_v10,resolve_final_references,digest,answer_h_with_shared_references,prepare_h_with_shared_references
from scripts.serious_eval_full_source_arms_v9 import prepare_primary_arms_v9,prepare_generic_final_v9
from scripts.serious_eval_semantic_score import validate_answer
S='Mina: I do not believe\r\nthat the plan is safe.\r\nJo: I am unsure whether the plan is safe.'
Q='Which positions are reported, and what remains unproved?'
def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def raw_answer(quote):return json.dumps(dict(answer='The source reports an outer denial, not belief in the opposite.',source_citations=[dict(source_id='s',quote=quote)],uncertainty='Private belief and world truth unproved.',assumptions='Reported expression only.'))
class SourceReferenceTests(unittest.TestCase):
    def index(self,text=S,version=1,**kwargs):
        s=AuthorizedText('s',text,version=version,**kwargs);return SourceReferenceIndex((s,),Scope(source_ids=('s',)))
    def locate(self,index,text=S,version=1,quote='I do not believe that the plan is safe.'):
        return index.locate('s',quote,expected_version=version,expected_sha256=sha(text))
    def test_positive_original_span_bytes_and_raw_proposal_separated(self):
        row=self.locate(self.index());self.assertEqual(row['quote'],'I do not believe\r\nthat the plan is safe.');self.assertEqual(S[row['start']:row['end']],row['quote']);self.assertEqual(row['proposed_quote'],'I do not believe that the plan is safe.');self.assertFalse(row['semantic_support_certified']);self.assertEqual(row['method'],'UNIQUE_WHITESPACE_EQUIVALENT_SOURCE_SPAN')
    def test_exact_priority_and_ambiguity_fail_closed(self):
        self.assertEqual(self.locate(self.index(),quote='Jo: I am unsure')['method'],'UNIQUE_EXACT_SOURCE_SUBSTRING')
        for text,quote in [('Mina knows p.\nMina knows p.','Mina knows p.'),('Mina knows\np.\nMina knows\t p.','Mina knows p.')]:
            with self.assertRaises(ValueError):self.locate(self.index(text),text=text,quote=quote)
    def test_negation_actor_punctuation_case_and_hyphen_never_changed(self):
        for quote in ['I believe that the plan is safe.','Jo: I do not believe that the plan is safe.','i do not believe that the plan is safe.','I do not believe that the plan is safe!','I do not believe that the plan is safer.']:
            with self.assertRaises(ValueError):self.locate(self.index(),quote=quote)
        with self.assertRaises(ValueError):self.locate(self.index('Infor-\nmation remains uncertain.'),text='Infor-\nmation remains uncertain.',quote='Information remains uncertain.')
    def test_bounds_include_retrieved_original_span_and_visible_bytes(self):
        text='A'+' '*1499+'B'
        with self.assertRaises(ValueError):self.locate(self.index(text),text=text,quote='A B')
        for quote in ('','   ','x'*1501):
            with self.assertRaises(ValueError):self.locate(self.index(),quote=quote)
        with self.assertRaises(ValueError):self.index('文'*166667)
    def test_source_boundary_private_time_order_and_no_hidden_metadata(self):
        hidden=AuthorizedText('secret','Mina knows\nprivate fact.',permitted_observers=('Mina',),access_time='2026-09-30T12:00:00Z',order=2)
        public=AuthorizedText('s',S,permitted_observers=('Jo',),access_time='2026-09-30T10:00:00Z')
        scope=Scope(source_ids=('s','secret'),observer='Jo',access_time='2026-09-30T11:00:00Z',through_order=1)
        index=SourceReferenceIndex((public,hidden),scope);self.assertEqual(set(index.versions()),{'s'})
        with self.assertRaises(ValueError):index.locate('secret','private fact',expected_version=1,expected_sha256=sha(hidden.text))
        row=self.locate(index);self.assertEqual(row['scope_id'],scope.id);self.assertNotIn('secret',json.dumps(row))
        no=SourceReferenceIndex((AuthorizedText('s',S,access_time=None),),Scope(source_ids=('s',),access_time='2026-09-30T11:00:00Z'));self.assertEqual(no.versions(),{})
    def test_multiple_sources_remain_distinct_and_code_layout_not_semantically_certified(self):
        sources=(AuthorizedText('a','Mina does not\nbelieve p.'),AuthorizedText('b','Jo believes p.'))
        index=SourceReferenceIndex(sources,Scope(source_ids=('a','b')))
        with self.assertRaises(ValueError):index.locate('b','Mina does not believe p.',expected_version=1,expected_sha256=sha(sources[1].text))
        row=index.locate('a','Mina does not believe p.',expected_version=1,expected_sha256=sha(sources[0].text));self.assertEqual(row['source_id'],'a')
        code='if allowed:\n    send()\nrevoke()'
        row=self.locate(self.index(code),text=code,quote='if allowed: send() revoke()');self.assertEqual(row['quote'],code);self.assertFalse(row['semantic_support_certified'])
    def test_source_version_revision_invalidates_stale_binding(self):
        before=self.locate(self.index());revised=S.replace('safe','uncertain');after=self.index(revised,version=2)
        with self.assertRaises(ValueError):self.locate(after)
        with self.assertRaises(ValueError):self.locate(after,text=revised,version=1)
        self.assertEqual(self.locate(after,text=revised,version=2,quote='I do not believe that the plan is uncertain.')['source_version'],2)
        self.assertEqual(before['quote'],'I do not believe\r\nthat the plan is safe.')
    def test_equal_whole_inputs_and_versioned_generic_map_composition(self):
        p=prepare_primary_arms_v10(Q,'s',S);u=p['ordinary_payload']
        for arm in ('C','P','G_map'):self.assertEqual(json.loads(p[arm][-1]['content']),u)
        raw=json.dumps(dict(source_index=[dict(id='e1',source_id='s',quote='I do not believe that the plan is safe.')],relations=[],answer_plan=[dict(operation='RETRIEVE',evidence_ids=['e1'])],open_questions=[]))
        final=prepare_generic_final_v10(p,raw);v=json.loads(final['messages'][-1]['content']);self.assertEqual(v['sources'],u['sources']);self.assertEqual(v['question'],Q);self.assertEqual(final['reference_receipt']['raw_map'],raw);self.assertFalse(final['reference_receipt']['semantic_qualification'])
        for field,value in [('sources',[dict(source_id='s',text=S),dict(source_id='s2',text='extra')]),('question','changed')]:
            bad=copy.deepcopy(p);bad['ordinary_payload'][field]=value
            with self.assertRaises(ValueError):prepare_generic_final_v10(bad,raw)
    def test_oracle_fields_and_invalid_generic_relation_still_rejected(self):
        p=prepare_primary_arms_v10(Q,'s',S)
        for map in [dict(source_index=[dict(id='e1',source_id='s',quote='I do not believe that the plan is safe.',private_truth=True)],relations=[],answer_plan=[],open_questions=[]),dict(source_index=[dict(id='e1',source_id='s',quote='I do not believe that the plan is safe.')],relations=[dict(from_id='e1',to_id='e2',kind='SUPPORTS')],answer_plan=[],open_questions=[])]:
            with self.assertRaises(ValueError):prepare_generic_final_v10(p,json.dumps(map))
    def test_final_vocabulary_and_raw_answer_preserved_for_c_p_g_h(self):
        raw=raw_answer('I do not believe that the plan is safe.')
        for method in ('C','P','G','H'):
            out=resolve_final_references(raw,[dict(source_id='s',text=S)]);validate_answer(out['answer'],{'s':S});self.assertEqual(set(out['answer']),{'answer','source_citations','uncertainty','assumptions'});self.assertEqual(out['reference_receipt']['raw_answer'],raw);self.assertEqual(out['answer']['answer'],json.loads(raw)['answer'])
        for source in ([dict(source_id='other',text=S)],):
            with self.assertRaises(ValueError):resolve_final_references(raw,source)
        with self.assertRaises(ValueError):resolve_final_references('{"answer":"x","answer":"y"}',[dict(source_id='s',text=S)])
    def test_ordinary_h_one_final_stub_preserves_actual_cognition_source(self):
        source='_Mina._ I do not believe\r\nthat Jo believes the plan is safe.\r\n\r\n'+('Ordinary neutral background. '*650)
        calls=[]
        def model(messages):
            calls.append(messages);return json.dumps(dict(answer='Outer denial does not establish Jo’s inner denial.',source_citations=[dict(source_id='ordinary-source',quote='I do not believe that Jo believes the plan is safe.')],uncertainty='Private and world truth unproved.',assumptions='Source-reported expression.'))
        out=answer_h_with_shared_references(HCLCognitionLayer(model),Q,source);self.assertEqual(len(calls),1);u=json.loads(calls[0][-1]['content']);self.assertEqual(u['sources'][0]['text'],source);self.assertTrue(out['prepared'].preparation_receipt['specialized_cognition_treatment'])
        resolved=out['result'];self.assertIn('common read-only source-reference locator',calls[0][0]['content']);self.assertEqual(resolved['answer']['source_citations'][0]['quote'],'I do not believe\r\nthat Jo believes the plan is safe.')
    def test_shared_policy_cannot_overrun_existing_h_context_bound(self):
        from hcl.v1 import prepare_person_context
        source='Ordinary background. '*900;layer=HCLCognitionLayer(lambda _: '')
        old=prepare_person_context(layer,Q,source);bound=len(json.dumps(list(old.messages),ensure_ascii=False))+2
        with self.assertRaises(ValueError):prepare_h_with_shared_references(layer,Q,source,max_context_chars=bound)
    def test_h_resource_never_reintroduces_private_caller_source(self):
        from hcl.v1 import PerspectiveMode
        source='Mina: private report. '+('secret background. '*1000)
        calls=[]
        layer=HCLCognitionLayer(lambda m:calls.append(m))
        with self.assertRaises(ValueError):answer_h_with_shared_references(layer,Q,source,perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET,observer_actor='Jo')
        self.assertEqual(calls,[])
    def test_historical_v9_and_exact_scorer_still_refuse_layout_rewrite(self):
        raw=raw_answer('I do not believe that the plan is safe.')
        with self.assertRaises(ValueError):validate_answer(json.loads(raw),{'s':S})
        map=json.dumps(dict(source_index=[dict(id='e1',source_id='s',quote='I do not believe that the plan is safe.')],relations=[],answer_plan=[],open_questions=[]))
        with self.assertRaises(ValueError):prepare_generic_final_v9(prepare_primary_arms_v9(Q,'s',S),map)
if __name__=='__main__':unittest.main()
