"""Authored ordinary-source integration witness; zero provider transport."""
import json,hashlib,argparse
from pathlib import Path
from hcl.v1 import HCLCognitionLayer,prepare_person_context
from hcl.v1.long_source_question import prepare_long_source_context
from scripts.serious_eval_contract import runtime_digest

def witness():
    source=('Mina said: "I do not believe Noor believes the gate is open."\r\n'+
        'Neutral ordinary archive record.\r\n'*1800+
        'Noor said: "I am unsure whether the gate is open."\r\n'+
        'Kai said: "I know the gate is open."')
    question='What does Mina believe Noor believes?'
    def prohibited(_):raise AssertionError('no provider/model answer in correctness witness')
    h=prepare_person_context(HCLCognitionLayer(prohibited),question,source)
    hn=prepare_long_source_context(question,source,epistemic_checks=False)
    hp,np=(json.loads(x.messages[-1]['content']) for x in (h,hn))
    checked=hp.pop('checked_epistemic');assert hp==np
    assert hp['sources'][0]['text']==source
    assert checked['query_projection'][0]['result']=='OUTER_ATTRIBUTION_DENIED'
    assert checked['query_projection'][0]['unprojected_inner_state']=='NO_INNER_POLARITY_INFERENCE'
    assert h.preparation_receipt['specialized_cognition_treatment']
    assert not hn.preparation_receipt['specialized_cognition_treatment']
    def fingerprint(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return dict(schema='hcl-i02-long-epistemic-v8-witness-v1',CAPABILITY_DELTA='Ordinary complete long reader text now invokes existing B01 grounded modal checking and transmits checked source-reported objects, outer/inner scope and explicit unknown private truth; H-new keeps the same complete source/candidates and removes only this mechanism.',origin='HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY',source_chars=len(source),source_sha256=hashlib.sha256(source.encode()).hexdigest(),query_sha256=hashlib.sha256(question.encode()).hexdigest(),runtime_sha256=runtime_digest(),h_receipt=h.preparation_receipt,h_new_receipt=hn.preparation_receipt,h_input_sha256=fingerprint(h.messages),h_new_input_sha256=fingerprint(hn.messages),equal_source_query_candidates=True,treatment_input_differs=h.messages!=hn.messages,positive_witness='OUTER_ATTRIBUTION_DENIED_NOT_INNER_DENIAL',specialized_mechanism='B01_EXISTING_MODAL_SCOPE_CHECKER',specialized_treatment_present=True,private_state_established=False,answer_gain_established=False,independent_semantic_qualification=False,confirmation_qualified=False,provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    Path(a.output).write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n');print('LONG_READER_B01_INTEGRATION_PROVIDER_FREE_WITNESS')
