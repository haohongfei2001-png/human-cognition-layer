"""Complete scripted C04-to-C05 composition with action-time/current separation."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from hcl.cognition import UniversalHCL
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort
from hcl.cognition.universal_entry import CallAllowance
from scripts.development_c02_planned_input_amendment import validate_current
from scripts.witness_agency_chain import SOURCE,QUERY

QUESTION='Explain the reported action using its plans and appraisal, without inferring a unique motive.'
ACTION='Mira said, "I left the meeting."'
LATER='Mira said, "I now believe it is false that the train is running instead of the train is running."'


class ScriptedPort:
    provider_free=True
    def __init__(self,overflow=False):
        self.requests={};self.calls=[];self.overflow=overflow
        self.validator=DeepSeekMeteredPort(SimpleNamespace(max_retries=0,
            base_url='https://api.deepseek.com',timeout=60))
    def reservation_usd(self,phase,messages):
        _,encoded=self.validator.request(phase,messages)
        self.requests[phase]=dict(bytes=len(encoded),sha256=hashlib.sha256(encoded).hexdigest())
        return '0'
    def complete(self,phase,messages):
        self.calls.append(phase)
        if phase=='planning':
            chain=dict(capability='C05',question=QUERY,source_ids=['scene'],bindings=[])
            operations=[dict(capability='C04',question='How does Mira appraise the delay?',source_ids=['scene'],bindings=[]),chain]
            if self.overflow:operations.append(dict(chain))
            value=dict(task='Keep action-time reasoning separate from current source state',operations=operations,
                limitations=['SCRIPTED_SELECTION_NOT_MODEL_PLANNING_EVIDENCE'])
        else:
            source=json.loads(messages[-1]['content'])['sources'][0]
            value=dict(answer='The source reports the action; its conditional explanation does not establish a unique motive or actual emotion.',
                source_citations=[dict(source_id=source['source_id'],version=source['version'],
                    quote=ACTION,start=source['text'].index(ACTION))],
                uncertainty='Later belief does not backfill the earlier source prefix.',
                assumptions='Synthetic interface witness; source order is not verified calendar chronology.')
        return dict(text=json.dumps(value),actual_usd='0',usage={})


def witness():
    validate_current();session=UniversalHCL();session.put_source('scene',SOURCE)
    def answer(overflow=False):
        port=ScriptedPort(overflow)
        result=session.answer(QUESTION,planner_backend=port,answer_backend=port,
            allowance=CallAllowance(2,0,'SYNTHETIC_PROVIDER_FREE_WITNESS'))
        assert result['provider_calls']==0
        if not overflow:
            assert result['status']=='ANSWERED_WITH_EXPLICIT_LIMITS'
            assert result['source_review']['deliverable'] and not result['source_review']['semantic_certification']
            final=json.loads(result['actual_final_messages'][-1]['content'])
            assert final['question']==QUESTION and final['sources'][0]['text']==session.sources['scene']['text']
        return result,port
    before,first=answer();appraisal,chain=before['operations']
    assert appraisal['checked_treatment_present'] and chain['checked_treatment_present']
    assert set(appraisal['support_claim_ids'])&set(chain['support_claim_ids'])
    assert chain['result']['explanations'][0]['disposition']=='CONDITIONALLY_SUPPORTED'
    assert chain['result']['current_plans'][0]['model_condition_check']=='MODEL_CONDITION_CONTRADICTED'
    assert chain['result']['appraisal']['reported_emotions']==[]
    old_claims=set(appraisal['support_claim_ids']+chain['support_claim_ids'])
    session.put_source('scene',SOURCE+'\n'+LATER)
    old_status={key:session.workspace.core.support_statuses()[key]for key in old_claims}
    assert set(old_status.values())=={'UNSUPPORTED'}
    after,second=answer();updated=after['operations'][1]['result']
    assert updated['original_sources'][0]['version']==2
    assert updated['current_plans'][0]['subjective_feasibility']=='CONTRADICTED_UNDER_REPORTED_BELIEFS'
    assert updated['explanations'][0]['disposition']=='CONDITIONALLY_SUPPORTED'
    span=session.workspace.core.spans[updated['action_time']['source_span_id']]
    assert span.version==2 and span.quote==(SOURCE+'\n'+LATER)[:updated['action_time']['end']]
    overflow,third=answer(True)
    assert third.calls==['planning'] and overflow['status']=='ORCHESTRATION_UNAVAILABLE_OR_FAILED'
    assert len(overflow['operations'])==3 and all(r['executed']for r in overflow['operations'])
    assert 'answer' not in overflow
    return dict(schema='hcl-universal-agency-chain-witness-v1',before=before,after=after,
        combined_overflow=overflow,complete_request_measurements=dict(before=first.requests,after=second.requests),
        old_support_after_revision=old_status,model_planning='SCRIPTED_NOT_VERIFIED',
        semantic_certification=False,complete_capability_integration=False,provider_calls=0,
        provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.write_text(json.dumps(witness(),indent=2,ensure_ascii=False)+'\n')
