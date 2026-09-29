"""Provider-free H treatment-presence check on exposed external calibration input."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.v1 import CognitionRequest, HCLCognitionLayer
from hcl.v1.router import CognitionRouter
from scripts.i02_musr_calibration import FIRST_GROUP_SHA256, calibration_candidate, parse_pinned
from scripts.serious_eval_contract import runtime_digest


def require_treatment(receipt):
    if (receipt.get('provider_calls') != 0 or receipt.get('native_gold_used') is not False or
            receipt.get('longmemeval') != 'SEALED_NOT_ACCESSED' or
            receipt.get('specialized_treatment_present') is not True or
            receipt.get('cognition_context_present') is not True or
            receipt.get('checked_observation_count', 0) < 1):
        raise ValueError('H treatment-presence gate failed; no paid comparison')
    return True


def require_fair_treatment(receipt):
    require_treatment(receipt)
    if (receipt.get('source_quote_span_valid') is not True or
            receipt.get('h_hnew_same_question_and_source') is not True or
            receipt.get('h_hnew_same_other_context') is not True or
            receipt.get('h_hnew_only_information_state_capability_diff') is not True or
            receipt.get('h_hnew_final_input_different') is not True):
        raise ValueError('H/H-new fairness or grounded treatment gate failed')
    return True


def audit(source_file):
    rows, groups = parse_pinned(Path(source_file).read_bytes())
    if groups[FIRST_GROUP_SHA256] != [0, 1, 2, 3]:
        raise ValueError('exposed calibration group changed')
    candidate = calibration_candidate(rows[0], source_group_id=FIRST_GROUP_SHA256)
    request = CognitionRequest(candidate['question'], narrative=candidate['source_text'])
    prepared = HCLCognitionLayer(lambda _: '').prepare(request)
    ablated = HCLCognitionLayer(lambda _: '',
        router=CognitionRouter(information_state_enabled=False)).prepare(request)
    # A direct pass-through is a legitimate implementation behavior, but it
    # cannot serve as specialized H treatment evidence for this case family.
    direct = prepared.plan.direct
    actual_user_input = json.loads(prepared.messages[-1]['content'])
    ablated_user_input = json.loads(ablated.messages[-1]['content'])
    if actual_user_input['narrative'] != candidate['source_text'] or (
            actual_user_input['query'] != candidate['question']):
        raise ValueError('H ordinary input drift')
    checked = ((prepared.context.information_state.get('checked_observation_count', 0))
               if prepared.context is not None else 0)
    treatment = bool(checked and 'information_state' in prepared.plan.capabilities)
    observation = (prepared.context.information_state['last_reported_observation']
        if treatment else None)
    source_valid = bool(observation and candidate['source_text'][
        observation['source_start']:observation['source_end']] == observation['source_quote'])
    same_source = bool(actual_user_input.get('query') == ablated_user_input.get('query') and
        actual_user_input.get('narrative') == ablated_user_input.get('narrative') ==
            candidate['source_text'])
    h_context = actual_user_input.get('cognition_context', {})
    hnew_context = ablated_user_input.get('cognition_context', {})
    same_other_context = ({k: v for k, v in h_context.items() if k != 'information_state'} ==
        hnew_context and 'information_state' not in hnew_context)
    only_mechanism = (set(prepared.plan.capabilities) - set(ablated.plan.capabilities) ==
        {'information_state'} and
        set(ablated.plan.capabilities) - set(prepared.plan.capabilities) == set())
    result = dict(schema='hcl-i02-native-treatment-preflight-v2',
        source_file_sha256=hashlib.sha256(Path(source_file).read_bytes()).hexdigest(),
        source_group_sha256=FIRST_GROUP_SHA256,
        calibration_case_id=candidate['case_id'],
        architecture_main_sha='636c6fe849dfba641d03df2813d0e568a1835300',
        evaluated_hcl_runtime_sha256=runtime_digest(),
        entry='HCLCognitionLayer.prepare(CognitionRequest(ordinary_question,narrative))',
        direct=direct, selected_capabilities=list(prepared.plan.capabilities),
        cognition_context_present=prepared.context is not None,
        checked_observation_count=checked,
        source_and_question_preserved_in_final_input=True,
        source_quote_span_valid=source_valid,
        checked_observation=observation,
        h_hnew_same_question_and_source=same_source,
        h_hnew_same_other_context=same_other_context,
        h_hnew_only_information_state_capability_diff=only_mechanism,
        h_hnew_final_input_different=(prepared.messages != ablated.messages),
        h_final_input_sha256=hashlib.sha256(json.dumps(prepared.messages,
            ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        hnew_final_input_sha256=hashlib.sha256(json.dumps(ablated.messages,
            ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        specialized_treatment_present=treatment,
        provider_calls=0, provider_spend_usd=0,
        native_gold_used=False, longmemeval='SEALED_NOT_ACCESSED')
    try:
        require_fair_treatment(result)
    except ValueError:
        result['disposition'] = 'FAIL_TREATMENT_OR_FAIRNESS_NO_PAID_COMPARISON'
    else:
        result['disposition'] = 'PASS_PROVIDER_FREE_TREATMENT_REVIEW_BEFORE_PAID_COMPARISON'
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('source_file')
    parser.add_argument('--output')
    args = parser.parse_args()
    result = audit(args.source_file)
    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2) + '\n')
    else:
        print(json.dumps(result))
