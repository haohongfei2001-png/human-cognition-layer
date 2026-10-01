"""Optional exact identity encoding: cost/capacity, never inference/utility proof."""
import copy,json,unittest
from hcl.cognition import CognitionWorkspace
from hcl.v1.compact import compact_reader_context,expand_reader_context,READER_ENCODING
from tests.test_v1_conditional_reader_entry import SOURCE,QUERY,QUOTES,Backend,proposals

class ReaderContextCostTests(unittest.TestCase):
    def workspace(self,text=SOURCE):
        w=CognitionWorkspace();w.put_source('meeting',text);return w
    def prepare(self,w=None,**kw):
        return (w or self.workspace()).prepare_reader_semantic(QUERY,source_ids=('meeting',),backend=Backend(),**kw)
    def test_exact_round_trip_and_original_sources_remain_literal(self):
        w=self.workspace();before=self.prepare(w);after=self.prepare(w,compact_context=True)
        p=json.loads(before.messages[-1]['content']);q=json.loads(after.messages[-1]['content'])
        self.assertEqual(expand_reader_context(q),p);self.assertEqual(q['sources'],p['sources'])
        self.assertEqual(before.operation_ids,after.operation_ids);self.assertEqual(before.scope,after.scope)
        self.assertEqual(q['conditional_cognition']['encoding'],READER_ENCODING)
        self.assertLess(len(after.messages[-1]['content']),len(before.messages[-1]['content']))
        self.assertIn('Aliases add no evidence',after.messages[0]['content'])
        self.assertFalse(after.receipt['semantic_certification'])
    def test_positive_one_final_call_original_citation_unchanged(self):
        raw=json.dumps(dict(answer='A conditional plan is reported.',source_citations=[QUOTES[1]],uncertainty='Unverified translation.',assumptions='No private truth.'));calls=[];b=Backend()
        a=self.workspace().answer_reader_semantic(QUERY,lambda m:calls.append(m) or raw,source_ids=('meeting',),backend=b,compact_context=True)
        self.assertEqual(a['answer'],raw);self.assertEqual(a['answer_raw'],raw)
        self.assertEqual(len(calls),1);self.assertEqual(len(b.calls),1)
        self.assertTrue(a['source_citation_audit']['deliverable']);self.assertEqual(calls,[a['actual_final_messages']])
    def test_default_wire_unencoded_and_no_existing_codec_changes(self):
        r=self.prepare();p=json.loads(r.messages[-1]['content'])
        self.assertNotIn('encoding',p['conditional_cognition']);self.assertFalse(r.receipt['compact_context'])
        self.assertEqual(expand_reader_context(p),p)
    def test_budget_applies_after_lossless_encoding_original_retained(self):
        plain=self.prepare();compact=self.prepare(compact_context=True)
        bound=len(compact.messages[-1]['content']);self.assertLess(bound,len(plain.messages[-1]['content']))
        with self.assertRaises(ValueError):self.prepare(max_chars=bound)
        accepted=self.prepare(compact_context=True,max_chars=bound)
        self.assertEqual(json.loads(accepted.messages[-1]['content'])['sources'][0]['text'],SOURCE)
        with self.assertRaises(ValueError):self.prepare(compact_context=True,max_chars=bound-1)
    def test_revision_invalidates_alias_context_and_recomposes_condition(self):
        w=self.workspace();old=self.prepare(w,compact_context=True)
        correction='Dana corrected the belief: the gate is not clear.';w.put_source('meeting',SOURCE+'\n'+correction)
        with self.assertRaises(ValueError):old.current_messages(w)
        rows=proposals()+[dict(source_id='meeting',quote=correction,kind='event',content=dict(canonical_statement='Dana: I now believe it is false that the gate is clear instead of the gate is clear.'))]
        new=w.prepare_reader_semantic(QUERY,source_ids=('meeting',),backend=Backend(rows),compact_context=True)
        p=expand_reader_context(json.loads(new.messages[-1]['content']))
        self.assertEqual(p['conditional_cognition']['state']['checked_plan_feasibility'][0]['plans'][0]['subjective_feasibility'],'CONTRADICTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(p['sources'][0]['version'],2)
    def test_refuses_derived_citations_and_private_world_moral_upgrade(self):
        raw=json.dumps(dict(answer='The person spoke literally.',source_citations=['Dana: I want to protect the gate.'],uncertainty='',assumptions=''));a=self.workspace().answer_reader_semantic(QUERY,lambda _:raw,source_ids=('meeting',),backend=Backend(),compact_context=True)
        self.assertFalse(a['source_citation_audit']['deliverable']);self.assertEqual(a['answer_raw'],raw)
        p=expand_reader_context(json.loads(a['actual_final_messages'][-1]['content']))
        self.assertEqual(p['conditional_cognition']['state']['checked_plan_feasibility'][0]['plans'][0]['deliberate_impossibility'],'NOT_INFERRED')
        for k in ('semantic_certification','world_truth_established','private_state_established'):self.assertFalse(a['prepared'].receipt[k])
    def test_unauthorized_access_and_cross_actor_source_fail_before_candidate(self):
        w=CognitionWorkspace();w.put_source('private',SOURCE,permitted_observers=('Dana',));b=Backend()
        with self.assertRaises(ValueError):w.prepare_reader_semantic(QUERY,source_ids=('private',),observer='Noor',backend=b,compact_context=True)
        self.assertFalse(b.calls)
        with self.assertRaises(ValueError):w.prepare_reader_semantic(QUERY,source_ids=('private','other'),backend=b,compact_context=True)
        self.assertFalse(b.calls)
    def test_collision_namespace_falls_back_and_input_is_not_mutated(self):
        p=json.loads(self.prepare().messages[-1]['content']);old=copy.deepcopy(p);q=compact_reader_context(p)
        self.assertEqual(p,old);p['shared_semantic_binding']['unresolved_source_text']='@HCL_ID_0'
        self.assertEqual(compact_reader_context(p),p)
        with self.assertRaises(ValueError):compact_reader_context(q)
    def test_decoder_rejects_corrupt_unknown_duplicate_and_key_collision(self):
        q=json.loads(self.prepare(compact_context=True).messages[-1]['content']);table=q['conditional_cognition']['opaque_identity_refs'];first=next(iter(table))
        for mutation in ('unknown','duplicate','bad','key_collision'):
            x=copy.deepcopy(q);t=x['conditional_cognition']['opaque_identity_refs']
            if mutation=='unknown':x['shared_semantic_binding']['operation_ids'].append('@HCL_ID_99999')
            if mutation=='duplicate':t['@HCL_ID_99999']=t[first]
            if mutation=='bad':t[first]='a moral truth'
            if mutation=='key_collision':x['conditional_cognition']['state']={first:True,t[first]:False}
            with self.assertRaises(ValueError,msg=mutation):expand_reader_context(x)
    def test_negation_unknown_time_source_assumptions_and_hash_ids_round_trip(self):
        p=json.loads(self.prepare().messages[-1]['content']);state=p['conditional_cognition']['state']
        state['boundary_fixture']=dict(negated=False,unknown=None,empty=[],condition='not p',source='other',actor='Noor',calendar_time='UNKNOWN',access='UNKNOWN',normative_premise='CALLER_CONDITIONAL_ONLY')
        q=compact_reader_context(p);self.assertEqual(expand_reader_context(q),p)
        self.assertEqual(q['conditional_cognition']['state']['boundary_fixture'],state['boundary_fixture'])
    def test_small_no_duplicates_falls_back_with_no_reference_overhead(self):
        p=dict(sources=[dict(text='original')],conditional_cognition=dict(state=dict(unknown=None)),shared_semantic_binding={})
        self.assertEqual(compact_reader_context(p),p)

if __name__=='__main__':unittest.main()
