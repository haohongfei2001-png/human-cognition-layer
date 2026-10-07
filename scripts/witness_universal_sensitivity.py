"""Scripted G05 orchestration with source/request support and explicit refusals."""
import argparse
import json
from pathlib import Path

from hcl.cognition import UniversalHCL
from hcl.cognition.universal_entry import CallAllowance
from scripts.development_semantic_bridge_contract_amendment import validate_current
from scripts.witness_argument_sensitivity import SOURCE, QUESTION


class ScriptedPort:
    provider_free=True
    def reservation_usd(self,phase,messages):return '0'
    def complete(self,phase,messages):
        if phase=='planning':
            value=dict(task='Compare source-local argument sensitivity',operations=[dict(
                capability='G05',question='Compare the three possible changes.',
                source_ids=['scene'],bindings=[])],limitations=['SCRIPTED_SELECTION_NOT_MODEL_PLANNING_EVIDENCE'])
        else:
            value=dict(answer='Conditional sensitivity preserves the source and leaves conclusion truth unresolved.',
                source_citations=[],uncertainty='Synthetic interface witness, not evaluated model analysis.',
                assumptions='Hypotheticals are caller conditions; source reports are not verified world facts.')
        return dict(text=json.dumps(value),actual_usd='0',usage={})


def witness():
    validate_current()
    session=UniversalHCL();session.put_source('scene',SOURCE);port=ScriptedPort()
    def answer(question):
        return session.answer(question,planner_backend=port,answer_backend=port,
            allowance=CallAllowance(2,0,'SYNTHETIC_PROVIDER_FREE_WITNESS'))
    before=answer(QUESTION);operation=before['operations'][0]
    assert before['status']=='ANSWERED_WITH_EXPLICIT_LIMITS' and before['provider_calls']==0
    assert operation['variant_count']==3 and not operation['source_modified']
    variants=operation['result']['variants']
    assert [v['comparisons'][0]['sensitivity'] for v in variants]==[
        'SUPPORT_REMOVED_UNDER_ASSUMPTION','READING_CHANGED_CONCLUSION_UNRESOLVED',
        'VALUE_PREMISE_CHANGED_CONCLUSION_UNRESOLVED']
    assert all(v['comparisons'][1]['sensitivity']=='STRUCTURALLY_UNAFFECTED_BY_THIS_VARIANT' for v in variants)
    assert all(c['conclusion_truth']=='NOT_ESTABLISHED' for v in variants for c in v['comparisons'])
    claim=operation['support_claim_ids'][0];request=operation['request_provenance']['span_id']
    assert session.workspace.core.dependencies[claim]=={tuple(sorted((request,session.workspace._spans['scene'])))}
    session.put_source('scene',SOURCE+'\nNoor: In choice, I challenge the fact that Mira could leave.')
    previous_status=session.workspace.core.support_statuses()[claim]
    assert previous_status=='UNSUPPORTED'
    after=answer(QUESTION);updated=after['operations'][0]
    assert updated['result']['source_version']==2
    assert updated['result']['variants'][0]['comparisons'][0]['sensitivity']=='ALREADY_CONTESTED_REMAINS_UNRESOLVED'
    assert after['status']=='ANSWERED_WITH_EXPLICIT_LIMITS' and after['provider_calls']==0
    session.workspace.core.withdraw(updated['request_provenance']['span_id'])
    request_status=session.workspace.core.support_statuses()[updated['support_claim_ids'][0]]
    assert request_status=='UNSUPPORTED'
    broad=answer('Analyze human society.');rejected=broad['operations'][0]
    assert not rejected['executed'] and rejected['status']=='ADAPTER_REJECTED_NOT_COMPLETED'
    assert broad['provider_calls']==0
    return dict(schema='hcl-universal-sensitivity-witness-v1',before=before,after=after,
        broad_request=broad,previous_result_support_after_correction=previous_status,
        revised_result_support_after_request_withdrawal=request_status,
        model_planning='SCRIPTED_NOT_VERIFIED',semantic_certification=False,
        complete_capability_integration=False,provider_calls=0,provider_spend_usd=0,
        longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.write_text(json.dumps(witness(),indent=2,ensure_ascii=False)+'\n')
