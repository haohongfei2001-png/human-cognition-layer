"""Source-grounded goal/means/plan objects with explicit lifecycle distinctions."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import hashlib
import re

from hcl.v04.model import EventRecord
from hcl.v06.belief import BeliefEvidenceKind
from hcl.v07 import HCLV07Runtime, IntentionEvidenceEvent, IntentionSignal
from .core import ClaimKind, identity

_GOAL = re.compile(r'I (?P<verb>want to|aim to|completed my goal to|abandoned my goal to|am unsure whether to) (?P<goal>.+)')
_SUBGOAL = re.compile(r'To (?P<parent>.+), my subgoal is to (?P<goal>.+)')
_PLAN = re.compile(r'I (?P<verb>plan to|am considering a plan to) (?P<action>.+?) in order to (?P<goal>.+?)(?: if (?P<condition>.+))?')
_PLAN_END = re.compile(r'I (?P<verb>abandoned|completed) (?:my|the) plan to (?P<action>.+)')
_OPPORTUNITY = re.compile(r'I have (?P<polarity>an|no) opportunity to (?P<action>.+)')
_INTENT = re.compile(r'I intend to (?P<action>.+)')
_QUERY = re.compile(r"What are (?P<actor>[A-Z][\w-]*)'s goals and plans[?.]?")
_POLICY = ('These are explicit source-reported goals, plans and opportunities, not verified '
    'private intentions or world feasibility. A goal does not select a plan; a considered '
    'means does not become a selected plan. Completion is not proof of intended causation. '
    'Source order is not independently established event chronology. Conditions and '
    'opportunity claims remain distinct. A parent goal does not automatically activate '
    'every subgoal, and completing a subgoal does not prove the parent complete.')


@dataclass(frozen=True)
class AgencyResult:
    scope: object
    source_versions: tuple[tuple[str, int], ...]
    payload_json: str
    claim_ids: tuple[str, ...]

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000, include_sources=True):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000 or type(include_sources) is not bool:
            raise ValueError('bounded agency context required')
        if any(s not in workspace._documents or workspace._versions[s] != version for s, version in self.source_versions):
            raise ValueError('agency source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses[k] != 'SUPPORT_AVAILABLE' for k in self.claim_ids):
            raise ValueError('agency support changed; recompute')
        selected, pending = set(), list(self.claim_ids)
        pending.extend(row['candidate_id'] for row in self.payload['diagnostics'])
        while pending:
            key = pending.pop()
            if key in selected:
                continue
            selected.add(key)
            for group in workspace.core.dependencies.get(key, ()):
                pending.extend(group)
            pending.extend(workspace.core.challenges.get(key, ()))
            if key in workspace.core.interpretations:
                interpretation = workspace.core.interpretations[key]
                pending.extend(interpretation.required_premises)
                pending.extend(interpretation.alternatives)
        receipt = workspace.core.receipt(self.scope)
        receipt['claims'] = [row for row in receipt['claims'] if row['id'] in selected]
        receipt['spans'] = [row for row in receipt['spans'] if row['id'] in selected]
        receipt['revisions'] = [row for row in receipt['revisions'] if row['old'] in selected and row['new'] in selected]
        payload = self.payload
        if not include_sources:
            # The enclosing ordinary reader retains these exact whole sources.
            payload = dict(payload)
            rows = payload.pop('original_sources')
            payload['shared_source_references'] = [dict(source_id=r['source_id'], version=r['version'],
                source_sha256=hashlib.sha256(r['text'].encode()).hexdigest()) for r in rows]
        messages = [dict(role='system', content=_POLICY), dict(role='user',
            content=json.dumps(dict(cognition=payload, evidence=receipt),
                ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('agency context budget exceeded')
        return messages


def prepare_agency(workspace, query, *, source_id, observer=None):
    match = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not match:
        raise ValueError('bounded explicit actor goal/plan question required')
    actor = match['actor']
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    return check_agency_candidates(workspace, query, semantic, source_id=source_id, actor=actor)


def is_agency_utterance(body):
    return isinstance(body,str) and any(pattern.fullmatch(body.rstrip('.!?').strip())
        for pattern in (_GOAL,_SUBGOAL,_PLAN,_PLAN_END,_OPPORTUNITY,_INTENT))


def check_agency_candidates(workspace, query, semantic, *, source_id, actor, only_agency_events=False):
    """Existing C01 on already grounded candidates; no second extraction or oracle."""
    from .semantic import SemanticResult, _PRONOUNS
    from .core import EvidenceCore
    if (not isinstance(query,str) or not query.strip() or len(query)>8000
            or not isinstance(semantic,SemanticResult) or not isinstance(workspace.core,EvidenceCore)
            or not isinstance(actor,str) or not re.fullmatch(r'[A-Z][\w-]*(?: [A-Z][\w-]*)?',actor)
            or actor.lower() in _PRONOUNS or type(only_agency_events) is not bool
            or source_id not in workspace._documents
            or semantic.scope.source_ids not in ((),(source_id,))):
        raise ValueError('bounded grounded actor/source agency input required')
    core = workspace.core
    if any(key not in core.claims or core.claims[key].scope!=semantic.scope
            for key in semantic.candidate_ids+semantic.root_ids):
        raise ValueError('agency candidates outside grounded core or scope')
    for key in semantic.candidate_ids:
        span=core.spans[core.claims[key].content['source_span_id']]
        if (span.source_id!=source_id or span.version!=workspace._versions[source_id]
                or span.quote!=workspace._documents[source_id][0][span.start:span.end]):
            raise ValueError('agency candidate source version changed; recompute')
    runtime = HCLV07Runtime()
    events, diagnostics, operations, goal_evidence, plans, subgoals, opportunities, intentions = [], [], [], {}, {}, [], [], []
    last_goal_signal = {}
    source_candidates = []
    support_statuses = core.support_statuses()
    for key in semantic.candidate_ids:
        content = core.claims[key].content
        if content['kind'] != 'event':
            continue
        row = content['proposal']
        if (content['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM'
                or row.get('assertion_scope') != 'SOURCE_REPORT'
                or support_statuses[key] != 'SUPPORT_AVAILABLE'
                or (only_agency_events and not is_agency_utterance(row.get('utterance')))
                or row.get('speaker_candidates') != [actor] or row.get('speaker_surface') != actor):
            continue
        source_candidates.append((core.spans[content['source_span_id']].start, key, row, content['source_span_id']))
    source_candidates.sort()
    if len(source_candidates) > 16:
        raise ValueError('agency statement budget exceeded')
    for index, (_, candidate, row, span_id) in enumerate(source_candidates, 1):
        span = core.spans[span_id]
        body = row['utterance'].rstrip('.!?').strip()
        goal, subgoal = _GOAL.fullmatch(body), _SUBGOAL.fullmatch(body)
        plan, ending = _PLAN.fullmatch(body), _PLAN_END.fullmatch(body)
        opportunity, intention = _OPPORTUNITY.fullmatch(body), _INTENT.fullmatch(body)
        if not any((goal, subgoal, plan, ending, opportunity, intention)):
            diagnostics.append(dict(candidate_id=candidate, status='NO_GOAL_PLAN_OR_INTENTION_INFERRED'))
            continue
        # The retained projector needs ordered timestamps. They are explicit
        # ordinal adapter values, never a claim about a calendar or actual time.
        stamp = (datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=index)).isoformat()
        event = EventRecord(identity('agency-event', candidate), stamp, span.quote, source_id, stamp,
            actor_id=actor, metadata={'time_semantics': 'SOURCE_ORDER_ONLY'})
        runtime.ingest_event(event)
        events.append(event)
        def operation(kind, data, supports=()):
            claim = core.claim(semantic.scope, ClaimKind.SYSTEM_INTERPRETATION,
                dict(operation=kind, actor=actor, **data, source_span_id=span_id,
                    authority='EXPLICIT_SELF_REPORT', private_state='NOT_VERIFIED'))
            core.support(claim, candidate, *supports)
            core.interpret(claim, unknown_conditions=('accurate_sincere_self_report_not_verified',))
            operations.append(claim)
            return claim
        if goal or subgoal:
            target = (goal or subgoal)['goal']
            if ' if ' in target or ';' in target:
                diagnostics.append(dict(candidate_id=candidate, status='CONDITIONAL_OR_COMPOUND_GOAL_UNRESOLVED'))
                continue
            verb = goal['verb'] if goal else 'want to'
            signal = {'want to': IntentionSignal.EXPLICIT_GOAL, 'aim to': IntentionSignal.EXPLICIT_GOAL,
                'completed my goal to': IntentionSignal.EXPLICIT_COMPLETION,
                'abandoned my goal to': IntentionSignal.EXPLICIT_ABANDONMENT,
                'am unsure whether to': IntentionSignal.CHARACTER_UNCERTAIN}[verb]
            claim = operation('REPORTED_GOAL_TRANSITION', dict(goal=target, signal=signal.value))
            evidence = IntentionEvidenceEvent(identity('agency-goal-evidence', claim), event.event_id,
                actor, target, signal, BeliefEvidenceKind.SELF_REPORT, stamp, stamp, span.quote)
            runtime.ingest_intention_evidence(evidence)
            goal_evidence[evidence.evidence_id] = claim
            last_goal_signal[target] = signal
            if subgoal:
                relation = operation('REPORTED_SUBGOAL_FOR', dict(goal=target, parent_goal=subgoal['parent']), (claim,))
                subgoals.append(dict(subgoal=target, parent_goal=subgoal['parent'], claim_id=relation))
        elif plan:
            action, target, condition = plan['action'], plan['goal'], plan['condition']
            if any(not value.strip() or len(value) > 300 for value in (action, target, condition or 'unconditional')):
                raise ValueError('bounded nonempty plan terms required')
            status = 'REPORTED_SELECTED' if plan['verb'] == 'plan to' else 'CONSIDERED_NOT_SELECTED'
            claim = operation('REPORTED_PLAN', dict(action=action, goal=target, condition=condition, status=status))
            key = (action, target, condition)
            prior = plans.get(key)
            # Considering the same means later is not an explicit revocation of
            # an earlier selected plan. Keep the unresolved selection evidence.
            if prior and prior['status'] == 'REPORTED_SELECTED' and status == 'CONSIDERED_NOT_SELECTED':
                status = 'SELECTION_CONFLICT_OR_CHANGE_UNRESOLVED'
            plans[key] = dict(action=action, goal=target, condition=condition, status=status,
                claims=(prior['claims'] if prior else []) + [claim])
        elif ending:
            matching = [p for p in plans.values() if p['action'] == ending['action']]
            if len(matching) != 1:
                diagnostics.append(dict(candidate_id=candidate, status='PLAN_LIFECYCLE_REFERENCE_MISSING_OR_AMBIGUOUS'))
                continue
            selected = matching[0]
            status = 'REPORTED_ABANDONED' if ending['verb'] == 'abandoned' else 'REPORTED_COMPLETED'
            claim = operation('REPORTED_PLAN_LIFECYCLE', dict(action=ending['action'], status=status), tuple(selected['claims']))
            selected['claims'].append(claim)
            selected['status'] = status
        elif opportunity:
            claim = operation('REPORTED_OPPORTUNITY', dict(action=opportunity['action'],
                available=opportunity['polarity'] == 'an'))
            opportunities.append(dict(action=opportunity['action'], available=opportunity['polarity'] == 'an', claim_id=claim))
        elif intention:
            claim = operation('REPORTED_INTENTION', dict(action=intention['action']))
            intentions.append(dict(action=intention['action'], claim_id=claim,
                causation='NOT_ESTABLISHED', completion='NOT_ESTABLISHED'))
    goals, goal_claims = [], {}
    for estimate in runtime.goal_estimates(actor):
        state = estimate.as_dict()
        effective_status = ('CHARACTER_UNCERTAIN' if last_goal_signal[estimate.goal_key] == IntentionSignal.CHARACTER_UNCERTAIN else estimate.status.value)
        supports = [goal_evidence[key] for key in estimate.direct_evidence_ids + estimate.character_uncertainty_ids]
        claim = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='RETAINED_V07_GOAL_PROJECTION', actor=actor, goal=estimate.goal_key,
                source_order_status=effective_status, temporal_semantics='SOURCE_ORDER_NOT_CALENDAR_TIME'))
        core.support(claim, *supports)
        operations.append(claim)
        goals.append(dict(goal=estimate.goal_key, status=effective_status, claim_id=claim,
            retained_state=state, intended_causation='NOT_ESTABLISHED'))
        goal_claims[estimate.goal_key] = claim
    goal_states = {g['goal']: g['status'] for g in goals}
    checked_plans = []
    for plan in plans.values():
        related = [o for o in opportunities if o['action'] == plan['action']]
        values = {o['available'] for o in related}
        access = 'CONFLICTING_CLAIMS' if len(values) > 1 else 'REPORTED_AVAILABLE' if True in values else 'REPORTED_UNAVAILABLE' if False in values else 'UNKNOWN'
        goal_status = goal_states.get(plan['goal'], 'SYSTEM_INSUFFICIENT')
        pursuit = ('NO_SELECTED_PLAN' if plan['status'] == 'CONSIDERED_NOT_SELECTED'
            else 'PLAN_NOT_CURRENTLY_SELECTED' if plan['status'] != 'REPORTED_SELECTED'
            else 'GOAL_NOT_REPORTED_ACTIVE' if goal_status != 'ACTIVE'
            else 'OPPORTUNITY_CONTRADICTED' if access == 'REPORTED_UNAVAILABLE'
            else 'OPPORTUNITY_UNRESOLVED' if access in ('UNKNOWN', 'CONFLICTING_CLAIMS')
            else 'CONDITION_REQUIRES_CHECK' if plan['condition'] else 'SOURCE_SUPPORTED_PURSUIT_NOT_WORLD_FEASIBILITY')
        result = dict(action=plan['action'], goal=plan['goal'], condition=plan['condition'],
            selection=plan['status'], goal_status=goal_status, opportunity=access, pursuit_check=pursuit,
            success='NOT_ESTABLISHED', private_intention='NOT_VERIFIED')
        claim = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='GOAL_PLAN_OPPORTUNITY_JOIN', actor=actor, **result))
        supports = plan['claims'] + [o['claim_id'] for o in related]
        if plan['goal'] in goal_claims:
            supports.append(goal_claims[plan['goal']])
        core.support(claim, *supports)
        operations.append(claim)
        checked_plans.append(dict(result, claim_id=claim, source_claim_ids=plan['claims']))
    versions = tuple((s, workspace._versions[s]) for s in semantic.scope.source_ids)
    payload = dict(query=query, actor=actor, original_sources=[dict(source_id=s, version=v, text=workspace._documents[s][0]) for s, v in versions], goals=goals, subgoal_relations=subgoals,
        plans=checked_plans, intentions=intentions, opportunities=opportunities,
        diagnostics=diagnostics, state='SOURCE_REPORTED_AGENCY' if goals or plans or intentions else 'SYSTEM_INSUFFICIENT',
        provider_calls=0, temporal_semantics='SOURCE_ORDER_ONLY_NOT_VERIFIED_EVENT_CHRONOLOGY', policy=_POLICY)
    return AgencyResult(semantic.scope, versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(operations))
