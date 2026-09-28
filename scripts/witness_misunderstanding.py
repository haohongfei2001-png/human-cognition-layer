"""D04 local factors and explicit expectation repair without promise rewriting."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace
from hcl.cognition.misunderstanding import prepare_misunderstanding

SOURCE = '\n'.join(('Mira said, "In team, by ready I mean permit is true."',
    'Noor said, "In team, by ready I mean draft is true."',
    'Mira said, "I promise Noor to deliver the ready report if the permit arrives."',
    "Narrator: Noor did not hear Mira's last statement.",
    'Noor said, "As reviewer in team, I expect Mira to deliver the ready report."',
    'Noor said, "I expect Mira to deliver the ready report."'))
CLARIFY = '\nMira said, "I clarify to Noor that my promise to deliver the ready report still requires that the permit arrives."'
RECEIPT = "\nNarrator: Noor heard Mira's last statement."
REVISION = '\nNoor said, "I now expect Mira to deliver the ready report if the permit arrives."'
QUERY = "Explain Noor's expectation of Mira's promise to deliver the ready report in team, using ready for report."


def witness():
    w = CognitionWorkspace()
    cases = dict(initial=SOURCE, unreceived=SOURCE + CLARIFY, received=SOURCE + CLARIFY + RECEIPT,
        revised=SOURCE + CLARIFY + RECEIPT + REVISION)
    results = {}
    for name, source in cases.items():
        w.put_source('authored-d04-scene', source)
        results[name] = prepare_misunderstanding(w, QUERY, source_id='authored-d04-scene').messages(w)
    states = {name: json.loads(messages[1]['content']) for name, messages in results.items()}
    assert states['initial']['initial_factors']['local_meaning']['status'] == 'DIFFERING_SOURCE_LOCAL_CRITERIA'
    assert states['unreceived']['status'] == 'CLARIFICATION_NOT_RECEIVED'
    assert states['received']['status'] == 'CLARIFICATION_RECEIVED_EXPECTATION_UNREVISED'
    assert states['revised']['status'] == 'REVISED_EXPECTATION_ALIGNS_CLARIFICATION_AVAILABLE'
    assert states['revised']['original_promise']['quote'] == states['initial']['original_promise']['quote']
    return dict(schema='hcl-d04-positive-witness-v1',
        capability_delta='Localize non-receipt, condition omission, differing local meanings and role expectation; explicit revised expectation replaces the current analyst explanation without rewriting the original promise or inferring restored trust.',
        actual_final_messages=results, implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_D04_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
