"""Bounded ordinary questions select existing source preparation, no new mechanism."""
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import re

from hcl.v04.model import EventRecord
from .capabilities import CostClass, resolve_dependencies
from .cg04 import _TERM, _label
from .cg03 import NarrativePremise
from .context import ANSWER_POLICY, CognitionContext, event_row
from .layer import HCLCognitionLayer, PreparedAnswer, AnswerReceipt
from .router import CognitionRequest, CognitionPlan, PerspectiveMode
from .composition import prepare_composed_answer, ComposedAnswer, ComposedAnswerReceipt
from .compact import compact_cognition_context, COMPACT_POLICY

_QUESTIONS = tuple((kind, re.compile(pattern)) for kind, pattern in (
    ('preference', rf"Explain (?P<actor>{_TERM})'s preferences as (?P<role>{_TERM}) in (?P<context>{_TERM})[.?]?"),
    ('preference', rf'解释 (?P<actor>{_TERM}) 在 (?P<context>{_TERM}) 中的 (?P<role>{_TERM}) 角色偏好[。？]?'),
    ('belief_preference', rf"Explain (?P<actor>{_TERM})'s belief and preferences as (?P<role>{_TERM}) in (?P<context>{_TERM})[.?]?"),
    ('belief_preference', rf'解释 (?P<actor>{_TERM}) 在 (?P<context>{_TERM}) 中的信念与 (?P<role>{_TERM}) 角色偏好[。？]?'),
    ('concept_preference', rf"Explain (?P<actor>{_TERM})'s meaning of (?P<term>{_TERM}) for (?P<item>{_TERM}) and preferences as (?P<role>{_TERM}) in (?P<context>{_TERM})[.?]?"),
    ('concept_preference', rf'解释 (?P<actor>{_TERM}) 在 (?P<context>{_TERM}) 中对 (?P<item>{_TERM}) 的 (?P<term>{_TERM}) 词义与 (?P<role>{_TERM}) 角色偏好[。？]?'),
    ('belief_concept_preference', rf"Explain (?P<actor>{_TERM})'s belief, meaning of (?P<term>{_TERM}) for (?P<item>{_TERM}) and preferences as (?P<role>{_TERM}) in (?P<context>{_TERM})[.?]?"),
    ('belief_concept_preference', rf'解释 (?P<actor>{_TERM}) 在 (?P<context>{_TERM}) 中的信念、对 (?P<item>{_TERM}) 的 (?P<term>{_TERM}) 词义与 (?P<role>{_TERM}) 角色偏好[。？]?'),
    ('belief_responsibility', rf"Explain (?P<actor>{_TERM})'s belief and conditional responsibility[.?]?"),
    ('belief_responsibility', rf'解释 (?P<actor>{_TERM}) 的信念与条件责任依据[。？]?'),
    ('responsibility', rf"Explain (?P<actor>{_TERM})'s conditional responsibility[.?]?"),
    ('responsibility', rf'解释 (?P<actor>{_TERM}) 的条件责任依据[。？]?'),
    ('compare', rf"Compare (?P<actor>{_TERM})'s belief and meaning of (?P<term>{_TERM}) for (?P<item>{_TERM}) in (?P<context>{_TERM})[.?]?"),
    ('compare', rf'比较 (?P<actor>{_TERM}) 在 (?P<context>{_TERM}) 中对 (?P<item>{_TERM}) 是否 (?P<term>{_TERM}) 的信念与词义标准[。？]?'),
    ('belief', rf"Explain (?P<actor>{_TERM})'s belief[.?]?"),
    ('belief', rf'What does (?P<actor>{_TERM}) believe[.?]?'),
    ('belief', rf'解释 (?P<actor>{_TERM}) 的信念[。？]?'),
    ('concept', rf"Interpret (?P<actor>{_TERM})'s meaning of (?P<term>{_TERM}) for (?P<item>{_TERM}) in (?P<context>{_TERM})[.?]?"),
    ('concept', rf'解释 (?P<actor>{_TERM}) 在 (?P<context>{_TERM}) 中对 (?P<item>{_TERM}) 的 (?P<term>{_TERM}) 词义[。？]?'),
))


def _refusal(query, narrative, mode, reason, *, max_context_chars, preserve_reader_source=True):
    """Preserve only the authorized reader source; never guess a private view."""
    stamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
    event = EventRecord('question-source-' + hashlib.sha256(narrative.encode()).hexdigest()[:12],
        stamp, narrative, 'authorized-ordinary-question-source', stamp, metadata={'reader_only': True})
    context = CognitionContext(perspective_mode=mode.value,
        evidence=[event_row(event)] if preserve_reader_source and mode == PerspectiveMode.READER_ANALYSIS else [],
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


def _attach_source_scope(prepared, original_query, source_receipt, *, max_context_chars):
    payload = json.loads(prepared.messages[-1]['content'])
    key = 'composed_cognition' if isinstance(prepared, ComposedAnswer) else 'cognition_context'
    scope = dict(kind='SOURCE_STATEMENT_ORDER_ONLY', through_statement=source_receipt['through_statement'],
                 calendar_time='NOT_ESTABLISHED')
    payload['query'], payload['source_order_scope'] = original_query, scope
    context = prepared.context if isinstance(prepared, PreparedAnswer) else None
    extra = len(json.dumps(scope, ensure_ascii=False, sort_keys=True))
    exceeded = len(json.dumps(payload[key], ensure_ascii=False, sort_keys=True)) + extra > max_context_chars
    if exceeded:
        uncertainty = [dict(status='SYSTEM_INSUFFICIENT', reason='source-order context budget exceeded; narrow source')]
        if key == 'composed_cognition':
            payload[key] = dict(focal_actor=payload[key].get('focal_actor'),
                perspective_mode=payload[key]['perspective_mode'], operation_contexts=[], uncertainty=uncertainty)
        else:
            context = CognitionContext(perspective_mode=context.perspective_mode, uncertainty=uncertainty)
            payload[key] = compact_cognition_context(context.as_dict())
    messages = (dict(role='system', content=prepared.messages[0]['content'] +
        ' This snapshot includes only the explicitly selected source statements. '
        'Event timestamps encode statement order, not calendar time or verified receipt time. '
        'Later revisions and exposure are absent from this view; absent evidence stays unknown.'),
        dict(role='user', content=json.dumps(payload, ensure_ascii=False, sort_keys=True)))
    receipt = dict(prepared.preparation_receipt, source_selection=source_receipt,
        actual_final_messages=list(messages))
    if exceeded:
        receipt['failure'] = 'source_order_context_budget_exceeded'
    return replace(prepared, messages=messages, preparation_receipt=receipt,
                   **({'context': context} if isinstance(prepared, PreparedAnswer) else {}))


def prepare_person_context(layer, query, narrative, *, perspective_mode=PerspectiveMode.READER_ANALYSIS,
                           observer_actor=None, narrative_access=False, max_context_chars=48000,
                           as_of_statement=None, responsibility_premises=(), premise_scope='ALL_SOURCE'):
    """Ordinary question + ordinary source -> existing prepared cognition state.

    Question grammar selects operation/scenario, never correct mental states.
    Private views still require explicit, source-validated access preparation.
    """
    if not isinstance(layer, HCLCognitionLayer) or layer.intentions is not None or layer.affects is not None:
        raise ValueError('request-local cognition layer required')
    if not isinstance(query, str) or not query.strip() or len(query) > 16000:
        raise ValueError('bounded nonempty ordinary question required')
    if (not isinstance(perspective_mode, PerspectiveMode) or type(narrative_access) is not bool or
        type(max_context_chars) is not int or not 512 <= max_context_chars <= 64000):
        raise ValueError('explicit perspective, access flag and bounded context required')
    if observer_actor is not None:
        _label(observer_actor)
    if (perspective_mode == PerspectiveMode.OBSERVER_ABOUT_TARGET) != (observer_actor is not None):
        raise ValueError('observer perspective requires one explicit observer')
    if as_of_statement is not None and (type(as_of_statement) is not int or not 1 <= as_of_statement <= 24):
        raise ValueError('source statement scope must be an integer from1 to24')
    if (not isinstance(responsibility_premises, tuple) or len(responsibility_premises) > 3 or
        not all(isinstance(p, NarrativePremise) for p in responsibility_premises) or
        len({p.premise_id for p in responsibility_premises}) != len(responsibility_premises) or
        premise_scope not in ('ALL_SOURCE', 'FOCAL_EPISODE')):
        raise ValueError('bounded distinct caller normative premises and explicit source scope required')
    query = query.strip()
    # One ordinary entrypoint selects the already-certified integration surfaces.
    # Lazy imports prevent module initialization cycles; recursive inner questions
    # contain no outer source/event/contrast wrapper.
    delegated = dict(perspective_mode=perspective_mode, max_context_chars=max_context_chars,
        observer_actor=observer_actor, narrative_access=narrative_access,
        responsibility_premises=responsibility_premises, premise_scope=premise_scope)
    if as_of_statement is not None:
        delegated['as_of_statement'] = as_of_statement
    if query.startswith(('Across sources, ', '按来源变化，')):
        from .source_revision import prepare_source_revision
        return prepare_source_revision(layer, query, narrative, **delegated)
    if query.startswith(('Across events, ', '按事件变化，', 'At event ', '截至事件 ')):
        from .narrative_question import prepare_narrative_context
        return prepare_narrative_context(layer, query, narrative, **delegated)
    from .perspective_contrast import _QUESTIONS as contrast_questions, prepare_perspective_contrast
    candidate = (re.fullmatch(r'At statement ([1-9][0-9]?), (.+)', query) or
                 re.fullmatch(r'截至第 ([1-9][0-9]?) 条陈述，(.+)', query))
    contrast_query = candidate[2] if candidate else query
    if any(p.fullmatch(contrast_query) for p in contrast_questions):
        if responsibility_premises or premise_scope != 'ALL_SOURCE':
            raise ValueError('caller premise requires an explicit responsibility question')
        if perspective_mode != PerspectiveMode.READER_ANALYSIS and not narrative_access:
            return _refusal(query, '', perspective_mode,
                'private_question_requires_explicit_source_access_preparation',
                max_context_chars=max_context_chars, preserve_reader_source=False)
        return prepare_perspective_contrast(layer, query, narrative, observer_actor=observer_actor,
            as_of_statement=as_of_statement, max_context_chars=max_context_chars)
    if not isinstance(narrative, str) or not narrative.strip() or len(narrative) > 16000:
        raise ValueError('bounded nonempty ordinary source required')
    original_query, original_source = query, narrative
    prefix = (re.fullmatch(r'At statement ([1-9][0-9]?), (.+)', query.strip()) or
              re.fullmatch(r'截至第 ([1-9][0-9]?) 条陈述，(.+)', query.strip()))
    if prefix:
        index = int(prefix[1])
        if as_of_statement is not None and as_of_statement != index:
            return _refusal(query, narrative, perspective_mode, 'conflicting_source_order_scope',
                max_context_chars=max_context_chars, preserve_reader_source=False)
        as_of_statement, query = index, prefix[2]
        if query.startswith(('At statement', '截至第')):
            return _refusal(original_query, narrative, perspective_mode, 'nested_source_order_scope',
                max_context_chars=max_context_chars, preserve_reader_source=False)
    elif query.strip().startswith(('At statement', '截至第')):
        return _refusal(query, narrative, perspective_mode, 'unsupported_source_order_scope',
            max_context_chars=max_context_chars, preserve_reader_source=False)
    if as_of_statement is not None:
        lines = [line.strip() for line in narrative.splitlines() if line.strip()]
        if not 1 <= as_of_statement <= len(lines) <= 24 or any(len(line) > 2000 for line in lines):
            return _refusal(original_query, narrative, perspective_mode, 'source_order_scope_out_of_bounds',
                max_context_chars=max_context_chars, preserve_reader_source=False)
        narrative = '\n'.join(lines[:as_of_statement])
        selection = dict(method='EXPLICIT_AUTHORIZED_SOURCE_PREFIX', through_statement=as_of_statement,
            original_source_sha256=hashlib.sha256(original_source.encode()).hexdigest(),
            selected_source_sha256=hashlib.sha256(narrative.encode()).hexdigest(),
            source_statement_numbers=list(range(1, as_of_statement + 1)),
            calendar_time='NOT_ESTABLISHED', future_source_enters_preparation=False)
        # Re-enter once with the scoped source and plain operation question.
        # No semantic work has run on the original/future source.
        prepared = prepare_person_context(layer, query, narrative, perspective_mode=perspective_mode,
            observer_actor=observer_actor, narrative_access=narrative_access, max_context_chars=max_context_chars,
            responsibility_premises=responsibility_premises, premise_scope=premise_scope)
        return _attach_source_scope(prepared, original_query, selection, max_context_chars=max_context_chars)
    matches = [(kind, match.groupdict()) for kind, pattern in _QUESTIONS
               if (match := pattern.fullmatch(query.strip()))]
    if len(matches) != 1 or matches[0][1]['actor'] == 'Narrator':
        return _refusal(query, narrative, perspective_mode, 'unsupported_or_ambiguous_question_scope',
            max_context_chars=max_context_chars)
    kind, task = matches[0]
    responsibility = kind in ('responsibility', 'belief_responsibility')
    if not responsibility and (responsibility_premises or premise_scope != 'ALL_SOURCE'):
        raise ValueError('caller premise requires an explicit responsibility question')
    if responsibility and not responsibility_premises:
        return _refusal(query, narrative, perspective_mode, 'explicit_caller_normative_premise_required',
            max_context_chars=max_context_chars)
    if perspective_mode != PerspectiveMode.READER_ANALYSIS and not narrative_access:
        return _refusal(query, narrative, perspective_mode, 'private_question_requires_explicit_source_access_preparation',
            max_context_chars=max_context_chars)
    common = dict(target_actor=task['actor'], narrative=narrative, perspective_mode=perspective_mode,
        observer_actor=observer_actor, narrative_access=narrative_access,
        max_context_chars=max_context_chars, compact_context=True)
    requests = []
    if kind in ('belief', 'compare', 'belief_responsibility', 'belief_preference', 'belief_concept_preference'):
        requests.append(CognitionRequest(query, belief_analysis=True, **common))
    if kind in ('concept', 'compare', 'concept_preference', 'belief_concept_preference'):
        requests.append(CognitionRequest(query, concept_analysis=True,
            concept_context=task['context'], concept_term=task['term'], concept_item=task['item'], **common))
    if responsibility:
        requests.append(CognitionRequest(query, responsibility_analysis=True,
            responsibility_premises=responsibility_premises, responsibility_premise_scope=premise_scope, **common))
    if kind in ('preference', 'belief_preference', 'concept_preference', 'belief_concept_preference'):
        requests.append(CognitionRequest(query, preference_analysis=True,
            preference_role=task['role'], preference_context=task['context'], **common))
    prepared = (prepare_composed_answer(layer, query, tuple(requests), max_context_chars=max_context_chars,
        pool_sources=True, compare_belief_concepts=(kind == 'compare'))
        if len(requests) > 1 else layer.prepare(requests[0]))
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
