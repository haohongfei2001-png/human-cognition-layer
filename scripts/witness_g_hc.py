"""G-HC integrated three-operation, two-scope correction and budget witness."""
import hashlib
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hcl.cognition.argument_sensitivity import ArgumentSensitivityWorkspace
from hcl.cognition.registry import PACKAGES

SOURCE = '''Narrator: In choice, Mira could leave.
Mira: In choice, for free alternatives is true is necessary.
Noor: In choice, for free pressure_absent is true is necessary.
Mira: In choice, I value autonomy over safety.
Noor: In choice, I value safety over autonomy.
Mira: In choice, I conclude choice is free because Mira could leave and autonomy matters.
Noor: In choice, I conclude choice is not free because Mira faced pressure and safety matters.
Narrator: In work, Noor finished report.
Noor: In work, I conclude task was done because Noor finished report.'''
QUESTION = '''If Mira could leave were false, what changes?
If Mira used Noor's reading of free, what changes?
If Mira valued safety over autonomy instead, what changes?'''


def _state(workspace):
    concept = workspace.prepare('How is free used?', observer='Analyst').payload
    argument = workspace.prepare_argument('Which claims are conditional?', observer='Analyst').payload
    sensitivity = workspace.compare(QUESTION, observer='Analyst')
    work = next(a for a in argument['arguments'] if a['context'] == 'work')
    choice = next(a for a in argument['arguments'] if a['actor'] == 'Mira')
    return dict(concept=concept, argument=argument, sensitivity=sensitivity.payload,
                actual_final_model_messages=sensitivity.messages(workspace),
                unrelated_work_argument=work, focal_choice_argument=choice)


def witness():
    required = {f'{wave}{n:02d}' for wave in 'ABCDEFG' for n in range(1, 6)}
    assert required <= PACKAGES.keys()
    assert all(PACKAGES[k]['implementation'] == 'CORRECTNESS_VERIFIED' for k in required)
    w = ArgumentSensitivityWorkspace('g-hc-scene')
    w.put_source(SOURCE, recorded_at='2026-02-10T00:00:00Z',
                 permitted_observers=('Analyst',))
    before = _state(w)
    corrected = SOURCE.replace('Narrator: In choice, Mira could leave.',
                               'Narrator: In choice, Mira could not leave.')
    w.put_source(corrected, recorded_at='2026-02-11T00:00:00Z',
                 permitted_observers=('Analyst',))
    after = _state(w)
    assert before['focal_choice_argument']['premise_checks'][0]['status'] == 'REPORTED_FACT_NOT_WORLD_VERIFIED'
    assert after['focal_choice_argument']['premise_checks'][0]['status'] == 'UNRESOLVED_PREMISE'
    assert before['sensitivity']['variants'][0]['comparisons'][0]['sensitivity'] == 'SUPPORT_REMOVED_UNDER_ASSUMPTION'
    assert after['sensitivity']['variants'][0]['comparisons'][0]['sensitivity'] == 'UNSUPPORTED_PREMISE_REMAINS_UNRESOLVED'
    assert before['concept']['relations'] == after['concept']['relations']
    assert before['unrelated_work_argument']['premise_checks'][0]['status'] == after['unrelated_work_argument']['premise_checks'][0]['status']
    assert before['unrelated_work_argument']['claim'] == after['unrelated_work_argument']['claim']
    try:
        w.compare(QUESTION, observer='Noor')
    except ValueError:
        denied = True
    else:
        denied = False
    assert denied
    try:
        w.compare(QUESTION, observer='Analyst').messages(w, max_chars=1000)
    except ValueError:
        refused_oversize = True
    else:
        refused_oversize = False
    assert refused_oversize
    return dict(schema='hcl-g-hc-readiness-witness-v1',
        capability_delta='One ordinary authorized scene now composes local concept interpretation, argument-source checking and controlled sensitivity over a source correction; focal support changes while the unrelated work conclusion and concept comparison remain stable.',
        original_source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        corrected_source_sha256=hashlib.sha256(corrected.encode()).hexdigest(),
        original_source=SOURCE, corrected_source=corrected,
        ordinary_question=QUESTION, before=before, after=after,
        checks=dict(a_to_g_registry_count=len(required), multi_operation=True,
                    multi_step_source_revision=True, unrelated_scope_unchanged=True,
                    access_denied=denied, oversize_refused=refused_oversize,
                    live_adapter_efficacy='UNTESTED_NOT_CLAIMED',
                    formal_or_moral_truth='NOT_INFERRED'),
        gate_scope='PROVIDER_FREE_HARD_COGNITION_READINESS_NOT_EFFICACY',
        provider_calls=0, provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_G_HC_READINESS_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, separators=(',', ':')) + '\n')
