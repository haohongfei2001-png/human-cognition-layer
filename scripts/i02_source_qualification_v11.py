"""Conservative author exclusions for latest development metadata previews.

A frontmatter probe emitted three Gaskell prose words; a publisher AI synopsis
of Wharton was shown. Neither source may silently become unseen confirmation.
Historical frozen v10 and paid experiments retain their original conditions.
"""
import hashlib
from scripts.i02_source_qualification_v10 import require_qualified_confirmation_source_v10
AUTHORS={'elizabeth-gaskell','edith-wharton'}
SYSTEMS={'elizabeth-gaskell-original-english-framed-fiction','edith-wharton-original-english-fiction'}
SOURCE_SHA256='3a51cd3465537a94ab034d292435b23cfeaf822b9c2aa6addf66f33590a4ad91'
def require_latest_preview_disjoint(candidate):
    if not isinstance(candidate,dict):raise ValueError('candidate must be an object')
    text=candidate.get('source_text')
    if (candidate.get('author_id') in AUTHORS or candidate.get('writing_system_id') in SYSTEMS or
        candidate.get('template_id')=='complete-person-other-choice-development-question-v2' or
        (isinstance(text,str) and hashlib.sha256(text.encode()).hexdigest()==SOURCE_SHA256)):
        raise ValueError('development preview cannot qualify unseen confirmation')
    return True

def require_qualified_confirmation_source_v11(freeze,candidate,audit,repository,revision,lineage=None):
    require_latest_preview_disjoint(candidate)
    return require_qualified_confirmation_source_v10(freeze,candidate,audit,repository,revision,lineage)
