"""Lossless request-local storage pool, with operation access links preserved."""
from collections import Counter
from copy import deepcopy
import hashlib
import json

ENCODING = 'hcl-composed-source-pool-v1'
ENCODING_WITH_PREPARATION = 'hcl-composed-source-pool-v2'
PREPARATION_POLICY = (
    'preparation_defaults restores per-stage zero semantic-preparer/extraction calls and extraction cost, zero answer calls, '
    'null answer cost and DEFERRED_TO_SINGLE_COMPOSED_ANSWER. These are not aggregate usage.'
)
_PREPARATION_DEFAULTS = dict(semantic_preparer_calls=0, extraction_provider_calls=0,
    answer_provider_calls=0, extraction_spend_usd=0, answer_spend_usd=None,
    answer_execution='DEFERRED_TO_SINGLE_COMPOSED_ANSWER')
POOL_POLICY = (
    'source_record_ref reads actor_id/raw_text/valid_time/recorded_at from source_records. '
    'Keep each row event_id/source_id and each operation evidence list. Pool sharing is '
    'storage only, never shared access, belief, agreement or cross-operation support.'
)
_FIELDS = ('actor_id', 'raw_text', 'valid_time', 'recorded_at')


def _identity(event):
    return json.dumps({k: event[k] for k in _FIELDS}, ensure_ascii=False, sort_keys=True)


def pool_composed_sources(state, *, preparation_defaults=True):
    if type(preparation_defaults) is not bool:
        raise ValueError('explicit preparation encoding flag required')
    row = deepcopy(state)
    if 'source_pool_encoding' in row or 'source_records' in row:
        raise ValueError('composition already contains a source pool')
    events = [event for op in row['operation_contexts'] for event in op['cognition_context'].get('evidence', [])]
    counts = Counter(_identity(e) for e in events)
    pool = {}
    for event in events:
        identity = _identity(event)
        if counts[identity] < 2:
            continue
        reference = 'source-' + hashlib.sha256(identity.encode()).hexdigest()[:16]
        template = {k: event.pop(k) for k in _FIELDS}
        if reference in pool and pool[reference] != template:
            raise ValueError('source pool reference collision')
        pool[reference] = template
        event['source_record_ref'] = reference
    if not pool:
        return row
    row['source_records'] = pool
    row['source_pool_encoding'] = ENCODING
    if preparation_defaults:
        candidate = deepcopy(row)
        eligible = 0
        for op in candidate['operation_contexts']:
            context = op['cognition_context']
            prep = context.get('preparation', {})
            if all(k in prep and type(prep[k]) is type(v) and prep[k] == v for k, v in _PREPARATION_DEFAULTS.items()):
                for k in _PREPARATION_DEFAULTS:
                    prep.pop(k)
                context['preparation_defaults'] = True
                eligible += 1
        candidate['source_pool_encoding'] = ENCODING_WITH_PREPARATION
        size = lambda value: len(json.dumps(value, ensure_ascii=False, sort_keys=True))
        # Include decoder policy overhead; leave small/non-duplicate inputs literal.
        if eligible >= 2 and size(candidate) + len(PREPARATION_POLICY) < size(row):
            row = candidate
    if json.dumps(expand_composed_sources(row), sort_keys=True) != json.dumps(state, sort_keys=True):
        raise ValueError('composition pool failed lossless round trip')
    return row


def expand_composed_sources(state):
    row = deepcopy(state)
    encoding = row.pop('source_pool_encoding', None)
    if encoding is None:
        if 'source_records' in row or any('preparation_defaults' in op['cognition_context'] for op in row['operation_contexts']):
            raise ValueError('unmarked composition source pool')
        return row
    if encoding not in (ENCODING, ENCODING_WITH_PREPARATION):
        raise ValueError('unsupported composition source pool')
    pool = row.pop('source_records')
    if not isinstance(pool, dict):
        raise ValueError('bounded composition source map required')
    for op in row['operation_contexts']:
        context = op['cognition_context']
        has_marker = 'preparation_defaults' in context
        marker = context.pop('preparation_defaults', None)
        if has_marker:
            prep = context.get('preparation')
            if (encoding != ENCODING_WITH_PREPARATION or marker is not True or not isinstance(prep, dict) or
                any(k in prep for k in _PREPARATION_DEFAULTS)):
                raise ValueError('invalid per-stage preparation defaults')
            prep.update(_PREPARATION_DEFAULTS)
        for event in op['cognition_context'].get('evidence', []):
            reference = event.pop('source_record_ref', None)
            if reference is None:
                continue
            template = pool.get(reference)
            if not isinstance(template, dict) or set(template) != set(_FIELDS) or any(k in event for k in _FIELDS):
                raise ValueError('invalid composed source reference')
            expected = 'source-' + hashlib.sha256(_identity(template).encode()).hexdigest()[:16]
            if reference != expected:
                raise ValueError('composed source pool content drift')
            event.update(template)
    return row
