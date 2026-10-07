"""Scripted original prose -> structured C02 input -> conditional result -> cited answer."""
import argparse,hashlib,json
from decimal import Decimal
from pathlib import Path
from hcl.cognition import UniversalHCL
from scripts.development_native_reader_policy_amendment import validate_current
from scripts.serious_eval_contract import runtime_digest
from tests.test_v1_c02_planned_input import SOURCE,ORIGINAL,QUOTES,candidates,selected,state
from tests.test_v1_universal_appraisal import RequestBoundedStub
from tests.test_v1_universal_question import plan,run


class CitedPort(RequestBoundedStub):
    def complete(self,phase,messages):
        response=super().complete(phase,messages)
        if phase=='answer':
            payload=json.loads(messages[-1]['content']);source=payload['sources'][0]
            response['text']=json.dumps(dict(answer='The reports permit conditional explanations; they do not establish Kellan\'s unique actual motive.',
                source_citations=[dict(source_id='maintenance',version=source['version'],quote=QUOTES[0],start=0)],
                uncertainty='Other explanations and the interpretation remain unresolved.',assumptions='The model-proposed structured reading is unverified.'))
        return response


def witness():
    validate_current();session=UniversalHCL();cases={};prior_claims=[]
    for name in ('original','revised_ignorance'):
        source=SOURCE if name=='original'else SOURCE.replace('knew about','did not know about')
        session.put_source('maintenance',source)
        if prior_claims:assert all(session.workspace.core.support_statuses()[claim]!='SUPPORT_AVAILABLE'for claim in prior_claims)
        rows=candidates()
        if name!='original':
            rows[2]['quote']=rows[2]['quote'].replace('knew','did not know')
            rows[2]['content']['canonical_statement']=rows[2]['content']['canonical_statement'].replace('knew','did not know')
        port=CitedPort(plan(selected(rows)));result=run(session,ORIGINAL,port);row,expanded,native=state(result)
        assert result['status']=='ANSWERED_WITH_EXPLICIT_LIMITS'and result['source_review']['deliverable']
        assert [phase for phase,_ in port.calls]==['planning','answer']
        assert native['winning_motive']=='NOT_INFERRED'and not row['semantic_certification']
        assert native['explanations'][0]['disposition']==('CONDITIONALLY_SUPPORTED'if name=='original'else'WEAKENED_BY_COUNTEREVIDENCE')
        requests={phase:dict(bytes=len(port.encoded[phase]),sha256=hashlib.sha256(port.encoded[phase]).hexdigest(),
            conservative_reservation_usd=port.validator.reservation_usd(phase,messages))for phase,messages in port.calls}
        cases[name]=dict(requests=requests,conservative_schedule_reservation_usd=str(sum(Decimal(r['conservative_reservation_usd'])for r in requests.values())),
            original_source_snapshot=session.sources['maintenance'],dispositions=[r['disposition']for r in native['explanations']],
            source_version=expanded['sources'][0]['version'],translation_assumptions=len(expanded['shared_semantic_binding']['assumptions']),
            prior_claims_withdrawn=bool(prior_claims),original_citation_status=result['source_review']['status'],native_results=result['hcl_execution']['native_results'],
            additional_provider_phases=0,provider_calls=0)
        prior_claims=row['support_claim_ids']
    return dict(schema='hcl-c02-planned-input-witness-v1',status='PASS_SCRIPTED_C02_FULL_FLOW_AND_REVISION_NOT_MODEL_QUALITY',
        runtime_sha256=runtime_digest(),native_action_explanations_sha256=hashlib.sha256(Path('hcl/cognition/action_explanations.py').read_bytes()).hexdigest(),
        maximum_request_bytes=36000,planning_tokens=4096,answer_tokens=8192,cases=cases,
        native_parser_changed=False,model_understanding_verified=False,efficacy_established=False,provider_calls=0,authorized_additional_calls=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(),indent=2,sort_keys=True)+'\n')
    print('PLANNED_C02_CONDITIONAL_SOURCE_FLOW_AND_REVISION_PASS_PROVIDER_FREE')
