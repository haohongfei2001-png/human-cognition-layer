"""A development-read play/author is never unseen confirmation under renamed IDs."""
import hashlib
from scripts.i02_source_qualification_v11 import require_qualified_confirmation_source_v11
AUTHOR='lady-gregory'
SYSTEM='lady-gregory-original-english-one-act-drama'
TEMPLATE='complete-multiparty-information-choice-development-v1'
SOURCE_SHA256='712a9a29d5b8ab974342cf7b2b3c7ad72ae8df979a2ec0bb479b914919d5ce2e'
RAW_SHA256='5a154c3d214a49e75b2003205356dc78ae25c3c3162a8851d54a57265cfeda23'
def require_gregory_disjoint(candidate):
    if not isinstance(candidate,dict):raise ValueError('candidate object required')
    source=candidate.get('source_text')
    if (candidate.get('author_id')==AUTHOR or candidate.get('writing_system_id')==SYSTEM or
        candidate.get('template_id')==TEMPLATE or
        candidate.get('source_sha256') in {SOURCE_SHA256,RAW_SHA256} or
        (isinstance(source,str) and hashlib.sha256(source.encode()).hexdigest()==SOURCE_SHA256)):
        raise ValueError('Gregory development author/play/question cannot be unseen confirmation')
    return True
def require_qualified_confirmation_source_v12(freeze,candidate,audit,repository,revision,lineage=None):
    require_gregory_disjoint(candidate)
    return require_qualified_confirmation_source_v11(freeze,candidate,audit,repository,revision,lineage)
