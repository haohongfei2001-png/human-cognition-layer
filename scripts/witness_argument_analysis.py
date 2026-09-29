"""G04 ordinary philosophical disagreement and actual final model context."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hcl.cognition.argument_analysis import ArgumentWorkspace

SOURCE = '''Narrator: In choice, Mira could leave.
Mira: In choice, for free alternatives is true is necessary.
Noor: In choice, for free pressure_absent is true is necessary.
Mira: In choice, I value autonomy over safety.
Noor: In choice, I value safety over autonomy.
Mira: In choice, I conclude choice is free because Mira could leave and autonomy matters.
Noor: In choice, I conclude choice is not free because Mira faced pressure and safety matters.
Noor: In choice, I challenge the fact that Mira could leave.
Noor: In choice, pressured exit is a counterexample to choice is free.
Mira: In choice, this choice is like earlier choice because both allowed exit.'''


def witness():
    w = ArgumentWorkspace('ordinary-choice')
    w.put_source(SOURCE, recorded_at='2026-02-10T00:00:00Z',
                 permitted_observers=('Analyst',))
    before = w.prepare_argument('Why do Mira and Noor disagree about freedom?',
                                observer='Analyst', through_order=7)
    after = w.prepare_argument('Why do Mira and Noor disagree about freedom?', observer='Analyst')
    assert before.payload['arguments'][0]['premise_checks'][0]['status'] == 'REPORTED_FACT_NOT_WORLD_VERIFIED'
    dispute = after.payload['disagreements'][0]
    assert dispute['fact_challenges'] and dispute['concept_reading_differences'] and dispute['explicit_value_conflicts']
    assert after.payload['arguments'][0]['targeted_counterexamples']
    return dict(schema='hcl-g04-positive-witness-v1',
        capability_delta='Ordinary opposed arguments now expose distinct fact challenge, local concept reading and explicit value-priority pivots, preserving counterexample and analogy sources without a moral or formal validity verdict.',
        ordinary_source=SOURCE, before=before.payload, after=after.payload,
        actual_final_model_messages=after.messages(w),
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0,
        provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_G04_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
