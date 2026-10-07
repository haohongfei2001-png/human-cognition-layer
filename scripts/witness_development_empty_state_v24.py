"""Exact archived-v23 comparison on authored inputs; no model/scoring transport."""
import argparse, copy, json, subprocess, sys, tempfile, zipfile
from pathlib import Path
from hcl.cognition import CognitionWorkspace
from scripts.development_drc007_replay import validate_archive
SNAPSHOT=Path('reports/HCL_DRC007_CERTIFIED_REPLAY.zip')
EMPTY='The wind moved a curtain beside the doorway. A cabinet remained shut.'
ACTIVE='Adele believes the path is open. Adele said, "I do not believe the path is open." Adele said, "I plan to walk the path in order to inspect the hall if the path is open."'
QUERY='Describe source reports and their limits, without inventing private mental state or world truth.'
def verify_declared_pursuit_delta(before, after):
 # This authored fixture has one selected plan but no recognized active goal.
 # Its archived negative classification is intentionally repaired, not equal.
 from hcl.cognition.plan_feasibility import _POLICY, _PURSUIT_POLICY
 expected=copy.deepcopy(before)
 groups=expected['checked_plan_feasibility']; assert len(groups)==1
 group=groups[0]; assert len(group['plans'])==1
 row=group['plans'][0]
 assert row['selection']=='REPORTED_SELECTED' and row['goal_status']=='SYSTEM_INSUFFICIENT'
 assert row['subjective_feasibility']=='NOT_CURRENTLY_PURSUED'
 assert row['claim_id']=='claim:ae9c27d5ae80b5218067e4c8962b68064cea836f8199b3b91f2afe720fa7bda7'
 assert group['policy']==_POLICY
 assert expected['sources']==[dict(source_id='scene',version=1,text=ACTIVE)]
 row['subjective_feasibility']='PURSUIT_UNRESOLVED'
 row['claim_id']='claim:c85a2da25c56828dab88aa16042b428be928585aa4a63b5868a4d3f68d4fbe46'
 group['policy']=_POLICY+_PURSUIT_POLICY
 assert after==expected, 'unexpected drift outside the three declared pursuit paths'
 return True
def prepare(source):
 w=CognitionWorkspace();w.put_source('scene',source)
 return w,w.prepare_reader_entry(QUERY,source_ids=('scene',),allow_translation=False)
def witness():
 cert=validate_archive()
 assert cert['run_sha']=='cc00450f0d35bbb4664a4477157bec731e220207'
 before=[]
 with tempfile.TemporaryDirectory(prefix='hcl-v24-before-') as tmp:
  with zipfile.ZipFile(SNAPSHOT) as z:
   for n in cert['files']:
    if n.startswith('hcl/') and n.endswith('.py'):
     p=Path(tmp)/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
  code='import json,sys;from hcl.cognition import CognitionWorkspace;d=json.load(sys.stdin);w=CognitionWorkspace();w.put_source("scene",d["source"]);p=w.prepare_reader_entry(d["query"],source_ids=("scene",),allow_translation=False);print(json.dumps(dict(messages=p.messages,receipt=p.receipt)))'
  for source in (EMPTY,ACTIVE):
   before.append(json.loads(subprocess.run([sys.executable,'-c',code],input=json.dumps(dict(source=source,query=QUERY)),cwd=tmp,text=True,capture_output=True,check=True).stdout))
 w,p=prepare(EMPTY);a,q=prepare(ACTIVE)
 assert not p.receipt['checked_treatment_present'] and not before[0]['receipt']['checked_treatment_present']
 empty_payload=json.loads(p.messages[-1]['content']); assert not empty_payload['hcl_orchestration']['base_bypass']
 assert {k:v for k,v in empty_payload.items() if k!='hcl_orchestration'}==json.loads(before[0]['messages'][-1]['content'])
 assert 'no supported checked domain result.' in p.messages[0]['content']
 assert 'private states or world truth' in p.messages[0]['content'] and 'Quote only original text.' in p.messages[0]['content']
 assert len(json.dumps(p.messages,ensure_ascii=False))<=64000
 assert q.receipt['checked_treatment_present']
 assert verify_declared_pursuit_delta(json.loads(before[1]['messages'][-1]['content']),{k:v for k,v in json.loads(q.messages[-1]['content']).items() if k!='hcl_orchestration'})
 state=json.loads(q.messages[-1]['content']);assert state['checked_epistemic']['comparisons'][0]['relation']=='DIFFERS_FROM_SUBJECT_REPORT'
 assert state['checked_agency'] and state['checked_plan_feasibility'][0]['plans'][0]['subjective_condition']=='NOT_AFFIRMED_NOT_NEGATION'
 raw=json.dumps(dict(answer='The source describes a curtain and cabinet; no private state is established.',source_citations=[dict(source_id='scene',quote=EMPTY,version=1)],uncertainty='Source reports do not certify world truth.',assumptions='Only supplied original text.'))
 result=w.answer_reader_entry(QUERY,lambda _:raw,source_ids=('scene',),allow_translation=False)
 assert result['answer_raw']==raw and result['source_citation_audit']['deliverable'] and not result['source_citation_audit']['semantic_certification']
 w.put_source('scene',EMPTY+' The doorway remained empty.')
 try:p.current_messages(w)
 except ValueError:stale=True
 else:raise AssertionError('stale final source input must be refused')
 revised=w.prepare_reader_entry(QUERY,source_ids=('scene',));assert json.loads(revised.messages[-1]['content'])['sources'][0]['version']==2
 return dict(schema='hcl-current-empty-state-archived-v23-regression-v1',status='PASS_PROVIDER_FREE',CAPABILITY_DELTA='current universal entry preserves archived source and other checked-result paths while adding orchestration and correcting one missing-goal pursuit classification with its claim identity and fixed policy; no current minimal-wire or token-saving claim',before_main_sha=cert['run_sha'],before_runtime_sha256=cert['runtime_sha256'],authored_empty_source=EMPTY,authored_composed_source=ACTIVE,query=QUERY,before_empty_messages=before[0]['messages'],actual_empty_final_messages=result['actual_final_messages'],empty_entry_receipt=p.receipt,before_serialized_message_characters=len(json.dumps(before[0]['messages'],ensure_ascii=False)),after_serialized_message_characters=len(json.dumps(p.messages,ensure_ascii=False)),actual_checked_messages=q.messages,checked_result_payload_equal_archived_v23=False,checked_payload_equal_except_verified_three_path_pursuit_delta=True,orchestration_payload_added=True,source_citation_audit=result['source_citation_audit'],answer_raw=raw,stale_source_refused=stale,revised_messages=revised.messages,provider_calls=0,provider_spend_usd=0,actual_token_saving_claimed=False,actual_cost_saving_claimed=False,answer_gain_claimed=False,semantic_certification=False,evidence='CURRENT_ORCHESTRATION_PROVIDER_FREE_REGRESSION',longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',required=True);args=a.parse_args();Path(args.output).write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n');print('CURRENT_EMPTY_STATE_ARCHIVED_SOURCE_REGRESSION_PASS')
