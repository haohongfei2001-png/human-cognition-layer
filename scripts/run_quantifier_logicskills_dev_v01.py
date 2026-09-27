"""Four independent controlled-language symbolization probes; strong thinking C/P."""
import argparse,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from hcl.quantified_logic import parse,equivalent,signature,FormulaError
from scripts.reasoning_probe_backend import ReasoningBackend,BudgetLedger
from scripts.run_narrative_torque_dev_v02 import transport_failure
REVISION='31b175699127b766e64eb0c550893396404f665b'
DATA_SHA='6c39b461f428536f7b0870b2179cee216d59d7bf4122b213aee85ff5b44d7fe8'
MANIFEST=ROOT/'eval/conceptual/logicskills_symbolization_dev_selection_v01.json'
SALT='HCL-CONCEPTUAL-QUANTIFIER-LOGICSKILLS-DEVELOPMENT-V01'
TOKEN='HCL_QUANTIFIER_LOGICSKILLS_DEV_V01_ONCE'
CAP=.05
EXCLUDE=[11131]
PUBLIC_EXAMPLE_SENTENCES=["A human chased a donkey that chased it"]
COMMON=('Translate the full controlled-English sentence using exactly the supplied abbreviation key. This is formal sentence meaning, not private psychology or world knowledge. Consider all quantifier scopes and clause attachments carefully. Return exactly one JSON object with only formula, a single formula string; no other keys or markdown. Example of output SYNTAX only: {"formula":"∀xFx"}. Grammar: uppercase one-letter unary/binary predicate followed by one/two lowercase terms; variables s..z, constants a..r; negation ¬, quantifiers ∀ or ∃ directly bind a variable followed by formula; binary forms (formula∧formula), (formula∨formula), (formula→formula), (formula↔formula). No equality, free variables, invented key symbols, brackets or English. The example is not the answer.')
THIN=('Individuate each constant and bound variable, track which quantifier binds every occurrence, and preserve clause scope under negation. Do not interchange forall-exists with exists-forall. Consider a small counterexample to competing readings, then translate the stated sentence without adding existence or assuming distinct named objects. This procedure does not supply a reference formula.')
def sha(b):return hashlib.sha256(b.encode() if isinstance(b,str) else b).hexdigest()
def load(path):
 b=path.read_bytes()
 if sha(b)!=DATA_SHA:raise ValueError('pinned source digest mismatch')
 x=json.loads(b)
 if len(x)!=300 or any(v['language']!='english' for v in x):raise ValueError('source format drift')
 return x
def select(data):
 rows=[]
 for v in data:
  if v['id'] in EXCLUDE or any(t.lower() in v['question'].lower() for t in PUBLIC_EXAMPLE_SENTENCES):continue
  source={'input':v['question'],'scope':'CONTROLLED_FORMAL_SYMBOLIZATION_NOT_PRIVATE_MENTAL_OR_WORLD_TRUTH'}
  rows.append({'id':v['id'],'source':source,'source_sha256':sha(json.dumps(source,sort_keys=True))})
 rows.sort(key=lambda v:sha(SALT+'|'+v['source_sha256']));chosen=[];seen=set()
 for v in rows:
  if v['source_sha256'] in seen:continue
  chosen.append(v);seen.add(v['source_sha256'])
  if len(chosen)==4:break
 if len(chosen)!=4:raise ValueError('four distinct source inputs required')
 return chosen
def manifest(items):return {'format':'hcl-quantifier-logicskills-dev-v01','revision':REVISION,'data_sha256':DATA_SHA,'salt':SALT,'excluded_public_format_example_ids':EXCLUDE,'excluded_public_paper_sentences':PUBLIC_EXAMPLE_SENTENCES,'scope':'four source-only-selected controlled-language development inputs; no natural discourse/full/native/fresh efficacy claim','cases':[{k:v for k,v in i.items() if k!='source'} for i in items]}
def messages(item,arm):return [{'role':'system','content':COMMON+(' '+THIN if arm=='P' else '')},{'role':'user','content':json.dumps(item['source'],sort_keys=True)}]
def preflight(items):
 totals={a:sum(sum(len(m['content'].encode()) for m in messages(i,a)) for i in items) for a in ['C','P']}
 if len(items)!=4 or any(v>12000 for v in totals.values()):raise ValueError('call/input-byte cap exceeded')
 bound=((24000+8*1024)*.30+8*4096*1.20)/1e6
 assert bound<CAP
 return {'provider_calls':0,'cases':4,'max_calls':8,'input_byte_caps_per_arm':12000,'actual_input_bytes':totals,'output_token_cap_per_call_including_reasoning':4096,'rated_peak_usd_upper_bound':bound,'cap_usd':CAP,'thinking':'enabled','effort':'high','temperature':'not supplied; unsupported in thinking mode; no deterministic decoding claim'}
def parse_answer(raw,item):
 x=json.loads(raw)
 if not isinstance(x,dict) or set(x)!={'formula'}:raise ValueError('single formula JSON required')
 ast=parse(x['formula']);preds,constants=signature([ast]);key=item['source']['input'].split('Abbreviations:\n',1)
 if len(key)!=2:raise ValueError('public symbol key absent')
 import re
 declared={k:v for k,v in re.findall(r'^([A-Za-z]): (.+)$',key[1],re.M)}
 if any(p not in declared or arity!=len(set(re.findall(r'\[(\d+)\]',declared[p]))) for p,arity in preds.items()) or any(c not in declared for c in constants):raise ValueError('invented key symbol or arity mismatch')
 return x,ast

def execute(items,data,backends):
 rows=[dict(i,arms={}) for i in items];fail=[];outchars={a:0 for a in backends}
 for row in rows:
  for a in ['C','P']:
   ms=messages(row,a);row['arms'][a]={'actual_messages':ms,'response':None,'answer':None,'invalid_reason':None}
   try:
    response=backends[a].complete(ms);outchars[a]+=len(response['raw_response'])+response['reasoning_chars'];row['arms'][a]['response']=response
    try:ans,ast=parse_answer(response['raw_response'],row);row['arms'][a]['answer']=ans
    except (ValueError,TypeError,KeyError):row['arms'][a]['invalid_reason']='invalid formula output'
    if outchars[a]>64000:raise RuntimeError('reasoning plus final character cap exceeded')
   except Exception as exc:
    if row['arms'][a]['response'] is None:row['arms'][a]['response']=getattr(backends[a],'last_attempt',None)
    fail.append({'id':row['id'],'arm':a,**transport_failure(exc)});break
  if fail:break
 # First native-form lookup only after ALL attempted provider calls have ended.
 byid={v['id']:v for v in data}
 for row in rows:
  try:
   row['reference_formula']=byid[row['id']]['form'];target=parse(row['reference_formula']);reference_error=None
  except Exception as exc:row.setdefault('reference_formula',None);target=None;reference_error=type(exc).__name__
  for a,v in row['arms'].items():
   if reference_error:v['semantic_verification']={'status':'SCORER_ERROR','error_type':reference_error}
   elif v['answer']:
    try:ast=parse(v['answer']['formula']);v['semantic_verification']=equivalent(ast,target)
    except Exception as exc:v['semantic_verification']={'status':'SCORER_ERROR','error_type':type(exc).__name__}
   else:v['semantic_verification']={'status':'INVALID_OR_NOT_COMPLETED'}
 return rows,fail

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-file',type=Path,required=True);m=p.add_mutually_exclusive_group(required=True);m.add_argument('--freeze',action='store_true');m.add_argument('--validate-only',action='store_true');m.add_argument('--execute',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'artifacts/quantifier-logicskills-dev-v01/results.json');a=p.parse_args();data=load(a.source_file);items=select(data);f=manifest(items);check=preflight(items)
 if a.freeze:MANIFEST.parent.mkdir(parents=True,exist_ok=True);MANIFEST.write_text(json.dumps(f,indent=2)+'\n');print(json.dumps(check|{'manifest_sha256':sha(MANIFEST.read_bytes())}));return 0
 if f!=json.loads(MANIFEST.read_text()):raise ValueError('selection drift')
 if a.validate_only:print(json.dumps(check));return 0
 if os.getenv('GITHUB_ACTIONS')!='true' or os.getenv('GITHUB_RUN_ATTEMPT')!='1' or os.getenv('HCL_QUANTIFIER_LOGICSKILLS_DEV_RUN_ONCE_TOKEN')!=TOKEN:raise RuntimeError('separate first-attempt cloud token required')
 if float(os.getenv('HCL_QUANTIFIER_LOGICSKILLS_DEV_COST_AUTHORIZED_USD') or 0)<CAP:raise RuntimeError('separate quantifier authorization required')
 key=os.getenv('DEEPSEEK_API_KEY')
 if not key:raise RuntimeError('existing credential unavailable')
 ledger=BudgetLedger(cap_usd=CAP);bs={v:ReasoningBackend(key,ledger) for v in ['C','P']};rows,fail=execute(items,data,bs);models={v['response']['response_model'] for row in rows for v in row['arms'].values() if v['response'] and v['response']['response_model']};unknown=[row['id'] for row in rows if any(v['semantic_verification']['status'] in ('UNKNOWN','SCORER_ERROR') for v in row['arms'].values())]
 if len(models)>1:fail.append({'error_type':'ProviderModelDrift'})
 status='PARTIAL_DEVELOPMENT_CONSUMED' if fail else 'SCORING_INCONCLUSIVE' if unknown else 'SUCCESS'
 result={'format':f['format'],'scope':f['scope'],'status':status,'selection_sha256':sha(MANIFEST.read_bytes()),'results':rows,'failures':fail,'scorer_unknown_ids':unknown,'metrics':{a:{'calls':b.calls,'rated_cost_usd':b.cost,'wall_seconds':b.wall} for a,b in bs.items()},'total_ledger_usd':ledger.spent_usd};a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':status,'calls':sum(b.calls for b in bs.values()),'ledger_usd':ledger.spent_usd}));return 0 if status=='SUCCESS' else 1
if __name__=='__main__':sys.exit(main())
