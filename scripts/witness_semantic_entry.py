"""A02 authored development witness; no provider/corpus access."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace


def witness():
    w = CognitionWorkspace()
    text = ('Mira said, “I believe the door is open.” '
            'Noor replied, “I am unsure whether the door is open.” '
            'She added, “I do not believe the door is open.”')
    w.put_source('conversation', text)
    before = w.prepare_semantic('Who expressed belief or uncertainty about the door?', source_ids=('conversation',))
    first = [w.core.claims[k].content['proposal'] for k in before.candidate_ids
             if w.core.claims[k].content['kind'] == 'proposition']
    assert [p['signal'] for p in first] == ['AFFIRM', 'UNCERTAIN', 'DENY']
    assert first[2]['subject_candidates'] == ['Mira', 'Noor']
    assert first[2]['reference_binding'] == 'UNRESOLVED'
    invalidated = w.put_source('conversation', text.replace('I believe', 'I do not believe', 1))
    assert set(before.candidate_ids) <= invalidated
    after = w.prepare_semantic('Who expressed belief or uncertainty about the door?', source_ids=('conversation',))
    revised = [w.core.claims[k].content['proposal'] for k in after.candidate_ids
               if w.core.claims[k].content['kind'] == 'proposition']
    assert revised[0]['signal'] == 'DENY'
    assert revised[1:] == first[1:]
    return dict(schema='hcl-a02-positive-witness-v1',
        capability_delta='Ordinary reported dialogue resolves explicit first person, preserves pronoun alternatives and revises only the changed expressed stance.',
        before=first, after=revised, actual_final_messages=after.messages,
        diagnostics=after.diagnostics, backend_calls=0, provider_calls=0, provider_spend_usd=0,
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_A02_WITNESS.json')
    path.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(path)
