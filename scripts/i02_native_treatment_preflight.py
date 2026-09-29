"""Provider-free H treatment-presence check on exposed external calibration input."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.v1 import CognitionRequest, HCLCognitionLayer
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


def audit(source_file):
    rows, groups = parse_pinned(Path(source_file).read_bytes())
    if groups[FIRST_GROUP_SHA256] != [0, 1, 2, 3]:
        raise ValueError('exposed calibration group changed')
    candidate = calibration_candidate(rows[0], source_group_id=FIRST_GROUP_SHA256)
    request = CognitionRequest(candidate['question'], narrative=candidate['source_text'])
    prepared = HCLCognitionLayer(lambda _: '').prepare(request)
    # A direct pass-through is a legitimate implementation behavior, but it
    # cannot serve as specialized H treatment evidence for this case family.
    direct = prepared.plan.direct
    actual_user_input = json.loads(prepared.messages[-1]['content'])
    if actual_user_input['narrative'] != candidate['source_text'] or (
            actual_user_input['query'] != candidate['question']):
        raise ValueError('H ordinary input drift')
    checked = ((prepared.context.information_state.get('checked_observation_count', 0))
               if prepared.context is not None else 0)
    treatment = bool(checked and 'information_state' in prepared.plan.capabilities)
    return dict(schema='hcl-i02-native-treatment-preflight-v1',
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
        specialized_treatment_present=treatment,
        disposition=('FAIL_TREATMENT_ABSENT_NO_PAID_COMPARISON' if not treatment else
            'REVIEW_CHECKED_TREATMENT_BEFORE_ANY_PAID_COMPARISON'),
        provider_calls=0, provider_spend_usd=0,
        native_gold_used=False, longmemeval='SEALED_NOT_ACCESSED')


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
