"""Exclude development-exposed IRIE system before immutable earlier gates."""
import hashlib
from scripts.i02_source_qualification_v6 import require_qualified_confirmation_source_v6

IRIE_SYSTEM = 'irie-volume34-ai-ethics-case-studies'
IRIE_AUTHORS = frozenset({'norman-mooradian','calvin-hillis','ebrahim-bagheri','zack-marshall'})
IRIE_PRIVACY_HASH = '84630476faa359a964021d4d4615a708627c1bbc052a92c3ac11e4c774330791'

def require_irie_disjoint(candidate):
    if not isinstance(candidate,dict):
        raise ValueError('candidate must be an object')
    text = candidate.get('source_text')
    if (candidate.get('writing_system_id') == IRIE_SYSTEM or
            candidate.get('author_id') in IRIE_AUTHORS or
            (isinstance(text,str) and hashlib.sha256(text.encode()).hexdigest() == IRIE_PRIVACY_HASH)):
        raise ValueError('IRIE development exposure cannot be unseen confirmation')
    return True

def require_qualified_confirmation_source_v7(freeze,candidate,audit,repository,revision,lineage=None):
    require_irie_disjoint(candidate)
    return require_qualified_confirmation_source_v6(freeze,candidate,audit,repository,revision,lineage)
