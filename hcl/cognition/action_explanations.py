"""Source-conditioned competing explanations; no winner becomes a true motive."""
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
import re

from hcl.v04.model import EventRecord
from hcl.v1.cg01 import (ConditionFact, ConditionKind, ExplanationCandidate,
    FactAuthority, RequiredCondition, check_explanations)
from .agency import prepare_agency, _GOAL, _SUBGOAL
from .core import ClaimKind, identity
from .workspace import CognitionWorkspace

_QUERY = re.compile(r'Why did (?P<actor>[A-Z][\w-]*) (?P<action>[^?]+)\?')
_PAST = {'attend': 'attended', 'decline': 'declined', 'leave': 'left', 'open': 'opened',
    'stay': 'stayed', 'take': 'took', 'help': 'helped', 'refuse': 'refused', 'skip': 'skipped', 'wait': 'waited'}
_POLICY = ('These are non-exhaustive conditional action explanations, not inferred actual '
    'motives. Supported conditions do not prove any explanation. Counterevidence to '
    'one candidate is not proof of another. Multiple supported goals may coexist; do '
    'not choose a unique motive. Action-time claims remain source reports. Source-order '
    'projection is conditional, not verified chronology; later knowledge without an '
    'explicit action-time reference cannot establish earlier knowledge.')


@dataclass(frozen=True)
class ActionExplanations:
    scope: object
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded explanation context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('explanation source changed; recompute')
        status = workspace.core.support_statuses()
        if any(status.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('explanation support changed; recompute')
        messages = [dict(role='system', content=_POLICY), dict(role='user', content=json.dumps(
            self.payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('explanation context budget exceeded')
        return messages


def prepare_explanations(workspace, query, *, source_id, observer=None):
    match = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not match or len(match['action']) > 300:
        raise ValueError('bounded named action question required')
    actor, action = match['actor'], match['action']
    parts = action.split(' ', 1)
    if len(parts) != 2:
        raise ValueError('explicit action and object required')
    verb, topic = parts
    negated_action = verb == 'not'
    if negated_action:
        nested = topic.split(' ', 1)
        if len(nested) != 2:
            raise ValueError('explicit negated action and object required')
        verb, topic = nested
    past = None if negated_action else _PAST.get(verb)
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    core, source_rows = workspace.core, []
    for candidate in semantic.candidate_ids:
        content = core.claims[candidate].content
        if content['kind'] != 'event' or content['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM':
            continue
        row = content['proposal']
        span = core.spans[content['source_span_id']]
        if row.get('assertion_scope') != 'SOURCE_REPORT':
            continue
        speaker = row.get('speaker_surface')
        narrator = speaker == 'Narrator' and span.quote.startswith('Narrator:')
        if not narrator and row.get('speaker_candidates') != [speaker]:
            continue
        source_rows.append((span.start, candidate, row, span, narrator))
    source_rows.sort(key=lambda r: r[0])
    if len(source_rows) > 20:
        raise ValueError('action explanation source budget exceeded')
    actions = []
    for index, (_, candidate, row, span, narrator) in enumerate(source_rows):
        text = row['utterance'].rstrip('.!?')
        prefix = actor if narrator else 'I'
        forms = {f'{prefix} did {action}'}
        if past:
            forms.add(f'{prefix} {past} {topic}')
        if (narrator or row['speaker_surface'] == actor) and text in forms:
            actions.append(index)
    if len(actions) > 1:
        raise ValueError('multiple matching action episodes; narrow the source')
    versions = tuple((s, workspace._versions[s]) for s in semantic.scope.source_ids)
    original = workspace._documents[source_id][0] if versions else ''
    if not actions:
        payload = dict(query=query, actor=actor, action=action, status='SYSTEM_INSUFFICIENT',
            reason='no_unambiguous_visible_action', source=original, explanations=[], provider_calls=0)
        return ActionExplanations(semantic.scope, versions, json.dumps(payload, sort_keys=True), ())
    index = actions[0]
    action_start, action_candidate, action_row, action_span, narrator = source_rows[index]
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events, event_claims = [], {}
    for position, (_, candidate, row, span, is_narrator) in enumerate(source_rows, 1):
        stamp = (base + timedelta(seconds=position)).isoformat()
        event = EventRecord(identity('explanation-source', candidate), stamp, span.quote, source_id, stamp,
            actor_id=actor if position - 1 == index else None if is_narrator else row['speaker_surface'],
            metadata={'reader_only': True, 'time_semantics': 'SOURCE_ORDER_ONLY'})
        events.append(event)
        event_claims[event.event_id] = candidate
    action_event = events[index]
    prefix_source = original[:action_start].strip()
    agency_payload = None
    goals = []
    if prefix_source:
        prefix_workspace = CognitionWorkspace()
        prefix_id = identity('action-prefix', source_id, action_start, prefix_source)
        prefix_workspace.put_source(prefix_id, prefix_source)
        agency = prepare_agency(prefix_workspace, f"What are {actor}'s goals and plans?", source_id=prefix_id)
        agency_payload = agency.payload
        goals = sorted({p['goal'] for p in agency.payload['plans']
            if p['action'] == action and p['selection'] == 'REPORTED_SELECTED' and p['goal_status'] == 'ACTIVE'})
    if len(goals) > 2:
        raise ValueError('more than two source-supported goal explanations; narrow source')
    knowledge = RequiredCondition(ConditionKind.KNOWLEDGE, topic)
    ignorance = RequiredCondition(ConditionKind.KNOWLEDGE, 'explicit-absence:' + topic)
    opportunity = RequiredCondition(ConditionKind.OPPORTUNITY, action)
    no_opportunity = RequiredCondition(ConditionKind.OPPORTUNITY, 'explicit-absence:' + action)
    facts, fact_claims, diagnostics, claims = [], {}, [], []
    def fact(event, candidate, condition, value, authority, label):
        item = ConditionFact(identity('action-condition', event.event_id, condition.kind.value, condition.key, value),
            event.event_id, actor, condition, value, action_event.valid_time, authority)
        claim = core.claim(semantic.scope, ClaimKind.SYSTEM_INTERPRETATION,
            dict(operation='ACTION_TIME_SOURCE_CONDITION', actor=actor, kind=condition.kind.value,
                key=condition.key, value=value, authority=authority.value, source_event_id=event.event_id,
                interpretation=label, temporal_assumption='EXPLICIT_ACTION_REFERENCE_OR_SOURCE_ORDER_PREFIX'))
        core.support(claim, candidate)
        core.interpret(claim, unknown_conditions=('source_claim_accuracy_not_verified',))
        claims.append(claim)
        facts.append(item)
        fact_claims[item.fact_id] = claim
    for event, (_, candidate, row, span, is_narrator) in zip(events, source_rows):
        speaker = row['speaker_surface']
        if speaker != actor and not is_narrator:
            continue
        subject = actor if is_narrator else 'I'
        body = row['utterance'].rstrip('.!?')
        authority = FactAuthority.EXPLICIT_NARRATOR if is_narrator else FactAuthority.DIRECT_SELF_REPORT
        if body in (f'At the time, {subject} knew about {topic}', f'At the time, {subject} did not know about {topic}'):
            positive = 'did not know' not in body
            fact(event, candidate, knowledge, positive, authority, 'EXPLICIT_ACTION_TIME_KNOWLEDGE_CLAIM')
            fact(event, candidate, ignorance, not positive, authority, 'EXPLICIT_NEGATION_NOT_CLOSED_WORLD_ABSENCE')
        elif body in ((f'At the time, {subject} could choose to {action}', f'At the time, {subject} could not choose to {action}') if negated_action else (f'At the time, {subject} could {action}', f'At the time, {subject} could not {action}')):
            positive = body.startswith(f'At the time, {subject} could choose to ') if negated_action else 'could not' not in body
            fact(event, candidate, opportunity, positive, authority, 'EXPLICIT_ACTION_TIME_OPPORTUNITY_CLAIM')
            fact(event, candidate, no_opportunity, not positive, authority, 'EXPLICIT_NEGATION_NOT_CLOSED_WORLD_ABSENCE')
        elif re.search(r'\b(know|knew|learned|could)\b', body):
            diagnostics.append(dict(candidate_id=candidate, status='NO_UNAMBIGUOUS_ACTION_TIME_CONDITION'))
    # Prefix C01 state is an auditable conditional projection, not a current goal
    # borrowed from later text. Every supporting source candidate remains linked.
    prefix_candidates = [r[1] for r in source_rows if r[0] < action_start]
    for goal in goals:
        condition = RequiredCondition(ConditionKind.GOAL, goal)
        goal_sources = []
        for event, row in zip(events, source_rows):
            parsed = _GOAL.fullmatch(row[2]['utterance'].rstrip('.!?')) or _SUBGOAL.fullmatch(row[2]['utterance'].rstrip('.!?'))
            if row[0] < action_start and row[2]['speaker_surface'] == actor and parsed and parsed['goal'] == goal:
                goal_sources.append(event)
        if not goal_sources:
            raise ValueError('C01 goal lacks an original source event')
        item = ConditionFact(identity('goal-at-action', action_event.event_id, goal), goal_sources[-1].event_id,
            actor, condition, True, action_event.valid_time, FactAuthority.DIRECT_SELF_REPORT)
        claim = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='C01_PRE_ACTION_GOAL_AND_PLAN', actor=actor, goal=goal,
                assumption='SOURCE_ORDER_PREFIX_AND_ACCURATE_SELF_REPORT', c01_projection=agency_payload))
        core.support(claim, *prefix_candidates)
        claims.append(claim)
        facts.append(item)
        fact_claims[item.fact_id] = claim
    candidates = []
    def hypothesis(label, required):
        candidates.append(ExplanationCandidate(identity('explanation', actor, action, label), actor,
            action_event.event_id, action_event.valid_time, label, action_event.event_id, tuple(required)))
    if goals:
        for goal in goals:
            hypothesis('goal-directed pursuit of ' + goal, (knowledge, opportunity, RequiredCondition(ConditionKind.GOAL, goal)))
    else:
        hypothesis('informed choice concerning the recorded action', (knowledge, opportunity))
    hypothesis('lack of awareness relevant to the recorded action', (ignorance,))
    if len(candidates) < 3:
        hypothesis('opportunity constraint relevant to the recorded action', (no_opportunity,))
    rows = check_explanations(tuple(candidates), tuple(facts), tuple(events))
    results = []
    for row in rows:
        conditions = row['conditions']
        conflicts = [c for c in conditions if c['support'] and (c['challenge'] or c['contradiction'])]
        disposition = ('CONFLICTING_PREMISES' if conflicts else
            'WEAKENED_BY_COUNTEREVIDENCE' if any(c['state'] in ('CHALLENGED', 'CONTRADICTED') for c in conditions) else
            'CONDITIONALLY_SUPPORTED' if row['status'] == 'CONSISTENT_CONDITIONAL' else 'UNRESOLVED')
        for condition in conflicts:
            condition['state'] = 'CONFLICTING_CLAIMS'
        result = dict(candidate_id=row['candidate']['candidate_id'], hypothesis=row['candidate']['explanation'], disposition=disposition,
            conditions=conditions, retained_checker_status=row['status'], actual_motive='NOT_ESTABLISHED',
            exclusive='NOT_ASSUMED', caution=row['caution'])
        claim = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='COMPETING_ACTION_EXPLANATION_CHECK', actor=actor, action=action, **result))
        supports = {action_candidate}
        for condition in conditions:
            for key in condition['support'] + condition['challenge'] + condition['contradiction']:
                supports.add(fact_claims[key])
        core.support(claim, *supports)
        claims.append(claim)
        results.append(dict(result, claim_id=claim))
    payload = dict(query=query, actor=actor, action=action, original_source=original,
        action_quote=action_span.quote, action_source_span_id=core.claims[action_candidate].content['source_span_id'],
        action_source_start=action_span.start, action_source_end=action_span.end, source_events=[asdict(e) for e in events], explanations=results, conditions=[asdict(f) for f in facts], condition_claims=fact_claims,
        diagnostics=diagnostics, hypothesis_set='NON_EXHAUSTIVE_NON_EXCLUSIVE',
        winning_motive='NOT_INFERRED', source_order_time='CONDITIONAL_NOT_VERIFIED_CHRONOLOGY',
        c01_prefix=agency_payload, dependency_claim_ids=claims, provider_calls=0, policy=_POLICY)
    return ActionExplanations(semantic.scope, versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(claims))
