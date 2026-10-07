"""Complete D01/D02 composition with finite acknowledgment and historical meaning."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from hcl.cognition import UniversalHCL
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort
from hcl.cognition.universal_entry import CallAllowance
from scripts.development_native_reader_policy_amendment import validate_current
from scripts.witness_commitment import SOURCE as PROMISE_SOURCE, QUERY as PROMISE_QUERY
from scripts.witness_mutual_understanding import SOURCE as ACK_SOURCE, QUERY

SOURCE=PROMISE_SOURCE+'\n'+ACK_SOURCE
QUESTION='Describe the conditional commitment and finite acknowledgment history without inferring private understanding.'
TARGET='the meeting is at noon'
REVISION='Mira said, "I revise my meaning from the meeting is at noon to the meeting is at one."'


class ScriptedPort:
    provider_free=True
    def __init__(self,overflow=False,query=QUERY):
        self.requests={};self.calls=[];self.overflow=overflow;self.query=query
        self.validator=DeepSeekMeteredPort(SimpleNamespace(max_retries=0,
            base_url='https://api.deepseek.com',timeout=60))
    def reservation_usd(self,phase,messages):
        _,encoded=self.validator.request(phase,messages)
        self.requests[phase]=dict(bytes=len(encoded),sha256=hashlib.sha256(encoded).hexdigest())
        return '0'
    def complete(self,phase,messages):
        self.calls.append(phase)
        if phase=='planning':
            acknowledgment=dict(capability='D02',question=self.query,source_ids=['scene'],bindings=[])
            operations=([dict(acknowledgment)for _ in range(3)]if self.overflow else
                [dict(capability='D01',question=PROMISE_QUERY,source_ids=['scene'],bindings=[]),acknowledgment])
            value=dict(task='Preserve commitment and finite acknowledgment as separate source reports',
                operations=operations,limitations=['SCRIPTED_SELECTION_NOT_MODEL_PLANNING_EVIDENCE'])
        else:
            source=json.loads(messages[-1]['content'])['sources'][0]
            quotes=(PROMISE_SOURCE.splitlines()[0],ACK_SOURCE.splitlines()[0])
            value=dict(answer='The source reports a conditional promise and a finite acknowledgment history; neither establishes private understanding or moral obligation.',
                source_citations=[dict(source_id=source['source_id'],version=source['version'],quote=quote,start=source['text'].index(quote))for quote in quotes],
                uncertainty='A revised meaning does not retroactively update the other participant or restore trust.',
                assumptions='Source order is not verified chronology; each receipt belongs to its own statement and time.')
        return dict(text=json.dumps(value),actual_usd='0',usage={})


def witness():
    validate_current();session=UniversalHCL();session.put_source('scene',SOURCE)
    def answer(overflow=False,query=QUERY):
        port=ScriptedPort(overflow,query)
        result=session.answer(QUESTION,planner_backend=port,answer_backend=port,
            allowance=CallAllowance(2,0,'SYNTHETIC_PROVIDER_FREE_WITNESS'))
        assert result['provider_calls']==0
        if not overflow:
            assert result['status']=='ANSWERED_WITH_EXPLICIT_LIMITS'
            assert result['source_review']['deliverable'] and not result['source_review']['semantic_certification']
            final=json.loads(result['actual_final_messages'][-1]['content'])
            assert final['question']==QUESTION and final['sources'][0]['text']==session.sources['scene']['text']
        return result,port
    before,first=answer();promise,ack=before['operations']
    assert promise['checked_treatment_present'] and ack['checked_treatment_present']
    assert promise['result']['commitment']['receipt']=='REPORTED_NON_EXPOSURE'
    assert ack['result']['status']=='BOUNDED_MUTUALLY_ACKNOWLEDGED'
    old_claims=list(dict.fromkeys(promise['support_claim_ids']+ack['support_claim_ids']))
    session.put_source('scene',SOURCE+'\n'+REVISION)
    old_status={key:session.workspace.core.support_statuses()[key]for key in old_claims}
    assert set(old_status.values())=={'UNSUPPORTED'}
    after,second=answer();current=after['operations'][1]
    assert current['checked_treatment_present'] and current['result']['status']=='SUPERSEDED_MEANING'
    assert current['result']['acknowledgment_chains'][0]['status']=='SUPERSEDED_MEANING_HISTORICAL_ACKNOWLEDGMENT'
    assert after['operations'][0]['result']['commitment']['receipt']=='REPORTED_NON_EXPOSURE'
    assert json.loads(after['actual_final_messages'][-1]['content'])['sources'][0]['version']==2
    unacknowledged,current_port=answer(query=QUERY.replace('noon','one'))
    assert not unacknowledged['operations'][1]['checked_treatment_present']
    assert unacknowledged['operations'][1]['result']['status']=='NO_COMPLETE_ACKNOWLEDGMENT_CHAIN'
    targets=[f'the meeting is at {time}'+' as agreed'*10 for time in ('noon','one','two')]
    overflow_source=ACK_SOURCE.replace(TARGET,targets[0])
    for old,new in zip(targets,targets[1:]):
        overflow_source+='\n'+f'Mira said, "I revise my meaning from {old} to {new}."'+'\n'+'\n'.join(ACK_SOURCE.replace(TARGET,new).splitlines()[1:])
    session.put_source('scene',overflow_source)
    overflow,third=answer(True,QUERY.replace(TARGET,targets[-1]))
    assert third.calls==['planning'] and overflow['status']=='ORCHESTRATION_UNAVAILABLE_OR_FAILED'
    assert len(overflow['operations'])==3 and all(r['executed']for r in overflow['operations'])
    assert all(len(r['result']['acknowledgment_chains'])==3 and r['result']['original_source']==overflow_source for r in overflow['operations'])
    assert 'answer' not in overflow
    return dict(schema='hcl-universal-understanding-witness-v1',before=before,after=after,
        current_target_without_chain=unacknowledged,combined_overflow=overflow,
        complete_request_measurements=dict(before=first.requests,after=second.requests,current_target_without_chain=current_port.requests),
        old_support_after_revision=old_status,model_planning='SCRIPTED_NOT_VERIFIED',
        semantic_certification=False,complete_capability_integration=False,provider_calls=0,
        provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.write_text(json.dumps(witness(),indent=2,ensure_ascii=False)+'\n')
