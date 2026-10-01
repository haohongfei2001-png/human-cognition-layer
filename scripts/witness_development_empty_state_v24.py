"""Exact archived-v23 comparison on authored inputs; no model/scoring transport."""
import argparse, json, subprocess, sys, tempfile, zipfile
from pathlib import Path
from hcl.cognition import CognitionWorkspace
from scripts.development_drc007_replay import validate_archive
SNAPSHOT=Path('reports/HCL_DRC007_CERTIFIED_REPLAY.zip')
EMPTY='The wind moved a curtain beside the doorway. A cabinet remained shut.'
ACTIVE='Adele believes the path is open. Adele said, "I do not believe the path is open." Adele said, "I plan to walk the path in order to inspect the hall if the path is open."'
QUERY='Describe source reports and their limits, without inventing private mental state or world truth.'
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
 assert p.messages[-1]==before[0]['messages'][-1]
 assert 'No checked cognition state was derived.' in p.messages[0]['content']
 assert 'private states or world truth' in p.messages[0]['content'] and 'Quote only original text.' in p.messages[0]['content']
 assert len(json.dumps(p.messages,ensure_ascii=False))<len(json.dumps(before[0]['messages'],ensure_ascii=False))
 assert q.receipt['checked_treatment_present'] and q.messages==before[1]['messages']
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
 return dict(schema='hcl-explicit-empty-state-v24-witness',status='PASS_PROVIDER_FREE',CAPABILITY_DELTA='ordinary reader without executed cognition now explicitly discloses checked-state absence and uses a smaller original-source/private-world/quote contract; actual checked cognition input remains byte-for-byte identical',before_main_sha=cert['run_sha'],before_runtime_sha256=cert['runtime_sha256'],authored_empty_source=EMPTY,authored_composed_source=ACTIVE,query=QUERY,before_empty_messages=before[0]['messages'],actual_empty_final_messages=result['actual_final_messages'],empty_entry_receipt=p.receipt,before_serialized_message_characters=len(json.dumps(before[0]['messages'],ensure_ascii=False)),after_serialized_message_characters=len(json.dumps(p.messages,ensure_ascii=False)),actual_checked_messages=q.messages,checked_messages_equal_archived_v23=True,source_citation_audit=result['source_citation_audit'],answer_raw=raw,stale_source_refused=stale,revised_messages=revised.messages,provider_calls=0,provider_spend_usd=0,actual_token_saving_claimed=False,actual_cost_saving_claimed=False,answer_gain_claimed=False,semantic_certification=False,evidence='IMPLEMENTED_UNVALIDATED_SIMPLIFICATION',longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',required=True);args=a.parse_args();Path(args.output).write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n');print('EMPTY_STATE_V24_PASS_PROVIDER_FREE')
