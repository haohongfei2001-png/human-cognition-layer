"""Opt-in ordinary-source preparation for the retained v0.6 belief runtime."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import re

from hcl.v04.model import EventRecord
from hcl.v06.perspective import SYSTEM_VIEWER, event_accessible_to
from .cg04 import _TERM

_SELF = re.compile(rf'(?P<speaker>{_TERM}): In (?P<context>{_TERM}), '
    rf'I (?P<stance>believe|do not believe|am unsure whether) (?P<item>{_TERM}) is (?P<term>{_TERM})\.')
_REVISION = re.compile(rf'(?P<speaker>{_TERM}): In (?P<context>{_TERM}), '
    rf'I now believe (?P<item>{_TERM}) is (?P<term>{_TERM}) instead of (?P<old_item>{_TERM}) is (?P<old_term>{_TERM})\.')
_REPORT = re.compile(rf'(?P<speaker>{_TERM}): In (?P<context>{_TERM}), '
    rf'(?P<subject>{_TERM}) (?P<stance>believes|does not believe|is unsure whether) '
    rf'(?P<item>{_TERM}) is (?P<term>{_TERM})\.')

BELIEF_POLICY = ('Belief states here preserve explicit source assertions, not verified private '
    'psychology, knowledge or world truth. SELF_REPORT, NARRATOR_ASSERTION and '
    'THIRD_PARTY_REPORT remain distinct; indirect reports cannot establish a private '
    'belief. Believing that an item is fair does not establish fairness or a moral '
    'premise. Exposure to a definition does not establish acceptance or revision. '
    'Proposition keys are exact context/item/term labels, not an ontology.')


def decode_belief_source(text):
    """Complete, bounded syntax only; no substring or action-to-belief inference."""
    match = _SELF.fullmatch(text) or _REVISION.fullmatch(text)
    if match and match['speaker'] != 'Narrator':
        row = match.groupdict()
        return dict(row, subject=row['speaker'], evidence_kind='SELF_REPORT')
    match = _REPORT.fullmatch(text)
    if match and match['subject'] not in (match['speaker'], 'Narrator'):
        row = match.groupdict()
        return dict(row, evidence_kind=('NARRATOR_ASSERTION' if row['speaker'] == 'Narrator' else 'THIRD_PARTY_REPORT'))
    raise ValueError('unsupported belief source')


def _key(row, *, old=False):
    return '/'.join((row['context'], row['old_item' if old else 'item'], row['old_term' if old else 'term']))


@dataclass(frozen=True)
class BeliefPreparation:
    events: tuple[EventRecord, ...]
    payloads: tuple[tuple[str, dict], ...]
    failure: str | None
    diagnostics: tuple[dict, ...]


def belief_narrative_events(narrative):
    lines = [line.strip() for line in narrative.splitlines() if line.strip()]
    if not 1 <= len(lines) <= 24 or any(len(line) > 2000 for line in lines):
        # Preserve the authorized source in the reader channel, without a
        # partial semantic parse or character-access promotion.
        stamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
        return (EventRecord('belief-whole-' + hashlib.sha256(narrative.encode()).hexdigest()[:12],
            stamp, narrative, 'authorized-belief-line-order', stamp, metadata={'reader_only': True}),)
    digest = hashlib.sha256(narrative.encode()).hexdigest()[:10]
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = []
    for index, line in enumerate(lines, 1):
        speaker = re.match(rf'({_TERM}): ', line)
        stamp = (base + timedelta(seconds=index)).isoformat()
        events.append(EventRecord(f'belief-{digest}-{index}', stamp, line, 'authorized-belief-line-order', stamp,
            speaker[1] if speaker and speaker[1] != 'Narrator' else None,
            metadata={'reader_only': True, 'narrator': bool(speaker and speaker[1] == 'Narrator')}))
    return tuple(events)


def prepare_belief_sources(events, *, viewer=SYSTEM_VIEWER, event_time=None, knowledge_cutoff=None):
    """Produce event-local payloads, then independently validate with v0.6.

    Revision requires an earlier matching direct self report in this request's
    accessible time/record scope. Missing/hidden anchors never create old state.
    """
    if not isinstance(events, tuple) or not 1 <= len(events) <= 24:
        raise ValueError('bounded belief source tuple required')
    rows, diagnostics, prior = [], [], {}
    actors, contexts, propositions = set(), set(), set()
    def within(event):
        parse = lambda stamp: datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        return ((not event_time or parse(event.valid_time) <= parse(event_time)) and
                (not knowledge_cutoff or parse(event.recorded_at) <= parse(knowledge_cutoff)))
    try:
        parse = lambda stamp: datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        for event in sorted(events, key=lambda e: (parse(e.valid_time), parse(e.recorded_at), e.event_id)):
            text = event.raw_text.strip()
            try:
                row = decode_belief_source(text)
            except ValueError:
                if re.search(r'\b(?:believe|believes|belief|unsure whether)\b', text, re.I):
                    raise ValueError('unsupported_or_ambiguous_belief_source')
                diagnostics.append(dict(source_event_id=event.event_id, status='NO_BELIEF_INFERRED'))
                continue
            if ((row['speaker'] != 'Narrator' and event.actor_id != row['speaker']) or
                (row['speaker'] == 'Narrator' and (event.actor_id is not None or not (
                    event.metadata.get('narrator') or event.metadata.get('reader_only') or
                    event.metadata.get('source_kind') == 'narrator')))):
                raise ValueError('belief_source_actor_mismatch')
            actors.update((row['subject'], row['speaker']))
            contexts.add(row['context'])
            proposition = _key(row)
            propositions.add(proposition)
            signal = ('DENY' if row.get('stance') in ('do not believe', 'does not believe') else
                'UNCERTAIN' if row.get('stance') in ('am unsure whether', 'is unsure whether') else 'AFFIRM')
            supersedes = None
            if row.get('old_item'):
                old = _key(row, old=True)
                if old == proposition:
                    raise ValueError('revision_must_change_proposition')
                anchor = prior.get((row['subject'], old))
                if (anchor and anchor[1] == 'AFFIRM' and within(anchor[0]) and
                    event_accessible_to(anchor[0], viewer) and
                    parse(anchor[0].valid_time) < parse(event.valid_time)):
                    supersedes = old
                else:
                    diagnostics.append(dict(source_event_id=event.event_id,
                        status='REVISION_ANCHOR_UNAVAILABLE_NEW_SELF_REPORT_ONLY'))
            evidence = dict(subject_agent_id=row['subject'], proposition_key=proposition,
                signal=signal, evidence_kind=row['evidence_kind'],
                supersedes_proposition_key=supersedes, evidence_text=text)
            rows.append((event.event_id, dict(belief_evidence=[evidence], challenge_relations=[])))
            if row['evidence_kind'] == 'SELF_REPORT':
                prior[(row['subject'], proposition)] = (event, signal)
                if supersedes:
                    prior.pop((row['subject'], supersedes), None)
            if len(actors - {'Narrator'}) > 4 or len(contexts) > 2 or len(propositions) > 8 or len(rows) > 8:
                raise ValueError('belief_semantic_bounds')
        return BeliefPreparation(events, tuple(rows), None if rows else 'no_explicit_belief', tuple(diagnostics))
    except ValueError as exc:
        return BeliefPreparation(events, (), str(exc), tuple(diagnostics))


class SourceBeliefBackend:
    """Local deterministic adapter into the unchanged retained v0.6 validator."""
    def __init__(self, event, payload):
        self.event, self.payload = event, payload

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        source = json.loads(messages[-1]['content'])['event']
        if (source['event_id'], source['raw_text'], source['actor_id']) != (
                self.event.event_id, self.event.raw_text, self.event.actor_id):
            raise ValueError('belief backend source binding mismatch')
        return json.dumps(self.payload, ensure_ascii=False, sort_keys=True)
