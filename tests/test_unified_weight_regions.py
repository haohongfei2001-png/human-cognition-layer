"""Full ordinary runner, replay, current ACL and exact source/host contracts."""
from copy import deepcopy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionIssue, ConceptAdoptionIssue
from hcl.kernel.types import HCLFailure, Issue, thaw
from hcl.memory import codec
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.local_model import LocalModelOperator
from hcl.operators.weight_region_model import WeightRegionOperator, verify_weight_regions
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.execution_ledger import ExecutionLedger
from hcl.runtime.recovery import RecoveryManager
from hcl.semantics.judgment_compiler import JudgmentCompiler
from hcl.semantics.segments import segment_snapshot, question_segments
from scripts.witness_unified_weight_regions import propose, interval_constraints, SCENE, PRINCIPLES
from tests import test_unified_s4_judgment as runtime


class WeightRegionRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.f=runtime.JudgmentExecutionTests();self.f.setUp();self.addCleanup(self.f.tearDown)
        scene=self.f.store.put_source('s',self.f.owner,'scene',SCENE)
        principles=self.f.store.put_source('s',self.f.owner,'principles',PRINCIPLES)
        self.f.request=replace(self.f.request,source_handles=(scene,principles))

    def candidate(self):return propose(self.f.store.snapshot('s',self.f.owner,self.f.request.source_handles),self.f.request.question)

    def run_candidate(self,candidate=None,request=None,stream=False):
        request=request or self.f.request
        result,port=self.f.run_candidate(candidate or self.candidate(),request,stream=stream)
        self.assertEqual(result.status,'PARTIAL',result.diagnostics)
        proof=ExecutionLedger(self.f.store).delivery_inferences(request,result.execution_receipt['result_ids'])[0]
        return thaw(proof.values),result,port,proof

    def pure(self,candidate=None,limit=100000):
        snapshot=self.f.store.snapshot('s',self.f.owner,self.f.request.source_handles)
        allowance=replace(self.f.request.budget,max_local_evaluations=limit)
        program=JudgmentCompiler().compile(snapshot,segment_snapshot(snapshot,self.f.request.question),json.dumps(candidate or self.candidate()),allowance)
        return WeightRegionOperator().run(snapshot,Issue('domain','judgment.evaluate'),allowance,program).candidate_delta.new_inferences[0]

    def test_ordinary_source_bound_exact_domain_reaches_final_claim(self):
        value,result,port,proof=self.run_candidate(stream=True)
        self.assertTrue(value['complete']);self.assertEqual(port.attempts,1)
        analysis=value['analyses'][0]
        self.assertEqual(analysis['possible_recommended'],['X','Y','Z']);self.assertFalse(analysis['robust_recommended'])
        self.assertIn('2/5',result.answer);self.assertIn('3/5',result.answer)
        self.assertTrue(any(f.field=='analyses' for c in result.claim_records for f in c.used_result_fields))
        self.assertEqual(codec.loads(codec.dumps(proof)),proof)
        self.assertFalse(analysis['adoption_authorized'])

    def test_interval_changes_only_weight_analysis_not_actual_facts_commitments(self):
        before=thaw(self.pure().values)
        candidate=self.candidate();domain=candidate['weight_domains'][0]
        domain['constraints']=interval_constraints(domain['segment_ids'])
        after=thaw(self.pure(candidate).values)
        self.assertEqual(before['program']['base_program'],after['program']['base_program'])
        b=before['actual_judgment']['models'][0]; a=after['actual_judgment']['models'][0]
        self.assertEqual(b['decisions'][0]['outcomes'],a['decisions'][0]['outcomes'])
        self.assertEqual({k:v['possible_values'] for k,v in b['facts'].items()},{k:v['possible_values'] for k,v in a['facts'].items()})
        self.assertEqual(b['actual_interaction']['values']['models'][0]['commitments'],a['actual_interaction']['values']['models'][0]['commitments'])
        self.assertEqual(after['analyses'][0]['unique_robust_recommended'],['Y'])
        self.assertTrue(after['analyses'][0]['complete'])

    def test_domain_analysis_does_not_authorize_concept_adoption(self):
        _,_,_,proof=self.run_candidate()
        request=replace(self.f.request,request_id='no-domain-adoption',source_handles=(),
            budget=replace(self.f.request.budget,max_mock_calls=0),issue=ExecutionIssue('root',goals=(
                ConceptAdoptionIssue('adopt',stream_id='values',support_result_ids=(proof.result_id,),version_labels=('values',)),)))
        port=OfflineModelPort('NO_SEND');result=HCL(self.f.store,principal=self.f.owner,gateway=ModelGateway(self.f.store,port)).run_sync(request)
        self.assertNotEqual(result.status,'COMPLETED');self.assertFalse(result.answer);self.assertEqual(port.attempts,0)

    def test_upstream_computed_once_shared_across_domains_and_cells(self):
        from hcl.operators.judgment_model import JudgmentModelOperator
        original=JudgmentModelOperator._run;calls=[]
        def observe(*args,**kwargs):calls.append(1);return original(*args,**kwargs)
        with patch.object(JudgmentModelOperator,'_run',new=observe):value=thaw(self.pure().values)
        self.assertEqual(len(calls),1);self.assertGreater(len(value['analyses'][0]['branches'][0]['regions']['cells']),1)

    def test_real_m13_joint_extensions_preserve_dissent(self):
        c=self.candidate();m=c['models'][0];m['argument']['priorities']=[]
        f=m['decisions'][0]['frameworks'][0]
        f['norms']=[dict(id='duty',label='protect',permitted_actions=['X'],guard_fact_ids=['knowledge','control'],argument_query_id='duty',segment_ids=f['segment_ids'])]
        value=thaw(self.pure(c).values);a=value['analyses'][0]
        self.assertEqual(len(a['branches']),2);self.assertTrue(a['complete']);self.assertFalse(a['robust_recommended'])
        self.assertEqual({b['basis'] for b in a['branches']},{'PREFERRED_CONDITIONAL'})
        self.assertTrue(all(b['extension'] is not None for b in a['branches']))

    def test_unknown_norm_guard_retains_conditional_regions_without_robust_claim(self):
        c=self.candidate();m=c['models'][0];m['mental']['variables'][1]['initial']=None
        f=m['decisions'][0]['frameworks'][0]
        f['norms']=[dict(id='promise',label='promise',permitted_actions=['X'],guard_fact_ids=['promise'],argument_query_id=None,segment_ids=f['segment_ids'])]
        value=thaw(self.pure(c).values);a=value['analyses'][0]
        self.assertFalse(value['complete']);self.assertFalse(a['robust_recommended']);self.assertFalse(a['possible_recommended'])
        self.assertTrue(a['branches'][0]['regions']['cells']);self.assertFalse(a['branches'][0]['conditions_complete'])

    def test_hard_norm_cannot_be_compensated_with_extreme_utility(self):
        c=self.candidate();f=c['models'][0]['decisions'][0]['frameworks'][0]
        f['norms']=[dict(id='duty',label='protect',permitted_actions=['X'],guard_fact_ids=[],argument_query_id=None,segment_ids=f['segment_ids'])]
        value=thaw(self.pure(c).values);a=value['analyses'][0]
        self.assertEqual(a['unique_robust_recommended'],['X'])
        self.assertEqual({e['status'] for e in a['branches'][0]['eligibility']},{'PERMITTED_IN_DECLARED_FRAMEWORK','PROHIBITED'})

    def test_world_infeasible_action_excluded_from_all_regions(self):
        c=self.candidate();c['models'][0]['mental']['plans'][0]['graph']['actions'][0]['feasible']=[]
        a=thaw(self.pure(c).values)['analyses'][0]
        self.assertNotIn('X',a['possible_recommended'])
        self.assertTrue(any(e['status']=='INFEASIBLE' for e in a['branches'][0]['eligibility']))

    def test_expected_requires_explicit_joint_probability_scenario(self):
        c=self.candidate();m=c['models'][0];m['mental']['variables'][0]['initial']=None;m['mental']['events']=[];m['mental']['active_assumptions']=['interpretation']
        a=thaw(self.pure(c).values)['analyses'][0]
        self.assertFalse(a['complete']);self.assertIn('EXPECTED_PROBABILITIES_UNSPECIFIED',a['frontier'])
        c['weight_domains'][0]['decision_rule']='MAXIMIN';a=thaw(self.pure(c).values)['analyses'][0]
        self.assertTrue(a['complete']);self.assertTrue(a['branches'][0]['regions']['complete'])

    def test_empty_domain_not_vacuously_robust(self):
        c=self.candidate();d=c['weight_domains'][0];d['constraints']=interval_constraints(d['segment_ids'],high='1/4')
        a=thaw(self.pure(c).values)['analyses'][0]
        self.assertTrue(a['complete']);self.assertFalse(a['robust_recommended']);self.assertFalse(a['possible_recommended'])
        self.assertEqual(a['branches'][0]['regions']['domain_status'],'EMPTY')

    def test_budget_prefix_and_proof_frontier_keep_no_universal_claim(self):
        for limit in (0,1,100):
            with patch('hcl.operators.weight_region_model.verify_weight_program',side_effect=AssertionError('no unbudgeted validation')),self.assertRaises(HCLFailure) as caught:self.pure(limit=limit)
            self.assertEqual(caught.exception.diagnostic.code,'WEIGHT_VALIDATION_FRONTIER')
        for limit in (1500,1800,2200):
            proof=self.pure(limit=limit);value=thaw(proof.values)
            self.assertLessEqual(value['local_evaluations'],limit)
            if not value['complete']:
                self.assertTrue(value['issues']);self.assertFalse(any(a['robust_recommended'] for a in value['analyses']))
        from hcl.operators.weight_regions import solve_regions
        r=solve_regions({'constraints':[]},{'A':{'s':{'x':1,'y':0}},'B':{'s':{'x':0,'y':1}}},['x','y'],'EXPECTED',__import__('hcl.operators.judgment',fromlist=['JudgmentWork']).JudgmentWork(100000),max_proof_bytes=20)
        self.assertFalse(r['complete']);self.assertIn('WEIGHT_PROOF_CAPACITY_FRONTIER',r['frontier'])

    def test_forged_regions_source_host_and_proof_metadata_rejected(self):
        _,_,_,original=self.run_candidate();AnswerAssembler()._claim(original)
        mutations=[lambda v:v['analyses'][0].update(robust_recommended=['X']),
            lambda v:v['analyses'][0]['branches'][0]['regions']['recommendation_partition'][1].update(lower='1/3'),
            lambda v:v['analyses'][0]['branches'][0]['regions']['coverage'][0]['children'][0]['certificate'].update(point=['9']),
            lambda v:v['program']['host_context'].update(session_id='other'),
            lambda v:v['program']['weight_domains'][0]['binding'].update(actor='someone'),
            lambda v:v['source_versions'].update(principles=999),
            lambda v:v['local_model'].update(dialect='judgment-model-1')]
        for mutate in mutations:
            v=thaw(original.values);mutate(v)
            with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(original,values=v))
        for fields in [dict(assumption_environments=()),dict(premise_ids=('scene',)),dict(counterevidence_ids=('fake',)),dict(coverage='ADOPTED')]:
            with self.assertRaises(HCLFailure):AnswerAssembler()._claim(replace(original,**fields))

    def test_three_dimension_cells_and_reasons_survive_compact_delivery(self):
        c=self.candidate(); d=c['models'][0]['decisions'][0]
        extra=deepcopy(d['dimensions'][0]);extra['id']='z';extra['label']='z'
        extra['state_values']={k:'0' for k in extra['state_values']};d['dimensions'].append(extra)
        _,_,_,proof=self.run_candidate(c)
        claim=AnswerAssembler().compact_claim(proof)
        fields=claim.used_result_fields
        self.assertTrue(any(f.field=='analyses' and 'cells' in f.path and f.path[-1]=='constraints' for f in fields))
        self.assertTrue(any(f.field=='analyses' and f.path[-1]=='alternative_reasons' for f in fields))
        self.assertTrue(any(f.field=='analyses' and f.path[-1]=='eligibility' for f in fields))

    def test_invalid_sources_authority_constraints_and_legacy_field_injection(self):
        for mutation in [lambda c:c['weight_domains'][0].update(winner='X'),
            lambda c:c['weight_domains'][0].update(decision_rule='PARETO'),
            lambda c:c['weight_domains'][0]['origin'].update(kind='AUTHENTICATED_USER'),
            lambda c:c['weight_domains'][0].update(segment_ids=[question_segments(self.f.request.question)[0].segment_id]),
            lambda c:c['models'][0]['decisions'][0]['frameworks'][0].update(weights={'x':'1/2','y':'1/2'},decision_rule='EXPECTED'),
            lambda c:c['weight_domains'][0].update(constraints=[dict(id='bad',coefficients=dict(x=True,y=0),rhs=1,relation='LE',segment_ids=c['weight_domains'][0]['segment_ids'])]),
            lambda c:c.update(schema='hcl-judgment-candidates-1')]:
            c=self.candidate();mutation(c)
            with self.assertRaises((HCLFailure,ValueError)):self.pure(c)

    def test_reopen_exact_replay_no_new_send_and_source_staleness(self):
        _,result,_,_=self.run_candidate(stream=True)
        self.f.store.close();self.f.store=__import__('hcl.memory.store',fromlist=['StateStore']).StateStore.sqlite(self.f.path)
        replay,port=self.f.run_candidate(self.candidate(),stream=True)
        self.assertEqual(result.answer,replay.answer);self.assertEqual(port.attempts,0)
        self.f.store.put_source('s',self.f.owner,'principles','Changed declared weight domain.')
        replay,port=self.f.run_candidate({'schema':'UNUSED'},self.f.request)
        self.assertIn(replay.status,('STALE_STATE','DENIED'));self.assertFalse(replay.answer);self.assertEqual(port.attempts,0)

    def test_returned_computed_committed_recovery_never_resends(self):
        class Crash(BaseException):pass
        for seam in ('return_persisted','execution_computed','execution_effects_committed'):
            request=replace(self.f.request,request_id=seam,issue=ExecutionIssue('root',goals=(Issue(seam,'judgment.evaluate'),)))
            c=self.candidate();owner=self.f.store.owner_id;fired=False
            def stop(stage):
                nonlocal fired
                if stage==seam and not fired:fired=True;raise Crash()
            with patch.object(self.f.store,'_checkpoint',side_effect=stop),self.assertRaises(Crash):self.f.run_candidate(c,request)
            self.assertTrue(fired)
            self.f.store.close();self.f.store=__import__('hcl.memory.store',fromlist=['StateStore']).StateStore.sqlite(self.f.path)
            RecoveryManager(self.f.store).resume_execution(request,expected_owner_id=owner)
            if seam=='return_persisted':value,result,port,_=self.run_candidate(c,request)
            else:
                with patch.object(LocalModelOperator,'run',side_effect=AssertionError('accepted cannot recompute')):value,result,port,_=self.run_candidate(c,request)
            self.assertTrue(value['complete']);self.assertEqual(port.attempts,0)

    def test_secondary_acl_revocation_and_unknown_send_hold(self):
        candidate=self.candidate();self.run_candidate(candidate);self.f.store.set_readers('s',self.f.owner,'principles',{'bob'})
        result,port=self.f.run_candidate(candidate);self.assertEqual(result.status,'DENIED');self.assertFalse(result.answer);self.assertEqual(port.attempts,0)
        self.f.store.set_readers('s',self.f.owner,'principles',{'alice'})
        class Crash(BaseException):pass
        request=replace(self.f.request,request_id='unknown')
        def stop(stage):
            if stage=='send_started':raise Crash()
        with patch.object(self.f.store,'_checkpoint',side_effect=stop),self.assertRaises(Crash):self.f.run_candidate(self.candidate(),request)
        with self.assertRaises(HCLFailure):RecoveryManager(self.f.store).resume_execution(request,expected_owner_id=self.f.store.owner_id)
        result,port=self.f.run_candidate(self.candidate(),request)
        self.assertIsNone(result.usage['mock_calls']);self.assertEqual(result.usage['held_mock_calls'],1);self.assertEqual(port.attempts,0)


if __name__=='__main__':unittest.main()
