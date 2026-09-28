"""Bounded, source-scoped checks of candidate character-action explanations.

The checker evaluates conditions on explanations, never a person's true motive.
Semantic facts must be explicit; silence is not negative knowledge.
"""
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum

from hcl.v04.model import EventRecord
from hcl.v06.perspective import event_accessible_to


class ConditionKind(str, Enum):
    KNOWLEDGE = 'KNOWLEDGE'
    GOAL = 'GOAL'
    OPPORTUNITY = 'OPPORTUNITY'


class FactAuthority(str, Enum):
    EXPLICIT_NARRATOR = 'EXPLICIT_NARRATOR'
    DIRECT_SELF_REPORT = 'DIRECT_SELF_REPORT'
    THIRD_PARTY_ATTRIBUTION = 'THIRD_PARTY_ATTRIBUTION'
    DIRECT_OBSERVATION = 'DIRECT_OBSERVATION'


@dataclass(frozen=True)
class RequiredCondition:
    kind: ConditionKind
    key: str


@dataclass(frozen=True)
class ConditionFact:
    fact_id: str
    source_event_id: str
    target_actor: str
    condition: RequiredCondition
    value: bool
    claim_time: str
    authority: FactAuthority
    # A first-learning report can explicitly establish lack of prior knowledge.
    # This flag is only valid for an explicit narrator report and KNOWLEDGE.
    first_learning_time: str | None = None


@dataclass(frozen=True)
class ExplanationCandidate:
    candidate_id: str
    target_actor: str
    action_event_id: str
    action_time: str
    explanation: str
    source_event_id: str
    required: tuple[RequiredCondition, ...]


def _time(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None:
        raise ValueError('timezone-aware time required')
    return parsed


def _validate(candidate, facts, events):
    if candidate.action_event_id not in events or candidate.source_event_id not in events:
        raise ValueError('candidate source/action event missing')
    action = events[candidate.action_event_id]
    if action.actor_id != candidate.target_actor or _time(action.valid_time) != _time(candidate.action_time):
        raise ValueError('candidate action identity/time mismatch')
    if not candidate.required or len(candidate.required) > 6:
        raise ValueError('candidate must have one to six required conditions')
    if (candidate.source_event_id != candidate.action_event_id and
        candidate.target_actor.lower() not in events[candidate.source_event_id].raw_text.lower()):
        raise ValueError('candidate attribution must name target in source')
    for fact in facts:
        source = events.get(fact.source_event_id)
        if source is None or fact.target_actor != candidate.target_actor:
            continue
        _time(fact.claim_time)
        if fact.authority == FactAuthority.EXPLICIT_NARRATOR and source.actor_id is not None:
            raise ValueError('narrator authority requires narrator source')
        if fact.authority == FactAuthority.DIRECT_SELF_REPORT and source.actor_id != candidate.target_actor:
            raise ValueError('self report must come from target')
        if fact.authority != FactAuthority.DIRECT_SELF_REPORT and fact.target_actor.lower() not in source.raw_text.lower():
            raise ValueError('condition source must name target')
        if fact.first_learning_time is not None:
            if fact.authority != FactAuthority.EXPLICIT_NARRATOR or fact.condition.kind != ConditionKind.KNOWLEDGE:
                raise ValueError('first learning requires explicit narrator knowledge report')
            if _time(fact.first_learning_time) != _time(source.valid_time):
                raise ValueError('first learning time must match source event')


def check_explanations(candidates: tuple[ExplanationCandidate, ...],
                       facts: tuple[ConditionFact, ...], events: tuple[EventRecord, ...],
                       *, mode: str = 'READER_ANALYSIS', observer_actor: str | None = None,
                       event_time: str | None = None,
                       knowledge_cutoff: str | None = None) -> tuple[dict, ...]:
    """Return condition states and bounded candidate assessments.

    A later narrator report can revise a reader's retrospective assessment of
    an action. It never becomes information the actor held at action time.
    """
    if len(candidates) > 3 or len(events) > 24 or len(facts) > 48:
        raise ValueError('CG-01 first-round bounds exceeded')
    if len({c.candidate_id for c in candidates}) != len(candidates):
        raise ValueError('duplicate candidate IDs')
    if len({f.fact_id for f in facts}) != len(facts):
        raise ValueError('duplicate condition fact IDs')
    if len({c.target_actor for c in candidates} | {f.target_actor for f in facts}) > 4:
        raise ValueError('at most four actors')
    if len({e.event_id for e in events}) != len(events):
        raise ValueError('duplicate event IDs')
    if mode not in ('READER_ANALYSIS', 'CHARACTER_PERSPECTIVE', 'OBSERVER_ABOUT_TARGET'):
        raise ValueError('invalid perspective mode')
    if mode == 'OBSERVER_ABOUT_TARGET' and not observer_actor:
        raise ValueError('observer required')
    event_map = {e.event_id: e for e in events}
    results = []
    for candidate in candidates:
        _validate(candidate, facts, event_map)
        action_time = _time(candidate.action_time)
        candidate_source = event_map[candidate.source_event_id]
        action_source = event_map[candidate.action_event_id]
        if event_time and (_time(candidate_source.valid_time) > _time(event_time) or
                           action_time > _time(event_time)):
            continue
        if mode == 'CHARACTER_PERSPECTIVE' and (
            _time(candidate_source.valid_time) > action_time or
            not event_accessible_to(candidate_source, candidate.target_actor) or
            not event_accessible_to(action_source, candidate.target_actor)):
            continue
        if mode == 'OBSERVER_ABOUT_TARGET' and (
            not event_accessible_to(candidate_source, observer_actor) or
            not event_accessible_to(action_source, observer_actor)):
            continue
        rows = []
        for required in candidate.required:
            support, challenge, contradiction = [], [], []
            for fact in facts:
                if fact.target_actor != candidate.target_actor or fact.condition != required:
                    continue
                source = event_map.get(fact.source_event_id)
                if source is None:
                    raise ValueError('fact source event missing')
                if knowledge_cutoff and _time(source.recorded_at) > _time(knowledge_cutoff):
                    continue
                if event_time and _time(source.valid_time) > _time(event_time):
                    continue
                if mode == 'CHARACTER_PERSPECTIVE':
                    if _time(source.valid_time) > action_time or not event_accessible_to(source, candidate.target_actor):
                        continue
                elif mode == 'OBSERVER_ABOUT_TARGET' and not event_accessible_to(source, observer_actor):
                    continue
                # A claim about a condition after the action cannot establish
                # what was true at the action, except explicit first learning.
                first_learning = (fact.first_learning_time is not None and
                                  _time(fact.first_learning_time) > action_time)
                if fact.first_learning_time is not None and not first_learning:
                    continue  # earlier learning does not prove retained knowledge
                if not first_learning and _time(fact.claim_time) > action_time:
                    continue
                negative = first_learning or not fact.value
                reliable = fact.authority == FactAuthority.EXPLICIT_NARRATOR
                if negative:
                    (contradiction if reliable else challenge).append(fact.fact_id)
                else:
                    support.append(fact.fact_id)
            state = ('CONTRADICTED' if contradiction else 'SUPPORTED' if support and not challenge
                     else 'CHALLENGED' if challenge else 'UNKNOWN')
            rows.append({'kind': required.kind.value, 'key': required.key, 'state': state,
                         'support': support, 'challenge': challenge, 'contradiction': contradiction})
        status = ('INVALIDATED' if any(r['state'] == 'CONTRADICTED' for r in rows) else
                  'CONSISTENT_CONDITIONAL' if all(r['state'] == 'SUPPORTED' for r in rows) else
                  'UNRESOLVED')
        results.append({'candidate': asdict(candidate), 'status': status, 'conditions': rows,
                        'caution': 'conditions do not establish a unique or true motive'})
    return tuple(results)


def revise_explanations(candidates, previous_facts, new_facts, events, **scope):
    """Recompute after an update and identify only changed candidates."""
    if len(new_facts) > 2:
        raise ValueError('at most two update points')
    before = check_explanations(candidates, tuple(previous_facts), tuple(events), **scope)
    after = check_explanations(candidates, tuple(previous_facts) + tuple(new_facts), tuple(events), **scope)
    changed = tuple(row['candidate']['candidate_id'] for old, row in zip(before, after)
                    if old['status'] != row['status'] or old['conditions'] != row['conditions'])
    return {'before': before, 'after': after, 'changed_candidate_ids': changed}
