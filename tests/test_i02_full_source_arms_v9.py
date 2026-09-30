import copy,json,unittest
from scripts.serious_eval_full_source_arms_v9 import prepare_primary_arms_v9,prepare_generic_final_v9,FullSourceWorkspaceV9
from scripts.serious_eval_arms_v8 import prepare_primary_arms_v8
SOURCE='Mina said: "I support the plan."\r\n'+('The complete source contains a neutral office log entry.\r\n'*4200)+'Mina said: "I am uncertain about the plan."'
Q='How did the reported position change and what remains unproved?'
def mapped():return dict(source_index=[dict(id='e1',source_id='s',quote='Mina said: "I support the plan."'),dict(id='e2',source_id='s',quote='Mina said: "I am uncertain about the plan."')],relations=[dict(from_id='e2',to_id='e1',kind='QUALIFIES')],answer_plan=[dict(operation='COMPARE',evidence_ids=['e1','e2'])],open_questions=['Private intention is not established.'])
class FullSourceArmsTests(unittest.TestCase):
    def test_complete_long_ordinary_input_same_contract_and_old_envelope_retained(self):
        self.assertGreater(len(SOURCE),217526)
        with self.assertRaises(ValueError):prepare_primary_arms_v8(Q,'s',SOURCE)
        p=prepare_primary_arms_v9(Q,'s',SOURCE)
        f=prepare_generic_final_v9(p,json.dumps(mapped()))
        for m in [p['C'],p['P'],p['G_map'],f]:
            u=json.loads(m[-1]['content']);self.assertEqual(u['question'],Q);self.assertEqual(u['sources'],[dict(source_id='s',text=SOURCE)])
            self.assertEqual(u['answer_fields'],p['ordinary_payload']['answer_fields'])
        self.assertFalse(p['semantic_qualification']);self.assertEqual(p['provider_calls_authorized'],0)
        self.assertEqual(p['accounting']['G_map_calls'],1);self.assertEqual(p['accounting']['G_final_calls'],1)
        for spec in p['call_specs'].values():self.assertEqual(spec['reasoning_effort'],'high');self.assertEqual(spec['thinking'],dict(type='enabled'))
    def test_historical_short_policies_and_ordinary_h_refusal_remain_explicit(self):
        short='Mina said: "I support the plan."'
        old=prepare_primary_arms_v8(Q,'s',short);new=prepare_primary_arms_v9(Q,'s',short)
        for phase in ('C','P'):self.assertEqual(old[phase],new[phase])
        from scripts.witness_i02_full_source_arms_v9 import witness
        got=witness();self.assertEqual(got['h_ordinary_entry_status'],'REFUSED_COMPLETE_LONG_SOURCE')
        self.assertEqual(got['old_v8_status'],'REFUSED_64K_ENVELOPE');self.assertEqual(got['provider_calls'],0)
        self.assertFalse(got['confirmation_qualified']);self.assertFalse(got['semantic_qualification'])
    def test_exact_generic_composition_and_no_source_to_private_state_promotion(self):
        p=prepare_primary_arms_v9(Q,'s',SOURCE);w=json.loads(prepare_generic_final_v9(p,json.dumps(mapped()))[-1]['content'])['generic_evidence_workspace']
        self.assertEqual(w['relation_semantics'],'UNVERIFIED_MODEL_PROPOSAL');self.assertEqual(w['quote_status'],'EXACT_UNIQUE_SOURCE_SPAN_CHECKED')
        for r in w['source_index']:self.assertEqual(SOURCE[r['start']:r['end']],r['quote'])
        bad=mapped();bad['source_index'][0]['private_intention']='harm'
        with self.assertRaises(ValueError):prepare_generic_final_v9(p,json.dumps(bad))
    def test_unsupported_sources_ranges_relations_and_ambiguity_refused(self):
        p=prepare_primary_arms_v9(Q,'s',SOURCE)
        for kind in ['source','quote','relation']:
            m=mapped()
            if kind=='source':m['source_index'][0]['source_id']='other'
            if kind=='quote':m['source_index'][0]['quote']='Mina knew the consequence.'
            if kind=='relation':m['relations'][0]['kind']='TRUE_INTENTION'
            with self.assertRaises(ValueError):prepare_generic_final_v9(p,json.dumps(m))
        duplicate=SOURCE+'\r\nMina said: "I support the plan."'
        with self.assertRaises(ValueError):prepare_generic_final_v9(prepare_primary_arms_v9(Q,'s',duplicate),json.dumps(mapped()))
    def test_revision_invalidates_map_preserves_unaffected_source_and_payload_mutation_refused(self):
        payload=dict(sources=[dict(source_id='s',text=SOURCE),dict(source_id='other',text='Other source unchanged.')])
        w=FullSourceWorkspaceV9(payload);w.ingest(json.dumps(mapped()));before=copy.deepcopy(w._sources['other'])
        w.revise_source('s',SOURCE+'\r\nNew report.');self.assertEqual(w._sources['other'],before)
        with self.assertRaises(ValueError):w.snapshot()
        w.ingest(json.dumps(mapped()));self.assertEqual(w.snapshot()['source_index'][0]['source_version'],2)
        p=prepare_primary_arms_v9(Q,'s',SOURCE);p['ordinary_payload']['question']='Different question'
        with self.assertRaises(ValueError):prepare_generic_final_v9(p,json.dumps(mapped()))
    def test_utf8_complete_source_and_total_map_bounds_fail_without_partial_replacement(self):
        for source in ['x'*500001,'文'*166667]:
            with self.assertRaises(ValueError):prepare_primary_arms_v9(Q,'s',source)
        w=FullSourceWorkspaceV9(dict(sources=[dict(source_id='s',text=SOURCE)]));w.ingest(json.dumps(mapped()))
        with self.assertRaises(ValueError):w.ingest(' '*24001)
        with self.assertRaises(ValueError):w.snapshot()
        with self.assertRaises(ValueError):w.revise_source('s','x'*500001)
        self.assertEqual(w._sources['s']['text'],SOURCE)
if __name__=='__main__':unittest.main()
