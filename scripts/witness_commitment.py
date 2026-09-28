"""D01 conditional promise lifecycle and later receipt witness."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace
from hcl.cognition.commitments import prepare_commitment

SOURCE = '\n'.join(('Mira said, "I promise Noor to deliver the report if the permit arrives."',
    "Narrator: Noor did not hear Mira's last statement.",
    'Noor said, "I expect Mira to deliver the report."'))
QUERY = "What is the status of Mira's promise to Noor to deliver the report?"


def witness():
    w = CognitionWorkspace()
    cases = dict(unknown=SOURCE,
        condition_false=SOURCE + '\nNarrator: It is false that the permit arrives.',
        condition_true=SOURCE + '\nNarrator: It is true that the permit arrives.',
        later_receipt=SOURCE + "\nNarrator: Noor later heard Mira's last statement.",
        withdrawal=SOURCE + '\nMira said, "I withdraw my promise to Noor to deliver the report."')
    results = {}
    for name, source in cases.items():
        w.put_source('authored-d01-scene', source)
        result = prepare_commitment(w, QUERY, source_id='authored-d01-scene')
        results[name] = result.messages(w)
    states = {name: json.loads(messages[1]['content']) for name, messages in results.items()}
    assert states['unknown']['commitment']['lifecycle'] == 'CONDITION_UNRESOLVED'
    assert states['condition_false']['commitment']['lifecycle'] == 'CONDITION_NOT_MET_IN_SOURCE'
    assert states['condition_true']['commitment']['lifecycle'] == 'CONDITIONALLY_TRIGGERED_IN_SOURCE'
    assert states['withdrawal']['commitment']['lifecycle'] == 'REPORTED_WITHDRAWN'
    assert states['later_receipt']['cg02_source_check']['expectation_comparisons'][0]['condition_receipt_at_expectation'] == 'REPORTED_NON_EXPOSURE'
    return dict(schema='hcl-d01-positive-witness-v1',
        capability_delta='Distinguish false/unknown promise conditions, missing receipt and withdrawal; later receipt changes current access without rewriting earlier expectation knowledge.',
        actual_final_messages=results, implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_D01_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
