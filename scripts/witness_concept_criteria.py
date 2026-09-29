"""G03 ordinary source to conditional concept readings and final model input."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hcl.cognition import ConceptCriteriaWorkspace

SOURCE = '''Mira: In team, for fair consent is true is necessary.
Mira: In team, for fair transparency is true is typical.
Noor: In team, for fair transparency is true is sufficient.
Narrator: In team, proposal has consent false.
Narrator: In team, proposal has transparency true.
Mira: In team, proposal is fair.
Mira: In team, I now use fair with consent is true as sufficient instead of consent is true as necessary.
Narrator: In team, proposal has consent true.
Mira: In team, proposal is not fair.'''


def witness():
    workspace = ConceptCriteriaWorkspace('ordinary-scene')
    workspace.put_source(SOURCE, recorded_at='2026-01-10T00:00:00Z',
                         permitted_observers=('Analyst',), event_time='2026-01-01T00:00:00Z')
    before = workspace.prepare('How does Mira apply fair to the proposal?', observer='Analyst',
                               through_order=6)
    after = workspace.prepare('How does Mira now apply fair to the proposal?', observer='Analyst')
    earlier = next(r for r in before.payload['readings'] if r['actor'] == 'Mira' and r['kind'] == 'NECESSARY')
    later = next(r for r in after.payload['readings'] if r['actor'] == 'Mira' and r['kind'] == 'SUFFICIENT')
    assert earlier['conditional_result'] == 'REFUTED_BY_SOURCE_CLAIM'
    assert earlier['source_reported_counterexample']
    assert later['conditional_result'] == 'NOT_ESTABLISHED'
    assert before.payload['source_version'] == after.payload['source_version']
    return dict(schema='hcl-g03-positive-witness-v1',
        capability_delta='Ordinary source text now supports source-local necessary, sufficient and typical concept criteria, explicit counterexamples and non-retroactive revision, with actor and context boundaries.',
        ordinary_source=SOURCE, before=before.payload, after=after.payload,
        actual_final_model_messages=after.messages(workspace),
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0, provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_G03_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
