"""Single-smoke routing and native admission controls; never model-effect evidence."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import hcl_entry_contract_smoke_candidate as r
import hcl_entry_contract_smoke_public as public
import hcl_entry_contract_smoke_native_public as native
import hcl_entry_contract_smoke_cli as cli
import test_hcl_entry_contract_smoke_candidate as fixture
import test_hcl_entry_contract_smoke_native_regressions as regression


def add_known_blocked_reader(response,index,request):
    if request['reasoning_effort']!='high':return
    value=json.loads(response['choices'][0]['message']['content'])
    op=dict(value['operations'][0],capability='B02');op.pop('input_mode',None)
    value['operations'].append(op);response['choices'][0]['message']['content']=json.dumps(value)


class DeclaredEntryGateTests(unittest.TestCase):
    def helper(self):
        obj=regression.NativeCaptureRegressions(methodName='runTest');obj.setUp();self.addCleanup(obj.doCleanups);return obj

    def test_single_case_configuration_freezes_blockers_modes_effort_and_before_final_rules(self):
        package=r.OfflinePackage.build(fixture.fixture_packet(),fixture.RUNTIME)
        self.assertEqual(set(package.value['requests']),{'control-0:HCL:planning'})
        self.assertEqual(set(package.value['declared_source_entry_blockers']),{'control-0'})
        payload=json.loads(r.messages(package.cases[0],'HCL')[-1]['content'])
        self.assertEqual(payload['executable_entry_contract']['caller_requirement'],'CHECKED_NATIVE_REQUIRED')
        self.assertEqual(r.declared_source_entry_blockers(package.cases[0]),package.value['declared_source_entry_blockers']['control-0'])
        self.assertEqual(payload['sources'],package.cases[0]['sources'])
        self.assertNotIn('private_evaluation',json.dumps(payload))
        self.assertEqual(package.value['reasoning_effort'],{'planning':'high','answer':'low'})
        for key in ('native_source_and_publication_integrity_required_before_final','actual_allowed_checked_native_required_before_final','no_second_stage','independent_source_review_still_required'):
            self.assertTrue(package.value['entry_requirements'][key])

    def test_known_blocked_choice_refuses_before_native_and_never_reserves_final(self):
        client=fixture.Client(add_known_blocked_reader);receipt,package=fixture.execute(client)
        row=receipt['arms'][0];check=row['entry_requirements']
        self.assertEqual(len(client.calls),1);self.assertIsNone(row['final_text'])
        self.assertEqual(row['status'],'BOUNDED_HCL_SCHEMA_SELECTION_OR_ADAPTER_FAILURE')
        self.assertEqual(row['selected_capabilities'],['B01','B02'])
        self.assertEqual(row['executed_capabilities'],[])
        self.assertIsNone(check)
        self.assertEqual(row['native_results'],0)
        # A captured empty actual projection is not a complete selected plan.
        evidence=public.export(receipt,package)
        with self.assertRaises(ValueError):public.validate_phase1_gate(package,evidence,{})
        self.assertEqual(receipt['reserved_cny'],str(r.HOLD_CNY['planning']))
        self.assertEqual([call['phase'] for call in receipt['calls']],['planning'])
        self.assertEqual(receipt['status'],'STOPPED_NO_RETRY')

    def test_second_stage_is_unavailable_before_any_call_or_directory(self):
        package=r.OfflinePackage.build(fixture.fixture_packet(),fixture.RUNTIME)
        for stage in (0,2,True,'1'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as directory:
                client=fixture.Client();target=Path(directory)/'run'
                with self.assertRaises(ValueError):r.run_offline(client,package,stage,target,clock=lambda:fixture.NOW)
                self.assertEqual(client.calls,[]);self.assertFalse(target.exists())
                with self.assertRaises(ValueError):cli.paths(Path(directory),stage)

    def test_other_checked_family_does_not_release_the_final(self):
        def other_family(response,index,request):
            if request['reasoning_effort']=='high':
                value=json.loads(response['choices'][0]['message']['content']);value['operations'][0]['capability']='C01'
                response['choices'][0]['message']['content']=json.dumps(value)
        client=fixture.Client(other_family);receipt,_=fixture.execute(client)
        self.assertEqual(len(client.calls),1);self.assertEqual(receipt['arms'][0]['checked_treatment'],['C01'])
        self.assertFalse(receipt['arms'][0]['entry_requirements']['allowed_family_checked_treatment_present'])
        self.assertIsNone(receipt['arms'][0]['final_text']);self.assertEqual(receipt['status'],'STOPPED_NO_RETRY')

    def test_passing_necessary_conditions_never_certify_answer_semantics(self):
        receipt,package=fixture.execute();evidence=public.export(receipt,package);review=fixture.review_fixture(package,evidence)
        self.assertFalse(receipt['arms'][0]['entry_requirements']['semantic_relevance_or_quality_certified'])
        review['gates']['all_key_facts_preserved']=False
        with self.assertRaises(ValueError):public.validate_phase1_gate(package,evidence,review)

    def test_model_pass_field_cannot_override_actual_capture(self):
        def forged(response,index,request):
            if request['reasoning_effort']=='high':
                value=json.loads(response['choices'][0]['message']['content']);value['entry_requirements']={'PRIVATE_PLANNER_CANARY':True}
                response['choices'][0]['message']['content']=json.dumps(value)
        client=fixture.Client(forged);receipt,package=fixture.execute(client)
        self.assertEqual(len(client.calls),1);self.assertEqual(receipt['arms'][0]['native_results'],0)
        self.assertNotIn('PRIVATE_PLANNER_CANARY',json.dumps(public.export(receipt,package)))

    def test_public_routing_forgery_is_recomputed_from_actual_native(self):
        helper=self.helper();receipt,bundle,_=helper.run_fixture()
        evidence=public.export(receipt,helper.package,helper.grant,native_bundle=bundle)
        changed=copy.deepcopy(evidence);changed['arms'][0]['entry_requirements'].update(known_source_entry_blockers_avoided=False,blocked_operation_indexes=[0])
        with self.assertRaisesRegex(ValueError,'ENTRY_REQUIREMENTS_MUST_BIND_ACTUAL_NATIVE_CAPTURE'):public.validate_actual_entry_requirements(changed,helper.package)
        changed_receipt=copy.deepcopy(receipt);changed_receipt['arms'][0]['entry_requirements']=changed['arms'][0]['entry_requirements']
        with self.assertRaisesRegex(ValueError,'ENTRY_REQUIREMENTS_MUST_BIND_ACTUAL_NATIVE_CAPTURE'):public.export(changed_receipt,helper.package,helper.grant,native_bundle=bundle)

    def test_partial_capture_cannot_certify_unobserved_selected_operations(self):
        helper=regression.EndToEndProjectionCommitmentTests(methodName='runTest');helper.setUp();self.addCleanup(helper.doCleanups)
        receipt,_,evidence=helper.public_fixture(partial=True)
        self.assertIsNone(receipt['arms'][0]['entry_requirements']);self.assertIsNone(evidence['arms'][0]['entry_requirements'])
        self.assertNotIn('UNDISPATCHED_PROPOSAL_MUST_STAY_PRIVATE',json.dumps(evidence))
        with self.assertRaises(ValueError):helper.run_gate(evidence)

    def test_pre_native_rejection_cannot_be_forged_into_a_passing_capture(self):
        helper=self.helper();receipt,bundle,_=helper.run_fixture(mutate=add_known_blocked_reader)
        evidence=public.export(receipt,helper.package,helper.grant,native_bundle=bundle)
        self.assertIsNone(evidence['arms'][0]['entry_requirements'])
        good,package=fixture.execute()
        changed=copy.deepcopy(evidence)
        changed['arms'][0]['entry_requirements']=copy.deepcopy(good['arms'][0]['entry_requirements'])
        with self.assertRaises(ValueError):public.validate_actual_entry_requirements(changed,helper.package)
        self.assertEqual(evidence['provider_calls'],0)
        self.assertEqual(evidence['offline_transport_calls'],1)
        self.assertEqual(evidence['remaining_authorized_calls'],0)

    def test_current_strict_contract_and_source_indexes_are_bound_before_transport(self):
        package=r.OfflinePackage.build(fixture.fixture_packet(),fixture.RUNTIME)
        case=package.cases[0]
        for mutation in ('caller_requirement','source_index'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as directory:
                ledger=r.Ledger(Path(directory)/'run',package,1,lambda:fixture.NOW,lambda:0)
                client=fixture.Client();port=r.BoundedPort(client,ledger,case['case_id']+':HCL')
                prompt=copy.deepcopy(r.messages(case,'HCL'));body=json.loads(prompt[-1]['content'])
                if mutation=='caller_requirement':
                    body['executable_entry_contract']['caller_requirement']='ORDINARY_EVIDENCE_LIMITS_ALLOWED'
                else:body['executable_entry_contract']['sources'][0]['source_index']=1
                prompt[-1]['content']=json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(',',':'))
                with self.assertRaises(ValueError):port.reservation_usd('planning',prompt)
                self.assertEqual(client.calls,[]);self.assertEqual(ledger.value['calls'],[])
                ledger.close()

    def test_bad_anchor_refuses_before_native_and_final_without_leaking_planner(self):
        def bad(response,index,request):
            if request['reasoning_effort']!='high':return
            value=json.loads(response['choices'][0]['message']['content']);op=value['operations'][0]
            op['input_mode']='semantic';op['semantic_candidates']=[dict(source_id=op['source_ids'][0],quote='ABSENT_ANCHOR_PRIVATE_CANARY',kind='event',content={'canonical_statement':'Mira: I believe the box is blue.'})]
            response['choices'][0]['message']['content']=json.dumps(value)
        client=fixture.Client(bad);receipt,package=fixture.execute(client)
        self.assertEqual(len(client.calls),1);self.assertEqual(receipt['arms'][0]['native_results'],0)
        self.assertEqual(receipt['arms'][0]['selected_capabilities'],[])
        self.assertNotIn('ABSENT_ANCHOR_PRIVATE_CANARY',json.dumps(public.export(receipt,package)))

    def test_same_record_validator_runs_before_final_and_again_at_capture_and_export(self):
        helper=self.helper()
        with patch.object(native,'validate_captured_native_record',wraps=native.validate_captured_native_record) as shared:
            receipt,bundle,client=helper.run_fixture();self.assertEqual(shared.call_count,2)
            expected=native.validate_captured_native_record(bundle['reviews'][0],helper.package.cases[0],helper.package.value['runtime_sha256'])
            evidence=public.export(receipt,helper.package,helper.grant,native_bundle=bundle);self.assertEqual(shared.call_count,4)
        self.assertEqual(len(client.calls),2);self.assertEqual(expected,evidence['approved_native_evidence']['records'][0])

    def test_integrity_flags_and_safe_boolean_index_types_cannot_forge_pass(self):
        receipt,package=fixture.execute();evidence=public.export(receipt,package)
        for status in (None,True,'REJECTED_UNAVAILABLE','NOT_CAPTURED'):
            changed=copy.deepcopy(evidence);changed['arms'][0]['native_integrity_status']=status
            with self.assertRaises(ValueError):public.validate_phase1_gate(package,changed,fixture.review_fixture(package,changed))
        good=receipt['arms'][0]['entry_requirements']
        for mutation in (dict(known_source_entry_blockers_avoided=1),dict(blocked_operation_indexes=[True]),dict(blocked_operation_indexes=[3]),dict(semantic_relevance_or_quality_certified=True)):
            with self.assertRaises(ValueError):public.clean_entry_requirements(dict(good,**mutation))

    def test_new_source_review_must_include_fixed_routing_condition(self):
        receipt,package=fixture.execute();evidence=public.export(receipt,package);review=fixture.review_fixture(package,evidence)
        self.assertTrue(public.validate_phase1_gate(package,evidence,review))
        review['gates']['known_source_entry_blockers_avoided']=False
        with self.assertRaises(ValueError):public.validate_phase1_gate(package,evidence,review)

    def test_single_smoke_money_time_and_permission_are_independent_from_old_grants(self):
        self.assertEqual(r.AUTH,'OWNER_APPROVED_HCL_ENTRY_CONTRACT_SMOKE_20261008_2_CALLS_2_30_CNY')
        self.assertEqual(r.MAX_CALLS,{1:2});self.assertEqual(str(r.TOTAL_CNY),'2.30')
        self.assertEqual(str(sum(r.SCHEDULE_CNY.values())),'2.219328')
        self.assertIsNone(r.EXPIRES);self.assertEqual(r.ELAPSED,{1:600});self.assertEqual(r.WAIT,180)
        with patch.object(r,'APPROVED',None),self.assertRaisesRegex(ValueError,'OWNER_APPROVAL_NOT_FROZEN'):r.require_time(fixture.NOW)

if __name__=='__main__':unittest.main()
