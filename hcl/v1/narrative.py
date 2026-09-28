"""Conservative ordinary-text preparation for the bounded CG-01 path.

This deliberately extracts only explicit, locally anchored statements. It does
not treat an unmentioned condition as false or generate a private-state fact.
"""
import re
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from hcl.v04.model import EventRecord
from .cg01 import (ConditionFact, ConditionKind, ExplanationCandidate,
                   FactAuthority, RequiredCondition)


_NAME = r'[A-Z][A-Za-z0-9_-]{0,39}'
_ACTION = re.compile(rf'\b(?P<actor>{_NAME})\s+(?P<verb>did not attend|missed|skipped|declined|refused|left|stayed away from|attended)\s+(?P<object>[^,;]+)', re.I)
_QUERY_ACTOR = re.compile(rf'\bwhy\s+(?:did|does|would)\s+(?P<actor>{_NAME})\b', re.I)


@dataclass(frozen=True)
class SemanticPreparation:
    """Typed result from an explicitly configured semantic preparation adapter."""
    events: tuple[EventRecord, ...]
    candidates: tuple[ExplanationCandidate, ...]
    facts: tuple[ConditionFact, ...]
    raw_output: str
    model_id: str
    provider_calls: int
    cost_usd: float | None
    source_span_diagnostics: tuple[str, ...] = ()


def query_actor(query: str) -> str | None:
    match = _QUERY_ACTOR.search(query)
    return match.group('actor') if match else None


def _topic(text):
    if re.search(r'\bmeeting\b', text, re.I):
        return 'meeting'
    if re.search(r'\bparty\b', text, re.I):
        return 'party'
    return None


def prepare_narrative(narrative: str, query: str, target_actor: str | None = None):
    """Extract an action and explicit condition statements; preserve all source rows.

    Returns an empty candidate set if the constrained grammar cannot anchor an
    action. A model answer can still use the original authorized source text.
    """
    sentences = [part.strip() for part in re.split(r'[.!?。！？]+', narrative) if part.strip()]
    target = target_actor or query_actor(query)
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    source_prefix = 'narrative-' + hashlib.sha256(narrative.encode('utf-8')).hexdigest()[:12]
    if len(sentences) > 24:
        # Preserve the authorized source for reader analysis, but do not
        # silently truncate events or attempt deterministic candidates.
        stamp = start.isoformat()
        whole = EventRecord(f'{source_prefix}-whole', stamp, narrative,
            'authorized-narrative-order-only', stamp, metadata={'reader_only': True})
        return (whole,), (), (), target
    events = []
    action = None
    for index, sentence in enumerate(sentences):
        match = _ACTION.search(sentence)
        actor = match.group('actor') if match else None
        stamp = (start + timedelta(seconds=index)).isoformat()
        events.append(EventRecord(f'{source_prefix}-{index+1}', stamp, sentence,
                                  'authorized-narrative-order-only', stamp,
                                  actor_id=actor, metadata={'reader_only': True}))
        if target and actor and actor.lower() == target.lower() and action is None:
            action = (events[-1], match)
    candidates = []
    facts = []
    if action is None:
        return tuple(events), tuple(candidates), tuple(facts), target
    action_event, action_match = action
    topic = _topic(action_match.group('object'))
    if topic:
        required = (RequiredCondition(ConditionKind.KNOWLEDGE, topic),
                    RequiredCondition(ConditionKind.OPPORTUNITY, action_match.group('verb').lower()))
    else:
        required = (RequiredCondition(ConditionKind.OPPORTUNITY, action_match.group('verb').lower()),)
    # A deliberate-choice hypothesis is offered as a candidate, never asserted.
    candidates.append(ExplanationCandidate('candidate-choice', target, action_event.event_id,
                       action_event.valid_time, 'deliberate choice to perform the recorded action',
                       action_event.event_id, required))
    for event in events:
        text = event.raw_text
        if topic and re.search(rf'\b{re.escape(target)}\b.*\bfirst learned\b.*\b{topic}\b.*\bafter\b', text, re.I):
            facts.append(ConditionFact(f'fact-{event.event_id}-first-learned', event.event_id,
                target, RequiredCondition(ConditionKind.KNOWLEDGE, topic), False,
                event.valid_time, FactAuthority.EXPLICIT_NARRATOR,
                first_learning_time=event.valid_time))
        elif topic and re.search(rf'\b{re.escape(target)}\b.*\b(?:knew|heard about|learned about)\b.*\b{topic}\b.*\bbefore\b', text, re.I):
            facts.append(ConditionFact(f'fact-{event.event_id}-knowledge', event.event_id,
                target, RequiredCondition(ConditionKind.KNOWLEDGE, topic), True,
                action_event.valid_time, FactAuthority.EXPLICIT_NARRATOR))
        if re.search(rf'\b{re.escape(target)}\b.*\b(?:could not|was unable to|had no chance to)\b.*\b(?:attend|go|leave)\b', text, re.I):
            facts.append(ConditionFact(f'fact-{event.event_id}-no-opportunity', event.event_id,
                target, required[-1], False, action_event.valid_time, FactAuthority.EXPLICIT_NARRATOR))
        elif re.search(rf'\b{re.escape(target)}\b.*\b(?:could|had a chance to|was able to)\b.*\b(?:attend|go|leave)\b', text, re.I):
            facts.append(ConditionFact(f'fact-{event.event_id}-opportunity', event.event_id,
                target, required[-1], True, action_event.valid_time, FactAuthority.EXPLICIT_NARRATOR))
        if event.event_id != action_event.event_id and re.search(rf'\b(?:thought|believed|interpreted)\b.*\b{re.escape(target)}\b.*\b(?:oppose|opposition)\b', text, re.I):
            candidates.append(ExplanationCandidate('candidate-opposition', target,
                action_event.event_id, action_event.valid_time,
                'an observer attributed deliberate opposition', event.event_id,
                required + (RequiredCondition(ConditionKind.GOAL, 'opposition'),)))
        if re.search(rf'\b{re.escape(target)}\b.*\b(?:said|stated)\b.*\b(?:wanted|intended|planned)\b.*\b(?:oppose|opposition)\b', text, re.I):
            facts.append(ConditionFact(f'fact-{event.event_id}-goal', event.event_id,
                target, RequiredCondition(ConditionKind.GOAL, 'opposition'), True,
                action_event.valid_time, FactAuthority.EXPLICIT_NARRATOR))
    return tuple(events), tuple(candidates[:3]), tuple(facts), target
