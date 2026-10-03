"""Source-neutral ordinary dialogue: existing B01 reaches final H with exact spans."""
import copy,json,unittest
from hcl.v1 import HCLCognitionLayer,prepare_person_context,PerspectiveMode
from hcl.v1.person_question import answer_person_context
from hcl.v1.long_source_question import prepare_long_source_context
from hcl.cognition.core import EvidenceCore,Scope
from hcl.cognition.semantic import AuthorizedText,prepare_semantics
from hcl.cognition.epistemic import check_epistemic_candidates,MentalProposition
from scripts.serious_eval_full_source_arms_v9 import prepare_primary_arms_v9

Q='How do the reported views differ and what is unproved?'
def source(dialogue):return 'Ordinary development archive record.\r\n'*700+'\r\n'+dialogue
def payload(p):return json.loads(p.messages[-1]['content'])
def prepare(s,**kw):return prepare_person_context(HCLCognitionLayer(lambda _:None),Q,s,**kw)
def objects(p):return payload(p)['checked_epistemic']['epistemic_objects']
class TypographicDialogueTests(unittest.TestCase):
    def test_positive_multiline_named_nested_denial_and_separate_knowledge(self):
        s=source('_Mina._ I do not believe Noor believes the gate\r\nis open.\r\n\r\n_Noor._ I believe the gate\r\nis open.\r\n\r\n_Kai._ I know the gate is open.\r\n')
        p=prepare(s);rows=objects(p)
        self.assertEqual(payload(p)['sources'][0]['text'],s)
        self.assertEqual(p.preparation_receipt['dialogue_selection']['selected_modal_candidates'],3)
        self.assertTrue(p.preparation_receipt['specialized_cognition_treatment'])
        first=rows[0]['public_expression']['expressed_content']
        self.assertEqual((first['holder'],first['polarity']),('Mina','DENY'))
        self.assertEqual((first['content']['holder'],first['content']['polarity']),('Noor','AFFIRM'))
        self.assertEqual(rows[2]['public_expression']['expressed_content']['attitude'],'KNOWLEDGE_CLAIM')
        self.assertIsNone(rows[2]['private_interpretation'])
        for r in rows:self.assertIn(r['public_expression']['original_quote'],s)
        checked=prepare_person_context(HCLCognitionLayer(lambda _:None),'What does Mina believe Noor believes?',s)
        proj=payload(checked)['checked_epistemic']['query_projection'][0]
        self.assertEqual(proj['result'],'OUTER_ATTRIBUTION_DENIED');self.assertEqual(proj['world_truth'],'NOT_ESTABLISHED')
    def test_heading_role_is_source_local_and_pronoun_or_embedded_direction_not_resolved(self):
        s=source('_She._ I believe the gate is open.\n\n_Mina._ [imagining] I believe the gate is open.\n\n_Noor._ "I believe the gate is open."\n\n_Kai._ I believe the gate is open. [Aside.]\n')
        p=prepare(s);self.assertNotIn('checked_epistemic',payload(p));self.assertFalse(p.preparation_receipt['specialized_cognition_treatment'])
        for row in payload(p)['cognitive_candidates']:
            self.assertNotEqual(row['proposal'].get('speaker_surface'),'guessed-human')
    def test_hypothetical_scene_preamble_keeps_expression_unsettled(self):
        p=prepare(source('Hypothetical dialogue:\n\n_Mina._ I believe the gate is open.'))
        self.assertFalse(p.preparation_receipt['specialized_cognition_treatment'])
        self.assertNotIn('checked_epistemic',payload(p))

    def test_runtime_chain_rejects_new_digest_or_previous_digest_drift(self):
        from pathlib import Path
        from scripts.i02_runtime_amendment_v9 import validate_runtime_amendment_v9
        from scripts.development_universal_agency_chain_amendment import validate_current
        self.assertTrue(validate_current())
        names=['HCL_I01_EVALUATION_FREEZE.json','HCL_I02_RUNTIME_AMENDMENT.json']+[f'HCL_I02_RUNTIME_AMENDMENT_V{i}.json' for i in range(2,10)]
        chain=[json.loads(Path('reports',n).read_text()) for n in names]
        certified_v9=chain[-1]['amended_hcl_runtime_sha256']
        self.assertTrue(validate_runtime_amendment_v9(*chain,current_digest=certified_v9))
        for field in ('amended_hcl_runtime_sha256','previous_hcl_runtime_sha256'):
            bad=copy.deepcopy(chain);bad[-1][field]='0'*64
            with self.assertRaisesRegex(ValueError,'v9 runtime amendment'):validate_runtime_amendment_v9(*bad,current_digest=certified_v9)

    def test_explicit_access_filter_and_no_event_time_from_layout(self):
        core=EvidenceCore();r=prepare_semantics(Q,(AuthorizedText('a','_Mina._ I believe the gate is open.',permitted_observers=('Mina',)),),core=core,scope=Scope(observer='Noor',source_ids=('a',)),dialogue_blocks=True,modal_events_only=True)
        self.assertFalse(r.candidate_ids);self.assertNotIn('gate',json.dumps(r.messages))
        core=EvidenceCore();r=prepare_semantics(Q,(AuthorizedText('a','_Mina._ I believe the gate is open.\n\n_Noor._ I heard the gate is open.'),),core=core,dialogue_blocks=True,modal_events_only=True)
        self.assertEqual(len(check_epistemic_candidates(core,Q,r).records),2)
        for c in json.loads(r.messages[-1]['content'])['cognitive_candidates']:
            self.assertIsNone(c['proposal']['event_time']);self.assertIsNone(c['proposal']['access_time'])
        p=prepare(source('_Mina._ I believe the gate is open.'),perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET,observer_actor='Noor')
        self.assertNotIn('gate',json.dumps(p.messages))
    def test_declared_selection_keeps_every_modal_event_without_ordinary_dialogue_quota_loss(self):
        s=source('\n\n'.join(['_Mina._ We wait by the gate.']*60+['_Mina._ I believe the gate is open.','_Noor._ I do not believe the gate is open.']))
        p=prepare(s);sel=p.preparation_receipt['dialogue_selection']
        self.assertEqual(sel['discovered_speech_events'],62);self.assertEqual(sel['selected_modal_candidates'],2)
        self.assertTrue(sel['every_eligible_event_retained']);self.assertFalse(sel['complete_speech_analysis'])
        self.assertEqual(payload(p)['sources'][0]['text'],s)
        with self.assertRaisesRegex(ValueError,'no_silent_truncation'):
            prepare(source('\n\n'.join(['_Mina._ I believe the gate is open.']*65)))
    def test_hnew_same_selection_source_and_vocabulary_and_comparator_composition(self):
        s=source('_Mina._ I believe the gate is open.\n\n_Noor._ I do not believe the gate is open.')
        h=prepare_long_source_context(Q,s);n=prepare_long_source_context(Q,s,epistemic_checks=False)
        left,right=payload(h),payload(n);left.pop('checked_epistemic');self.assertEqual(left,right)
        self.assertEqual(h.preparation_receipt['dialogue_selection'],n.preparation_receipt['dialogue_selection'])
        arms=prepare_primary_arms_v9(Q,'ordinary-source',s)
        for arm in ('C','P','G_map'):
            row=json.loads(arms[arm][-1]['content']);self.assertEqual(row['sources'][0]['text'],s);self.assertEqual(row['question'],Q)
        self.assertIn('answer, source_citations, uncertainty',h.messages[0]['content'])
    def test_source_revision_and_one_answer_smoke_do_not_reuse_old_interpretation(self):
        s=source('_Mina._ I believe the gate is open.\n\n_Noor._ I heard the gate is open.')
        old=prepare(s);before=copy.deepcopy(old.messages);new=prepare(s.replace('_Mina._ I believe','_Mina._ I do not believe'))
        self.assertEqual(old.messages,before)
        self.assertEqual(objects(old)[0]['public_expression']['expressed_content']['polarity'],'AFFIRM')
        self.assertEqual(objects(new)[0]['public_expression']['expressed_content']['polarity'],'DENY')
        self.assertEqual(objects(old)[1]['public_expression']['expressed_content'],objects(new)[1]['public_expression']['expressed_content'])
        calls=[]
        r=answer_person_context(HCLCognitionLayer(lambda m:calls.append(m) or 'development stub'),Q,s,debug=True)
        self.assertEqual(len(calls),1);self.assertIn('checked_epistemic',payload(r.prepared))
        self.assertEqual(r.prepared.preparation_receipt['extraction_provider_calls'],0)
    def test_legacy_default_backend_and_literal_forms_unchanged(self):
        script='_Mina._ I believe the gate is open.'
        self.assertFalse(prepare_semantics(Q,(AuthorizedText('a',script),)).candidate_ids)
        for text in ('Mina: I believe the gate is open.','Mina said: "I believe the gate is open."'):
            c=EvidenceCore();r=prepare_semantics(Q,(AuthorizedText('a',text),),core=c)
            self.assertIsInstance(check_epistemic_candidates(c,Q,r).records[0].tree,MentalProposition)
        with self.assertRaises(ValueError):prepare_semantics(Q,(AuthorizedText('a',script),),dialogue_blocks='yes')
if __name__=='__main__':unittest.main()
