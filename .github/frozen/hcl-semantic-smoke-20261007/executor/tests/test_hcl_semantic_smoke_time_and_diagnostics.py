"""No calendar cutoff, bounded stages and safe scalar diagnostics. Fake SDK only."""
import copy
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import hcl_semantic_smoke_candidate as r
import hcl_semantic_smoke_public as public
import hcl_semantic_smoke_cli as cli
import test_hcl_semantic_smoke_candidate as fixture
import test_hcl_semantic_smoke_adapter as adapter


class RecoveryTimeAndDiagnosticsTests(unittest.TestCase):
    def test_none_expiry_is_explicit_and_both_sides_of_old_cutoff_are_allowed(self):
        self.assertIsNone(r.EXPIRES)
        for now in (datetime(2026, 10, 7, 13, 59, 59, tzinfo=timezone.utc),
                    datetime(2026, 10, 7, 14, tzinfo=timezone.utc),
                    datetime(2026, 10, 8, 15, tzinfo=timezone.utc)):
            r.require_time(now)
        with self.assertRaises(ValueError): r.require_time(r.timestamp(r.APPROVED) - timedelta(seconds=1))
        package = r.OfflinePackage.build(fixture.fixture_packet(), fixture.RUNTIME)
        self.assertIsNone(package.value['expires_at'])
        self.assertEqual(package.value['stage_windows_seconds'], {'1': 600})

    def test_actual_adapter_after_old_cutoff_sends_only_two_fake_calls(self):
        now = datetime(2026, 10, 7, 14, 1, tzinfo=timezone.utc)
        setup = adapter.AdapterTests()
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temp, patch.object(fixture, 'NOW', now), patch.object(adapter, 'NOW', now):
            package, grant, args, locations = setup.setup_files(root, temp)
            client = fixture.Client()
            result = cli.execute_admitted(root, 1, setup.environment(), temporary_root=Path(temp),
                git_reader=setup.git_reader, client_factory=lambda: client, clock=lambda: now)
            self.assertEqual(len(client.calls), 2)
            self.assertEqual(result['status'], 'COMPLETED_ONE_PASS')
            evidence = cli.export_terminal(root, 1, setup.environment(), now=now)
            self.assertIsNone(evidence['authorization_expiry_utc'])
            self.assertEqual(evidence['budget_state'], 'CLOSED_NO_TRANSFER_NO_RETRY')

    def test_each_stage_loses_admission_at_exact_180_second_margin(self):
        package = r.OfflinePackage.build(fixture.fixture_packet(), fixture.RUNTIME)
        for stage in (1,):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as root:
                elapsed = [0]
                ledger = r.Ledger(Path(root) / 'run', package, stage,
                    lambda: datetime(2026, 10, 8, 15, tzinfo=timezone.utc), lambda: elapsed[0])
                elapsed[0] = r.ELAPSED[stage] - r.WAIT - 1
                ledger.admit(); ledger.require_final_dispatch_margin()
                elapsed[0] += 1
                with self.assertRaisesRegex(ValueError, 'BATCH_DEADLINE_SEND_MARGIN'): ledger.admit()
                with self.assertRaisesRegex(ValueError, 'FINAL_STAGE_SEND_MARGIN_INVALID'): ledger.require_final_dispatch_margin()
                self.assertEqual(ledger.value['calls'], [])

    def test_single_smoke_schedule_and_total_are_bounded(self):
        package = r.OfflinePackage.build(fixture.fixture_packet(), fixture.RUNTIME)
        self.assertEqual(r.MAX_CALLS, {1: 2})
        self.assertEqual(r.order(package.cases, 1), [('control-0', 'HCL')])
        with self.assertRaisesRegex(ValueError, 'EXACT_STAGE_REQUIRED'): r.order(package.cases, 2)
        self.assertEqual(str(sum(r.SCHEDULE_CNY.values())), '1.998144')
        self.assertLessEqual(sum(r.SCHEDULE_CNY.values()), r.TOTAL_CNY)
        self.assertEqual(package.value['maximum_final_texts'], 1)
        self.assertEqual(package.value['public_native_maximum_case_records'], 1)

    def test_incomplete_planning_preserves_only_safe_finish_and_token_counts(self):
        def length(result, index, request):
            result['choices'][0]['finish_reason'] = 'length'
            result['choices'][0]['message'].update(content='', reasoning_content='PRIVATE_REASONING_CANARY')
            result['usage'] = dict(prompt_tokens=100, completion_tokens=16384,
                completion_tokens_details={'reasoning_tokens': 16384})
        client = fixture.Client(length); receipt, package = fixture.execute(client)
        evidence = public.export(receipt, package); metadata = evidence['calls'][0]['response_metadata']
        self.assertEqual(metadata, dict(choice_count=1, finish_reasons=['length'],
            visible_content_characters=0, provider_reported_reasoning_tokens=16384))
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(evidence['status'], 'STOPPED_NO_RETRY')
        self.assertNotIn('PRIVATE_REASONING_CANARY', json.dumps(evidence))
        self.assertIsNone(evidence['arms'][0]['final_text'])

    def test_missing_reasoning_counts_remain_unknown_not_zero(self):
        receipt, package = fixture.execute()
        evidence = public.export(receipt, package)
        for call in evidence['calls']:
            self.assertIsNone(call['response_metadata']['provider_reported_reasoning_tokens'])
            self.assertEqual(call['response_metadata']['finish_reasons'], ['stop'])

    def test_untrusted_reason_strings_and_count_types_never_become_public_text(self):
        raw = dict(choices=[dict(finish_reason='PRIVATE_CANARY', message=dict(content='ok', reasoning_content='SECRET'))],
            usage=dict(completion_tokens=50, completion_tokens_details={'reasoning_tokens': 'PRIVATE_CANARY'}))
        metadata = r.safe_response_metadata(raw, 'planning')
        self.assertEqual(metadata['finish_reasons'], ['OTHER_OR_MISSING'])
        self.assertIsNone(metadata['provider_reported_reasoning_tokens'])
        self.assertNotIn('PRIVATE_CANARY', json.dumps(metadata))
        for change in (dict(provider_reported_reasoning_tokens=True), dict(visible_content_characters='SECRET'),
                       dict(finish_reasons=['PRIVATE_CANARY']), dict(raw_response='SECRET')):
            value = copy.deepcopy(metadata); value.update(change)
            with self.assertRaises(ValueError): public.clean_response_metadata(value, 'planning')

    def test_smoke_delivery_failure_stops_without_replacement_or_another_case(self):
        def invalid_final(result, index, request):
            if request['max_tokens'] == 8192:
                result['choices'][0]['message']['content'] = '{invalid final'
        client = fixture.Client(invalid_final); receipt, package = fixture.execute(client, stage=1)
        evidence = public.export(receipt, package)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(evidence['status'], 'STOPPED_NO_RETRY')
        self.assertEqual(len(evidence['arms']), 1)
        self.assertEqual(evidence['remaining_authorized_calls'], 0)
        with tempfile.TemporaryDirectory() as root, self.assertRaisesRegex(ValueError, 'EXACT_STAGE_REQUIRED'):
            r.run_offline(fixture.Client(), package, 2, Path(root) / 'run', clock=lambda: fixture.NOW)


class SingleSmokeAuthorizationTests(unittest.TestCase):
    def test_new_exact_approval_and_only_one_stage(self):
        self.assertEqual(r.APPROVED, '2026-10-07T13:32:22Z')
        self.assertEqual(r.AUTH, 'OWNER_APPROVED_HCL_SEMANTIC_SMOKE_20261007_2_CALLS_2_CNY')
        self.assertEqual(r.TOTAL_CNY, Decimal('2'))
        self.assertEqual(r.CAP_CNY, {1: Decimal('2.00')})
        self.assertEqual(r.MAX_CALLS, {1: 2})
        self.assertEqual(r.ELAPSED, {1: 600})

    def test_every_alternate_stage_refuses_before_transport(self):
        package = r.OfflinePackage.build(fixture.fixture_packet(), fixture.RUNTIME)
        for stage in (0, 2, -1, True, '1', None):
            client = fixture.Client()
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as root:
                with self.assertRaisesRegex(ValueError, 'EXACT_STAGE_REQUIRED'):
                    r.run_offline(client, package, stage, Path(root) / 'run', clock=lambda: fixture.NOW)
                with self.assertRaisesRegex(ValueError, 'EXACT_STAGE_REQUIRED'):
                    cli.paths(root, stage)
                self.assertEqual(client.calls, [])

    def test_static_request_catalog_cannot_include_other_cases_or_base(self):
        package = r.OfflinePackage.build(fixture.fixture_packet(), fixture.RUNTIME)
        self.assertEqual(set(package.value['requests']), {'control-0:HCL:planning'})
        self.assertEqual(package.value['stage_orders'], {'1': [['control-0', 'HCL']]})
        self.assertEqual(package.value['maximum_aggregate_calls'], 2)
        self.assertEqual(package.value['maximum_aggregate_cny'], '2')

    def test_public_scope_is_one_actual_smoke_and_one_record(self):
        import hcl_semantic_smoke_native_public as native
        receipt, package = fixture.execute()
        evidence = public.export(receipt, package)
        self.assertEqual([c['case_id'] for c in evidence['cases']], ['control-0'])
        self.assertEqual(len(evidence['arms']), 1)
        self.assertEqual(native.MAX_RECORDS, 1)
        self.assertEqual(native.MAX_OPERATIONS, 3)
        self.assertEqual(native.MAX_RECORD_BYTES, 1048576)
        permission = fixture.native_permission_fixture(package)
        permission['maximum_case_records'] = 3
        with self.assertRaises(ValueError): native.validate_permission(permission, package.value['packet_sha256'])

    def test_money_projection_cannot_expand_single_smoke_authority(self):
        self.assertEqual(public.money('2'), '2')
        for value in ('2.000001', '6', '12'):
            with self.assertRaises(ValueError): public.money(value)

    def test_successful_delivery_still_requires_relevant_native_source_review(self):
        receipt, package = fixture.execute(); evidence = public.export(receipt, package)
        review = fixture.review_fixture(package, evidence)
        review['gates']['relevant_native_execution_passed'] = False
        review['overall_pass'] = False
        review['critical_failure_tags'] = ['RELEVANT_REAL_NATIVE_TREATMENT_ABSENT']
        with self.assertRaises(ValueError): public.validate_phase1_gate(package, evidence, review)
