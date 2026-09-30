"""Synthetic complete input and actual final treatment; no paid transport."""
import argparse,hashlib,json
from pathlib import Path
from hcl.v1 import HCLCognitionLayer,prepare_person_context
from hcl.v1.long_source_question import prepare_long_source_context
from scripts.serious_eval_contract import runtime_digest

def witness():
    source='Ordinary authored development archive.\r\n'*700+'\r\n'+ '\r\n\r\n'.join(['_Mina._ We wait by the gate.']*60+['_Mina._ I do not believe Noor believes the gate\r\nis open.','_Noor._ I believe the gate\r\nis open.','_Kai._ I know the gate is open.'])
    query='What does Mina believe Noor believes?'
    def prohibited(_):raise AssertionError('provider forbidden in correctness witness')
    h=prepare_person_context(HCLCognitionLayer(prohibited),query,source)
    hn=prepare_long_source_context(query,source,epistemic_checks=False)
    hp,np=(json.loads(x.messages[-1]['content']) for x in (h,hn))
    checked=hp.pop('checked_epistemic');assert hp==np
    assert hp['sources'][0]['text']==source
    assert checked['query_projection'][0]['result']=='OUTER_ATTRIBUTION_DENIED'
    assert checked['query_projection'][0]['unprojected_inner_state']=='NO_INNER_POLARITY_INFERENCE'
    assert h.preparation_receipt['dialogue_selection']['discovered_speech_events']==63
    assert h.preparation_receipt['dialogue_selection']['selected_modal_candidates']==3
    assert h.preparation_receipt['specialized_cognition_treatment']
    assert not hn.preparation_receipt['specialized_cognition_treatment']
    sha=lambda x:hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return dict(schema='hcl-i02-typographic-dialogue-v9-witness-v1',CAPABILITY_DELTA='Existing B01 now grounds named, line-wrapped dialogue expressions and preserves outer denial versus inner affirmation, separate knowledge claims and unknown private truth in actual complete-source H input. Query-independent modal selection retains every eligible expression despite irrelevant dialogue; H-new retains selection and drops only B01 checked state.',origin='HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY',source_chars=len(source),source_sha256=hashlib.sha256(source.encode()).hexdigest(),runtime_sha256=runtime_digest(),h_receipt=h.preparation_receipt,h_new_receipt=hn.preparation_receipt,h_input_sha256=sha(h.messages),h_new_input_sha256=sha(hn.messages),equal_source_query_candidates_selection=True,treatment_input_differs=h.messages!=hn.messages,positive_witness='NAMED_WRAPPED_DIALOGUE_OUTER_DENIAL_NOT_INNER_DENIAL',private_state_established=False,answer_gain_established=False,confirmation_qualified=False,provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    Path(a.output).write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n');print('TYPOGRAPHIC_DIALOGUE_B01_PROVIDER_FREE_WITNESS')
