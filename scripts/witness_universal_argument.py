"""Synthetic G04 orchestration, identical-claim regression and invalidation witness."""
import argparse
import json
from pathlib import Path

from hcl.cognition import UniversalHCL
from hcl.cognition.argument_analysis import _opposed
from hcl.cognition.universal_entry import CallAllowance
from scripts.development_a02_structural_scope_amendment import validate_current
from scripts.witness_argument_analysis import SOURCE

QUESTION = 'Map the reported disagreement without choosing a winner or asserting world truth.'


class ScriptedPort:
    provider_free=True
    def reservation_usd(self,phase,messages):return '0'
    def complete(self,phase,messages):
        if phase=='planning':
            value=dict(task='Map source-local arguments',operations=[dict(
                capability='G04',question='Map the reported disagreement.',
                source_ids=['scene'],bindings=[])],limitations=['SCRIPTED_SELECTION_NOT_MODEL_PLANNING_EVIDENCE'])
        else:
            value=dict(answer='The source-local argument map preserves the stated premises and limits.',
                source_citations=[],uncertainty='Synthetic interface witness, not evaluated model analysis.',
                assumptions='Source-reported arguments do not establish world truth or a verdict.')
        return dict(text=json.dumps(value),actual_usd='0',usage={})


def witness():
    validate_current()
    session=UniversalHCL();session.put_source('scene',SOURCE);port=ScriptedPort()
    before=session.answer(QUESTION,planner_backend=port,answer_backend=port,
        allowance=CallAllowance(2,0,'SYNTHETIC_PROVIDER_FREE_WITNESS'))
    operation=before['operations'][0]
    assert before['status']=='ANSWERED_WITH_EXPLICIT_LIMITS' and before['provider_calls']==0
    assert operation['argument_count']==2 and operation['disagreement_count']==1
    disagreement=operation['result']['disagreements'][0]
    assert all(disagreement[key] for key in ('fact_challenges','concept_reading_differences','explicit_value_conflicts'))
    assert disagreement['winner']=='NOT_SELECTED' and not operation['verdict_produced']
    claim=operation['support_claim_ids'][0]
    assert session.workspace.core.support_statuses()[claim]=='SUPPORT_AVAILABLE'
    session.put_source('scene',SOURCE.replace('I conclude choice is not free','I conclude choice is free'))
    old_status=session.workspace.core.support_statuses()[claim]
    assert old_status=='UNSUPPORTED'
    after=session.answer(QUESTION,planner_backend=port,answer_backend=port,
        allowance=CallAllowance(2,0,'SYNTHETIC_PROVIDER_FREE_WITNESS'))
    updated=after['operations'][0]
    assert updated['result']['source_version']==2
    assert updated['argument_count']==2 and updated['disagreement_count']==0
    assert not _opposed('choice is free','choice is free')
    assert _opposed('choice is free','choice is not free')
    assert after['provider_calls']==0 and after['status']=='ANSWERED_WITH_EXPLICIT_LIMITS'
    return dict(schema='hcl-universal-argument-witness-v1',before=before,after=after,
        previous_result_support_after_correction=old_status,
        identical_conclusions_opposed=False,explicit_negation_opposed=True,
        model_planning='SCRIPTED_NOT_VERIFIED',semantic_certification=False,
        complete_capability_integration=False,provider_calls=0,provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.write_text(json.dumps(witness(),indent=2,ensure_ascii=False)+'\n')
