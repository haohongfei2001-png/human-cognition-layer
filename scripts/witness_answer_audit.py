"""H04 source-first conditional answer and bounded closure witness."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition.answer_audit import AnswerAuditWorkspace
from tests.test_v1_wave_h03 import SOURCE, CORRECTED, QUERY


def witness():
    workspace = AnswerAuditWorkspace()
    workspace.put_source('team-scene', SOURCE)
    before = workspace.prepare_audited_answer(QUERY, source_id='team-scene')
    old_input = before.messages(workspace)
    old_draft = before.draft(workspace)
    workspace.revise_source('team-scene', CORRECTED,
        kind='ANALYST_SOURCE_CORRECTION')
    after = workspace.prepare_audited_answer(QUERY, source_id='team-scene')
    final_input = after.messages(workspace)
    assert before.payload['best_recorded_explanation']['hypotheses'] == ['INFORMATION_GAP']
    assert after.payload['best_recorded_explanation']['status'] == 'NO_SUPPORTED_RECORDED_EXPLANATION'
    assert before.payload['decisive_counterevidence'][0]['hypothesis'] == 'INFORMED_CONTROLLABLE_STATED_CHOICE'
    assert after.payload['decisive_counterevidence'][0]['hypothesis'] == 'INFORMATION_GAP'
    assert before.payload['conditional_conclusion']['reported_regard'] == after.payload['conditional_conclusion']['reported_regard']
    return dict(schema='hcl-h04-positive-witness-v1',
        capability_delta='The same source correction now changes a bounded, source-quoted answer audit: the most supported recorded conditional explanation loses support, its decisive counterevidence is exposed, unresolved alternatives and unchanged reported regard remain separate.',
        ordinary_source_before=SOURCE, ordinary_source_after=CORRECTED,
        ordinary_question=QUERY, before=before.payload, after=after.payload,
        conditional_draft_before=old_draft, conditional_draft_after=after.draft(workspace),
        actual_model_input_before=old_input, actual_final_model_input=final_input,
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0,
        provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_H04_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, separators=(',', ':')) + '\n')
