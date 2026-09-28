"""Join action-time plan checks to explanations without backfilling later belief."""
from dataclasses import dataclass
import json
import re

from .action_explanations import prepare_explanations
from .appraisal import prepare_appraisal
from .core import ClaimKind
from .plan_feasibility import prepare_plan_feasibility
from .workspace import CognitionWorkspace

_QUERY = re.compile(r'Why did (?P<actor>[A-Z][\w-]*) (?P<action>[^?]+), considering their plans and appraisal of (?P<episode>[^?]+)\?')
_POLICY = ('These are conditional, nonexclusive explanations, never established motives. '
    'The action-time source prefix and the current source projection are separate. '
    'Later belief cannot repair or undermine an earlier explanation without an explicit '
    'earlier-time claim. Declared model failure is not character knowledge. Appraisal '
    'is not actual feeling. No unique motive, private emotion or moral truth is inferred. '
    'Source order is an explicit assumption, not verified event chronology.')


class SemanticWorkspace(CognitionWorkspace):
    """Question-neutral extraction shared by the opt-in operation chain.

    A configured backend is bounded to one attempt unless the caller explicitly
    supplies another budget. An exception consumes an attempt; no hidden retries.
    """
    def __init__(self, *, semantic_backend=None, max_backend_calls=1):
        super().__init__()
        if type(max_backend_calls) is not int or not 0 <= max_backend_calls <= 4:
            raise ValueError('bounded extraction attempt budget required')
        self.semantic_backend = semantic_backend
        self.max_backend_calls = max_backend_calls
        self.backend_attempts = 0
        self.semantic_cache = {}

    def prepare_semantic(self, query, *, source_ids, observer=None, backend=None):
        selected = backend if backend is not None else self.semantic_backend
        if not isinstance(source_ids, tuple) or any(s not in self._documents for s in source_ids):
            raise ValueError('registered source tuple required')
        key = (tuple((s, self._versions[s]) for s in source_ids), observer, id(selected))
        cached = self.semantic_cache.get(key)
        if cached and all(c in self.core.grounded() for c in cached.root_ids):
            return cached
        visible = any(observer is None or observer in self._documents[s][1] for s in source_ids)
        if selected is not None and visible:
            if self.backend_attempts >= self.max_backend_calls:
                raise ValueError('extraction attempt budget exhausted')
            self.backend_attempts += 1
        result = super().prepare_semantic('Extract source-anchored literal speech events without inferring mental states.',
            source_ids=source_ids, observer=observer, backend=selected)
        self.semantic_cache[key] = result
        return result


@dataclass(frozen=True)
class AgencyChain:
    source_versions: tuple
    payload_json: str
    claim_ids: tuple

    @property
    def payload(self):
        return json.loads(self.payload_json)

    def messages(self, workspace, *, max_chars=64000):
        if type(max_chars) is not int or not 1000 <= max_chars <= 128000:
            raise ValueError('bounded chain context required')
        if any(s not in workspace._documents or workspace._versions[s] != v for s, v in self.source_versions):
            raise ValueError('chain source changed; recompute')
        statuses = workspace.core.support_statuses()
        if any(statuses.get(c) != 'SUPPORT_AVAILABLE' for c in self.claim_ids):
            raise ValueError('chain support changed; recompute')
        messages = [dict(role='system', content=_POLICY), dict(role='user', content=json.dumps(self.payload, ensure_ascii=False, sort_keys=True))]
        if len(json.dumps(messages, ensure_ascii=False)) > max_chars:
            raise ValueError('chain context budget exceeded')
        return messages


def prepare_agency_chain(workspace, query, *, source_id, observer=None):
    match = _QUERY.fullmatch(query) if isinstance(query, str) and len(query) <= 8000 else None
    if not match or len(match['action']) > 300 or len(match['episode']) > 160:
        raise ValueError('bounded actor/action/appraisal question required')
    actor, action, episode = match['actor'], match['action'], match['episode']
    explanations = prepare_explanations(workspace, f'Why did {actor} {action}?', source_id=source_id, observer=observer)
    plan_query = f"Could {actor}'s plans work under their beliefs and the declared model?"
    current = prepare_plan_feasibility(workspace, plan_query, source_id=source_id, observer=observer)
    appraisal = prepare_appraisal(workspace, f'How does {actor} appraise {episode}?', source_id=source_id, observer=observer)
    core, exp = workspace.core, explanations.payload
    claims = list(explanations.claim_ids + current.claim_ids + appraisal.claim_ids)
    prior_plans, prefix_receipt, bridge = [], None, None
    if exp.get('action_source_end') is not None:
        original, acl = workspace._documents[source_id]
        end = exp['action_source_end']
        prefix = original[:end]
        local = SemanticWorkspace()
        local.put_source(source_id, prefix, permitted_observers=acl)
        prior = prepare_plan_feasibility(local, plan_query, source_id=source_id, observer=observer)
        # The prefix is an exact span in the original source version. A derived
        # workspace is never silently promoted to an independent source.
        span = core.add_span(original, source_id=source_id, version=workspace._versions[source_id],
            start=0, end=end, permitted_observers=acl)
        workspace._version_spans[source_id].add(span)
        root = core.claim(explanations.scope, ClaimKind.SOURCE_REPORT,
            dict(source_id=source_id, end=end, role='ACTION_SOURCE_PREFIX'))
        core.support(root, span)
        prior_plans = [{k: v for k, v in p.items() if k not in ('claim_id', 'support_claim_ids')} for p in prior.payload['plans']]
        prefix_receipt = dict(source_span_id=span, end=end, time_assumption='SOURCE_ORDER_PREFIX_NOT_VERIFIED_CHRONOLOGY',
            plans=prior_plans, reported_belief_states=prior.payload['reported_belief_states'])
        bridge = core.claim(explanations.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='ACTION_PREFIX_PLAN_CHECK', **prefix_receipt))
        core.support(bridge, root)
        claims.append(bridge)
    joined = []
    for candidate in exp['explanations']:
        goals = {c['key'] for c in candidate['conditions'] if c['kind'] == 'GOAL'}
        linked = [p for p in prior_plans if p['goal'] in goals and p['action'] == action]
        states = {p['subjective_feasibility'] for p in linked}
        plan_status = ('NOT_A_GOAL_CANDIDATE' if not goals else 'UNRESOLVED' if not states else
            'SUPPORTED_PLAN_AVAILABLE' if states == {'SUPPORTED_UNDER_REPORTED_BELIEFS'} else
            'PLAN_COUNTEREVIDENCE' if states <= {'CONTRADICTED_UNDER_REPORTED_BELIEFS', 'REPORTED_OPPORTUNITY_BLOCKED', 'NOT_CURRENTLY_PURSUED'} else
            'MIXED_OR_UNRESOLVED_PLANS')
        disposition = candidate['disposition']
        if goals and disposition == 'CONDITIONALLY_SUPPORTED':
            disposition = ('WEAKENED_BY_PLAN_COUNTEREVIDENCE' if plan_status == 'PLAN_COUNTEREVIDENCE' else
                'CONDITIONALLY_SUPPORTED' if plan_status == 'SUPPORTED_PLAN_AVAILABLE' else 'PLAN_DEPENDENCY_UNRESOLVED')
        result = dict(hypothesis=candidate['hypothesis'], original_condition_check=candidate['disposition'],
            disposition=disposition, linked_action_time_plans=linked, plan_dependency=plan_status,
            actual_motive='NOT_ESTABLISHED', unique_motive='NOT_INFERRED', condition_claim_id=candidate['claim_id'])
        claim = core.claim(explanations.scope, ClaimKind.CONDITIONAL_TOOL_RESULT,
            dict(operation='ACTION_EXPLANATION_PLAN_DEPENDENCY_JOIN', **result))
        core.support(claim, candidate['claim_id'], *([bridge] if goals and bridge else []))
        claims.append(claim)
        joined.append(dict(result, claim_id=claim))
    payload = dict(query=query, actor=actor, action=action, original_sources=current.payload['original_sources'],
        action_quote=exp.get('action_quote'), action_time=prefix_receipt,
        current_plans=current.payload['plans'], current_beliefs=current.payload['reported_belief_states'],
        explanations=joined, appraisal=appraisal.payload['appraisal'],
        appraisal_causation='NO_PLAN_FAILURE_TO_EMOTION_INFERENCE', source_authority='CONDITIONAL_SOURCE_REPORTS',
        status='CHECKED_CONDITIONAL_CHAIN' if joined else 'SYSTEM_INSUFFICIENT_ACTION', policy=_POLICY)
    return AgencyChain(explanations.source_versions, json.dumps(payload, ensure_ascii=False, sort_keys=True), tuple(claims))
