"""Authored nonliteral input reaches real checks only under visible hypotheses."""
import argparse
import hashlib
import json
from pathlib import Path
from hcl.cognition import CognitionWorkspace
from scripts.serious_eval_contract import runtime_digest

SOURCE_LINES = ('Dana expressed a desire to protect the gate.',
    'Dana described a conditional plan to call Noor to protect the gate, provided the gate was clear.',
    'Dana reported having the opportunity to call Noor.',
    'Dana expressed confidence that the gate was clear.',
    'The story explicitly stipulated a fictional model in which the gate was not clear.')
DERIVED_LINES = ('Dana: I want to protect the gate.',
    'Dana: I plan to call Noor in order to protect the gate if the gate is clear.',
    'Dana: I have an opportunity to call Noor.',
    'Dana: I believe the gate is clear.',
    'Narrator: In the declared model, it is false that the gate is clear.')
QUERY = 'Which actions are supported and what limits remain?'

class AuthoredBackend:
    """Correctness fixture, never a real model extraction or semantic-quality proof."""
    def __init__(self, rows): self.rows, self.calls = rows, []
    def complete_json(self, messages, **kwargs):
        self.calls.append(dict(messages=messages, parameters=kwargs))
        return json.dumps(dict(candidates=self.rows))

def witness():
    original = '\n'.join(SOURCE_LINES)
    rows = [dict(source_id='meeting', quote=q, kind='event', content=dict(canonical_statement=d))
        for q,d in zip(SOURCE_LINES,DERIVED_LINES)]
    w = CognitionWorkspace(); w.put_source('meeting', original)
    backend = AuthoredBackend(rows)
    before = w.prepare_reader_semantic(QUERY, source_ids=('meeting',), backend=backend)
    p = json.loads(before.messages[-1]['content'])
    plan = p['conditional_cognition']['state']['checked_plan_feasibility'][0]['plans'][0]
    assert plan['subjective_feasibility'] == 'SUPPORTED_UNDER_REPORTED_BELIEFS'
    assert plan['model_condition_check'] == 'MODEL_CONDITION_CONTRADICTED'
    assert plan['deliberate_impossibility'] == 'NOT_INFERRED'
    assert len(before.scope.assumptions) == 5
    assert p['shared_semantic_binding']['original_sources'][0]['text'] == original
    assert before.receipt['checked_treatment_present'] and not before.receipt['semantic_certification']
    correction = 'Dana explicitly corrected the report: the gate was not clear rather than clear.'
    revised_source = original + '\n' + correction
    revised_rows = rows + [dict(source_id='meeting', quote=correction, kind='event',
        content=dict(canonical_statement='Dana: I now believe it is false that the gate is clear instead of the gate is clear.'))]
    invalidated = w.put_source('meeting', revised_source)
    assert set(before.operation_ids) <= invalidated
    try: before.current_messages(w)
    except ValueError: stale_blocked = True
    else: raise AssertionError('stale answer revived')
    final_calls = []; revised_backend = AuthoredBackend(revised_rows)
    answered = w.answer_reader_semantic(QUERY, lambda m: final_calls.append(m) or json.dumps(dict(answer='Conditional source report.',source_citations=[SOURCE_LINES[0]],uncertainty='Unverified translations.',assumptions='No private/world truth.')),
        source_ids=('meeting',), backend=revised_backend)
    after = answered['prepared']
    plan_after = json.loads(after.messages[-1]['content'])['conditional_cognition']['state']['checked_plan_feasibility'][0]['plans'][0]
    assert plan_after['subjective_feasibility'] == 'CONTRADICTED_UNDER_REPORTED_BELIEFS'
    assert final_calls == [after.messages] and len(revised_backend.calls) == 1
    return dict(schema='hcl-development-conditional-reader-v15-witness-v1',
        CAPABILITY_DELTA='Ordinary nonliteral source descriptions can enter existing B01/C01/C03 consistency checks through source-anchored, explicitly unverified translations. Actual conditional state enters final input, originals stay whole, and revision invalidates the old chain. No private/world semantic truth is certified.',
        origin='HCL_AUTHORED_PROPOSALS_CORRECTNESS_STUB_NOT_MODEL_EXTRACTION_EFFICACY',
        runtime_sha256=runtime_digest(), before=before.receipt, after=after.receipt,
        initial_original_sha256=hashlib.sha256(original.encode()).hexdigest(),
        revised_original_sha256=hashlib.sha256(revised_source.encode()).hexdigest(),
        invalidated_operation_ids=sorted(invalidated), stale_answer_blocked=stale_blocked,
        checked_treatment_present=True, every_nonliteral_translation_unverified=True,
        positive_witness='NONLITERAL_INPUT_CONDITIONAL_B01_C01_C03_COMPOSITION_AND_REVISION',
        extraction_stub_calls_per_preparation=1, final_stub_calls=1,
        actual_final_messages=final_calls[0], provider_calls=0, provider_spend_usd=0,
        answer_gain_established=False, semantic_certification=False,
        independent_confirmation_qualified=False, longmemeval='SEALED_NOT_ACCESSED')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(), ensure_ascii=False, sort_keys=True, indent=2)+'\n')
    print('CONDITIONAL_NONLITERAL_READER_ACTUAL_TREATMENT_WITNESS_PASS')
