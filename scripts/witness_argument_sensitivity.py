"""G05 ordinary three-way sensitivity without mutating source evidence."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hcl.cognition.argument_sensitivity import ArgumentSensitivityWorkspace

SOURCE = '''Narrator: In choice, Mira could leave.
Mira: In choice, for free alternatives is true is necessary.
Noor: In choice, for free pressure_absent is true is necessary.
Mira: In choice, I value autonomy over safety.
Noor: In choice, I value safety over autonomy.
Mira: In choice, I conclude choice is free because Mira could leave and autonomy matters.
Noor: In choice, I conclude choice is not free because Mira faced pressure and safety matters.'''
QUESTION = '''If Mira could leave were false, what changes?
If Mira used Noor's reading of free, what changes?
If Mira valued safety over autonomy instead, what changes?'''


def witness():
    w = ArgumentSensitivityWorkspace('ordinary-choice')
    w.put_source(SOURCE, recorded_at='2026-02-10T00:00:00Z',
                 permitted_observers=('Analyst',))
    prepared = w.compare(QUESTION, observer='Analyst')
    view = prepared.payload
    assert [v['comparisons'][0]['sensitivity'] for v in view['variants']] == [
        'SUPPORT_REMOVED_UNDER_ASSUMPTION', 'READING_CHANGED_CONCLUSION_UNRESOLVED',
        'VALUE_PREMISE_CHANGED_CONCLUSION_UNRESOLVED']
    assert all(v['comparisons'][1]['sensitivity'] == 'STRUCTURALLY_UNAFFECTED_BY_THIS_VARIANT'
               for v in view['variants'])
    return dict(schema='hcl-g05-positive-witness-v1',
        capability_delta='Three ordinary one-factor hypotheticals independently expose a fact-support loss, a local concept-reading change and an explicit value-premise change while preserving the other argument path and original source.',
        ordinary_source=SOURCE, ordinary_question=QUESTION, comparison=view,
        actual_final_model_messages=prepared.messages(w),
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0,
        provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_G05_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
