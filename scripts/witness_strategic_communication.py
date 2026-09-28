"""D03 belief-sensitive falsehood and literally true concealment candidates."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace
from hcl.cognition.strategic_communication import prepare_strategic_communication

SOURCE = '\n'.join(('Mira said, "I want to make Noor believe the train is running."',
    'Mira said, "I believe the train is running."',
    'Mira said, "Noor, the train is running."',
    "Narrator: Mira's statement that the train is running is false."))
QUERY = "How might Mira's statement to Noor that the train is running be explained?"
TRUE_SOURCE = '\n'.join(('Mira said, "I want to keep Noor from learning that the bridge is closed."',
    'Mira said, "I know the bridge is closed."',
    'Noor said, "I need to know whether the bridge is closed."',
    "Narrator: Mira heard Noor's last statement.",
    'Mira said, "Noor, the bridge has lights."',
    "Narrator: Mira's statement that the bridge has lights is true.",
    "Narrator: Mira's statement that the bridge has lights omitted that the bridge is closed."))
TRUE_QUERY = "How might Mira's statement to Noor that the bridge has lights be explained?"


def witness():
    w = CognitionWorkspace()
    cases = dict(benign=(SOURCE, QUERY), contrary_belief=(SOURCE.replace('I believe the train is running.', 'I believe it is false that the train is running.'), QUERY),
        false_alone=('\n'.join(SOURCE.splitlines()[2:]), QUERY), literally_true=(TRUE_SOURCE, TRUE_QUERY))
    results = {}
    for name, (source, query) in cases.items():
        w.put_source('authored-d03-scene', source)
        results[name] = prepare_strategic_communication(w, query, source_id='authored-d03-scene').messages(w)
    states = {name: {r['hypothesis']: r['disposition'] for r in json.loads(messages[1]['content'])['explanations']} for name, messages in results.items()}
    assert states['benign']['BENIGN_ERROR'] == 'CONDITIONALLY_SUPPORTED'
    assert states['contrary_belief']['DELIBERATE_FALSEHOOD'] == 'CONDITIONALLY_SUPPORTED'
    assert states['false_alone']['DELIBERATE_FALSEHOOD'] == 'UNRESOLVED'
    assert states['literally_true']['LITERALLY_TRUE_POTENTIALLY_MISLEADING'] == 'CONDITIONALLY_SUPPORTED'
    return dict(schema='hcl-d03-positive-witness-v1',
        capability_delta='A changed pre-statement belief revises benign-error versus deliberate-falsehood conditions; a true statement can coexist with separately grounded concealment concerns, without determining actual deception.',
        actual_final_messages=results, implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_D03_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
