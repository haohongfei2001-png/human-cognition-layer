"""Existing C03 composition actually enters final complete-source H input."""
import copy,json,unittest
from hcl.v1 import HCLCognitionLayer,prepare_person_context,PerspectiveMode
from hcl.v1.person_question import answer_person_context
from hcl.v1.long_source_question import prepare_long_source_context
from hcl.cognition.workspace import CognitionWorkspace
from hcl.cognition.agency import check_agency_candidates
from hcl.cognition.plan_feasibility import check_plan_candidates
Q='Could the reported plan work under the expressed belief and source-declared model?'
G='Mina said: "I want to protect the gate."'
P='Mina said: "I plan to call Noor in order to protect the gate if the gate is clear."'
O='Mina said: "I have an opportunity to call Noor."'
B='Mina said: "I believe the gate is clear."'
M='Narrator: In the declared model, it is false that the gate is clear.'
def source(*lines):return 'Ordinary authored development archive.\r\n'*700+'\r\n'+'\r\n'.join(lines)
def prepare(s,**kw):return prepare_person_context(HCLCognitionLayer(lambda _:None),Q,s,**kw)
def payload(p):return json.loads(p.messages[-1]['content'])
def plan(p):return payload(p)['checked_plan_feasibility'][0]['plans'][0]
class LongPlanCompositionTests(unittest.TestCase):
    def test_positive_belief_model_divergence_in_actual_final_input_without_knowing_failure(self):
        s=source(G,P,O,B,M);p=prepare(s);row=plan(p)
        self.assertEqual(row['subjective_feasibility'],'SUPPORTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(row['model_condition_check'],'MODEL_CONDITION_CONTRADICTED')
        self.assertEqual(row['relation'],'BELIEF_MODEL_DIVERGENCE_NOT_KNOWING_INFEASIBILITY')
        self.assertEqual(row['deliberate_impossibility'],'NOT_INFERRED');self.assertEqual(row['world_feasibility'],'NOT_ESTABLISHED')
        self.assertEqual(payload(p)['sources'][0]['text'],s)
        self.assertIn('checked_epistemic',payload(p));self.assertIn('checked_agency',payload(p))
        c=payload(p)['checked_plan_feasibility'][0]
        self.assertNotIn('original_sources',c);self.assertNotIn('agency',c)
        import hashlib
        expected=hashlib.sha256(json.dumps(payload(p)['checked_agency'][0]['cognition'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        self.assertEqual(c['shared_agency_reference']['cognition_sha256'],expected)
        self.assertEqual(c['shared_source_references'][0]['source_id'],'ordinary-source')
        self.assertGreaterEqual(len(row['support_claim_ids']),3)
        projected=payload(p)['checked_agency'][0]['evidence']
        audit=p.preparation_receipt['agency_derivation_audits'][0]['evidence']
        self.assertEqual(projected['spans'],audit['spans'])
        self.assertEqual(projected['claim_support_status'],{r['id']:r['support_status'] for r in audit['claims']})
        self.assertTrue(projected['conditional_premises'])
    def test_model_claim_or_knowledge_exposure_other_actor_attribution_never_fills_belief(self):
        for b in (None,B.replace('I believe','I know'),B.replace('I believe','I heard'),B.replace('Mina','Noor'),'Noor said: "Mina believes the gate is clear."','If '+B):
            p=prepare(source(G,P,O,*([b] if b else []),M.replace('false','true')))
            self.assertEqual(plan(p)['declared_model_condition'],'DECLARED_CONDITION_MET')
            self.assertEqual(plan(p)['subjective_condition'],'UNKNOWN')
            self.assertEqual(plan(p)['subjective_feasibility'],'BELIEF_CONDITION_UNRESOLVED')
    def test_denial_uncertainty_and_conflicts_not_negation_or_permission(self):
        p=prepare(source(G,P,O,B.replace('I believe','I do not believe'),M))
        self.assertEqual(plan(p)['subjective_condition'],'NOT_AFFIRMED_NOT_NEGATION')
        p=prepare(source(G,P,O,B.replace('I believe','I am unsure whether'),M))
        self.assertEqual(plan(p)['subjective_condition'],'UNRESOLVED')
        p=prepare(source(G,P,O,B,B.replace('I believe','I believe it is false that'),M,M.replace('false','true')))
        self.assertEqual(plan(p)['subjective_condition'],'CONFLICT');self.assertEqual(plan(p)['declared_model_condition'],'CONFLICT')
        self.assertEqual(plan(p)['subjective_feasibility'],'BELIEF_CONDITION_UNRESOLVED')
    def test_explicit_revision_changes_dependent_condition_and_preserves_previous_input(self):
        s=source(G,P,O,B,M);old=prepare(s);saved=copy.deepcopy(old.messages)
        new=prepare(s+'\r\nMina said: "I now believe it is false that the gate is clear instead of the gate is clear."')
        self.assertEqual(old.messages,saved)
        self.assertEqual(plan(new)['subjective_feasibility'],'CONTRADICTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(plan(new)['values_change'],'NOT_INFERRED')
        c=payload(new)['checked_plan_feasibility'][0]
        self.assertIn('REPORTED_CHARACTER_REVISION',str(c['belief_transition_receipts']))
        self.assertIn('ORDINAL_SOURCE_ORDER',c['temporal_assumption'])
    def test_typographic_ordinary_source_and_revision_remain_exact_no_rewritten_timeline(self):
        s=source('\r\n\r\n'.join(['_Mina._ We wait by the gate.']*60+['_Mina._ I want to protect the gate.','_Mina._ I plan to call Noor in order to protect the gate if the gate is clear.','_Mina._ I have an opportunity to call Noor.','_Mina._ I believe the gate is clear.',M,'_Mina._ I now believe it is false that the gate is clear instead of the gate is clear.']))
        p=prepare(s);self.assertEqual(payload(p)['sources'][0]['text'],s)
        self.assertEqual(plan(p)['subjective_feasibility'],'CONTRADICTED_UNDER_REPORTED_BELIEFS')
        candidates=payload(p)['cognitive_candidates']
        self.assertTrue(any(r['proposal'].get('utterance','').startswith('I now believe') for r in candidates))
        self.assertTrue(all(r['source_quote'] in s for r in candidates))
    def test_hnew_preserves_b01_c01_and_selection_and_removes_only_c03_state(self):
        s=source(G,P,O,B,M);h=prepare_long_source_context(Q,s);n=prepare_long_source_context(Q,s,plan_checks=False)
        left,right=payload(h),payload(n);left.pop('checked_plan_feasibility');self.assertEqual(left,right)
        self.assertEqual(h.preparation_receipt['agency_treatment'],n.preparation_receipt['agency_treatment'])
        self.assertEqual(h.preparation_receipt['epistemic_treatment'],n.preparation_receipt['epistemic_treatment'])
        self.assertEqual(n.preparation_receipt['plan_feasibility_treatment']['checked_plans'],0)
        self.assertIn('checked_agency',right);self.assertIn('checked_epistemic',right)
    def test_private_access_model_authority_and_candidate_budgets_fail_without_upgrade(self):
        p=prepare(source(G,P,O,B,M),perspective_mode=PerspectiveMode.OBSERVER_ABOUT_TARGET,observer_actor='Noor')
        self.assertNotIn('the gate is clear',json.dumps(p.messages))
        p=prepare(source(G,P,O,B,M.replace('Narrator:','Noor:')))
        self.assertEqual(plan(p)['declared_model_condition'],'UNKNOWN')
        with self.assertRaisesRegex(ValueError,'belief/model plan statement budget'):
            prepare(source('\r\n\r\n'.join(['_Mina._ I want to protect the gate.',
                '_Mina._ I plan to call Noor in order to protect the gate if the gate is clear.',
                '_Mina._ I have an opportunity to call Noor.']+
                [f'_Mina._ I believe condition {i}.' for i in range(17)])))
    def test_shared_agency_core_scope_source_version_and_live_support(self):
        w=CognitionWorkspace();w.put_source('s','\n'.join((G,P,O,B,M)))
        sem=w.prepare_semantic(Q,source_ids=('s',));a=check_agency_candidates(w,Q,sem,source_id='s',actor='Mina',only_agency_events=True)
        r=check_plan_candidates(w,Q,sem,a,source_id='s',actor='Mina',relevant_events_only=True)
        self.assertTrue(r.payload['plans']);w.core.withdraw(a.claim_ids[0])
        with self.assertRaisesRegex(ValueError,'support changed'):check_plan_candidates(w,Q,sem,a,source_id='s',actor='Mina')
        with self.assertRaises(ValueError):r.messages(w,include_sources=False)
    def test_forged_agency_payload_cannot_upgrade_source_or_plan_condition(self):
        from dataclasses import replace
        w=CognitionWorkspace();w.put_source('s','\n'.join((G,P,O,B,M)))
        sem=w.prepare_semantic(Q,source_ids=('s',));a=check_agency_candidates(w,Q,sem,source_id='s',actor='Mina',only_agency_events=True)
        bad=a.payload;bad['plans'][0]['opportunity']='REPORTED_UNAVAILABLE'
        with self.assertRaisesRegex(ValueError,'grounded join'):
            check_plan_candidates(w,Q,sem,replace(a,payload_json=json.dumps(bad)),source_id='s',actor='Mina')
        bad=a.payload;bad['original_sources'][0]['text']='Unrelated private source.'
        with self.assertRaisesRegex(ValueError,'source or actor'):
            check_plan_candidates(w,Q,sem,replace(a,payload_json=json.dumps(bad)),source_id='s',actor='Mina')

    def test_one_final_answer_smoke_no_second_extraction_or_actual_efficacy_claim(self):
        calls=[];s=source(G,P,O,B,M)
        r=answer_person_context(HCLCognitionLayer(lambda m:calls.append(m) or 'development stub'),Q,s,debug=True)
        self.assertEqual(len(calls),1);self.assertIn('checked_plan_feasibility',payload(r.prepared))
        self.assertEqual(r.prepared.preparation_receipt['extraction_provider_calls'],0)
        self.assertFalse(r.prepared.preparation_receipt['plan_feasibility_treatment']['answer_gain_established'])
if __name__=='__main__':unittest.main()
