"""Metered single requests for a reasoning-enabled baseline; no retries or CoT dump."""
import hashlib,time
from scripts.run_v06_fantom_cpgd_fresh_v01 import (BudgetLedger,BASE_URL,MODEL,PEAK_INPUT_CACHE_HIT_USD_PER_M,PEAK_INPUT_CACHE_MISS_USD_PER_M,PEAK_OUTPUT_USD_PER_M)
class ReasoningBackend:
 def __init__(self,key,ledger):
  from openai import OpenAI
  self.client=OpenAI(api_key=key,base_url=BASE_URL,max_retries=0,timeout=120);self.ledger=ledger;self.calls=0;self.cost=0.;self.wall=0.
 def complete(self,messages):
  bound=self.ledger.reserve_bound(messages,4096);self.calls+=1;start=time.perf_counter()
  actual={'model':MODEL,'messages':messages,'max_tokens':4096,'reasoning_effort':'high','top_p':1,'extra_body':{'thinking':{'type':'enabled'}},'response_format':{'type':'json_object'}}
  self.last_attempt={'actual_request':actual,'raw_response':None,'response_model':None}
  try:
   response=self.client.chat.completions.create(**actual);msg=response.choices[0].message;raw=msg.content or '';reason=getattr(msg,'reasoning_content',None)
   self.last_attempt.update({'raw_response':raw,'response_sha256':hashlib.sha256(raw.encode()).hexdigest(),'response_model':str(response.model) if response.model else None,'finish_reason':response.choices[0].finish_reason,'reasoning_chars':len(reason) if isinstance(reason,str) else None,'reasoning_sha256':hashlib.sha256(reason.encode()).hexdigest() if isinstance(reason,str) else None})
   usage=response.usage
   prompt=usage.prompt_tokens;total=usage.completion_tokens;details=getattr(usage,'completion_tokens_details',None);reason_tokens=getattr(details,'reasoning_tokens',None)
   hit=getattr(usage,'prompt_cache_hit_tokens',0) or 0;miss=getattr(usage,'prompt_cache_miss_tokens',prompt-hit)
   if any(type(v)is not int or v<0 for v in [prompt,total,hit,miss,reason_tokens]) or hit+miss!=prompt or not reason_tokens<=total<=4096:raise RuntimeError('invalid total/hidden-reasoning token usage')
   msg=response.choices[0].message;raw=msg.content or '';reason=getattr(msg,'reasoning_content',None)
   if not isinstance(reason,str) or not isinstance(raw,str) or not response.model:raise RuntimeError('reasoning/model identity absent')
   cost=(hit*PEAK_INPUT_CACHE_HIT_USD_PER_M+miss*PEAK_INPUT_CACHE_MISS_USD_PER_M+total*PEAK_OUTPUT_USD_PER_M)/1e6
   if cost>bound:raise RuntimeError('usage exceeds pre-request reservation')
  except Exception:
   self.last_attempt['accounting']='FULL_RESERVATION_AFTER_FAILURE'
   self.ledger.charge(bound);self.cost+=bound;raise
  finally:self.wall+=time.perf_counter()-start
  self.ledger.charge(cost);self.cost+=cost
  return {'actual_request':actual,'raw_response':raw,'response_sha256':hashlib.sha256(raw.encode()).hexdigest(),'response_model':str(response.model),'reasoning_chars':len(reason),'reasoning_sha256':hashlib.sha256(reason.encode()).hexdigest(),'usage':{'prompt_tokens':prompt,'completion_tokens':total,'reasoning_tokens':reason_tokens,'cache_hit_tokens':hit,'cache_miss_tokens':miss},'finish_reason':response.choices[0].finish_reason,'rated_cost_usd':cost}
