"""Deterministic authored ordinary-input envelope witness; no provider transport."""
import json,hashlib
from pathlib import Path
from hcl.v1 import HCLCognitionLayer,prepare_person_context
from scripts.serious_eval_contract import runtime_digest
from scripts.serious_eval_arms_v8 import prepare_primary_arms_v8
from scripts.serious_eval_full_source_arms_v9 import prepare_primary_arms_v9,prepare_generic_final_v9,digest

def witness():
    source='Mina said: "I support the plan."\r\n'+('The complete source contains a neutral office log entry.\r\n'*4200)+'Mina said: "I am uncertain about the plan."'
    question='How did the reported position change and what remains unproved?'
    prepared=prepare_primary_arms_v9(question,'s',source)
    fixture_map=json.dumps(dict(source_index=[dict(id='e1',source_id='s',quote='Mina said: "I support the plan."'),dict(id='e2',source_id='s',quote='Mina said: "I am uncertain about the plan."')],relations=[dict(from_id='e2',to_id='e1',kind='QUALIFIES')],answer_plan=[dict(operation='COMPARE',evidence_ids=['e1','e2'])],open_questions=['Private intention not established.']))
    final=prepare_generic_final_v9(prepared,fixture_map)
    inputs={**{p:prepared[p] for p in ('C','P','G_map')},'G_final':final};rows={}
    for phase,messages in inputs.items():
        payload=json.loads(messages[-1]['content'])
        assert payload['sources']==[dict(source_id='s',text=source)] and payload['question']==question
        rows[phase]=dict(complete_source_present=True,message_sha256=digest(messages),serialized_utf8_bytes=len(json.dumps(messages,ensure_ascii=False).encode()),answer_fields=payload['answer_fields'])
    try:prepare_primary_arms_v8(question,'s',source)
    except ValueError:old_status='REFUSED_64K_ENVELOPE'
    else:raise AssertionError('historical envelope unexpectedly changed')
    def prohibited(_):raise AssertionError('provider-free witness cannot answer')
    try:prepare_person_context(HCLCognitionLayer(prohibited),question,source)
    except ValueError:h_status='REFUSED_COMPLETE_LONG_SOURCE'
    else:raise AssertionError('H coverage boundary unexpectedly changed')
    return dict(schema='hcl-i02-full-source-arms-v9-witness-v1',source_origin='HCL_AUTHORED_SYNTHETIC_PROVIDER_FREE_ONLY',source_characters=len(source),source_sha256=hashlib.sha256(source.encode()).hexdigest(),question_sha256=hashlib.sha256(question.encode()).hexdigest(),inputs=rows,old_v8_status=old_status,h_ordinary_entry_status=h_status,h_runtime_sha256=runtime_digest(),g_map_origin='AUTHORED_PROVIDER_FREE_REPLAY_NOT_MODEL_EXTRACTION',relation_semantics='UNVERIFIED_MODEL_PROPOSAL',semantic_qualification=False,confirmation_qualified=False,h_efficacy='NOT_TESTED',provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    Path(a.output).write_text(json.dumps(witness(),indent=2)+'\n');print('FULL_SOURCE_ENVELOPE_PROVIDER_FREE_WITNESS')
