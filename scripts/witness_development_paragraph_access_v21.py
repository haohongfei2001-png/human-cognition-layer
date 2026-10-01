"""Same-source paragraph access plus consumed inputs-only context regression."""
import argparse,json,subprocess,sys,tempfile,zipfile
from pathlib import Path
from hcl.cognition import CognitionWorkspace
from scripts.development_drc005_replay import validate_archive,ARCHIVE
SOURCE='Mara said, “I believe the road is clear.” Niko Reed heard Mara\'s last statement. Tess did not hear Mara\'s last statement. Tess later read Mara\'s last statement.'
QUERY='Compare the source-reported information routes and unknown mental states.'
class NoCall:
 def complete_json(self,*a,**k):raise AssertionError('no automatic extraction')
def witness():
 cert=validate_archive();items=[dict(source=SOURCE,query=QUERY)]+[dict(source=r['source'],query=r['question']) for r in json.loads(Path('reports/HCL_DRC005_SUBSET.json').read_text())['cases']]
 with tempfile.TemporaryDirectory(prefix='hcl-v21-before-') as tmp:
  with zipfile.ZipFile(ARCHIVE) as z:
   for name in cert['files']:
    p=Path(tmp)/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
  code='import json,sys;from hcl.cognition import CognitionWorkspace;out=[]\nfor d in json.load(sys.stdin):\n w=CognitionWorkspace();w.put_source("source",d["source"]);p=w.prepare_reader_entry(d["query"],source_ids=("source",));out.append({"messages":p.messages,"receipt":p.receipt})\nprint(json.dumps(out))'
  before=json.loads(subprocess.run([sys.executable,'-c',code],input=json.dumps(items),cwd=tmp,text=True,capture_output=True,check=True).stdout)
 w=CognitionWorkspace();w.put_source('source',SOURCE)
 raw=json.dumps(dict(answer='Niko has reported receipt; Tess has later receipt after nonreceipt.',source_citations=[dict(source_id='source',quote="Tess later read Mara's last statement.",version=1)],uncertainty='No calendar time/comprehension/knowledge.',assumptions='Literal source reports only.'))
 result=w.answer_reader_entry(QUERY,lambda _:raw,source_ids=('source',),backend=NoCall());p=result['prepared'];payload=json.loads(p.messages[-1]['content']);state=payload['checked_reported_communication']
 assert 'checked_reported_communication' not in json.loads(before[0]['messages'][-1]['content']) and payload['checked_epistemic'] and state['views']
 assert result['answer_raw']==raw and result['source_citation_audit']['deliverable'] and result['preparation_provider_calls']==0
 assert all(SOURCE[b['start']:b['start']+len(b['quote'])]==b['quote'] for b in state['original_quote_bindings'])
 regression=[]
 for i,item in enumerate(items[1:],1):
  local=CognitionWorkspace();local.put_source('source',item['source']);entry=local.prepare_reader_entry(item['query'],source_ids=('source',),backend=NoCall());actual=json.loads(entry.messages[-1]['content']);assert set(actual)=={'query','sources'} and actual['sources'][0]['text']==item['source'] and entry.receipt['extraction_calls']==0 and not entry.receipt['checked_treatment_present']
  b=len(json.dumps(before[i]['messages'],ensure_ascii=False));a=len(json.dumps(entry.messages,ensure_ascii=False));assert a<b
  regression.append(dict(consumed_item_index=i-1,before_preparation_wire_chars=b,after_preparation_wire_chars=a,actual_tokens_or_bill_savings_claimed=False,answers_rerun=False,scores_changed=False))
 w.put_source('source',SOURCE.replace('Niko Reed heard','Niko Reed did not hear'))
 try:p.current_messages(w)
 except ValueError:invalidated=True
 else:raise AssertionError('stale paragraph state remained usable')
 return dict(schema='hcl-paragraph-access-v21-witness',status='PASS_PROVIDER_FREE',capability_delta='same ordinary paragraph now enters real B02 reported receipt/later-receipt checks beside B01, preserving offsets, qualifiers and unknown mental states',before_runtime_sha256=cert['runtime_sha256'],before_messages=before[0]['messages'],source=SOURCE,query=QUERY,actual_final_messages=result['actual_final_messages'],entry_receipt=p.receipt,raw_answer=raw,source_citation_audit=result['source_citation_audit'],revision_invalidates=invalidated,consumed_inputs_only_regression=regression,provider_calls=0,provider_spend_usd=0,answer_backend='STUB_NOT_PROVIDER',answer_gain=False,semantic_certification=False,utility='IMPLEMENTED_UNVALIDATED',longmemeval='SEALED_NOT_ACCESSED')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--output',required=True);args=a.parse_args();Path(args.output).write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n');print('PARAGRAPH_ACCESS_V21_PASS_PROVIDER_FREE')
