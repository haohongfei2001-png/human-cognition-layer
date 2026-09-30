"""Provider-free complete-source comparators; historical v1-v8 stay immutable.

A longer ordinary source is never excerpted to satisfy the old 64k envelope.
Generic workspace semantics remain model proposals; this does not qualify a
source, model, H treatment, or any paid execution.
"""
from copy import deepcopy
import hashlib,json
from scripts.serious_eval_contract import FIELDS
from scripts.serious_eval_arms import _OUTPUT,_P,_G_FINAL
from scripts.serious_eval_arms_v3 import _GOAL_BOUNDARY
from scripts.serious_eval_arms_v4 import _unique_object
from scripts.serious_eval_arms_v8 import _CITATION_CONTRACT,call_spec_v8
from scripts.serious_eval_generic_workspace_v5 import GenericEvidenceWorkspace,_FINAL_POLICY,_MAP_POLICY
MAX_SOURCE_BYTES=500000
MAX_MAP_BYTES=24000
LIMITS={'source_index':32,'relations':32,'answer_plan':16,'open_questions':12}
QUALIFICATION='C_P_G_V9_FULL_SOURCE_PROVIDER_FREE_UNQUALIFIED'

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def validate_sources(sources):
    if (not isinstance(sources,list) or not 1<=len(sources)<=8 or
        any(not isinstance(s,dict) or set(s)!={'source_id','text'} or
            not isinstance(s['source_id'],str) or not s['source_id'].strip() or len(s['source_id'])>256 or
            not isinstance(s['text'],str) or not s['text'].strip() for s in sources) or
        len({s['source_id'] for s in sources})!=len(sources) or
        sum(len(s['text'].encode()) for s in sources)>MAX_SOURCE_BYTES):
        raise ValueError('bounded distinct complete authorized sources required; never truncate')

class FullSourceWorkspaceV9(GenericEvidenceWorkspace):
    def __init__(self,payload):
        validate_sources(payload.get('sources'))
        self._sources={s['source_id']:dict(text=s['text'],version=1) for s in payload['sources']}
        self._map=None;self._mapped_versions=None
    def revise_source(self,source_id,text):
        if source_id not in self._sources:raise ValueError('known source revision required')
        revised=[dict(source_id=sid,text=text if sid==source_id else s['text']) for sid,s in self._sources.items()]
        validate_sources(revised)
        if text!=self._sources[source_id]['text']:
            self._sources[source_id]=dict(text=text,version=self._sources[source_id]['version']+1)
            self._map=None;self._mapped_versions=None
    def ingest(self,raw_map):
        self._map=None;self._mapped_versions=None
        if not isinstance(raw_map,str) or len(raw_map.encode())>MAX_MAP_BYTES:
            raise ValueError('full-source generic map byte bound')
        mapped=json.loads(raw_map,object_pairs_hook=_unique_object)
        if not isinstance(mapped,dict) or set(mapped)!=set(LIMITS) or any(
            not isinstance(mapped[k],list) or len(mapped[k])>limit for k,limit in LIMITS.items()):
            raise ValueError('full-source generic map array bound')
        # Original quote/actor/source/version/relationship/plan validation remains.
        super().ingest(raw_map)
        self._map['schema']='hcl-i02-full-source-generic-workspace-v9'
        self._map['map_byte_length']=len(raw_map.encode())
        return self.snapshot()

def prepare_primary_arms_v9(question,source_id,source_text):
    if not isinstance(question,str) or not question.strip() or len(question)>8000:
        raise ValueError('bounded ordinary question required')
    sources=[dict(source_id=source_id,text=source_text)];validate_sources(sources)
    payload=dict(question=question,sources=sources,answer_fields=list(FIELDS))
    user=dict(role='user',content=json.dumps(payload,sort_keys=True,ensure_ascii=False))
    policy=(_MAP_POLICY+' The full-source resource envelope permits at most32 source_index rows,32 relations,16 plan rows and12 open questions, under24000 UTF-8 bytes; each quote remains at most1500 characters. IDs remain e1..e64, with no invented or ambiguous quotes. Use the complete source and retrieve counterevidence; no H-private cognitive states or oracle segmentation are supplied. ')
    prepared=dict(C=[dict(role='system',content=_CITATION_CONTRACT+_OUTPUT),deepcopy(user)],
        P=[dict(role='system',content=_CITATION_CONTRACT+_GOAL_BOUNDARY+_P),deepcopy(user)],
        G_map=[dict(role='system',content=policy),deepcopy(user)],ordinary_payload=deepcopy(payload),
        accounting=dict(C_calls=1,P_calls=1,G_map_calls=1,G_final_calls=1,all_input_output_tokens_and_latency_count=True),
        qualification=QUALIFICATION,call_specs={p:call_spec_v8(p) for p in ('C','P','G_map','G_final')},
        provider_calls_authorized=0,provider_spend_authorized_usd=0,semantic_qualification=False)
    prepared['prepared_sha256']=digest(prepared)
    return prepared

def prepare_generic_final_v9(prepared,raw_map):
    if (not isinstance(prepared,dict) or prepared.get('qualification')!=QUALIFICATION or
        prepared.get('prepared_sha256')!=digest({k:v for k,v in prepared.items() if k!='prepared_sha256'})):
        raise ValueError('intact full-source prepared comparator required')
    payload=prepared['ordinary_payload'];workspace=FullSourceWorkspaceV9(payload);mapped=workspace.ingest(raw_map)
    final_payload=dict(deepcopy(payload),generic_evidence_workspace=mapped)
    return [dict(role='system',content=_CITATION_CONTRACT+_FINAL_POLICY+_GOAL_BOUNDARY+_G_FINAL),
        dict(role='user',content=json.dumps(final_payload,sort_keys=True,ensure_ascii=False))]
