"""Conditional FOL conclusions across explicit supplied readings.

No NL translator, benchmark labels, private mental truth or completeness claim.
Reuses generic equivalence; inconsistency and solver unknown remain distinct.
"""
import hashlib,json
from hcl.quantified_logic import FormulaError,parse,signature,equivalent,MAX_NODES

SCOPE='ALL_SUPPLIED_FORMAL_READINGS_ONLY_NOT_NL_OR_WORLD_TRUTH'

def _and(formulas):
 node=formulas[0]
 for formula in formulas[1:]:node=('and',node,formula)
 return node

def classify_reading(premises,conclusion,timeout_ms=500):
 """Classical full-FOL consequence conditional on a supplied formalization."""
 if not isinstance(premises,list) or not 1<=len(premises)<=16:raise FormulaError('one to16 formal premises required')
 if type(timeout_ms)is not int or not 1<=timeout_ms<=2000:raise FormulaError('bounded solver timeout required')
 nodes=[parse(p) for p in premises];c=parse(conclusion);signature(nodes+[c])
 def size(n):return 1+sum(size(v) for v in n[1:] if isinstance(v,tuple) and v and v[0] in ('atom','not','all','some','and','or','implies','iff'))
 if sum(size(n) for n in nodes+[c])>MAX_NODES:raise FormulaError('combined formula node limit')
 p=_and(nodes);contradiction=('and',c,('not',c))
 consistency=equivalent(p,contradiction,timeout_ms)
 out={'scope':SCOPE,'status':'UNKNOWN','label':None,'consistency_check':consistency}
 if consistency['status']=='EQUIVALENT':out['status']='INCONSISTENT_PREMISES';return out
 if consistency['status']=='UNKNOWN':return out
 entail=equivalent(p,('and',p,c),timeout_ms);refute=equivalent(p,('and',p,('not',c)),timeout_ms)
 out.update(entailment_check=entail,refutation_check=refute)
 e,r=entail['status'],refute['status']
 if 'UNKNOWN' in (e,r):return out
 if e=='EQUIVALENT' and r=='NOT_EQUIVALENT':out.update(status='CLASSIFIED',label='True')
 elif r=='EQUIVALENT' and e=='NOT_EQUIVALENT':out.update(status='CLASSIFIED',label='False')
 elif e==r=='NOT_EQUIVALENT':out.update(status='CLASSIFIED',label='Uncertain')
 else:out['status']='SOLVER_RESULT_CONFLICT'
 return out

def compare_readings(readings,timeout_ms=500):
 """Preserve each interpretation; never silently select a preferred reading."""
 if not isinstance(readings,list) or not 1<=len(readings)<=4:raise FormulaError('one to4 explicit readings required')
 identities=set();rows=[]
 for reading in readings:
  if not isinstance(reading,dict) or set(reading)!={'id','source_sha256','premises','conclusion'}:raise FormulaError('explicit reading identity/source digest/formulas required')
  rid=reading['id'];source=reading['source_sha256']
  if not isinstance(rid,str) or not 1<=len(rid)<=128 or rid in identities:raise FormulaError('unique bounded reading id required')
  if not isinstance(source,str) or len(source)!=64 or any(c not in '0123456789abcdef' for c in source):raise FormulaError('source SHA256 required')
  identities.add(rid);result=classify_reading(reading['premises'],reading['conclusion'],timeout_ms)
  rows.append({'id':rid,'source_sha256':source,'formalization_sha256':hashlib.sha256(json.dumps(reading,sort_keys=True).encode()).hexdigest(),**result})
 if len({r['source_sha256'] for r in rows})!=1:raise FormulaError('readings must concern the same declared source')
 status='UNRESOLVED_READING';label=None
 if all(r['status']=='CLASSIFIED' for r in rows):
  labels={r['label'] for r in rows}
  if len(labels)==1:status='AGREEMENT_ACROSS_SUPPLIED_READINGS';label=rows[0]['label']
  else:status='READING_DEPENDENT'
 return {'scope':SCOPE,'status':status,'label':label,'readings':rows,'provider_calls':0,'nl_reading_completeness':'NOT_ESTABLISHED'}
