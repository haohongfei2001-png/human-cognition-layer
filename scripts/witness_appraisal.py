"""C04 mixed goals/feelings and source-anchored reappraisal."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace
from hcl.cognition.appraisal import prepare_appraisal


def witness():
    source = '\n'.join(('Mira said, "I want to rest."', 'Mira said, "I want to finish the report."',
        'Mira said, "The delay helps my goal to rest."',
        'Mira said, "The delay hinders my goal to finish the report."',
        'Mira said, "I feel relieved and worried about the delay."',
        'Mira said, "About the delay, I feel in control."',
        'Mira said, "About the delay, I am uncertain about the outcome."'))
    w = CognitionWorkspace()
    w.put_source('authored-c04-scene', source)
    before = prepare_appraisal(w, 'How does Mira appraise the delay?', source_id='authored-c04-scene')
    assert before.payload['appraisal']['goal_congruence'] == 'MIXED_GOAL_CONGRUENCE'
    assert before.payload['appraisal']['reported_emotions'] == ['relieved', 'worried']
    original_messages = before.messages(w)
    revised_source = source + '\nMira said, "I now see the delay as harmful for my goal to rest."'
    w.put_source('authored-c04-scene', revised_source)
    revised = prepare_appraisal(w, 'How does Mira appraise the delay?', source_id='authored-c04-scene')
    assert revised.payload['appraisal']['goal_congruence'] == 'HINDERS_EVIDENCED_GOALS'
    assert len(revised.payload['retained_v08']['historical_evidence']) == 1
    revised_messages = revised.messages(w)
    # An independent source correction checks current goal relevance; this does
    # not assert the character retracted the separately reported feeling.
    w.put_source('authored-c04-scene', source + '\nMira said, "I abandoned my goal to finish the report."')
    goals_changed = prepare_appraisal(w, 'How does Mira appraise the delay?', source_id='authored-c04-scene')
    assert goals_changed.payload['appraisal']['goal_congruence'] == 'SUPPORTS_EVIDENCED_GOALS'
    assert goals_changed.payload['appraisal']['reported_emotions'] == ['relieved', 'worried']
    return dict(schema='hcl-c04-positive-witness-v1',
        capability_delta='The same episode supports one goal and hinders another; explicit reappraisal retires only its matching prior report, while a changed goal set updates conditional relevance without erasing reported mixed feelings or inferring actual emotion.',
        original_source=source, before_actual_final_messages=original_messages,
        reappraisal_actual_final_messages=revised_messages, goal_revision_actual_final_messages=goals_changed.messages(w),
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED', activation='OPT_IN',
        provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_C04_WITNESS.json')
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(target)
