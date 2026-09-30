"""Exclude the OBP author/writing system exposed during source-first calibration audit.

This overlay leaves consumed v1-v8 freezes unchanged. Source hashes prevent a
literal mirror with renamed metadata from claiming unseen confirmation; it is
not a paraphrase detector or proof of model-training novelty.
"""
import hashlib
from scripts.i02_source_qualification_v8 import require_qualified_confirmation_source_v8

SYSTEM = 'obp-dimmock-fisher-ethics-for-a-level-2017'
AUTHORS = frozenset({'dimmock-fisher', 'mark-dimmock', 'andrew-fisher'})
SOURCE_SHA256 = '268665309d08875af75ca4eceebdd9f367b474e0f86fdec27325af6476a4975e'


def require_obp_disjoint(candidate):
    if not isinstance(candidate, dict):
        raise ValueError('candidate must be an object')
    text = candidate.get('source_text')
    if (candidate.get('writing_system_id') == SYSTEM or
            candidate.get('author_id') in AUTHORS or
            candidate.get('template_id') == 'obp-native-philosophy-chapter-issue' or
            (isinstance(text, str) and hashlib.sha256(text.encode()).hexdigest() == SOURCE_SHA256)):
        raise ValueError('OBP development source audit cannot be unseen confirmation')
    return True


def require_qualified_confirmation_source_v9(freeze, candidate, audit, repository, revision, lineage=None):
    require_obp_disjoint(candidate)
    return require_qualified_confirmation_source_v8(freeze, candidate, audit, repository, revision, lineage)
