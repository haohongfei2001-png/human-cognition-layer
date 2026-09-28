"""C02 ordinary mixed-goal alternatives and explicit ignorance counterevidence."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace
from hcl.cognition.action_explanations import prepare_explanations


def witness():
    source = '\n'.join(('Mira said, "I want to avoid the noise."',
        'Mira said, "I plan to skip the meeting in order to avoid the noise."',
        'Mira said, "I want to finish the report."',
        'Mira said, "I plan to skip the meeting in order to finish the report."',
        'Mira said, "At the time, I knew about the meeting."',
        'Mira said, "At the time, I could skip the meeting."', 'Mira said, "I skipped the meeting."'))
    w = CognitionWorkspace()
    w.put_source('authored-c02-scene', source)
    before = prepare_explanations(w, 'Why did Mira skip the meeting?', source_id='authored-c02-scene')
    assert sum(r['disposition'] == 'CONDITIONALLY_SUPPORTED' for r in before.payload['explanations']) == 2
    original_messages = before.messages(w)
    w.put_source('authored-c02-scene', source.replace('I knew about', 'I did not know about'))
    after = prepare_explanations(w, 'Why did Mira skip the meeting?', source_id='authored-c02-scene')
    assert all(r['disposition'] == 'WEAKENED_BY_COUNTEREVIDENCE' for r in after.payload['explanations'][:2])
    assert after.payload['explanations'][2]['disposition'] == 'CONDITIONALLY_SUPPORTED'
    assert after.payload['winning_motive'] == 'NOT_INFERRED'
    return dict(schema='hcl-c02-positive-witness-v1',
        capability_delta='Two source-supported goal-directed explanations coexist; explicit action-time ignorance weakens both knowledge-dependent candidates without proving the remaining conditional explanation or a unique motive.',
        original_source=source, before_actual_final_messages=original_messages, after_actual_final_messages=after.messages(w),
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED', activation='OPT_IN',
        provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_C02_WITNESS.json')
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(target)
