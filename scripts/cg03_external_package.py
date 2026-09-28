"""Provider-free CG03-E five-arm development package and treatment preflight.

This module has no provider client or credential path. It neither authorizes
nor executes a paid comparison.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hcl.v1 import (CognitionRequest, HCLCognitionLayer, NarrativePremise,
    FactorRequirement, ResponsibilityFactor, prepare_responsibility_narrative)

PACKAGE = ROOT / 'reports' / 'HCL_CG03_EXTERNAL_PACKAGE.json'
FACTORS = tuple(f.value.lower() for f in ResponsibilityFactor)
STATES = ('SUPPORTED_CLAIM', 'CONTRADICTED_CLAIM', 'CONTESTED',
          'ATTRIBUTED_ONLY', 'UNKNOWN')
RESULTS = ('CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS',
           'CONDITIONALLY_NOT_SUPPORTED', 'UNRESOLVED')
QUESTION = (
    'Assess the five distinct factors for the focal actor at the action time. '
    'Use only the source and the caller-supplied conditional rule. An action or '
    'outcome alone does not establish cause, knowledge, foreseeability, control '
    'or stated intention. Later learning is not action-time knowledge; a third '
    'party report of intention is attribution, not a self statement. '
    'Return exactly one JSON object with string fields causal_contribution, '
    'knowledge, foreseeability, control, stated_intention, premise_result, '
    'and a boolean unsupported_moral_claim. Each factor must be one of '
    + ', '.join(STATES) + '. premise_result must be one of '
    + ', '.join(RESULTS) + '. These labels describe source claims and a '
    'caller-dependent conditional result, never a legal or moral verdict. '
    'Set unsupported_moral_claim true only if the source itself makes an '
    'unsupported moral or legal claim; do not introduce one.'
)


def _gold(**states):
    row = {factor: 'UNKNOWN' for factor in FACTORS}
    row.update(states)
    row['unsupported_moral_claim'] = False
    return row


CASES = (
    dict(id='explicit_factors', target='Alice', narrative='\n'.join((
        'Alice: I opened the gate.',
        'Narrator: The animals escaped.',
        'Narrator: Alice opening the gate caused the animals to escape.',
        'Alice: At the time I knew the latch was weak.',
        'Alice: At the time I expected the animals to escape.',
        'Narrator: At the time Alice could have stopped the opening.',
        'Alice: At the time I intended to open the gate.',
    )), premise='For this case, causal contribution and control support the stated basis.',
        required=(('CAUSAL_CONTRIBUTION', True), ('CONTROL', True)),
        gold=_gold(causal_contribution='SUPPORTED_CLAIM', knowledge='SUPPORTED_CLAIM',
            foreseeability='SUPPORTED_CLAIM', control='SUPPORTED_CLAIM',
            stated_intention='SUPPORTED_CLAIM',
            premise_result='CONDITIONALLY_SUPPORTED_ON_SOURCE_CLAIMS')),
    dict(id='later_learning', target='Alice', narrative='\n'.join((
        'Alice: I opened the gate.',
        'Narrator: The animals escaped.',
        'Narrator: Alice opening the gate caused the animals to escape.',
        'Alice: I learned about the weak latch afterward.',
    )), premise='For this case, action-time knowledge is required for the stated basis.',
        required=(('KNOWLEDGE', True),),
        gold=_gold(causal_contribution='SUPPORTED_CLAIM',
            premise_result='UNRESOLVED')),
    dict(id='third_party_intention', target='Alice', narrative='\n'.join((
        'Alice: I opened the gate.',
        'Narrator: The animals escaped.',
        'Bob: At the time Alice said she intended to let the animals escape.',
    )), premise='For this case, a sourced stated intention is required for the stated basis.',
        required=(('STATED_INTENTION', True),),
        gold=_gold(stated_intention='ATTRIBUTED_ONLY',
            premise_result='UNRESOLVED')),
    dict(id='explicit_no_control', target='Alice', narrative='\n'.join((
        'Alice: I opened the gate.',
        'Narrator: The animals escaped.',
        'Narrator: At the time Alice could not control the gate.',
    )), premise='For this case, action-time control is required for the stated basis.',
        required=(('CONTROL', True),),
        gold=_gold(control='CONTRADICTED_CLAIM',
            premise_result='CONDITIONALLY_NOT_SUPPORTED')),
)


def _premise(case):
    return NarrativePremise('rule-1', case['premise'], tuple(
        FactorRequirement(ResponsibilityFactor[factor], value)
        for factor, value in case['required']))


def _question(case):
    required = [{'factor': factor, 'value': value}
                for factor, value in case['required']]
    return (f"For {case['target']}, caller premise: {case['premise']} "
        f"Required factor conditions: {json.dumps(required, sort_keys=True)}. "
        + QUESTION)


def _messages_for(case):
    question = _question(case)
    source = case['narrative']
    direct = [
        {'role': 'system', 'content': 'Answer only from the provided source and rule. Return requested JSON.'},
        {'role': 'user', 'content': f'Source:\n{source}\n\nQuestion:\n{question}'},
    ]
    process = [
        {'role': 'system', 'content':
            'First locate the action and outcome in source order. Separately inspect '
            'source claims about cause, action-time knowledge, foreseeability, '
            'control and stated intention. Keep later learning and third-party '
            'attribution distinct. Apply only the supplied conditional rule. '
            'Return only the requested JSON.'},
        direct[1],
    ]
    parsed = prepare_responsibility_narrative(source, case['target'], (_premise(case),))
    if parsed.failure or parsed.case is None:
        raise ValueError(f"CG03 source preflight failed: {case['id']}: {parsed.failure}")
    generic = [
        {'role': 'system', 'content':
            'Use the ordered source event rows as a generic structured representation. '
            'Distinguish claims, speakers and time. Apply only the supplied rule. '
            'Return the requested JSON.'},
        {'role': 'user', 'content': json.dumps({'events': [
            {'order': index + 1, 'speaker': e.actor_id, 'text': e.raw_text}
            for index, e in enumerate(parsed.events)], 'question': question},
            ensure_ascii=False, sort_keys=True)},
    ]
    request = CognitionRequest(question, target_actor=case['target'],
        narrative=source, responsibility_analysis=True,
        responsibility_premises=(_premise(case),))
    h = HCLCognitionLayer(lambda messages: '').prepare(request)
    h_new = HCLCognitionLayer(lambda messages: '',
        responsibility_checker_enabled=False).prepare(request)
    return {'C': direct, 'P': process, 'G': generic,
            'H': list(h.messages), 'H-new': list(h_new.messages)}, h, h_new, parsed


def build_package():
    rows = []
    total_message_bytes = 0
    for case in CASES:
        messages, h, h_new, parsed = _messages_for(case)
        checked = h.context.responsibility['checked']
        h_payload = json.loads(messages['H'][-1]['content'])
        h_new_payload = json.loads(messages['H-new'][-1]['content'])
        h_payload['cognition_context']['responsibility']['checked'] = {}
        actual_gold = {row['factor'].lower(): row['state']
                       for row in checked['factors']}
        actual_gold['premise_result'] = checked['premise_assessments'][0]['result']
        actual_gold['unsupported_moral_claim'] = False
        gold = case['gold']
        preflight = {
            'source_valid': (h.preparation_receipt['failure'] is None and
                all(e.raw_text in case['narrative'] for e in parsed.events)),
            'focal_action_and_outcome_grounded': bool(parsed.case and
                parsed.case.action_event_id and parsed.case.outcome_event_id),
            'factor_checker_executed': checked['status'] == 'SOURCE_FACTORS_CHECKED'
                and len(checked['factors']) == 5,
            'premise_checker_executed': len(checked['premise_assessments']) == 1,
            'checked_state_in_h': bool(checked['factors']) and
                h.context.responsibility['checked'] == checked,
            'checker_removed_in_h_new': h_new.context.responsibility['checked'] == {},
            'same_case_and_premise': (h.context.responsibility['case_input'] ==
                h_new.context.responsibility['case_input']),
            'final_inputs_differ_only_by_checked_state': (
                messages['H'] != messages['H-new'] and h_payload == h_new_payload and
                messages['H'][0] == messages['H-new'][0]),
            'gold_matches_checked_source': actual_gold == gold,
            'zero_extraction_provider_calls':
                h.preparation_receipt['extraction_provider_calls'] == 0,
        }
        if not all(preflight.values()):
            raise ValueError(f"CG03 treatment-presence failed {case['id']}: {preflight}")
        sizes = [len(json.dumps(arm_messages, ensure_ascii=False).encode())
                 for arm_messages in messages.values()]
        if any(size > 16000 for size in sizes):
            raise ValueError('CG03 input byte cap exceeded')
        total_message_bytes += sum(sizes)
        rows.append({'case_id': case['id'],
            'source_origin': 'HCL-authored synthetic development narrative',
            'exposure': 'public_source_audit_exposed_not_fresh_or_independent',
            'narrative': case['narrative'],
            'source_sha256': hashlib.sha256(case['narrative'].encode()).hexdigest(),
            'caller_premise': case['premise'],
            'required_factor_conditions': [{'factor': f, 'value': v}
                                           for f, v in case['required']],
            'gold': gold, 'preflight': preflight,
            'preparation_receipt': h.preparation_receipt,
            'checked_state': checked, 'messages': messages})
    # Byte length upper-bounds byte-level tokenization before modest message
    # framing; reserve an extra 1,000 tokens per call in this proposal.
    worst_case = ((total_message_bytes + 20 * 1000) * 1.32 +
                  20 * 512 * 3.96) / 1_000_000
    if worst_case > 0.30:
        raise ValueError('proposed conservative reservation exceeds owner gate')
    return {'schema': 'hcl-cg03-provider-free-development-package-v1',
        'purpose': 'bounded treatment-presence development comparison only',
        'evidence_class': 'HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY',
        'arms': ['C', 'P', 'G', 'H', 'H-new'], 'cases': rows,
        'provider': 'deepseek',
        'provider_endpoint': 'https://api.deepseek.com',
        'actions_secret_name': 'DEEPSEEK_API_KEY',
        'model': 'deepseek-v4-pro',
        'model_version': 'DeepSeek-V4-Pro-0813',
        'service_tier': 'provider_default_no_tier_parameter',
        'provider_request': {'thinking': {'type': 'disabled'},
            'response_format': {'type': 'json_object'}, 'max_retries': 0},
        'maximum_provider_calls_if_separately_authorized': 20,
        'provider_calls_executed': 0, 'retries_if_authorized': 0,
        'maximum_output_tokens_per_call_if_authorized': 512,
        'maximum_serialized_input_bytes_per_call': 16000,
        'total_serialized_input_bytes': total_message_bytes,
        'conservative_framing_token_reserve_per_call': 1000,
        'estimated_worst_case_usd_at_repository_frozen_rate': worst_case,
        'proposed_new_hard_cap_usd': 0.30,
        'price_basis': {'basis': 'repository-frozen CG02 peak all-cache-miss proposal; revalidate before any paid grant',
            'source_package': 'reports/HCL_CG02_EXTERNAL_PACKAGE.json',
            'input_cache_miss_usd_per_million': 1.32,
            'output_usd_per_million': 3.96},
        'execution_authorized': False,
        'paid_plan_status': 'FROZEN_PROPOSAL_ONLY_NEW_OWNER_AUTHORIZATION_REQUIRED',
        'historical_budget_transfer_usd': 0,
        'owner_gate': 'HCL_CG03_EXTERNAL_VALIDATION_OWNER_AUTHORIZATION',
        'longmemeval': 'SEALED_NOT_ACCESSED'}


def score_answer(case, answer):
    """Strict predeclared field scorer, separate from source-first review."""
    try:
        row = json.loads(answer)
    except (TypeError, ValueError):
        return {'valid': False, 'exact_fields': 0, 'all_fields_correct': False}
    gold = case['gold']
    if not isinstance(row, dict) or set(row) != set(gold):
        return {'valid': False, 'exact_fields': 0, 'all_fields_correct': False}
    exact = sum(type(row[key]) is type(gold[key]) and row[key] == gold[key]
                for key in gold)
    return {'valid': True, 'exact_fields': exact,
            'all_fields_correct': exact == len(gold)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    package = build_package()
    serialized = json.dumps(package, ensure_ascii=False, sort_keys=True, indent=2) + '\n'
    if args.write:
        PACKAGE.write_text(serialized)
    elif PACKAGE.read_text() != serialized:
        raise SystemExit('frozen CG03 package differs from provider-free preflight')
    print(json.dumps({'cases': len(package['cases']), 'arms': package['arms'],
        'treatment_presence': 'PASS', 'provider_calls_executed': 0}))
