"""Lossless request-local storage pool, with operation access links preserved."""
from collections import Counter
from copy import deepcopy
import hashlib
import json

ENCODING = 'hcl-composed-source-pool-v1'
POOL_POLICY = (
    'source_record_ref reads actor_id/raw_text/valid_time/recorded_at from source_records. '
    'Keep each row event_id/source_id and each operation evidence list. Pool sharing is '
    'storage only, never shared access, belief, agreement or cross-operation support.'
)
_FIELDS = ('actor_id', 'raw_text', 'valid_time', 'recorded_at')


def _identity(event):
    return json.dumps({k: event[k] for k in _FIELDS}, ensure_ascii=False, sort_keys=True)


def pool_composed_sources(state):
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
    if expand_composed_sources(row) != state:
        raise ValueError('composition pool failed lossless round trip')
    return row


def expand_composed_sources(state):
    row = deepcopy(state)
    encoding = row.pop('source_pool_encoding', None)
    if encoding is None:
        if 'source_records' in row:
            raise ValueError('unmarked composition source pool')
        return row
    if encoding != ENCODING:
        raise ValueError('unsupported composition source pool')
    pool = row.pop('source_records')
    if not isinstance(pool, dict):
        raise ValueError('bounded composition source map required')
    for op in row['operation_contexts']:
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
