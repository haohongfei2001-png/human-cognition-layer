"""Compose existing source-scoped operations; never infer bridges between them."""
from dataclasses import dataclass
import json

from .compact import compact_cognition_context, COMPACT_POLICY
from .context import ANSWER_POLICY
from .layer import HCLCognitionLayer
from .router import CognitionRequest, PerspectiveMode

COMPOSITION_POLICY = (
    'The operations below analyze the same authorized source and focal actor. '
    'Keep each operation scope and its uncertainty distinct. Combine them to '
    'answer the question, without treating local concept criteria as preferences, '
    'preferences as intention/control, or any source claim as a moral conclusion. '
    'A responsibility explanation remains conditional on that operation caller '
    'premise. Failure or missing state in one operation is unresolved, not support '
    'from another. Never transfer evidence across operation access boundaries.'
)


@dataclass(frozen=True)
class ComposedAnswer:
    plans: tuple
    stages: tuple
    messages: tuple[dict, ...]
    preparation_receipt: dict


@dataclass(frozen=True)
class ComposedAnswerReceipt:
    answer: str
    prepared: ComposedAnswer


def _operation(plan):
    active = [name for name, yes in (
        ('responsibility', plan.responsibility_structure),
        ('preferences', plan.contextual_preference),
        ('concepts', plan.concept_interpretation)) if yes]
    if len(active) != 1:
        raise ValueError('composition requires explicit existing CG03/04/05 operations')
    return active[0]


def prepare_composed_answer(layer, query, requests, *, max_context_chars=48000, compact_context=True):
    """Prepare 2–3 existing operations, from a common source, with no model calls."""
    if not isinstance(layer, HCLCognitionLayer):
        raise ValueError('existing cognition layer required')
    if not isinstance(query, str) or not query.strip() or len(query) > 16000:
        raise ValueError('bounded composed question required')
    if (not isinstance(requests, tuple) or not 2 <= len(requests) <= 3 or
        not all(isinstance(r, CognitionRequest) for r in requests)):
        raise ValueError('two or three bounded existing operation requests required')
    if type(max_context_chars) is not int or not 512 <= max_context_chars <= 64000 or type(compact_context) is not bool:
        raise ValueError('bounded composition context and explicit encoding required')
    first = requests[0]
    if not first.target_actor or not (first.narrative or first.evidence):
        raise ValueError('one focal actor and authorized shared source required')
    signature = lambda r: (r.target_actor, r.observer_actor, r.event_time, r.knowledge_cutoff, r.narrative, r.evidence, r.narrative_access)
    if any(signature(r) != signature(first) for r in requests):
        raise ValueError('operations must share exact actor, observer, source and time scope')
    if any(r.allow_semantic_preparation or r.tools for r in requests):
        raise ValueError('composition cannot schedule extraction or formal tools')
    plans = tuple(layer.router.plan(r) for r in requests)
    operations = tuple(_operation(p) for p in plans)
    if len(set(operations)) != len(operations) or len({p.perspective_mode for p in plans}) != 1:
        raise ValueError('distinct operations with identical perspective required')
    mode = plans[0].perspective_mode
    # Existing prose paths have different historical speaker-access assumptions.
    # Do not infer an access channel while joining them: ordinary input is reader
    # analysis; private views need shared validated typed EventRecords.
    if first.narrative and mode != PerspectiveMode.READER_ANALYSIS and not first.narrative_access:
        raise ValueError('ordinary composition requires reader analysis; private views need typed access')
    if layer.intentions is not None or layer.affects is not None:
        raise ValueError('composition requires request-local state; injected persistent views need explicit scoped integration')
    stages = tuple(layer.prepare(r) for r in requests)
    contexts = []
    for p in stages:
        row = p.context.as_dict()
        row['preparation'] = dict(row['preparation'], answer_provider_calls=0,
            answer_execution='DEFERRED_TO_SINGLE_COMPOSED_ANSWER')
        contexts.append(compact_cognition_context(row) if compact_context else row)
    state = dict(focal_actor=first.target_actor, perspective_mode=mode.value,
        observer_actor=first.observer_actor,
        temporal_scope={'event_time': first.event_time, 'knowledge_cutoff': first.knowledge_cutoff},
        operation_contexts=[dict(operation=op, cognition_context=row) for op, row in zip(operations, contexts)],
        cross_operation_inference='NO_AUTOMATIC_CONCEPT_PREFERENCE_INTENTION_OR_MORAL_PROMOTION')
    serialized = json.dumps(state, ensure_ascii=False, sort_keys=True)
    failure = None
    if len(serialized) > max_context_chars:
        failure = 'composition_context_budget_exceeded'
        state = dict(focal_actor=first.target_actor, perspective_mode=mode.value,
            temporal_scope=state['temporal_scope'], operation_contexts=[],
            uncertainty=[dict(status='SYSTEM_INSUFFICIENT', reason='composition context budget exceeded; narrow the shared source')])
    policies = tuple(dict.fromkeys(p.messages[0]['content'] for p in stages))
    # One policy per actual operation, avoiding multiple copies of shared policy.
    additions = [p.removeprefix(ANSWER_POLICY).strip() for p in policies]
    policy = ANSWER_POLICY + ' ' + ' '.join(a for a in additions if a) + ' ' + COMPOSITION_POLICY
    if compact_context:
        # A compact stage may already carry this policy; include it once only.
        policy = policy.replace(COMPACT_POLICY, '').strip() + ' ' + COMPACT_POLICY
    messages = (dict(role='system', content=policy), dict(role='user', content=json.dumps(
        {'query': query, 'composed_cognition': state}, ensure_ascii=False, sort_keys=True)))
    receipt = dict(method='existing_capability_composition', operations=list(operations),
        failure=failure, extraction_provider_calls=0, answer_provider_calls=1,
        evidence_class='PROVIDER_FREE_INTEGRATION_NOT_EXTERNAL_EFFICACY',
        stage_preparation=[dict(p.preparation_receipt, answer_provider_calls=0, preparation_only=True) for p in stages],
        actual_final_messages=list(messages), longmemeval='SEALED_NOT_ACCESSED')
    return ComposedAnswer(plans, stages, messages, receipt)


def answer_composed(layer, query, requests, *, debug=False, **kwargs):
    prepared = prepare_composed_answer(layer, query, requests, **kwargs)
    answer = (layer.base_model(list(prepared.messages)) if callable(layer.base_model)
              else layer.base_model.complete(list(prepared.messages)))
    if not isinstance(answer, str):
        raise TypeError('base model adapter must return an answer string')
    return ComposedAnswerReceipt(answer, prepared) if debug else answer
