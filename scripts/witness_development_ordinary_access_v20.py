"""Authored ordinary access delta plus consumed inputs-only cost regression."""
import argparse,json,subprocess,sys,tempfile,zipfile
from pathlib import Path
from hcl.cognition import CognitionWorkspace
from scripts.development_drc004_replay import validate_archive,ARCHIVE
SOURCE='Leah said, “I believe the gate is clear.”\nAri Stone heard Leah\'s last statement.\nTess did not hear Leah\'s last statement.\nLeah\'s last statement was publicly available.'
QUERY='Who has a reported route to the statement, and what remains unknown?'
class NoCall:
 def complete_json(self,*args,**kwargs):raise AssertionError('automatic extraction must be simplified away')

def witness():
 cert=validate_archive()
 with tempfile.TemporaryDirectory(prefix='hcl-v20-before-') as tmp:
  with zipfile.ZipFile(ARCHIVE) as z:
   for name in cert['files']:
    p=Path(tmp)/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
  snippet='import json,sys;from hcl.cognition import CognitionWorkspace;d=json.load(sys.stdin);w=CognitionWorkspace();w.put_source("meeting",d["source"]);p=w.prepare_reader_entry(d["query"],source_ids=("meeting",));print(json.dumps({"payload":json.loads(p.messages[-1]["content"]),"receipt":p.receipt}))'
  before=json.loads(subprocess.run([sys.executable,'-c',snippet],input=json.dumps(dict(source=SOURCE,query=QUERY)),cwd=tmp,text=True,capture_output=True,check=True).stdout)
 w=CognitionWorkspace();w.put_source('meeting',SOURCE)
 output=json.dumps(dict(answer='The source reports Ari hearing and Tess not hearing the statement.',source_citations=[dict(source_id='meeting',quote="Ari Stone heard Leah's last statement.",version=1),dict(source_id='meeting',quote="Tess did not hear Leah's last statement.",version=1)],uncertainty='Comprehension, acceptance, knowledge and private beliefs are unknown.',assumptions='Source report and order only.'))
 result=w.answer_reader_entry(QUERY,lambda _:output,source_ids=('meeting',),backend=NoCall());p=result['prepared'];payload=json.loads(result['actual_final_messages'][-2]['content']);state=payload['checked_reported_communication']
 assert 'checked_reported_communication' not in before['payload'] and state['views']
 assert result['answer']==output and result['answer_raw']==output and p.receipt['extraction_calls']==0 and payload['checked_epistemic']
 views={v['source_named_actor']:v for v in state['views']};assert len(views['Ari Stone']['visible_derived_statements'])==1 and not views['Tess']['visible_derived_statements']
 assert all(v['knowledge']=='NOT_ESTABLISHED' for v in state['views'])
 regression=[]
 for row in json.loads(Path('reports/HCL_DRC004_SUBSET.json').read_text())['cases']:
  local=CognitionWorkspace();local.put_source('consumed-source',row['source']);entry=local.prepare_reader_entry(row['question'],source_ids=('consumed-source',),backend=NoCall())
  assert entry.receipt['extraction_calls']==0
  regression.append(dict(case_id=row['case_id'],current_extraction_calls=0,original_paid_extraction_calls=1,answers_rerun=False,scores_changed=False))
 w.put_source('meeting',SOURCE.replace('Ari Stone heard','Ari Stone did not hear'))
 try:p.current_messages(w)
 except ValueError:revision=True
 else:raise AssertionError('stale access state remained answerable')
 return dict(schema='hcl-ordinary-access-v20-witness',status='PASS_PROVIDER_FREE',
  capability_delta='ordinary explicit receipt/nonreceipt now enters real B02 access checks alongside B01 public expression, without private knowledge inference or extraction',
  before_runtime_sha256=cert['runtime_sha256'],before_payload=before['payload'],
  source=SOURCE,query=QUERY,actual_final_messages=result['actual_final_messages'],entry_receipt=p.receipt,
  raw_answer=output,source_citation_audit=result['source_citation_audit'],revision_invalidates=revision,
  consumed_inputs_only_regression=regression,provider_calls=0,provider_spend_usd=0,
  answer_backend='STUB_NOT_PROVIDER',answer_gain=False,semantic_certification=False,
  evidence='AUTHORED_CORRECTNESS_AND_CONSUMED_INPUTS_NOT_NEW_BENCHMARK_EFFICACY',longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',required=True);args=a.parse_args();Path(args.output).write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n');print('ORDINARY_ACCESS_V20_PASS_PROVIDER_FREE')
