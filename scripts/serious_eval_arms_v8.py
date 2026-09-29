"""I02 comparator candidate with an executable strong-model call contract.

Historical v1-v7 prompts and paid runs remain immutable. This candidate is
provider-free and does not qualify model behavior or authorize a paid run.
"""

from copy import deepcopy

from scripts.serious_eval_generic_workspace_v7 import (
    prepare_generic_final_v7, prepare_primary_arms_v7)


_CITATION_CONTRACT = (
    'In the final JSON, source_citations must be an array of objects, each '
    'with exactly source_id and quote. The quote is one nonempty exact '
    'substring of that source text, not an array, paraphrase, or workspace '
    'summary. Use [] when no source quote supports a claim. Keep answer, '
    'uncertainty, and assumptions as strings. '
)

_CALL_SPEC = {
    'provider': 'deepseek',
    'model': 'deepseek-v4-pro',
    'thinking': {'type': 'enabled'},
    'reasoning_effort': 'high',
    'response_format': {'type': 'json_object'},
    'max_tokens': 8192,
}


def call_spec_v8(phase):
    """One explicit native reasoning setting for all final comparators.

    G-map is separately charged and gets the same reasoning mode. No token
    ceilings or price are frozen here; I02 must establish those before I03.
    """
    if phase not in {'C', 'P', 'G_map', 'G_final'}:
        raise ValueError('unknown comparator phase')
    return deepcopy(_CALL_SPEC)


def prepare_primary_arms_v8(question, source_id, source_text):
    prepared = prepare_primary_arms_v7(question, source_id, source_text)
    for phase in ('C', 'P'):
        prepared[phase][0] = dict(prepared[phase][0],
            content=_CITATION_CONTRACT + prepared[phase][0]['content'])
    prepared['qualification'] = 'C_P_G_V8_PROVIDER_FREE_CANDIDATE_UNQUALIFIED'
    prepared['call_specs'] = {phase: call_spec_v8(phase)
        for phase in ('C', 'P', 'G_map', 'G_final')}
    return prepared


def prepare_generic_final_v8(prepared, raw_map):
    if prepared.get('qualification') != 'C_P_G_V8_PROVIDER_FREE_CANDIDATE_UNQUALIFIED':
        raise ValueError('v8 prepared comparator required')
    legacy = dict(prepared,
        qualification='C_P_G_V7_PROVIDER_FREE_CANDIDATE_UNQUALIFIED')
    final = prepare_generic_final_v7(legacy, raw_map)
    final[0] = dict(final[0], content=_CITATION_CONTRACT + final[0]['content'])
    return final
