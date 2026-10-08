"""R4/R5 regressions: unrelated synthetic fixtures and offline transport only.

No credentials, provider clients, account readers, network, repository mutation,
publication, grants, markers, or activated workflows. Existing fixture approvals
are synthetic control inputs, never owner authorization.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import hcl_entry_contract_smoke_candidate as r
import hcl_entry_contract_smoke_native_public as native
import hcl_entry_contract_smoke_public as public
from test_hcl_entry_contract_smoke_candidate import (
    Client, NOW, RUNTIME, fixture_packet, native_permission_fixture, review_fixture,
)


class NativeCaptureRegressions(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.package = r.OfflinePackage.build(fixture_packet(), RUNTIME)
        self.permission = native_permission_fixture(self.package)
        self.grant = {'public_native_evidence_permission': self.permission}
        self.serial = 0

    def run_fixture(self, stage=1, mutate=None, empty=False):
        self.serial += 1
        kwargs = {}
        if stage == 2:
            first, _, _ = self.run_fixture()
            evidence = public.export(first, self.package)
            review = review_fixture(self.package, evidence)
            kwargs.update(phase1_evidence=evidence, phase1_review=review,
                          phase1_review_sha256=r.digest(review))
        self.serial += 1
        directory = self.root / str(self.serial)
        client = Client(mutate=mutate, empty=empty)
        receipt = r.run_offline(client, self.package, stage, directory,
                                clock=lambda: NOW, **kwargs)
        self.assertTrue(all(not call['provider_call'] for call in receipt['calls']))
        bundle = json.loads((directory / 'native-review-private.json').read_text())
        return receipt, bundle, client

    def argument(self, case, capability='B01', *, semantic=None):
        argument = dict(capability=capability, question=case['question'],
                        source_ids=[case['sources'][0]['source_id']], bindings=[])
        if capability in ('B01','C01','C02','C03'):argument['input_mode']='semantic' if semantic is not None else 'literal'
        if semantic is not None:
            argument['semantic_candidates'] = [semantic]
        return argument

    def semantic(self, case, **changes):
        source = case['sources'][0]
        quote = source['text'].splitlines()[0]
        row = dict(source_id=source['source_id'], quote=quote, start=0,
                   kind='event', content={'canonical_statement': quote})
        row.update(changes)
        return row

    def private_review(self, case, arguments, *, dispatch_count=None):
        session = native._session(case)
        outputs = []
        for argument in arguments[:dispatch_count]:
            try:
                result = session._execute(argument, case['question'])
            except ValueError:
                result = dict(capability=argument['capability'],
                              status='ADAPTER_REJECTED_NOT_COMPLETED', executed=False)
            outputs.append(result)
        return r.private_native_review(case, dict(plan={'operations': arguments},
                                                 operations=outputs))

    def assert_block_rejected(self, receipt, bundle):
        before = copy.deepcopy(receipt)
        with self.assertRaises(ValueError):
            public.export(receipt, self.package, self.grant, native_bundle=bundle)
        self.assertEqual(receipt, before)
        # The CLI follows this exact ordinary-first path when rejecting a native
        # block, retaining the conservative receipt instead of exposing text.
        result = public.export(receipt, self.package, self.grant, native_bundle=None)
        self.assertEqual(result['native_publication_status'], 'AUTHORIZED_BUT_NATIVE_UNAVAILABLE_GATE_CLOSED')
        self.assertIsNone(result['approved_native_evidence'])
        self.assertEqual(result['budget_state'], 'CLOSED_NO_TRANSFER_NO_RETRY')
        self.assertEqual(result['reserved_cny'], receipt['reserved_cny'])
        self.assertEqual(result['arms'][0]['native_results'], receipt['arms'][0]['native_results'])
        self.assertEqual(result['offline_transport_calls'], len(receipt['calls']))
        return result

    def published_from_capture(self, receipt, bundle):
        """Construct the old accepted shape, with all new integrity fields valid."""
        records = []
        cases = {case['case_id']: case for case in self.package.cases}
        for row in bundle['reviews']:
            case = cases[row['case_id']]
            operations = []
            for index, output in enumerate(row['native_outputs']):
                argument = row['validated_operation_arguments'][index]
                operations.append(dict(operation_index=index,
                    capability_id=argument['capability'], arguments_origin=native.ARGUMENT_ORIGIN,
                    source_validated_arguments=copy.deepcopy(argument),
                    native_result_and_policy=copy.deepcopy(output),
                    arguments_sha256=r.digest(argument), native_output_sha256=r.digest(output)))
            records.append(dict(schema='hcl-entry-contract-smoke-approved-native-record-v1',
                case_id=row['case_id'], arm='HCL', source_roots=copy.deepcopy(row['source_roots']),
                original_question_sha256=hashlib.sha256(case['question'].encode()).hexdigest(),
                private_native_review_sha256=r.digest(row), operations=operations,
                actual_operation_count=len(operations),
                actual_executed_count=sum(op['executed'] for op in row['native_outputs']),
                runtime_sha256=self.package.value['runtime_sha256']))
        for record in records: record['native_projection_sha256'] = r.digest(record)
        return dict(schema='hcl-entry-contract-smoke-approved-native-evidence-v1',
            destination=native.DESTINATION, permission_sha256=r.digest(self.permission),
            packet_sha256=self.package.value['packet_sha256'],
            package_sha256=r.digest(self.package.value), stage=bundle['stage'],
            receipt_sha256=r.digest(receipt), records=records, record_count=len(records),
            semantic_certification=False, reviewed_native_relevance=False)

    def test_r4_model_anchor_is_rejected_before_dispatch_and_cannot_be_published(self):
        def inject(response,index,request):
            if request['reasoning_effort']!='high':return
            plan=json.loads(response['choices'][0]['message']['content']);case=self.package.cases[0]
            plan['operations'][0]['input_mode']='semantic'
            plan['operations'][0]['semantic_candidates']=[self.semantic(case,quote='NON_SOURCE_CANARY',content={'canonical_statement':'Mira: I believe NON_SOURCE_CANARY.'})]
            response['choices'][0]['message']['content']=json.dumps(plan)
        receipt,bundle,client=self.run_fixture(mutate=inject)
        self.assertEqual(len(client.calls),1);self.assertEqual(receipt['arms'][0]['native_results'],0)
        self.assertEqual(bundle['reviews'][0]['validated_operation_arguments'],[])
        output=public.export(receipt,self.package,self.grant,native_bundle=bundle)
        self.assertNotIn('NON_SOURCE_CANARY',json.dumps(output))
        case=self.package.cases[0];arg=self.argument(case,semantic=self.semantic(case,quote='NON_SOURCE_CANARY'))
        forged=self.private_review(case,[arg]);bad=dict(bundle,reviews=[forged])
        with self.assertRaises(ValueError):native.export_native_records(bad,self.package,self.permission)


    def test_r4_absent_quote_wrong_offsets_and_shape_valid_other_source_quote_reject(self):
        cases = self.package.cases
        trials = [(cases[0], self.semantic(cases[0], quote='ABSENT_CANARY')),
                  (cases[0], self.semantic(cases[0], start=1)),
                  (cases[0], self.semantic(cases[0], start=True)),
                  (cases[0], self.semantic(cases[0], start=-1)),
                  (cases[0], self.semantic(cases[0], start=10000)),
                  (cases[1], self.semantic(cases[1], quote='No receipt of the update is recorded.')),
                  (cases[1], self.semantic(cases[1], source_id=cases[1]['sources'][1]['source_id']))]
        absent_without_offset = self.semantic(cases[0], quote='ABSENT_NO_OFFSET_CANARY')
        del absent_without_offset['start']; trials.append((cases[0], absent_without_offset))
        for case, semantic in trials:
            with self.subTest(case=case['case_id'], semantic=semantic):
                argument = self.argument(case, semantic=semantic)
                review = self.private_review(case, [argument])
                bundle = dict(schema='hcl-entry-contract-smoke-private-native-review-bundle-v1',
                    package_sha256=r.digest(self.package.value),
                    stage=1 if case == cases[0] else 2, reviews=[review])
                with self.assertRaises(ValueError):
                    native.export_native_records(bundle, self.package, self.permission)
                published = self.published_from_capture({}, bundle)
                with self.assertRaises(ValueError):
                    native.validate_published_native_evidence(published, self.package, self.permission)

    def test_r4_binding_checks_do_not_rely_on_runtime_plan_validator(self):
        case = self.package.cases[1]
        source = case['sources'][0]
        for changes in ({'quote': 'ABSENT_BINDING'}, {'start': 1}, {'start': True},
                        {'source_id': case['sources'][1]['source_id']}):
            binding = dict(role='actor', source_id=source['source_id'], start=0, quote='Mira')
            binding.update(changes)
            argument = self.argument(case); argument['bindings'] = [binding]
            session = native._session(case)
            with self.subTest(changes=changes), patch.object(session, '_validate_plan', return_value=None):
                with self.assertRaisesRegex(ValueError, 'EXACT_FROZEN_SOURCE_ANCHOR_REQUIRED'):
                    native._validated_arguments(session, [argument])

    def test_r4_valid_offset_optional_anchor_and_actual_evidence_are_not_stripped(self):
        receipt, bundle, _ = self.run_fixture()
        case = self.package.cases[0]
        for has_offset in (True, False):
            semantic = self.semantic(case)
            if not has_offset:
                del semantic['start']
            argument = self.argument(case, semantic=semantic)
            argument['bindings'] = [dict(role='actor', source_id=case['sources'][0]['source_id'], start=0, quote='Mira')]
            review = self.private_review(case, [argument])
            changed = copy.deepcopy(bundle); changed['reviews'] = [review]
            # Standalone replay still proves source anchoring, not receipt provenance.
            published = native.export_native_records(changed, self.package, self.permission)
            self.assertTrue(native.validate_published_native_evidence(published, self.package, self.permission))
            op = published['records'][0]['operations'][0]
            self.assertEqual(op['source_validated_arguments'], argument)
            self.assertEqual(op['native_result_and_policy'], review['native_outputs'][0])
            self.assertEqual(op['arguments_origin'], native.ARGUMENT_ORIGIN)
            self.assertFalse(published['semantic_certification'])

    def test_r4_frozen_source_version_and_text_root_mismatch_reject(self):
        _, bundle, _ = self.run_fixture()
        for changes in ({'version': 2}, {'version': True}, {'version': 1.0}, {'text_sha256': 'a' * 64}, {'source_id': 'other-source'}):
            changed = copy.deepcopy(bundle); changed['reviews'][0]['source_roots'][0].update(changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'EXACT_SYNTHETIC_SOURCE_ROOTS_REQUIRED'):
                native.export_native_records(changed, self.package, self.permission)

    def test_r5_valid_same_case_c01_record_cannot_replace_actual_b01_for_either_stage(self):
        for stage in (1,):
            with self.subTest(stage=stage):
                receipt, bundle, _ = self.run_fixture(stage)
                original = public.export(receipt, self.package, self.grant, native_bundle=bundle)
                self.assertEqual(original['native_publication_status'], 'AUTHORIZED_BOUNDED_NATIVE_EVIDENCE')
                self.assertTrue(native.validate_published_native_evidence(
                    original['approved_native_evidence'], self.package, self.permission, receipt=receipt))
                case = next(case for case in self.package.cases if case['case_id'] == bundle['reviews'][0]['case_id'])
                alternate = self.private_review(case, [self.argument(case, 'C01')])
                changed = copy.deepcopy(bundle); changed['reviews'][0] = alternate
                standalone = native.export_native_records(changed, self.package, self.permission)
                self.assertEqual(standalone['records'][0]['operations'][0]['capability_id'], 'C01')
                self.assertTrue(native.validate_published_native_evidence(standalone, self.package, self.permission))
                self.assert_block_rejected(receipt, changed)
                with self.assertRaisesRegex(ValueError, 'EXACT_RECEIPT_NATIVE_CAPTURE_HASH_REQUIRED'):
                    native.export_native_records(changed, self.package, self.permission, receipt=receipt)

    def test_r5_package_stage_case_arm_and_capture_hash_binding(self):
        receipt, bundle, _ = self.run_fixture()
        mutations = [lambda b: b.update(package_sha256='a' * 64),
                     lambda b: b.update(stage=2),
                     lambda b: b['reviews'][0].update(case_id='control-1'),
                     lambda b: b['reviews'][0]['validated_operation_arguments'][0].update(question='Other valid question?'),
                     lambda b: b['reviews'][0]['native_outputs'][0].update(status='CHANGED')]
        for mutate in mutations:
            changed = copy.deepcopy(bundle); mutate(changed)
            self.assert_block_rejected(receipt, changed)
        changed_receipt = copy.deepcopy(receipt)
        changed_receipt['arms'][0]['native_review_sha256'] = 'a' * 64
        self.assert_block_rejected(changed_receipt, bundle)
        receipt2, bundle2, _ = self.run_fixture(1)
        base = receipt2['arms'][0]
        base.update(arm='Base', native_review_available=True, native_review_sha256=r.digest(bundle2['reviews'][0]))
        with self.assertRaisesRegex(ValueError, 'ALL_SCHEDULED_POSITIONS_REQUIRED'):
            public.export(receipt2, self.package, self.grant, native_bundle=bundle2)

    def test_r5_selected_executed_checked_sequences_and_result_counts_bind(self):
        def two_operations(response, index, request):
            if request['reasoning_effort'] == 'high':
                plan = json.loads(response['choices'][0]['message']['content'])
                second = copy.deepcopy(plan['operations'][0]); second['capability'] = 'C01'
                plan['operations'].append(second)
                response['choices'][0]['message']['content'] = json.dumps(plan)
        receipt, bundle, _ = self.run_fixture(mutate=two_operations)
        accepted = public.export(receipt, self.package, self.grant, native_bundle=bundle)
        self.assertEqual(accepted['native_publication_status'], 'AUTHORIZED_BOUNDED_NATIVE_EVIDENCE')
        self.assertEqual(receipt['arms'][0]['selected_capabilities'], ['B01', 'C01'])
        trials = [('selected_capabilities', ['C01', 'B01']),
                  ('selected_capabilities', ['B01', 'C01', 'B01']),
                  ('executed_capabilities', ['C01', 'B01']),
                  ('executed_capabilities', ['B01']), ('native_results', 1)]
        trials.append(('checked_treatment', ['B01'] if receipt['arms'][0]['checked_treatment'] != ['B01'] else []))
        for key, value in trials:
            changed = copy.deepcopy(receipt); changed['arms'][0][key] = value
            if key == 'executed_capabilities':
                changed['arms'][0]['checked_treatment'] = [capability for capability in changed['arms'][0]['checked_treatment'] if capability in value]
            with self.subTest(key=key, value=value):
                self.assert_block_rejected(changed, bundle)

    def test_r5_published_actual_arguments_bind_with_exact_receipt_context(self):
        receipt, bundle, _ = self.run_fixture()
        published = native.export_native_records(bundle, self.package, self.permission, receipt=receipt)
        argument = self.argument(self.package.cases[0])
        argument['question'] = 'Another source-backed question?'
        alternate = self.private_review(self.package.cases[0], [argument])
        op = published['records'][0]['operations'][0]
        op.update(capability_id='B01', source_validated_arguments=argument,
                  native_result_and_policy=alternate['native_outputs'][0],
                  arguments_sha256=r.digest(argument), native_output_sha256=r.digest(alternate['native_outputs'][0]))
        with self.assertRaisesRegex(ValueError, 'EXACT_PUBLISHED_NATIVE_(CAPTURE_HASH|PROJECTION)_REQUIRED'):
            native.validate_published_native_evidence(published, self.package, self.permission, receipt=receipt)

    def test_r5_valid_partial_capture_preserves_actual_operations_without_proposal_disclosure(self):
        case = self.package.cases[0]
        arguments = [self.argument(case), self.argument(case, 'C01')]
        arguments[1]['question'] = 'UNDISPATCHED_PROPOSAL_CANARY'
        review = self.private_review(case, arguments, dispatch_count=1)
        bundle = dict(schema='hcl-entry-contract-smoke-private-native-review-bundle-v1',
                      package_sha256=r.digest(self.package.value), stage=1, reviews=[review])
        published = native.export_native_records(bundle, self.package, self.permission)
        record = published['records'][0]
        self.assertNotIn('UNDISPATCHED_PROPOSAL_CANARY', json.dumps(published))
        self.assertEqual(record['operations'][0]['source_validated_arguments'], arguments[0])
        self.assertEqual(record['actual_operation_count'], 1)
        self.assertEqual(record['actual_executed_count'], 1)
        self.assertTrue(native.validate_published_native_evidence(published, self.package, self.permission))

    def test_r5_empty_valid_native_selection_is_preserved_without_fabrication(self):
        receipt, bundle, _ = self.run_fixture(empty=True)
        result = public.export(receipt, self.package, self.grant, native_bundle=bundle)
        self.assertEqual(result['native_publication_status'], 'AUTHORIZED_BOUNDED_NATIVE_EVIDENCE')
        record = result['approved_native_evidence']['records'][0]
        self.assertEqual(record['operations'], [])
        self.assertEqual(record['actual_executed_count'], 0)
        self.assertTrue(native.validate_published_native_evidence(result['approved_native_evidence'],
                            self.package, self.permission, receipt=receipt))

    def test_r5_published_receipt_digest_cannot_be_reassociated(self):
        receipt, bundle, _ = self.run_fixture()
        published = native.export_native_records(bundle, self.package, self.permission, receipt=receipt)
        other = copy.deepcopy(receipt); other['elapsed_seconds'] += 1
        with self.assertRaisesRegex(ValueError, 'EXACT_NATIVE_RECEIPT_HASH_REQUIRED'):
            native.validate_published_native_evidence(published, self.package, self.permission, receipt=other)


class EndToEndProjectionCommitmentTests(unittest.TestCase):
    def setUp(self):
        self.helper = NativeCaptureRegressions(methodName='runTest')
        self.helper.setUp(); self.addCleanup(self.helper.doCleanups)
        self.package = self.helper.package; self.permission = self.helper.permission

    def public_fixture(self, stage=1, partial=False):
        receipt, bundle, _ = self.helper.run_fixture(stage)
        if partial:
            cid = bundle['reviews'][0]['case_id']; case = next(c for c in self.package.cases if c['case_id'] == cid)
            arguments = [self.helper.argument(case), self.helper.argument(case, 'C01')]
            arguments[1]['question'] = 'UNDISPATCHED_PROPOSAL_MUST_STAY_PRIVATE'
            result = native._session(case)._execute(arguments[0], case['question'])
            self.helper.serial += 1
            ledger = r.Ledger(self.helper.root / ('capture-' + str(self.helper.serial)), self.package, stage, lambda: NOW, lambda: 0)
            ledger.value = copy.deepcopy(receipt)
            arm = next(a for a in ledger.value['arms'] if a['case_id'] == cid and a['arm'] == 'HCL')
            arm['selected_capabilities'] = ['B01', 'C01']
            ledger.native_review(case, dict(plan={'operations': arguments}, operations=[result]))
            receipt = ledger.value
            bundle = copy.deepcopy(bundle); bundle['reviews'][0] = ledger.native_reviews[0]
        evidence = public.export(receipt, self.package, self.helper.grant, native_bundle=bundle)
        self.assertTrue(native.validate_published_native_evidence(evidence['approved_native_evidence'], self.package, self.permission, receipt=receipt))
        self.assertTrue(native.validate_published_native_evidence(evidence['approved_native_evidence'], self.package, self.permission, public_capture=evidence))
        return receipt, bundle, evidence

    def mutate_same_capability(self, evidence, *, rehash=False):
        changed = copy.deepcopy(evidence); record = changed['approved_native_evidence']['records'][0]
        case = next(c for c in self.package.cases if c['case_id'] == record['case_id'])
        argument = self.helper.argument(case)
        argument['question'] = 'Different valid same-capability replay question?'
        output = native._session(case)._execute(argument, case['question'])
        captured = r.private_native_review(case, dict(plan={'operations': [argument]}, operations=[output]))['native_outputs'][0]
        operation = record['operations'][0]
        operation.update(source_validated_arguments=argument, native_result_and_policy=captured, arguments_sha256=r.digest(argument), native_output_sha256=r.digest(captured))
        if rehash: record['native_projection_sha256'] = native.published_projection_sha256(record)
        return changed

    def gate_view(self):
        package = self.package
        class ReadOnlyValidationView:
            value = package.value; packet = package.packet; cases = package.cases
            def verify(self): return package.verify()
        return ReadOnlyValidationView()

    def run_gate(self, evidence):
        view = self.gate_view(); value = copy.deepcopy(evidence)
        value.update(schema='hcl-entry-contract-smoke-public-evidence-v1', mode='LIVE_EXISTING_ACCOUNT', provider_calls=2, offline_transport_calls=0, usage_rated_cny=value['simulated_usage_rated_cny'], run_id='42', head_sha='a' * 40)
        for call in value['calls']: call.update(provider_call=True, offline_transport_call=False)
        review = review_fixture(view, value); review['approved_native_evidence_sha256'] = r.digest(value['approved_native_evidence'])
        return public.validate_phase1_gate(view, value, review, native_permission=self.permission)

    def test_capture_stores_exact_disclosed_projection_digest_for_full_and_partial_records(self):
        for stage in (1,):
            for partial in (False, True):
                receipt, bundle, evidence = self.public_fixture(stage, partial)
                record = evidence['approved_native_evidence']['records'][0]
                arm = next(a for a in receipt['arms'] if a['case_id'] == record['case_id'] and a['arm'] == 'HCL')
                self.assertEqual(arm['native_projection_status'], 'CAPTURED')
                self.assertEqual(arm['native_projection_sha256'], native.published_projection_sha256(record))
                self.assertEqual(arm['native_projection_sha256'], r.digest(native.native_projection_from_capture(bundle['reviews'][0], self.package.value['runtime_sha256'])))
                self.assertNotIn('UNDISPATCHED_PROPOSAL_MUST_STAY_PRIVATE', json.dumps(evidence))

    def test_same_capability_changes_fail_full_and_partial_actual_receipt_and_public_context(self):
        for stage in (1,):
            for partial in (False, True):
                receipt, bundle, evidence = self.public_fixture(stage, partial)
                for rehash in (False, True):
                    changed = self.mutate_same_capability(evidence, rehash=rehash)
                    native_value = changed['approved_native_evidence']
                    with self.subTest(stage=stage, partial=partial, rehash=rehash):
                        with self.assertRaises(ValueError): native.validate_published_native_evidence(native_value, self.package, self.permission, receipt=receipt)
                        with self.assertRaises(ValueError): native.validate_published_native_evidence(native_value, self.package, self.permission, public_capture=changed)
                        with self.assertRaisesRegex(ValueError, 'ACTUAL_NATIVE_CAPTURE_CONTEXT_REQUIRED'):
                            native.validate_published_native_evidence(native_value, self.package, self.permission)

    def test_actual_smoke_gate_rejects_changed_replay_with_original_full_or_partial_commitment(self):
        for partial in (False, True):
            receipt, bundle, evidence = self.public_fixture(1, partial)
            if partial:
                self.assertIsNone(evidence['arms'][0]['entry_requirements'])
                with self.assertRaisesRegex(ValueError, 'NECESSARY_ENTRY_REQUIREMENTS_NOT_SATISFIED'):
                    self.run_gate(evidence)
            else:
                self.assertTrue(self.run_gate(evidence))
            for rehash in (False, True):
                changed = self.mutate_same_capability(evidence, rehash=rehash)
                with self.subTest(partial=partial, rehash=rehash), self.assertRaisesRegex(ValueError, 'EXACT_PUBLISHED_NATIVE_PROJECTION_REQUIRED'):
                    self.run_gate(changed)

    def test_missing_or_rejected_projection_commitment_cannot_pass_smoke_gate(self):
        _, _, evidence = self.public_fixture()
        for changes in ({'native_projection_sha256': None}, {'native_projection_status': 'REJECTED_UNAVAILABLE'}, {'native_projection_sha256': 'a' * 64}):
            changed = copy.deepcopy(evidence); changed['arms'][0].update(changes)
            with self.assertRaises(ValueError): self.run_gate(changed)

    def test_projection_capture_failure_keeps_original_final_and_usage_but_closes_native_gate(self):
        with patch.object(native, 'native_projection_from_capture', side_effect=ValueError('CAPTURE_FAILURE_CANARY_NEVER_DISCLOSE')):
            receipt, bundle, client = self.helper.run_fixture()
        arm = receipt['arms'][0]
        self.assertEqual(len(client.calls), 1); self.assertEqual(arm['status'], 'PRE_FINAL_NATIVE_REQUIREMENTS_REJECTED_NO_CALL')
        self.assertEqual(arm['native_projection_status'], 'REJECTED_UNAVAILABLE'); self.assertIsNone(arm['native_projection_sha256'])
        self.assertIsNone(arm['final_text']); self.assertTrue(all('usage' in c for c in receipt['calls']))
        safe = self.helper.assert_block_rejected(receipt, bundle)
        self.assertEqual(safe['arms'][0]['final_text'], arm['final_text'])
        self.assertNotIn('CAPTURE_FAILURE_CANARY_NEVER_DISCLOSE', json.dumps(safe))
        with self.assertRaises(ValueError): self.run_gate(safe)

    def test_mixed_valid_operation_and_bad_anchor_refuse_before_any_native_or_final(self):
        def mixed(response,index,request):
            if request['reasoning_effort']!='high':return
            plan=json.loads(response['choices'][0]['message']['content']);rejected=copy.deepcopy(plan['operations'][0])
            rejected['input_mode']='semantic'
            rejected['semantic_candidates']=[self.helper.semantic(self.package.cases[0],quote='ABSENT_ANCHOR_MUST_STAY_PRIVATE')]
            plan['operations'].append(rejected);response['choices'][0]['message']['content']=json.dumps(plan)
        receipt,bundle,client=self.helper.run_fixture(mutate=mixed)
        self.assertEqual(len(client.calls),1);self.assertEqual(receipt['arms'][0]['native_results'],0)
        self.assertIsNone(receipt['arms'][0]['final_text'])
        safe=public.export(receipt,self.package,self.helper.grant,native_bundle=bundle)
        self.assertEqual(safe['reserved_cny'],str(r.HOLD_CNY['planning']))
        self.assertNotIn('ABSENT_ANCHOR_MUST_STAY_PRIVATE',json.dumps(safe))


    def test_public_native_projection_fields_cannot_be_replaced_at_export_for_either_stage(self):
        for stage in (1,):
            receipt, bundle, evidence = self.public_fixture(stage, partial=True)
            changed = copy.deepcopy(receipt)
            arm = next(a for a in changed['arms'] if a['arm'] == 'HCL')
            arm['native_projection_sha256'] = 'f' * 64
            with self.assertRaisesRegex(ValueError, 'EXACT_RECEIPT_NATIVE_PROJECTION_REQUIRED'):
                public.export(changed, self.package, self.helper.grant, native_bundle=bundle)


if __name__ == '__main__':
    unittest.main()
