"""R1-R3 regressions from the independent review, with real disposable Git histories.

All approvals/grants/workflows are unrelated synthetic fixtures in temporary
folders; no real repository, SDK, credentials, account or provider is touched.
"""
import copy
from datetime import timedelta
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import hcl_entry_contract_smoke_candidate as r
import hcl_entry_contract_smoke_cli as cli
import hcl_entry_contract_smoke_public as public
import hcl_entry_contract_smoke_reviews as reviews
import test_hcl_entry_contract_smoke_candidate as fixtures
import test_hcl_entry_contract_smoke_adapter as adapter_fixtures


class ActualReviewArtifactTests(unittest.TestCase):
    def make(self, root):
        return fixtures.ReusableEntryContractTests().frozen_fixture(root)

    def test_original_r1_nonexistent_hash_repro_now_refuses(self):
        with tempfile.TemporaryDirectory() as root:
            package = self.make(root)
            package.value['independent_case_review_sha256'] = 'e' * 64
            package.value['independent_executor_review_sha256'] = 'f' * 64
            with self.assertRaisesRegex(ValueError, 'EXACT_REVIEW_OR_CASE_FILE_BYTES_REQUIRED'):
                package.verify()

    def test_missing_or_altered_review_bytes_refuse_before_account_or_client(self):
        for kind in ('missing-case', 'missing-executor', 'altered-case', 'altered-executor'):
            with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temporary:
                setup = adapter_fixtures.AdapterTests()
                package, grant, args, paths = setup.setup_files(root, temporary)
                path = Path(root) / (reviews.CASE_REVIEW if kind.endswith('case') else reviews.EXECUTOR_REVIEW)
                if kind.startswith('missing'): path.unlink()
                else: path.write_bytes(path.read_bytes() + b' ')
                account_calls = []; factory_calls = []
                with patch.object(cli, 'normalized_prechecks', side_effect=lambda *a, **k: account_calls.append(True)):
                    with self.subTest(kind=kind), self.assertRaises(ValueError):
                        cli.execute_admitted(root, 1, setup.environment(), temporary_root=Path(temporary), git_reader=setup.git_reader, client_factory=lambda: factory_calls.append(True), clock=lambda: fixtures.NOW)
                self.assertEqual(account_calls, []); self.assertEqual(factory_calls, [])

    def test_hash_correct_but_failing_or_unrelated_case_review_is_rejected(self):
        mutations = [lambda x: x.update(verdict='CHANGES_REQUIRED_NOT_APPROVED_FOR_ACTIVATION'), lambda x: x.update(case_raw_file_sha256='1' * 64), lambda x: x.update(case_canonical_packet_sha256='2' * 64), lambda x: x.update(runtime_sha256='3' * 64), lambda x: x.update(runtime_commit='4' * 40), lambda x: x['checks'].update(native_admissibility_passed=False), lambda x: x['checks'].update(native_capacity_passed=False), lambda x: x.update(live_execution_authorized=True)]
        for mutation in mutations:
            with tempfile.TemporaryDirectory() as root:
                package = self.make(root); path = Path(root) / reviews.CASE_REVIEW
                value = cli.load_json(path); mutation(value); r.save(path, value)
                package.value['independent_case_review_sha256'] = r.file_sha(path)
                with self.assertRaises(ValueError): package.verify()

    def test_hash_correct_but_unrelated_executor_workflow_reader_or_case_target_refuses(self):
        mutations = [lambda x: x.update(verdict='CHANGES_REQUIRED_NOT_APPROVED_FOR_ACTIVATION'), lambda x: x['executor_files_sha256'].update({'hcl_entry_contract_smoke_candidate.py': '5' * 64}), lambda x: x['workflow_files_sha256'].update({next(iter(x['workflow_files_sha256'])): '6' * 64}), lambda x: x['read_only_reader_files_sha256'].update({'scripts/two_stage_account.py': '7' * 64}), lambda x: x.update(case_review_file_sha256='8' * 64), lambda x: x.update(runtime_sha256='9' * 64), lambda x: x['checks'].update(all_blockers_resolved=False), lambda x: x['verification'].update(provider_free_tests_passed=0)]
        for mutation in mutations:
            with tempfile.TemporaryDirectory() as root:
                package = self.make(root); path = Path(root) / reviews.EXECUTOR_REVIEW
                value = cli.load_json(path); mutation(value); r.save(path, value)
                package.value['independent_executor_review_sha256'] = r.file_sha(path)
                with self.assertRaises(ValueError): package.verify()

    def test_raw_case_bytes_and_canonical_case_digest_are_distinct_checked_targets(self):
        with tempfile.TemporaryDirectory() as root:
            package = self.make(root); path = Path(root) / reviews.CASE_FILE
            self.assertNotEqual(package.value['case_raw_file_sha256'], package.value['packet_sha256'])
            original = path.read_bytes(); parsed = json.loads(original)
            path.write_bytes(r.canonical(parsed))  # Same JSON value, different byte artifact.
            with self.assertRaisesRegex(ValueError, 'EXACT_REVIEW_OR_CASE_FILE_BYTES_REQUIRED'): package.verify()
            path.write_bytes(original); package.verify()
            package.value['case_raw_file_sha256'] = package.value['packet_sha256']
            with self.assertRaises(ValueError): package.verify()

    def test_actual_v5_case_review_reference_targets_raw_and_canonical_correctly(self):
        path = Path(r.__file__).parent / 'review-inputs/case-review.json'
        self.assertEqual(r.file_sha(path), '804a6010a7401b186dd70efcb0dc753964e9b29b6ac091544bd43bba688a6eb7')
        value = cli.load_json(path)
        self.assertEqual(value['case_raw_file_sha256'], '5f89c5de74111a3ae9a396ebc194c393684f851bb73ec2e42a42d2a48cc18409')
        self.assertEqual(value['case_canonical_packet_sha256'], 'fa39ec373700214c1280ea5413fa46cbfe006641d02a8a094757b87f05507e2f')
        self.assertTrue(all(value['checks'][key] is True for key in {'source_rubric_passed', 'native_admissibility_passed', 'native_capacity_passed', 'all_five_cases_unscored_before_output'}))
        self.assertFalse(value['live_execution_authorized'])

    def test_reviews_are_non_circular_file_set_targets_not_later_package_hash(self):
        with tempfile.TemporaryDirectory() as root:
            package = self.make(root)
            for relative in (reviews.CASE_REVIEW, reviews.EXECUTOR_REVIEW):
                value = cli.load_json(Path(root) / relative)
                self.assertNotIn('package_sha256', value)
                self.assertNotIn(r.digest(package.value), json.dumps(value))
            self.assertEqual(cli.load_json(Path(root) / reviews.EXECUTOR_REVIEW)['executor_files_sha256'], package.value['configuration']['executor_files'])


class FinalWorkerDispatchMarginTests(unittest.TestCase):
    def ledger(self, directory, wall, elapsed):
        package = r.OfflinePackage.build(fixtures.fixture_packet(), fixtures.RUNTIME)
        ledger = r.Ledger(directory, package, 1, lambda: wall[0], lambda: elapsed[0], offline=True)
        ledger.active = package.cases[0]['case_id'] + ':HCL'
        client = fixtures.Client(); port = r.BoundedPort(client, ledger, ledger.active)
        prompt = r.messages(package.cases[0], 'HCL'); port.reservation_usd('planning', prompt)
        return package, ledger, client, port, prompt

    def assert_zero_send_closed(self, package, ledger, client):
        self.assertEqual(client.calls, []); self.assertTrue(ledger.stopped)
        row = ledger.value['calls'][0]
        self.assertEqual(row['failure_code'], 'FINAL_DISPATCH_MARGIN_REJECTED_NO_CALL')
        self.assertFalse(row['provider_call']); self.assertFalse(row['offline_transport_call'])
        self.assertEqual(row['invocation_status'], 'NOT_INVOKED'); self.assertNotIn('usage', row)
        self.assertEqual(row['reserved_cny'], str(r.HOLD_CNY['planning']))
        ledger.arm(ledger.active)['status'] = 'UNKNOWN_FAILURE_STOP'; ledger.close()
        evidence = public.export(ledger.value, package)
        self.assertEqual(evidence['provider_calls'], 0); self.assertEqual(evidence['offline_transport_calls'], 0)
        self.assertEqual(evidence['reserved_cny'], str(r.HOLD_CNY['planning']))
        self.assertEqual(evidence['budget_state'], 'CLOSED_NO_TRANSFER_NO_RETRY')
        self.assertEqual(evidence['remaining_authorized_calls'], 0)

    def test_delayed_fsync_blocks_send_after_stage_window(self):
        with tempfile.TemporaryDirectory() as root:
            wall = [fixtures.NOW]; elapsed = [0]
            package, ledger, client, port, prompt = self.ledger(Path(root) / 'run', wall, elapsed)
            original = ledger.persist; delayed = [False]
            def delayed_persist():
                original()
                if not delayed[0] and ledger.value['calls'][0]['invocation_status'] == 'INVOKED_OR_SEND_UNKNOWN':
                    delayed[0] = True; wall[0] += timedelta(seconds=601); elapsed[0] += 601
            with patch.object(ledger, 'persist', delayed_persist), self.assertRaises(r.MeteredPortError):
                port.complete('planning', prompt)
            self.assertGreater(elapsed[0], r.ELAPSED[1]); self.assert_zero_send_closed(package, ledger, client)

    def test_delayed_fsync_blocks_lost_180_second_stage_margin(self):
        with tempfile.TemporaryDirectory() as root:
            wall = [fixtures.NOW]; elapsed = [0]
            package, ledger, client, port, prompt = self.ledger(Path(root) / 'run', wall, elapsed)
            original = ledger.persist; changed = [False]
            def persist():
                original()
                if not changed[0] and ledger.value['calls'][0]['invocation_status'] == 'INVOKED_OR_SEND_UNKNOWN':
                    changed[0] = True; wall[0] += timedelta(seconds=420); elapsed[0] += 420
            with patch.object(ledger, 'persist', persist), self.assertRaises(r.MeteredPortError): port.complete('planning', prompt)
            self.assertLess(elapsed[0], r.ELAPSED[1]); self.assert_zero_send_closed(package, ledger, client)

    def test_consumption_persistence_rechecks_approval_before_sdk_factory(self):
        setup = adapter_fixtures.AdapterTests()
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temporary:
            package, grant, args, locations = setup.setup_files(root, temporary)
            wall = [fixtures.NOW]; factories = []; original = cli.exclusive_json
            def delayed(path, value):
                original(path, value)
                if Path(path) == locations['consumed']: wall[0] = r.timestamp(r.APPROVED) - timedelta(seconds=1)
            with patch.object(cli, 'exclusive_json', delayed), self.assertRaises(ValueError):
                cli.execute_admitted(root, 1, setup.environment(), temporary_root=Path(temporary), git_reader=setup.git_reader, client_factory=lambda: factories.append(True), clock=lambda: wall[0])
            self.assertEqual(factories, []); self.assertTrue(locations['consumed'].exists()); self.assertFalse(locations['directory'].exists())

    def test_worker_scheduling_delay_checks_stage_window_at_dispatch(self):
        with tempfile.TemporaryDirectory() as root:
            wall = [fixtures.NOW]; elapsed = [0]
            package, ledger, client, port, prompt = self.ledger(Path(root) / 'run', wall, elapsed)
            original_thread = r.threading.Thread
            def delayed_thread(*args, **kwargs):
                target = kwargs['target']
                def delayed():
                    wall[0] += timedelta(seconds=421); elapsed[0] = 421
                    target()
                kwargs['target'] = delayed
                return original_thread(*args, **kwargs)
            with patch.object(r.threading, 'Thread', delayed_thread), self.assertRaises(r.MeteredPortError): port.complete('planning', prompt)
            self.assert_zero_send_closed(package, ledger, client)


class RealGrantAdoptionHistoryTests(unittest.TestCase):
    """Actual disposable Git E->G->M, including a normal two-parent grant merge."""
    def git(self, root, *args):
        result = subprocess.run(['git', '-C', str(root), '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', '-c', 'user.name=Offline Regression', '-c', 'user.email=offline@example.invalid', *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env={'PATH': '/usr/bin:/bin', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_TERMINAL_PROMPT': '0'})
        if result.returncode: raise AssertionError('DISPOSABLE_GIT_FIXTURE_FAILED: ' + ' '.join(args))
        return result.stdout.strip()

    def commit(self, root, message):
        self.git(root, 'add', '-A'); self.git(root, 'commit', '-m', message)
        return self.git(root, 'rev-parse', 'HEAD')

    def make_history(self, root, *, merge_grant=False, stage=1, extra_grant_change=False, extra_marker_change=False):
        root = Path(root); self.git(root, 'init', '-b', 'main')
        (root / 'offline-runtime-anchor.txt').write_text('Synthetic local Git anchor; no model or workflow execution.\n')
        runtime_commit = self.commit(root, 'Offline runtime anchor R')
        package = fixtures.ReusableEntryContractTests().frozen_fixture(root)
        for field in cli.REPAIR_FIELDS: package.value[field] = runtime_commit
        fixtures.write_review_fixture_artifacts(package)
        locations = cli.paths(root, stage)
        r.save(locations['package'], package.value)
        # The exact reviewed code/test set is present at E, before any grant.
        executor_dir = root / cli.EXECUTOR_RELATIVE
        for name in package.value['configuration']['executor_files']:
            target = executor_dir / name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((Path(r.__file__).parent / name).read_bytes())
        if stage == 2:
            prior = root / 'reports/offline-smoke-adoption-placeholder.txt'; prior.parent.mkdir(exist_ok=True); prior.write_text('E may contain prior adopted smoke artifacts; this fixture never claims a real smoke.\n')
        executor = self.commit(root, 'Adopt reviewed code and package E')
        grant, args = fixtures.ReusableEntryContractTests().inputs(package, stage)
        grant['executor_commit'] = executor
        if merge_grant: self.git(root, 'switch', '-c', 'offline-grant-pr')
        r.save(locations['grant'], grant)
        if extra_grant_change: (root / 'unrelated-change.txt').write_text('Must refuse E..G drift.\n')
        self.commit(root, 'Add only synthetic stage grant')
        if merge_grant:
            self.git(root, 'switch', 'main'); self.git(root, 'merge', '--no-ff', 'offline-grant-pr', '-m', 'Merge synthetic grant-only PR G')
        grant_commit = self.git(root, 'rev-parse', 'HEAD')
        marker = dict(schema='hcl-entry-contract-smoke-marker-proposal-v1', authorization_ref=r.AUTH, stage=stage, package_sha256=r.digest(package.value), grant_sha256=r.digest(grant), executor_commit=executor, grant_commit=grant_commit)
        r.save(locations['marker'], marker)
        if extra_marker_change: (root / 'marker-extra.txt').write_text('Must refuse G..M drift.\n')
        head = self.commit(root, 'Synthetic marker-only M')
        identity = dict(run_id='42', head_sha=head)
        history = [dict(total_count=1, workflow_runs=[dict(id=42, workflow_id=7, path=f'.github/workflows/hcl-entry-contract-smoke-20261008-{stage}-once.yml', head_branch='main', run_attempt=1, head_sha=head, event='push', created_at=fixtures.NOW.isoformat())])]
        environment = adapter_fixtures.AdapterTests().environment(stage); environment['GITHUB_SHA'] = head
        return package, grant, identity, history, environment, executor, grant_commit, head

    def test_real_direct_grant_and_pr_merge_both_have_non_circular_valid_e_g_m(self):
        for merge in (False, True):
            for stage in (1,):
                with self.subTest(merge=merge, stage=stage), tempfile.TemporaryDirectory() as root:
                    package, grant, identity, history, env, executor, adoption, marker = self.make_history(root, merge_grant=merge, stage=stage)
                    package.verify()
                    launch = cli.read_launch(root, stage, package, grant, identity, env, history)
                    self.assertTrue(r.validate_launch_proposal(**launch))
                    self.assertEqual(launch['executor_commit'], executor); self.assertEqual(launch['grant_commit'], adoption)
                    self.assertEqual(launch['parent_sha'], adoption); self.assertEqual(launch['head_sha'], marker)
                    self.assertNotEqual(executor, adoption); self.assertNotEqual(adoption, marker)
                    stored = json.loads(self.git(root, 'show', f'{adoption}:.github/HCL_ENTRY_CONTRACT_SMOKE_20261008_{stage}_GRANT.json'))
                    self.assertEqual(stored['executor_commit'], executor)
                    parent_count = len(self.git(root, 'rev-list', '--parents', '-n', '1', adoption).split()) - 1
                    self.assertEqual(parent_count, 2 if merge else 1)
                    self.assertEqual(launch['grant_changed_paths'], [f'.github/HCL_ENTRY_CONTRACT_SMOKE_20261008_{stage}_GRANT.json'])

    def test_unrelated_executor_to_grant_change_rejects_direct_or_merge_adoption(self):
        for merge in (False, True):
            with tempfile.TemporaryDirectory() as root:
                package, grant, identity, history, env, *_ = self.make_history(root, merge_grant=merge, extra_grant_change=True)
                with self.assertRaisesRegex(ValueError, 'ONLY_STAGE_GRANT_MAY_CHANGE'):
                    cli.read_launch(root, 1, package, grant, identity, env, history)

    def test_unrelated_marker_commit_change_rejects(self):
        with tempfile.TemporaryDirectory() as root:
            package, grant, identity, history, env, *_ = self.make_history(root, merge_grant=True, extra_marker_change=True)
            with self.assertRaisesRegex(ValueError, 'EXACT_MARKER_ONLY_LAUNCH_REQUIRED'):
                cli.read_launch(root, 1, package, grant, identity, env, history)

    def test_marker_must_bind_both_confirmed_adoption_g_and_known_executor_e(self):
        with tempfile.TemporaryDirectory() as root:
            package, grant, identity, history, env, *_ = self.make_history(root, merge_grant=True)
            launch = cli.read_launch(root, 1, package, grant, identity, env, history)
            for field in ('executor_commit', 'grant_commit'):
                changed = copy.deepcopy(launch); changed['marker'][field] = 'f' * 40
                with self.assertRaises(ValueError): r.validate_launch_proposal(**changed)


class HonestIntegrityClosureTests(unittest.TestCase):
    def test_corrupted_call_ledger_outputs_unknown_totals_and_preserves_original_holds_file(self):
        setup = adapter_fixtures.AdapterTests()
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temporary:
            package, grant, args, locations = setup.setup_files(root, temporary)
            result = r.run(fixtures.Client(), package, grant, locations['directory'], **args)
            path = locations['directory'] / 'receipt.json'; result['reserved_cny'] = 'NON_NUMERIC_PRIVATE_CANARY'; r.save(path, result)
            before = path.read_bytes(); exported = cli.export_terminal(root, 1, setup.environment(), now=fixtures.NOW)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(exported['status'], 'RECEIPT_INTEGRITY_UNAVAILABLE_NO_RESUME')
            self.assertIsNone(exported['reserved_cny']); self.assertIsNone(exported['provider_calls']); self.assertIsNone(exported['usage_rated_cny'])
            self.assertEqual(exported['prior_reservations'], 'ALL_PREEXISTING_FULL_HOLDS_RETAINED_NO_RELEASE')
            self.assertEqual(exported['remaining_authorized_calls'], 0)
            self.assertNotIn('NON_NUMERIC_PRIVATE_CANARY', json.dumps(exported))

    def test_exact_adopted_runtime_stays_unchanged(self):
        self.assertEqual(r.runtime_digest(fixtures.RUNTIME), '50e62d02790f165d1d73fc3275fc6f795da7582b9f81143eaa7aa69806660d16')



if __name__ == '__main__':
    unittest.main()
