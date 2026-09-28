"""Bounded ordinary questions select existing source preparation, no new mechanism."""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import re

from hcl.v04.model import EventRecord
from .capabilities import CostClass, resolve_dependencies
from .cg04 import _TERM, _label
from .context import ANSWER_POLICY, CognitionContext, event_row
from .layer import HCLCognitionLayer, PreparedAnswer, AnswerReceipt
from .router import CognitionRequest, CognitionPlan, PerspectiveMode
from .composition import prepare_composed_answer, ComposedAnswer, ComposedAnswerReceipt
from .compact import compact_cognition_context, COMPACT_POLICY

_QUESTIONS = tuple((kind, re.compile(pattern)) for kind, pattern in (
    ('compare', rf"Compare (?P<actor>{_TERM})'s belief and meaning of (?P<term>{_TERM}) for (?P<item>{_TERM}) in (?P<context>{_TERM})[.?]?"),
    ('compare', rf'比较 (?P<actor>{_TERM}) 在 (?P<context>{_TERM}) 中对 (?P<item>{_TERM}) 是否 (?P<term>{_TERM}) 的信念与词义标准[。？]?'),
    ('belief', rf"Explain (?P<actor>{_TERM})'s belief[.?]?"),
    ('belief', rf'What does (?P<actor>{_TERM}) believe[.?]?'),
    ('belief', rf'解释 (?P<actor>{_TERM}) 的信念[。？]?'),
    ('concept', rf"Interpret (?P<actor>{_TERM})'s meaning of (?P<term>{_TERM}) for (?P<item>{_TERM}) in (?P<context>{_TERM})[.?]?"),
))


def _refusal(query, narrative, mode, reason, *, max_context_chars):
    """Preserve only the authorized reader source; never guess a private view."""
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    event = EventRecord('question-source-' + hashlib.sha256(narrative.encode()).hexdigest()[:12],
        stamp, narrative, 'authorized-ordinary-question-source', stamp, metadata={'reader_only': True})
    context = CognitionContext(perspective_mode=mode.value,
        evidence=[event_row(event)] if mode == PerspectiveMode.READER_ANALYSIS else [],
        uncertainty=[dict(status='SYSTEM_INSUFFICIENT', reason=reason)],
        preparation=dict(method='bounded_ordinary_question_refusal', failure=reason,
                         extraction_provider_calls=0, answer_provider_calls=1))
    transmitted = compact_cognition_context(context.as_dict())
    if len(json.dumps(transmitted, ensure_ascii=False, sort_keys=True)) > max_context_chars:
        context.evidence = []
        context.uncertainty.append(dict(status='SYSTEM_INSUFFICIENT', reason='context budget exceeded; narrow source'))
        transmitted = compact_cognition_context(context.as_dict())
        if len(json.dumps(transmitted, ensure_ascii=False, sort_keys=True)) > max_context_chars:
            # The full audit stays in the receipt; don't let refusal metadata
            # exceed the same transmitted-state budget as a successful path.
            context.preparation = {}
            transmitted = compact_cognition_context(context.as_dict())
    plan = CognitionPlan(True, resolve_dependencies(('evidence', 'uncertainty')), (), (),
        'evidence_bounded', {'uncertainty': reason}, CostClass.LOW,
        max_context_chars=max_context_chars, perspective_mode=mode)
    messages = (dict(role='system', content=ANSWER_POLICY + ' ' + COMPACT_POLICY + ' Structured person analysis was not grounded; '
        'use authorized reader text cautiously and say when the requested analysis is unsupported.'),
        dict(role='user', content=json.dumps(dict(query=query, cognition_context=transmitted), ensure_ascii=False, sort_keys=True)))
    return PreparedAnswer(plan, context, messages, dict(method='bounded_ordinary_question_refusal',
        failure=reason, extraction_provider_calls=0, answer_provider_calls=1,
        actual_final_messages=list(messages), longmemeval='SEALED_NOT_ACCESSED'))


def prepare_person_context(layer, query, narrative, *, perspective_mode=PerspectiveMode.READER_ANALYSIS,
                           observer_actor=None, narrative_access=False, max_context_chars=48000):
    """Ordinary question + ordinary source -> existing prepared cognition state.

    Question grammar selects operation/scenario, never correct mental states.
    Private views still require explicit, source-validated access preparation.
    """
    if not isinstance(layer, HCLCognitionLayer) or layer.intentions is not None or layer.affects is not None:
        raise ValueError('request-local cognition layer required')
    if not isinstance(query, str) or not query.strip() or len(query) > 16000:
        raise ValueError('bounded nonempty ordinary question required')
    if not isinstance(narrative, str) or not narrative.strip() or len(narrative) > 16000:
        raise ValueError('bounded nonempty ordinary source required')
    if (not isinstance(perspective_mode, PerspectiveMode) or type(narrative_access) is not bool or
        type(max_context_chars) is not int or not 512 <= max_context_chars <= 64000):
        raise ValueError('explicit perspective, access flag and bounded context required')
    if observer_actor is not None:
        _label(observer_actor)
    if (perspective_mode == PerspectiveMode.OBSERVER_ABOUT_TARGET) != (observer_actor is not None):
        raise ValueError('observer perspective requires one explicit observer')
    matches = [(kind, match.groupdict()) for kind, pattern in _QUESTIONS
               if (match := pattern.fullmatch(query.strip()))]
    if len(matches) != 1 or matches[0][1]['actor'] == 'Narrator':
        return _refusal(query, narrative, perspective_mode, 'unsupported_or_ambiguous_question_scope',
            max_context_chars=max_context_chars)
    kind, task = matches[0]
    if perspective_mode != PerspectiveMode.READER_ANALYSIS and not narrative_access:
        return _refusal(query, narrative, perspective_mode, 'private_question_requires_explicit_source_access_preparation',
            max_context_chars=max_context_chars)
    common = dict(target_actor=task['actor'], narrative=narrative, perspective_mode=perspective_mode,
        observer_actor=observer_actor, narrative_access=narrative_access,
        max_context_chars=max_context_chars, compact_context=True)
    requests = []
    if kind in ('belief', 'compare'):
        requests.append(CognitionRequest(query, belief_analysis=True, **common))
    if kind in ('concept', 'compare'):
        requests.append(CognitionRequest(query, concept_analysis=True,
            concept_context=task['context'], concept_term=task['term'], concept_item=task['item'], **common))
    prepared = (prepare_composed_answer(layer, query, tuple(requests), max_context_chars=max_context_chars,
        pool_sources=True, compare_belief_concepts=True) if kind == 'compare' else layer.prepare(requests[0]))
    receipt = dict(prepared.preparation_receipt, question_entrypoint=dict(method='bounded_explicit_task_scope',
        operation=kind, scope=task, source_of_mental_state='ORDINARY_SOURCE_NOT_QUESTION_OR_CALLER_GOLD'),
        actual_final_messages=list(prepared.messages))
    return replace(prepared, preparation_receipt=receipt)


def answer_person_context(layer, query, narrative, *, debug=False, **kwargs):
    prepared = prepare_person_context(layer, query, narrative, **kwargs)
    answer = (layer.base_model(list(prepared.messages)) if callable(layer.base_model)
        else layer.base_model.complete(list(prepared.messages)))
    if not isinstance(answer, str):
        raise TypeError('base model adapter must return an answer string')
    receipt = ComposedAnswerReceipt if isinstance(prepared, ComposedAnswer) else AnswerReceipt
    return receipt(answer, prepared) if debug else answer
