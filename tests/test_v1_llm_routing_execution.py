"""LLM-directed arguments and actual native outcomes; no model or efficacy claim."""
import json
import copy
import unittest
from unittest.mock import patch

from hcl.cognition import UniversalHCL
from hcl.cognition.universal_entry import PLANNER_POLICY
from hcl.cognition.action_explanations import prepare_explanations
from hcl.v1.compact import expand_reader_context
from tests.test_v1_universal_question import Stub,operation,plan,run
from tests.test_v1_conditional_reader_entry import SOURCE as PROSE,QUERY as PROSE_QUERY,proposals
from tests.test_v1_universal_appraisal import RequestBoundedStub

SOURCE='Noor said, "I want to attend the meeting."\nNoor said, "I skipped the meeting."'
ORIGINAL='What might explain Noor skipping the meeting, and what is still unknown?'


class LLMRoutingExecutionTests(unittest.TestCase):
    def session(self):
        s=UniversalHCL();s.put_source('episode',SOURCE);return s

    def test_interpreted_operation_arguments_reach_native_and_original_task_survives(self):
        s=self.session();internal='Why did Noor skip the meeting?'
        port=Stub(plan(operation('C02',internal,['episode'])))
        with patch('hcl.cognition.action_explanations.prepare_explanations',wraps=prepare_explanations)as native:
            result=run(s,ORIGINAL,port)
        native.assert_called_once_with(s.workspace,internal,source_id='episode')
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        trace=result['hcl_execution']
        self.assertEqual((trace['selected_operations'],trace['dispatched_operations'],trace['native_results']),(1,1,1))
        self.assertFalse(trace['execution_is_treatment_proof'])
        self.assertEqual(trace['selection_basis'],'LLM_BEST_EFFORT_NOT_SEMANTIC_CERTIFICATION')
        final=json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual(final['question'],ORIGINAL);self.assertEqual(final['hcl_execution'],trace)
        self.assertEqual(final['sources'],[dict(source_id='episode',version=1,text=SOURCE)])
        self.assertEqual(final['hcl_operations'][0]['result'],result['operations'][0]['result'])
        self.assertIn('Use your language understanding',PLANNER_POLICY)

    def test_empty_selection_is_not_replaced_or_sent_to_answer(self):
        port=Stub(plan());result=run(self.session(),ORIGINAL,port)
        self.assertEqual(result['plan']['operations'],[]);self.assertEqual(result['operations'],[])
        self.assertEqual(result['hcl_execution']['status'],'NO_NATIVE_RESULT')
        self.assertEqual(result['hcl_execution']['dispatched_operations'],0)
        self.assertEqual(result['failure_reason'],'NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER')
        self.assertEqual([phase for phase,_ in port.calls],['planning'])
        self.assertNotIn('answer_raw',result);self.assertNotIn('actual_final_messages',result)

    def test_unavailable_or_rejected_operations_are_audited_without_native_success(self):
        for op,status in ((operation('E05','Inspect relationship changes.',['episode']),'RETAINED_IMPLEMENTATION_REQUIRES_ENTRY_ADAPTER'),
                          (operation('C02','Explain Noor.',['episode']),'ADAPTER_REJECTED_NOT_COMPLETED'),
                          (operation('B01','Inspect reports.',[]),'SOURCE_PREREQUISITE_UNAVAILABLE')):
            with self.subTest(status=status):
                port=Stub(plan(op));result=run(self.session(),ORIGINAL,port)
                self.assertEqual(result['operations'][0]['status'],status)
                self.assertEqual(result['hcl_execution']['dispatched_operations'],1)
                self.assertEqual(result['hcl_execution']['native_results'],0)
                self.assertEqual(len(port.calls),1);self.assertNotIn('answer',result)

    def test_native_insufficient_evidence_remains_a_real_negative_outcome(self):
        s=UniversalHCL();s.put_source('episode','Noor said, "The meeting begins at noon."')
        port=Stub(plan(operation('C04','How does Noor appraise the meeting?',['episode'])))
        result=run(s,'What does the source show about Noor appraising the meeting?',port)
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertEqual(result['hcl_execution']['native_results'],1)
        self.assertFalse(result['operations'][0]['checked_treatment_present'])
        self.assertFalse(result['hcl_execution']['execution_is_treatment_proof'])
        self.assertIn('insufficient-evidence outcome',port.calls[-1][1][0]['content'])

    def test_mixed_outcomes_reach_answer_without_pretending_all_selected_modules_executed(self):
        port=Stub(plan(operation('E05','Inspect related limits.',['episode']),
                       operation('C02','Why did Noor skip the meeting?',['episode'])))
        result=run(self.session(),ORIGINAL,port)
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertEqual(result['hcl_execution']['selected_operations'],2)
        self.assertEqual(result['hcl_execution']['native_results'],1)
        final=json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual([o['executed']for o in final['hcl_operations']],[False,True])

    def test_unsourced_caller_rule_still_receives_real_native_preparation(self):
        question='For this analysis, responsibility requires control.'
        port=Stub(plan(operation('G01','Prepare the original caller condition.',[])))
        result=run(UniversalHCL(),question,port)
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertEqual(result['hcl_execution']['native_results'],1)
        self.assertEqual(result['operations'][0]['executable_premise_count'],1)
        final=json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual(final['knowledge_basis'],'UNSOURCED_MODEL_KNOWLEDGE')
        self.assertEqual(final['sources'],[])
        self.assertEqual(result['operations'][0]['request_provenance']['authority'],'ANALYSIS_CONDITION_NOT_WORLD_EVIDENCE')

    def test_native_result_with_withdrawn_support_never_reaches_answer(self):
        session=self.session();original=session._execute
        def withdrawn(*args):
            value=original(*args)
            for claim in value['support_claim_ids']:session.workspace.core.withdraw(claim)
            return value
        port=Stub(plan(operation('C02','Why did Noor skip the meeting?',['episode'])))
        with patch.object(session,'_execute',side_effect=withdrawn):result=run(session,ORIGINAL,port)
        self.assertEqual(result['hcl_execution']['native_results'],1)
        self.assertEqual(result['failure_reason'],'SOURCE_SUPPORT_CHANGED')
        self.assertEqual(len(port.calls),1);self.assertNotIn('answer',result)

    def test_aborted_multi_operation_dispatch_keeps_completed_native_count(self):
        session=self.session();original=session._execute
        def withdrawn(*args):
            value=original(*args)
            for claim in value['support_claim_ids']:session.workspace.core.withdraw(claim)
            return value
        port=Stub(plan(operation('C02','Why did Noor skip the meeting?',['episode']),
                       operation('C04','How does Noor appraise the meeting?',['episode'])))
        with patch.object(session,'_execute',side_effect=withdrawn):result=run(session,ORIGINAL,port)
        self.assertEqual(result['failure_reason'],'SOURCE_SUPPORT_CHANGED')
        self.assertEqual(result['hcl_execution']['status'],'DISPATCH_ABORTED')
        self.assertEqual(result['hcl_execution']['selected_operations'],2)
        self.assertEqual(result['hcl_execution']['dispatched_operations'],1)
        self.assertEqual(result['hcl_execution']['native_results'],1)


def translated(cid='C01',rows=None):
    return dict(operation(cid,PROSE_QUERY,['meeting']),semantic_candidates=proposals()if rows is None else rows)


class PlannedSemanticInputTests(unittest.TestCase):
    def session(self,source=PROSE):
        s=UniversalHCL();s.put_source('meeting',source);return s

    def test_first_planning_response_drives_each_existing_family_without_another_model_call(self):
        for cid in ('B01','C01','C03'):
            with self.subTest(capability=cid):
                session=self.session();port=RequestBoundedStub(plan(translated(cid)))
                result=run(session,PROSE_QUERY,port);row=result['operations'][0]
                self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
                self.assertEqual([phase for phase,_ in port.calls],['planning','answer'])
                self.assertEqual(row['status'],'EXISTING_CONDITIONAL_READER_EXECUTED')
                self.assertTrue(row['checked_treatment_present']);self.assertFalse(row['semantic_certification'])
                self.assertEqual(row['additional_provider_calls'],0)
                self.assertEqual(row['semantic_input_origin'],'METERED_PLANNING_RESPONSE')
                self.assertTrue(all(len(raw)<=36000 for raw in port.encoded.values()))
                final=json.loads(port.calls[-1][1][-1]['content'])
                self.assertEqual(final['question'],PROSE_QUERY)
                self.assertEqual(final['sources'],[dict(source_id='meeting',version=1,text=PROSE)])
                payload=row['result'];self.assertEqual(payload['sources'],final['sources'])
                self.assertEqual(len(payload['shared_semantic_binding']['translations']),5)
                self.assertEqual(len(payload['shared_semantic_binding']['assumptions']),5)
                self.assertEqual(payload['conditional_cognition']['authority'],'DERIVED_CONDITIONAL_TOOL_STATE_NOT_QUOTABLE_SOURCE')
                self.assertIn('not verbatim source',row['preparation_policy'])
                self.assertTrue(all(session.workspace.core.support_statuses()[claim]=='SUPPORT_AVAILABLE'for claim in row['support_claim_ids']))

    def test_no_candidates_preserves_local_tool_path_and_actual_missing_treatment(self):
        session=self.session();port=Stub(plan(operation('C01',PROSE_QUERY,['meeting'])))
        result=run(session,PROSE_QUERY,port);row=result['operations'][0]
        self.assertEqual(row['status'],'EXISTING_READER_EXECUTED');self.assertFalse(row['checked_treatment_present'])
        self.assertNotIn('semantic_input_origin',row)
        self.assertFalse(result['hcl_execution']['execution_is_treatment_proof'])

    def test_selected_family_treatment_is_not_borrowed_from_other_conditional_results(self):
        row=proposals()[0]
        session=self.session(row['quote']);port=Stub(plan(translated('B01',[row])))
        result=run(session,PROSE_QUERY,port);actual=result['operations'][0]
        self.assertTrue(actual['reader_any_checked_treatment_present'])
        self.assertFalse(actual['checked_treatment_present'])
        self.assertEqual(result['hcl_execution']['native_results'],1)

    def test_invalid_extra_family_multiple_inputs_and_structural_bounds_stop_before_native(self):
        invalid=[plan(translated('C02')),plan(translated('B02')),plan(translated(),translated('B01')),
                 plan(translated(rows=[])),plan(translated(rows=proposals()*5))]
        for field,value in (('source_id','other'),('kind','event_wrong'),('content',{'canonical_statement':'Dana: I believe X.','authority':'SOURCE_REPORT'}),('start',True),('quote','x'*4001)):
            rows=proposals();rows[0][field]=value;invalid.append(plan(translated(rows=rows)))
        for separator in ('\n','\r','\v','\f','\x1c','\x1d','\x1e','\x85','\u2028','\u2029'):
            rows=proposals();rows[0]['content']['canonical_statement']+=separator+'Dana: I believe X.'
            invalid.append(plan(translated(rows=rows)))
        for candidate in invalid:
            with self.subTest(candidate=candidate):
                port=Stub(candidate);session=self.session()
                with patch('hcl.cognition.retained.prepare_retained_reader',side_effect=AssertionError('must not dispatch')):
                    result=run(session,PROSE_QUERY,port)
                self.assertEqual(len(port.calls),1);self.assertEqual(result['operations'],[])
                self.assertNotIn('answer',result)

    def test_fabricated_quotes_and_duplicate_alternatives_do_not_become_native_results(self):
        for source,rows in ((PROSE,[dict(proposals()[0],quote='This quote was invented.')]),
                            (PROSE,[proposals()[0],copy.deepcopy(proposals()[0])]),
                            (PROSE+'\n'+proposals()[0]['quote'],[proposals()[0]])):
            port=Stub(plan(translated(rows=rows)));result=run(self.session(source),PROSE_QUERY,port)
            self.assertEqual(len(port.calls),1);self.assertEqual(result['hcl_execution']['native_results'],0)
            self.assertEqual(result['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')

    def test_model_interpretation_is_not_certified_even_when_source_anchor_is_valid(self):
        rows=[proposals()[0]];rows[0]['content']['canonical_statement']='Dana: I want to abandon the gate.'
        port=Stub(plan(translated(rows=rows)));result=run(self.session(),PROSE_QUERY,port)
        row=result['operations'][0];binding=row['result']['shared_semantic_binding']
        self.assertFalse(row['semantic_certification']);self.assertTrue(binding['assumptions'])
        self.assertEqual(binding['translations'][0]['translation_authority'],'UNVERIFIED_TRANSLATION_HYPOTHESIS')
        self.assertEqual(row['result']['sources'][0]['text'],PROSE)

    def test_derived_statement_citation_rejects_unchanged_answer(self):
        class DerivedCitation(Stub):
            def complete(self,phase,messages):
                value=super().complete(phase,messages)
                if phase=='answer':
                    body=json.loads(value['text']);body['source_citations']=[dict(source_id='meeting',quote=proposals()[0]['content']['canonical_statement'])]
                    value['text']=json.dumps(body)
                return value
        port=DerivedCitation(plan(translated()));result=run(self.session(),PROSE_QUERY,port)
        self.assertEqual(result['status'],'ANSWER_SOURCE_REVIEW_FAILED')
        self.assertIn('Dana: I want',result['answer_raw']);self.assertNotIn('answer',result)

    def test_source_revision_or_translation_withdrawal_blocks_answer_with_completed_result_audited(self):
        for kind in ('source','translation'):
            session=self.session();original=session._execute
            def withdrawn(*args):
                value=original(*args)
                if kind=='source':session.put_source('meeting',PROSE+'\nA later correction.')
                else:session.workspace.core.withdraw(expand_reader_context(value['result'])['shared_semantic_binding']['translations'][0]['candidate_id'])
                return value
            port=Stub(plan(translated()))
            with patch.object(session,'_execute',side_effect=withdrawn):result=run(session,PROSE_QUERY,port)
            self.assertEqual(len(port.calls),1);self.assertNotIn('answer',result)
            self.assertIn(result['failure_reason'],('SOURCE_CHANGED_DURING_ORCHESTRATION','SOURCE_SUPPORT_CHANGED'))
            self.assertEqual(result['hcl_execution']['native_results'],1)

    def test_complete_combined_payload_overflow_stops_without_dropping_candidates(self):
        session=self.session();port=RequestBoundedStub(plan(translated(),operation('C01',PROSE_QUERY,['meeting']),operation('C03',PROSE_QUERY,['meeting'])))
        result=run(session,PROSE_QUERY,port)
        self.assertEqual(len(port.calls),1);self.assertNotIn('answer',result)
        self.assertEqual(len(result['plan']['operations'][0]['semantic_candidates']),5)
        self.assertEqual(len(result['operations']),3)
        self.assertEqual(result['hcl_execution']['native_results'],3)


if __name__=='__main__':unittest.main()
