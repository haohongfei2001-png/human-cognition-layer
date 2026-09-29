"""H05 difficult and simple routes with a local source correction."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hcl.cognition.hard_cognition import HardCognitionSession
from tests.test_v1_wave_h03 import SOURCE, CORRECTED, QUERY
from tests.test_v1_wave_h05 import STAMP, LATER, LEFT, RIGHT, DIRECT


def witness():
    session = HardCognitionSession()
    for source_id, text in [('case', SOURCE), ('chapter-a', LEFT), ('chapter-b', RIGHT)]:
        session.put_chapter(source_id, text, branch='main', recorded_at=STAMP,
            permitted_observers=('Analyst',))
    kwargs = dict(actor='Mira', case_source_id='case', branch='main',
        story_through='2026-01-05', disclosed_through='2026-01-05',
        known_at=STAMP, observer='Analyst')
    direct = session.prepare(DIRECT, **kwargs)
    old = session.prepare(QUERY, **kwargs)
    old_input = old.messages(session)
    session.put_chapter('case', CORRECTED, branch='main', recorded_at=LATER,
        permitted_observers=('Analyst',))
    new = session.prepare(QUERY, **dict(kwargs, known_at=LATER))
    new_input = new.messages(session)
    assert direct.payload['operations'] == ['H01_DIRECT_SOURCE']
    assert old.payload['cross_source_assessment']['relevant_conflicts']
    assert new.payload['revision_delta']['leading_explanation_before'] != new.payload['revision_delta']['leading_explanation_after']
    assert new.payload['revision_delta']['narrative_conflicts_before'] == new.payload['revision_delta']['narrative_conflicts_after']
    assert old.messages(session) == old_input
    return dict(schema='hcl-h05-positive-witness-v1',
        capability_delta='One difficult ordinary question selects an audited belief-plan-expectation-relationship chain plus independently scoped multi-chapter counterreports; source correction changes the case-file conclusion, preserves the historical view, and leaves conflicting narrative reports distinct. A simple question takes the direct route.',
        ordinary_question=QUERY, ordinary_direct_question=DIRECT,
        case_file_before=SOURCE, case_file_after=CORRECTED,
        narrative_sources=[LEFT, RIGHT],
        direct=direct.payload, before=old.payload, after=new.payload,
        actual_direct_model_input=direct.messages(session),
        actual_model_input_before=old_input, actual_final_model_input=new_input,
        implementation='CORRECTNESS_VERIFIED', ordinary_input='REPLAY_VERIFIED',
        efficacy='UNTESTED', activation='OPT_IN', provider_calls=0,
        provider_spend_usd=0, longmemeval='SEALED_NOT_ACCESSED')


if __name__ == '__main__':
    target = Path(sys.argv[1] if len(sys.argv) > 1 else 'reports/HCL_WAVE_H05_WITNESS.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(witness(), ensure_ascii=False, separators=(',', ':')) + '\n')
