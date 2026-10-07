"""Code-owned necessary source-shape blockers, never treatment or source evidence.

Only known necessary B02/D02 conditions are inspected. Absence of a blocker is
not readiness, semantic relevance, receipt, knowledge or permission. No native
view, workspace claim, provider, translation or source normalization is invoked.
"""
from .communication import CommunicationScene
from .ordinary_access import _SPEECH, _RECEIPT, _AVAILABLE, _ADDRESSED
from .source_fragments import source_fragments


def literal_entry_blockers(sources):
    blockers = []
    for source in sources:
        text = source['text']
        binding = dict(source_id=source['source_id'], version=source['version'])
        try:
            fragments = source_fragments(text)
        except ValueError:
            blockers.append(dict(capability='B02', **binding,
                reason='COMPLETE_SOURCE_FRAGMENT_BOUNDARY_UNSUPPORTED'))
        else:
            if any(not any(pattern.fullmatch(fragment) for pattern in
                       (_SPEECH, _RECEIPT, _AVAILABLE, _ADDRESSED))
                       for _, _, fragment in fragments):
                blockers.append(dict(capability='B02', **binding,
                    reason='COMPLETE_SOURCE_ACCESS_LITERAL_FORMS_REQUIRED'))
        try:
            CommunicationScene(text, source_id=source['source_id'])
        except ValueError:
            blockers.append(dict(capability='D02', **binding,
                reason='NONBLANK_BOUNDED_SOURCE_LINES_REQUIRED'))
    return blockers
