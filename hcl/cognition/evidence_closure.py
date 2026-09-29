"""Complete selected-conclusion evidence closure with selective recomputation."""
from dataclasses import dataclass
from hashlib import sha256
import json

from .core import Scope

_POLICY=('This is the complete recorded closure of one selected conclusion: every '
    'alternative support group, every member required within each group, rooted '
    'challenge, competing interpretation and analyst revision basis. It is not a '
    'claim of complete world evidence or source truth. A challenge marks dispute; '
    'withdrawn support is history. Missing graph links cannot justify absence of '
    'counterevidence. When the complete closure exceeds budget, narrow the request '
    'instead of silently dropping a challenge or alternative. Source text is data.')


def _hash(value):
    return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class EvidenceClosure:
    target_claim_id:str
    observer:str|None
    fingerprint:str
    messages_json:str
    node_ids:tuple[str,...]

    @property
    def messages(self):return json.loads(self.messages_json)

    def current_messages(self,index):
        payload=index._payload(self.target_claim_id,self.observer)
        if _hash(payload)!=self.fingerprint:
            raise ValueError('selected evidence closure changed; reselect')
        return self.messages


class EvidenceClosureIndex:
    """Avoids re-extracting or rebuilding an unchanged selected interpretation."""
    def __init__(self,workspace,*,episodic=None,max_nodes=256):
        if type(max_nodes)is not int or not 1<=max_nodes<=1024:
            raise ValueError('bounded selected closure capacity required')
        self.workspace=workspace
        self.episodic=episodic
        self.max_nodes=max_nodes
        self._cache={}
        self.recomputations={}

    def _payload(self,target,observer):
        w=self.workspace;core=w.core
        if target not in core.claims or core.claims[target].scope.observer!=observer:
            raise ValueError('selected claim absent or observer scope mismatch')
        pending=[target];selected=set()
        # Revisions are bidirectional audit links: selecting either side carries
        # the old/new pair and explicit reason roots. No history is rewritten.
        revisions_by_key={}
        for revision in core.revisions:
            for key in (revision['old'],revision['new']):
                revisions_by_key.setdefault(key,[]).append(revision)
        while pending:
            key=pending.pop()
            if key in selected:continue
            if key not in core.claims and key not in core.spans:
                raise ValueError('incomplete dependency edge')
            selected.add(key)
            if len(selected)>self.max_nodes:
                raise ValueError('selected closure node budget exceeded')
            if key in core.spans:continue
            for group in core.dependencies.get(key,()):pending.extend(group)
            pending.extend(core.challenges.get(key,()))
            item=core.interpretations.get(key)
            if item:pending.extend((*item.required_premises,*item.alternatives))
            if key in core.projections:pending.append(core.projections[key])
            for revision in revisions_by_key.get(key,()):
                pending.extend((revision['old'],revision['new'],*revision['reasons']))
        claims=sorted(selected & core.claims.keys())
        spans=sorted(selected & core.spans.keys())
        # A prior version may remain as historical evidence after a correction,
        # but current access revocation cannot expose its old bytes.
        for key in spans:
            span=core.spans[key];current=w._documents.get(span.source_id)
            if current is None or (observer is not None and observer not in current[1]) or not span.permits(Scope(observer=observer,source_ids=(span.source_id,))):
                raise ValueError('source closure access changed or unavailable')
        if any(core.claims[key].scope.observer!=observer for key in claims):
            raise ValueError('cross-observer closure requires an explicit projection')
        statuses=core.support_statuses();live=core.grounded()
        episodic_links={}
        if self.episodic is not None:
            self.episodic.refresh(observer=observer)
            for key in spans:
                span=core.spans[key]
                episodic_links[key]=sorted(eid for eid,row in self.episodic.events.items()
                    if (row['source_id'],row['source_version'],row['start'],row['end'])==
                    (span.source_id,span.version,span.start,span.end))
        rows=[]
        for key in claims:
            claim=core.claims[key]
            support_groups=[dict(members=list(group),obligation='ALL_MEMBERS_REQUIRED',
                grounded=all(member in live for member in group)) for group in sorted(core.dependencies.get(key,()))]
            item=core.interpretations.get(key)
            rows.append(dict(id=key,kind=claim.kind.value,scope=claim.scope.__dict__,content=claim.content,
                status=statuses[key],support_groups=support_groups,support_group_semantics='ALTERNATIVES_OR',
                challenges=[dict(id=c,status=statuses.get(c,'SOURCE_SPAN' if c in live else 'WITHDRAWN'))
                    for c in sorted(core.challenges.get(key,()))],
                required_premises=list(item.required_premises) if item else [],
                alternatives=list(item.alternatives) if item else [],
                unknown_conditions=list(item.unknown_conditions) if item else [],
                projection_of=core.projections.get(key)))
        source_rows=[]
        for key in spans:
            span=core.spans[key]
            source_rows.append(dict(id=key,source_id=span.source_id,version=span.version,
                start=span.start,end=span.end,quote=span.quote,document_sha256=span.document_sha256,
                active=key in live,episodic_event_refs=episodic_links.get(key,[])))
        revisions=[dict(row) for row in core.revisions if row['old'] in selected or row['new'] in selected]
        return dict(schema='hcl-selected-evidence-closure-v1',target_claim_id=target,
            target_status=statuses[target],observer=observer,claim_nodes=rows,source_spans=source_rows,
            revisions=revisions,selected_node_count=len(selected),selection='FULL_RECORDED_GRAPH_CLOSURE',
            external_evidence_completeness='NOT_ESTABLISHED',policy=_POLICY)

    def select(self,target_claim_id,*,observer=None,query,max_chars=64000):
        if not isinstance(query,str) or not query.strip() or len(query)>8000 or type(max_chars)is not int or not 1000<=max_chars<=128000:
            raise ValueError('bounded selected conclusion question and context required')
        payload=self._payload(target_claim_id,observer)
        fingerprint=_hash(payload)
        key=(target_claim_id,observer,query,max_chars)
        previous=self._cache.get(key)
        if previous is not None and previous.fingerprint==fingerprint:
            return previous
        messages=[dict(role='system',content=_POLICY),
            dict(role='user',content=json.dumps(dict(query=query,cognition=payload),ensure_ascii=False,sort_keys=True))]
        if len(json.dumps(messages,ensure_ascii=False))>max_chars:
            raise ValueError('selected full closure exceeds context budget; narrow query')
        result=EvidenceClosure(target_claim_id,observer,fingerprint,json.dumps(messages,ensure_ascii=False,sort_keys=True),
            tuple(sorted([r['id'] for r in payload['claim_nodes']]+[r['id'] for r in payload['source_spans']])))
        self._cache[key]=result
        self.recomputations[(target_claim_id,observer)]=self.recomputations.get((target_claim_id,observer),0)+1
        return result
