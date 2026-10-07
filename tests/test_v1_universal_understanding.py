"""Target-bound finite acknowledgment; scripted wiring is not private understanding."""
import json
import unittest
from dataclasses import asdict
from unittest.mock import patch

from hcl.cognition import UniversalHCL
from hcl.cognition.capability_catalog import CATALOG
from hcl.cognition.mutual_understanding import prepare_mutual_understanding
from tests.test_v1_mutual_understanding import SOURCE,QUERY
from tests.test_v1_commitments import SOURCE as PROMISE_SOURCE, QUERY as PROMISE_QUERY
from tests.test_v1_universal_appraisal import RequestBoundedStub
from tests.test_v1_universal_question import Stub,operation,plan,run

ORIGINAL='Distinguish source-reported acknowledgment from private understanding.'
TARGET='the meeting is at noon'
REVISION='Mira said, "I revise my meaning from the meeting is at noon to the meeting is at one."'
DOUBT='Noor said, "I do not understand Mira to mean that the meeting is at noon."'
OP=lambda query=QUERY,ids=('scene',):operation('D02',query,list(ids))
SEPARATORS=('\r','\v','\f','\x1c','\x1d','\x1e','\x85','\u2028','\u2029')


def entry(source=SOURCE,query=QUERY,bounded=False):
    session=UniversalHCL();session.put_source('scene',source)
    port=(RequestBoundedStub if bounded else Stub)(plan(OP(query)))
    return session,port,run(session,ORIGINAL,port)


def output(result):
    row=result['operations'][0]
    assert row['status']=='D02_EXECUTED',row
    return row,row['result']


class UniversalUnderstandingTests(unittest.TestCase):
    def test_complete_native_payload_policy_and_support_reach_original_answer_context(self):
        session,port,result=entry(bounded=True);row,payload=output(result)
        native=prepare_mutual_understanding(session.workspace,QUERY,source_id='scene')
        self.assertEqual(payload,native.payload)
        self.assertEqual(row['support_claim_ids'],list(native.claim_ids))
        self.assertTrue(row['checked_treatment_present'])
        self.assertEqual(payload['actual_comprehension'],'NOT_ESTABLISHED')
        self.assertEqual(payload['infinite_common_knowledge'],'NOT_INFERRED')
        final=json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual(final['question'],ORIGINAL)
        self.assertEqual(final['sources'],[dict(source_id='scene',version=1,text=SOURCE)])
        self.assertEqual(final['hcl_operations'][0]['result'],payload)
        self.assertTrue(all(len(raw)<=36000 for raw in port.encoded.values()))
        self.assertEqual(result['provider_calls'],0)

    def test_catalog_describes_finite_target_contract_without_forced_selection(self):
        session,port,_=entry();contract=CATALOG['D02'].entry_contract
        self.assertEqual(contract.question_origin,'OPERATION_QUESTION')
        self.assertEqual((contract.minimum_sources,contract.maximum_sources),(1,1))
        inventory=json.loads(port.calls[0][1][-1]['content'])['capability_inventory']
        self.assertEqual(next(r for r in inventory if r['capability_id']=='D02'),json.loads(json.dumps({key:value for key,value in asdict(CATALOG['D02']).items() if key!='implementation'})))
        self.assertEqual(run(session,ORIGINAL,Stub(plan()))['operations'],[])

    def test_missing_each_delivery_link_remains_incomplete_without_private_comprehension(self):
        lines=SOURCE.splitlines()
        for index,field in ((1,'original_receipt_at_interpretation'),(3,'interpretation_receipt_at_confirmation'),(5,'confirmation_receipt_current')):
            _,_,result=entry('\n'.join(line for i,line in enumerate(lines)if i!=index));row,payload=output(result)
            self.assertTrue(row['checked_treatment_present'])
            self.assertEqual(payload['status'],'ACKNOWLEDGMENT_DELIVERY_INCOMPLETE')
            self.assertFalse(payload['acknowledgment_chains'][0][field]['received'])
            self.assertEqual(payload['actual_comprehension'],'NOT_ESTABLISHED')

    def test_later_receipt_cannot_backfill_either_earlier_link(self):
        sources=(SOURCE.replace("Narrator: Noor heard Mira's last statement.","Narrator: Noor did not hear Mira's last statement.",1).replace('Narrator: Mira heard',"Narrator: Noor later heard Mira's last statement.\nNarrator: Mira heard"),
                 SOURCE.replace("Narrator: Mira heard Noor's last statement.\n",'')+"\nNarrator: Mira later heard Noor's last statement.")
        for source in sources:
            _,_,result=entry(source);payload=output(result)[1]
            self.assertEqual(payload['status'],'ACKNOWLEDGMENT_DELIVERY_INCOMPLETE')

    def test_bare_superseded_meaning_and_unrelated_chains_do_not_count_as_treatment(self):
        bare=SOURCE.splitlines()[0]+'\n'+REVISION
        _,_,result=entry(bare);row,payload=output(result)
        self.assertEqual(payload['status'],'SUPERSEDED_MEANING')
        self.assertTrue(row['support_claim_ids']);self.assertFalse(row['checked_treatment_present'])
        for query in (QUERY.replace('noon','one'),QUERY.replace('noon','Noon'),QUERY.replace('noon?','noon.?')):
            _,_,result=entry(query=query);row,payload=output(result)
            self.assertTrue(payload['acknowledgment_chains'])
            self.assertFalse(row['checked_treatment_present'])

    def test_acknowledged_history_and_new_meaning_stay_separate(self):
        session,_,before=entry();old=prepare_mutual_understanding(session.workspace,QUERY,source_id='scene')
        session.put_source('scene',SOURCE+'\n'+REVISION)
        with self.assertRaisesRegex(ValueError,'source changed'):old.messages(session.workspace)
        after=run(session,ORIGINAL,Stub(plan(OP())));row,payload=output(after)
        self.assertTrue(row['checked_treatment_present'])
        self.assertEqual(payload['status'],'SUPERSEDED_MEANING')
        self.assertEqual(payload['acknowledgment_chains'][0]['status'],'SUPERSEDED_MEANING_HISTORICAL_ACKNOWLEDGMENT')
        self.assertEqual(output(before)[1]['status'],'BOUNDED_MUTUALLY_ACKNOWLEDGED')
        current=run(session,ORIGINAL,Stub(plan(OP(QUERY.replace('noon','one')))))
        self.assertFalse(output(current)[0]['checked_treatment_present'])
        self.assertEqual(json.loads(after['actual_final_messages'][-1]['content'])['sources'][0]['version'],2)

    def test_matching_doubt_is_negative_evidence_and_other_or_embedded_doubt_is_not(self):
        _,_,result=entry(DOUBT);row,payload=output(result)
        self.assertTrue(row['checked_treatment_present']);self.assertFalse(payload['acknowledgment_chains'])
        self.assertEqual(payload['status'],'EXPLICIT_UNCERTAINTY_OR_CONFLICT')
        self.assertEqual(payload['actual_comprehension'],'NOT_ESTABLISHED')
        for source,query in ((DOUBT,QUERY.replace('noon','one')),('If '+DOUBT,QUERY)):
            _,_,result=entry(source,query);self.assertFalse(output(result)[0]['checked_treatment_present'])

    def test_summary_target_is_taken_only_from_this_supported_native_result(self):
        session=UniversalHCL();session.put_source('scene',SOURCE)
        unrelated=prepare_mutual_understanding(session.workspace,QUERY.replace('noon','one'),source_id='scene')
        self.assertEqual(session.workspace.core.claims[unrelated.payload['dependency_claim_id']].content['target'],'the meeting is at one')
        result=run(session,ORIGINAL,Stub(plan(OP())))
        self.assertTrue(output(result)[0]['checked_treatment_present'])

    def test_okay_nested_belief_and_third_party_confirmation_are_not_requested_chains(self):
        for source in ('\n'.join(SOURCE.splitlines()[:2])+ '\nNoor said, "Okay."',
                       '\n'.join(SOURCE.splitlines()[:2])+ '\nNoor said, "I believe Mira believes the meeting is at noon."',
                       SOURCE.replace('Mira said, "I confirm','Kai said, "I confirm')):
            _,_,result=entry(source);self.assertFalse(output(result)[0]['checked_treatment_present'])

    def test_branch_specific_doubt_reports_do_not_claim_receipt_view_validation(self):
        for recipient in ('Nöor','N'+'o'*32):
            source=DOUBT.replace('Noor',recipient);query=QUERY.replace('Noor',recipient)
            _,_,result=entry(source,query);row,payload=output(result)
            self.assertTrue(row['checked_treatment_present'])
            self.assertFalse(payload['acknowledgment_chains'])
            self.assertEqual(payload['actual_comprehension'],'NOT_ESTABLISHED')
            _,_,result=entry(SOURCE.replace('Noor',recipient),query)
            self.assertEqual(result['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')

    def test_each_dangerous_separator_refuses_the_native_false_positive_before_preparation(self):
        speech=[SOURCE.splitlines()[i]for i in (0,2,4)]
        for separator in SEPARATORS:
            source='Noor said, "Okay."'+separator+'\n'.join(speech)
            with self.subTest(separator=repr(separator)),patch('hcl.cognition.mutual_understanding.prepare_mutual_understanding')as native:
                _,port,result=entry(source);native.assert_not_called()
                self.assertEqual(result['operations'][0]['status'],'D02_REQUIRES_LF_OR_CRLF_SOURCE')
                self.assertFalse(result['operations'][0]['executed'])
                self.assertEqual(json.loads(port.calls[-1][1][-1]['content'])['sources'][0]['text'].encode(),source.encode())
        for separator in ('\n','\r\n'):
            _,_,result=entry('Noor said, "Okay."'+separator+'\n'.join(speech))
            row,payload=output(result)
            self.assertEqual(payload['status'],'ACKNOWLEDGMENT_DELIVERY_INCOMPLETE')
            self.assertTrue(all(not payload['acknowledgment_chains'][0][k]['received']for k in ('original_receipt_at_interpretation','interpretation_receipt_at_confirmation','confirmation_receipt_current')))

    def test_missing_multiple_sources_query_bounds_and_nonactual_receipts_refuse(self):
        for ids in ([],['scene','other']):
            session=UniversalHCL();session.put_source('scene',SOURCE);session.put_source('other',SOURCE)
            result=run(session,ORIGINAL,Stub(plan(OP(ids=ids))))
            self.assertEqual(result['operations'][0]['status'],'D02_REQUIRES_ONE_SOURCE'if ids else'SOURCE_PREREQUISITE_UNAVAILABLE')
        for query in ('Do they understand each other?',QUERY.replace('Noor','Mira'),QUERY.replace(TARGET,'x'*251)):
            _,_,result=entry(query=query);self.assertEqual(result['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
        source=SOURCE.replace("Narrator: Noor heard Mira's last statement.","Narrator: In a hypothetical scene:\nNarrator: Noor heard Mira's last statement.",1)
        _,_,result=entry(source);self.assertFalse(result['operations'][0].get('checked_treatment_present',False))
        resumed=source.replace('Noor said, "I understand','Narrator: In reality:\nNoor said, "I understand')
        _,_,result=entry(resumed);self.assertEqual(result['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')

    def test_source_row_and_candidate_limits_remain_explicit(self):
        source=SOURCE+'\n'+'\n'.join('Noor said, "Ordinary words."'for _ in range(15))
        _,_,result=entry(source);self.assertEqual(result['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
        source=SOURCE+'\n'+'\n'.join('Noor said, "I believe the road is safe."'for _ in range(12))
        _,_,result=entry(source);self.assertEqual(result['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')

    def test_chain_summary_or_source_withdrawal_stops_before_answer(self):
        for kind in ('FINITE_ACKNOWLEDGMENT_CHAIN','MUTUAL_UNDERSTANDING_SUMMARY','source'):
            session=UniversalHCL();session.put_source('scene',SOURCE);execute=session._execute
            def changed(*args):
                row=execute(*args)
                key=session.workspace._spans['scene']if kind=='source'else next(k for k,c in session.workspace.core.claims.items()if c.content.get('operation')==kind)
                session.workspace.core.withdraw(key);return row
            port=Stub(plan(OP()))
            with patch.object(session,'_execute',side_effect=changed):result=run(session,ORIGINAL,port)
            self.assertEqual([phase for phase,_ in port.calls],['planning'])
            self.assertEqual(result['failure_reason'],'SOURCE_SUPPORT_CHANGED');self.assertNotIn('answer',result)

    def test_revision_or_support_change_during_answer_discards_delivery(self):
        for revision in (True,False):
            session=UniversalHCL();session.put_source('scene',SOURCE)
            def change(phase):
                if phase!='answer':return
                if revision:session.put_source('scene',SOURCE+'\n'+REVISION)
                else:session.workspace.core.withdraw(next(k for k,c in session.workspace.core.claims.items()if c.content.get('operation')=='FINITE_ACKNOWLEDGMENT_CHAIN'))
            result=run(session,ORIGINAL,Stub(plan(OP()),callback=change))
            self.assertIn('SOURCE_',result['failure_reason']);self.assertNotIn('answer',result)

    def test_combined_d01_d02_keeps_both_native_results_and_other_outer_source(self):
        source=PROMISE_SOURCE+'\n'+SOURCE;session=UniversalHCL();session.put_source('scene',source)
        session.put_source('other','Noor said, "Unrelated words."')
        port=RequestBoundedStub(plan(operation('D01',PROMISE_QUERY,['scene']),OP()))
        result=run(session,ORIGINAL,port)
        self.assertEqual([r['status']for r in result['operations']],['D01_EXECUTED','D02_EXECUTED'])
        self.assertTrue(all(r['checked_treatment_present']for r in result['operations']))
        final=json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual(final['hcl_operations'],result['operations'])
        self.assertEqual(final['sources'][0]['text'],source);self.assertEqual(len(final['sources']),2)
        self.assertTrue(all(len(raw)<=36000 for raw in port.encoded.values()))

    def test_complete_planning_overflow_makes_no_backend_call(self):
        _,port,result=entry(SOURCE+'\n'+'x'*16000,bounded=True)
        self.assertEqual(port.calls,[])
        self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED')

    def test_complete_answer_overflow_retains_all_history_and_operations(self):
        targets=[f'the meeting is at {time}'+' as agreed'*10 for time in ('noon','one','two')]
        source=SOURCE.replace(TARGET,targets[0])
        for old,new in zip(targets,targets[1:]):
            source+='\n'+f'Mira said, "I revise my meaning from {old} to {new}."'+'\n'+'\n'.join(SOURCE.replace(TARGET,new).splitlines()[1:])
        query=QUERY.replace(TARGET,targets[-1]);session=UniversalHCL();session.put_source('scene',source)
        port=RequestBoundedStub(plan(OP(query),OP(query),OP(query)))
        result=run(session,ORIGINAL,port)
        self.assertEqual([phase for phase,_ in port.calls],['planning'])
        self.assertEqual(result['status'],'ORCHESTRATION_UNAVAILABLE_OR_FAILED')
        self.assertEqual(len(result['operations']),3)
        for row in result['operations']:
            self.assertTrue(row['executed'])
            self.assertEqual(row['result']['original_source'],source)
            self.assertEqual(len(row['result']['acknowledgment_chains']),3)
        self.assertNotIn('answer',result)


if __name__=='__main__':unittest.main()
