"""Authored source-bound delivery and offline real-failure regression, no rerun."""
import argparse
import json
from pathlib import Path
from hcl.cognition import CognitionWorkspace
from scripts.serious_eval_contract import runtime_digest
from scripts.witness_development_conditional_reader_v15 import SOURCE_LINES, DERIVED_LINES, QUERY, AuthoredBackend

def witness():
    source='\n'.join(SOURCE_LINES)
    rows=[dict(source_id='meeting',quote=q,kind='event',content=dict(canonical_statement=d))
        for q,d in zip(SOURCE_LINES,DERIVED_LINES)]
    w=CognitionWorkspace();w.put_source('meeting',source)
    actual=[]
    good=json.dumps(dict(answer='The source describes a conditional plan; the translations remain assumptions.',
        source_citations=[SOURCE_LINES[1]],uncertainty='No private or world truth.',assumptions='Declared fictional model only.'))
    positive=w.answer_reader_semantic(QUERY,lambda m:actual.append(m) or good,
        source_ids=('meeting',),backend=AuthoredBackend(rows))
    assert positive['answer']==good and positive['source_citation_audit']['deliverable']
    assert not positive['source_citation_audit']['semantic_certification']
    body=json.loads(actual[0][-1]['content'])
    assert body['sources'][0]['text']==source
    conditional=body['conditional_cognition']['state']
    assert conditional['checked_plan_feasibility'][0]['plans'][0]['deliberate_impossibility']=='NOT_INFERRED'
    receipt=json.loads(Path('reports/HCL_DRE001_RAW_RECEIPT.json').read_text())
    bad=receipt['attempts'][-1]['response_raw']['choices'][0]['message']['content']
    negative=w.answer_reader_semantic(QUERY,lambda m:actual.append(m) or bad,
        source_ids=('meeting',),backend=AuthoredBackend(rows))
    assert negative['answer_raw']==bad and not negative['source_citation_audit']['deliverable']
    assert json.loads(negative['answer'])['source_citations']==[]
    assert receipt['final_format_valid'] and receipt['provider_calls']==2
    return dict(schema='hcl-development-original-source-v16-witness-v1',
        CAPABILITY_DELTA='Source analysis now keeps original text primary and translated cognition explicitly nonquotable. Original-anchored final JSON can be delivered; derived source quotations are preserved raw but fail closed, without hidden quote replacement or semantic certification.',
        origin='HCL_AUTHORED_CORRECTNESS_AND_CONSUMED_FAILURE_OFFLINE_REGRESSION',
        runtime_sha256=runtime_digest(),positive=dict(raw_answer=good,audit=positive['source_citation_audit'],
            actual_final_messages=actual[0],preparation=positive['prepared'].receipt),
        negative=dict(raw_answer=bad,delivered_answer=negative['answer'],audit=negative['source_citation_audit'],
            actual_final_messages=actual[1]),conditional_state_preserved=True,
        offline_failure_run_id=36789819187,old_frozen_result_rescored=False,old_output_corrected=False,
        provider_calls=0,provider_spend_usd=0,stub_final_calls=2,
        semantic_certification=False,answer_gain_established=False,
        independent_confirmation_qualified=False,longmemeval='SEALED_NOT_ACCESSED')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print('ORIGINAL_SOURCE_BOUNDARY_AND_RAW_PRESERVING_DELIVERY_WITNESS_PASS')
