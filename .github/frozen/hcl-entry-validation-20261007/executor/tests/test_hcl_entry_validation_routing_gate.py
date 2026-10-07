"""New predeclared entry conditions; scripted controls, never model-effect evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import hcl_entry_validation_candidate as r
import hcl_entry_validation_public as public
import hcl_entry_validation_native_public as native
import test_hcl_entry_validation_candidate as fixture
import test_hcl_entry_validation_native_regressions as regression


def add_known_blocked_reader(response, index, request):
    if request['max_tokens'] != 16384:
        return
    value=json.loads(response['choices'][0]['message']['content'])
    value['operations'].append(dict(value['operations'][0],capability='B02'))
    response['choices'][0]['message']['content']=json.dumps(value)


class DeclaredEntryGateTests(unittest.TestCase):
    def test_new_configuration_freezes_selected_cases_blockers_and_separate_rule(self):
        package=r.OfflinePackage.build(fixture.fixture_packet(),fixture.RUNTIME)
        self.assertEqual(set(package.value['requests']),{'control-0:HCL:planning','control-3:HCL:planning','control-4:HCL:planning'})
        self.assertEqual(set(package.value['declared_source_entry_blockers']),{'control-0','control-3','control-4'})
        for case in (package.cases[0],package.cases[3],package.cases[4]):
            payload=json.loads(r.messages(case,'HCL')[-1]['content'])
            self.assertEqual(payload['literal_entry_blockers'],package.value['declared_source_entry_blockers'][case['case_id']])
            self.assertEqual(payload['sources'],case['sources'])
            self.assertNotIn('private_evaluation',json.dumps(payload))
        self.assertTrue(package.value['entry_requirements']['independent_source_review_still_required'])
        self.assertTrue(package.value['entry_requirements']['source_validated_native_capture_required_before_next_case'])
        self.assertEqual(package.packet,fixture.fixture_packet())

    def test_known_blocked_choice_retains_complete_final_native_and_two_calls(self):
        client=fixture.Client(add_known_blocked_reader);receipt,package=fixture.execute(client)
        row=receipt['arms'][0];check=row['entry_requirements']
        self.assertEqual(len(client.calls),2);self.assertEqual(row['status'],'ANSWER_ACCEPTED')
        self.assertIsNotNone(row['final_text']);self.assertTrue(row['citations_accepted'])
        self.assertEqual(row['selected_capabilities'],['B01','B02'])
        self.assertEqual(row['executed_capabilities'],['B01','B02'])
        self.assertEqual(check['blocked_operation_indexes'],[1]);self.assertFalse(check['known_source_entry_blockers_avoided'])
        self.assertTrue(check['allowed_family_checked_treatment_present'])
        self.assertEqual(receipt['status'],'STOPPED_NO_RETRY')
        evidence=public.export(receipt,package)
        self.assertEqual(evidence['arms'][0]['final_text'],row['final_text'])
        with self.assertRaises(ValueError):public.validate_phase1_gate(package,evidence,fixture.review_fixture(package,evidence))

    def test_stage2_known_blocked_first_case_stops_before_second_case_without_retry(self):
        client=fixture.Client(add_known_blocked_reader);receipt,package=fixture.execute(client,stage=2)
        evidence=public.export(receipt,package)
        self.assertEqual(len(client.calls),2)
        self.assertEqual(evidence['arms'][0]['status'],'ANSWER_ACCEPTED')
        self.assertEqual(evidence['arms'][1]['status'],'NOT_ATTEMPTED')
        self.assertIsNone(evidence['arms'][1]['entry_requirements'])
        self.assertEqual(evidence['remaining_authorized_calls'],0)
        self.assertEqual(evidence['reserved_cny'],'1.998144')
        self.assertEqual([case['case_id'] for case in evidence['cases']],['control-3','control-4'])

    def test_no_allowed_family_checked_treatment_stops_even_with_valid_other_native(self):
        def other_family(response,index,request):
            if request['max_tokens']==16384:
                value=json.loads(response['choices'][0]['message']['content']);value['operations'][0]['capability']='C01'
                response['choices'][0]['message']['content']=json.dumps(value)
        client=fixture.Client(other_family);receipt,package=fixture.execute(client,stage=2)
        row=receipt['arms'][0];check=row['entry_requirements']
        self.assertEqual(len(client.calls),2);self.assertEqual(row['status'],'ANSWER_ACCEPTED')
        self.assertEqual(row['checked_treatment'],['C01'])
        self.assertTrue(check['known_source_entry_blockers_avoided'])
        self.assertFalse(check['allowed_family_checked_treatment_present'])
        self.assertEqual(receipt['status'],'STOPPED_NO_RETRY')
        self.assertEqual(receipt['arms'][1]['status'],'NOT_ATTEMPTED')

    def test_passing_necessary_conditions_do_not_certify_semantics(self):
        receipt,package=fixture.execute();row=receipt['arms'][0]
        self.assertTrue(row['entry_requirements']['known_source_entry_blockers_avoided'])
        self.assertTrue(row['entry_requirements']['allowed_family_checked_treatment_present'])
        self.assertFalse(row['entry_requirements']['semantic_relevance_or_quality_certified'])
        evidence=public.export(receipt,package);review=fixture.review_fixture(package,evidence)
        review['gates']['all_key_facts_preserved']=False
        with self.assertRaises(ValueError):public.validate_phase1_gate(package,evidence,review)

    def test_model_supplied_pass_field_cannot_override_captured_facts(self):
        def forged(response,index,request):
            if request['max_tokens']==16384:
                value=json.loads(response['choices'][0]['message']['content'])
                value['entry_requirements']={'allowed_family_checked_treatment_present':True,'PRIVATE_PLANNER_CANARY':True}
                response['choices'][0]['message']['content']=json.dumps(value)
        client=fixture.Client(forged);receipt,package=fixture.execute(client)
        self.assertEqual(len(client.calls),1);self.assertEqual(receipt['arms'][0]['native_results'],0)
        self.assertFalse(receipt['arms'][0]['entry_requirements']['allowed_family_checked_treatment_present'])
        self.assertNotIn('PRIVATE_PLANNER_CANARY',json.dumps(public.export(receipt,package)))

    def test_public_rule_forgery_is_recomputed_from_exact_bound_actual_native(self):
        helper=regression.NativeCaptureRegressions(methodName='runTest');helper.setUp();self.addCleanup(helper.doCleanups)
        receipt,bundle,_=helper.run_fixture(mutate=add_known_blocked_reader)
        evidence=public.export(receipt,helper.package,helper.grant,native_bundle=bundle)
        changed=copy.deepcopy(evidence)
        changed['arms'][0]['entry_requirements'].update(known_source_entry_blockers_avoided=True,blocked_operation_indexes=[])
        with self.assertRaisesRegex(ValueError,'ENTRY_REQUIREMENTS_MUST_BIND_ACTUAL_NATIVE_CAPTURE'):
            public.validate_actual_entry_requirements(changed,helper.package)
        changed_receipt=copy.deepcopy(receipt)
        changed_receipt['arms'][0]['entry_requirements']=changed['arms'][0]['entry_requirements']
        with self.assertRaisesRegex(ValueError,'ENTRY_REQUIREMENTS_MUST_BIND_ACTUAL_NATIVE_CAPTURE'):
            public.export(changed_receipt,helper.package,helper.grant,native_bundle=bundle)

    def test_partial_capture_clears_stale_complete_rule_pass_and_preserves_record(self):
        helper=regression.EndToEndProjectionCommitmentTests(methodName='runTest');helper.setUp();self.addCleanup(helper.doCleanups)
        receipt,bundle,evidence=helper.public_fixture(partial=True)
        self.assertIsNone(receipt['arms'][0]['entry_requirements'])
        self.assertIsNone(evidence['arms'][0]['entry_requirements'])
        self.assertEqual(evidence['approved_native_evidence']['records'][0]['actual_operation_count'],1)
        self.assertNotIn('UNDISPATCHED_PROPOSAL_MUST_STAY_PRIVATE',json.dumps(evidence))
        with self.assertRaises(ValueError):helper.run_gate(evidence)

    def test_projection_capture_failure_closes_before_next_stage2_case(self):
        first,package=fixture.execute()
        evidence=public.export(first,package);review=fixture.review_fixture(package,evidence)
        with tempfile.TemporaryDirectory() as directory, patch.object(native,'native_projection_from_capture',side_effect=ValueError('PRIVATE_ERROR_NOT_PUBLIC')):
            client=fixture.Client()
            receipt=r.run_offline(client,package,2,Path(directory)/'run',clock=lambda:fixture.NOW,
                phase1_evidence=evidence,phase1_review=review,phase1_review_sha256=r.digest(review))
        self.assertEqual(len(client.calls),2)
        self.assertIsNotNone(receipt['arms'][0]['final_text'])
        self.assertEqual(receipt['arms'][0]['native_projection_status'],'REJECTED_UNAVAILABLE')
        self.assertEqual(receipt['arms'][1]['status'],'NOT_ATTEMPTED')
        self.assertEqual(receipt['status'],'STOPPED_NO_RETRY')

    def test_new_source_review_must_attest_to_additional_frozen_routing_condition(self):
        receipt,package=fixture.execute();evidence=public.export(receipt,package);review=fixture.review_fixture(package,evidence)
        self.assertTrue(public.validate_phase1_gate(package,evidence,review))
        review['gates']['known_source_entry_blockers_avoided']=False
        with self.assertRaises(ValueError):public.validate_phase1_gate(package,evidence,review)

    def test_safe_boolean_and_index_types_are_not_coerced(self):
        receipt,_=fixture.execute();good=receipt['arms'][0]['entry_requirements']
        for mutate in (lambda x:x.update(known_source_entry_blockers_avoided=1),
                       lambda x:x.update(blocked_operation_indexes=[True]),
                       lambda x:x.update(blocked_operation_indexes=[3]),
                       lambda x:x.update(semantic_relevance_or_quality_certified=True)):
            bad=copy.deepcopy(good);mutate(bad)
            with self.assertRaises(ValueError):public.clean_entry_requirements(bad)

    def test_stage2_mixed_good_native_and_bad_anchor_stops_after_original_round(self):
        helper=regression.NativeCaptureRegressions(methodName='runTest');helper.setUp();self.addCleanup(helper.doCleanups)
        def mixed(response,index,request):
            if request['max_tokens'] != 16384:return
            value=json.loads(response['choices'][0]['message']['content'])
            rejected=copy.deepcopy(value['operations'][0])
            source=json.loads(request['messages'][-1]['content'])['sources'][0]
            rejected['semantic_candidates']=[dict(source_id=source['source_id'],quote='ABSENT_ANCHOR_MUST_STAY_PRIVATE',start=0,kind='event',content={'canonical_statement':source['text'].splitlines()[0]})]
            value['operations'].append(rejected)
            response['choices'][0]['message']['content']=json.dumps(value)
        receipt,bundle,client=helper.run_fixture(stage=2,mutate=mixed)
        self.assertEqual(len(client.calls),2)
        self.assertEqual(receipt['status'],'STOPPED_NO_RETRY')
        self.assertEqual(receipt['arms'][0]['status'],'ANSWER_ACCEPTED')
        self.assertEqual(receipt['arms'][0]['native_integrity_status'],'REJECTED_UNAVAILABLE')
        self.assertEqual(receipt['arms'][1]['status'],'NOT_ATTEMPTED')
        self.assertIsNone(receipt['arms'][1]['entry_requirements'])
        self.assertEqual(len(bundle['reviews']),1)
        self.assertIn('ABSENT_ANCHOR_MUST_STAY_PRIVATE',json.dumps(bundle))
        safe=helper.assert_block_rejected(receipt,bundle)
        self.assertEqual(safe['arms'][0]['final_text'],receipt['arms'][0]['final_text'])
        self.assertEqual(safe['reserved_cny'],'1.998144')
        self.assertEqual(safe['offline_transport_calls'],2)
        self.assertNotIn('ABSENT_ANCHOR_MUST_STAY_PRIVATE',json.dumps(safe))

    def _stage2_capture_mutation(self, mutate, canary):
        first,package=fixture.execute()
        evidence=public.export(first,package);review=fixture.review_fixture(package,evidence)
        original=r.Ledger.native_review
        def changed_capture(ledger,case,result):
            changed=copy.deepcopy(result);mutate(changed)
            return original(ledger,case,changed)
        with tempfile.TemporaryDirectory() as directory, patch.object(r.Ledger,'native_review',new=changed_capture):
            client=fixture.Client();target=Path(directory)/'run'
            receipt=r.run_offline(client,package,2,target,clock=lambda:fixture.NOW,
                phase1_evidence=evidence,phase1_review=review,phase1_review_sha256=r.digest(review))
            bundle=json.loads((target/'native-review-private.json').read_text())
        self.assertEqual(len(client.calls),2)
        self.assertEqual(receipt['status'],'STOPPED_NO_RETRY')
        self.assertEqual(receipt['arms'][0]['status'],'ANSWER_ACCEPTED')
        self.assertEqual(receipt['arms'][0]['native_projection_status'],'CAPTURED')
        self.assertEqual(receipt['arms'][0]['native_integrity_status'],'REJECTED_UNAVAILABLE')
        self.assertEqual(receipt['arms'][1]['status'],'NOT_ATTEMPTED')
        self.assertTrue(all('usage' in call for call in receipt['calls']))
        grant={'public_native_evidence_permission':fixture.native_permission_fixture(package)}
        with self.assertRaises(ValueError):public.export(receipt,package,grant,native_bundle=bundle)
        safe=public.export(receipt,package,grant,native_bundle=None)
        self.assertEqual(safe['arms'][0]['final_text'],receipt['arms'][0]['final_text'])
        self.assertEqual(safe['reserved_cny'],'1.998144')
        self.assertEqual(safe['offline_transport_calls'],2)
        self.assertIsNone(safe['approved_native_evidence'])
        self.assertIn(canary,json.dumps(bundle));self.assertNotIn(canary,json.dumps(safe))

    def test_stage2_forbidden_captured_field_stops_before_next_dispatch(self):
        def mutate(result):result['operations'][0]['result']['private_history']='PRIVATE_CAPTURE_FIELD_CANARY'
        self._stage2_capture_mutation(mutate,'PRIVATE_CAPTURE_FIELD_CANARY')

    def test_stage2_captured_result_drift_stops_before_next_dispatch(self):
        def mutate(result):result['operations'][0]['status']='NATIVE_RESULT_DRIFT_CANARY'
        self._stage2_capture_mutation(mutate,'NATIVE_RESULT_DRIFT_CANARY')

    def test_same_record_validator_is_used_by_capture_and_native_export(self):
        helper=regression.NativeCaptureRegressions(methodName='runTest');helper.setUp();self.addCleanup(helper.doCleanups)
        with patch.object(native,'validate_captured_native_record',wraps=native.validate_captured_native_record) as shared:
            receipt,bundle,_=helper.run_fixture()
            self.assertEqual(shared.call_count,1)
            expected=native.validate_captured_native_record(bundle['reviews'][0],helper.package.cases[0],helper.package.value['runtime_sha256'])
            evidence=public.export(receipt,helper.package,helper.grant,native_bundle=bundle)
            self.assertEqual(shared.call_count,3)
        self.assertEqual(expected,evidence['approved_native_evidence']['records'][0])
        self.assertEqual(receipt['arms'][0]['native_integrity_status'],'VALIDATED')

    def test_integrity_flag_cannot_be_missing_rejected_or_non_enum_at_gate(self):
        receipt,package=fixture.execute();evidence=public.export(receipt,package)
        for status in (None,True,'REJECTED_UNAVAILABLE','NOT_CAPTURED'):
            changed=copy.deepcopy(evidence);changed['arms'][0]['native_integrity_status']=status
            with self.assertRaises(ValueError):public.validate_phase1_gate(package,changed,fixture.review_fixture(package,changed))
        changed=copy.deepcopy(receipt);changed['arms'][0]['native_integrity_status']=True
        with self.assertRaisesRegex(ValueError,'EXACT_NATIVE_INTEGRITY_STATE_REQUIRED'):public.export(changed,package)

    def test_current_fee_time_and_two_plus_four_caps_do_not_reopen_old_budgets(self):
        self.assertEqual(r.APPROVED,'2026-10-07T16:11:19Z')
        self.assertEqual(r.AUTH,'OWNER_APPROVED_HCL_ENTRY_VALIDATION_20261007_6_CALLS_6_CNY')
        self.assertEqual(r.MAX_CALLS,{1:2,2:4});self.assertEqual(str(r.TOTAL_CNY),'6')
        self.assertEqual(str(sum(r.SCHEDULE_CNY.values())),'5.994432')
        self.assertIsNone(r.EXPIRES)
        self.assertEqual(r.ELAPSED,{1:600,2:1200});self.assertEqual(r.WAIT,180)

if __name__=='__main__':unittest.main()
