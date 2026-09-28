"""D02 received acknowledgment versus exposure and revised meaning."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace
from hcl.cognition.mutual_understanding import prepare_mutual_understanding

SOURCE = '\n'.join(('Mira said, "I mean that the meeting is at noon."',
    "Narrator: Noor heard Mira's last statement.",
    'Noor said, "I understand Mira to mean that the meeting is at noon."',
    "Narrator: Mira heard Noor's last statement.",
    'Mira said, "I confirm Noor\'s understanding that the meeting is at noon."',
    "Narrator: Noor heard Mira's last statement."))
QUERY = 'Do Mira and Noor share an acknowledged understanding that the meeting is at noon?'


def witness():
    w = CognitionWorkspace()
    revised = SOURCE + '\nMira said, "I revise my meaning from the meeting is at noon to the meeting is at one."'
    cases = dict(hearing_only='\n'.join(SOURCE.splitlines()[:2]) + '\nNoor said, "Okay."',
        confirmation_unreceived='\n'.join(SOURCE.splitlines()[:-1]), acknowledged=SOURCE, revised=revised)
    results = {}
    for name, source in cases.items():
        w.put_source('authored-d02-scene', source)
        results[name] = prepare_mutual_understanding(w, QUERY, source_id='authored-d02-scene').messages(w)
    statuses = {name: json.loads(messages[1]['content'])['status'] for name, messages in results.items()}
    assert statuses == dict(hearing_only='NO_COMPLETE_ACKNOWLEDGMENT_CHAIN',
        confirmation_unreceived='ACKNOWLEDGMENT_DELIVERY_INCOMPLETE',
        acknowledged='BOUNDED_MUTUALLY_ACKNOWLEDGED', revised='SUPERSEDED_MEANING')
    return dict(schema='hcl-d02-positive-witness-v1',
        capability_delta='Separate exposure from received finite mutual acknowledgment; an explicit meaning revision retires the old shared interpretation without silently updating the other person.',
        actual_final_messages=results, implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_D02_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
