"""Four independent NL argument sources; provisional native annotation agreement."""
import argparse,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.reasoning_probe_backend import ReasoningBackend,BudgetLedger
from scripts.run_narrative_torque_dev_v02 import transport_failure
REVISION='5d7bb84c7edab3fb358e057d2807f19cf5cf5e2d'
DATA_SHA='6922c988ef10987bd6545568ee8e63e897af80994591fa20539767da58f8e3d1'
SALT='HCL-NATURAL-ARGUMENT-FOLIO-DEVELOPMENT-V01'
TOKEN='HCL_NATURAL_ARGUMENT_FOLIO_DEV_V01_ONCE'
CAP=.05
MANIFEST=ROOT/'eval/conceptual/folio_natural_argument_dev_selection_v01.json'
EXPOSED=['If people work in student jobs on campus']
LABELS={'True','False','Uncertain'}
COMMON=('Read all supplied natural-language premises and the conclusion. Treat premises as stipulated in this task, not verified world facts. Classify the conclusion: True if it follows, False if its negation follows, Uncertain if neither follows. Absence of support does not establish False. Respect quantifiers, named individuals, clause scope and negation. Use only supplied premises, no external factual/moral/private-mental assumptions. Return exactly one JSON object with only label, one of True, False, Uncertain. No extra fields, prose or markdown. Output syntax example only: {"label":"Uncertain"}; this is not the answer.')
THIN=('Track which individuals and quantifiers each premise concerns, and distinguish the stated relation from its converse. Check whether the conclusion or its negation actually follows; consider a consistent alternative interpretation before claiming entailment. Do not invent existential assumptions or equate all named individuals. This procedure supplies no reference label or formalization.')
def sha(b):return hashlib.sha256(b.encode() if isinstance(b,str) else b).hexdigest()
def load(path):
 b=path.read_bytes()
 if sha(b)!=DATA_SHA:raise ValueError('pinned source digest mismatch')
 data=[json.loads(x) for x in b.splitlines()]
 if len(data)!=204 or any(not isinstance(x['premises'],list) or not all(isinstance(p,str) for p in x['premises']) or not isinstance(x['conclusion'],str) for x in data):raise ValueError('source schema')
 return data

def select(data):
 stories={}
 for index,x in enumerate(data):
  if any(t.lower() in p.lower() for t in EXPOSED for p in x['premises']):continue
  story=sha(json.dumps(x['premises'],ensure_ascii=False));source={'premises':x['premises'],'conclusion':x['conclusion'],'scope':'CONDITIONAL_NL_ARGUMENT_NOT_WORLD_OR_PRIVATE_MENTAL_TRUTH'}
  item={'row_index':index,'story_sha256':story,'source_sha256':sha(json.dumps(source,sort_keys=True)),'source':source}
  stories.setdefault(story,[]).append(item)
 representatives=[min(rows,key=lambda x:sha(SALT+'|question|'+x['source_sha256'])) for rows in stories.values()]
 representatives.sort(key=lambda x:sha(SALT+'|story|'+x['story_sha256']))
 if len(representatives)<4:raise ValueError('four independent premise families required')
 return representatives[:4]
def manifest(items):return {'format':'hcl-natural-argument-folio-dev-v01','revision':REVISION,'data_sha256':DATA_SHA,'salt':SALT,'exposed_premise_substrings_excluded':EXPOSED,'scope':'Older public v0.0 provisional native human-annotation agreement; source-first audit required, not corrected/latest/full/fresh/ground-truth cognition efficacy','cases':[{k:v for k,v in x.items() if k!='source'} for x in items]}
def messages(item,arm):return [{'role':'system','content':COMMON+(' '+THIN if arm=='P' else '')},{'role':'user','content':json.dumps(item['source'],sort_keys=True)}]
def preflight(items):
 totals={a:sum(sum(len(m['content'].encode()) for m in messages(x,a)) for x in items) for a in ['C','P']};bound=((24000+8*1024)*.30+8*4096*1.20)/1e6
 if len(items)!=4 or any(v>12000 for v in totals.values()) or bound>=CAP:raise ValueError('frozen budget cap')
 return {'provider_calls':0,'max_calls':8,'actual_input_utf8bytes':totals,'input_cap_per_arm':12000,'output_total_tokens_per_call':4096,'reasoning_plus_final_chars_per_arm':64000,'rated_peak_bound_usd':bound,'cap_usd':CAP,'thinking':'enabled','effort':'high'}
def parse_answer(raw):
 x=json.loads(raw)
 if not isinstance(x,dict) or set(x)!={'label'} or x['label'] not in LABELS:raise ValueError('exact label JSON required')
 return x

def execute(items,data,backends):
 rows=[dict(x,arms={}) for x in items];fail=[];chars={a:0 for a in backends}
 for row in rows:
  for a in ['C','P']:
   ms=messages(row,a);v={'actual_messages':ms,'response':None,'answer':None,'invalid_reason':None};row['arms'][a]=v
   try:
    resp=backends[a].complete(ms);v['response']=resp;chars[a]+=len(resp['raw_response'])+resp['reasoning_chars']
    try:v['answer']=parse_answer(resp['raw_response'])
    except (ValueError,TypeError,KeyError):v['invalid_reason']='invalid label output'
    if chars[a]>64000:raise RuntimeError('reasoning plus final character cap')
   except Exception as exc:
    if v['response'] is None:v['response']=getattr(backends[a],'last_attempt',None)
    fail.append({'row_index':row['row_index'],'arm':a,**transport_failure(exc)});break
  if fail:break
 # First native label/formal-annotation access after all provider attempts ended.
 for row in rows:
  try:
   native=data[row['row_index']];label=native['label']
   if label not in LABELS:raise ValueError('unsupported native label')
   row['native_annotation']={'label':label,'premises-FOL':native.get('premises-FOL'),'conclusion-FOL':native.get('conclusion-FOL')};err=None
  except Exception as exc:row['native_annotation']=None;err=type(exc).__name__
  for a,v in row['arms'].items():
   v['native_agreement']=None if err or not v['answer'] else v['answer']['label']==label
   v['reference_error']=err
 return rows,fail

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-file',type=Path,required=True);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--freeze',action='store_true');g.add_argument('--validate-only',action='store_true');g.add_argument('--execute',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'artifacts/natural-argument-folio-dev-v01/results.json');a=p.parse_args();data=load(a.source_file);items=select(data);m=manifest(items);plan=preflight(items)
 if a.freeze:MANIFEST.parent.mkdir(parents=True,exist_ok=True);MANIFEST.write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(plan));return 0
 if json.loads(MANIFEST.read_text())!=m:raise ValueError('selection drift')
 if a.validate_only:print(json.dumps(plan));return 0
 if os.getenv('GITHUB_ACTIONS')!='true' or os.getenv('GITHUB_RUN_ATTEMPT')!='1' or os.getenv('HCL_NATURAL_ARGUMENT_FOLIO_DEV_RUN_ONCE_TOKEN')!=TOKEN:raise RuntimeError('separate first-attempt cloud authorization token')
 if float(os.getenv('HCL_NATURAL_ARGUMENT_FOLIO_DEV_COST_AUTHORIZED_USD') or 0)<CAP or not os.getenv('DEEPSEEK_API_KEY'):raise RuntimeError('new independent financial authorization required')
 ledger=BudgetLedger(cap_usd=CAP);backends={a:ReasoningBackend(os.environ['DEEPSEEK_API_KEY'],ledger) for a in ['C','P']};rows,fail=execute(items,data,backends);models={v['response']['response_model'] for row in rows for v in row['arms'].values() if v['response'] and v['response'].get('response_model')}
 if len(models)>1:fail.append({'error_type':'ProviderModelDrift'})
 reference_error=any(v['reference_error'] for row in rows for v in row['arms'].values());status='PARTIAL_DEVELOPMENT_CONSUMED' if fail else 'REFERENCE_INCONCLUSIVE' if reference_error else 'SUCCESS'
 result={'format':m['format'],'scope':m['scope'],'status':status,'selection_sha256':sha(MANIFEST.read_bytes()),'results':rows,'failures':fail,'metrics':{a:{'calls':b.calls,'rated_cost_usd':b.cost,'wall_seconds':b.wall} for a,b in backends.items()},'total_ledger_usd':ledger.spent_usd};a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':status,'calls':sum(b.calls for b in backends.values()),'ledger_usd':ledger.spent_usd}));return 0 if status=='SUCCESS' else 1
if __name__=='__main__':sys.exit(main())
