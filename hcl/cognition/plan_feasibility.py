"""Keep reported-belief plan feasibility distinct from an explicit model."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import hashlib
import re

from .agency import prepare_agency, AgencyResult, validate_agency_candidate_scope
from .core import ClaimKind, identity
from .revision_time import RevisionTimeline, _REVISION, _CHALLENGE, _ACCEPT, _REJECT

_QUERY = re.compile(r"Could (?P<actor>[A-Z][\w-]*)'s plans work under their beliefs and the declared model\?")
_MODEL = re.compile(r'In the declared model, it is (?P<value>true|false) that (?P<proposition>.+)')
_NEGATED = re.compile(r'it is (?P<value>true|false) that (?P<proposition>.+)')
_POLICY = ('Compare conditional plan checks, not verified private beliefs or world facts. '
    'A declared model is an explicit source assumption. Model/character disagreement '
    'does not mean the character knew the plan was infeasible. Not believing p is not '
    'the same as believing not-p. A plan revision does not establish a change of values. '
    'Source-order projection is not verified calendar chronology. Selected plan, '
    'reported goal, opportunity, belief and model condition remain separate.')


def _literal(text):
    match = _NEGATED.fullmatch(text)
    return (match['proposition'], match['value'] == 'true') if match else (text, True)


@dataclass(frozen=True)
class PlanFeasibility:
    scope: object
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000, include_sources=True):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000 or type(include_sources) is not bool:
            raise ValueError('bounded plan context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('plan evidence changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(k) != 'SUPPORT_AVAILABLE' for k in self.claim_ids):
            raise ValueError('plan support is no longer available')
        payload=self.payload
        if not include_sources:
            rows=payload.pop('original_sources')
            payload['shared_source_references']=[dict(source_id=r['source_id'],version=r['version'],
                source_sha256=hashlib.sha256(r['text'].encode()).hexdigest()) for r in rows]
            agency=payload.pop('agency')
            agency.pop('original_sources')
            agency['shared_source_references']=payload['shared_source_references']
            payload['shared_agency_reference']=dict(actor=agency['actor'],
                source_references=payload['shared_source_references'],
                cognition_sha256=hashlib.sha256(json.dumps(agency,ensure_ascii=False,sort_keys=True).encode()).hexdigest())
        messages = [dict(role='system', content=_POLICY), dict(role='user',
            content=json.dumps(payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('plan context budget exceeded')
        return messages


def prepare_plan_feasibility(workspace, query, *, source_id, observer=None):
    match = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not match:
        raise ValueError('explicit bounded character/model plan question required')
    actor = match['actor']
    agency = prepare_agency(workspace, f"What are {actor}'s goals and plans?", source_id=source_id, observer=observer)
    semantic = workspace.prepare_semantic(query, source_ids=(source_id,), observer=observer)
    return check_plan_candidates(workspace,query,semantic,agency,source_id=source_id,actor=actor)


def is_reported_belief_update(body):
    return isinstance(body,str) and any(p.fullmatch(body.rstrip('.!?'))
        for p in (_REVISION,_CHALLENGE,_ACCEPT,_REJECT))


def check_plan_candidates(workspace, query, semantic, agency, *, source_id, actor,
                          relevant_events_only=False, dialogue_blocks=False):
    """Reuse C03 joins on shared grounded C01 and ordinary source evidence."""
    if type(relevant_events_only) is not bool or type(dialogue_blocks) is not bool:
        raise ValueError('explicit bounded plan selection flags required')
    validate_agency_candidate_scope(workspace,query,semantic,source_id=source_id,actor=actor)
    core=workspace.core
    if (not isinstance(agency,AgencyResult) or agency.scope!=semantic.scope
            or agency.source_versions!=tuple((s,workspace._versions[s]) for s in semantic.scope.source_ids)
            or agency.payload['actor']!=actor or any(k not in core.claims or core.claims[k].scope!=semantic.scope
                for k in agency.claim_ids)):
        raise ValueError('grounded current actor/source agency result required')
    original_sources=[dict(source_id=s,version=v,text=workspace._documents[s][0]) for s,v in agency.source_versions]
    if (agency.payload['original_sources']!=original_sources or
            any(core.claims[k].content.get('actor')!=actor for k in agency.claim_ids)):
        raise ValueError('agency payload source or actor differs from grounded claims')
    for plan in agency.payload['plans']:
        claim=core.claims.get(plan.get('claim_id'))
        if (claim is None or claim.id not in agency.claim_ids or
                claim.content.get('operation')!='GOAL_PLAN_OPPORTUNITY_JOIN' or
                {k:v for k,v in plan.items() if k not in ('claim_id','source_claim_ids')}!=
                {k:v for k,v in claim.content.items() if k not in ('operation','actor')}):
            raise ValueError('agency plan state differs from grounded join')
    agency.messages(workspace,include_sources=False,max_chars=128000)
    claims,rows=list(agency.claim_ids),[]
    statuses=core.support_statuses()
    for candidate in semantic.candidate_ids:
        content = core.claims[candidate].content
        if content['kind'] != 'event' or content['validation']['semantic_support'] != 'BOUNDED_LITERAL_FORM':
            continue
        row = content['proposal']
        if row['assertion_scope'] != 'SOURCE_REPORT' or statuses[candidate]!='SUPPORT_AVAILABLE':
            continue
        span = core.spans[content['source_span_id']]
        if relevant_events_only:
            from .epistemic import parse_mental_proposition, MentalProposition, Attitude
            body=row['utterance'].rstrip('.!?')
            direct=row.get('speaker_candidates')==[actor] and row.get('speaker_surface')==actor
            try:
                tree=parse_mental_proposition(body,actor) if direct else None
            except ValueError:
                tree=None
            belief=direct and ((isinstance(tree,MentalProposition) and tree.holder==actor
                and tree.attitude==Attitude.BELIEF and isinstance(tree.content,str)) or is_reported_belief_update(body))
            model_decl=row['speaker_surface']=='Narrator' and span.quote.startswith('Narrator:') and _MODEL.fullmatch(body)
            if not (belief or model_decl):
                continue
        rows.append((span.start, candidate, row, span))
    rows.sort(key=lambda row: row[0])
    if len(rows) > 16:
        raise ValueError('belief/model plan statement budget exceeded')
    timeline = RevisionTimeline(identity('plan-belief-domain', source_id),dialogue_blocks=dialogue_blocks)
    model = []
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for index, (_, candidate, row, span) in enumerate(rows, 1):
        stamp = (base + timedelta(seconds=index)).isoformat()
        timeline.record(candidate, span.quote, event_time=stamp, recorded_at=stamp)
        declaration = _MODEL.fullmatch(row['utterance'].rstrip('.!?'))
        if declaration and row['speaker_surface'] == 'Narrator' and span.quote.startswith('Narrator:'):
            claim = core.claim(semantic.scope, ClaimKind.SYSTEM_INTERPRETATION,
                dict(operation='EXPLICIT_DECLARED_MODEL_CONDITION', proposition=declaration['proposition'],
                    value=declaration['value'] == 'true', authority='SOURCE_DECLARED_MODEL_NOT_WORLD_TRUTH'))
            core.support(claim, candidate)
            core.interpret(claim, unknown_conditions=('model_accuracy_not_established',))
            claims.append(claim)
            model.append(dict(proposition=declaration['proposition'], value=declaration['value'] == 'true', claim_id=claim))
    end = (base + timedelta(seconds=len(rows) + 1)).isoformat()
    snapshot = timeline.snapshot(event_time=end, known_at=end).payload
    belief_claims, belief_states = {}, []
    evidence = {e['evidence_id']: e for e in snapshot['evidence']}
    event_records = {t['source_event_id']: t['record_id'] for t in snapshot['transitions']}
    for native in snapshot['estimates']:
        if native['subject_agent_id'] != actor:
            continue
        state = {k: v for k, v in native.items() if k != 'dependency_claim_id'}
        ids = {key for key, item in evidence.items() if item['subject_agent_id'] == actor and (item['proposition_key'] == state['proposition_key'] or item['supersedes_proposition_key'] == state['proposition_key'])}
        bound = {event_records[evidence[key]['source_event_id']] for key in ids}
        if not bound:
            continue
        claim = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='B03_REPORTED_BELIEF_FOR_PLAN', native_state=state,
                private_state='CONDITIONAL_ON_ACCURATE_SINCERE_SELF_REPORT', time='SOURCE_ORDER_ONLY'))
        core.support(claim, *sorted(bound))
        claims.append(claim)
        belief_claims[state['proposition_key']] = claim
        belief_states.append(state)
    results = []
    for plan in agency.payload['plans']:
        condition = plan['condition']
        proposition, expected = _literal(condition) if condition else (None, True)
        relevant_beliefs = [s for s in belief_states if _literal(s['proposition_key'])[0] == proposition] if condition else []
        truth_values = {_literal(s['proposition_key'])[1] for s in relevant_beliefs if s['status'] == 'AFFIRMED'}
        uncertain = any(s['status'] in ('CHARACTER_UNCERTAIN', 'CONFLICT') or s['unresolved_challenge_evidence_ids'] for s in relevant_beliefs)
        subjective = ('NO_CONDITION' if not condition else 'CONFLICT' if len(truth_values) > 1 else
            'UNRESOLVED' if uncertain else 'AFFIRMED_REQUIRED_CONDITION' if truth_values == {expected} else
            'AFFIRMED_OPPOSITE_CONDITION' if truth_values == {not expected} else
            'NOT_AFFIRMED_NOT_NEGATION' if any(s['status'] == 'DENIED' for s in relevant_beliefs) else 'UNKNOWN')
        relevant_model = [m for m in model if m['proposition'] == proposition] if condition else []
        model_values = {m['value'] for m in relevant_model}
        objective = ('NO_CONDITION' if not condition else 'CONFLICT' if len(model_values) > 1 else
            'DECLARED_CONDITION_MET' if model_values == {expected} else
            'DECLARED_CONDITION_CONTRADICTED' if model_values == {not expected} else 'UNKNOWN')
        eligible = plan['selection'] == 'REPORTED_SELECTED' and plan['goal_status'] == 'ACTIVE'
        opportunity = plan['opportunity']
        subject_check = ('NOT_CURRENTLY_PURSUED' if not eligible else
            'REPORTED_OPPORTUNITY_BLOCKED' if opportunity == 'REPORTED_UNAVAILABLE' else
            'OPPORTUNITY_UNRESOLVED' if opportunity != 'REPORTED_AVAILABLE' else
            'SUPPORTED_UNDER_REPORTED_BELIEFS' if subjective in ('NO_CONDITION', 'AFFIRMED_REQUIRED_CONDITION') else
            'CONTRADICTED_UNDER_REPORTED_BELIEFS' if subjective == 'AFFIRMED_OPPOSITE_CONDITION' else 'BELIEF_CONDITION_UNRESOLVED')
        model_check = ('MODEL_CONDITION_CONTRADICTED' if objective == 'DECLARED_CONDITION_CONTRADICTED' else
            'MODEL_CONDITION_SUPPORTED_ONLY' if objective in ('NO_CONDITION', 'DECLARED_CONDITION_MET') else 'MODEL_CONDITION_UNRESOLVED')
        relation = ('BELIEF_MODEL_DIVERGENCE_NOT_KNOWING_INFEASIBILITY' if
            (subjective == 'AFFIRMED_REQUIRED_CONDITION' and objective == 'DECLARED_CONDITION_CONTRADICTED') or
            (subjective == 'AFFIRMED_OPPOSITE_CONDITION' and objective == 'DECLARED_CONDITION_MET') else
            'NO_ESTABLISHED_DIVERGENCE')
        result = dict(action=plan['action'], goal=plan['goal'], condition=condition, selection=plan['selection'],
            goal_status=plan['goal_status'], opportunity=opportunity, subjective_condition=subjective,
            declared_model_condition=objective, subjective_feasibility=subject_check, model_condition_check=model_check,
            relation=relation, values_change='NOT_INFERRED', world_feasibility='NOT_ESTABLISHED',
            deliberate_impossibility='NOT_INFERRED')
        claim = core.claim(semantic.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='BELIEF_PLAN_DECLARED_MODEL_JOIN', actor=actor, **result))
        supports = [plan['claim_id']] + [belief_claims[s['proposition_key']] for s in relevant_beliefs] + [m['claim_id'] for m in relevant_model]
        core.support(claim, *supports)
        claims.append(claim)
        results.append(dict(result, claim_id=claim, support_claim_ids=supports))
    versions = tuple((s, workspace._versions[s]) for s in semantic.scope.source_ids)
    payload = dict(query=query, actor=actor, original_sources=[dict(source_id=s, version=v, text=workspace._documents[s][0]) for s, v in versions],
        plans=results, reported_belief_states=belief_states, declared_model=model, agency=agency.payload,
        belief_transition_receipts=[dict({k: v for k, v in t.items() if k != 'dependency_claim_id'}, original_candidate_id=t['record_id']) for t in snapshot['transitions']],
        temporal_assumption='ORDINAL_SOURCE_ORDER_ADAPTER_NOT_REAL_CALENDAR_TIME',
        source_authority='ACCURATE_SELF_REPORT_AND_DECLARED_MODEL_ARE_CONDITIONS_NOT_FACTS',
        provider_calls=0, policy=_POLICY)
    return PlanFeasibility(semantic.scope, versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(claims))
