"""Scripted complete D01 lifecycle with original citations and no receipt backfill."""
import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from hcl.cognition import UniversalHCL
from hcl.cognition.deepseek_metered import DeepSeekMeteredPort
from hcl.cognition.universal_entry import CallAllowance
from scripts.development_final_delivery_amendment import validate_current
from scripts.witness_commitment import SOURCE, QUERY

QUESTION='Describe the conditional promise and reported access history without inferring moral obligation or private understanding.'
PROMISE=SOURCE.splitlines()[0]
LATER="Narrator: Noor later heard Mira's last statement."
WITHDRAWAL='Mira said, "I withdraw my promise to Noor to deliver the report."'


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
            operation=dict(capability='D01',question=QUERY,source_ids=['scene'],bindings=[])
            value=dict(task='Track conditional commitment and access without private knowledge inference',
                operations=[dict(operation)for _ in range(3 if self.overflow else 1)],
                limitations=['SCRIPTED_SELECTION_NOT_MODEL_PLANNING_EVIDENCE'])
        else:
            source=json.loads(messages[-1]['content'])['sources'][0]
            quote=source['text'].splitlines()[0]
            value=dict(answer='The source reports a conditional promise. Receipt, expectation and withdrawal remain separate source reports.',
                source_citations=[dict(source_id=source['source_id'],version=source['version'],quote=quote,start=0)],
                uncertainty='Reported receipt does not establish private understanding or moral obligation.',
                assumptions='Source order is not verified chronology; a later receipt cannot backfill an earlier expectation.')
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
    before,first=answer();row=before['operations'][0];old_claims=row['support_claim_ids']
    assert row['checked_treatment_present']
    assert row['result']['commitment']['receipt']=='REPORTED_NON_EXPOSURE'
    assert row['result']['commitment']['condition_status']=='UNKNOWN'
    session.put_source('scene',SOURCE+'\n'+LATER+'\n'+WITHDRAWAL)
    old_status={key:session.workspace.core.support_statuses()[key]for key in old_claims}
    assert set(old_status.values())=={'UNSUPPORTED'}
    after,second=answer();value=after['operations'][0]['result']
    assert value['commitment']['receipt']=='REPORTED_LATER_EXPOSURE'
    assert value['commitment']['lifecycle']=='REPORTED_WITHDRAWN'
    assert value['cg02_source_check']['expectation_comparisons'][0]['condition_receipt_at_expectation']=='REPORTED_NON_EXPOSURE'
    assert value['commitment']['obligation']=='NOT_ESTABLISHED'
    assert json.loads(after['actual_final_messages'][-1]['content'])['sources'][0]['version']==2
    overflow_source=SOURCE.replace('the permit arrives','the permit arrives '+'before the deadline '*40)
    session.put_source('scene',overflow_source)
    overflow,third=answer(True)
    assert third.calls==['planning'] and overflow['status']=='ORCHESTRATION_UNAVAILABLE_OR_FAILED'
    assert len(overflow['operations'])==3 and all(r['executed']for r in overflow['operations'])
    assert all(r['result']['original_source']==overflow_source for r in overflow['operations'])
    assert 'answer' not in overflow
    return dict(schema='hcl-universal-commitment-witness-v1',before=before,after=after,
        combined_overflow=overflow,complete_request_measurements=dict(before=first.requests,after=second.requests),
        old_support_after_revision=old_status,model_planning='SCRIPTED_NOT_VERIFIED',
        semantic_certification=False,complete_capability_integration=False,provider_calls=0,
        provider_spend_usd=0,longmemeval='SEALED_NOT_ACCESSED')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.write_text(json.dumps(witness(),indent=2,ensure_ascii=False)+'\n')
