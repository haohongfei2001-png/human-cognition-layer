"""Lossless source-reference encoding of already projected cognition context."""
from copy import deepcopy
import json

ENCODING = 'hcl-source-reference-v1'
EMPTY_DEFAULTS = {
    'provenance': [], 'temporal_scope': {}, 'actors': [], 'perspective': {}, 'belief': [],
    'explicit_intention': [], 'affect_evidence': [], 'uncertainty': [], 'tool_results': [],
    'unsupported_inferences': [], 'explanations': [], 'open_unknown_candidate': {},
    'preparation': {}, 'social': {}}
COMPACT_POLICY = (
    'Encoding hcl-source-reference-v1: quote_from_source reads evidence[source_event_id].raw_text '
    '(strip trims whitespace). Checked from_case_input rows inherit same-ID case_input fields, '
    'minus without_case_fields, then apply listed overrides. Omitted empty-default fields are empty lists/dicts, not '
    'negative claims. provenance.common fields apply to every provenance.rows entry. References add no evidence or access.'
)


def _quote_refs(value, sources, *, expand):
    if isinstance(value, list):
        return [_quote_refs(v, sources, expand=expand) for v in value]
    if not isinstance(value, dict):
        return value
    row = {k: _quote_refs(v, sources, expand=expand) for k, v in value.items()}
    source = sources.get(row.get('source_event_id'))
    if expand and 'quote_from_source' in row:
        form = row.pop('quote_from_source')
        if source is None or form not in ('raw', 'strip') or 'quote' in row:
            raise ValueError('invalid compact source quote reference')
        row['quote'] = source if form == 'raw' else source.strip()
    elif not expand and isinstance(row.get('quote'), str) and source is not None:
        form = 'raw' if row['quote'] == source else 'strip' if row['quote'] == source.strip() else None
        if form:
            row.pop('quote')
            row['quote_from_source'] = form
    return row


def compact_cognition_context(context):
    """No selection or truncation: encode only already visible, exact duplicates."""
    row = deepcopy(context)
    if 'encoding' in row:
        raise ValueError('context already has an encoding')
    sources = {e['event_id']: e['raw_text'] for e in row.get('evidence', [])}
    for slot in ('responsibility', 'preferences', 'concepts'):
        if slot in row:
            row[slot] = _quote_refs(row[slot], sources, expand=False)
    for slot, base_key, checked_key, identifier in (
        ('preferences', 'statements', 'statements', 'statement_id'),
        ('concepts', 'definitions', 'readings', 'definition_id'),
        ('responsibility', 'premises', 'premise_assessments', 'premise_id')):
        section = row.get(slot, {})
        bases = {r[identifier]: r for r in section.get('case_input', {}).get(base_key, [])}
        checked = section.get('checked', {})
        if checked_key not in checked:
            continue
        output = []
        for item in checked[checked_key]:
            base = bases.get(item.get(identifier))
            if base is None:
                output.append(item)
                continue
            delta = {k: v for k, v in item.items() if k == identifier or k not in base or
                json.dumps(v, sort_keys=True) != json.dumps(base[k], sort_keys=True)}
            removed = [k for k in base if k not in item]
            if removed:
                delta['without_case_fields'] = removed
            delta['from_case_input'] = True
            output.append(delta)
        checked[checked_key] = output
    provenance = row.get('provenance', [])
    if len(provenance) > 1:
        common = {k: v for k, v in provenance[0].items() if all(
            k in p and json.dumps(p[k], sort_keys=True) == json.dumps(v, sort_keys=True)
            for p in provenance[1:])}
        encoded = {'common': common, 'rows': [{k: v for k, v in p.items() if k not in common}
            for p in provenance]}
        if len(json.dumps(encoded)) < len(json.dumps(provenance)):
            row['provenance'] = encoded
    for key, value in EMPTY_DEFAULTS.items():
        if key in row and row[key] == value:
            del row[key]
    row['encoding'] = ENCODING
    # Encoder must never be a semantic rewrite, including source redactions.
    if expand_cognition_context(row) != context:
        raise ValueError('context reference encoding failed lossless round trip')
    return row


def expand_cognition_context(context):
    row = deepcopy(context)
    if row.pop('encoding', None) != ENCODING:
        raise ValueError('unsupported context encoding')
    provenance = row.get('provenance')
    if isinstance(provenance, dict):
        if set(provenance) != {'common', 'rows'} or not isinstance(provenance['common'], dict) or not isinstance(provenance['rows'], list):
            raise ValueError('invalid compact provenance table')
        row['provenance'] = [dict(provenance['common'], **p) for p in provenance['rows']]
    for key, value in EMPTY_DEFAULTS.items():
        row.setdefault(key, deepcopy(value))
    for slot, base_key, checked_key, identifier in (
        ('preferences', 'statements', 'statements', 'statement_id'),
        ('concepts', 'definitions', 'readings', 'definition_id'),
        ('responsibility', 'premises', 'premise_assessments', 'premise_id')):
        section = row.get(slot, {})
        bases = {r[identifier]: r for r in section.get('case_input', {}).get(base_key, [])}
        for item in section.get('checked', {}).get(checked_key, []):
            if 'from_case_input' not in item:
                continue
            if item.pop('from_case_input') is not True or item.get(identifier) not in bases:
                raise ValueError('invalid compact checked-state reference')
            removed = item.pop('without_case_fields', [])
            if not isinstance(removed, list) or any(k not in bases[item[identifier]] for k in removed):
                raise ValueError('invalid compact case-field exclusion')
            merged = dict(bases[item[identifier]])
            for key in removed:
                del merged[key]
            merged.update(item)
            item.clear()
            item.update(merged)
    sources = {e['event_id']: e['raw_text'] for e in row.get('evidence', [])}
    for slot in ('responsibility', 'preferences', 'concepts'):
        if slot in row:
            row[slot] = _quote_refs(row[slot], sources, expand=True)
    return row
