"""Optional, exact-source access clauses for existing ordinary-text preparation."""
from dataclasses import replace
import re
from .cg04 import _TERM, _time

_CUE = re.compile(rf'Narrator: (?P<actors>{_TERM}(?: and {_TERM}){{0,3}}) heard the previous statement\.')


def prepare_source_access(events):
    """Only explicit narrated exposure; no belief, understanding or world truth."""
    if not isinstance(events, tuple) or not 1 <= len(events) <= 24:
        raise ValueError('bounded parsed source tuple required')
    output = [replace(e, metadata=dict(e.metadata, reader_only=True), observer_ids=(), recipient_ids=()) for e in events]
    receipts = []
    for index, cue in enumerate(events):
        match = _CUE.fullmatch(cue.raw_text.strip())
        if not match:
            if re.search(r'\bheard the previous statement\b', cue.raw_text):
                return tuple(replace(e, metadata=dict(e.metadata, reader_only=True), observer_ids=(), recipient_ids=()) for e in events), {
                    'status': 'INVALID_ACCESS_SOURCE', 'basis': [], 'failure': 'unsupported_access_clause'}
            continue
        actors = tuple(match['actors'].split(' and '))
        if (cue.actor_id is not None or not index or len(set(actors)) != len(actors) or
            'Narrator' in actors or _CUE.fullmatch(events[index - 1].raw_text.strip())):
            return tuple(replace(e, metadata=dict(e.metadata, reader_only=True), observer_ids=(), recipient_ids=()) for e in events), {
                'status': 'INVALID_ACCESS_SOURCE', 'basis': [], 'failure': 'invalid_previous_statement_reference'}
        previous = output[index - 1]
        proof = dict(source_event_id=cue.event_id, quote=cue.raw_text, actor_ids=list(actors),
            statement_event_id=previous.event_id, valid_time=cue.valid_time, recorded_at=cue.recorded_at)
        output[index - 1] = replace(previous, recipient_ids=actors,
            metadata=dict(previous.metadata, reader_only=False, narrative_access_basis=proof))
        receipts.append(proof)
    if len({actor for proof in receipts for actor in proof['actor_ids']} | {e.actor_id for e in events if e.actor_id}) > 4:
        raise ValueError('narrated source-access actor bound exceeded')
    return tuple(output), dict(status='EXPLICIT_REPORTED_EXPOSURE_CHECKED', basis=receipts,
        exposure_implies_belief=False, unmentioned_access='UNKNOWN', failure=None)


def scope_source_access(events, *, event_time=None, knowledge_cutoff=None):
    """A later access receipt never grants access inside an earlier view."""
    sources = {e.event_id: e for e in events}
    positions = {e.event_id: i for i, e in enumerate(events)}
    output = []
    for event in events:
        proof = event.metadata.get('narrative_access_basis')
        if proof is None:
            output.append(event)
            continue
        if not isinstance(proof, dict):
            raise ValueError('typed source-access proof required')
        cue = sources.get(proof.get('source_event_id'))
        match = _CUE.fullmatch(cue.raw_text.strip()) if cue else None
        if (not match or cue.actor_id is not None or proof.get('quote') != cue.raw_text or
            proof.get('statement_event_id') != event.event_id or
            proof.get('actor_ids') != match['actors'].split(' and ') or
            proof.get('valid_time') != cue.valid_time or proof.get('recorded_at') != cue.recorded_at or
            _time(cue.valid_time) <= _time(event.valid_time) or
            positions[cue.event_id] != positions[event.event_id] + 1 or
            bool(event.metadata.get('public')) or
            tuple(event.recipient_ids) not in (tuple(proof.get('actor_ids', [])), ()) or event.observer_ids):
            raise ValueError('source access proof lacks exact later narrator anchor')
        if (event_time and _time(cue.valid_time) > _time(event_time)) or (
            knowledge_cutoff and _time(cue.recorded_at) > _time(knowledge_cutoff)):
            event = replace(event, recipient_ids=(), observer_ids=(),
                metadata=dict(event.metadata, reader_only=True))
        else:
            event = replace(event, recipient_ids=tuple(proof['actor_ids']),
                metadata=dict(event.metadata, reader_only=False))
        output.append(event)
    return tuple(output)
