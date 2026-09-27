"""Source-only explicit formal argument countermodels; C/P plus deterministic tool."""
import argparse,hashlib,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from hcl.quantified_logic import parse,signature,check_countermodel,find_countermodel
from scripts.reasoning_probe_backend import ReasoningBackend,BudgetLedger
from scripts.run_narrative_torque_dev_v02 import transport_failure
REVISION='31b175699127b766e64eb0c550893396404f665b'
DATA_SHA='cd57f6d31afa19e83e48e087b22db4296a7ef9f56ff83aa3324f39a62cef60c0'
SALT='HCL-ARGUMENT-COUNTERMODEL-DEVELOPMENT-V01'
TOKEN='HCL_ARGUMENT_COUNTERMODEL_DEV_V01_ONCE'
CAP=.05
EXCLUDE=['62d4f6152155aa29']
MANIFEST=ROOT/'eval/conceptual/logicskills_argument_countermodel_selection_v01.json'
COMMON=('Construct a countermodel for the supplied explicit formal argument: all premises true and conclusion false. Return JSON only with exactly domain, constants, predicates. Domain must be [0,1,2]. Constants maps each lowercase named constant to one domain integer; predicates maps each unary uppercase predicate to a list of integers and each binary predicate to a list of two-integer lists. Assign exactly every symbol used, with no duplicate extension entries. Empty predicate extensions allowed. Bound variables are not constants. Distinct named constants may denote the same individual. Interpret forall/exists, negation and implication with ordinary classical first-order semantics. Do not return prose, a formula or a solver program. This is conditional formal reasoning, not empirical or private mental truth.')
THIN=('Track each predicate arity, bound variable and named constant. Evaluate every premise and the negated conclusion in the same interpretation; reject candidates where any premise is false. Search small relation extensions deliberately, preserving quantifier scopes. A merely plausible interpretation is insufficient; check all three domain individuals for universal claims.')
def sha(b):return hashlib.sha256(b.encode() if isinstance(b,str) else b).hexdigest()
def argument(text):
 marker='Argument:\n\n'
 if text.count(marker)!=1:raise ValueError('argument source marker')
 raw=text.split(marker)[1].strip()
 if raw.count(' |= ')!=1:raise ValueError('consequence marker')
 before,conclusion=raw.split(' |= ');parts=[];start=0;depth=0
 for i,c in enumerate(before):
  if c=='(':depth+=1
  elif c==')':depth-=1
  elif c==',' and depth==0:parts.append(before[start:i].strip());start=i+1
  if depth<0:raise ValueError('source parenthesis')
 if depth:raise ValueError('source parenthesis')
 parts.append(before[start:].strip())
 if not 1<=len(parts)<=16:raise ValueError('premise count')
 asts=[parse(x) for x in parts];target=parse(conclusion.strip());signature(asts+[target])
 return parts,conclusion.strip(),asts,target

def load(path):
 b=path.read_bytes()
 if sha(b)!=DATA_SHA:raise ValueError('pinned source digest')
 x=json.loads(b)
 if len(x)!=300 or any(not isinstance(k,str) or not isinstance(v,str) for k,v in x.items()):raise ValueError('source schema')
 return x

def select(data):
 items=[]
 for k,text in data.items():
  if k in EXCLUDE:continue
  premises,conclusion,_,_=argument(text)
  source={'public_task':text,'premises':premises,'conclusion':conclusion,'domain':[0,1,2],'scope':'FORMAL_ARGUMENT_NOT_WORLD_OR_PRIVATE_MENTAL_TRUTH'}
  items.append({'id':k,'source':source,'source_sha256':sha(json.dumps(source,sort_keys=True))})
 items.sort(key=lambda v:sha(SALT+'|'+v['source_sha256']));chosen=[];seen=set()
 for v in items:
  if v['source_sha256'] in seen:continue
  chosen.append(v);seen.add(v['source_sha256'])
  if len(chosen)==4:break
 if len(chosen)!=4:raise ValueError('four source-distinct arguments')
 return chosen

def manifest(items):return {'format':'hcl-argument-countermodel-dev-v01','revision':REVISION,'data_sha256':DATA_SHA,'salt':SALT,'excluded_format_example_ids':EXCLUDE,'scope':'Four development explicit formal countermodel tasks; no NL translation/fresh/general cognition claim','cases':[{k:v for k,v in x.items() if k!='source'} for x in items]}
def messages(item,arm):return [{'role':'system','content':COMMON+(' '+THIN if arm=='P' else '')},{'role':'user','content':json.dumps(item['source'],sort_keys=True)}]
def preflight(items):
 totals={a:sum(sum(len(m['content'].encode()) for m in messages(i,a)) for i in items) for a in ['C','P']}
 bound=((24000+8*1024)*.30+8*4096*1.20)/1e6
 if len(items)!=4 or any(x>12000 for x in totals.values()) or bound>=CAP:raise ValueError('frozen cap')
 return {'provider_calls':0,'max_calls':8,'input_utf8bytes':totals,'input_byte_caps_per_arm':12000,'output_tokens_per_call_including_reasoning':4096,'reasoning_plus_final_char_caps_per_arm':64000,'rated_peak_upper_bound_usd':bound,'cap_usd':CAP,'thinking':'enabled','effort':'high','tool':'zero-provider generic source-only finite search, fixed domain3/timeout2000ms'}
def model_answer(raw,item):
 model=json.loads(raw)
 if not isinstance(model,dict) or set(model)!={'domain','constants','predicates'} or model['domain']!=[0,1,2]:raise ValueError('exact interpretation JSON/domain required')
 ps=[parse(v) for v in item['source']['premises']];c=parse(item['source']['conclusion']);return model,check_countermodel(ps,c,model)
def execute(items,backends):
 rows=[dict(x,arms={}) for x in items];fail=[];chars={a:0 for a in backends}
 for row in rows:
  for a in ['C','P']:
   ms=messages(row,a);v={'actual_messages':ms,'response':None,'model':None,'verification':None,'invalid_reason':None};row['arms'][a]=v
   try:
    resp=backends[a].complete(ms);v['response']=resp;chars[a]+=len(resp['raw_response'])+resp['reasoning_chars']
    if chars[a]>64000:raise RuntimeError('reasoning plus final character cap')
   except Exception as exc:
    if v['response'] is None:v['response']=getattr(backends[a],'last_attempt',None)
    fail.append({'id':row['id'],'arm':a,**transport_failure(exc)});break
  if fail:break
 # No paid corrections, no reference models; independent scoring after all calls.
 for row in rows:
  for a,v in row['arms'].items():
   if not v['response'] or v['response'].get('raw_response') is None:continue
   try:v['model'],v['verification']=model_answer(v['response']['raw_response'],row)
   except (ValueError,TypeError,KeyError):v['invalid_reason']='invalid interpretation JSON'
   except Exception as exc:v['verification']={'status':'SCORER_ERROR','error_type':type(exc).__name__}
  ps=[parse(x) for x in row['source']['premises']];c=parse(row['source']['conclusion'])
  try:row['arms']['T']={'provider_calls':0,'tool':find_countermodel(ps,c,3,2000)}
  except Exception as exc:row['arms']['T']={'provider_calls':0,'tool':{'status':'SCORER_ERROR','error_type':type(exc).__name__}}
 return rows,fail

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-file',type=Path,required=True);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--freeze',action='store_true');g.add_argument('--validate-only',action='store_true');g.add_argument('--execute',action='store_true');p.add_argument('--out',type=Path,default=ROOT/'artifacts/argument-countermodel-dev-v01/results.json');a=p.parse_args();data=load(a.source_file);items=select(data);m=manifest(items);plan=preflight(items)
 if a.freeze:MANIFEST.parent.mkdir(parents=True,exist_ok=True);MANIFEST.write_text(json.dumps(m,indent=2)+'\n');print(json.dumps(plan));return 0
 if json.loads(MANIFEST.read_text())!=m:raise ValueError('selection drift')
 if a.validate_only:print(json.dumps(plan));return 0
 if os.getenv('GITHUB_ACTIONS')!='true' or os.getenv('GITHUB_RUN_ATTEMPT')!='1' or os.getenv('HCL_ARGUMENT_COUNTERMODEL_DEV_RUN_ONCE_TOKEN')!=TOKEN:raise RuntimeError('separate first-attempt authorization token')
 if float(os.getenv('HCL_ARGUMENT_COUNTERMODEL_DEV_COST_AUTHORIZED_USD') or 0)<CAP or not os.getenv('DEEPSEEK_API_KEY'):raise RuntimeError('new independent authorization/credential required')
 ledger=BudgetLedger(cap_usd=CAP);backends={v:ReasoningBackend(os.environ['DEEPSEEK_API_KEY'],ledger) for v in ['C','P']};rows,fail=execute(items,backends);models={v['response']['response_model'] for row in rows for k,v in row['arms'].items() if k!='T' and v.get('response') and v['response'].get('response_model')}
 if len(models)>1:fail.append({'error_type':'ProviderModelDrift'})
 scorer_error=any((v.get('verification') or v.get('tool') or {}).get('status')=='SCORER_ERROR' for row in rows for v in row['arms'].values());status='PARTIAL_DEVELOPMENT_CONSUMED' if fail else 'SCORING_INCONCLUSIVE' if scorer_error else 'SUCCESS'
 result={'format':m['format'],'scope':m['scope'],'status':status,'selection_sha256':sha(MANIFEST.read_bytes()),'results':rows,'failures':fail,'metrics':{k:{'calls':b.calls,'rated_cost_usd':b.cost,'wall_seconds':b.wall} for k,b in backends.items()},'total_ledger_usd':ledger.spent_usd};a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':status,'calls':sum(b.calls for b in backends.values()),'ledger_usd':ledger.spent_usd}));return 0 if status=='SUCCESS' else 1
if __name__=='__main__':sys.exit(main())
