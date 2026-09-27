"""Generic bounded formula parsing, full FOL equivalence and finite witnesses.

Formal-input semantics only: no automatic NL translation or private mental truth.
No finite search failure is promoted to validity/necessity.
"""
import itertools,re

MAX_NODES=512
class FormulaError(ValueError):pass

def parse(text):
 if not isinstance(text,str) or len(text)>4000:raise FormulaError('bounded formula string required')
 s=re.sub(r'\s+','',text);pos=nodes=0
 def read(bound,depth=0):
  nonlocal pos,nodes
  nodes+=1
  if nodes>MAX_NODES or depth>64 or pos>=len(s):raise FormulaError('formula syntax/size limit')
  c=s[pos];pos+=1
  if c=='¬':return ('not',read(bound,depth+1))
  if c in '∀∃':
   if pos>=len(s) or s[pos] not in 'stuvwxyz':raise FormulaError('bound variable required')
   v=s[pos];pos+=1;return ('all' if c=='∀' else 'some',v,read(bound|{v},depth+1))
  if c=='(':
   left=read(bound,depth+1)
   if pos>=len(s) or s[pos] not in '∧∨→↔':raise FormulaError('binary connective required')
   op={'∧':'and','∨':'or','→':'implies','↔':'iff'}[s[pos]];pos+=1;right=read(bound,depth+1)
   if pos>=len(s) or s[pos]!=')':raise FormulaError('closing parenthesis required')
   pos+=1;return (op,left,right)
  if c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':raise FormulaError('predicate required')
  terms=[]
  while pos<len(s) and s[pos] in 'abcdefghijklmnopqrstuvwxyz':
   t=s[pos];pos+=1
   if t in 'stuvwxyz' and t not in bound:raise FormulaError('free variable')
   terms.append(t)
  if len(terms) not in (1,2):raise FormulaError('unary/binary predicate required')
  return ('atom',c,tuple(terms))
 ast=read(set())
 if pos!=len(s):raise FormulaError('trailing formula content')
 signature([ast]);return ast

def signature(formulas):
 preds={};constants=set()
 def walk(n):
  if n[0]=='atom':
   p,ts=n[1:]
   if p in preds and preds[p]!=len(ts):raise FormulaError('inconsistent predicate arity')
   preds[p]=len(ts);constants.update(t for t in ts if t in 'abcdefghijklmnopqr')
  elif n[0] in ('all','some'):walk(n[2])
  elif n[0]=='not':walk(n[1])
  else:walk(n[1]);walk(n[2])
 for n in formulas:walk(n)
 return preds,sorted(constants)

def validate_model(model,formulas):
 preds,constants=signature(formulas)
 if not isinstance(model,dict) or set(model)!={'domain','constants','predicates'}:raise FormulaError('complete finite interpretation required')
 d=model['domain'];cs=model['constants'];ps=model['predicates']
 if not isinstance(d,list) or not 1<=len(d)<=4 or any(type(x)is not int for x in d) or d!=list(range(len(d))):raise FormulaError('explicit nonempty domain 0..n-1 up to4 required')
 if not isinstance(cs,dict) or set(cs)!=set(constants) or any(type(v)is not int or v not in d for v in cs.values()):raise FormulaError('complete in-domain constants required')
 if not isinstance(ps,dict) or set(ps)!=set(preds):raise FormulaError('complete predicate signature required')
 normalized={}
 for p,arity in preds.items():
  ext=ps[p]
  if not isinstance(ext,list):raise FormulaError('predicate extension list required')
  tuples=[]
  for entry in ext:
   t=[entry] if arity==1 else entry
   if not isinstance(t,list) or len(t)!=arity or any(type(i)is not int or i not in d for i in t):raise FormulaError('extension arity/domain violation')
   tuples.append(tuple(t))
  if len(tuples)!=len(set(tuples)):raise FormulaError('duplicate extension')
  normalized[p]=set(tuples)
 return d,dict(cs),normalized

def evaluate(ast,model):
 d,cs,ps=validate_model(model,[ast]);fuel=20000
 def ev(n,env):
  nonlocal fuel
  fuel-=1
  if fuel<0:raise FormulaError('evaluation work limit')
  op=n[0]
  if op=='atom':return tuple(env[t] if t in env else cs[t] for t in n[2]) in ps[n[1]]
  if op=='not':return not ev(n[1],env)
  if op in ('all','some'):
   vals=[ev(n[2],env|{n[1]:i}) for i in d];return all(vals) if op=='all' else any(vals)
  a=ev(n[1],env);b=ev(n[2],env)
  return {'and':a and b,'or':a or b,'implies':not a or b,'iff':a==b}[op]
 return ev(ast,{})

def check_countermodel(premises,conclusion,model):
 # Shared signature may include symbols absent from individual formulas.
 validate_model(model,premises+[conclusion])
 def projected(n):
  ps,cs=signature([n]);return {'domain':model['domain'],'constants':{c:model['constants'][c] for c in cs},'predicates':{p:model['predicates'][p] for p in ps}}
 vals=[evaluate(p,projected(p)) for p in premises];c=evaluate(conclusion,projected(conclusion))
 return {'scope':'FORMAL_INTERPRETATION_NOT_WORLD_OR_PRIVATE_MENTAL_TRUTH','premises':vals,'conclusion':c,'is_countermodel':all(vals) and not c}

def find_countermodel(premises,conclusion,domain_size=2,timeout_ms=2000):
 import z3
 if type(domain_size)is not int or not 1<=domain_size<=4:raise FormulaError('bounded nonempty domain required')
 preds,constants=signature(premises+[conclusion]);d=list(range(domain_size));s=z3.Solver();s.set(timeout=timeout_ms)
 cs={c:z3.Int('constant_'+c) for c in constants};tables={p:{t:z3.Bool(p+'_'+ '_'.join(map(str,t))) for t in itertools.product(d,repeat=arity)} for p,arity in preds.items()}
 for v in cs.values():s.add(v>=0,v<domain_size)
 fuel=20000
 def translate(n,env):
  nonlocal fuel
  fuel-=1
  if fuel<0:raise FormulaError('finite expansion work limit')
  op=n[0]
  if op=='atom':
   terms=[env[t] if t in env else cs[t] for t in n[2]]
   return z3.Or([z3.And([v==i for v,i in zip(terms,t)]+[cell]) for t,cell in tables[n[1]].items()])
  if op=='not':return z3.Not(translate(n[1],env))
  if op in ('all','some'):
   vals=[translate(n[2],env|{n[1]:z3.IntVal(i)}) for i in d];return z3.And(vals) if op=='all' else z3.Or(vals)
  a,b=translate(n[1],env),translate(n[2],env)
  return {'and':z3.And,'or':z3.Or,'implies':z3.Implies,'iff':lambda a,b:a==b}[op](a,b)
 for p in premises:s.add(translate(p,{}))
 s.add(z3.Not(translate(conclusion,{})));status=s.check()
 if status!=z3.sat:return {'status':'NO_COUNTERMODEL_IN_THIS_DOMAIN' if status==z3.unsat else 'UNKNOWN','domain_size':domain_size,'entailment':'UNRESOLVED','model':None}
 m=s.model();model={'domain':d,'constants':{c:m.eval(v,model_completion=True).as_long() for c,v in cs.items()},'predicates':{p:[t[0] if preds[p]==1 else list(t) for t,v in entries.items() if z3.is_true(m.eval(v,model_completion=True))] for p,entries in tables.items()}}
 proof=check_countermodel(premises,conclusion,model)
 if not proof['is_countermodel']:raise RuntimeError('solver witness fails independent evaluation')
 return {'status':'VERIFIED_FINITE_COUNTERMODEL','domain_size':domain_size,'entailment':'NOT_ENTAILED','model':model,'verification':proof}

def equivalent(left,right,timeout_ms=2000):
 """Full first-order equivalence. No finite-domain absence shortcut."""
 import z3
 # A verified finite witness suffices to refute full equivalence. Failure does not.
 for size in (1,2):
  for direction,a,b in [('left_true_right_false',left,right),('right_true_left_false',right,left)]:
   try:w=find_countermodel([a],b,size,min(timeout_ms,200))
   except FormulaError:continue
   if w['status']=='VERIFIED_FINITE_COUNTERMODEL':return {'status':'NOT_EQUIVALENT','scope':'FULL_FOL_FORMAL_INPUT_ONLY','direction':direction,'countermodel':w}
 preds,constants=signature([left,right]);u=z3.DeclareSort('FormalDomain');cs={c:z3.Const(c,u) for c in constants};ps={p:z3.Function(p,*([u]*arity),z3.BoolSort()) for p,arity in preds.items()}
 def tr(n,env,depth=0):
  op=n[0]
  if op=='atom':return ps[n[1]](*[env[t] if t in env else cs[t] for t in n[2]])
  if op=='not':return z3.Not(tr(n[1],env,depth+1))
  if op in ('all','some'):
   v=z3.Const(n[1]+'_'+str(depth),u);f=tr(n[2],env|{n[1]:v},depth+1);return z3.ForAll([v],f) if op=='all' else z3.Exists([v],f)
  a,b=tr(n[1],env,depth+1),tr(n[2],env,depth+1)
  return {'and':z3.And,'or':z3.Or,'implies':z3.Implies,'iff':lambda a,b:a==b}[op](a,b)
 s=z3.Solver();s.set(timeout=timeout_ms);s.add(z3.Xor(tr(left,{}),tr(right,{})));v=s.check()
 return {'status':'EQUIVALENT' if v==z3.unsat else 'NOT_EQUIVALENT' if v==z3.sat else 'UNKNOWN','scope':'FULL_FOL_FORMAL_INPUT_ONLY','reason_unknown':s.reason_unknown() if v==z3.unknown else None}
