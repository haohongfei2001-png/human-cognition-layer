"""Provider-free future source-auditor budget; consumed v1 never migrates or reruns.

The real v1 call exhausted 8,192 reasoning tokens before producing JSON.
This raises the explicit total-output reservation for a future different source;
it does not establish model competence or authorize any new transport.
"""
import hashlib
import json

MAX_OUTPUT_TOKENS = 16384
CLIENT_TIMEOUT_SECONDS = 300
PEAK_INPUT = 1.32
PEAK_OUTPUT = 3.96


def reserve_future_source_audit(messages, cap_usd):
    if (not isinstance(messages, list) or len(messages) != 2 or
            any(not isinstance(m, dict) or set(m) != {'role', 'content'} or
                not isinstance(m['content'], str) for m in messages) or
            [m['role'] for m in messages] != ['system', 'user'] or
            not isinstance(cap_usd, (int, float)) or isinstance(cap_usd, bool) or cap_usd <= 0):
        raise ValueError('complete ordinary messages and positive new cap required')
    request = dict(model='deepseek-v4-pro', messages=messages, thinking=dict(type='enabled'),
        reasoning_effort='high', max_tokens=MAX_OUTPUT_TOKENS, response_format=dict(type='json_object'))
    bound = 2 * len(json.dumps(request, ensure_ascii=False).encode()) + 2048
    reserve = (bound * PEAK_INPUT + MAX_OUTPUT_TOKENS * PEAK_OUTPUT) / 1_000_000
    if reserve > cap_usd:
        raise ValueError('future cap does not cover full native reasoning/output reservation')
    return dict(schema='hcl-i02-future-source-auditor-budget-v2',
        request_sha256=hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        complete_messages_sha256=hashlib.sha256(json.dumps(messages, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
        input_token_bound=bound, max_output_tokens=MAX_OUTPUT_TOKENS,
        client_timeout_seconds=CLIENT_TIMEOUT_SECONDS, peak_reservation_usd=reserve,
        provider_calls_authorized=0, provider_spend_authorized_usd=0,
        applies_to='FUTURE_DIFFERENT_SOURCE_AND_NEW_FREEZE_ONLY',
        consumed_v1_migration=False, existing_grant_transfer=False,
        model_semantics_qualified=False, longmemeval='SEALED_NOT_ACCESSED')
