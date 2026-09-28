"""B01 nested attribution witness; authored, provider-free, not efficacy evidence."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace, prepare_epistemic, Attitude


def witness():
    w = CognitionWorkspace()
    w.put_source('scene', 'Mira said, "I believe Noor believes the gate is open." '
                         'Noor replied, "I do not believe the gate is open."')
    query = 'What does Mira think Noor believes?'
    bundle = prepare_epistemic(w, query, source_ids=('scene',))
    before_messages = bundle.messages(w.core, query)
    comparison = json.loads(before_messages[-1]['content'])['comparisons'][0]
    assert comparison['relation'] == 'DIFFERS_FROM_SUBJECT_REPORT'
    assert bundle.project(w.core, ('Mira', 'Noor'), attitude=Attitude.BELIEF)[0]['result'] == 'SOURCE_REPORTED_AFFIRM'
    assert bundle.project(w.core, ('Noor',), attitude=Attitude.BELIEF)[0]['result'] == 'SOURCE_REPORTED_DENY'
    noor_span = w.core.claims[bundle.records[1].expression_id].content['source_span_id']
    invalidated = w.core.withdraw(noor_span)
    assert comparison['claim_id'] in invalidated
    assert bundle.records[0].expression_id not in invalidated
    after_messages = bundle.messages(w.core, query)
    assert not json.loads(after_messages[-1]['content'])['comparisons']
    return dict(schema='hcl-b01-positive-witness-v1',
        capability_delta='Query-selected nested belief attribution is compared with the subject own report without detachment; withdrawing subject evidence invalidates only the comparison and subject interpretation.',
        before_actual_final_messages=before_messages, after_actual_final_messages=after_messages,
        invalidated=sorted(invalidated), provider_calls=0, provider_spend_usd=0,
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_B01_WITNESS.json')
    path.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(path)
