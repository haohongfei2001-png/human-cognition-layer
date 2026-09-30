"""Authored future-reference witness; never imports/reinterprets consumed outputs."""
import argparse,json
from pathlib import Path
from hcl.v1 import HCLCognitionLayer,answer_person_context
from scripts.serious_eval_full_source_arms_v10 import prepare_primary_arms_v10,prepare_generic_final_v10,resolve_final_references,answer_h_with_shared_references
from scripts.serious_eval_full_source_arms_v9 import prepare_primary_arms_v9,prepare_generic_final_v9
from scripts.serious_eval_semantic_score import validate_answer
from scripts.serious_eval_contract import runtime_digest
SOURCE='_Mina._ I do not believe\r\nthat Jo believes the plan is safe.\r\n\r\n'+('Ordinary neutral background. '*650)
QUESTION='Which positions are reported, and what remains unproved?'
QUOTE='I do not believe that Jo believes the plan is safe.'
def witness():
    raw=json.dumps(dict(answer='The source reports outer denial, without establishing Jo’s inner denial.',source_citations=[dict(source_id='ordinary-source',quote=QUOTE)],uncertainty='Private belief, truth and event time unproved.',assumptions='Only source-reported expression.'))
    map=json.dumps(dict(source_index=[dict(id='e1',source_id='ordinary-source',quote=QUOTE)],relations=[],answer_plan=[dict(operation='RETRIEVE',evidence_ids=['e1'])],open_questions=['Private belief unproved.']))
    prepared=prepare_primary_arms_v10(QUESTION,'ordinary-source',SOURCE);g=prepare_generic_final_v10(prepared,map)
    calls=[]
    def model(messages):calls.append(messages);return raw
    h=answer_h_with_shared_references(HCLCognitionLayer(model),QUESTION,SOURCE)
    final=h['result']
    validate_answer(final['answer'],{'ordinary-source':SOURCE})
    old_answer_rejected=old_map_rejected=False
    try:validate_answer(json.loads(raw),{'ordinary-source':SOURCE})
    except ValueError:old_answer_rejected=True
    try:prepare_generic_final_v9(prepare_primary_arms_v9(QUESTION,'ordinary-source',SOURCE),map)
    except ValueError:old_map_rejected=True
    assert old_answer_rejected and old_map_rejected and len(calls)==1
    return dict(schema='hcl-i02-source-reference-positive-witness-v1',source_origin='HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY',ordinary_question=QUESTION,source_text=SOURCE,actual_cpg_prepared=prepared,actual_g_final=g,actual_h_final_messages=calls[0],h_preparation_receipt=h['prepared'].preparation_receipt,raw_final_answer=raw,resolved_final=final,answer_body_unchanged=json.loads(raw)['answer']==final['answer']['answer'],source_bytes_unchanged=True,shared_for_c_p_g_h=True,old_v9_and_scorer_still_reject_layout_rewrite=True,h_runtime_sha256=runtime_digest(),final_stub_calls=1,provider_calls=0,provider_spend_usd=0,old_consumed_outputs_inspected_or_rescored=False,semantic_qualification=False,h_answer_gain=False,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();Path(a.output).write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n')
