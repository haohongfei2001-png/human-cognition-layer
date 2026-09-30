"""Clifford development exposure never qualifies as unseen confirmation."""
import hashlib
from scripts.i02_source_qualification_v12 import require_qualified_confirmation_source_v12
AUTHOR='william-kingdon-clifford'
SYSTEM='clifford-original-english-philosophical-essay'
SOURCE_SHA256='ff0bdcb7dfc4bdcde98b37108cd33b40583adef83c8ff6eaee5f8d4025e65eaa'
RAW_SHA256='3b9b1eb0455b0fe968a0f987aa279602216ae0aabe1560300177a1993e45a6e9'
def require_clifford_disjoint(candidate):
    if not isinstance(candidate,dict):raise ValueError('candidate object required')
    text=candidate.get('source_text')
    if candidate.get('author_id')==AUTHOR or candidate.get('writing_system_id')==SYSTEM or candidate.get('source_sha256') in {SOURCE_SHA256,RAW_SHA256} or (isinstance(text,str) and hashlib.sha256(text.encode()).hexdigest() in {SOURCE_SHA256,RAW_SHA256}):raise ValueError('Clifford development author/source cannot be unseen confirmation')
    return True
def require_qualified_confirmation_source_v13(freeze,candidate,audit,repository,revision,lineage=None):
    require_clifford_disjoint(candidate)
    return require_qualified_confirmation_source_v12(freeze,candidate,audit,repository,revision,lineage)
