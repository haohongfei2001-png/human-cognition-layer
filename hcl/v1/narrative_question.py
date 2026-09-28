"""Explicit event sections select existing cognition composition over a short story."""
from dataclasses import replace
import hashlib
import json
import re

from .cg04 import _TERM
from .composition import ComposedAnswer
from .person_question import prepare_person_context, _QUESTIONS, _refusal
from .router import PerspectiveMode
from .source_revision import (AuthorizedSourceRecord, prepare_source_revision, _bindings, _conflicts)

_EVENT = re.compile(rf'(?:Event (?P<english>{_TERM}):|事件 (?P<chinese>{_TERM})：)')
NARRATIVE_POLICY = (
    'Event labels are explicit sections of one authorized ordinary source, not '
    'independent sources, calendar times or verified receipts. Each snapshot '
    'source ID names its event section in that source. The question selects only '
    'the requested existing operations and the selected event prefix. Later '
    'sections cannot rewrite earlier supported views; only explicit local '
    'revisions affect their named actor/context/item/term/factor. Keep belief, '
    'meaning and preferences distinct; an action never supplies motive/emotion, '
    'exposure never supplies acceptance, and a caller rule never supplies moral truth.'
)


def prepare_narrative_context(layer, query, narrative, *, perspective_mode=PerspectiveMode.READER_ANALYSIS,
                              max_context_chars=64000, **kwargs):
    """Across events / At event X + ordinary compound question, zero extraction."""
    if (not isinstance(query, str) or not query.strip() or len(query) > 16000 or
        not isinstance(narrative, str) or not narrative.strip() or len(narrative) > 16000 or
        not isinstance(perspective_mode, PerspectiveMode) or
        type(max_context_chars) is not int or not 512 <= max_context_chars <= 64000):
        raise ValueError('bounded ordinary event source/question/view required')
    def refuse(reason):
        return _refusal(query, '', perspective_mode, reason, max_context_chars=max_context_chars,
                        preserve_reader_source=False)
    if 'as_of_statement' in kwargs:
        return refuse('event_and_statement_scope_must_not_mix')
    through = None
    if query.startswith(('Across events, ', '按事件变化，')):
        inner = query.removeprefix('Across events, ').removeprefix('按事件变化，')
    elif (m := re.fullmatch(rf'At event ({_TERM}), (.+)', query)) or (
            m := re.fullmatch(rf'截至事件 ({_TERM})，(.+)', query)):
        through, inner = m[1], m[2]
    else:
        return refuse('explicit_event_question_scope_required')
    matches = [(kind, m) for kind, p in _QUESTIONS if (m := p.fullmatch(inner.strip()))]
    if len(matches) != 1 or matches[0][0] not in (
            'compare', 'belief_responsibility', 'belief_preference',
            'concept_preference', 'belief_concept_preference'):
        return refuse('event_question_requires_explicit_existing_composition')
    groups, names, current = [], set(), None
    lines = [line.strip() for line in narrative.splitlines() if line.strip()]
    for line in lines:
        header = _EVENT.fullmatch(line)
        if header:
            name = header['english'] or header['chinese']
            if name in names or len(names) == 4:
                return refuse('ambiguous_or_unbounded_event_identity')
            current = dict(event_id=name, lines=[])
            groups.append(current)
            names.add(name)
        elif current is None or line.startswith(('Event ', '事件 ')):
            return refuse('missing_or_invalid_explicit_event_boundary')
        else:
            current['lines'].append(line)
    if (not 2 <= len(groups) <= 4 or any(not g['lines'] for g in groups) or
        sum(len(g['lines']) for g in groups) > 24 or any(len(line) > 2000 for line in lines)):
        return refuse('ordinary_event_source_bounds')
    if through is not None:
        if through not in names:
            return refuse('unknown_selected_event')
        groups = groups[:next(i for i, g in enumerate(groups) if g['event_id'] == through) + 1]
    records = tuple(AuthorizedSourceRecord(g['event_id'], '\n'.join(g['lines']), 'CALLER_AUTHORIZED',
        groups[i - 1]['event_id'] if i else None) for i, g in enumerate(groups))
    if len(records) > 1:
        prepared = prepare_source_revision(layer, 'Across sources, ' + inner, records,
            perspective_mode=perspective_mode, max_context_chars=max_context_chars, **kwargs)
        payload = json.loads(prepared.messages[-1]['content'])
        if 'source_revision_cognition' not in payload:
            return prepared
        state = payload['source_revision_cognition']
    else:
        stage = prepare_person_context(layer, inner, records[0].text, perspective_mode=perspective_mode,
            max_context_chars=max_context_chars, **kwargs)
        payload = json.loads(stage.messages[-1]['content'])
        key = 'composed_cognition' if 'composed_cognition' in payload else 'cognition_context'
        positions = [dict(source_id=records[0].source_id, statement_number=i, text=line)
            for i, line in enumerate(groups[0]['lines'], 1)]
        binding = _bindings(stage, positions)
        state = dict(source_relation='ORDERED_SOURCE_PATH', calendar_time='NOT_ESTABLISHED',
            verified_receipt_time='NOT_ESTABLISHED', snapshots=[dict(
                through_source_id=records[0].source_id, source_path=[records[0].source_id],
                state_kind=key, state=payload[key], source_bindings=binding,
                source_conflicts=_conflicts(stage, binding))])
        prepared = stage
    selection = dict(selected_event_ids=[g['event_id'] for g in groups], through_event=through,
        source_kind='ONE_AUTHORIZED_ORDINARY_EVENT_NARRATIVE', calendar_time='NOT_ESTABLISHED',
        operations_selected_by='EXPLICIT_ORDINARY_COMPOUND_QUESTION')
    state = dict(state, event_selection=selection)
    failure = prepared.preparation_receipt.get('failure')
    if len(json.dumps(state, ensure_ascii=False, sort_keys=True)) > max_context_chars:
        failure = 'narrative_event_context_budget_exceeded'
        state = dict(snapshots=[], uncertainty=[dict(status='SYSTEM_INSUFFICIENT', reason=failure)])
    messages = (dict(role='system', content=prepared.messages[0]['content'] + ' ' + NARRATIVE_POLICY),
        dict(role='user', content=json.dumps(dict(query=query, narrative_cognition=state),
                                             ensure_ascii=False, sort_keys=True)))
    receipt = dict(prepared.preparation_receipt, method='existing_capability_ordinary_event_composition',
        event_selection=selection, original_source_sha256=hashlib.sha256(narrative.encode()).hexdigest(),
        selected_source_sha256=hashlib.sha256('\n'.join(r.text for r in records).encode()).hexdigest(),
        failure=failure, actual_final_messages=list(messages), extraction_provider_calls=0,
        answer_provider_calls=1, longmemeval='SEALED_NOT_ACCESSED')
    return replace(prepared, messages=messages, preparation_receipt=receipt)


def answer_narrative_context(layer, query, narrative, *, debug=False, **kwargs):
    from .composition import ComposedAnswerReceipt
    from .layer import AnswerReceipt
    prepared = prepare_narrative_context(layer, query, narrative, **kwargs)
    answer = (layer.base_model(list(prepared.messages)) if callable(layer.base_model)
              else layer.base_model.complete(list(prepared.messages)))
    if not isinstance(answer, str):
        raise TypeError('base model adapter must return an answer string')
    receipt = ComposedAnswerReceipt if isinstance(prepared, ComposedAnswer) else AnswerReceipt
    return receipt(answer, prepared) if debug else answer
