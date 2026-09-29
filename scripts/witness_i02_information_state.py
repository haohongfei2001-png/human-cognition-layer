"""Authored provider-free witness for the general ordinary access repair."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hcl.v1 import CognitionRequest, HCLCognitionLayer
from hcl.v1.router import CognitionRouter
from scripts.serious_eval_contract import runtime_digest

SOURCE = ('Bea put the key in the drawer. '
          'Alice saw Bea put the key in the drawer. '
          'Bea moved the key to the shelf.')
QUESTION = 'Where would Alice look for the key?'


def witness():
    request = CognitionRequest(QUESTION, narrative=SOURCE, target_actor='Alice')
    model = lambda _: ''
    h = HCLCognitionLayer(model).prepare(request)
    h_new = HCLCognitionLayer(model,
        router=CognitionRouter(information_state_enabled=False)).prepare(request)
    h_input = json.loads(h.messages[-1]['content'])
    h_new_input = json.loads(h_new.messages[-1]['content'])
    state = h_input['cognition_context']['information_state']
    assert h_input['narrative'] == SOURCE and h_input['query'] == QUESTION
    assert h_new_input['narrative'] == SOURCE and h_new_input['query'] == QUESTION
    assert state['checked_observation_count'] == 1
    assert state['last_reported_observation']['location'] == 'drawer'
    assert state['later_source_movement_without_observation_evidence']
    assert 'information_state' not in h_new_input['cognition_context']
    assert set(h.plan.capabilities) - set(h_new.plan.capabilities) == {'information_state'}
    assert h.messages != h_new.messages
    return dict(schema='hcl-i02-information-state-provider-free-witness-v1',
        capability_delta='ordinary named observation enters a source-checked actor information view',
        input_source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        question=QUESTION, observation=state['last_reported_observation'],
        later_source_movement_without_observation_evidence=True,
        no_private_belief_or_predicted_search_assertion=True,
        h_capabilities=list(h.plan.capabilities),
        h_new_capabilities=list(h_new.plan.capabilities),
        h_final_messages_sha256=hashlib.sha256(json.dumps(h.messages,
            ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        h_new_final_messages_sha256=hashlib.sha256(json.dumps(h_new.messages,
            ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        amended_hcl_runtime_sha256=runtime_digest(),
        provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED',
        evidence_class='HCL_AUTHORED_PROVIDER_FREE_CORRECTNESS_NOT_INDEPENDENT_EFFICACY')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output')
    args = parser.parse_args()
    receipt = witness()
    if args.output:
        Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False,
            indent=2, sort_keys=True) + '\n')
    else:
        print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
