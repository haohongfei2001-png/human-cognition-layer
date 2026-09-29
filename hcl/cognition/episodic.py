"""Authorized source-local event retrieval, never a character knowledge test."""
from dataclasses import dataclass
import json
import re

from .core import Scope, identity
from .semantic import AuthorizedText, _local_candidates

_STOP=set('the a an is are was were of to in at on for and or what which evidence about concerns does did has have that this as i my'.split())
_POLICY=('These are selected source excerpts, not a complete narrative or a character knowledge state. '
    'A retrieval miss, omitted event or low score never means the character did not know or the '
    'source contains no evidence. Names are source-local labels, not cross-document identity. '
    'Excerpts preserve assertion scope and exact provenance. A summary is an extract, never a '
    'new fact. Narrative order is not event time. Dependencies listed are navigation references; '
    'their conclusions and full support/challenge closure are not asserted by this retrieval.')


def _tokens(text):
    return set(re.findall(r"[\w-]+",text.lower()))-_STOP


@dataclass(frozen=True)
class EpisodicRetrieval:
    observer: str | None
    visible_versions: tuple
    payload_json: str

    @property
    def payload(self):return json.loads(self.payload_json)

    def messages(self,index):
        if self.visible_versions!=index.visible_versions(self.observer):
            raise ValueError('retrieval collection or access changed; retrieve again')
        for row in self.payload['events']:
            index.fetch(row['event_id'],observer=self.observer)
        return [dict(role='system',content=_POLICY),dict(role='user',content=self.payload_json)]


class EpisodicIndex:
    """Versioned source indexes, with access filtering before ranking or counts.

    Indexing uses the same bounded literal parser and local offsets as A02. No
    backend call, paraphrase, inferred event time or cross-document alias is added.
    """
    def __init__(self,workspace,*,max_events=512):
        if type(max_events)is not int or not 1<=max_events<=1024:
            raise ValueError('bounded episodic capacity required')
        self.workspace=workspace
        self.max_events=max_events
        self.events={}
        self.source_versions={}
        self.indexes={name:{} for name in ('person','proposition','transition','token','dependency')}
        self.index_builds={}

    def visible_versions(self,observer):
        return tuple(sorted((s,self.workspace._versions[s]) for s,(text,acl) in self.workspace._documents.items() if observer is None or observer in acl))

    def _rebuild_indexes(self):
        self.indexes={name:{} for name in self.indexes}
        for eid,row in self.events.items():
            fields=dict(person=row['person_labels'],proposition=row['proposition_keys'],
                transition=row['transition_markers'],token=_tokens(row['excerpt']),dependency=[row['source_span_id']])
            for kind,terms in fields.items():
                for term in terms:self.indexes[kind].setdefault(term,set()).add(eid)
        core=self.workspace.core
        span_events={}
        for eid,r in self.events.items():
            span_events.setdefault((r['source_id'],r['source_version'],r['start'],r['end']),set()).add(eid)
        def ancestors(key,seen):
            if key in seen:return set()
            if key in core.spans:
                s=core.spans[key]
                return span_events.get((s.source_id,s.version,s.start,s.end),set())
            return set().union(*(ancestors(k,seen|{key}) for group in core.dependencies.get(key,()) for k in group))
        for key in core.claims:
            events=ancestors(key,set())
            if events:self.indexes['dependency'][key]=events

    def refresh(self,*,observer=None):
        w=self.workspace
        # Do not index hidden additions or let their size change visible retrieval.
        for source_id,version in self.visible_versions(observer):
            if self.source_versions.get(source_id)==version:continue
            text,acl=w._documents[source_id]
            if len(text)>64000:raise ValueError('episodic source requires bounded chapter segmentation')
            candidates=_local_candidates(AuthorizedText(source_id,text,version,acl))
            source_events=[r for r in candidates if r['kind']=='event']
            visible_ids={s for s,v in self.visible_versions(observer)}
            remaining=sum(r['source_id']!=source_id and r['source_id'] in visible_ids for r in self.events.values())
            if remaining+len(source_events)>self.max_events:raise ValueError('episodic event capacity exceeded')
            built=[]
            for event in source_events:
                start,end=event['start'],event['start']+len(event['quote'])
                span=w.core.add_span(text,source_id=source_id,version=version,start=start,end=end,
                    permitted_observers=acl,order=text[:start].count('\n')+1)
                w._version_spans[source_id].add(span)
                content=event['content']
                related=[r for r in candidates if r['start']==start and r['kind']=='proposition']
                props=[r['content']['proposition'].casefold() for r in related]
                line_start=text.rfind('\n',0,start)+1
                line_end=text.find('\n',end)
                if line_end<0:line_end=len(text)
                transitions=[x for x in ('now','no longer','instead of','later','previously') if re.search(r'\b'+re.escape(x)+r'\b',content['utterance'],re.I)]
                row=dict(event_id=identity('episode',source_id,version,start,end),source_id=source_id,source_version=version,
                    source_span_id=span,start=start,end=end,excerpt=event['quote'],summary=event['quote'],
                    summary_authority='EXTRACTIVE_SOURCE_QUOTE_NOT_NEW_FACT',source_line_context=text[line_start:line_end],
                    speaker_surface=content['speaker_surface'],person_labels=content['speaker_candidates'],
                    speaker_resolution='EXPLICIT_SOURCE_LABEL' if content['speaker_candidates']==[content['speaker_surface']] else 'UNRESOLVED_REFERENCE',
                    person_identity='SOURCE_LOCAL_ONLY',proposition_keys=props,transition_markers=transitions,
                    assertion_scope=content['assertion_scope'],narrative_line=text[:start].count('\n')+1,
                    event_time='NOT_INFERRED',character_knowledge='NOT_INFERRED')
                built.append(row)
            self.events={eid:r for eid,r in self.events.items() if r['source_id']!=source_id}
            self.events.update({r['event_id']:r for r in built})
            self.source_versions[source_id]=version
            self.index_builds[source_id]=self.index_builds.get(source_id,0)+1
        # Removed sources and revoked/changed source versions cannot be fetched.
        self.events={eid:r for eid,r in self.events.items() if r['source_id'] in w._documents and w._versions[r['source_id']]==r['source_version']}
        self._rebuild_indexes()

    def fetch(self,event_id,*,observer=None):
        row=self.events.get(event_id)
        if row is None:raise ValueError('event unavailable in current authorized index')
        w=self.workspace;s=row['source_id']
        if s not in w._documents or w._versions[s]!=row['source_version']:
            raise ValueError('stale source event')
        span=w.core.spans[row['source_span_id']]
        if not span.permits(Scope(observer=observer,source_ids=(s,))) or span.id in w.core.withdrawn:
            raise ValueError('event unavailable in current authorized index')
        text=w._documents[s][0]
        if text[row['start']:row['end']]!=row['excerpt']:
            raise ValueError('source span mismatch')
        return json.loads(json.dumps(row))

    def retrieve(self,query,*,observer=None,max_events=8,max_chars=16000,person=None,proposition=None,transition=None,dependency=None):
        if not isinstance(query,str) or not query.strip() or len(query)>8000 or type(max_events)is not int or not 1<=max_events<=32 or type(max_chars)is not int or not 1000<=max_chars<=128000:
            raise ValueError('bounded query and retrieval budgets required')
        for value in (person,proposition,transition,dependency):
            if value is not None and (not isinstance(value,str) or not value or len(value)>8000):raise ValueError('bounded index filter required')
        self.refresh(observer=observer)
        visible=dict(self.visible_versions(observer))
        allowed={eid for eid,r in self.events.items() if r['source_id'] in visible}
        claim=self.workspace.core.claims.get(dependency)
        if claim and (not set(claim.scope.source_ids)<=visible.keys() or claim.scope.observer not in (None,observer)):
            allowed=set()
        for kind,value in (('person',person),('proposition',proposition.casefold() if proposition else None),('transition',transition),('dependency',dependency)):
            if value is not None:allowed &= self.indexes[kind].get(value,set())
        terms=_tokens(query)
        hits=set().union(*(self.indexes['token'].get(t,set()) for t in terms)) if terms else set()
        matched=allowed & hits
        ranked=sorted(matched,key=lambda eid:(-len(terms&_tokens(self.events[eid]['excerpt'])),self.events[eid]['source_id'],self.events[eid]['start']))
        rows=[];truncated=False
        for eid in ranked:
            if len(rows)>=max_events:truncated=True;break
            row=self.fetch(eid,observer=observer)
            trial=dict(query=query,events=rows+[row],status='SELECTED_EXCERPTS',selection_completeness='PARTIAL_RETRIEVAL_NOT_EVIDENCE_CLOSURE',missing_evidence='NOT_CHARACTER_IGNORANCE_OR_SOURCE_ABSENCE',policy=_POLICY)
            if len(json.dumps(trial,ensure_ascii=False))+len(_POLICY)+128>max_chars:
                truncated=True;break
            rows.append(row)
        payload=dict(query=query,events=rows,status='SELECTED_EXCERPTS' if rows else 'RETRIEVAL_MISS',
            selection_completeness='PARTIAL_RETRIEVAL_NOT_EVIDENCE_CLOSURE',budget_truncated=truncated,
            missing_evidence='NOT_CHARACTER_IGNORANCE_OR_SOURCE_ABSENCE',policy=_POLICY)
        raw=json.dumps(payload,ensure_ascii=False,sort_keys=True)
        if len(json.dumps([dict(role='system',content=_POLICY),dict(role='user',content=raw)],ensure_ascii=False))>max_chars:
            raise ValueError('retrieval context envelope exceeds budget')
        return EpisodicRetrieval(observer,self.visible_versions(observer),raw)
