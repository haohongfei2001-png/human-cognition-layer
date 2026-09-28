"""Unified execution with caller-supplied model and explicit optional preparation."""
from dataclasses import dataclass
import hashlib
import json
from hcl.v04.model import EventRecord
from .context import ANSWER_POLICY, CognitionContext, evidence_level, event_row
from .router import CognitionPlan, CognitionRequest, CognitionRouter
from .router import PerspectiveMode


@dataclass(frozen=True)
class PreparedAnswer:
    plan: CognitionPlan
    context: CognitionContext | None
    messages: tuple[dict, ...]
    preparation_receipt: dict | None = None


@dataclass(frozen=True)
class AnswerReceipt:
    answer: str
    prepared: PreparedAnswer


class HCLCognitionLayer:
    """Model adapter: callable(messages)->str or object.complete(messages)->str.

    Validated historical runtimes may be injected to reuse committed semantic
    evidence. Extraction is opt-in through an explicit adapter and request flag.
    Without an injected runtime each request gets isolated transient state.
    """
    def __init__(self, base_model, *, intentions=None, affects=None, router=None,
                 semantic_preparer=None):
        if affects is not None:
            if intentions is not None and affects.intentions is not intentions:
                raise ValueError('affect and intention runtimes must share state')
            intentions = affects.intentions
        self.base_model = base_model
        self.intentions = intentions
        self.affects = affects
        self.router = router or CognitionRouter()
        self.semantic_preparer = semantic_preparer

    def prepare(self, request: CognitionRequest):
        plan = self.router.plan(request)
        if plan.direct:
            # No runtime construction/projection, extraction, or tool invocation.
            payload = {'query': request.query, 'history': list(request.history),
                       'evidence': [event_row(e) for e in request.evidence],
                       'narrative': request.narrative}
            return PreparedAnswer(plan, None, ({'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},))

        from hcl.v07 import HCLV07Runtime
        from hcl.v06 import SYSTEM_VIEWER
        from .cg01 import check_explanations
        from .narrative import SemanticPreparation, prepare_narrative
        from .tools import execute_tool
        parsed_events = candidates = facts = ()
        preparation_audit = {'method': 'caller_typed_evidence', 'semantic_preparer_calls': 0,
                             'extraction_provider_calls': 0, 'answer_provider_calls': 1,
                             'extraction_spend_usd': 0, 'answer_spend_usd': None,
                             'failure': None, 'input': None, 'output': None,
                             'time_basis': 'caller_supplied_event_times'}
        if plan.explanation and request.narrative:
            parsed_events, candidates, facts, _ = prepare_narrative(
                request.narrative, request.query, plan.target_actor)
            preparation_audit.update(method='bounded_deterministic_narrative',
                input={'query': request.query, 'narrative': request.narrative,
                       'target_actor': plan.target_actor, 'perspective_mode': plan.perspective_mode.value},
                output={'event_ids': [e.event_id for e in parsed_events],
                        'candidate_ids': [c.candidate_id for c in candidates],
                        'fact_ids': [f.fact_id for f in facts]},
                time_basis='sentence_order_not_calendar_time')
            if not candidates and request.allow_semantic_preparation:
                if self.semantic_preparer is None:
                    preparation_audit['failure'] = 'semantic_preparer_unavailable'
                else:
                    preparation_audit['semantic_preparer_calls'] = 1
                    result = None
                    try:
                        result = self.semantic_preparer(dict(preparation_audit['input']))
                        if not isinstance(result, SemanticPreparation):
                            raise ValueError('invalid semantic preparation output')
                        if (type(result.provider_calls) is not int or result.provider_calls < 0 or
                            not isinstance(result.raw_output, str) or len(result.raw_output) > 64000 or
                            not isinstance(result.model_id, str) or not result.model_id or
                            (result.cost_usd is not None and
                             (not isinstance(result.cost_usd, (int, float)) or result.cost_usd < 0)) or
                            len(result.events) > 23 or
                            len(result.candidates) > 3 or len(result.facts) > 48):
                            raise ValueError('semantic preparation bounds exceeded')
                        if any(e.raw_text not in request.narrative or not e.metadata.get('reader_only')
                               for e in result.events):
                            raise ValueError('unanchored or non-reader-only semantic event')
                        check_explanations(result.candidates, result.facts, result.events,
                                           mode=PerspectiveMode.READER_ANALYSIS.value)
                        digest = hashlib.sha256(request.narrative.encode()).hexdigest()[:12]
                        full_source = EventRecord('narrative-full-' + digest,
                            '2026-01-01T00:00:00+00:00', request.narrative,
                            'authorized-narrative-order-only',
                            '2026-01-01T00:00:00+00:00', metadata={'reader_only': True})
                        if any(e.event_id == full_source.event_id for e in result.events):
                            raise ValueError('reserved full-source event ID')
                        parsed_events, candidates, facts = ((full_source,) + result.events,
                            result.candidates, result.facts)
                        preparation_audit.update(method='explicit_semantic_preparer',
                            extraction_provider_calls=result.provider_calls,
                            extraction_spend_usd=result.cost_usd, model_id=result.model_id,
                            output=result.raw_output,
                            source_span_diagnostics=list(result.source_span_diagnostics))
                    except (ValueError, TypeError, KeyError, AttributeError):
                        preparation_audit.update(failure='invalid_semantic_preparation',
                            extraction_provider_calls=(result.provider_calls
                                if isinstance(result, SemanticPreparation) else None),
                            extraction_spend_usd=(result.cost_usd
                                if isinstance(result, SemanticPreparation) else None),
                            model_id=(result.model_id
                                if isinstance(result, SemanticPreparation) else None),
                            output=(result.raw_output
                                if isinstance(result, SemanticPreparation) else None))
                    except Exception:
                        preparation_audit.update(failure='semantic_preparer_error',
                            extraction_provider_calls=None, extraction_spend_usd=None,
                            output=None)
        input_evidence = request.evidence + parsed_events
        if plan.explanation and len(input_evidence) > 24:
            raise ValueError('CG-01 accepts at most 24 evidence events')
        explanation_rows = (check_explanations(candidates, facts, input_evidence,
            mode=plan.perspective_mode.value, observer_actor=request.observer_actor,
            event_time=request.event_time, knowledge_cutoff=request.knowledge_cutoff)
            if candidates else ())
        intentions = self.intentions or HCLV07Runtime()
        perspectives = intentions.perspectives
        # Detect all collisions before appending any input to a persistent view.
        known = {e.event_id: e for e in perspectives.events}
        for event in input_evidence:
            if event.event_id in known and known[event.event_id] != event:
                raise ValueError('event ID conflicts with committed state')
            if event.event_id in known and known[event.event_id] == event:
                continue
            if sum(e.event_id == event.event_id for e in input_evidence) > 1:
                raise ValueError('duplicate input evidence ID')
        for event in input_evidence:
            intentions.ingest_event(event)
        target = plan.target_actor
        if target is None:
            mentioned = [a for a in perspectives.known_agents if a != SYSTEM_VIEWER and a.lower() in request.query.lower().split()]
            if len(mentioned) == 1:
                target = mentioned[0]
        # A person task with no unambiguous actor must fail closed, never use
        # the system view as if it were a character view.
        person_task = any(c in plan.capabilities for c in ('perspective', 'intention', 'affect'))
        scope = {'event_time': request.event_time, 'knowledge_cutoff': request.knowledge_cutoff}
        context = CognitionContext(temporal_scope=scope, perspective_mode=plan.perspective_mode.value)
        if request.narrative and plan.explanation and not candidates and not preparation_audit['failure']:
            preparation_audit['failure'] = 'no_action_anchor'
        context.preparation = {key: value for key, value in preparation_audit.items()
                               if key not in ('input', 'output')}
        viewer = (SYSTEM_VIEWER if plan.perspective_mode == PerspectiveMode.READER_ANALYSIS
                  else request.observer_actor or target)
        if person_task and (target is None or target == SYSTEM_VIEWER):
            visible = ()
            context.uncertainty.append({'status': 'SYSTEM_INSUFFICIENT', 'reason': 'explicit target_actor required'})
        else:
            if plan.perspective_mode == PerspectiveMode.OBSERVER_ABOUT_TARGET:
                view = perspectives.second_order_view(request.observer_actor, target, **scope)
            elif plan.perspective_mode == PerspectiveMode.CHARACTER_PERSPECTIVE:
                view = perspectives.perspective_view(target, **scope)
            else:
                view = perspectives.perspective_view(SYSTEM_VIEWER, **scope)
            visible = view.events
            if 'perspective' in plan.capabilities:
                projected = perspectives.answer_context(target, observer_agent_id=request.observer_actor, **scope)
                # Reader source evidence and target information are distinct.
                context.perspective = {'target_actor': target, 'observer_actor': request.observer_actor,
                                       'order': projected.perspective_order,
                                       'event_ids': list(projected.target_information_view.event_ids),
                                       'visible_event_ids': list(view.event_ids),
                                       'mode': plan.perspective_mode.value}
                belief_rows = (perspectives.subject_beliefs(target, viewer_agent_id=target, **scope)
                    if plan.perspective_mode == PerspectiveMode.CHARACTER_PERSPECTIVE else
                    projected.belief_estimates)
                context.belief = [b.as_dict() for b in belief_rows
                    if any((b.basis_evidence_ids, b.unresolved_challenge_evidence_ids,
                            b.indirect_support_evidence_ids, b.indirect_counter_evidence_ids))]
                # Historical v0.6 enumerates global proposition names even when
                # an observer has zero supporting evidence. Never serialize
                # those hidden/future names into the observer answer context.
                if not context.belief:
                    context.uncertainty.append({'status': 'SYSTEM_INSUFFICIENT', 'reason': 'no committed belief evidence; exposure is not acceptance'})
            if 'intention' in plan.optional_capabilities:
                semantic_viewer = (SYSTEM_VIEWER if plan.perspective_mode == PerspectiveMode.READER_ANALYSIS
                    else request.observer_actor or target)
                projected = intentions.answer_context(target, observer_agent_id=semantic_viewer, **scope)
                context.explicit_intention = [dict(row, evidence_level=('MODEL_INFERENCE' if row['signal'] == 'INFERRED_MOTIVATION' else evidence_level(row['provenance']))) for row in projected['intention_evidence']]
                if not context.explicit_intention:
                    context.uncertainty.append({'status': 'SYSTEM_INSUFFICIENT', 'reason': 'no committed intention evidence; use source cautiously'})
            if 'affect' in plan.optional_capabilities:
                if self.affects is not None:
                    semantic_viewer = (SYSTEM_VIEWER if plan.perspective_mode == PerspectiveMode.READER_ANALYSIS
                        else request.observer_actor or target)
                    projected = self.affects.answer_context(target, observer_agent_id=semantic_viewer, **scope)
                    context.affect_evidence = [dict(row, evidence_level=('MODEL_INFERENCE' if row['strength'] == 'INFERRED' else evidence_level(row['provenance']))) for row in projected['current_evidence']]
                if not context.affect_evidence:
                    context.uncertainty.append({'status': 'SYSTEM_INSUFFICIENT', 'reason': 'no committed affect evidence; action does not prove feeling'})
            if plan.explanation and target:
                action_scope = candidates[0].action_time if candidates else request.event_time
                if plan.perspective_mode == PerspectiveMode.OBSERVER_ABOUT_TARGET:
                    target_view = perspectives.second_order_view(request.observer_actor, target,
                        event_time=action_scope, knowledge_cutoff=request.knowledge_cutoff)
                else:
                    target_view = perspectives.perspective_view(target, event_time=action_scope,
                        knowledge_cutoff=request.knowledge_cutoff)
                context.perspective = {'target_actor': target, 'observer_actor': request.observer_actor,
                    'mode': plan.perspective_mode.value, 'target_access_at_action_event_ids': list(target_view.event_ids),
                    'visible_event_ids': list(view.event_ids)}
                if candidates:
                    context.explanations = list(explanation_rows)
                else:
                    context.uncertainty.append({'status': 'SYSTEM_INSUFFICIENT',
                        'reason': 'no action and candidate explanation anchored by the bounded narrative grammar'})
                context.open_unknown_candidate = {'status': 'OPEN',
                    'reason': 'other explanations remain possible; no unique motive inferred'}
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
                perspective_mode=plan.perspective_mode.value,
                uncertainty=[{'status': 'SYSTEM_INSUFFICIENT', 'reason': 'context budget exceeded; request a narrower source/time scope'}])
            payload = self._payload(request.query, context)
        return PreparedAnswer(plan, context, ({'role': 'system', 'content': ANSWER_POLICY},
                                              {'role': 'user', 'content': payload}), preparation_audit)

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
