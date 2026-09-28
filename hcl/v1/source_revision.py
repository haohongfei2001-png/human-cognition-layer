"""Explicit authorized source paths reuse existing ordinary preparation locally."""
from dataclasses import dataclass
import hashlib
import json
import re

from .belief_preparation import decode_belief_source
from .compact import expand_cognition_context
from .composition import ComposedAnswer, ComposedAnswerReceipt
from .person_question import prepare_person_context, _refusal, _QUESTIONS
from .router import PerspectiveMode
from .source_pool import expand_composed_sources

SOURCE_REVISION_POLICY = (
    'Each source snapshot below is a separate request-local view over its explicit '
    'authorized source path. Source order is not calendar time or verified receipt '
    'time. Later source statements/exposure never backfill an earlier snapshot. '
    'Incomparable source branches have no merged winner. source_conflicts record '
    'contradictory visible assertions without explicit revision; do not resolve '
    'them from a last assertion, average them or declare a private belief. '
    'Keep each actor/context/item/term/factor revision and source provenance local. '
    'Conditional responsibility remains dependent on the explicit caller premise. '
    'Missing or unsupported source analysis remains unknown.'
)


@dataclass(frozen=True)
class AuthorizedSourceRecord:
    source_id: str
    text: str
    authority: str | None = None
    after_source_id: str | None = None


def _contexts(prepared):
    payload = json.loads(prepared.messages[-1]['content'])
    if 'composed_cognition' in payload:
        state = expand_composed_sources(payload['composed_cognition'])
        return [(r['operation'], expand_cognition_context(r['cognition_context']))
                for r in state['operation_contexts']]
    return [('single', expand_cognition_context(payload['cognition_context']))]


def _bindings(prepared, positions):
    rows = []
    for operation, context in _contexts(prepared):
        for event in context.get('evidence', []):
            # Existing bounded ordinary parsers preserve the line index in IDs.
            suffix = re.search(r'-(\d+)$', event['event_id'])
            indices = ([int(suffix[1])] if suffix and 1 <= int(suffix[1]) <= len(positions) and
                       positions[int(suffix[1]) - 1]['text'] == event['raw_text'] else
                       [i for i, p in enumerate(positions, 1) if p['text'] == event['raw_text']])
            if not indices and event['raw_text'] == '\n'.join(p['text'] for p in positions):
                indices = list(range(1, len(positions) + 1))  # authorized reader refusal only
            if not indices:
                raise ValueError('prepared_source_binding_missing')
            rows.append(dict(operation=operation, source_event_id=event['event_id'],
                source_statements=[dict(source_id=positions[i - 1]['source_id'],
                    statement_number=positions[i - 1]['statement_number']) for i in indices]))
    return rows


def _conflicts(prepared, bindings):
    """Expose conflicting visible source assertions; never rewrite retained state."""
    found = {}
    by_event = {(r['operation'], r['source_event_id']): r['source_statements'] for r in bindings}
    for operation, context in _contexts(prepared):
        keys = {(b['subject_agent_id'], *b['proposition_key'].split('/')) for b in context.get('belief', [])}
        for event in context.get('evidence', []):
            try:
                row = decode_belief_source(event['raw_text'])
            except ValueError:
                continue
            if row['evidence_kind'] != 'SELF_REPORT':
                continue
            key = (row['subject'], row['context'], row['item'], row['term'])
            if key not in keys:
                continue
            if row.get('old_item'):
                found.pop((row['subject'], row['context'], row['old_item'], row['old_term']), None)
                found.pop(key, None)
            stance = row.get('stance', 'believe')
            found.setdefault(key, {})[event['event_id']] = dict(
                source_event_id=event['event_id'], stance=stance,
                source_statements=by_event[(operation, event['event_id'])])
    conflicts = []
    for key, witnesses in found.items():
        values = list(witnesses.values())
        if ({v['stance'] for v in values} >= {'believe', 'do not believe'} and
            len({s['source_id'] for v in values for s in v['source_statements']}) > 1):
            conflicts.append(dict(actor_id=key[0], context=key[1], item=key[2], term=key[3],
                status='UNRESOLVED_CONTRADICTORY_SOURCE_ASSERTIONS', witnesses=values))
    return conflicts


def prepare_source_revision(layer, query, sources, *, perspective_mode=PerspectiveMode.READER_ANALYSIS,
                            max_context_chars=64000, **kwargs):
    """An ordinary question compares 2–4 explicit source snapshots, no provider work.

    CALLER_AUTHORIZED grants this request access to text, not factual reliability.
    after_source_id declares a source path only. Branches never merge implicitly.
    """
    if (not isinstance(query, str) or not query.strip() or len(query) > 16000 or
        not isinstance(perspective_mode, PerspectiveMode) or
        type(max_context_chars) is not int or not 512 <= max_context_chars <= 64000):
        raise ValueError('bounded ordinary source-revision question and view required')
    def refuse(reason):
        return _refusal(query, '', perspective_mode, reason, max_context_chars=max_context_chars,
                        preserve_reader_source=False)
    if (not isinstance(sources, tuple) or not 2 <= len(sources) <= 4 or
        not all(isinstance(s, AuthorizedSourceRecord) for s in sources)):
        return refuse('bounded_explicit_source_records_required')
    paths, by_id, line_count, size = {}, {}, 0, 0
    for s in sources:
        if (not isinstance(s.source_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', s.source_id) or
            s.source_id in by_id or s.authority != 'CALLER_AUTHORIZED' or
            not isinstance(s.text, str) or not s.text.strip() or
            (s.after_source_id is not None and
             (not isinstance(s.after_source_id, str) or s.after_source_id not in by_id))):
            return refuse('invalid_or_missing_source_authority_identity_order')
        lines = [line.strip() for line in s.text.splitlines() if line.strip()]
        line_count += len(lines)
        size += len(s.text)
        if line_count > 24 or size > 16000 or any(len(line) > 2000 for line in lines):
            return refuse('source_record_bounds')
        by_id[s.source_id] = s
        paths[s.source_id] = (paths[s.after_source_id] if s.after_source_id is not None else ()) + (s.source_id,)
    if 'as_of_statement' in kwargs:
        return refuse('source_record_and_statement_scope_must_not_mix')
    if query.startswith('Across sources, '):
        inner = query.removeprefix('Across sources, ')
    elif query.startswith('按来源变化，'):
        inner = query.removeprefix('按来源变化，')
    else:
        return refuse('explicit_source_revision_question_required')
    if inner.startswith(('At statement', '截至第', 'Across sources', '按来源变化')):
        return refuse('nested_source_revision_scope')
    if not any(p.fullmatch(inner.strip()) for _, p in _QUESTIONS):
        return refuse('unsupported_or_mixed_source_revision_task')
    stages, snapshots = [], []
    for source in sources:
        path = paths[source.source_id]
        positions = [dict(source_id=sid, statement_number=i, text=line)
            for sid in path for i, line in enumerate(
                (line.strip() for line in by_id[sid].text.splitlines() if line.strip()), 1)]
        narrative = '\n'.join(p['text'] for p in positions)
        prepared = prepare_person_context(layer, inner, narrative, perspective_mode=perspective_mode,
            max_context_chars=max_context_chars, **kwargs)
        # Each snapshot starts fresh; no later record is passed to preparation.
        try:
            bindings = _bindings(prepared, positions)
        except ValueError:
            return refuse('prepared_source_binding_missing')
        payload = json.loads(prepared.messages[-1]['content'])
        key = 'composed_cognition' if 'composed_cognition' in payload else 'cognition_context'
        snapshots.append(dict(through_source_id=source.source_id, source_path=list(path),
            source_order='EXPLICIT_SOURCE_PATH_NOT_CALENDAR_OR_VERIFIED_RECEIPT',
            state_kind=key, state=payload[key], source_bindings=bindings,
            source_conflicts=_conflicts(prepared, bindings)))
        stages.append(prepared)
    leaves = [sid for sid in by_id if not any(s.after_source_id == sid for s in sources)]
    state = dict(source_relation='ORDERED_SOURCE_PATH' if len(leaves) == 1 else 'INCOMPARABLE_SOURCE_BRANCHES_NO_MERGED_STATE',
        snapshots=snapshots, calendar_time='NOT_ESTABLISHED', verified_receipt_time='NOT_ESTABLISHED')
    failure = None
    if len(json.dumps(state, ensure_ascii=False, sort_keys=True)) > max_context_chars:
        failure = 'source_revision_context_budget_exceeded'
        state = dict(snapshots=[], uncertainty=[dict(status='SYSTEM_INSUFFICIENT', reason=failure)])
    policies = tuple(dict.fromkeys(s.messages[0]['content'] for s in stages))
    messages = (dict(role='system', content=' '.join(policies) + ' ' + SOURCE_REVISION_POLICY),
        dict(role='user', content=json.dumps(dict(query=query, source_revision_cognition=state),
                                             ensure_ascii=False, sort_keys=True)))
    receipt = dict(method='existing_capability_authorized_source_revision', failure=failure,
        source_records=[dict(source_id=s.source_id, after_source_id=s.after_source_id, authority=s.authority,
            text_sha256=hashlib.sha256(s.text.encode()).hexdigest()) for s in sources],
        extraction_provider_calls=0, answer_provider_calls=1, provider_calls_executed=0,
        evidence_class='PROVIDER_FREE_INTEGRATION_NOT_EXTERNAL_EFFICACY',
        stage_preparation=[dict(s.preparation_receipt, answer_provider_calls=0,
            preparation_only=True) for s in stages], actual_final_messages=list(messages),
        longmemeval='SEALED_NOT_ACCESSED')
    return ComposedAnswer(tuple(s.plan if hasattr(s, 'plan') else s.plans for s in stages),
                          tuple(stages), messages, receipt)


def answer_source_revision(layer, query, sources, *, debug=False, **kwargs):
    prepared = prepare_source_revision(layer, query, sources, **kwargs)
    answer = (layer.base_model(list(prepared.messages)) if callable(layer.base_model)
              else layer.base_model.complete(list(prepared.messages)))
    if not isinstance(answer, str):
        raise TypeError('base model adapter must return an answer string')
    return ComposedAnswerReceipt(answer, prepared) if debug else answer
