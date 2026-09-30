"""Future shared C/P/G/H reference resource; old v9/scorer/runs unchanged."""
from copy import deepcopy
import hashlib,json
from hcl.cognition.core import Scope
from hcl.cognition.semantic import AuthorizedText
from scripts.serious_eval_source_reference_v1 import SourceReferenceIndex,MAX_REFERENCES
from scripts.serious_eval_full_source_arms_v9 import prepare_primary_arms_v9,prepare_generic_final_v9,validate_sources,MAX_MAP_BYTES,LIMITS,digest
from scripts.serious_eval_arms_v4 import _unique_object
from scripts.serious_eval_semantic_score import validate_answer
QUALIFICATION='C_P_G_V10_SHARED_SOURCE_LOCATOR_PROVIDER_FREE_UNQUALIFIED'
_POLICY=(' A common read-only source-reference locator is available to all methods. '
    'It can retrieve the unique original source span when a proposed quote differs '
    'only in whitespace layout. Original source bytes, words, punctuation, negation, '
    'actor and scope remain unchanged; ambiguous, stale or lexically changed '
    'references are rejected. This checks a reference, not a semantic claim. ')

def index_sources(sources):
    validate_sources(sources)
    items=tuple(AuthorizedText(s['source_id'],s['text']) for s in sources)
    return SourceReferenceIndex(items,Scope(source_ids=tuple(s.source_id for s in items)))

def _resolve(index,sid,quote):
    versions=index.versions()
    if sid not in versions:raise ValueError('source outside reference view')
    return index.locate(sid,quote,expected_version=versions[sid]['version'],expected_sha256=versions[sid]['source_sha256'])

def prepare_primary_arms_v10(question,source_id,source_text):
    p=prepare_primary_arms_v9(question,source_id,source_text)
    for phase in ('C','P','G_map'):p[phase][0]['content']+=_POLICY
    p['qualification']=QUALIFICATION;p['shared_reference_resource']='SOURCE_SPAN_ONLY_V1_ALL_ARMS'
    p['prepared_sha256']=digest({k:v for k,v in p.items() if k!='prepared_sha256'})
    return p

def prepare_generic_final_v10(prepared,raw_map):
    if (prepared.get('qualification')!=QUALIFICATION or prepared.get('prepared_sha256')!=digest({k:v for k,v in prepared.items() if k!='prepared_sha256'})):raise ValueError('intact versioned prepared comparator required')
    if not isinstance(raw_map,str) or len(raw_map.encode())>MAX_MAP_BYTES:raise ValueError('raw map resource bound')
    original=json.loads(raw_map,object_pairs_hook=_unique_object)
    if not isinstance(original,dict) or set(original)!=set(LIMITS) or any(not isinstance(original[k],list) or len(original[k])>limit for k,limit in LIMITS.items()):raise ValueError('bounded exact generic map fields required')
    mapped=deepcopy(original);index=index_sources(prepared['ordinary_payload']['sources']);receipts=[]
    for row in mapped['source_index']:
        if not isinstance(row,dict) or set(row)!={'id','source_id','quote'}:raise ValueError('exact reference row fields required')
        receipt=_resolve(index,row['source_id'],row['quote']);row['quote']=receipt['quote'];receipts.append(dict(row_id=row['id'],**receipt))
    resolved=json.dumps(mapped,ensure_ascii=False,sort_keys=True)
    if len(resolved.encode())>MAX_MAP_BYTES:raise ValueError('retrieved map exceeds unchanged map byte bound')
    # Rebuild unchanged v9 comparator on the same ordinary inputs, then use its
    # relation/plan/schema/citation validation. No oracle fields reach G final.
    u=prepared['ordinary_payload']
    if len(u['sources'])!=1:raise ValueError('v9/v10 G entry requires one complete source; never drop extra sources')
    source=u['sources'][0]
    legacy=prepare_primary_arms_v9(u['question'],source['source_id'],source['text'])
    messages=prepare_generic_final_v9(legacy,resolved);messages[0]['content']+=_POLICY
    return dict(messages=messages,reference_receipt=dict(schema='hcl-i02-shared-reference-map-v1',raw_map=raw_map,raw_map_sha256=hashlib.sha256(raw_map.encode()).hexdigest(),resolved_map=resolved,references=receipts,semantic_qualification=False,provider_calls=0))

def resolve_final_references(raw_answer,sources,*,scope=None):
    # Scope-aware H may pass AuthorizedText directly; ordinary C/P/G uses the
    # same version1 public source view. No repository or hidden-source lookup.
    if isinstance(sources,tuple):
        if scope is None:raise ValueError('authorized typed sources require explicit scope')
        index=SourceReferenceIndex(sources,scope);visible=[dict(source_id=s.source_id,text=s.text) for s in sources if s.visible_to(scope)]
    else:
        if scope is not None:raise ValueError('explicit scope requires typed authorized sources')
        index=index_sources(sources);visible=sources
    if not isinstance(raw_answer,str) or len(raw_answer.encode())>128000:raise ValueError('bounded raw final JSON required')
    original=json.loads(raw_answer,object_pairs_hook=_unique_object)
    if not isinstance(original,dict) or set(original)!={'answer','source_citations','uncertainty','assumptions'} or not isinstance(original['source_citations'],list) or len(original['source_citations'])>MAX_REFERENCES:raise ValueError('shared ordinary final contract required')
    answer=deepcopy(original);receipts=[]
    for row in answer['source_citations']:
        if not isinstance(row,dict) or set(row)!={'source_id','quote'}:raise ValueError('source references only; no oracle or answer fields')
        receipt=_resolve(index,row['source_id'],row['quote']);row['quote']=receipt['quote'];receipts.append(receipt)
    validate_answer(answer,{s['source_id']:s['text'] for s in visible})
    return dict(answer=answer,reference_receipt=dict(schema='hcl-i02-shared-reference-final-v1',raw_answer=raw_answer,raw_answer_sha256=hashlib.sha256(raw_answer.encode()).hexdigest(),references=receipts,semantic_qualification=False,provider_calls=0))

def prepare_h_with_shared_references(layer,query,narrative,**kwargs):
    """Future common resource on actual ordinary H preparation, no extra source/state."""
    from dataclasses import replace
    from hcl.v1 import prepare_person_context
    p=prepare_person_context(layer,query,narrative,**kwargs)
    payload=json.loads(p.messages[-1]['content']);sources=payload.get('sources')
    if not isinstance(sources,list) or not sources or any(set(row)!={'source_id','version','text'} for row in sources):raise ValueError('actual authorized H source view required; never fall back to caller narrative')
    view=payload.get('scope')
    if not isinstance(view,dict) or view.get('observer') is not None:raise ValueError('actual public H scope required; no raw-source fallback')
    scope=Scope(**dict(view,source_ids=tuple(view['source_ids']),assumptions=tuple(view['assumptions'])))
    typed=tuple(AuthorizedText(s['source_id'],s['text'],version=s['version']) for s in sources)
    if set(SourceReferenceIndex(typed,scope).versions())!={s.source_id for s in typed}:raise ValueError('unprepared source time/access view; no fallback')
    messages=deepcopy(list(p.messages));messages[0]['content']+=_POLICY
    if len(json.dumps(messages,ensure_ascii=False))>p.plan.max_context_chars:raise ValueError('shared reference policy exceeds unchanged H context budget')
    receipt=dict(p.preparation_receipt,shared_reference_resource='SOURCE_SPAN_ONLY_V1_ALL_ARMS',actual_final_messages=messages)
    return replace(p,messages=tuple(messages),preparation_receipt=receipt)

def answer_h_with_shared_references(layer,query,narrative,**kwargs):
    p=prepare_h_with_shared_references(layer,query,narrative,**kwargs)
    raw=layer.base_model(list(p.messages)) if callable(layer.base_model) else layer.base_model.complete(list(p.messages))
    payload=json.loads(p.messages[-1]['content'])
    typed=tuple(AuthorizedText(s['source_id'],s['text'],version=s['version']) for s in payload['sources'])
    view=payload['scope'];scope=Scope(**dict(view,source_ids=tuple(view['source_ids']),assumptions=tuple(view['assumptions'])))
    result=resolve_final_references(raw,typed,scope=scope)
    return dict(prepared=p,result=result,final_model_calls=1)
