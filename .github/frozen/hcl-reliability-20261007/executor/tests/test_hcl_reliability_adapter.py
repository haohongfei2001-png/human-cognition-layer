"""Offline-only adapter/public-native permission tests. Never construct an SDK.

All grant/package/approval references here are synthetic control fixtures kept in
TemporaryDirectory or memory, never owner grants, active workflow or final freeze.
"""
import ast
import copy
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import hcl_reliability_candidate as r
import hcl_reliability_public as public
import hcl_reliability_native_public as native
import hcl_reliability_cli as cli
from test_hcl_reliability_candidate import Client, NOW, RUNTIME, fixture_packet, native_permission_fixture, review_fixture
import test_hcl_reliability_candidate as fixtures


class NativePublicTests(unittest.TestCase):
    def setUp(self):
        self.package = r.OfflinePackage.build(fixture_packet(), RUNTIME)
        self.permission = native_permission_fixture(self.package)
        case = self.package.cases[0]; session = native._session(case)
        argument = dict(capability='B01', question=case['question'], source_ids=[case['sources'][0]['source_id']], bindings=[])
        result = session._execute(argument, case['question'])
        self.review = r.private_native_review(case, dict(plan={'operations': [argument]}, operations=[result]))
        self.bundle = dict(schema='hcl-reliability-private-native-review-bundle-v1', package_sha256=r.digest(self.package.value), stage=1, reviews=[self.review])

    def test_exact_permission_allows_only_source_validated_captured_native_fields(self):
        result = native.export_native_records(self.bundle, self.package, self.permission)
        self.assertTrue(native.validate_published_native_evidence(result, self.package, self.permission))
        row = result['records'][0]
        self.assertEqual(row['actual_operation_count'], 1); self.assertEqual(row['actual_executed_count'], 1)
        self.assertEqual(row['operations'][0]['capability_id'], 'B01')
        self.assertLessEqual(len(r.canonical(row)), 1048576)
        self.assertFalse(result['semantic_certification']); self.assertFalse(result['reviewed_native_relevance'])
        for field in ('task', 'limitations', 'raw_plan', 'choices', 'reasoning_content', 'messages'):
            self.assertNotIn('"' + field + '"', json.dumps(result))

    def test_absent_wrong_destination_or_unbounded_permission_never_exports(self):
        values = [None, {}, dict(self.permission, destination='https://example.invalid'), dict(self.permission, maximum_case_records=6), dict(self.permission, maximum_operations_per_record=4), dict(self.permission, maximum_record_utf8_bytes=1048577), dict(self.permission, packet_sha256='f' * 64), dict(self.permission, approval_message_ref='')]
        for permission in values:
            with self.subTest(permission=permission), self.assertRaises(ValueError):
                native.export_native_records(self.bundle, self.package, permission)

    def test_extra_unknown_duplicate_case_or_more_than_five_records_is_rejected(self):
        for mutate in (lambda b: b['reviews'].append(copy.deepcopy(b['reviews'][0])), lambda b: b['reviews'][0].update(case_id='unknown-private-history'), lambda b: b['reviews'].extend(copy.deepcopy(b['reviews']) * 5), lambda b: b.update(raw_planner='NEVER_PUBLISH')):
            bundle = copy.deepcopy(self.bundle); mutate(bundle)
            with self.assertRaises(ValueError): native.export_native_records(bundle, self.package, self.permission)

    def test_source_argument_anchor_policy_result_and_support_binding_drift_is_rejected(self):
        mutations = [lambda x: x['source_roots'][0].update(version=2), lambda x: x['validated_operation_arguments'][0].update(source_ids=['invented']), lambda x: x['validated_operation_arguments'][0].update(bindings=[dict(role='actor', source_id='control-source-0-0', start=0, quote='Invented')]), lambda x: x['native_outputs'][0].update(preparation_policy='SOURCE_INJECTED_POLICY'), lambda x: x['native_outputs'][0].update(support_claim_ids=['invented']), lambda x: x['native_outputs'][0]['result'].update(private_history='NEVER_PUBLISH'), lambda x: x.update(task='RAW_PLANNER_TASK'), lambda x: x['native_outputs'][0].update(reasoning_content='NEVER_PUBLISH')]
        for mutate in mutations:
            bundle = copy.deepcopy(self.bundle); mutate(bundle['reviews'][0])
            with self.assertRaises((ValueError, KeyError)): native.export_native_records(bundle, self.package, self.permission)

    def test_record_and_operation_caps_are_fail_closed_without_truncation(self):
        large = copy.deepcopy(self.bundle); large['reviews'][0]['native_outputs'][0]['result']['large'] = 'x' * 1048577
        with self.assertRaisesRegex(ValueError, 'BOUND_EXCEEDED'): native.export_native_records(large, self.package, self.permission)
        many = copy.deepcopy(self.bundle)
        many['reviews'][0]['validated_operation_arguments'] *= 4; many['reviews'][0]['native_outputs'] *= 4
        with self.assertRaises(ValueError): native.export_native_records(many, self.package, self.permission)

    def test_republished_record_cannot_swap_policy_or_hash_or_actual_counts(self):
        original = native.export_native_records(self.bundle, self.package, self.permission)
        mutations = [lambda x: x.update(permission_sha256='e' * 64), lambda x: x['records'][0].update(actual_executed_count=3), lambda x: x['records'][0]['operations'][0].update(arguments_sha256='a' * 64), lambda x: x['records'][0]['operations'][0]['native_result_and_policy'].update(preparation_policy='OTHER_POLICY'), lambda x: x['records'][0].update(raw_request='PRIVATE_CANARY')]
        for mutate in mutations:
            value = copy.deepcopy(original); mutate(value)
            with self.assertRaises(ValueError): native.validate_published_native_evidence(value, self.package, self.permission)

    def test_nonobject_records_and_nonfinite_native_json_are_rejected(self):
        for record in (None, 'raw planner string', 3, []):
            bundle = dict(self.bundle, reviews=[record])
            with self.assertRaises(ValueError): native.export_native_records(bundle, self.package, self.permission)
        for value in (float('nan'), float('inf'), -float('inf')):
            with self.assertRaises(ValueError): native._json_safety({'native_score': value})

    def test_actual_semantic_bridge_arguments_replay_without_new_planning(self):
        case = self.package.cases[0]; source = case['sources'][0]
        quote = source['text'].splitlines()[0]
        argument = dict(capability='B01', question=case['question'], source_ids=[source['source_id']], bindings=[], semantic_candidates=[dict(source_id=source['source_id'], quote=quote, start=0, kind='event', content={'canonical_statement': quote})])
        session = native._session(case); result = session._execute(argument, case['question'])
        review = r.private_native_review(case, dict(plan={'operations': [argument]}, operations=[result]))
        bundle = dict(self.bundle, reviews=[review])
        published = native.export_native_records(bundle, self.package, self.permission)
        self.assertTrue(native.validate_published_native_evidence(published, self.package, self.permission))


class AdapterTests(unittest.TestCase):
    def environment(self, stage=1):
        return dict(GITHUB_REF='refs/heads/main', GITHUB_RUN_ATTEMPT='1', GITHUB_EVENT_NAME='push', GITHUB_REPOSITORY=cli.REPOSITORY, GITHUB_WORKFLOW_REF=f'{cli.REPOSITORY}/.github/workflows/hcl-reliability-20261007-{stage}-once.yml@refs/heads/main', GITHUB_RUN_ID='42', GITHUB_SHA='a' * 40)

    def setup_files(self, root, temp):
        package = fixtures.ReusableEntryContractTests().frozen_fixture(root)
        grant, args = fixtures.ReusableEntryContractTests().inputs(package, 1)
        locations = cli.paths(root, 1, Path(temp))
        r.save(locations['package'], package.value); r.save(locations['cases'], package.packet); r.save(locations['grant'], grant)
        r.save(locations['marker'], args['launch']['marker']); r.save(locations['history'], args['launch']['pages'])
        r.save(locations['price'], args['price'])
        old_account = {key: value for key, value in args['account'].items() if key != 'existing_account_only'}
        old_account['schema'] = 'hcl-two-stage-account-readiness-v1'; r.save(locations['account'], old_account)
        r.save(locations['presence'], dict(args['identity'], existing_provider_secret='PRESENT'))
        expected = cli.admission_value(package, grant, args['identity'], args['launch'], args['price'], args['account'])
        r.save(locations['admission'], expected)
        return package, grant, args, locations

    def git_reader(self, root, args):
        if args[0] == 'rev-list': return 'a' * 40 + ' ' + 'b' * 40
        if args[0] == 'diff-tree': return '.github/HCL_RELIABILITY_20261007_1_TRIGGER.json'
        if args[0] == 'diff': return '.github/HCL_RELIABILITY_20261007_1_GRANT.json'
        if args[:2] == ['merge-base', '--is-ancestor']: return ''
        raise AssertionError('unexpected non-read-only git command')

    def test_exact_official_environment_contract_rejects_every_missing_or_changed_identity(self):
        env = self.environment(); self.assertEqual(cli.environment_identity(env, 1), {'run_id': '42', 'head_sha': 'a' * 40})
        changes = [('GITHUB_REF', 'refs/pull/1/merge'), ('GITHUB_RUN_ATTEMPT', '2'), ('GITHUB_EVENT_NAME', 'workflow_dispatch'), ('GITHUB_REPOSITORY', 'other/repo'), ('GITHUB_WORKFLOW_REF', 'other/ref'), ('GITHUB_SHA', 'unknown'), ('GITHUB_RUN_ID', '0')]
        for key, value in changes:
            bad = dict(env); bad[key] = value
            with self.assertRaises(ValueError): cli.environment_identity(bad, 1)
        for key in env:
            bad = dict(env); bad.pop(key)
            with self.assertRaises(ValueError): cli.environment_identity(bad, 1)

    def test_future_adapter_calls_fake_factory_only_after_all_admission_guards(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temp:
            package, grant, args, locations = self.setup_files(root, temp)
            client = Client(); created = []
            def factory(): created.append(True); return client
            result = cli.execute_admitted(root, 1, self.environment(), temporary_root=Path(temp), git_reader=self.git_reader, client_factory=factory, clock=lambda: NOW)
            self.assertEqual(created, [True]); self.assertEqual(len(client.calls), 2)
            self.assertTrue(locations['consumed'].exists()); self.assertEqual(result['budget_state'], 'CLOSED_NO_TRANSFER_NO_RETRY')
            bundle = cli.load_json(locations['directory'] / 'native-review-private.json')
            evidence = public.export(result, package, grant, args['identity'], native_bundle=bundle)
            review = review_fixture(package, evidence)
            self.assertTrue(public.validate_phase1_gate(package, evidence, review, native_permission=grant['public_native_evidence_permission']))
            with self.assertRaises(ValueError):
                cli.execute_admitted(root, 1, self.environment(), temporary_root=Path(temp), git_reader=self.git_reader, client_factory=factory, clock=lambda: NOW)
            self.assertEqual(created, [True])

    def test_missing_permission_stale_precheck_history_or_admission_never_constructs_client(self):
        for mutation in ('permission', 'stale_account', 'usd', 'identity', 'history', 'admission', 'consumed'):
            with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temp:
                package, grant, args, locations = self.setup_files(root, temp)
                if mutation == 'permission': grant['public_native_evidence_permission'] = None; r.save(locations['grant'], grant)
                elif mutation == 'stale_account': value = cli.load_json(locations['account']); value['checked_at'] = (NOW - timedelta(minutes=11)).isoformat(); r.save(locations['account'], value)
                elif mutation == 'usd': value = cli.load_json(locations['account']); value['currency'] = 'USD'; r.save(locations['account'], value)
                elif mutation == 'identity': r.save(locations['presence'], {'run_id': '99', 'head_sha': 'b' * 40, 'existing_provider_secret': 'PRESENT'})
                elif mutation == 'history': value = cli.load_json(locations['history']); value[0]['total_count'] = 2; r.save(locations['history'], value)
                elif mutation == 'admission': value = cli.load_json(locations['admission']); value['price_sha256'] = 'f' * 64; r.save(locations['admission'], value)
                else: r.save(locations['consumed'], {'already': 'consumed'})
                created = []
                with self.subTest(mutation=mutation), self.assertRaises((ValueError, FileExistsError)):
                    cli.execute_admitted(root, 1, self.environment(), temporary_root=Path(temp), git_reader=self.git_reader, client_factory=lambda: created.append(True), clock=lambda: NOW)
                self.assertEqual(created, [])

    def test_actual_repair_ancestry_and_single_parent_marker_commit_are_required(self):
        for mode in ('parents', 'changed_paths', 'ancestry'):
            with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temp:
                package, grant, args, locations = self.setup_files(root, temp)
                def bad(root, query):
                    if mode == 'parents' and query[0] == 'rev-list': return 'a' * 40 + ' ' + 'b' * 40 + ' ' + 'c' * 40
                    if mode == 'changed_paths' and query[0] == 'diff-tree': return self.git_reader(root, query) + '\nhcl/changed.py'
                    if mode == 'ancestry' and query[0] == 'merge-base': raise ValueError('NOT_ANCESTOR')
                    return self.git_reader(root, query)
                with self.assertRaises(ValueError): cli.read_launch(root, 1, package, grant, args['identity'], self.environment(), args['launch']['pages'], git_reader=bad)

    def test_interrupted_send_closes_entire_hold_without_fabricating_usage_or_timing(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temp:
            package, grant, args, locations = self.setup_files(root, temp)
            ledger = r.Ledger(locations['directory'], package, 1, lambda: NOW, lambda: 0, offline=False, identity=args['identity'], admission_hashes=dict(grant_sha256=r.digest(grant), launch_sha256=r.digest(args['launch']), price_sha256=r.digest(args['price']), account_sha256=r.digest(args['account'])))
            ledger.active = 'control-0:HCL'; port = r.BoundedPort(Client(), ledger, ledger.active)
            port.reservation_usd('planning', r.messages(package.cases[0], 'HCL'))
            ledger.value['calls'][0].update(provider_call=True, invocation_status='INVOKED_OR_SEND_UNKNOWN'); ledger.persist()
            closed = cli.close_interrupted_receipt(ledger.value, package)
            self.assertEqual(closed['reserved_cny'], str(r.HOLD_CNY['planning'])); self.assertIsNone(closed['elapsed_seconds'])
            self.assertEqual(closed['remaining_authorized_calls'], 0); self.assertNotIn('usage', closed['calls'][0])
            self.assertEqual(closed['arms'][0]['status'], 'UNKNOWN_FAILURE_STOP')
            # The missing native record is deliberately not reconstructed or published.
            self.assertFalse((locations['directory'] / 'native-review-private.json').exists())

    def test_granted_but_absent_native_output_does_not_create_public_native_record(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temp:
            package, grant, args, locations = self.setup_files(root, temp)
            def mutate(result, i, request): result.pop('usage')
            result = r.run(Client(mutate), package, grant, locations['directory'], **args)
            value = public.export(result, package, grant, args['identity'], native_bundle=None)
            self.assertEqual(value['native_publication_status'], 'AUTHORIZED_BUT_NATIVE_UNAVAILABLE_GATE_CLOSED')
            self.assertIsNone(value['approved_native_evidence'])
            self.assertEqual(value['budget_state'], 'CLOSED_NO_TRANSFER_NO_RETRY')

    def test_missing_public_permission_refuses_reusable_run_before_any_call(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temp:
            package, grant, args, locations = self.setup_files(root, temp)
            grant['public_native_evidence_permission'] = None
            args['launch']['grant_sha256'] = r.digest(grant); args['launch']['marker']['grant_sha256'] = r.digest(grant)
            client = Client()
            with self.assertRaisesRegex(ValueError, 'EXPLICIT_NATIVE_PUBLICATION_PERMISSION_REQUIRED'):
                r.run(client, package, grant, locations['directory'], **args)
            self.assertEqual(client.calls, []); self.assertFalse(locations['directory'].exists())

    def test_terminal_export_rejects_whole_invalid_native_block_but_retains_closed_cost(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temp:
            package, grant, args, locations = self.setup_files(root, temp)
            result = r.run(Client(), package, grant, locations['directory'], **args)
            path = locations['directory'] / 'native-review-private.json'; bundle = cli.load_json(path)
            bundle['reviews'][0]['raw_planner_response'] = 'UNAPPROVED_PRIVATE_CANARY'; r.save(path, bundle)
            output = cli.export_terminal(root, 1, self.environment(), now=NOW)
            self.assertEqual(output['native_publication_status'], 'NATIVE_EXPORT_REJECTED_GATE_CLOSED')
            self.assertIsNone(output['approved_native_evidence'])
            self.assertEqual(output['reserved_cny'], str(r.SCHEDULE_CNY[1]))
            self.assertNotIn('UNAPPROVED_PRIVATE_CANARY', locations['public'].read_text())

    def test_expiry_and_send_margin_precede_client_factory(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temp:
            package, grant, args, locations = self.setup_files(root, temp)
            created = []
            with self.assertRaises(ValueError):
                cli.execute_admitted(root, 1, self.environment(), temporary_root=Path(temp), git_reader=self.git_reader, client_factory=lambda: created.append(True), clock=lambda: r.timestamp(r.EXPIRES) - timedelta(seconds=180))
            self.assertEqual(created, [])

    def test_read_only_adapter_modules_are_exact_pinned_and_unmodified(self):
        self.assertEqual(cli.read_only_reader_pins(RUNTIME), cli.READER_PINS)
        self.assertEqual(set(cli.READER_PINS), {'scripts/two_stage_account.py', 'scripts/two_stage_price.py'})
        with patch.object(cli, 'READER_PINS', dict(cli.READER_PINS, **{'scripts/two_stage_account.py': '0' * 64})):
            with self.assertRaises(ValueError): cli.read_only_reader_pins(RUNTIME)

    def test_templates_have_only_new_marker_push_and_approved_public_artifact(self):
        root = Path(cli.__file__).parent
        for stage in (1, 2):
            text = (root / f'workflow-templates/stage{stage}-once.yml').read_text()
            self.assertIn(f"paths: ['.github/HCL_RELIABILITY_20261007_{stage}_TRIGGER.json']", text)
            self.assertNotIn('workflow_dispatch:', text); self.assertNotIn('schedule:', text)
            self.assertIn('cancel-in-progress: false', text); self.assertIn('persist-credentials: false', text)
            self.assertIn('--paginate --slurp', text); self.assertIn('--preflight', text)
            self.assertIn(f'path: hcl-reliability-20261007-{stage}-public.json', text)
            self.assertNotIn('path: hcl-reliability-20261007-' + str(stage) + '-private', text)
            self.assertNotIn('HCL_TWO_STAGE_CNY_', text)

    def test_cli_has_no_freeze_or_grant_creation_mode_and_is_syntax_valid(self):
        source = Path(cli.__file__).read_text(); ast.parse(source)
        for forbidden in ("add_argument('--freeze'", "add_argument('--grant'", "add_argument('--activate'", "add_argument('--trigger'"):
            self.assertNotIn(forbidden, source)


if __name__ == '__main__':
    unittest.main()
