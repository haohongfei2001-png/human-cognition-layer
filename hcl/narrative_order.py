"""Generic, source-anchored strict event ordering; no inferred mental state.

Quoted anchors prove text fidelity, not correctness of semantic extraction.
No order is inferred from presentation order or from missing constraints.
"""
from dataclasses import dataclass
from collections import deque
from graphlib import TopologicalSorter, CycleError
from types import MappingProxyType

@dataclass(frozen=True)
class Anchor:
    start: int
    end: int
    quote: str
    def validate(self, text):
        if type(self.start) is not int or type(self.end) is not int or not (0<=self.start<self.end<=len(text)) or text[self.start:self.end]!=self.quote:
            raise ValueError('exact source offset/quote required')

@dataclass(frozen=True)
class Before:
    earlier: str
    later: str
    evidence: Anchor

class NarrativeOrder:
    """One explicit source/perspective scope, bounded 64 nodes / 4096 relations.

    The caller supplies the scope; this class does not authenticate its truth or
    identify actors automatically. Separate views cannot silently share edges.
    """
    def __init__(self, scope, text, events, relations):
        if not isinstance(scope,str) or not scope.strip() or not isinstance(text,str) or not text.strip():
            raise ValueError('nonempty explicit scope/source required')
        self.scope=scope;self.text=text;self.events=MappingProxyType(dict(events));self.relations=tuple(relations)
        if not 1<=len(self.events)<=64 or len(self.relations)>4096 or any(not isinstance(k,str) or not k.strip() for k in self.events):
            raise ValueError('bounded unique event keys required')
        for span in self.events.values():span.validate(text)
        self._adj={n:[] for n in self.events};pred={n:set() for n in self.events}
        for i,edge in enumerate(self.relations):
            if edge.earlier not in self.events or edge.later not in self.events:raise ValueError('unknown event in constraint')
            edge.evidence.validate(text);self._adj[edge.earlier].append((edge.later,i));pred[edge.later].add(edge.earlier)
        self._cycle=None
        try:tuple(TopologicalSorter(pred).static_order())
        except CycleError as exc:self._cycle=tuple(exc.args[1])
    def _path(self,start,end):
        queue=deque([(start,())]);seen={start}
        while queue:
            node,path=queue.popleft()
            for nxt,index in self._adj[node]:
                if nxt==end:return path+(index,)
                if nxt not in seen:seen.add(nxt);queue.append((nxt,path+(index,)))
        return None
    def compare(self,left,right):
        if left not in self.events or right not in self.events:raise ValueError('query event not in scope')
        if self._cycle is not None:
            return {'scope':self.scope,'relation':'CONFLICT','cycle':list(self._cycle),'support':[]}
        if left==right:return {'scope':self.scope,'relation':'SAME_EVENT','support':[]}
        forward=self._path(left,right);backward=self._path(right,left)
        if forward is not None:relation,path='BEFORE',forward
        elif backward is not None:relation,path='AFTER',backward
        else:relation,path='UNRESOLVED',()
        return {'scope':self.scope,'relation':relation,'support':[{'earlier':self.relations[i].earlier,'later':self.relations[i].later,'evidence':{'start':self.relations[i].evidence.start,'end':self.relations[i].evidence.end,'quote':self.relations[i].evidence.quote}} for i in path]}
    def context(self):
        """Query-independent sparse evidence closure for downstream readout."""
        relations=[{'left':a,'right':b,**self.compare(a,b)} for a in self.events for b in self.events if a!=b]
        return {'scope':self.scope,'events':{k:{'start':v.start,'end':v.end,'quote':v.quote} for k,v in self.events.items()},'relations':relations,'limits':'Only supplied strict-before constraints; UNRESOLVED is not simultaneity, falsehood or a hidden mental state. Extraction semantics require independent source audit.'}
