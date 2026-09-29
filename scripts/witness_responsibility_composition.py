"""G02 ordinary two-person source and conditional composition witness."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from hcl.cognition.responsibility_composition import ResponsibilityCompositionWorkspace

QUESTION=('For this analysis, responsibility requires causal contribution and control. '
    'For this analysis, collective responsibility requires each participant to satisfy the individual rule.')
STAMP='2026-01-08T00:00:00Z'


def episode(actor,control=True):
    lines=[f'{actor}: I opened the gate.','Narrator: The animals escaped.',
        f'Narrator: {actor} opening the gate caused the animals to escape.']
    if control:lines.append(f'Narrator: At the time {actor} could have stopped the opening.')
    lines.append(f'{actor}: At the time I could have closed the gate instead of opening the gate.')
    return '\n'.join(lines)


def witness():
    w=ResponsibilityCompositionWorkspace()
    sources={actor:episode(actor) for actor in ('Alice','Bob')}
    for actor,text in sources.items():
        w.put_episode(actor,actor.lower(),text,recorded_at=STAMP,permitted_observers=('Analyst',))
    joint='Narrator: Alice and Bob jointly opened the gate.'
    w.put_joint_report('joint',joint,recorded_at=STAMP,permitted_observers=('Analyst',))
    before=w.prepare(QUESTION,actors=('Alice','Bob'),observer='Analyst')
    assert before.payload['collective']['status']=='CONDITIONALLY_SUPPORTED_ON_REPORTED_JOINT_ACTION_AND_INDIVIDUAL_CLAIMS'
    assert all(next(f for f in r['checked']['factors'] if f['factor']=='STATED_INTENTION')['state']=='UNKNOWN' for r in before.payload['individuals'])
    w.put_episode('Bob','bob',episode('Bob',control=False),recorded_at='2026-01-09T00:00:00Z',permitted_observers=('Analyst',))
    after=w.prepare(QUESTION,actors=('Alice','Bob'),observer='Analyst')
    assert after.payload['collective']['status']=='UNRESOLVED_INDIVIDUAL_FACTORS'
    # The earlier receipt is preserved as historical evidence, but final input
    # must use a fresh preparation after the source correction.
    return dict(schema='hcl-g02-positive-witness-v1',
        capability_delta='Separate actor-level CG03 factors from source-reported alternatives and a separately adopted collective condition; changing Bob control evidence changes only Bob and the conditional group result.',
        ordinary_question=QUESTION,ordinary_sources=sources,joint_source=joint,
        before_correction=before.payload,after_correction=after.payload,
        actual_final_model_messages=after.messages(w),
        implementation='CORRECTNESS_VERIFIED',ordinary_input='REPLAY_VERIFIED',efficacy='UNTESTED',activation='OPT_IN',
        provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    target=Path(sys.argv[1] if len(sys.argv)>1 else 'reports/HCL_WAVE_G02_WITNESS.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n')
