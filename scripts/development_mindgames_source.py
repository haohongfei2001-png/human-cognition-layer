"""Source-only MindGames preparation; no provider, runtime tuning or authority.

The public native premise/hypothesis remain byte-identical. Formal annotations,
labels, model predictions and difficulty are excluded from both arms' input.
"""
import hashlib
import json

SEED = 'HCL-MINDGAMES-SOURCE-20261001/'
LABELS = ('entailment', 'not_entailment')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def select_rows(rows, count=6):
    if type(count) is not int or count < 1 or not isinstance(rows, list) or len(rows) < count:
        raise ValueError('complete native rows and positive subset size required')
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or type(row.get('index')) is not int or row['index'] in seen:
            raise ValueError('unique native integer index required')
        seen.add(row['index'])
    return sorted(rows, key=lambda row: hashlib.sha256((SEED+str(row['index'])).encode()).hexdigest())[:count]


def prepare_source(row):
    if (not isinstance(row, dict) or type(row.get('index')) is not int
            or any(not isinstance(row.get(k), str) or not row[k].strip() for k in ('premise', 'hypothesis'))
            or row.get('label') not in LABELS):
        raise ValueError('intact native premise/hypothesis/label required')
    ordinary = {k: row[k] for k in ('premise', 'hypothesis')}
    return dict(native_index=row['index'], native_row_sha256=digest(row),
                native_label=row['label'], ordinary_input=ordinary,
                ordinary_input_sha256=digest(ordinary),
                answer_vocabulary=list(LABELS),
                source_sha256=hashlib.sha256(row['premise'].encode()).hexdigest(),
                hypothesis_sha256=hashlib.sha256(row['hypothesis'].encode()).hexdigest(),
                provider_calls=0, authorized_calls=0, authorized_spend_usd=0,
                live_execution_enabled=False, confirmation_qualified=False)
