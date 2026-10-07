"""Existing C02 consumes planned structured interpretations; original prose stays evidence."""
import copy,json,unittest
from unittest.mock import patch
from hcl.cognition import UniversalHCL
from hcl.cognition.action_explanations import prepare_explanations
from hcl.v1.compact import expand_reader_context
from tests.test_v1_universal_question import Stub,operation,plan,run
from tests.test_v1_universal_appraisal import RequestBoundedStub

QUOTES=('Kellan wanted to inspect the gauge.',
    'Kellan had decided to open the valve to inspect the gauge.',
    'Kellan reported that, at the time, Kellan knew about the valve.',
    'Kellan reported that, at the time, Kellan could open the valve.',
    'Kellan opened the valve.')
LINES=('Kellan: I want to inspect the gauge.',
    'Kellan: I plan to open the valve in order to inspect the gauge.',
    'Kellan: At the time, I knew about the valve.',
    'Kellan: At the time, I could open the valve.',
    'Kellan: I opened the valve.')
SOURCE='\n'.join(QUOTES)
QUERY='Why did Kellan open the valve?'
ORIGINAL='What can explain Kellan opening the valve, and what remains unresolved?'


def candidates(quotes=QUOTES,lines=LINES):
    return [dict(source_id='maintenance',quote=q,kind='event',content=dict(canonical_statement=line))for q,line in zip(quotes,lines)]


def selected(rows=None,query=QUERY):
    return dict(operation('C02',query,['maintenance']),semantic_candidates=candidates()if rows is None else rows)


def execute(quotes=QUOTES,lines=LINES,*,rows=None,bounded=False,query=QUERY):
    s=UniversalHCL();s.put_source('maintenance','\n'.join(quotes))
    port=(RequestBoundedStub if bounded else Stub)(plan(selected(candidates(quotes,lines)if rows is None else rows,query)))
    return s,port,run(s,ORIGINAL,port)


def state(result):
    row=result['operations'][0]
    assert row['status']=='EXISTING_CONDITIONAL_C02_EXECUTED',row
    expanded=expand_reader_context(row['result'])
    return row,expanded,expanded['conditional_cognition']['state']['checked_action_explanations']


class PlannedExplanationInputTests(unittest.TestCase):
    def test_prose_to_real_native_explanations_to_complete_answer_uses_two_phases(self):
        with patch('hcl.cognition.action_explanations.prepare_explanations',wraps=prepare_explanations)as native:
            s,port,result=execute(bounded=True)
        self.assertEqual(native.call_count,1)
        row,expanded,payload=state(result)
        self.assertEqual(result['status'],'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertEqual([phase for phase,_ in port.calls],['planning','answer'])
        self.assertEqual(result['hcl_execution']['native_results'],1)
        self.assertEqual(row['additional_provider_calls'],0);self.assertTrue(row['checked_treatment_present'])
        self.assertFalse(row['semantic_certification']);self.assertEqual(row['semantic_input_origin'],'METERED_PLANNING_RESPONSE')
        self.assertEqual([e['disposition']for e in payload['explanations']],['CONDITIONALLY_SUPPORTED','WEAKENED_BY_COUNTEREVIDENCE','WEAKENED_BY_COUNTEREVIDENCE'])
        self.assertEqual(payload['winning_motive'],'NOT_INFERRED')
        self.assertTrue(all(e['actual_motive']=='NOT_ESTABLISHED'for e in payload['explanations']))
        self.assertEqual(expanded['sources'],[dict(source_id='maintenance',version=1,text=SOURCE)])
        self.assertEqual(payload['original_source'],'\n'.join(LINES))
        self.assertNotEqual(payload['original_source'],SOURCE)
        self.assertEqual(len(expanded['shared_semantic_binding']['assumptions']),5)
        self.assertTrue(all(b['translation_authority']=='UNVERIFIED_TRANSLATION_HYPOTHESIS'for b in expanded['shared_semantic_binding']['translations']))
        final=json.loads(port.calls[-1][1][-1]['content'])
        self.assertEqual(final['question'],ORIGINAL);self.assertEqual(final['sources'],expanded['sources'])
        self.assertIn('not verbatim source',row['preparation_policy'])
        self.assertTrue(all(len(raw)<=36000 for raw in port.encoded.values()))
        self.assertEqual(result['provider_calls'],0)
        self.assertTrue(all(s.workspace.core.support_statuses()[key]=='SUPPORT_AVAILABLE'for key in row['support_claim_ids']))

    def test_existing_direct_prose_and_literal_tool_interfaces_remain_unchanged(self):
        for source,expected in ((SOURCE,False),('\n'.join(LINES),True)):
            s=UniversalHCL();s.put_source('maintenance',source)
            port=Stub(plan(operation('C02',QUERY,['maintenance'])));result=run(s,ORIGINAL,port)
            row=result['operations'][0]
            self.assertEqual(row['status'],'C02_EXECUTED')
            self.assertEqual(bool(row['result']['explanations']),expected)
            self.assertNotIn('semantic_input_origin',row)

    def test_explicit_ignorance_revises_conditions_without_selecting_an_actual_motive(self):
        quotes=list(QUOTES);lines=list(LINES)
        quotes[2]=quotes[2].replace('knew','did not know');lines[2]=lines[2].replace('knew','did not know')
        payload=state(execute(quotes,lines)[2])[2]
        self.assertEqual(payload['explanations'][0]['disposition'],'WEAKENED_BY_COUNTEREVIDENCE')
        self.assertEqual(payload['explanations'][1]['disposition'],'CONDITIONALLY_SUPPORTED')
        self.assertEqual(payload['winning_motive'],'NOT_INFERRED')

    def test_conflicting_knowledge_and_opportunity_remain_conditional_conflicts(self):
        quotes=list(QUOTES)+['Kellan also reported not knowing about the valve at that time.',
                              'Kellan also reported being unable to open the valve at that time.']
        lines=list(LINES)+['Kellan: At the time, I did not know about the valve.',
                          'Kellan: At the time, I could not open the valve.']
        payload=state(execute(quotes,lines)[2])[2]
        self.assertEqual(payload['explanations'][0]['disposition'],'CONFLICTING_PREMISES')
        self.assertEqual(payload['winning_motive'],'NOT_INFERRED')

    def test_current_or_later_knowledge_is_not_backfilled_to_action_time(self):
        quotes=[q for i,q in enumerate(QUOTES)if i!=2]+['After opening the valve, Kellan learned about it.']
        lines=[line for i,line in enumerate(LINES)if i!=2]+['Kellan: I now know about the valve.']
        payload=state(execute(quotes,lines)[2])[2]
        self.assertFalse(any(f['condition']['kind']=='KNOWLEDGE'for f in payload['conditions']))
        self.assertEqual(payload['explanations'][0]['disposition'],'UNRESOLVED')

    def test_later_goal_and_plan_do_not_create_an_earlier_goal_explanation(self):
        order=(2,3,4,0,1)
        payload=state(execute([QUOTES[i]for i in order],[LINES[i]for i in order])[2])[2]
        self.assertFalse(any(e['hypothesis'].startswith('goal-directed')for e in payload['explanations']))

    def test_two_pre_action_goals_remain_competing_conditional_explanations(self):
        quotes=list(QUOTES[:2])+['Kellan wanted to cool the pipes.','Kellan planned to open the valve to cool the pipes.']+list(QUOTES[2:])
        lines=list(LINES[:2])+['Kellan: I want to cool the pipes.','Kellan: I plan to open the valve in order to cool the pipes.']+list(LINES[2:])
        _,port,result=execute(quotes,lines,bounded=True);payload=state(result)[2]
        supported=[row for row in payload['explanations']if row['disposition']=='CONDITIONALLY_SUPPORTED']
        self.assertEqual(len(supported),2)
        self.assertTrue(all(row['hypothesis'].startswith('goal-directed')for row in supported))
        self.assertTrue(all(row['exclusive']=='NOT_ASSUMED'for row in supported))
        self.assertEqual(payload['winning_motive'],'NOT_INFERRED');self.assertEqual(len(port.calls),2)

    def test_explicit_negated_action_choice_keeps_opportunity_negation_distinct(self):
        for unable in (False,True):
            modifier='could not'if unable else'could'
            quotes=[QUOTES[2],f'Kellan reported that at the time Kellan {modifier} choose not to open the valve.','Kellan did not open the valve.']
            lines=[LINES[2],f'Kellan: At the time, I {modifier} choose to not open the valve.','Kellan: I did not open the valve.']
            payload=state(execute(quotes,lines,query='Why did Kellan not open the valve?')[2])[2]
            self.assertEqual(payload['action'],'not open the valve')
            self.assertEqual(payload['explanations'][0]['disposition'],'WEAKENED_BY_COUNTEREVIDENCE'if unable else'CONDITIONALLY_SUPPORTED')
            self.assertEqual(payload['winning_motive'],'NOT_INFERRED')

    def test_candidate_array_order_cannot_reorder_source_action_history(self):
        payload=state(execute(rows=list(reversed(candidates())))[2])[2]
        self.assertEqual(payload['original_source'],'\n'.join(LINES))
        self.assertEqual(payload['explanations'][0]['disposition'],'CONDITIONALLY_SUPPORTED')

    def test_repeated_action_stays_ambiguous_without_older_or_latest_fallback(self):
        _,port,result=execute(list(QUOTES)+['Kellan opened the valve again.'],list(LINES)+[LINES[-1]])
        self.assertEqual(len(port.calls),1);self.assertEqual(result['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')
        self.assertEqual(len(result['plan']['operations'][0]['semantic_candidates']),6)

    def test_other_actor_conditions_are_not_reassigned_to_target_actor(self):
        quotes=list(QUOTES);lines=list(LINES)
        quotes[2]=quotes[2].replace('Kellan','Noor');lines[2]=lines[2].replace('Kellan','Noor')
        payload=state(execute(quotes,lines)[2])[2]
        self.assertFalse(any(f['condition']['kind']=='KNOWLEDGE'for f in payload['conditions']))
        self.assertEqual(payload['explanations'][0]['disposition'],'UNRESOLVED')

    def test_missing_action_is_a_native_insufficient_result_not_fake_positive_treatment(self):
        _,port,result=execute(QUOTES[:-1],LINES[:-1]);row,_,payload=state(result)
        self.assertEqual(payload['status'],'SYSTEM_INSUFFICIENT');self.assertFalse(row['checked_treatment_present'])
        self.assertEqual(result['hcl_execution']['native_results'],1)
        self.assertEqual([phase for phase,_ in port.calls],['planning','answer'])

    def test_malformed_query_and_native_row_limit_refuse_without_answer(self):
        cases=[dict(query='Explain possible motives for Kellan.')]
        cases.append(dict(quotes=list(QUOTES)+[f'Kellan mentioned topic {i}.'for i in range(16)],
                          lines=list(LINES)+[f'Kellan: I mentioned topic {i}.'for i in range(16)]))
        for case in cases:
            _,port,result=execute(**case)
            self.assertEqual(len(port.calls),1);self.assertEqual(result['operations'][0]['status'],'ADAPTER_REJECTED_NOT_COMPLETED')

    def test_fabricated_actor_or_source_quote_cannot_create_native_result(self):
        for field in ('actor','quote'):
            rows=candidates()
            if field=='actor':
                for row in rows:row['content']['canonical_statement']=row['content']['canonical_statement'].replace('Kellan','Invented')
            else:rows[0]['quote']='Kellan never reported this.'
            _,port,result=execute(rows=rows)
            self.assertEqual(len(port.calls),1);self.assertEqual(result['hcl_execution']['native_results'],0)

    def test_source_and_interpretation_withdrawal_stop_the_answer(self):
        for kind in ('source','interpretation','projection'):
            s=UniversalHCL();s.put_source('maintenance',SOURCE);original=s._execute
            def withdraw(*args):
                value=original(*args)
                binding=expand_reader_context(value['result'])['shared_semantic_binding']
                key=(s.workspace._spans['maintenance']if kind=='source'else binding['translation_ids'][0]if kind=='projection'else binding['translations'][0]['candidate_id'])
                s.workspace.core.withdraw(key);return value
            port=Stub(plan(selected()))
            with patch.object(s,'_execute',side_effect=withdraw):result=run(s,ORIGINAL,port)
            self.assertEqual(result['failure_reason'],'SOURCE_SUPPORT_CHANGED')
            self.assertEqual(len(port.calls),1);self.assertEqual(result['hcl_execution']['native_results'],1)

    def test_revision_preserves_original_version_and_invalidates_old_results(self):
        s,_,first=execute();old=first['operations'][0]['support_claim_ids']
        revised=SOURCE.replace('knew about','did not know about');s.put_source('maintenance',revised)
        self.assertTrue(all(s.workspace.core.support_statuses()[key]!='SUPPORT_AVAILABLE'for key in old))
        rows=candidates();rows[2]['quote']=rows[2]['quote'].replace('knew','did not know')
        rows[2]['content']['canonical_statement']=rows[2]['content']['canonical_statement'].replace('knew','did not know')
        port=Stub(plan(selected(rows)));result=run(s,ORIGINAL,port)
        _,expanded,payload=state(result)
        self.assertEqual(expanded['sources'],[dict(source_id='maintenance',version=2,text=revised)])
        self.assertTrue(all(row['source_version']==2 for row in expanded['shared_semantic_binding']['translations']))
        self.assertEqual(payload['explanations'][0]['disposition'],'WEAKENED_BY_COUNTEREVIDENCE')

    def test_only_original_source_quotes_can_be_delivered(self):
        for quote,expected in ((QUOTES[0],'ANSWERED_WITH_EXPLICIT_LIMITS'),(LINES[0],'ANSWER_SOURCE_REVIEW_FAILED')):
            class Cited(Stub):
                def complete(self,phase,messages):
                    value=super().complete(phase,messages)
                    if phase=='answer':
                        body=json.loads(value['text']);body['source_citations']=[dict(source_id='maintenance',quote=quote,version=1)]
                        value['text']=json.dumps(body)
                    return value
            s=UniversalHCL();s.put_source('maintenance',SOURCE);port=Cited(plan(selected()))
            result=run(s,ORIGINAL,port);self.assertEqual(result['status'],expected)
            self.assertEqual(json.loads(result['answer_raw'])['source_citations'][0]['quote'],quote)

    def test_compact_combination_fits_without_dropping_source_or_native_results(self):
        s=UniversalHCL();s.put_source('maintenance',SOURCE)
        # The whole large original question is retained in planning and answer.
        original=ORIGINAL+' '+('Context remains explicit. '*250)
        port=RequestBoundedStub(plan(selected(),operation('C01',ORIGINAL,['maintenance']),operation('C03',ORIGINAL,['maintenance'])))
        result=run(s,original,port)
        # Compact structural separators now fit this full synthetic request.
        # This is transport capacity, not evidence about model answer quality.
        self.assertEqual(len(port.calls),2);self.assertIn('answer',result)
        self.assertLessEqual(len(port.encoded['answer']),36000)
        self.assertEqual(result['hcl_execution']['native_results'],3)
        self.assertEqual(len(result['plan']['operations'][0]['semantic_candidates']),5)
        self.assertEqual(len(result['operations']),3)
        final=json.loads(result['actual_final_messages'][-1]['content'])
        self.assertEqual(final['sources'][0]['text'],SOURCE);self.assertEqual(final['question'],original)
        self.assertEqual(final['hcl_operations'],result['operations'])


if __name__=='__main__':unittest.main()
