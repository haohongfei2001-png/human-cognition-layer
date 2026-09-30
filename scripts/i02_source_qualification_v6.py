"""Require reachable-history and current-snapshot screens before older I02 gates."""

from scripts.i02_exposure_history import audit_history
from scripts.i02_exposure_snapshot import resolve_commit
from scripts.i02_source_qualification_v5 import require_qualified_confirmation_source_v5


def require_qualified_confirmation_source_v6(freeze, candidate, audit,
                                             repository, revision, lineage=None):
    if not isinstance(candidate, dict) or not isinstance(candidate.get('source_text'), str):
        raise ValueError('ordinary source text required for exposure screen')
    if resolve_commit(repository, revision) != resolve_commit(repository, 'HEAD'):
        raise ValueError('qualification history must be current checkout HEAD')
    history = audit_history(repository, candidate['source_text'])
    if history['status'] != 'REACHABLE_HISTORY_NO_TEXT_MATCH':
        raise ValueError('reachable Git history exposure requires independent review')
    snapshot = require_qualified_confirmation_source_v5(
        freeze, candidate, audit, repository, revision, lineage)
    return dict(history=history, snapshot=snapshot)
