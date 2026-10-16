"""Provider-free exact-domain computation and immutable-upstream witness."""
import argparse
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

import hcl
from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.execution_ledger import ExecutionLedger
from scripts.witness_unified_judgment import propose as base_propose, SCENE

PRINCIPLES = 'The analyst conditionally compares X=(10,0), Y=(6,6), Z=(0,10), under normalized nonnegative x,y weights. A declared interval is 9/20 <= x <= 11/20. Hard protection duties and original commitments remain fixed. No weights are inferred from behavior.'
QUESTION = 'Compute the exact recommendation regions and boundary ties under the declared weight domain.'


def propose(snapshot, question):
    candidate = base_propose(snapshot, question)
    model = candidate['models'][0]
    graph = model['mental']['plans'][0]['graph']
    graph['states'].append('balanced'); graph['terminal'].append('balanced'); graph['utilities']['balanced'] = '1'
    graph['actions'][0]['id'] = 'X'; graph['actions'][1]['id'] = 'Z'
    graph['actions'].append(dict(graph['actions'][0], id='Y', transitions={s: 'balanced' if s in ('risk','clear') else s for s in graph['states']}))
    for action in graph['actions']:
        action['transitions']['balanced'] = 'balanced'
        action['observations'] = {s:s for s in graph['states']}
    model['facts'][1]['reference']['action_id'] = 'X'
    decision = model['decisions'][0]; framework = decision['frameworks'][0]
    refs = framework['segment_ids']
    decision['dimensions'] = [dict(id=key, label=key, state_values=dict(risk='0', clear='0', protected=x, ignored=z, balanced='6'),
        action_costs=dict(X='0', Y='0', Z='0'), segment_ids=refs) for key, x, z in [('x','10','0'),('y','0','10')]]
    framework.update(weights=None, decision_rule='PARETO', norms=[])
    candidate.update(schema='hcl-judgment-candidates-5', weight_domains=[dict(id='values', source_id='scene', model_id='notice',
        decision_id=decision['id'], framework_id=framework['id'], decision_rule='EXPECTED', constraints=[],
        origin=deepcopy(framework['origin']), segment_ids=refs)])
    return candidate


def interval_constraints(refs, low='9/20', high='11/20'):
    return [dict(id='lower', coefficients=dict(x='-1',y='0'), relation='LE', rhs='-'+low, segment_ids=refs),
            dict(id='upper', coefficients=dict(x='1',y='0'), relation='LE', rhs=high, segment_ids=refs)]


def witness():
    owner = Principal('synthetic-weight-witness','owner'); rows=[]
    with tempfile.TemporaryDirectory() as directory:
        store=StateStore.sqlite(Path(directory)/'state.sqlite', revision=True); store.create_session('s',owner,{'bob'})
        handles=(store.put_source('s',owner,'scene',SCENE), store.put_source('s',owner,'principles',PRINCIPLES))
        for mode in ('simplex','interval','empty','budget','joint-norms','minimax-regret'):
            request=TaskRequest(mode,QUESTION,handles,'s',owner, budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,
                max_local_evaluations=1800 if mode=='budget' else 100000,max_request_bytes=1048576,max_context_tokens=1048576,
                max_output_bytes=1048576,max_total_output_bytes=8000000,max_visible_output_tokens=1048576),
                issue=ExecutionIssue('root',goals=(Issue(mode,'judgment.evaluate'),)))
            candidate=propose(store.snapshot('s',owner,handles),QUESTION); domain=candidate['weight_domains'][0]
            if mode in ('interval','empty'): domain['constraints']=interval_constraints(domain['segment_ids'],high='1/4' if mode=='empty' else '11/20')
            if mode=='minimax-regret': domain['decision_rule']='MINIMAX_REGRET'
            if mode=='joint-norms':
                model=candidate['models'][0]; model['argument']['priorities']=[]
                model['decisions'][0]['frameworks'][0]['norms']=[dict(id='protect',label='duty',permitted_actions=['X'],guard_fact_ids=['knowledge','control'],argument_query_id='duty',segment_ids=domain['segment_ids'])]
            port=OfflineModelPort(json.dumps(candidate)); result=HCL(store,principal=owner,gateway=ModelGateway(store,port)).run_sync(request)
            assert result.status=='PARTIAL', result.diagnostics
            actual=ExecutionLedger(store).delivery_inferences(request,result.execution_receipt['result_ids'])[0]
            value=thaw(actual.values)
            if mode=='simplex':
                analysis=value['analyses'][0]; partition=analysis['branches'][0]['regions']['recommendation_partition']
                assert len(partition)==5 and partition[1]['lower']=='2/5' and partition[3]['lower']=='3/5'
                assert analysis['complete'] and analysis['robust_recommended']==[] and analysis['possible_recommended']==['X','Y','Z']
            elif mode=='minimax-regret':
                assert value['analyses'][0]['complete']
                assert 'MINIMAX_REGRET' in result.answer
                assert all('maximum_regrets' in c for c in value['analyses'][0]['branches'][0]['regions']['cells'])
            elif mode=='interval': assert value['analyses'][0]['unique_robust_recommended']==['Y']
            elif mode=='empty': assert value['analyses'][0]['robust_recommended']==[] and value['analyses'][0]['branches'][0]['regions']['domain_status']=='EMPTY'
            elif mode=='joint-norms': assert len(value['analyses'][0]['branches'])==2 and value['analyses'][0]['robust_recommended']==[]
            else: assert not value['complete']
            replay_port=OfflineModelPort('NO_SEND'); replay=HCL(store,principal=owner,gateway=ModelGateway(store,replay_port)).run_sync(request)
            assert replay.answer==result.answer and replay_port.attempts==0
            rows.append(dict(case=mode,status=result.status,actual=value,answer=result.answer,usage=thaw(result.usage),
                claim_fields=[f.field for c in result.claim_records for f in c.used_result_fields],offline_attempts=port.attempts,replay_new_attempts=0))
        store.set_readers('s',owner,'principles',{'bob'}); denied=HCL(store,principal=owner).run_sync(request)
        assert denied.status=='DENIED' and not denied.answer
        rows.append(dict(case='secondary-source-current-acl',status=denied.status,answer_absent=True)); store.close()
    root=Path(hcl.__file__).resolve().parents[1]
    return dict(schema='hcl-unified-weight-regions-witness-1',checked_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        runtime_hashes={str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest() for p in sorted((root/'hcl').rglob('*.py'))},rows=rows,
        provider_calls=0,provider_spend_usd=0,sealed_content_reads=0,evidence_scope='INTEGRATED_OFFLINE_PARTIAL_EXACT_BOUNDED_WEIGHT_REGIONS',
        not_established=['OPEN_PRINCIPLE_DISCOVERY','PREFERENCE_INFERENCE','AUTHENTICATED_ADOPTION','FULL_M14','FULL_T17','FULL_T18','FULL_S4','LIVE_EFFECT'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output',required=True,type=Path); args=parser.parse_args()
    args.output.write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n')
