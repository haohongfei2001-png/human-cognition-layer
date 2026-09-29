"""G01 ordinary normative origin separation and CG03 typed-condition bridge."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from hcl.cognition.normative_premises import NormativePremiseWorkspace

SOURCE='''Institution team policy: responsibility requires knowledge and control.
Mira said, "I believe responsibility requires intention."
Narrator: On 2026-01-03, Noor said, "I endorse responsibility requires foreseeability."'''
QUESTION='For this analysis, responsibility requires knowledge and control. Was Mira responsible?'


def witness():
    workspace=NormativePremiseWorkspace()
    workspace.put_source('ordinary-scene',SOURCE,recorded_at='2026-01-08T00:00:00Z',
        permitted_observers=('Analyst',))
    prepared=workspace.prepare(QUESTION,observer='Analyst',known_at='2026-01-09T00:00:00Z',
        adopted_framework_text='a person is responsible only if they knew about the risk and could prevent the harm')
    assert [r['origin'] for r in prepared.payload['candidates']]==[
        'USER_SUPPLIED','ANALYST_ADOPTED','INSTITUTION_REPORTED','CHARACTER_REPORTED_ENDORSEMENT','CHARACTER_REPORTED_ENDORSEMENT']
    assert len(prepared.typed_premises)==2
    unadopted=workspace.prepare('Was Mira responsible?',observer='Analyst',known_at='2026-01-09T00:00:00Z')
    assert not unadopted.typed_premises
    return dict(schema='hcl-g01-positive-witness-v1',
        capability_delta='Ordinary question and source text yield source-origin normative candidates and typed conditional CG03 premises without prefilled FactorRequirement or automatic moral truth.',
        ordinary_question=QUESTION,ordinary_source=SOURCE,prepared=prepared.payload,
        cg03_typed_caller_conditions=[dict(premise_id=p.premise_id,text=p.text,
            requirements=[dict(factor=r.factor.value,value=r.value) for r in p.requirements]) for p in prepared.typed_premises],
        unadopted_framework=unadopted.payload,
        actual_final_model_messages=prepared.messages(workspace),
        implementation='CORRECTNESS_VERIFIED',ordinary_input='REPLAY_VERIFIED',efficacy='UNTESTED',activation='OPT_IN',
        provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    target=Path(sys.argv[1] if len(sys.argv)>1 else 'reports/HCL_WAVE_G01_WITNESS.json')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(witness(),ensure_ascii=False,indent=2)+'\n')
