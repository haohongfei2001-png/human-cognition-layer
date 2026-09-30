"""Future-only known Rebus/Kranak exposure gate; historical freezes stay intact."""
from urllib.parse import urlsplit
from scripts.i02_source_qualification_v13 import require_qualified_confirmation_source_v13

AUTHOR = 'joseph-kranak'
SYSTEM = 'rebus-introduction-to-philosophy-ethics-2019'
PUBLISHER = ('press.rebus.community', '/intro-to-phil-ethics/chapter/kantian-deontology')


def require_kranak_disjoint(candidate):
    if not isinstance(candidate, dict):
        raise ValueError('candidate object required')
    exposed_url = False
    for field in ('canonical_url', 'publisher_url', 'source_url'):
        value = candidate.get(field)
        if isinstance(value, str):
            parsed = urlsplit(value)
            if (parsed.hostname, parsed.path.rstrip('/')) == PUBLISHER:
                exposed_url = True
    if (candidate.get('author_id') == AUTHOR or
            candidate.get('writing_system_id') == SYSTEM or exposed_url):
        raise ValueError('Rebus/Kranak development exposure cannot be unseen confirmation')
    return True


def require_qualified_confirmation_source_v14(freeze, candidate, audit, repository,
                                             revision, lineage=None):
    require_kranak_disjoint(candidate)
    return require_qualified_confirmation_source_v13(
        freeze, candidate, audit, repository, revision, lineage)
