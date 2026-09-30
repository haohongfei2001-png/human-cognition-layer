"""Authored ordinary short-source B01/C01/C03 witness, not benchmark efficacy."""
import argparse,hashlib,json
from pathlib import Path
from hcl.v1 import HCLCognitionLayer,prepare_person_context
from hcl.v1.long_source_question import prepare_reader_cognition
from hcl.v1.person_question import answer_person_context
from scripts.serious_eval_contract import runtime_digest

def witness():
 source='\n\n'.join(['_Dana._ I want to protect the gate.','_Dana._ I plan to call Noor in order to protect the gate if the gate is clear.','_Dana._ I have an opportunity to call Noor.','_Dana._ I believe the gate is clear.','Narrator: In the declared model, it is false that the gate is clear.'])
 query='Which actions are supported and what limits remain?'
 def prohibited(_):raise AssertionError('no provider in authored witness')
 h=prepare_person_context(HCLCognitionLayer(prohibited),query,source)
 n=prepare_reader_cognition(query,source,plan_checks=False)
 hp,np=(json.loads(x.messages[-1]['content']) for x in (h,n))
 plans=hp.pop('checked_plan_feasibility');assert hp==np and hp['sources'][0]['text']==source
 plan=plans[0]['plans'][0]
 assert plan['subjective_feasibility']=='SUPPORTED_UNDER_REPORTED_BELIEFS'
 assert plan['model_condition_check']=='MODEL_CONDITION_CONTRADICTED'
 assert plan['deliberate_impossibility']=='NOT_INFERRED'
 revision=source+'\n\n_Dana._ I now believe it is false that the gate is clear instead of the gate is clear.'
 revised=prepare_person_context(HCLCognitionLayer(prohibited),query,revision)
 revised_plan=json.loads(revised.messages[-1]['content'])['checked_plan_feasibility'][0]['plans'][0]
 assert revised_plan['subjective_feasibility']=='CONTRADICTED_UNDER_REPORTED_BELIEFS'
 calls=[];answer=answer_person_context(HCLCognitionLayer(lambda m:calls.append(m) or 'Authored correctness stub.'),query,source,debug=True)
 assert calls==[list(h.messages)] and answer.prepared.messages==h.messages
 sha=lambda v:hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 return dict(schema='hcl-development-reader-entry-v13-witness-v1',CAPABILITY_DELTA='Ordinary short authorized reader questions need no fixed sentence to deliver existing source-local B01 expressions, C01 plan/opportunity and C03 belief/model condition joins to the actual final model. Full unmatched prose stays available with honest zero-treatment coverage. Private access and caller normative premises are not guessed.',origin='HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY',runtime_sha256=runtime_digest(),source_sha256=hashlib.sha256(source.encode()).hexdigest(),h_receipt=h.preparation_receipt,h_new_receipt=n.preparation_receipt,revision_receipt=revised.preparation_receipt,h_input_sha256=sha(h.messages),h_new_input_sha256=sha(n.messages),positive_witness='SHORT_ORDINARY_QUESTION_ACTUAL_B01_C01_C03_COMPOSITION',positive_revision='SOURCE_LOCAL_BELIEF_CORRECTION_UPDATES_PLAN_CONDITION',hnew_only_removes_c03=True,smoke_stub_calls=1,provider_calls=0,provider_spend_usd=0,answer_gain_established=False,independent_confirmation_qualified=False,longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
 Path(a.output).write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n');print('GENERAL_READER_EXISTING_COGNITION_PROVIDER_FREE_WITNESS')
