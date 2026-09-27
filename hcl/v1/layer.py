"""Unified execution with caller-supplied base model, zero extraction calls."""
from dataclasses import dataclass
import json
from .context import ANSWER_POLICY, CognitionContext, evidence_level, event_row
from .router import CognitionPlan, CognitionRequest, CognitionRouter


@dataclass(frozen=True)
class PreparedAnswer:
    plan: CognitionPlan
    context: CognitionContext | None
    messages: tuple[dict, ...]


@dataclass(frozen=True)
class AnswerReceipt:
    answer: str
    prepared: PreparedAnswer


class HCLCognitionLayer:
    """Model adapter: callable(messages)->str or object.complete(messages)->str.

    Validated historical runtimes may be injected to reuse committed semantic
    evidence. v1 does not schedule extraction or guess access, beliefs or motives.
    Without an injected runtime each request gets isolated transient state.
    """
    def __init__(self, base_model, *, intentions=None, affects=None, router=None):
        if affects is not None:
            if intentions is not None and affects.intentions is not intentions:
                raise ValueError('affect and intention runtimes must share state')
            intentions = affects.intentions
        self.base_model = base_model
        self.intentions = intentions
        self.affects = affects
        self.router = router or CognitionRouter()

    def prepare(self, request: CognitionRequest):
        plan = self.router.plan(request)
        if plan.direct:
            # No runtime construction/projection, extraction, or tool invocation.
            payload = {'query': request.query, 'history': list(request.history),
                       'evidence': [event_row(e) for e in request.evidence]}
            return PreparedAnswer(plan, None, ({'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},))

        from hcl.v07 import HCLV07Runtime
        from hcl.v06 import SYSTEM_VIEWER
        from .tools import execute_tool
        intentions = self.intentions or HCLV07Runtime()
        perspectives = intentions.perspectives
        # Detect all collisions before appending any input to a persistent view.
        known = {e.event_id: e for e in perspectives.events}
        for event in request.evidence:
            if event.event_id in known and known[event.event_id] != event:
                raise ValueError('event ID conflicts with committed state')
        for event in request.evidence:
            intentions.ingest_event(event)
        target = request.target_actor
        if target is None:
            mentioned = [a for a in perspectives.known_agents if a != SYSTEM_VIEWER and a.lower() in request.query.lower().split()]
            if len(mentioned) == 1:
                target = mentioned[0]
        # A person task with no unambiguous actor must fail closed, never use
        # the system view as if it were a character view.
        person_task = any(c in plan.capabilities for c in ('perspective', 'intention', 'affect'))
        scope = {'event_time': request.event_time, 'knowledge_cutoff': request.knowledge_cutoff}
        context = CognitionContext(temporal_scope=scope)
        viewer = request.observer_actor or target or SYSTEM_VIEWER
        if person_task and (target is None or target == SYSTEM_VIEWER):
            visible = ()
            context.uncertainty.append({'status': 'SYSTEM_INSUFFICIENT', 'reason': 'explicit target_actor required'})
        else:
            if request.observer_actor:
                view = perspectives.second_order_view(request.observer_actor, target, **scope)
            else:
                view = perspectives.perspective_view(target or SYSTEM_VIEWER, **scope)
            visible = view.events
            if 'perspective' in plan.capabilities:
                projected = perspectives.answer_context(target, observer_agent_id=request.observer_actor, **scope)
                # Only the target's bounded events go into evidence. Belief
                # estimates remain a separate evidence-about-belief channel.
                context.perspective = {'target_actor': target, 'observer_actor': request.observer_actor,
                                       'order': projected.perspective_order, 'event_ids': list(view.event_ids)}
                context.belief = [b.as_dict() for b in projected.belief_estimates
                    if any((b.basis_evidence_ids, b.unresolved_challenge_evidence_ids,
                            b.indirect_support_evidence_ids, b.indirect_counter_evidence_ids))]
                # Historical v0.6 enumerates global proposition names even when
                # an observer has zero supporting evidence. Never serialize
                # those hidden/future names into the observer answer context.
                if not context.belief:
                    context.uncertainty.append({'status': 'SYSTEM_INSUFFICIENT', 'reason': 'no committed belief evidence; exposure is not acceptance'})
            if 'intention' in plan.optional_capabilities:
                projected = intentions.answer_context(target, observer_agent_id=request.observer_actor, **scope)
                context.explicit_intention = [dict(row, evidence_level=('MODEL_INFERENCE' if row['signal'] == 'INFERRED_MOTIVATION' else evidence_level(row['provenance']))) for row in projected['intention_evidence']]
                if not context.explicit_intention:
                    context.uncertainty.append({'status': 'SYSTEM_INSUFFICIENT', 'reason': 'no committed intention evidence; use source cautiously'})
            if 'affect' in plan.optional_capabilities:
                if self.affects is not None:
                    projected = self.affects.answer_context(target, observer_agent_id=request.observer_actor or target, **scope)
                    context.affect_evidence = [dict(row, evidence_level=('MODEL_INFERENCE' if row['strength'] == 'INFERRED' else evidence_level(row['provenance']))) for row in projected['current_evidence']]
                if not context.affect_evidence:
                    context.uncertainty.append({'status': 'SYSTEM_INSUFFICIENT', 'reason': 'no committed affect evidence; action does not prove feeling'})
        context.evidence = [event_row(e) for e in visible]
        context.provenance = [{'source_event_id': e.event_id, 'source_id': e.source_id,
                               'actor_id': e.actor_id, 'evidence_level': 'SYSTEM_UNKNOWN',
                               'note': 'raw source; no private-state attribution inferred'} for e in visible]
        support_ids = {eid for row in context.belief for key in (
            'basis_evidence_ids', 'unresolved_challenge_evidence_ids',
            'indirect_support_evidence_ids', 'indirect_counter_evidence_ids') for eid in row[key]}
        context.provenance.extend({'evidence_id': row.evidence_id,
            'source_event_id': row.source_event_id, 'source_agent_id': row.source_agent_id,
            'evidence_level': evidence_level(row.evidence_kind.value),
            'channel': 'evidence_about_belief_not_character_information'}
            for row in perspectives.belief_evidence if row.evidence_id in support_ids)
        context.actors = sorted({a for a in (target, request.observer_actor) if a})
        context.unsupported_inferences = ['action implies motive', 'action implies private emotion',
                                          'information exposure implies belief revision',
                                          'system insufficient implies character uncertain',
                                          'conditional computation implies observed truth']
        source_by_id = {e.event_id: e for e in visible}
        for tool in request.tools:
            source = source_by_id.get(tool.source_event_id)
            if source is None:
                context.uncertainty.append({'status': 'SYSTEM_INSUFFICIENT', 'capability': tool.capability_id,
                                            'reason': 'tool source absent from bounded view'})
                continue
            try:
                result = execute_tool(tool, source, perspectives, viewer=viewer, **scope)
            except (ValueError, KeyError, TypeError) as exc:
                # Preserve system-level failure, no partial tool truth. Details
                # may contain private input, so do not add exception text.
                context.uncertainty.append({'status': 'INVALID_TOOL_INPUT', 'capability': tool.capability_id})
            else:
                context.tool_results.append(result)
        for cid in plan.blocked_tools:
            context.uncertainty.append({'status': 'SYSTEM_INSUFFICIENT', 'capability': cid,
                                        'reason': 'declared exact inputs unavailable; no automatic formalization'})
        payload = self._payload(request.query, context)
        if len(context.serialized()) > request.max_context_chars:
            # Do not arbitrarily truncate a source or promote partial evidence.
            context = CognitionContext(temporal_scope=scope, actors=context.actors,
                uncertainty=[{'status': 'SYSTEM_INSUFFICIENT', 'reason': 'context budget exceeded; request a narrower source/time scope'}])
            payload = self._payload(request.query, context)
        return PreparedAnswer(plan, context, ({'role': 'system', 'content': ANSWER_POLICY},
                                              {'role': 'user', 'content': payload}))

    @staticmethod
    def _payload(query, context):
        return json.dumps({'query': query, 'cognition_context': context.as_dict()}, ensure_ascii=False, sort_keys=True)

    def answer(self, query, *, debug=False, **kwargs):
        request = query if isinstance(query, CognitionRequest) else CognitionRequest(query, **kwargs)
        prepared = self.prepare(request)
        if callable(self.base_model):
            answer = self.base_model(list(prepared.messages))
        else:
            answer = self.base_model.complete(list(prepared.messages))
        if not isinstance(answer, str):
            raise TypeError('base model adapter must return an answer string')
        return AnswerReceipt(answer, prepared) if debug else answer
