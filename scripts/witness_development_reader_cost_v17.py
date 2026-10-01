"""Authored lossless transport/capacity witness, no provider or efficacy scoring."""
import argparse,json
from pathlib import Path
from hcl.cognition import CognitionWorkspace
from hcl.v1.compact import expand_reader_context
from scripts.serious_eval_contract import runtime_digest
from scripts.witness_development_conditional_reader_v15 import SOURCE_LINES,DERIVED_LINES,QUERY,AuthoredBackend

def witness():
    source='\n'.join(SOURCE_LINES);rows=[dict(source_id='meeting',quote=q,kind='event',content=dict(canonical_statement=d)) for q,d in zip(SOURCE_LINES,DERIVED_LINES)]
    w=CognitionWorkspace();w.put_source('meeting',source)
    before=w.prepare_reader_semantic(QUERY,source_ids=('meeting',),backend=AuthoredBackend(rows))
    after=w.prepare_reader_semantic(QUERY,source_ids=('meeting',),backend=AuthoredBackend(rows),compact_context=True)
    plain=json.loads(before.messages[-1]['content']);coded=json.loads(after.messages[-1]['content']);restored=expand_reader_context(coded)
    assert plain==restored and coded['sources']==plain['sources'] and before.operation_ids==after.operation_ids
    assert restored['conditional_cognition']['state']['checked_plan_feasibility'][0]['plans'][0]['deliberate_impossibility']=='NOT_INFERRED'
    bc=len(before.messages[-1]['content']);ac=len(after.messages[-1]['content']);assert ac<bc
    capacity=w.prepare_reader_semantic(QUERY,source_ids=('meeting',),backend=AuthoredBackend(rows),compact_context=True,max_chars=ac)
    raw=json.dumps(dict(answer='A conditional plan is reported.',source_citations=[SOURCE_LINES[1]],uncertainty='Translation unverified.',assumptions='No private or world truth.'));calls=[]
    answer=w.answer_reader_semantic(QUERY,lambda m:calls.append(m) or raw,source_ids=('meeting',),backend=AuthoredBackend(rows),compact_context=True)
    assert answer['answer']==raw and len(calls)==1 and answer['source_citation_audit']['deliverable']
    return dict(schema='hcl-development-reader-cost-v17-witness-v1',CAPABILITY_DELTA='Complete original text and existing conditional checked state now fit a smaller transport budget with reversible repeated opaque-ID aliases; original quotation boundary and one final call remain intact.',
        runtime_sha256=runtime_digest(),origin='HCL_AUTHORED_CORRECTNESS_ONLY',
        context_chars_before=bc,context_chars_after=ac,context_char_reduction=1-ac/bc,
        total_message_bytes_before=len(json.dumps(before.messages).encode()),total_message_bytes_after=len(json.dumps(after.messages).encode()),
        full_payload_round_trip_equal=True,operation_ids_equal=True,primary_source_unchanged=True,
        actual_final_messages=calls[0],preparation=answer['prepared'].receipt,raw_answer=raw,citation_audit=answer['source_citation_audit'],
        fit_user_context_char_budget=ac,old_context_does_not_fit_budget=bc>ac,
        provider_calls=0,provider_spend_usd=0,model_tokens_measured=False,answer_gain_established=False,
        semantic_certification=False,independent_confirmation_qualified=False,longmemeval='SEALED_NOT_ACCESSED')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
    Path(a.output).write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print('READER_COST_V17_LOSSLESS_CONTEXT_CAPACITY_WITNESS_PASS')
