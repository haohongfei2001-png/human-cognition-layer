"""Ordinary source report/subject/plan composition; exact v21 code comparison only."""
import argparse,hashlib,json,subprocess,sys,tempfile,zipfile
from pathlib import Path
from hcl.cognition import CognitionWorkspace
from hcl.cognition.core import ClaimKind
SNAPSHOT=Path('reports/HCL_DEVELOPMENT_V21_RUNTIME_SNAPSHOT.zip')
CERT=Path('reports/HCL_DEVELOPMENT_V21_RUNTIME_SNAPSHOT.json')
CERT_SHA='72240bf1062020d30ceb16757595ec4fa7bda312afc2bc357ca88f1be23bf871'
SOURCE='Mara believes the gate is safe. Mara said, "I do not believe the gate is safe." Mara said, "I plan to cross the gate in order to inspect the station if the gate is safe."'
QUERY='Compare source narrator attribution, expressed belief and conditional plan feasibility.'
class NoCall:
 def complete_json(self,*a,**k):raise AssertionError('no provider candidates')
def validate_snapshot():
 sha=lambda b:hashlib.sha256(b).hexdigest()
 if sha(CERT.read_bytes())!=CERT_SHA:raise ValueError('v21 Git-certified snapshot certificate drift')
 c=json.loads(CERT.read_text())
 if c['main_sha']!='e8bc6a5b8a2f8c0b45864af21c1edc565645dd00' or sha(SNAPSHOT.read_bytes())!=c['archive_sha256']:raise ValueError('v21 snapshot archive/SHA drift')
 with zipfile.ZipFile(SNAPSHOT) as z:
  if len(z.namelist())!=len(set(z.namelist())) or set(z.namelist())!=set(c['files']):raise ValueError('runtime snapshot membership drift')
  for name,r in c['files'].items():
   if not name.startswith('hcl/') or not name.endswith('.py') or '..' in Path(name).parts or 'longmemeval' in name.casefold():raise ValueError('unsafe runtime snapshot path')
   b=z.read(name)
   if sha(b)!=r['sha256'] or len(b)!=r['size_bytes'] or hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=r['git_blob_sha1']:raise ValueError('Git-verified runtime bytes drift')
 return c

def witness():
 cert=validate_snapshot()
 with tempfile.TemporaryDirectory(prefix='hcl-v22-before-') as tmp:
  with zipfile.ZipFile(SNAPSHOT) as z:
   for n in cert['files']:
    p=Path(tmp)/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
  code='import json,sys;from hcl.cognition import CognitionWorkspace;d=json.load(sys.stdin);w=CognitionWorkspace();w.put_source("report",d["source"]);p=w.prepare_reader_entry(d["query"],source_ids=("report",));print(json.dumps(p.messages))'
  before=json.loads(subprocess.run([sys.executable,'-c',code],input=json.dumps(dict(source=SOURCE,query=QUERY)),cwd=tmp,text=True,capture_output=True,check=True).stdout)
 w=CognitionWorkspace();w.put_source('report',SOURCE)
 raw=json.dumps(dict(answer='The narrator attributes belief but Mara expresses denial; the stated plan condition is not affirmed by that expressed belief, without inferring its opposite. Actual belief, intention and world feasibility remain unproved.',source_citations=[dict(source_id='report',quote='Mara believes the gate is safe.',version=1)],uncertainty='Narrator report and subject expression do not establish contemporaneous/private/world truth.',assumptions='Only source-reported channels and conditional plan.'))
 r=w.answer_reader_entry(QUERY,lambda _:raw,source_ids=('report',),backend=NoCall());p=r['prepared'];d=json.loads(p.messages[-1]['content']);rows=d['checked_epistemic']['comparisons'];old=json.loads(before[-1]['content'])
 assert old['checked_epistemic']['comparisons']==[] and rows[0]['relation']=='DIFFERS_FROM_SUBJECT_REPORT'
 assert d['checked_agency'] and d['checked_plan_feasibility'] and d['checked_plan_feasibility'][0]['plans'][0]['subjective_condition']=='NOT_AFFIRMED_NOT_NEGATION'
 assert r['answer_raw']==raw and r['source_citation_audit']['deliverable'] and p.receipt['extraction_calls']==0
 ids=p.receipt['local_preparation']['shared_support_claim_ids'];assert all(w.core.support_statuses()[key]=='SUPPORT_AVAILABLE' for key in ids)
 # An actual inner interpretation challenge invalidates the actual final input.
 key=rows[0]['claim_id'];scope=w.core.claims[key].scope;counter=w.core.claim(scope,ClaimKind.SOURCE_REPORT,dict(challenge='Interpretation contested.'));w.core.support(counter,w._spans['report']);w.core.challenge(key,counter)
 try:p.current_messages(w)
 except ValueError:challenge=True
 else:raise AssertionError('inner challenge did not block delivery')
 w.put_source('report',SOURCE.replace('Mara believes','Mara does not believe'));q=w.prepare_reader_entry(QUERY,source_ids=('report',));new=json.loads(q.messages[-1]['content']);assert new['checked_epistemic']['comparisons'][0]['relation']=='CONSISTENT_WITH_SUBJECT_REPORT' and new['sources'][0]['version']==2
 assert all(w.core.spans[x['source_span_id']].version==2 for x in new['cognitive_candidates'])
 return dict(schema='hcl-narrator-attribution-v22-witness',status='PASS_PROVIDER_FREE',CAPABILITY_DELTA='ordinary complete report/speech paragraph now enters actual narrator-attribution vs subject-expression comparison alongside C01/C03, without equating narrative report to own plan belief/private truth',source=SOURCE,query=QUERY,before_main_sha=cert['main_sha'],before_runtime_sha256=cert['runtime_sha256'],before_messages=before,actual_final_messages=r['actual_final_messages'],entry_receipt=p.receipt,source_citation_audit=r['source_citation_audit'],answer_raw=raw,inner_claim_challenge_invalidates=challenge,revised_messages=q.messages,provider_calls=0,provider_spend_usd=0,answer_backend='STUB_NOT_PROVIDER',answer_gain=False,semantic_certification=False,utility='IMPLEMENTED_UNVALIDATED',longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',required=True);args=a.parse_args();Path(args.output).write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n');print('NARRATOR_ATTRIBUTION_V22_PASS_PROVIDER_FREE')
