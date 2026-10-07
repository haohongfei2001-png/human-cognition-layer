"""C05 ordinary-entry authority and complete C04-to-C05 offline composition."""
import json
import unittest
from dataclasses import asdict
from unittest.mock import patch

from hcl.cognition import UniversalHCL, semantic
from hcl.cognition.agency_chain import prepare_agency_chain
from hcl.cognition.capability_catalog import CATALOG
from tests.test_v1_agency_chain import SOURCE, QUERY
from tests.test_v1_universal_appraisal import RequestBoundedStub
from tests.test_v1_universal_question import Stub, operation, plan, run

ORIGINAL='Explain the reported action using its plans and appraisal, without inferring a unique motive.'
LATER='Mira said, "I now believe it is false that the train is running instead of the train is running."'
OP = lambda query=QUERY, ids=('scene',): operation('C05', query, list(ids))


def entry(source=SOURCE, query=QUERY, bounded=False):
    session=UniversalHCL();session.put_source('scene',source)
    port=(RequestBoundedStub if bounded else Stub)(plan(OP(query)))
    return session,port,run(session,ORIGINAL,port)


def output(receipt):
    row=receipt['operations'][0]
    assert row['status']=='C05_EXECUTED',row
    return row,row['result']


class UniversalAgencyChainTests(unittest.TestCase):
    def test_complete_native_chain_and_original_task_reach_final_request(self):
        session,port,receipt=entry(bounded=True);row,native=output(receipt)
        self.assertTrue(row['checked_treatment_present'])
        self.assertEqual(native['status'],'CHECKED_CONDITIONAL_CHAIN')
        self.assertEqual(native['explanations'][0]['disposition'],'CONDITIONALLY_SUPPORTED')
        self.assertEqual(native['current_plans'][0]['model_condition_check'],'MODEL_CONDITION_CONTRADICTED')
        self.assertEqual(native['explanations'][0]['actual_motive'],'NOT_ESTABLISHED')
        self.assertEqual(native['explanations'][0]['unique_motive'],'NOT_INFERRED')
        self.assertEqual(native['appraisal']['reported_emotions'],[])
        self.assertEqual(native['appraisal']['inferred_actual_emotion'],'NOT_ESTABLISHED')
        self.assertIn('Later belief cannot',native['policy'])
        final=json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual(final['question'],ORIGINAL)
        self.assertEqual(final['sources'],[dict(source_id='scene',version=1,text=SOURCE)])
        self.assertEqual(final['hcl_operations'][0]['result'],native)
        self.assertEqual(final['hcl_plan']['operations'][0]['question'],QUERY)
        self.assertTrue(row['support_claim_ids'])
        retained=prepare_agency_chain(session.workspace,QUERY,source_id='scene')
        self.assertEqual(native,retained.payload)
        self.assertEqual(row['support_claim_ids'],list(retained.claim_ids))
        self.assertTrue(all(session.workspace.core.support_statuses()[k]=='SUPPORT_AVAILABLE' for k in row['support_claim_ids']))
        self.assertEqual(set(port.encoded),{'planning','answer'})
        self.assertEqual(receipt['provider_calls'],0)

    def test_catalog_form_and_source_contract_reach_planner_without_forcing_selection(self):
        contract=CATALOG['C05'].entry_contract
        self.assertEqual(contract.question_origin,'OPERATION_QUESTION')
        self.assertEqual((contract.minimum_sources,contract.maximum_sources),(1,1))
        self.assertEqual(contract.question_forms,('Why did <Actor> <action>, considering their plans and appraisal of <episode>?',))
        session,port,_=entry()
        inventory=json.loads(port.calls[0][1][-1]['content'])['capability_inventory']
        self.assertEqual(next(r for r in inventory if r['capability_id']=='C05'),json.loads(json.dumps({key:value for key,value in asdict(CATALOG['C05']).items() if key!='implementation'})))
        result=run(session,ORIGINAL,Stub(plan()))
        self.assertEqual(result['operations'],[])
        self.assertFalse(result['answer_gain_established'])

    def test_later_reversal_changes_current_plans_not_action_time_explanation(self):
        _,_,receipt=entry(SOURCE+'\n'+LATER);_,native=output(receipt)
        self.assertEqual(native['current_plans'][0]['subjective_feasibility'],'CONTRADICTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(native['explanations'][0]['disposition'],'CONDITIONALLY_SUPPORTED')
        self.assertEqual(native['action_time']['plans'][0]['subjective_feasibility'],'SUPPORTED_UNDER_REPORTED_BELIEFS')
        self.assertEqual(native['appraisal_causation'],'NO_PLAN_FAILURE_TO_EMOTION_INFERENCE')

    def test_prior_opposite_absent_and_other_actor_belief_keep_different_limits(self):
        opposite=SOURCE.replace('I believe the train is running.','I believe it is false that the train is running.')
        _,_,receipt=entry(opposite)
        self.assertEqual(output(receipt)[1]['explanations'][0]['disposition'],'WEAKENED_BY_PLAN_COUNTEREVIDENCE')
        for source in (SOURCE.replace('Mira said, "I believe the train is running."\n',''),
                       SOURCE.replace('Mira said, "I believe','Noor said, "I believe')):
            _,_,receipt=entry(source)
            self.assertEqual(output(receipt)[1]['explanations'][0]['disposition'],'PLAN_DEPENDENCY_UNRESOLVED')

    def test_missing_and_hypothetical_action_are_not_treatment_despite_other_claims(self):
        action='Mira said, "I left the meeting."'
        for source in (SOURCE.replace(action+'\n',''),SOURCE.replace(action,'If '+action)):
            _,_,receipt=entry(source);row,native=output(receipt)
            self.assertFalse(row['checked_treatment_present'])
            self.assertEqual(native['status'],'SYSTEM_INSUFFICIENT_ACTION')
            self.assertEqual(native['explanations'],[])
            self.assertIsNone(native['action_time'])
            self.assertTrue(row['support_claim_ids'])

    def test_original_source_version_and_exact_prefix_survive_recomputation(self):
        session=UniversalHCL();session.put_source('scene','Earlier version.');session.put_source('scene',SOURCE)
        result=run(session,ORIGINAL,Stub(plan(OP())));_,native=output(result)
        prefix=native['action_time'];span=session.workspace.core.spans[prefix['source_span_id']]
        self.assertEqual(span.source_id,'scene');self.assertEqual(span.version,2)
        self.assertEqual((span.start,span.end),(0,prefix['end']))
        self.assertEqual(span.quote,SOURCE[:prefix['end']])
        self.assertEqual(native['original_sources'][0]['version'],2)
        old=prepare_agency_chain(session.workspace,QUERY,source_id='scene')
        session.put_source('scene',SOURCE+'\n'+LATER)
        with self.assertRaisesRegex(ValueError,'source changed'):old.messages(session.workspace)
        after=run(session,ORIGINAL,Stub(plan(OP())))
        self.assertEqual(output(after)[1]['original_sources'][0]['version'],3)
        self.assertEqual(output(after)[1]['explanations'][0]['disposition'],'CONDITIONALLY_SUPPORTED')

    def test_prefix_current_plan_appraisal_and_join_withdrawal_stop_before_answer(self):
        for kind in ('prefix','ACTION_PREFIX_PLAN_CHECK','BELIEF_PLAN_DECLARED_MODEL_JOIN','GOAL_APPRAISAL_AFFECT_CHANNEL_JOIN',
                     'ACTION_EXPLANATION_PLAN_DEPENDENCY_JOIN'):
            session=UniversalHCL();session.put_source('scene',SOURCE);execute=session._execute
            def changed(*args):
                row=execute(*args)
                if kind=='prefix':key=row['result']['action_time']['source_span_id']
                else:key=next(k for k,c in session.workspace.core.claims.items() if c.content.get('operation')==kind)
                session.workspace.core.withdraw(key)
                return row
            port=Stub(plan(OP()))
            with patch.object(session,'_execute',side_effect=changed):result=run(session,ORIGINAL,port)
            self.assertEqual([p for p,_ in port.calls],['planning'])
            self.assertEqual(result['failure_reason'],'SOURCE_SUPPORT_CHANGED')
            self.assertNotIn('answer',result)

    def test_revision_or_prefix_withdrawal_during_answer_discards_delivery(self):
        for revision in (True,False):
            session=UniversalHCL();session.put_source('scene',SOURCE)
            def change(phase):
                if phase!='answer':return
                if revision:session.put_source('scene',SOURCE+'\n'+LATER)
                else:
                    key=next(c.content['source_span_id'] for c in session.workspace.core.claims.values()
                             if c.content.get('operation')=='ACTION_PREFIX_PLAN_CHECK')
                    session.workspace.core.withdraw(key)
            result=run(session,ORIGINAL,Stub(plan(OP()),callback=change))
            self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
            self.assertIn('SOURCE_',result['failure_reason'])
            self.assertNotIn('answer',result)

    def test_missing_multiple_sources_and_malformed_questions_stay_explicit(self):
        for ids in ([],['scene','other']):
            session=UniversalHCL();session.put_source('scene',SOURCE);session.put_source('other',SOURCE)
            result=run(session,ORIGINAL,Stub(plan(OP(ids=ids))))
            self.assertFalse(result['operations'][0]['executed'])
            self.assertEqual(result['operations'][0]['status'],
                             'C05_REQUIRES_ONE_SOURCE' if ids else 'SOURCE_PREREQUISITE_UNAVAILABLE')
        for query in ('Explain the action.', 'Why did Mira '+'x'*301+', considering their plans and appraisal of the delay?',
                       'Why did Mira leave the meeting, considering their plans and appraisal of '+'x'*161+'?'):
            _,_,receipt=entry(query=query)
            self.assertEqual(receipt['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
        repeated=SOURCE+'\nMira said, "I left the meeting."'
        _,_,receipt=entry(repeated)
        self.assertEqual(receipt['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
        _,_,receipt=entry('\n'.join(['Mira said, "I want to attend the concert."']*17))
        self.assertEqual(receipt['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
        three_goals='\n'.join(('Mira said, "I want to rest."',
            'Mira said, "I plan to leave the meeting in order to rest."',
            'Mira said, "I want to finish the report."',
            'Mira said, "I plan to leave the meeting in order to finish the report."',SOURCE))
        _,_,receipt=entry(three_goals)
        self.assertEqual(receipt['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')

    def test_selected_source_does_not_merge_other_domain_or_drop_outer_source(self):
        session=UniversalHCL();session.put_source('scene',SOURCE)
        other=SOURCE.replace('I believe the train is running.','I believe it is false that the train is running.')
        session.put_source('other',other);port=Stub(plan(OP()));receipt=run(session,ORIGINAL,port)
        _,native=output(receipt)
        self.assertEqual([s['source_id']for s in native['original_sources']],['scene'])
        self.assertEqual(native['explanations'][0]['disposition'],'CONDITIONALLY_SUPPORTED')
        final=json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual([s['text']for s in final['sources']],[SOURCE,other])

    def test_existing_workspace_parsing_cost_is_local_and_disclosed(self):
        session=UniversalHCL();session.put_source('scene',SOURCE);calls=[];original=semantic.prepare_semantics
        def counted(query,sources,**kwargs):
            calls.append((sources[0].text==SOURCE,kwargs.get('backend')))
            return original(query,sources,**kwargs)
        with patch.object(semantic,'prepare_semantics',side_effect=counted):result=run(session,ORIGINAL,Stub(plan(OP())))
        self.assertTrue(output(result)[0]['executed'])
        self.assertEqual(sum(full for full,_ in calls),5)
        self.assertEqual(sum(not full for full,_ in calls),2)
        self.assertTrue(all(backend is None for _,backend in calls))
        self.assertEqual(result['provider_calls'],0)

    def test_complete_c04_to_c05_flow_shares_support_and_fits_real_request_bound(self):
        session=UniversalHCL();session.put_source('scene',SOURCE)
        port=RequestBoundedStub(plan(operation('C04','How does Mira appraise the delay?',['scene']),OP()))
        result=run(session,ORIGINAL,port)
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertEqual([r['status']for r in result['operations']],['C04_EXECUTED','C05_EXECUTED'])
        self.assertTrue(all(r['checked_treatment_present']for r in result['operations']))
        self.assertTrue(set(result['operations'][0]['support_claim_ids'])&set(result['operations'][1]['support_claim_ids']))
        shared_appraisal=next(k for k,c in session.workspace.core.claims.items()
                              if c.content.get('operation')=='GOAL_APPRAISAL_AFFECT_CHANNEL_JOIN')
        self.assertTrue(all(shared_appraisal in row['support_claim_ids'] for row in result['operations']))
        final=json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual(final['question'],ORIGINAL)
        self.assertEqual(final['sources'][0]['text'],SOURCE)
        self.assertEqual([r['result']for r in final['hcl_operations']],[r['result']for r in result['operations']])
        self.assertEqual(set(port.encoded),{'planning','answer'})
        self.assertEqual(result['provider_calls'],0)

    def test_complete_combined_overflow_preserves_all_operations_without_answer_call(self):
        session=UniversalHCL();session.put_source('scene',SOURCE)
        port=RequestBoundedStub(plan(operation('C04','How does Mira appraise the delay?',['scene']),OP(),OP()))
        result=run(session,ORIGINAL,port)
        self.assertEqual([p for p,_ in port.calls],['planning'])
        self.assertEqual(port.quoted_phases,['planning','answer'])
        self.assertTrue(all(row['executed']for row in result['operations']))
        self.assertEqual(len(result['operations']),3)
        final=json.loads(result['actual_final_messages'][-1]['content'])
        self.assertEqual(final['sources'][0]['text'],SOURCE)
        self.assertEqual(len(final['hcl_operations']),3)
        self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
        self.assertNotIn('answer',result)
        self.assertEqual(result['provider_calls'],0)


if __name__=='__main__':unittest.main()
