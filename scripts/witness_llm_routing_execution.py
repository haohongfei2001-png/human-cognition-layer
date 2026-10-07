"""Complete scripted planner -> retained conditional tool -> cited answer witness."""
import argparse,hashlib,json
from decimal import Decimal
from pathlib import Path
from hcl.cognition import UniversalHCL
from scripts.development_planning_allowance_amendment import validate_current
from scripts.serious_eval_contract import runtime_digest
from tests.test_v1_conditional_reader_entry import SOURCE,QUERY,QUOTES,proposals
from tests.test_v1_llm_routing_execution import translated
from tests.test_v1_universal_appraisal import RequestBoundedStub
from tests.test_v1_universal_question import plan,run


class CitedPort(RequestBoundedStub):
    def complete(self,phase,messages):
        response=super().complete(phase,messages)
        if phase=='answer':
            response['text']=json.dumps(dict(answer='The source reports a desire to protect the gate. The structured interpretation remains conditional.',
                source_citations=[dict(source_id='meeting',version=1,quote=QUOTES[0],start=0)],
                uncertainty='Model translation and private state are not certified.',assumptions='The supplied structured interpretation is a model hypothesis.'))
        return response


def witness():
    validate_current();cases={}
    for cid in ('B01','C01','C03'):
        session=UniversalHCL();session.put_source('meeting',SOURCE)
        port=CitedPort(plan(translated(cid)));result=run(session,QUERY,port)
        assert result['status']=='ANSWERED_WITH_EXPLICIT_LIMITS'
        assert result['source_review']['deliverable'] and not result['source_review']['semantic_certification']
        assert [phase for phase,_ in port.calls]==['planning','answer']
        row=result['operations'][0];assert row['checked_treatment_present'] and row['additional_provider_calls']==0
        requests={phase:dict(bytes=len(port.encoded[phase]),sha256=hashlib.sha256(port.encoded[phase]).hexdigest(),
            conservative_reservation_usd=port.validator.reservation_usd(phase,messages))for phase,messages in port.calls}
        cases[cid]=dict(requests=requests,complete_schedule_reservation_usd=str(sum(Decimal(r['conservative_reservation_usd'])for r in requests.values())),
            original_source_snapshot=session.sources['meeting'],selected_family_checked=True,
            native_results=result['hcl_execution']['native_results'],translation_assumptions=len(row['result']['shared_semantic_binding']['assumptions']),
            original_citation_status=result['source_review']['status'],provider_calls=0,additional_provider_phases=0)
    return dict(schema='hcl-llm-routing-execution-witness-v1',status='PASS_SCRIPTED_FULL_FLOW_NOT_MODEL_QUALITY',
        runtime_sha256=runtime_digest(),source_sha256=hashlib.sha256(SOURCE.encode()).hexdigest(),
        planner_candidates_sha256=hashlib.sha256(json.dumps(proposals(),sort_keys=True).encode()).hexdigest(),
        maximum_request_bytes=36000,planning_tokens=4096,answer_tokens=8192,cases=cases,
        model_understanding_verified=False,efficacy_established=False,provider_calls=0,authorized_additional_calls=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(),indent=2,sort_keys=True)+'\n')
    print('LLM_PLANNED_NATIVE_EXECUTION_FULL_FLOW_PASS_PROVIDER_FREE')
