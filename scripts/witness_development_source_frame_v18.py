"""Actual source identity, real cognition composition, no provider or rescoring."""
import argparse,json
from pathlib import Path
from hcl.cognition import CognitionWorkspace
from scripts.provider_json_contract import validate_json_mode_request
from scripts.serious_eval_contract import runtime_digest
SOURCE='Eva said, “I want to protect the garden.”\nEva added, “I plan to call Noor in order to protect the garden if the gate is clear.”\nEva said, “I have an opportunity to call Noor.”\nEva said, “I believe the gate is clear.”'
QUERY='Which actions are supported and what limits remain?'
def witness():
 w=CognitionWorkspace();w.put_source('garden',SOURCE);calls=[]
 raw=json.dumps(dict(answer='The source reports a conditional plan and belief; private sincerity and world feasibility are unknown.',source_citations=[dict(source_id='ordinary-source',version=1,quote='I plan to call Noor in order to protect the garden if the gate is clear.')],uncertainty='Source reports and conditions only.',assumptions='No private or world truth.'))
 good=w.answer_source_guarded(QUERY,lambda m:calls.append(m) or raw,source_ids=('garden',));assert good['answer']==raw
 validate_json_mode_request(dict(response_format=dict(type='json_object'),messages=calls[0]))
 state=json.loads(calls[0][-2]['content']);plan=state['checked_plan_feasibility'][0]['plans'][0]
 assert plan['deliberate_impossibility']=='NOT_INFERRED' and plan['world_feasibility']=='NOT_ESTABLISHED'
 badraw=raw.replace('ordinary-source','guessed-other-source');bad=w.answer_source_guarded(QUERY,lambda m:badraw,source_ids=('garden',));assert not bad['source_citation_audit']['deliverable'] and bad['answer_raw']==badraw
 old=w.prepare(QUERY,source_ids=('garden',));w.put_source('garden','Eva withdrew the report.')
 try:old.current_messages(w);raise AssertionError('old source support survived')
 except ValueError:pass
 oldreceipt=json.loads(Path('reports/HCL_DRC003_RAW_RECEIPT.json').read_text())
 try:validate_json_mode_request(oldreceipt['attempts'][-1]['request_raw']);raise AssertionError('bad request accepted')
 except ValueError:pass
 return dict(schema='hcl-development-source-frame-v18-witness-v1',CAPABILITY_DELTA='Ordinary whole-source reader can deliver valid source-quoted answers against actual input IDs with zero extraction and real checked cognition, reject guessed aliases or stale source support while preserving raw output, and detect JSON-mode request mistakes without transport.',runtime_sha256=runtime_digest(),origin='HCL_AUTHORED_CORRECTNESS_WITH_CONSUMED_REQUEST_OFFLINE_REGRESSION',actual_final_messages=calls[0],actual_cognition_state=state,positive_audit=good['source_citation_audit'],raw_answer=raw,negative_audit=bad['source_citation_audit'],negative_raw=badraw,source_revision_invalidates=True,JSON_request_refused_before_transport=True,historical_response_or_score_changed=False,provider_calls=0,provider_spend_usd=0,preparation_provider_calls=0,semantic_certification=False,answer_gain_established=False,independent_confirmation_qualified=False,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();Path(a.output).write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n');print('ACTUAL_SOURCE_FRAME_V18_AND_ZERO_EXTRACTION_COMPOSITION_WITNESS_PASS')
