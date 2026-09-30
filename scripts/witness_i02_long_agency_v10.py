"""Actual ordinary final input: a reported plan with contradicted opportunity."""
import argparse,hashlib,json
from pathlib import Path
from hcl.v1 import HCLCognitionLayer,prepare_person_context
from hcl.v1.long_source_question import prepare_long_source_context
from scripts.serious_eval_contract import runtime_digest

def witness():
    source='Ordinary authored development archive.\r\n'*700+'\r\n'+ '\r\n\r\n'.join(['_Mina._ We wait by the gate.']*60+['_Mina._ I want to protect the gate.','_Mina._ I plan to call Noor in order to protect the gate.','_Mina._ I have no opportunity to call Noor.','_Noor._ I believe the gate is open.'])
    query='Which reported goals and plans are supported, and what prevents pursuit?'
    def prohibited(_):raise AssertionError('no provider in correctness witness')
    h=prepare_person_context(HCLCognitionLayer(prohibited),query,source)
    hn=prepare_long_source_context(query,source,agency_checks=False)
    hp,np=(json.loads(x.messages[-1]['content']) for x in (h,hn))
    checked=hp.pop('checked_agency');assert hp==np
    assert hp['sources'][0]['text']==source
    assert checked[0]['cognition']['plans'][0]['pursuit_check']=='OPPORTUNITY_CONTRADICTED'
    assert checked[0]['cognition']['goals'][0]['status']=='ACTIVE'
    assert checked[0]['cognition']['plans'][0]['private_intention']=='NOT_VERIFIED'
    assert hn.preparation_receipt['epistemic_treatment']['checked_mental_expressions']==h.preparation_receipt['epistemic_treatment']['checked_mental_expressions']
    assert hn.preparation_receipt['agency_treatment']['checked_operations']==0
    sha=lambda x:hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return dict(schema='hcl-i02-long-agency-v10-witness-v1',CAPABILITY_DELTA='Ordinary complete long text now reuses C01 goal/plan/opportunity joins in actual H final input, distinguishing an active reported goal and selected plan from unavailable opportunity, without establishing private intent, success, moral permission or actual event chronology. B01 and source preparation are shared; H-new removes only C01 checked state.',origin='HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY',source_chars=len(source),source_sha256=hashlib.sha256(source.encode()).hexdigest(),runtime_sha256=runtime_digest(),h_receipt=h.preparation_receipt,h_new_receipt=hn.preparation_receipt,h_input_sha256=sha(h.messages),h_new_input_sha256=sha(hn.messages),equal_source_query_candidates_selection_b01=True,treatment_input_differs=h.messages!=hn.messages,positive_witness='ACTIVE_REPORTED_GOAL_SELECTED_PLAN_BUT_OPPORTUNITY_CONTRADICTED',private_intention_established=False,answer_gain_established=False,confirmation_qualified=False,provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    Path(a.output).write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n');print('LONG_READER_C01_PROVIDER_FREE_WITNESS')
