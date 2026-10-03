"""Synthetic provider-free G03 dispatch and invalidation witness; no live model port."""
import argparse
import json
from pathlib import Path

from hcl.cognition import UniversalHCL
from hcl.cognition.universal_entry import CallAllowance
from scripts.development_d01_source_line_amendment import validate_current

SOURCE = '''Mira: In team, for fair consent is true is necessary.
Mira: In team, for fair transparency is true is typical.
Noor: In team, for fair transparency is true is sufficient.
Narrator: In team, proposal has consent false.
Narrator: In team, proposal has transparency true.
Mira: In team, proposal is fair.'''
QUESTION = 'Compare the local readings of fair without assuming a shared meaning or moral truth.'


class ScriptedPort:
    provider_free=True
    def reservation_usd(self,phase,messages):return '0'
    def complete(self,phase,messages):
        if phase=='planning':
            value=dict(task='Compare source-local concept readings',operations=[dict(
                capability='G03',question='Compare the reported uses of fair.',
                source_ids=['scene'],bindings=[])],limitations=['SCRIPTED_SELECTION_NOT_MODEL_PLANNING_EVIDENCE'])
        else:
            value=dict(answer='The supplied criteria differ; the local readings do not establish moral truth.',
                source_citations=[],uncertainty='Synthetic interface witness, not evaluated model analysis.',
                assumptions='Source-local reports are conditional.')
        return dict(text=json.dumps(value),actual_usd='0',usage={})


def witness():
    validate_current()
    session=UniversalHCL();session.put_source('scene',SOURCE);port=ScriptedPort()
    before=session.answer(QUESTION,planner_backend=port,answer_backend=port,
        allowance=CallAllowance(2,0,'SYNTHETIC_PROVIDER_FREE_WITNESS'))
    operation=before['operations'][0]
    necessary=next(row for row in operation['result']['readings'] if row['kind']=='NECESSARY')
    assert before['status']=='ANSWERED_WITH_EXPLICIT_LIMITS' and before['provider_calls']==0
    assert necessary['conditional_result']=='REFUTED_BY_SOURCE_CLAIM'
    assert necessary['source_reported_counterexample']
    assert operation['active_criterion_count']==3 and not operation['semantic_certification']
    claim=operation['support_claim_ids'][0]
    assert session.workspace.core.support_statuses()[claim]=='SUPPORT_AVAILABLE'
    session.put_source('scene',SOURCE.replace('consent false','consent true'))
    old_status=session.workspace.core.support_statuses()[claim]
    assert old_status=='UNSUPPORTED'
    after=session.answer(QUESTION,planner_backend=port,answer_backend=port,
        allowance=CallAllowance(2,0,'SYNTHETIC_PROVIDER_FREE_WITNESS'))
    updated=after['operations'][0]
    assert updated['result']['source_version']==2
    assert next(row for row in updated['result']['readings'] if row['kind']=='NECESSARY')['conditional_result']=='NOT_REFUTED'
    assert after['provider_calls']==0 and after['status']=='ANSWERED_WITH_EXPLICIT_LIMITS'
    return dict(schema='hcl-universal-concept-witness-v1',before=before,after=after,
        previous_result_support_after_correction=old_status,
        model_planning='SCRIPTED_NOT_VERIFIED',semantic_certification=False,
        complete_capability_integration=False,provider_calls=0,provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.write_text(json.dumps(witness(),indent=2,ensure_ascii=False)+'\n')
