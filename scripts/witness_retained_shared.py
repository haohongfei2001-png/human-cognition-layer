"""A04-A05 authored end-to-end shared-material witness, no real provider."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace, prepare_retained, answer_retained


def witness():
    w = CognitionWorkspace()
    definition = 'Mira said, "In team, by fair I mean consent is true."'
    condition = 'Narrator: In team, proposal has consent false.'
    belief = 'Mira added, "In team, I believe proposal is fair."'
    query = "Compare Mira's belief and meaning of fair for proposal in team."
    w.put_source('meeting', '\n'.join((definition, condition, belief)))
    before = prepare_retained(w, query, source_ids=('meeting',))
    w.put_source('home', 'Noor said, "In home, I believe dinner is good."')
    noor = prepare_retained(w, 'What does Noor believe?', source_ids=('home',))
    noor_messages = noor.current_messages(w)
    invalidated = w.put_source('meeting', '\n'.join((definition, condition.replace('false', 'true'), belief)))
    calls = []
    answered = answer_retained(w, query, lambda messages: calls.append(messages) or 'source-bounded development stub',
        source_ids=('meeting',))
    after = answered['prepared']
    comparison = lambda r: json.loads(r.messages[-1]['content'])['composed_cognition']['belief_concept_comparison']['rows'][0]
    assert comparison(before)['relation'] == 'DIFFERS_FROM_LOCAL_SOURCE_CRITERIA'
    assert comparison(after)['relation'] == 'CONSISTENT_WITH_LOCAL_SOURCE_CRITERIA'
    assert set(before.operation_ids) <= invalidated
    assert not set(noor.operation_ids) & invalidated
    assert noor.current_messages(w) == noor_messages
    assert calls == [after.messages]
    return dict(schema='hcl-a04-a05-shared-witness-v1',
        capability_delta='Quoted ordinary source material enters retained belief/concept operations; a property revision propagates through the concept checker to the dependent comparison, preserving unrelated Noor.',
        before_comparison=comparison(before), after_comparison=comparison(after),
        before=before.receipt, after=after.receipt, actual_answer_adapter_inputs=calls,
        unrelated_noor_preserved=True, operation_graph=w.core.receipt(after.scope),
        answer_adapter_calls=1, answer_adapter='DEVELOPMENT_STUB_NOT_PROVIDER',
        provider_calls=0, provider_spend_usd=0, implementation='CORRECTNESS_VERIFIED',
        ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED', activation='OPT_IN',
        longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_A04_A05_WITNESS.json')
    path.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(path)
