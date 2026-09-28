"""C05 positive ordinary-input dependency and source-time witness."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition.agency_chain import SemanticWorkspace, prepare_agency_chain

SOURCE = '\n'.join(('Mira said, "I want to attend the concert."',
    'Mira said, "I plan to leave the meeting in order to attend the concert if the train is running."',
    'Mira said, "I have an opportunity to leave the meeting."',
    'Mira said, "I believe the train is running."',
    'Narrator: In the declared model, it is false that the train is running.',
    'Mira said, "At the time, I knew about the meeting."',
    'Mira said, "At the time, I could leave the meeting."',
    'Mira said, "I left the meeting."',
    'Mira said, "The delay hinders my goal to attend the concert."'))
QUERY = 'Why did Mira leave the meeting, considering their plans and appraisal of the delay?'


def witness():
    w = SemanticWorkspace()
    w.put_source('authored-c05-scene', SOURCE)
    before = prepare_agency_chain(w, QUERY, source_id='authored-c05-scene')
    messages = before.messages(w)
    assert before.payload['explanations'][0]['disposition'] == 'CONDITIONALLY_SUPPORTED'
    w.put_source('authored-c05-scene', SOURCE.replace('I believe the train is running.', 'I believe it is false that the train is running.'))
    corrected = prepare_agency_chain(w, QUERY, source_id='authored-c05-scene')
    assert corrected.payload['explanations'][0]['disposition'] == 'WEAKENED_BY_PLAN_COUNTEREVIDENCE'
    assert corrected.payload['appraisal']['reported_emotions'] == []
    correction_messages = corrected.messages(w)
    w.put_source('authored-c05-scene', SOURCE + '\nMira said, "I now believe it is false that the train is running instead of the train is running."')
    later = prepare_agency_chain(w, QUERY, source_id='authored-c05-scene')
    assert later.payload['explanations'][0]['disposition'] == 'CONDITIONALLY_SUPPORTED'
    assert later.payload['current_plans'][0]['subjective_feasibility'] == 'CONTRADICTED_UNDER_REPORTED_BELIEFS'
    return dict(schema='hcl-c05-positive-witness-v1',
        capability_delta='Correcting pre-action belief changes the plan-dependent explanation; a later belief revision changes only current plan checks, without inventing emotion or a unique motive.',
        before_actual_final_messages=messages, corrected_actual_final_messages=correction_messages,
        later_revision_actual_final_messages=later.messages(w),
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED', activation='OPT_IN',
        provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_C05_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
