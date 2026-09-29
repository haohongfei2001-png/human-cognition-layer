"""Strict G workspace boundary for the provider-free I02 v3 comparator.

Historical v1/v2 calibration runners and prompts are immutable. This parser
candidate keeps v3 C/P/G messages and charging unchanged, while allowing only
the declared generic source-map fields into G's final model input.
"""

import json

from scripts.serious_eval_arms_v3 import (
    prepare_generic_final_v3, prepare_primary_arms_v3)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate generic workspace key')
        result[key] = value
    return result


def prepare_generic_final_v4(prepared, raw_map):
    """Pass only exact, bounded source quotes and unresolved strings to G-final."""
    if not isinstance(raw_map, str) or not 2 <= len(raw_map) <= 60000:
        raise ValueError('bounded generic map response required')
    try:
        mapped = json.loads(raw_map, object_pairs_hook=_unique_object)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError('generic map JSON required') from exc
    if not isinstance(mapped, dict) or set(mapped) != {'source_index', 'open_questions'}:
        raise ValueError('exact generic workspace fields required')
    rows, questions = mapped['source_index'], mapped['open_questions']
    if (not isinstance(rows, list) or len(rows) > 64 or
            not isinstance(questions, list) or len(questions) > 32):
        raise ValueError('bounded generic workspace arrays required')
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'source_id', 'quote'} or
                not isinstance(row['source_id'], str) or
                not isinstance(row['quote'], str) or
                not 1 <= len(row['quote']) <= 1500):
            raise ValueError('exact bounded source quote row required')
    if any(not isinstance(value, str) or not 1 <= len(value) <= 2000
           for value in questions):
        raise ValueError('bounded unresolved-question strings required')
    # The v3 final builder still checks source IDs, exact quotations and
    # retention of the complete ordinary source; no historical parser changes.
    return prepare_generic_final_v3(prepared, json.dumps(mapped,
        ensure_ascii=False, sort_keys=True, separators=(',', ':')))


def provider_free_witness_v4(question, source_id, source_text, map_response):
    """Save actual final candidate messages without calling a provider."""
    prepared = prepare_primary_arms_v3(question, source_id, source_text)
    final = prepare_generic_final_v4(prepared,
        json.dumps(map_response, ensure_ascii=False))
    return {'C': prepared['C'], 'P': prepared['P'], 'G_map': prepared['G_map'],
        'G_final': final, 'ordinary_payload': prepared['ordinary_payload'],
        'accounting': prepared['accounting'],
        'prompt_qualification': prepared['qualification'],
        'workspace_boundary': 'STRICT_V4_PROVIDER_FREE_CANDIDATE_UNQUALIFIED'}
