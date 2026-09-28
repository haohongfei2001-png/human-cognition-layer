"""B05 real cross-operation access revision from ordinary narrative."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition.integrated_scene import IntegratedScene
from hcl.v1 import NarrativePremise, FactorRequirement, ResponsibilityFactor

SOURCE = '\n'.join(('Mira said, "In team, by fair I mean consent is true."',
    "Narrator: Noor missed Mira's last statement.", 'Narrator: In team, proposal has consent false.',
    'Narrator: Mira and Noor read the previous statement.',
    'Noor said, "I believe Mira believes the gate is open."',
    'Mira said, "I do not believe the gate is open."', "Narrator: Noor missed Mira's last statement.",
    'Mira said, "At the time I could not control the opening."', "Narrator: Noor missed Mira's last statement.",
    'Mira said, "I opened the gate."', "Narrator: Noor heard Mira's last statement.",
    'Narrator: The animals escaped.', 'Narrator: Mira and Noor read the previous statement.',
    'Narrator: Mira opening the gate caused the animals to escape.', 'Narrator: Mira and Noor read the previous statement.',
    'Kai said, "I believe the road is safe."'))
QUERIES = ('What does Noor think Mira believes?', "Interpret Mira's meaning of fair for proposal in team.",
    "Explain Mira's conditional responsibility.")


def witness():
    scene = IntegratedScene(SOURCE, source_id='authored-b05-scene')
    rule = NarrativePremise('control-rule', 'For this analysis control is required.',
        (FactorRequirement(ResponsibilityFactor.CONTROL, True),))
    before = scene.prepare('Noor', QUERIES, responsibility_premises=(rule,))
    mira = scene.prepare('Mira', QUERIES[1:], responsibility_premises=(rule,))
    kai = scene.prepare('Kai', ('What does Kai believe?',))
    originals = {r.observer: r.current_messages(scene) for r in (before, mira, kai)}
    changed = scene.update(SOURCE.replace('Noor missed', 'Noor heard'))
    assert changed == ('Noor',)
    after = scene.prepare('Noor', QUERIES, responsibility_premises=(rule,))
    assert scene.prepare('Mira', QUERIES[1:], responsibility_premises=(rule,)) is mira
    assert scene.prepare('Kai', ('What does Kai believe?',)) is kai
    assert mira.current_messages(scene) == originals['Mira']
    assert kai.current_messages(scene) == originals['Kai']
    new = json.loads(after.current_messages(scene)[-1]['content'])
    assert new['operations'][0]['cognitive_state']['comparisons'][0]['relation'] == 'DIFFERS_FROM_SUBJECT_REPORT'
    assert new['operations'][1]['cognitive_state']['cognition_context']['concepts']['checked']['readings'][0]['state'] == 'CRITERIA_NOT_MET'
    resp = new['operations'][2]['cognitive_state']['cognition_context']['responsibility']['checked']
    assert resp['premise_assessments'][0]['result'] == 'CONDITIONALLY_NOT_SUPPORTED'
    calls = []
    answer = scene.answer('Noor', QUERIES, lambda messages: calls.append(messages) or 'authored adapter smoke', responsibility_premises=(rule,))
    assert calls == [after.current_messages(scene)]
    return dict(schema='hcl-b05-positive-witness-v1',
        capability_delta='Only Noor access corrections change the visible nested-attribution comparison, concept criterion check and conditional control-premise result; Mira and Kai preserve actual inputs without reexecution.',
        original_source=SOURCE, changed_observers=list(changed), before_actual_final_messages=originals,
        after_noor_actual_final_messages=after.current_messages(scene), executions=scene.executions,
        final_adapter_calls=answer['answer_adapter_calls'], final_adapter_kind='LOCAL_AUTHORED_SMOKE_NOT_PROVIDER',
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED', efficacy='UNTESTED', activation='OPT_IN',
        provider_calls=0, provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('reports/HCL_WAVE_B05_WITNESS.json')
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print(target)
