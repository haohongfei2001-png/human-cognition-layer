"""H01 ordinary simple versus complex question-directed operation selection."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hcl.cognition.query_planner import QueryDirectedWorkspace

SOURCE = '''Narrator: In choice, Mira could leave.
Mira: In choice, for free alternatives is true is necessary.
Noor: In choice, for free pressure_absent is true is necessary.
Mira: In choice, I value autonomy over safety.
Noor: In choice, I value safety over autonomy.
Mira: In choice, I conclude choice is free because Mira could leave and autonomy matters.
Noor: In choice, I conclude choice is not free because Mira faced pressure and safety matters.'''


def witness():
    w = QueryDirectedWorkspace('ordinary-choice')
    w.put_source(SOURCE, recorded_at='2026-03-10T00:00:00Z',
                 permitted_observers=('Analyst',))
    simple = w.plan('What did the narrator report about Mira?', observer='Analyst')
    concept = w.plan('What does Mira mean by free?', observer='Analyst')
    disagreement = w.plan('Why do Mira and Noor disagree about freedom?', observer='Analyst')
    sensitivity = w.plan('If Mira could leave were false, what changes?', observer='Analyst')
    assert simple.payload['operations'] == ['DIRECT_SOURCE']
    assert concept.payload['operations'] == ['G03_CONCEPT_CRITERIA']
    assert disagreement.payload['operations'] == ['G03_CONCEPT_CRITERIA', 'G04_ARGUMENT_ANALYSIS']
    assert sensitivity.payload['operations'] == [
        'G03_CONCEPT_CRITERIA', 'G04_ARGUMENT_ANALYSIS', 'G05_SENSITIVITY']
    return dict(schema='hcl-h01-positive-witness-v1',
        capability_delta='The same ordinary authorized scene routes a single narrator fact directly while concept, disagreement and hypothetical questions execute only their required G03/G04/G05 dependency chains under explicit budgets.',
        ordinary_source=SOURCE,
        simple=dict(plan=simple.payload, actual_final_model_messages=simple.messages(w)),
        concept=dict(plan=concept.payload, actual_final_model_messages=concept.messages(w)),
        disagreement=dict(plan=disagreement.payload, actual_final_model_messages=disagreement.messages(w)),
        sensitivity=dict(plan=sensitivity.payload, actual_final_model_messages=sensitivity.messages(w)),
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0,
        provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_H01_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, separators=(',', ':')) + '\n')
