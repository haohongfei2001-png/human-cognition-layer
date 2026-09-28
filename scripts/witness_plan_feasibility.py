"""C03 reported-belief/model divergence, belief revision and plan replacement."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition import CognitionWorkspace
from hcl.cognition.plan_feasibility import prepare_plan_feasibility


def witness():
    source = '\n'.join(('Mira said, "I want to reach shelter."',
        'Mira said, "I plan to cross the bridge in order to reach shelter if the gate is open."',
        'Mira said, "I have an opportunity to cross the bridge."', 'Mira said, "I believe the gate is open."',
        'Narrator: In the declared model, it is false that the gate is open.'))
    w = CognitionWorkspace()
    w.put_source('authored-c03-scene', source)
    query = "Could Mira's plans work under their beliefs and the declared model?"
    before = prepare_plan_feasibility(w, query, source_id='authored-c03-scene')
    assert before.payload['plans'][0]['subjective_feasibility'] == 'SUPPORTED_UNDER_REPORTED_BELIEFS'
    assert before.payload['plans'][0]['model_condition_check'] == 'MODEL_CONDITION_CONTRADICTED'
    original_messages = before.messages(w)
    source += '\nMira said, "I now believe it is false that the gate is open instead of the gate is open."'
    w.put_source('authored-c03-scene', source)
    revised = prepare_plan_feasibility(w, query, source_id='authored-c03-scene')
    assert revised.payload['plans'][0]['subjective_feasibility'] == 'CONTRADICTED_UNDER_REPORTED_BELIEFS'
    revised_messages = revised.messages(w)
    source += '\n' + '\n'.join(('Mira said, "I abandoned the plan to cross the bridge."',
        'Mira said, "I plan to take the trail in order to reach shelter if the trail is clear."',
        'Mira said, "I have an opportunity to take the trail."', 'Mira said, "I believe the trail is clear."',
        'Narrator: In the declared model, it is true that the trail is clear.'))
    w.put_source('authored-c03-scene', source)
    after = prepare_plan_feasibility(w, query, source_id='authored-c03-scene')
    plans = {p['action']: p for p in after.payload['plans']}
    assert plans['cross the bridge']['subjective_feasibility'] == 'NOT_CURRENTLY_PURSUED'
    assert plans['take the trail']['subjective_feasibility'] == 'SUPPORTED_UNDER_REPORTED_BELIEFS'
    assert all(p['goal_status'] == 'ACTIVE' and p['values_change'] == 'NOT_INFERRED' for p in plans.values())
    return dict(schema='hcl-c03-positive-witness-v1',
        capability_delta='A plan can be supported under reported belief while its declared-model condition fails; explicit belief revision changes the dependent check, and an explicit replacement plan preserves the goal without inferring a value change.',
        final_source=source, before_actual_final_messages=original_messages,
        belief_revision_actual_final_messages=revised_messages, plan_revision_actual_final_messages=after.messages(w),
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED', activation='OPT_IN',
        provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_C03_WITNESS.json')
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(target)
