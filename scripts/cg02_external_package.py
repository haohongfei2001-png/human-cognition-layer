"""Freeze and verify a provider-free CG-02 five-arm development package.

This module has no provider client, credentials, or network path. It never runs
the external experiment; it only builds frozen inputs and checks treatment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from hcl.v1 import CognitionRequest, HCLCognitionLayer, prepare_social_narrative

PACKAGE = ROOT / 'reports' / 'HCL_CG02_EXTERNAL_PACKAGE.json'
QUESTION = (
    'Analyze the source social act and the later reported expectation. Return only '
    'one JSON object with string fields act_kind, condition, expectation_relation, '
    'access_status, response_reference, withdrawal_order, and a boolean '
    'unsupported_moral_claim. Use NONE for a field with no applicable fact and '
    'UNKNOWN for insufficient evidence. The relation labels are '
    'STRONGER_THAN_SOURCE, WEAKER_THAN_SOURCE, COMPATIBLE, or MIXED_OR_UNRESOLVED. '
    'Do not claim private understanding, deception, betrayal, broken promises, '
    'trust change or blame without separate explicit evidence.'
)
CASES = (
    dict(id='conditional_omission', target='Alice',
        narrative='Alice to Bob: "If I finish by Friday, I can go with you."\n'
                  'Bob: "Alice promised to go with me Friday."',
        gold=dict(act_kind='CONDITIONAL_COMMITMENT', condition='If I finish by Friday',
                  expectation_relation='STRONGER_THAN_SOURCE', access_status='DIRECT_ACCESS',
                  response_reference='NONE', withdrawal_order='NO_VISIBLE_WITHDRAWAL',
                  unsupported_moral_claim=False)),
    dict(id='conditional_preserved', target='Maya',
        narrative='Maya to Theo: "If the permit arrives Monday, I can host the workshop."\n'
                  'Theo: "If the permit arrives Monday, Maya promised to host the workshop."',
        gold=dict(act_kind='CONDITIONAL_COMMITMENT', condition='If the permit arrives Monday',
                  expectation_relation='COMPATIBLE', access_status='DIRECT_ACCESS',
                  response_reference='NONE', withdrawal_order='NO_VISIBLE_WITHDRAWAL',
                  unsupported_moral_claim=False)),
    dict(id='proposal_acceptance', target='Nora',
        narrative='Nora to Eli: "I propose we move the meeting to Tuesday."\n'
                  'Eli to Nora: "Yes, I accept."\n'
                  'Eli: "I expected Nora to move the meeting to Tuesday."',
        gold=dict(act_kind='PROPOSAL', condition='NONE',
                  expectation_relation='COMPATIBLE', access_status='NONE',
                  response_reference='ACCEPTANCE_REFERENCES_PRIOR',
                  withdrawal_order='NO_VISIBLE_WITHDRAWAL', unsupported_moral_claim=False)),
    dict(id='late_withdrawal', target='Leah',
        narrative='Leah to Omar: "If the venue confirms, I will reserve the room."\n'
                  'Omar: "Leah promised to reserve the room."\n'
                  'Leah to Omar: "I withdraw the reservation plan."',
        gold=dict(act_kind='CONDITIONAL_COMMITMENT', condition='If the venue confirms',
                  expectation_relation='STRONGER_THAN_SOURCE', access_status='DIRECT_ACCESS',
                  response_reference='WITHDRAWAL_REFERENCES_PRIOR',
                  withdrawal_order='AFTER_REPORTED_EXPECTATION',
                  unsupported_moral_claim=False)),
)


def _messages_for(case):
    question = f"For {case['target']}: {QUESTION}"
    source = case['narrative']
    direct = ({'role': 'system', 'content': 'Answer from the provided source only. Return the requested JSON.'},
              {'role': 'user', 'content': f'Source:\n{source}\n\nQuestion:\n{question}'})
    process = ({'role': 'system', 'content':
        'Read the source in order. Identify the exact speaker act and conditions. '
        'Then compare the participant\'s later quoted expectation with those conditions. '
        'Check whether the participant received the act, and whether acceptance or '
        'withdrawal happened before or after the expectation. Treat missing access '
        'as unknown and avoid moral or private-state conclusions. Return only the requested JSON.'},
        direct[1])
    generic_events = [dict(order=index + 1, speaker=event.actor_id,
        addressed_to=list(event.recipient_ids), text=event.raw_text)
        for index, event in enumerate(prepare_social_narrative(source).events)]
    generic = ({'role': 'system', 'content':
        'Use the ordered dialogue/event rows as a generic structured representation. '
        'Resolve speakers, recipients, conditions and later reports from the rows; '
        'do not assume private understanding. Return only the requested JSON.'},
        {'role': 'user', 'content': json.dumps({'events': generic_events,
            'question': question}, ensure_ascii=False, sort_keys=True)})
    request = CognitionRequest(question, target_actor=case['target'], narrative=source)
    h = HCLCognitionLayer(lambda messages: '').prepare(request)
    h_new = HCLCognitionLayer(lambda messages: '',
        social_checker_enabled=False).prepare(request)
    return {'C': list(direct), 'P': list(process), 'G': list(generic),
            'H': list(h.messages), 'H-new': list(h_new.messages)}, h, h_new


def build_package():
    rows = []
    for case in CASES:
        messages, h, h_new = _messages_for(case)
        state = h.context.social
        h_payload = json.loads(h.messages[-1]['content'])
        ablated_payload = json.loads(h_new.messages[-1]['content'])
        checked = h_payload['cognition_context']['social']
        h_payload['cognition_context']['social'] = {}
        primary = state['acts'][0]
        comparison = state['expectation_comparisons'][0]
        related = [row for row in state['acts'][1:] if row['refers_to'] == primary['act_id']]
        reference = ('WITHDRAWAL_REFERENCES_PRIOR' if any(row['kind'] == 'WITHDRAWAL'
            for row in related) else 'ACCEPTANCE_REFERENCES_PRIOR' if any(
            row['kind'] == 'ACCEPTANCE' for row in related) else 'NONE')
        condition = (primary['conditions_visible_in_view'][0]['text']
            if primary['conditions_visible_in_view'] else 'NONE')
        access = (next(iter(comparison['condition_access'].values()))
            if comparison['condition_access'] else 'NONE')
        preflight = {
            'source_valid': (h.preparation_receipt['failure'] is None and
                all(event['raw_text'] in case['narrative'] for event in h.context.evidence)),
            'grounded_act': state['checked_act_count'] >= 1,
            'condition_or_expectation_checked': state['checked_expectation_count'] >= 1,
            'checked_state_in_h': checked == state and bool(checked['acts']),
            'checker_removed_in_h_new': h_new.context.social == {},
            'final_inputs_differ_only_by_checked_state': (
                messages['H'] != messages['H-new'] and h_payload == ablated_payload),
            'zero_extraction_provider_calls': h.preparation_receipt['extraction_provider_calls'] == 0,
            'gold_matches_checked_source': (primary['kind'] == case['gold']['act_kind'] and
                condition == case['gold']['condition'] and
                comparison['relation'] == case['gold']['expectation_relation'] and
                access == case['gold']['access_status'] and
                reference == case['gold']['response_reference'] and
                comparison['withdrawal_order'] == case['gold']['withdrawal_order']),
        }
        if not all(preflight.values()):
            raise ValueError(f"CG-02 treatment-presence gate failed for {case['id']}: {preflight}")
        if any(len(json.dumps(arm_messages, ensure_ascii=False).encode()) > 8000
               for arm_messages in messages.values()):
            raise ValueError('input byte cap exceeded')
        rows.append({'case_id': case['id'], 'source_origin': 'HCL-authored synthetic dialogue',
            'exposure': 'source_audit_exposed_not_fresh_or_population_representative',
            'narrative': case['narrative'],
            'source_sha256': hashlib.sha256(case['narrative'].encode()).hexdigest(),
            'gold': case['gold'], 'preflight': preflight,
            'preparation_receipt': h.preparation_receipt,
            'checked_state': state, 'messages': messages})
    return {'schema': 'hcl-cg02-external-package-v1',
        'source_policy': 'Four newly authored, public in-repository development dialogues; no third-party source or sealed benchmark.',
        'purpose': 'bounded paired development probe; no broad efficacy or freshness claim',
        'provider': 'deepseek',
        'provider_endpoint': 'https://api.deepseek.com',
        'actions_secret_name': 'DEEPSEEK_API_KEY',
        'model': 'deepseek-v4-pro',
        'model_version': 'DeepSeek-V4-Pro-0813',
        'provider_request': {
            'thinking': {'type': 'disabled'},
            'response_format': {'type': 'json_object'},
            'max_retries': 0,
        },
        'arms': ['C', 'P', 'G', 'H', 'H-new'], 'cases': rows,
        'maximum_provider_calls': 20, 'retries': 0,
        'maximum_input_tokens_per_call': 8000,
        'maximum_output_tokens_per_call': 512,
        'estimated_worst_case_usd': 0.2517504,
        'proposed_hard_cap_usd': 0.30,
        'price_basis': {
            'basis': 'existing repository-frozen CG-01 DeepSeek peak-price contract',
            'source_package': 'reports/HCL_CG01_EXTERNAL_PACKAGE.json',
            'input_cache_miss_usd_per_million': 1.32,
            'output_usd_per_million': 3.96,
        },
        'execution_authorized': False,
        'owner_gate': 'HCL_CG02_EXTERNAL_VALIDATION_OWNER_AUTHORIZATION',
        'longmemeval': 'SEALED_NOT_ACCESSED'}


def score_answer(case, answer):
    """Strict predeclared field scorer; invalid JSON or extra claims fail."""
    try:
        parsed = json.loads(answer)
    except (TypeError, ValueError):
        return {'valid': False, 'exact_fields': 0, 'all_fields_correct': False}
    gold = case['gold']
    if not isinstance(parsed, dict) or set(parsed) != set(gold):
        return {'valid': False, 'exact_fields': 0, 'all_fields_correct': False}
    exact = sum(parsed[key] == gold[key] and type(parsed[key]) is type(gold[key])
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
        raise SystemExit('frozen CG-02 external package differs from provider-free preflight')
    print(json.dumps({'cases': len(package['cases']), 'arms': package['arms'],
        'maximum_provider_calls': package['maximum_provider_calls'],
        'provider_calls_executed': 0, 'treatment_presence': 'PASS'}))
