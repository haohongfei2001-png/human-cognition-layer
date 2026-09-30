"""Authored shared source revision -> actual B01/C01/C03 -> one final input."""
import argparse
import hashlib
import json
from pathlib import Path
from hcl.cognition import CognitionWorkspace, ClaimKind
from scripts.serious_eval_contract import runtime_digest

def witness():
    source = '\n\n'.join(('_Dana._ I want to protect the gate.',
        '_Dana._ I plan to call Noor in order to protect the gate if the gate is clear.',
        '_Dana._ I have an opportunity to call Noor.',
        '_Dana._ I believe the gate is clear.',
        'Narrator: In the declared model, it is false that the gate is clear.'))
    query = 'Which actions are supported and what limits remain?'
    w = CognitionWorkspace(); w.put_source('meeting', source)
    before = w.prepare(query, source_ids=('meeting',))
    initial = w.receipt(before)
    body = json.loads(before.messages[-1]['content'])
    assert body['sources'][0]['text'] == source
    plan = body['checked_plan_feasibility'][0]['plans'][0]
    assert plan['subjective_feasibility'] == 'SUPPORTED_UNDER_REPORTED_BELIEFS'
    assert plan['model_condition_check'] == 'MODEL_CONDITION_CONTRADICTED'
    assert plan['deliberate_impossibility'] == 'NOT_INFERRED'
    assert w.core.claims[before.claim_ids[0]].content['state'] == body
    revised_source = source + '\n\n_Dana._ I now believe it is false that the gate is clear instead of the gate is clear.'
    invalidated = w.put_source('meeting', revised_source)
    try: before.current_messages(w)
    except ValueError: stale_blocked = True
    else: raise AssertionError('old state revived')
    after = w.prepare(query, source_ids=('meeting',))
    revised = json.loads(after.messages[-1]['content'])['checked_plan_feasibility'][0]['plans'][0]
    assert revised['subjective_feasibility'] == 'CONTRADICTED_UNDER_REPORTED_BELIEFS'
    calls = []
    answer = w.answer(query, lambda m: calls.append(m) or 'Authored correctness stub.', source_ids=('meeting',))
    assert calls == [after.messages] and answer['preparation_provider_calls'] == 0
    key = after.claim_ids[0]
    challenge = w.core.claim(after.scope, ClaimKind.SYSTEM_INTERPRETATION, {'challenge': 'interpretation disputed'})
    w.core.support(challenge, w._spans['meeting']); w.core.challenge(key, challenge)
    try: w.answer(query, lambda m: calls.append(m), source_ids=('meeting',))
    except ValueError: challenged_blocked = True
    else: raise AssertionError('challenged state answered')
    assert len(calls) == 1 and not w.receipt(after)['current']
    w.core.withdraw(challenge)
    final = w.receipt(after); assert final['current']
    return dict(schema='hcl-development-shared-reader-v14-witness-v1',
        CAPABILITY_DELTA='An ordinary reader question now carries actual existing B01/C01/C03 state through the shared source dependency graph and one final answer call instead of crashing. Source revision changes the conditional plan result; stale or challenged state cannot answer. No new cognition module or private truth.',
        origin='HCL_AUTHORED_SYNTHETIC_DEVELOPMENT_ONLY',
        runtime_sha256=runtime_digest(), initial=initial, revised=final,
        initial_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
        revised_source_sha256=hashlib.sha256(revised_source.encode()).hexdigest(),
        invalidated_claim_ids=sorted(invalidated), stale_answer_blocked=stale_blocked,
        challenged_answer_blocked=challenged_blocked,
        positive_witness='ACTUAL_SHARED_READER_B01_C01_C03_COMPOSITION_AND_REVISION',
        ordinary_input_smoke_calls=1, actual_final_messages=calls[0],
        provider_calls=0, provider_spend_usd=0, answer_gain_established=False,
        independent_confirmation_qualified=False, longmemeval='SEALED_NOT_ACCESSED')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(), ensure_ascii=False, sort_keys=True, indent=2)+'\n')
    print('SHARED_READER_ACTUAL_STATE_REVISION_ONE_CALL_WITNESS_PASS')
