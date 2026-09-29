"""Provider-free I02 ordinary-input coverage receipt for fair C/P/G/H runs.

An H entry failure is an observed outcome under I01, never an exclusion rule.
Historical comparators and the frozen HCL runtime are not modified here.
"""
import hashlib
import json

from hcl.v1 import CognitionRequest, HCLCognitionLayer
from scripts.serious_eval_arms_v3 import prepare_primary_arms_v3
from scripts.serious_eval_contract import runtime_digest


def _digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def audit_ordinary_input(question, source_id, source_text):
    """Save complete input coverage without calling a model or reading gold."""
    prepared = prepare_primary_arms_v3(question, source_id, source_text)
    payload = prepared['ordinary_payload']
    for arm in ('C', 'P', 'G_map'):
        actual = json.loads(prepared[arm][-1]['content'])
        if (actual.get('question') != payload['question'] or
                actual.get('sources') != payload['sources'] or
                (arm != 'G_map' and actual != payload)):
            raise ValueError('comparator ordinary input drift')
    result = dict(schema='hcl-i02-ordinary-input-coverage-v1',
        question_sha256=_digest(question), source_id=source_id,
        source_sha256=_digest(source_text), source_chars=len(source_text),
        hcl_runtime_sha256=runtime_digest(),
        comparator_candidate='C_P_G_V3_PROVIDER_FREE_UNQUALIFIED',
        c_p_g_complete_source=True, provider_calls=0,
        provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')
    try:
        candidate = HCLCognitionLayer(lambda _: '').prepare(
            CognitionRequest(question, narrative=source_text,
                max_context_chars=64000))
    except ValueError as exc:
        result.update(h_entry='REJECTED_OBSERVED_OUTCOME',
            h_failure_type=type(exc).__name__, h_failure_reason=str(exc),
            h_complete_source_in_final_input=False)
    else:
        user = json.loads(candidate.messages[-1]['content'])
        if user.get('query') != question or user.get('narrative') != source_text:
            raise ValueError('H final input lost ordinary question or complete source')
        result.update(h_entry='ACCEPTED_PROVIDER_FREE', h_failure_type=None,
            h_failure_reason=None, h_complete_source_in_final_input=True,
            h_final_input_sha256=_digest(json.dumps(candidate.messages,
                ensure_ascii=False, sort_keys=True)))
    return result


def require_recorded_outcome(receipt):
    """Do not convert H refusal into a supposedly eligible H sample."""
    if (receipt.get('schema') != 'hcl-i02-ordinary-input-coverage-v1' or
            receipt.get('provider_calls') != 0 or
            receipt.get('c_p_g_complete_source') is not True or
            receipt.get('h_entry') not in ('ACCEPTED_PROVIDER_FREE',
                                           'REJECTED_OBSERVED_OUTCOME') or
            receipt.get('h_complete_source_in_final_input') is not
                (receipt['h_entry'] == 'ACCEPTED_PROVIDER_FREE')):
        raise ValueError('ordinary input coverage outcome missing or inconsistent')
    return True
