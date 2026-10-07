"""Scripted C04 complete-source delivery, current revisions and exact request bounds."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from hcl.cognition import UniversalHCL
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort
from hcl.cognition.universal_entry import CallAllowance
from scripts.development_planner_lifecycle_amendment import validate_current

QUESTION="How is the delay related to Mira's goals and reported feelings?"
OPERATION_QUESTION='How does Mira appraise the delay?'
FEELING='Mira said, "I feel relieved and worried about the delay."'
SOURCE='\n'.join(('Mira said, "I want to rest."',
    'Mira said, "I want to finish the report."',
    'Mira said, "The delay helps my goal to rest."',
    'Mira said, "The delay hinders my goal to finish the report."',FEELING))


class ScriptedPort:
    provider_free=True
    def __init__(self):
        self.requests={}
        self.validator=DeepSeekMeteredPort(SimpleNamespace(max_retries=0,
            base_url='https://api.deepseek.com',timeout=60))
    def reservation_usd(self,phase,messages):
        _,encoded=self.validator.request(phase,messages)
        self.requests[phase]=dict(bytes=len(encoded),sha256=hashlib.sha256(encoded).hexdigest())
        return '0'
    def complete(self,phase,messages):
        if phase=='planning':
            value=dict(task='Separate reported feelings from goal-linked appraisal',operations=[dict(
                capability='C04',question=OPERATION_QUESTION,source_ids=['scene'],bindings=[])],
                limitations=['SCRIPTED_SELECTION_NOT_MODEL_PLANNING_EVIDENCE'])
        else:
            source=json.loads(messages[-1]['content'])['sources'][0]
            value=dict(answer='Mira reports relief and worry; the source-relative goal appraisal remains conditional.',
                source_citations=[dict(source_id=source['source_id'],version=source['version'],
                    quote=FEELING,start=source['text'].index(FEELING))],
                uncertainty='No actual emotion, control or knowledge is established.',
                assumptions='Synthetic interface witness, not evaluated model analysis.')
        return dict(text=json.dumps(value),actual_usd='0',usage={})


def witness():
    validate_current()
    session=UniversalHCL();session.put_source('scene',SOURCE)
    def answer():
        port=ScriptedPort()
        result=session.answer(QUESTION,planner_backend=port,answer_backend=port,
            allowance=CallAllowance(2,0,'SYNTHETIC_PROVIDER_FREE_WITNESS'))
        assert result['status']=='ANSWERED_WITH_EXPLICIT_LIMITS' and result['provider_calls']==0
        final=json.loads(result['actual_final_messages'][-1]['content'])
        assert final['question']==QUESTION and final['sources'][0]['text']==session.sources['scene']['text']
        assert result['source_review']['deliverable'] and not result['source_review']['semantic_certification']
        return result,port.requests
    before,before_requests=answer();operation=before['operations'][0]
    assert operation['status']=='C04_EXECUTED' and operation['checked_treatment_present']
    native=operation['result'];assert native['appraisal']['goal_congruence']=='MIXED_GOAL_CONGRUENCE'
    assert native['appraisal']['reported_emotions']==['relieved','worried']
    assert native['appraisal']['inferred_actual_emotion']=='NOT_ESTABLISHED'
    session.put_source('scene',SOURCE+'\nMira said, "I abandoned my goal to finish the report."')
    old_status={key:session.workspace.core.support_statuses()[key]for key in operation['support_claim_ids']}
    assert set(old_status.values())=={'UNSUPPORTED'}
    after,after_requests=answer();updated=after['operations'][0]['result']
    assert updated['original_sources'][0]['version']==2
    assert updated['appraisal']['goal_congruence']=='SUPPORTS_EVIDENCED_GOALS'
    assert updated['appraisal']['reported_emotions']==['relieved','worried']
    return dict(schema='hcl-universal-appraisal-witness-v1',before=before,after=after,
        complete_request_measurements=dict(before=before_requests,after=after_requests),
        old_support_after_revision=old_status,model_planning='SCRIPTED_NOT_VERIFIED',
        semantic_certification=False,complete_capability_integration=False,
        provider_calls=0,provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.write_text(json.dumps(witness(),indent=2,ensure_ascii=False)+'\n')
