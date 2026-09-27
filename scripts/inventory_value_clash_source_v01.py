"""Provider-free source inventory; no cases, labels or character prose printed."""
import argparse,csv,hashlib,json
from pathlib import Path
PIN='744ec8d62681038a9f44aaba2f737ebd83e8b0d3'
def inventory(path):
 data=path.read_bytes();rows=list(csv.DictReader(data.decode('utf-8-sig').splitlines()))
 assert len(rows)==345 and len({r['id'] for r in rows})==345
 required={'id','situation','action','topic','source'}
 assert required<=set(rows[0])
 fields=list(rows[0]);profiles=[k for k in fields if k.startswith('character')];assert len(profiles)==11
 topics={t:sum(r['topic']==t for r in rows) for t in sorted({r['topic'] for r in rows})}
 return {'format':'hcl-value-clash-source-inventory-v01','provider_calls':0,'source_revision':PIN,'source_bytes':len(data),'source_sha256':hashlib.sha256(data).hexdigest(),'rows':len(rows),'profile_columns':profiles,'topics':topics,'exclusions_first_viewer_page_ids':[r['id'] for r in rows[:20]],'source_text_displayed':False,'native_category_labels_not_runtime_inputs':True,'qualified_scope':'public constructed-character description reading only; not psychological discomfort, objective morality or real hidden mental truth','selection_frozen':False,'paid_authorization_usd':0}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source-file',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();x=inventory(a.source_file);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
