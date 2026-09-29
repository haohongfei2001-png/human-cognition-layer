"""I02 confirmation source gate with an executed current-snapshot exposure check.

Historical disjointness, rights, source semantics and reviewer independence
remain separate requirements in the frozen earlier gates.
"""

from scripts.i02_exposure_snapshot import audit_snapshot
from scripts.i02_source_qualification_v4 import require_qualified_confirmation_source_v4


def require_qualified_confirmation_source_v5(freeze, candidate, audit,
                                             repository, revision, lineage=None):
    if not isinstance(candidate, dict) or not isinstance(candidate.get('source_text'), str):
        raise ValueError('ordinary source text required for exposure screen')
    receipt = audit_snapshot(repository, revision, candidate['source_text'])
    if receipt['status'] != 'TEXT_SNAPSHOT_NO_MATCH':
        raise ValueError('repository snapshot exposure requires independent review')
    require_qualified_confirmation_source_v4(freeze, candidate, audit, lineage)
    return receipt
