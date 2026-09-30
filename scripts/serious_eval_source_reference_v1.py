"""Read-only versioned source-span retrieval; whitespace is layout, never semantic truth.

Explicit opt-in future interface. No network, scorer edits or old-run repairs.
"""
import hashlib,json
from hcl.cognition.core import Scope
from hcl.cognition.semantic import AuthorizedText
MAX_SOURCE_BYTES=500000
MAX_QUOTE_CHARS=1500
MAX_REFERENCES=32

def _sha(text):return hashlib.sha256(text.encode()).hexdigest()
def _positions(text,needle):
    rows=[];offset=0
    while len(rows)<2:
        start=text.find(needle,offset)
        if start<0:break
        rows.append(start);offset=start+1
    return rows

def _layout_index(text):
    chars=[];starts=[];ends=[]
    for i,char in enumerate(text):
        if char.isspace():
            if chars and chars[-1]==' ':ends[-1]=i+1;continue
            char=' '
        chars.append(char);starts.append(i);ends.append(i+1)
    return ''.join(chars),starts,ends

class SourceReferenceIndex:
    def __init__(self,sources,scope):
        if (not isinstance(sources,tuple) or not 1<=len(sources)<=8 or
            not all(isinstance(s,AuthorizedText) for s in sources) or not isinstance(scope,Scope) or
            any(not isinstance(s.source_id,str) or not 1<=len(s.source_id)<=256 or
                not isinstance(s.text,str) or not s.text.strip() or type(s.version) is not int or s.version<1 for s in sources) or
            len({s.source_id for s in sources})!=len(sources)):
            raise ValueError('bounded distinct versioned authorized sources and scope required')
        # Filter time/access/order before indexing. Hidden text/identity/digest stays absent.
        visible=tuple(s for s in sources if s.visible_to(scope))
        if sum(len(s.text.encode()) for s in visible)>MAX_SOURCE_BYTES:raise ValueError('visible source byte budget exceeded; never truncate')
        self._sources={s.source_id:s for s in visible};self._indexes={};self._scope=scope
    def versions(self):
        return {sid:dict(version=s.version,source_sha256=_sha(s.text)) for sid,s in self._sources.items()}
    def locate(self,source_id,proposed_quote,*,expected_version,expected_sha256):
        if (not isinstance(source_id,str) or source_id not in self._sources or not isinstance(proposed_quote,str) or
            not proposed_quote.strip() or len(proposed_quote)>MAX_QUOTE_CHARS):raise ValueError('visible source and bounded nonempty reference required')
        s=self._sources[source_id]
        if type(expected_version) is not int or expected_version!=s.version or expected_sha256!=_sha(s.text):raise ValueError('stale source reference refused')
        exact=_positions(s.text,proposed_quote)
        if len(exact)>1:raise ValueError('ambiguous exact reference refused')
        if exact:
            start=exact[0];end=start+len(proposed_quote);method='UNIQUE_EXACT_SOURCE_SUBSTRING'
        else:
            if source_id not in self._indexes:self._indexes[source_id]=_layout_index(s.text)
            normalized,starts,ends=self._indexes[source_id];needle=' '.join(proposed_quote.split());hits=_positions(normalized,needle)
            if len(hits)!=1:raise ValueError('absent or ambiguous whitespace-equivalent reference refused')
            start=starts[hits[0]];end=ends[hits[0]+len(needle)-1];method='UNIQUE_WHITESPACE_EQUIVALENT_SOURCE_SPAN'
        quote=s.text[start:end]
        if len(quote)>MAX_QUOTE_CHARS or ' '.join(quote.split())!=' '.join(proposed_quote.split()):raise ValueError('resolved reference exceeds bound or changes lexical content')
        return dict(source_id=source_id,source_version=s.version,source_sha256=_sha(s.text),start=start,end=end,quote=quote,
            proposed_quote=proposed_quote,method=method,scope_id=self._scope.id,
            verification='SOURCE_SPAN_ONLY_NOT_SEMANTIC_SUPPORT',semantic_support_certified=False)
