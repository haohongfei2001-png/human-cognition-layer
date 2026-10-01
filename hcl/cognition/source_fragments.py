"""Complete quote-aware source statement boundaries, never a semantic parser."""

def source_fragments(text):
    """Conservative complete source fragments; quotes never split into narration.

    Periods outside paired quotes/newlines separate statements. Every resulting
    nonempty fragment must still pass the existing whole-fragment syntax checker;
    qualifiers/remainders cannot be discarded. Offsets refer to original text character positions.
    """
    start=0;closing=None;fragments=[]
    for i,char in enumerate(text):
        if closing is None and char in ('"','“'):
            closing='"' if char=='"' else '”'
        elif closing is not None and char==closing:
            closing=None
        elif char in ('”','“'):
            raise ValueError('unbalanced quotation; no access normalization')
        boundary=closing is None and (char=='\n' or char=='.' and (i+1==len(text) or text[i+1].isspace()))
        # Speech may end at its closing quote; include a following outside period.
        quote_boundary=(closing is None and char in ('"','”') and (i+1==len(text) or text[i+1].isspace()))
        if boundary or quote_boundary:
            raw=text[start:i+1];fragment=raw.strip()
            if fragment:fragments.append((text.count('\n',0,start)+1,start+len(raw)-len(raw.lstrip()),fragment))
            start=i+1
    if closing is not None:raise ValueError('unclosed quotation; no access normalization')
    raw=text[start:];fragment=raw.strip()
    if fragment:fragments.append((text.count('\n',0,start)+1,start+len(raw)-len(raw.lstrip()),fragment))
    if not 1<=len(fragments)<=80:raise ValueError('communication statement budget exceeded')
    return fragments
