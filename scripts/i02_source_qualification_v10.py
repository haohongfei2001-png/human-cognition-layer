"""Deny James development exposure before history, rights or confirmation assertions."""
import hashlib
from scripts.i02_source_qualification_v9 import require_qualified_confirmation_source_v9
SYSTEM='henry-james-original-english-psychological-fiction'
SOURCE_SHA256='2090d6458cd1f81d669a71a137f40a03996e99fff016c1a0c95cee77e278fe4a'
CONTAINER_SHA256='5f3dbf1715226fab954d77e35623d684fb408a9bc8af9846e97d59845e64c625'
def require_james_disjoint(candidate):
    if not isinstance(candidate,dict):raise ValueError('candidate must be an object')
    text=candidate.get('source_text')
    if (candidate.get('author_id')=='henry-james' or candidate.get('writing_system_id')==SYSTEM or
        candidate.get('template_id')=='independent-character-self-other-counterfactual-question-v1' or
        (isinstance(text,str) and hashlib.sha256(text.encode()).hexdigest() in {SOURCE_SHA256,CONTAINER_SHA256})):
        raise ValueError('James development source exposure cannot be unseen confirmation')
    return True
def require_qualified_confirmation_source_v10(freeze,candidate,audit,repository,revision,lineage=None):
    require_james_disjoint(candidate)
    return require_qualified_confirmation_source_v9(freeze,candidate,audit,repository,revision,lineage)
