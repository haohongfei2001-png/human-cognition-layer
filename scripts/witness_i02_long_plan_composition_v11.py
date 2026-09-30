"""Actual final C03 join, H-new and local revision on authored complete source."""
import argparse,hashlib,json
from pathlib import Path
from hcl.v1 import HCLCognitionLayer,prepare_person_context
from hcl.v1.long_source_question import prepare_long_source_context
from scripts.serious_eval_contract import runtime_digest

def witness():
    source='Ordinary authored development archive.\r\n'*700+'\r\n'+ '\r\n\r\n'.join(['_Mina._ We wait by the gate.']*60+['_Mina._ I want to protect the gate.','_Mina._ I plan to call Noor in order to protect the gate if the gate is clear.','_Mina._ I have an opportunity to call Noor.','_Mina._ I believe the gate is clear.','Narrator: In the declared model, it is false that the gate is clear.'])
    query='Could the reported plan work under the expressed belief and source-declared model?'
    def prohibited(_):raise AssertionError('no provider in correctness witness')
    h=prepare_person_context(HCLCognitionLayer(prohibited),query,source)
    hn=prepare_long_source_context(query,source,plan_checks=False)
    hp,np=(json.loads(x.messages[-1]['content']) for x in (h,hn))
    checked=hp.pop('checked_plan_feasibility');assert hp==np
    plan=checked[0]['plans'][0]
    assert plan['subjective_feasibility']=='SUPPORTED_UNDER_REPORTED_BELIEFS'
    assert plan['model_condition_check']=='MODEL_CONDITION_CONTRADICTED'
    assert plan['relation']=='BELIEF_MODEL_DIVERGENCE_NOT_KNOWING_INFEASIBILITY'
    assert hp['sources'][0]['text']==source
    assert hn.preparation_receipt['plan_feasibility_treatment']['checked_plans']==0
    revised=prepare_person_context(HCLCognitionLayer(prohibited),query,source+'\r\n\r\n_Mina._ I now believe it is false that the gate is clear instead of the gate is clear.')
    new=json.loads(revised.messages[-1]['content'])['checked_plan_feasibility'][0]['plans'][0]
    assert new['subjective_feasibility']=='CONTRADICTED_UNDER_REPORTED_BELIEFS'
    sha=lambda x:hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return dict(schema='hcl-i02-long-plan-composition-v11-witness-v1',CAPABILITY_DELTA='Complete ordinary-source H now composes existing C01 plan state with source-reported belief/revision and an explicit source-declared model through C03. It distinguishes subjective support from model contradiction without knowing infeasibility, intended failure, private truth or value change; explicit revision updates the dependent condition. H-new retains B01/C01/source/candidates and drops C03 alone.',origin='HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY',source_chars=len(source),source_sha256=hashlib.sha256(source.encode()).hexdigest(),runtime_sha256=runtime_digest(),h_receipt=h.preparation_receipt,h_new_receipt=hn.preparation_receipt,revision_receipt=revised.preparation_receipt,h_input_sha256=sha(h.messages),h_new_input_sha256=sha(hn.messages),equal_source_query_candidates_selection_b01_c01=True,treatment_input_differs=h.messages!=hn.messages,positive_witness='SUBJECTIVE_PLAN_SUPPORT_AND_DECLARED_MODEL_CONTRADICTION_NOT_KNOWING_FAILURE',positive_revision_witness='EXPLICIT_REPORTED_REVISION_CHANGES_DEPENDENT_CONDITION',world_feasibility_established=False,knowing_infeasibility_established=False,answer_gain_established=False,confirmation_qualified=False,provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    Path(a.output).write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n');print('LONG_READER_C03_COMPOSITION_PROVIDER_FREE_WITNESS')
