"""Ordinary source report/subject/plan composition; exact archived v22 code comparison only."""
import argparse,hashlib,json,subprocess,sys,tempfile,zipfile
from pathlib import Path
from hcl.cognition import CognitionWorkspace
from hcl.cognition.core import ClaimKind
from scripts.development_drc006_replay import validate_archive
SNAPSHOT=Path('reports/HCL_DRC006_CERTIFIED_REPLAY.zip')
SOURCE='Elena opened the window. Elena believes the corridor is quiet. Elena said, "I do not believe the corridor is quiet." Tomas arrived. Elena said, "I plan to enter the corridor in order to inspect the room if the corridor is quiet."'
QUERY='Compare source narrator attribution, expressed belief and conditional plan feasibility in the ordinary scene.'
class NoCall:
 def complete_json(self,*a,**k):raise AssertionError('no provider candidates')
def validate_snapshot():
 c=validate_archive()
 assert c['run_sha']=='76874879f8c961a154587f9de9d1bf390aa96eb9'
 return dict(main_sha=c['run_sha'],runtime_sha256=c['runtime_sha256'],files={n:r for n,r in c['files'].items() if n.startswith('hcl/') and n.endswith('.py')})

def witness():
 cert=validate_snapshot()
 with tempfile.TemporaryDirectory(prefix='hcl-v23-before-') as tmp:
  with zipfile.ZipFile(SNAPSHOT) as z:
   for n in cert['files']:
    p=Path(tmp)/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
  code='import json,sys;from hcl.cognition import CognitionWorkspace;d=json.load(sys.stdin);w=CognitionWorkspace();w.put_source("scene",d["source"]);p=w.prepare_reader_entry(d["query"],source_ids=("scene",));print(json.dumps(p.messages))'
  before=json.loads(subprocess.run([sys.executable,'-c',code],input=json.dumps(dict(source=SOURCE,query=QUERY)),cwd=tmp,text=True,capture_output=True,check=True).stdout)
 w=CognitionWorkspace();w.put_source('scene',SOURCE)
 raw=json.dumps(dict(answer='The narrator attributes belief but Elena expresses denial; the stated plan condition is not affirmed by that expressed belief, without inferring its opposite. Actual belief, intention and world feasibility remain unproved.',source_citations=[dict(source_id='scene',quote='Elena believes the corridor is quiet.',version=1)],uncertainty='Narrator report and subject expression do not establish contemporaneous/private/world truth.',assumptions='Only source-reported channels and conditional plan.'))
 r=w.answer_reader_entry(QUERY,lambda _:raw,source_ids=('scene',),backend=NoCall());p=r['prepared'];d=json.loads(p.messages[-1]['content']);rows=d['checked_epistemic']['comparisons'];old=json.loads(before[-1]['content'])
 assert old['checked_epistemic']['comparisons']==[] and rows[0]['relation']=='DIFFERS_FROM_SUBJECT_REPORT'
 assert d['checked_agency'] and d['checked_plan_feasibility'] and d['checked_plan_feasibility'][0]['plans'][0]['subjective_condition']=='NOT_AFFIRMED_NOT_NEGATION'
 assert r['answer_raw']==raw and r['source_citation_audit']['deliverable'] and p.receipt['extraction_calls']==0
 ids=p.receipt['local_preparation']['shared_support_claim_ids'];assert all(w.core.support_statuses()[key]=='SUPPORT_AVAILABLE' for key in ids)
 # An actual inner interpretation challenge invalidates the actual final input.
 key=rows[0]['claim_id'];scope=w.core.claims[key].scope;counter=w.core.claim(scope,ClaimKind.SOURCE_REPORT,dict(challenge='Interpretation contested.'));w.core.support(counter,w._spans['scene']);w.core.challenge(key,counter)
 try:p.current_messages(w)
 except ValueError:challenge=True
 else:raise AssertionError('inner challenge did not block delivery')
 w.put_source('scene',SOURCE.replace('Elena believes','Elena does not believe'));q=w.prepare_reader_entry(QUERY,source_ids=('scene',));new=json.loads(q.messages[-1]['content']);assert new['checked_epistemic']['comparisons'][0]['relation']=='CONSISTENT_WITH_SUBJECT_REPORT' and new['sources'][0]['version']==2
 assert all(w.core.spans[x['source_span_id']].version==2 for x in new['cognitive_candidates'])
 return dict(schema='hcl-mixed-narrative-v23-witness',status='PASS_PROVIDER_FREE',CAPABILITY_DELTA='explicit named narrator mental report amidst ordinary material context now enters actual B01 comparison/C01/C03 without turning context or attribution into private/world truth',source=SOURCE,query=QUERY,before_main_sha=cert['main_sha'],before_runtime_sha256=cert['runtime_sha256'],before_messages=before,actual_final_messages=r['actual_final_messages'],entry_receipt=p.receipt,source_citation_audit=r['source_citation_audit'],answer_raw=raw,inner_claim_challenge_invalidates=challenge,revised_messages=q.messages,provider_calls=0,provider_spend_usd=0,answer_backend='STUB_NOT_PROVIDER',answer_gain=False,semantic_certification=False,utility='IMPLEMENTED_UNVALIDATED',longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',required=True);args=a.parse_args();Path(args.output).write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n');print('MIXED_NARRATIVE_V23_PASS_PROVIDER_FREE')
