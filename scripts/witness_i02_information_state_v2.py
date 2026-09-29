"""Provider-free ordinary source and fair ablation witness after I02 repair."""
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hcl.v1 import CognitionRequest, HCLCognitionLayer
from hcl.v1.router import CognitionRouter
from scripts.serious_eval_contract import runtime_digest


SOURCE = ("Carefully lifting Bea's box, Kai sets it on the table. "
          'At the table, he glimpses a key among the papers. '
          'Bea moved the key to the drawer.')
QUESTION = 'Where would Kai look for the key?'


def witness():
    request = CognitionRequest(QUESTION, narrative=SOURCE)
    model = lambda _: ''
    h = HCLCognitionLayer(model).prepare(request)
    hnew = HCLCognitionLayer(model,
        router=CognitionRouter(information_state_enabled=False)).prepare(request)
    h_input = json.loads(h.messages[-1]['content'])
    hnew_input = json.loads(hnew.messages[-1]['content'])
    state = h_input['cognition_context']['information_state']
    assert state['checked_observation_count'] == 1
    observation = state['last_reported_observation']
    assert observation['location'] == 'table'
    assert SOURCE[observation['source_start']:observation['source_end']] == observation['source_quote']
    assert state['source_movements'][0]['location'] == 'drawer'
    assert h_input['query'] == hnew_input['query'] == QUESTION
    assert h_input['narrative'] == hnew_input['narrative'] == SOURCE
    assert {k: v for k, v in h_input['cognition_context'].items()
            if k != 'information_state'} == hnew_input['cognition_context']
    assert set(h.plan.capabilities) - set(hnew.plan.capabilities) == {'information_state'}
    assert h.messages != hnew.messages
    return dict(schema='hcl-i02-information-state-v2-witness',
        capability_delta='adjacent unique subject pronoun and ordinary glimpse enter actor-local source-checked information state',
        input_source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        h_actual_final_messages=h.messages,
        hnew_actual_final_messages=hnew.messages,
        h_capabilities=list(h.plan.capabilities),
        hnew_capabilities=list(hnew.plan.capabilities),
        checked_observation=observation,
        source_movements=state['source_movements'],
        source_quote_span_valid=True,
        no_private_belief_or_future_search_assertion=True,
        runtime_sha256=runtime_digest(),
        provider_calls=0, provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED',
        evidence_class='HCL_AUTHORED_PROVIDER_FREE_CORRECTNESS_NOT_INDEPENDENT_EFFICACY')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(), ensure_ascii=False,
        indent=2, sort_keys=True) + '\n')
