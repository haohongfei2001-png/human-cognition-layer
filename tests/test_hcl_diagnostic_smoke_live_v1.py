"""Provider-free new-authority/control tests. ALL approvals are TEST FIXTURES.

Nothing here creates real reviews/grants or imports/constructs an OpenAI client.
Transport-shaped doubles exercise live accounting, never establish real spend,
provider success, independent review, semantic quality, or authorization.
"""
import copy
from contextlib import nullcontext
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from hcl.cognition import universal_entry
from scripts import hcl_diagnostic_smoke_live_v1 as live
from scripts import hcl_offline_diagnostic_export_v1 as r
from scripts import hcl_offline_diagnostic_public_v1 as p
from scripts.hcl_offline_diagnostic_reference import _reference as ref

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 8, 13, tzinfo=timezone.utc)
IDENTITY = dict(run_id='42', head_sha='a' * 40)
CANARY = 'PRIVATE_PROVIDER_OR_PLANNER_CANARY'


def packet():
    return live.load_json(ROOT / live.CASE_PATH)


def package_fixture():
    data = packet()
    return live.LivePackage(dict(schema=live.PACKAGE_SCHEMA, status='FROZEN_BEFORE_THIS_DIAGNOSTIC_SMOKE_OUTPUT',
        authorization_ref=live.AUTH, approval_message_id=live.APPROVAL_MESSAGE_ID,
        approved_at_bound=live.APPROVED, currency='CNY', packet_sha256=live.PACKET_SHA256,
        case_raw_file_sha256=live.CASE_RAW_SHA256, runtime_sha256=live.RUNTIME_SHA256,
        runtime_commit=live.RUNTIME_COMMIT, configuration=live.build_configuration(data, ROOT),
        implementation_files={}, workflow_files={}, read_only_reader_files=dict(live.READER_PINS),
        independent_case_review_sha256='c' * 64, independent_executor_review_sha256='d' * 64), data, ROOT)


def permission_fixture():
    return dict(schema=live.PREFIX + '-public-permission-v1', authorization_ref=live.AUTH,
        approval_message_id=live.APPROVAL_MESSAGE_ID, approved_at_bound=live.APPROVED,
        destination=live.DESTINATION, packet_sha256=live.PACKET_SHA256, maximum_final_texts=1,
        maximum_native_records=1, maximum_operations_per_record=3, maximum_native_record_bytes=1048576,
        safe_error_codes_and_stages=True, budget_and_closing_records=True,
        source_validated_native_arguments_and_results=True, full_planner_response=False,
        hidden_reasoning=False, private_sources=False, credentials=False)


def grant_fixture(package):
    return dict(schema=live.PREFIX + '-new-grant-v1', status='READY', authorization_ref=live.AUTH,
        approval_message_id=live.APPROVAL_MESSAGE_ID, currency='CNY', stage=1,
        package_sha256=r.digest(package.value), approved_at_bound=live.APPROVED, expires_at=None,
        authorized_calls=2, authorized_cny='2.30', executor_commit='e' * 40,
        public_native_evidence_permission=permission_fixture(), retries=0,
        historical_budget_transfer=False, other_stage_budget_transfer=False)


def launch_fixture(package, grant):
    marker = dict(schema=live.PREFIX + '-marker-proposal-v1', authorization_ref=live.AUTH, stage=1,
        package_sha256=r.digest(package.value), grant_sha256=r.digest(grant),
        executor_commit='e' * 40, grant_commit='b' * 40)
    row = dict(id=42, workflow_id=7, head_branch='main', path=str(live.WORKFLOW_PATH),
        run_attempt=1, head_sha=IDENTITY['head_sha'], event='push', created_at=NOW.isoformat())
    return dict(run_id=42, attempt=1, pages=[dict(total_count=1, workflow_runs=[row])], workflow_id=7,
        head_sha=IDENTITY['head_sha'], parent_sha='b' * 40, event='push', paths=[str(live.MARKER_PATH)],
        marker=marker, package_sha256=r.digest(package.value), grant_sha256=r.digest(grant), stage=1,
        executor_commit='e' * 40, grant_commit='b' * 40, executor_ancestor_of_grant=True,
        grant_changed_paths=[str(live.GRANT_PATH)])


def prechecks_fixture():
    price = dict(**IDENTITY, url='https://api-docs.deepseek.com/zh-cn/quick_start/pricing/',
        checked_at=NOW.isoformat(), sha256='f' * 64,
        rates=dict(currency='CNY', input='9.0', output='27.0', model=r.MODEL, version='DeepSeek-V4-Pro-0813'))
    account = dict(schema=live.PREFIX + '-account-readiness-v1', **IDENTITY, checked_at=NOW.isoformat(),
        currency='CNY', available=True, model_calls=0, account_read_queries=1, existing_account_only=True)
    return price, account


def environment():
    return dict(GITHUB_REF='refs/heads/main', GITHUB_RUN_ATTEMPT='1', GITHUB_EVENT_NAME='push',
        GITHUB_REPOSITORY=live.REPOSITORY,
        GITHUB_WORKFLOW_REF=f'{live.REPOSITORY}/{live.WORKFLOW_PATH}@refs/heads/main',
        GITHUB_RUN_ID=IDENTITY['run_id'], GITHUB_SHA=IDENTITY['head_sha'])


def operation():
    source = packet()['cases'][0]['model_input']['sources'][0]
    quote = source['text'].split('\n\n')[2]
    return dict(capability='B01', question='What does Bea believe about Arun?',
        source_ids=[source['source_id']], bindings=[], input_mode='semantic',
        semantic_candidates=[dict(source_id=source['source_id'], quote=quote,
            start=source['text'].index(quote), kind='event',
            content=dict(canonical_statement='Bea: I believe Arun knows the flute is playback.'))])


def proposal(*operations):
    return json.dumps(dict(task=CANARY, operations=list(operations), limitations=[CANARY]))


class TestTransport:
    """In-memory SDK-shaped double, no imported SDK and no network route."""
    max_retries = 0
    timeout = 180
    base_url = 'https://api.deepseek.com'

    def __init__(self, responses=()):
        self.responses = responses; self.calls = []

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    def create(self, **request):
        self.calls.append(copy.deepcopy(request))
        if len(self.calls) > 2: raise AssertionError('TEST_NO_RETRIES')
        payload = json.loads(request['messages'][-1]['content'])
        if len(self.calls) <= len(self.responses):
            text = self.responses[len(self.calls) - 1]
        elif len(self.calls) == 1:
            text = proposal(operation())
        else:
            text = json.dumps(dict(answer='TEST FIXTURE: Bea attributes knowledge to Arun; Arun reports uncertainty. Jules reports Bea’s position. Equipment is unverified.',
                source_citations=[dict(source_id=s['source_id'], version=s['version'], quote=s['text'], start=0) for s in payload['sources']],
                uncertainty='TEST FIXTURE: tonight only; no equipment inspection.', assumptions='TEST FIXTURE ONLY.'))
        return dict(model=r.MODEL, usage=dict(prompt_tokens=100, completion_tokens=100, total_tokens=200),
            choices=[dict(finish_reason='stop', message=dict(content=text, reasoning_content=CANARY))],
            private_envelope=CANARY)


def source_review_fixture(package, evidence):
    arm = evidence['arms'][0]
    def checks(ids):
        return [dict(id=i, passed=True, source_evidence='TEST FIXTURE ONLY', answer_evidence='TEST FIXTURE ONLY') for i in ids]
    return dict(schema=live.REVIEW_SCHEMA, authorization_ref=live.AUTH, package_sha256=r.digest(package.value),
        packet_sha256=r.digest(package.packet), evidence_sha256=r.digest(evidence),
        final_answer_sha256=arm['final_answer_sha256'], request_diagnostics_sha256=r.digest(arm['request_diagnostics']),
        native_review_sha256=arm['native_review_sha256'], reviewer_role='INDEPENDENT_SOURCE_FIRST_AFTER_OUTPUT',
        same_smoke_and_rules_fixed_before_entry_contract_smoke_output=True, gates={key: True for key in p.GATES},
        obligations=checks(p.obligation_ids(package.packet['cases'][0])), smoke_semantics=checks(['S1', 'S2', 'S3', 'S4']),
        relevant_native_capability_ids=['B01'], critical_failure_tags=[], overall_pass=True)


def independent_review_fixtures(package):
    """In-memory gate controls, never written as actual independent reviews."""
    case = dict(schema=live.PREFIX+'-independent-case-review-v1', authorization_ref=live.AUTH,
        verdict='PASS_FOR_BOUNDED_DEVELOPMENT_ONLY',
        reviewer_role='INDEPENDENT_REGRESSION_CASE_REVIEW_BEFORE_DIAGNOSTIC_SMOKE_OUTPUT',
        targets=live.case_review_targets(package.value), checks={key: True for key in live.CASE_CHECKS},
        provider_calls=0, live_execution_authorized=False, efficacy_claimed=False)
    executor = dict(schema=live.PREFIX+'-independent-executor-approval-v1', authorization_ref=live.AUTH,
        verdict='PASS_FOR_BOUNDED_EXECUTOR_PACKAGE', reviewer_role='INDEPENDENT_READ_ONLY_SECURITY_REVIEW',
        targets=live.executor_review_targets(package.value), checks={key: True for key in live.EXECUTOR_CHECKS},
        verification=dict(provider_calls=0, account_queries=0, credentials_read=False,
                          sdk_constructed=False, provider_free_tests_passed=1), live_execution_authorized=False)
    return case, executor


class AuthorityTests(unittest.TestCase):
    def test_full_package_freeze_checks_actual_source_and_noncircular_review_targets(self):
        package = package_fixture(); value = package.value
        value['implementation_files'] = {name: r.file_sha(ROOT/name) for name in live.IMPLEMENTATION_FILES}
        value['workflow_files'] = {str(live.WORKFLOW_PATH): r.file_sha(ROOT/live.WORKFLOW_PATH)}
        case, executor = independent_review_fixtures(package)
        actual = live.hashed_json
        def read(root, relative, expected):
            if relative == live.CASE_REVIEW: return copy.deepcopy(case)
            if relative == live.EXECUTOR_REVIEW: return copy.deepcopy(executor)
            return actual(root, relative, expected)
        with patch.object(live, 'hashed_json', read):
            package.verify()
            for field, val in [('schema', 'hcl-entry-contract-smoke-final-package-v1'),
                ('approval_message_id', 'OLD_APPROVAL'), ('runtime_commit', '0'*40),
                ('runtime_sha256', '0'*64), ('packet_sha256', '0'*64)]:
                bad = live.LivePackage(copy.deepcopy(value), package.packet, ROOT); bad.value[field] = val
                with self.subTest(field=field), self.assertRaises(ValueError): bad.verify()
            for key, val in [('sdk_retries', False), ('planning_tokens', 16385), ('maximum_request_bytes', 36001)]:
                bad = live.LivePackage(copy.deepcopy(value), package.packet, ROOT); bad.value['configuration'][key] = val
                with self.subTest(key=key), self.assertRaises(ValueError): bad.verify()
            bad = live.LivePackage(copy.deepcopy(value), package.packet, ROOT)
            bad.value['implementation_files']['scripts/hcl_diagnostic_smoke_live_v1.py'] = '0'*64
            with self.assertRaisesRegex(ValueError, 'FILE_PINS'): bad.verify()

    def test_independent_review_verdict_checks_and_source_targets_cannot_be_rehashed_away(self):
        package = package_fixture(); case, executor = independent_review_fixtures(package)
        mutations = [(0, lambda x: x.update(verdict='PENDING')), (0, lambda x: x.update(live_execution_authorized=0)),
            (0, lambda x: x['checks'].update(native_capacity_passed=False)),
            (0, lambda x: x['targets'].update(runtime_sha256='0'*64)),
            (1, lambda x: x.update(authorization_ref=ref.AUTH)),
            (1, lambda x: x['targets'].update(configuration_sha256='0'*64)),
            (1, lambda x: x['verification'].update(provider_calls=1)),
            (1, lambda x: x['verification'].update(credentials_read=True)),
            (1, lambda x: x['verification'].update(provider_free_tests_passed=0)),
            (1, lambda x: x['checks'].update(original_receipt_and_capture_bound=False))]
        for index, mutate in mutations:
            rows = [copy.deepcopy(case), copy.deepcopy(executor)]; mutate(rows[index])
            with self.subTest(index=index), patch.object(live, 'hashed_json', side_effect=rows), self.assertRaises(ValueError):
                live.verify_review_artifacts(package)

    def test_current_request_and_runtime_stay_exact_and_old_authority_excluded(self):
        package = package_fixture(); config = package.value['configuration']
        self.assertEqual(config['runtime_sha256'], live.RUNTIME_SHA256)
        request = next(iter(config['requests'].values()))
        self.assertEqual(request['full_request_utf8_bytes'], 28333)
        self.assertEqual(request['full_request_sha256'], live.PLANNING_SHA256)
        self.assertNotIn(ref.AUTH, json.dumps(config))
        self.assertEqual(config['phase_holds_cny'], {'planning': '1.109664', 'answer': '1.109664'})
        self.assertEqual(config['reasoning_effort'], {'planning': 'high', 'answer': 'low'})

    def test_old_frozen_and_offline_packages_cannot_admit(self):
        old = ref.FrozenPackage({}, packet(), ROOT)
        offline = r.OfflinePackage.build(packet(), ROOT)
        for package in (old, offline, {}, None):
            with self.subTest(kind=type(package)), self.assertRaisesRegex(ValueError, 'EXACT_NEW_LIVE'):
                live.require_new_grant(package, {}, 1, NOW)
        with self.assertRaisesRegex(ValueError, 'EXACT_NEW_DIAGNOSTIC_PACKAGE'):
            live.LivePackage(offline.value, packet(), ROOT).verify()

    def test_archived_grant_gate_rejects_new_subclass_without_using_old_authority(self):
        with self.assertRaisesRegex(ValueError, 'OFFLINE_CANDIDATE'):
            ref.require_new_grant(package_fixture(), {}, 1, NOW)

    def test_new_grant_rejects_old_or_expanded_scope_before_factory(self):
        package = package_fixture(); grant = grant_fixture(package)
        with patch.object(live.LivePackage, 'verify', return_value=None):
            self.assertTrue(live.require_new_grant(package, grant, 1, NOW))
            changes = dict(authorization_ref=ref.AUTH, schema='hcl-entry-contract-smoke-new-grant-v1',
                approved_at_bound=ref.APPROVED, authorized_calls=3, authorized_cny='2.31', retries=1,
                historical_budget_transfer=True, other_stage_budget_transfer=True, stage=2,
                public_native_evidence_permission=None, approval_message_id='OLD_APPROVAL', expires_at='2030-01-01T00:00:00Z')
            for key, value in changes.items():
                with self.subTest(key=key), self.assertRaises(ValueError):
                    live.require_new_grant(package, dict(grant, **{key: value}), 1, NOW)
            for now in (datetime(2026, 10, 8, 12, tzinfo=timezone.utc), datetime(2026, 10, 8)):
                with self.assertRaises(ValueError): live.require_new_grant(package, grant, 1, now)
            self.assertTrue(live.require_new_grant(package, grant, 1, NOW + timedelta(days=40)))

    def test_permission_is_exact_new_destination_budget_and_disclosure(self):
        permission = permission_fixture()
        self.assertTrue(live.validate_permission(permission, live.PACKET_SHA256))
        for key, changed in dict(authorization_ref=ref.AUTH, destination='https://example.invalid', maximum_native_records=2,
            maximum_operations_per_record=4, maximum_native_record_bytes=1048577, maximum_final_texts=2,
            full_planner_response=True, hidden_reasoning=True, private_sources=True, credentials=True,
            budget_and_closing_records=False, approval_message_id='old', safe_error_codes_and_stages=1).items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                live.validate_permission(dict(permission, **{key: changed}), live.PACKET_SHA256)

    def test_environment_rejects_every_changed_identity(self):
        env = environment(); self.assertEqual(live.environment_identity(env), IDENTITY)
        for key in env:
            changed = dict(env); changed[key] = 'wrong'
            with self.subTest(key=key), self.assertRaises(ValueError): live.environment_identity(changed)
        with self.assertRaises(ValueError): live.environment_identity(env, 2)

    def test_complete_new_history_marker_and_adoption_are_required(self):
        package = package_fixture(); launch = launch_fixture(package, grant_fixture(package))
        self.assertTrue(live.validate_launch_proposal(**launch))
        mutations = [lambda x: x.update(attempt=2), lambda x: x.update(stage=True),
            lambda x: x.update(event='workflow_dispatch'), lambda x: x.update(parent_sha='c' * 40),
            lambda x: x.update(executor_ancestor_of_grant=False), lambda x: x.update(grant_changed_paths=['other']),
            lambda x: x.update(paths=[str(live.MARKER_PATH), 'unrelated']),
            lambda x: x['marker'].update(authorization_ref=ref.AUTH), lambda x: x['marker'].update(stage=True),
            lambda x: x['pages'][0].update(total_count=2),
            lambda x: x['pages'][0]['workflow_runs'].append(copy.deepcopy(x['pages'][0]['workflow_runs'][0])),
            lambda x: x['pages'][0]['workflow_runs'][0].update(path='.github/workflows/old.yml'),
            lambda x: x['pages'][0]['workflow_runs'][0].update(run_attempt=2),
            lambda x: x['pages'][0]['workflow_runs'][0].update(head_sha='c' * 40)]
        for index, mutate in enumerate(mutations):
            bad = copy.deepcopy(launch); mutate(bad)
            with self.subTest(index=index), self.assertRaises(ValueError): live.validate_launch_proposal(**bad)

    def test_fresh_exact_peak_price_and_existing_account_only(self):
        price, account = prechecks_fixture()
        self.assertTrue(live.validate_readonly_prechecks(price, account, IDENTITY, NOW))
        for target, key, val in [('price', 'checked_at', (NOW-timedelta(minutes=11)).isoformat()),
            ('price', 'url', 'https://unofficial.invalid'), ('price', 'run_id', '43'),
            ('account', 'head_sha', 'b'*40), ('account', 'currency', 'USD'),
            ('account', 'account_read_queries', 2), ('account', 'model_calls', True),
            ('account', 'existing_account_only', False), ('account', 'available', False),
            ('account', 'checked_at', (NOW+timedelta(seconds=1)).isoformat())]:
            a, b = copy.deepcopy(price), copy.deepcopy(account)
            (a if target == 'price' else b)[key] = val
            with self.subTest(target=target, key=key), self.assertRaises(ValueError):
                live.validate_readonly_prechecks(a, b, IDENTITY, NOW)

    def test_exclusive_consumption_is_durable_and_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'consumed.json'; live.exclusive_json(path, {'test': 1})
            before = path.read_bytes()
            with self.assertRaises(FileExistsError): live.exclusive_json(path, {'test': 2})
            self.assertEqual(path.read_bytes(), before)

    def test_pinned_precheck_normalization_preserves_exact_same_run_read_facts(self):
        price, account = prechecks_fixture()
        original = {k: v for k, v in account.items() if k != 'existing_account_only'}
        original['schema'] = 'hcl-two-stage-account-readiness-v1'
        with tempfile.TemporaryDirectory() as temporary:
            locations = live.paths(ROOT, 1, Path(temporary))
            r.save(locations['price'], price); r.save(locations['account'], original)
            r.save(locations['presence'], dict(IDENTITY, existing_provider_secret='PRESENT'))
            self.assertEqual(live.normalized_prechecks(ROOT, 1, IDENTITY, NOW, temporary_root=Path(temporary)), (price, account))
            original['account_read_queries'] = True; r.save(locations['account'], original)
            with self.assertRaisesRegex(ValueError, 'EXACT_EXISTING_ACCOUNT_READ_COUNT'):
                live.normalized_prechecks(ROOT, 1, IDENTITY, NOW, temporary_root=Path(temporary))


class LiveChainTests(unittest.TestCase):
    def chain(self, responses=(), *, context=None, transport=None):
        package = package_fixture(); grant = grant_fixture(package); client = transport or TestTransport(responses)
        with tempfile.TemporaryDirectory() as directory, patch.object(live.LivePackage, 'verify', return_value=None):
            ledger = live.Ledger(Path(directory)/'private', package, 1, lambda: NOW, __import__('time').monotonic,
                identity=IDENTITY, admission_hashes=dict(grant_sha256=r.digest(grant),
                    launch_sha256='1'*64, price_sha256='2'*64, account_sha256='3'*64))
            with context or nullcontext():
                receipt = r._run_with_ledger(ledger, client)
            self.assertEqual(receipt, live.load_json(ledger.path))
            bundle_path = ledger.directory / 'native-review-private.json'
            bundle = live.load_json(bundle_path) if bundle_path.exists() else None
            evidence = live.export(receipt, package, grant, IDENTITY)
            if bundle is not None:
                try: evidence = live.export(receipt, package, grant, IDENTITY, native_bundle=bundle)
                except ValueError: evidence['native_publication_status'] = 'NATIVE_EXPORT_REJECTED_GATE_CLOSED'
            artifact = live.artifact_from_evidence(receipt, evidence)
            self.assertEqual(evidence, live.evidence_from_artifact(artifact, package, grant, IDENTITY))
            for path in ledger.directory.iterdir(): self.assertNotIn(CANARY, path.read_text())
        return package, grant, receipt, bundle, evidence, artifact, client

    def test_live_constructor_first_persist_never_uses_archived_authority(self):
        package = package_fixture(); values = []; actual = live.Ledger.persist
        def persist(ledger):
            actual(ledger); values.append(live.load_json(ledger.path))
        with tempfile.TemporaryDirectory() as directory, patch.object(live.LivePackage, 'verify', return_value=None), patch.object(live.Ledger, 'persist', persist):
            live.Ledger(Path(directory)/'private', package, 1, lambda: NOW, lambda: 0,
                identity=IDENTITY, admission_hashes={})
        self.assertTrue(values)
        self.assertTrue(all(value['authorization_ref'] == live.AUTH and value['schema'] == live.RECEIPT_SCHEMA and value['mode'] == live.MODE for value in values))

    def test_offline_fake_and_old_packages_are_not_live_clients_or_authority(self):
        package = package_fixture()
        with tempfile.TemporaryDirectory() as directory, patch.object(live.LivePackage, 'verify', return_value=None):
            ledger = live.Ledger(Path(directory)/'private', package, 1, lambda: NOW, lambda: 0,
                identity=IDENTITY, admission_hashes={})
            with self.assertRaisesRegex(ValueError, 'OFFLINE_FAKE'): ledger.make_port(r.FakeClient(), package.cases[0]['case_id']+':HCL')
        with self.assertRaisesRegex(ValueError, 'EXACT_DETERMINISTIC_FAKE_CLIENT'):
            r.run_offline(TestTransport(), r.OfflinePackage.build(packet(), ROOT), 1, '/unused')

    def test_malformed_and_empty_plans_preserve_safe_stage_before_native(self):
        for response, code, stage in [('not JSON', 'INVALID_PLANNING_JSON', 'PLANNING_RESPONSE_VALIDATION'),
            (proposal(), 'NATIVE_HCL_RESULT_REQUIRED_BEFORE_ANSWER', 'NATIVE_RESULT_ADMISSION')]:
            result = self.chain((response,)); receipt, evidence, client = result[2], result[4], result[6]
            self.assertEqual(receipt['arms'][0]['orchestration_failure'], {'code': code, 'stage': stage})
            self.assertEqual(evidence['arms'][0]['orchestration_failure'], receipt['arms'][0]['orchestration_failure'])
            self.assertEqual(len(client.calls), 1)
            self.assertEqual(receipt['reserved_cny'], '1.109664')
            self.assertEqual(receipt['status'], 'STOPPED_NO_RETRY')

    def test_capture_failure_keeps_diagnosis_and_original_usage(self):
        value = self.chain(('not JSON',), context=patch.object(live.Ledger, 'native_review', side_effect=RuntimeError(CANARY)))
        arm = value[2]['arms'][0]
        self.assertEqual(arm['orchestration_failure'], {'code': 'INVALID_PLANNING_JSON', 'stage': 'PLANNING_RESPONSE_VALIDATION'})
        self.assertEqual(arm['capture_failure'], 'POST_RUNTIME_CAPTURE_FAILED')
        self.assertEqual(value[4]['provider_calls'], 1); self.assertIsNone(value[3])

    def test_one_pass_live_accounting_complete_native_and_trusted_review(self):
        package, grant, receipt, bundle, evidence, artifact, client = self.chain()
        self.assertEqual(len(client.calls), 2, receipt)
        self.assertEqual(evidence['status'], 'COMPLETED_ONE_PASS', receipt)
        self.assertEqual(evidence['provider_calls'], 2); self.assertEqual(evidence['offline_transport_calls'], 0)
        self.assertNotIn('actual_spend_cny', evidence); self.assertNotIn('simulated_usage_rated_cny', evidence)
        self.assertEqual(evidence['usage_rated_cny'], '0.0072'); self.assertIsNone(evidence['invoice_cost_cny'])
        self.assertEqual(receipt['reserved_cny'], '2.219328')
        self.assertEqual([call['reasoning_effort'] for call in client.calls], ['high', 'low'])
        self.assertEqual([call['max_tokens'] for call in client.calls], [16384, 16384])
        self.assertEqual(len(artifact['approved_native_evidence']['records']), 1)
        self.assertNotIn('arms', artifact)
        review = source_review_fixture(package, evidence)
        with patch.object(live.LivePackage, 'verify', return_value=None):
            self.assertTrue(live.validate_phase1_gate(package, artifact, review, grant=grant, identity=IDENTITY,
                original_receipt=receipt, original_native_bundle=bundle))

    def test_rehashed_public_receipt_and_native_cannot_replace_trusted_original(self):
        package, grant, receipt, bundle, evidence, artifact, client = self.chain()
        changed = copy.deepcopy(artifact)
        changed['original_receipt']['arms'][0]['arm_seconds'] += 0.01
        changed['approved_native_evidence']['receipt_sha256'] = r.digest(changed['original_receipt'])
        with patch.object(live.LivePackage, 'verify', return_value=None):
            forged = live.evidence_from_artifact(changed, package, grant, IDENTITY)
            review = source_review_fixture(package, forged)
            with self.assertRaisesRegex(ValueError, 'EXACT_TRUSTED_ORIGINAL_RECEIPT'):
                live.validate_phase1_gate(package, changed, review, grant=grant, identity=IDENTITY,
                    original_receipt=receipt, original_native_bundle=bundle)
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_DURABLE_RECEIPT_AND_CAPTURE'):
                live.validate_phase1_gate(package, artifact, source_review_fixture(package, evidence),
                    grant=grant, identity=IDENTITY, original_receipt=None, original_native_bundle=None)

    def test_valid_alternative_native_execution_cannot_replace_original_capture(self):
        first = self.chain(); op = operation(); op['question'] = 'What does Bea think?'
        second = self.chain((proposal(op),))
        self.assertEqual(second[4]['status'], 'COMPLETED_ONE_PASS')
        self.assertNotEqual(first[2]['arms'][0]['native_review_sha256'], second[2]['arms'][0]['native_review_sha256'])
        with patch.object(live.LivePackage, 'verify', return_value=None), self.assertRaisesRegex(ValueError, 'EXACT_TRUSTED_ORIGINAL_RECEIPT'):
            live.validate_phase1_gate(first[0], second[5], source_review_fixture(second[0], second[4]),
                grant=first[1], identity=IDENTITY, original_receipt=first[2], original_native_bundle=first[3])

    def test_native_or_original_receipt_extra_fields_fail_closed(self):
        package, grant, receipt, bundle, evidence, artifact, client = self.chain()
        changes = [lambda x: x.update(raw_plan=CANARY), lambda x: x['original_receipt'].update(raw_plan=CANARY),
            lambda x: x['original_receipt']['arms'][0].update(raw_plan=CANARY),
            lambda x: x['original_receipt']['calls'][0].update(raw_response=CANARY),
            lambda x: x['original_receipt']['admission_hashes'].update(api_key=CANARY),
            lambda x: x['approved_native_evidence'].update(another_record=CANARY),
            lambda x: x['approved_native_evidence']['records'][0].update(raw_plan=CANARY),
            lambda x: x['approved_native_evidence']['records'][0]['operations'][0]['native_result_and_policy'].update(reasoning_content=CANARY),
            lambda x: x['approved_native_evidence'].update(live_execution_authorized=False),
            lambda x: x['approved_native_evidence']['records'].append(copy.deepcopy(x['approved_native_evidence']['records'][0]))]
        with patch.object(live.LivePackage, 'verify', return_value=None):
            for index, mutate in enumerate(changes):
                value = copy.deepcopy(artifact); mutate(value)
                with self.subTest(index=index), self.assertRaises((ValueError, KeyError)):
                    live.evidence_from_artifact(value, package, grant, IDENTITY)

    def test_review_counterexample_orphan_fee_cannot_publish_private_value(self):
        package, grant, receipt, _, _, _, _ = self.chain(('not JSON',))
        bad = copy.deepcopy(receipt); call = bad['calls'][0]
        call.pop('usage'); call.pop('usage_rated_usd')
        call['usage_rated_cny'] = {'provider_envelope': CANARY}
        call.update(status='FAILED_OR_UNKNOWN', invocation_status='INVOKED_OR_SEND_UNKNOWN')
        with patch.object(live.LivePackage, 'verify', return_value=None), self.assertRaisesRegex(ValueError, 'COMPLETE_USAGE_AND_BOTH_RATED_AMOUNTS'):
            live.export(bad, package, grant, IDENTITY)

    def test_review_counterexample_unknown_send_cannot_become_zero_provider_cost(self):
        package, grant, receipt, _, _, _, _ = self.chain(('not JSON',))
        bad = copy.deepcopy(receipt); call = bad['calls'][0]
        for key in ('usage', 'usage_rated_cny', 'usage_rated_usd'): call.pop(key)
        call.update(status='FAILED_OR_UNKNOWN', invocation_status='INVOKED_OR_SEND_UNKNOWN',
                    provider_call=False, offline_transport_call=False,
                    failure_code='UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP')
        with patch.object(live.LivePackage, 'verify', return_value=None), self.assertRaisesRegex(ValueError, 'EXACT_CALL_STATUS_INVOCATION_TRANSPORT_USAGE'):
            live.export(bad, package, grant, IDENTITY)

    def test_all_usage_subsets_money_types_and_status_relations_are_checked(self):
        package, grant, receipt, _, _, _, _ = self.chain(('not JSON',))
        keys = ('usage', 'usage_rated_cny', 'usage_rated_usd')
        with patch.object(live.LivePackage, 'verify', return_value=None):
            for mask in range(8):
                bad = copy.deepcopy(receipt); call = bad['calls'][0]
                call.update(status='FAILED_OR_UNKNOWN', invocation_status='INVOKED_OR_SEND_UNKNOWN',
                            failure_code='UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP')
                for index, key in enumerate(keys):
                    if not mask & (1 << index): call.pop(key)
                with self.subTest(usage_mask=mask):
                    if mask in (0, 7):
                        value = live.export(bad, package, grant, IDENTITY)
                        self.assertEqual(value['provider_calls'], 1)
                        self.assertEqual(value['usage_complete'], mask == 7)
                        self.assertEqual(value['usage_rated_cny'], '0.0036' if mask == 7 else None)
                    else:
                        with self.assertRaisesRegex(ValueError, 'COMPLETE_USAGE_AND_BOTH_RATED_AMOUNTS'):
                            live.export(bad, package, grant, IDENTITY)
            for key in ('usage_rated_cny', 'usage_rated_usd', 'reserved_cny', 'reserved_usd',
                        'exact_request_reservation_cny', 'exact_request_reservation_usd'):
                for invalid in ({'provider_envelope': CANARY}, [CANARY], None, True, 0, 0.1, 'NaN', 'Infinity', '-Infinity', CANARY):
                    bad = copy.deepcopy(receipt); bad['calls'][0][key] = invalid
                    with self.subTest(key=key, invalid=repr(invalid)), self.assertRaises(ValueError):
                        live.export(bad, package, grant, IDENTITY)
            for changes in (dict(provider_call=False), dict(offline_transport_call=True),
                dict(invocation_status='NOT_INVOKED'), dict(status='RESERVED_BEFORE_CALL'),
                dict(status='FAILED_OR_UNKNOWN'), dict(status='RETURNED_REJECTED'),
                dict(failure_code='UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP')):
                bad = copy.deepcopy(receipt); bad['calls'][0].update(changes)
                with self.subTest(changes=changes), self.assertRaises(ValueError): live.export(bad, package, grant, IDENTITY)

    def test_every_original_receipt_field_rejects_unexpected_object_shape(self):
        package, grant, receipt, _, _, _, _ = self.chain()
        with patch.object(live.LivePackage, 'verify', return_value=None):
            for scope in ('receipt', 'arm', 'call'):
                row = receipt if scope == 'receipt' else receipt['arms' if scope == 'arm' else 'calls'][0]
                for key in row:
                    bad = copy.deepcopy(receipt)
                    changed = bad if scope == 'receipt' else bad['arms' if scope == 'arm' else 'calls'][0]
                    changed[key] = {'provider_envelope': CANARY}
                    with self.subTest(scope=scope, key=key), self.assertRaises((ValueError, TypeError)):
                        live.export(bad, package, grant, IDENTITY)

    def test_known_rejected_return_retains_real_usage_and_unknown_has_no_zero_estimate(self):
        class Rejected(TestTransport):
            def create(self, **request):
                value = super().create(**request); value['choices'][0]['finish_reason'] = 'length'
                return value
        value = self.chain(transport=Rejected())
        call = value[2]['calls'][0]
        self.assertEqual(call['status'], 'RETURNED_REJECTED')
        self.assertEqual(call['invocation_status'], 'RESPONSE_RETURNED_REJECTED')
        self.assertEqual(call['failure_code'], 'INCOMPLETE_ANSWER_NO_RETRY')
        self.assertEqual(value[4]['provider_calls'], 1); self.assertTrue(value[4]['usage_complete'])
        self.assertEqual(value[4]['usage_rated_cny'], '0.0036')

    def test_reserved_before_dispatch_keeps_full_hold_and_known_zero_calls(self):
        package = package_fixture(); grant = grant_fixture(package)
        with tempfile.TemporaryDirectory() as directory, patch.object(live.LivePackage, 'verify', return_value=None):
            ledger = live.Ledger(Path(directory)/'private', package, 1, lambda: NOW, __import__('time').monotonic,
                identity=IDENTITY, admission_hashes=dict(grant_sha256=r.digest(grant),
                    launch_sha256='1'*64, price_sha256='2'*64, account_sha256='3'*64))
            arm = package.cases[0]['case_id']+':HCL'; ledger.active = arm
            port = ledger.make_port(TestTransport(), arm)
            port.reservation_usd('planning', r.messages(package.cases[0], 'HCL'))
            ledger.arm(arm)['status'] = 'UNKNOWN_FAILURE_STOP'; ledger.stopped = True; ledger.close()
            value = live.export(ledger.value, package, grant, IDENTITY)
            self.assertEqual(value['provider_calls'], 0); self.assertTrue(value['usage_complete'])
            self.assertEqual(value['usage_rated_cny'], '0')
            self.assertEqual(value['reserved_cny'], '1.109664')

    def test_final_native_or_source_tamper_stops_before_second_hold(self):
        actual = universal_entry._share_identical_native_reader_contexts
        for target in ('source', 'native_policy'):
            def altered(payload):
                payload = actual(payload)
                if target == 'source': payload['sources'][0]['version'] += 1
                else: payload['hcl_operations'][0]['preparation_policy'] = 'UNTRUSTED_TEST_POLICY'
                return payload
            with self.subTest(target=target):
                result = self.chain(context=patch.object(universal_entry, '_share_identical_native_reader_contexts', altered))
                self.assertEqual(len(result[6].calls), 1)
                self.assertEqual(len(result[2]['calls']), 1)
                self.assertEqual(result[2]['reserved_cny'], '1.109664')
                self.assertNotIn('UNTRUSTED_TEST_POLICY', json.dumps(result[5]))

    def test_last_worker_margin_check_refuses_before_dispatch_retaining_hold(self):
        actual = live.Ledger.require_final_dispatch_margin
        def margin(ledger):
            if threading.current_thread() is not threading.main_thread():
                raise ValueError('FINAL_STAGE_SEND_MARGIN_INVALID')
            return actual(ledger)
        value = self.chain(context=patch.object(live.Ledger, 'require_final_dispatch_margin', margin))
        self.assertEqual(value[6].calls, [])
        self.assertEqual(value[2]['reserved_cny'], '1.109664')
        self.assertFalse(value[2]['calls'][0]['provider_call'])
        self.assertEqual(value[2]['calls'][0]['invocation_status'], 'NOT_INVOKED')
        self.assertEqual(value[2]['calls'][0]['failure_code'], 'FINAL_DISPATCH_MARGIN_REJECTED_NO_CALL')

    def test_stage_margin_and_late_return_cannot_reopen_or_refund(self):
        package = package_fixture(); elapsed = [0]
        with tempfile.TemporaryDirectory() as directory, patch.object(live.LivePackage, 'verify', return_value=None):
            ledger = live.Ledger(Path(directory)/'private', package, 1, lambda: NOW, lambda: elapsed[0],
                identity=IDENTITY, admission_hashes={})
            elapsed[0] = 420
            with self.assertRaisesRegex(ValueError, 'FINAL_STAGE_SEND_MARGIN'): ledger.admit()
        started, released, finished = threading.Event(), threading.Event(), threading.Event()
        class Late(TestTransport):
            def create(self, **request):
                started.set(); released.wait(timeout=2)
                value = super().create(**request); finished.set(); return value
        transport = Late(); actual = live.Ledger.make_port
        def port(ledger, client, arm):
            value = actual(ledger, client, arm); value.maximum_wait_seconds = 0.01; return value
        try:
            value = self.chain(transport=transport, context=patch.object(live.Ledger, 'make_port', port))
            before = copy.deepcopy(value[2]); released.set(); self.assertTrue(finished.wait(timeout=2))
            self.assertTrue(started.is_set()); self.assertEqual(value[2], before)
            self.assertEqual(value[2]['status'], 'STOPPED_NO_RETRY')
            self.assertEqual(value[2]['reserved_cny'], '1.109664')
            self.assertEqual(len(transport.calls), 1)
        finally: released.set()


class AdmissionAndExportTests(unittest.TestCase):
    def fixture_files(self, root, temporary):
        package = package_fixture(); package = live.LivePackage(package.value, package.packet, Path(root))
        grant = grant_fixture(package); launch = launch_fixture(package, grant); price, account = prechecks_fixture()
        locations = live.paths(root, 1, temporary)
        for key, value in [('package', package.value), ('cases', package.packet), ('grant', grant),
            ('marker', launch['marker']), ('history', launch['pages']), ('price', price),
            ('presence', dict(IDENTITY, existing_provider_secret='PRESENT'))]: r.save(locations[key], value)
        old_account = {key: value for key, value in account.items() if key != 'existing_account_only'}
        old_account['schema'] = 'hcl-two-stage-account-readiness-v1'; r.save(locations['account'], old_account)
        r.save(locations['admission'], live.admission_value(package, grant, IDENTITY, launch, price, account))
        return package, grant, launch, price, account, locations

    @staticmethod
    def git_reader(root, args):
        if args[0] == 'rev-list': return 'a'*40 + ' ' + 'b'*40
        if args[0] == 'diff-tree': return str(live.MARKER_PATH)
        if args[0] == 'diff': return str(live.GRANT_PATH)
        if args[:2] == ['merge-base', '--is-ancestor']: return ''
        raise AssertionError('READ_ONLY_GIT_ONLY')

    def test_execute_factory_only_after_guard_and_consumption_no_second_launch(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temporary:
            package, grant, launch, price, account, locations = self.fixture_files(root, Path(temporary))
            transport = TestTransport(('not JSON',)); constructed = []
            def factory():
                self.assertTrue(locations['consumed'].exists()); self.assertTrue((locations['directory']/'receipt.json').exists())
                constructed.append(True); return transport
            with patch.object(live.LivePackage, 'verify', return_value=None), patch.object(live, 'read_only_reader_pins'), patch.object(live, 'normalized_prechecks', return_value=(price, account)):
                receipt = live.execute_admitted(root, 1, environment(), temporary_root=Path(temporary),
                    git_reader=self.git_reader, client_factory=factory, clock=lambda: NOW)
                self.assertEqual(receipt['status'], 'STOPPED_NO_RETRY')
                with self.assertRaises(ValueError):
                    live.execute_admitted(root, 1, environment(), temporary_root=Path(temporary),
                        git_reader=self.git_reader, client_factory=factory, clock=lambda: NOW)
            self.assertEqual(constructed, [True]); self.assertEqual(len(transport.calls), 1)

    def test_bad_grant_permission_history_or_admission_never_reaches_sdk(self):
        for mutate in ('grant', 'permission', 'history', 'admission', 'consumed'):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temporary:
                package, grant, launch, price, account, locations = self.fixture_files(root, Path(temporary))
                if mutate == 'grant': grant['authorization_ref'] = ref.AUTH; r.save(locations['grant'], grant)
                elif mutate == 'permission': grant['public_native_evidence_permission'] = None; r.save(locations['grant'], grant)
                elif mutate == 'history': r.save(locations['history'], [])
                elif mutate == 'admission': r.save(locations['admission'], {})
                else: live.exclusive_json(locations['consumed'], {'FIXTURE_ALREADY_CONSUMED': True})
                with patch.object(live.LivePackage, 'verify', return_value=None), patch.object(live, 'read_only_reader_pins'), patch.object(live, 'normalized_prechecks', return_value=(price, account)), patch.object(live, '_make_existing_client') as factory:
                    with self.assertRaises((ValueError, FileExistsError)):
                        live.execute_admitted(root, 1, environment(), temporary_root=Path(temporary), git_reader=self.git_reader, clock=lambda: NOW)
                    factory.assert_not_called()

    def test_factory_failure_closes_zero_call_receipt_and_never_retries(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temporary:
            package, grant, launch, price, account, locations = self.fixture_files(root, Path(temporary))
            with patch.object(live.LivePackage, 'verify', return_value=None), patch.object(live, 'read_only_reader_pins'), patch.object(live, 'normalized_prechecks', return_value=(price, account)):
                with self.assertRaisesRegex(RuntimeError, CANARY):
                    live.execute_admitted(root, 1, environment(), temporary_root=Path(temporary), git_reader=self.git_reader,
                        client_factory=lambda: (_ for _ in ()).throw(RuntimeError(CANARY)), clock=lambda: NOW)
                receipt = live.load_json(locations['directory']/'receipt.json')
                self.assertEqual(receipt['calls'], []); self.assertEqual(receipt['status'], 'STOPPED_NO_RETRY')
                self.assertNotIn(CANARY, json.dumps(receipt))
                artifact = live.export_terminal(root, 1, environment())
                self.assertEqual(artifact['original_receipt']['remaining_authorized_calls'], 0)

    def test_ordinary_diagnostic_written_before_bad_native_capture(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temporary:
            package, grant, launch, price, account, locations = self.fixture_files(root, Path(temporary))
            with patch.object(live.LivePackage, 'verify', return_value=None), patch.object(live, 'read_only_reader_pins'), patch.object(live, 'normalized_prechecks', return_value=(price, account)):
                live.execute_admitted(root, 1, environment(), temporary_root=Path(temporary), git_reader=self.git_reader,
                    client_factory=lambda: TestTransport(('not JSON',)), clock=lambda: NOW)
                native_path = locations['directory']/'native-review-private.json'
                native_path.write_text('{'+CANARY)
                original_load = live.load_json
                def read(path, maximum=2*1024*1024):
                    if Path(path) == native_path:
                        ordinary = original_load(locations['public'])
                        self.assertEqual(ordinary['original_receipt']['arms'][0]['orchestration_failure']['code'], 'INVALID_PLANNING_JSON')
                    return original_load(path, maximum)
                with patch.object(live, 'load_json', read): artifact = live.export_terminal(root, 1, environment())
                self.assertEqual(artifact['native_publication_status'], 'NATIVE_EXPORT_REJECTED_GATE_CLOSED')
                self.assertNotIn(CANARY, locations['public'].read_text())

    def test_corrupt_or_unexpected_private_ordinary_data_yields_unknown_closed_fallback(self):
        for corruption in ('malformed_json', 'top_level_private', 'nested_private', 'invalid_identity',
                           'orphan_cost', 'unknown_send_false', 'duplicate_top', 'duplicate_nested', 'nonfinite'):
            with self.subTest(corruption=corruption), tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temporary:
                package, grant, launch, price, account, locations = self.fixture_files(root, Path(temporary))
                with patch.object(live.LivePackage, 'verify', return_value=None), patch.object(live, 'read_only_reader_pins'), patch.object(live, 'normalized_prechecks', return_value=(price, account)):
                    live.execute_admitted(root, 1, environment(), temporary_root=Path(temporary), git_reader=self.git_reader,
                        client_factory=lambda: TestTransport(('not JSON',)), clock=lambda: NOW)
                    path = locations['directory']/'receipt.json'; receipt = live.load_json(path)
                    if corruption == 'malformed_json': path.write_text('{'+CANARY)
                    elif corruption == 'duplicate_top': path.write_text(json.dumps(receipt)[:-1]+',"status":"'+CANARY+'"}')
                    elif corruption == 'duplicate_nested': path.write_text(json.dumps(receipt).replace('"prompt_tokens": 100', '"prompt_tokens": 100, "prompt_tokens": 101'))
                    elif corruption == 'nonfinite': path.write_text(json.dumps(receipt).replace('"prompt_tokens": 100', '"prompt_tokens": NaN'))
                    else:
                        if corruption == 'top_level_private': receipt['raw_plan'] = CANARY
                        elif corruption == 'nested_private': receipt['calls'][0]['response_metadata']['reasoning_content'] = CANARY
                        elif corruption in ('orphan_cost', 'unknown_send_false'):
                            call = receipt['calls'][0]
                            for key in ('usage', 'usage_rated_cny', 'usage_rated_usd'): call.pop(key)
                            call.update(status='FAILED_OR_UNKNOWN', invocation_status='INVOKED_OR_SEND_UNKNOWN',
                                        failure_code='UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP')
                            if corruption == 'orphan_cost': call['usage_rated_cny'] = {'provider_envelope': CANARY}
                            else: call['provider_call'] = False
                        else: receipt['identity']['run_id'] = '99'
                        r.save(path, receipt)
                    before = path.read_bytes(); artifact = live.export_terminal(root, 1, environment())
                    self.assertEqual(path.read_bytes(), before)
                    self.assertEqual(artifact['status'], 'RECEIPT_INTEGRITY_UNAVAILABLE_NO_RESUME')
                    self.assertEqual(artifact['remaining_authorized_calls'], 0)
                    self.assertEqual(artifact['remaining_authorized_cny'], '0')
                    self.assertFalse(artifact['usage_complete'])
                    for key in ('reserved_cny', 'provider_calls', 'usage_rated_cny', 'invoice_cost_cny', 'approved_native_evidence'):
                        self.assertIsNone(artifact[key])
                    self.assertNotIn(CANARY, locations['public'].read_text())
                    self.assertNotIn('original_receipt', artifact)

    def test_duplicate_or_nonfinite_grant_refuses_before_sdk(self):
        for malformed in ('duplicate_top', 'duplicate_nested', 'NaN', 'Infinity', '-Infinity'):
            with self.subTest(malformed=malformed), tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temporary:
                package, grant, launch, price, account, locations = self.fixture_files(root, Path(temporary))
                raw = json.dumps(grant)
                if malformed == 'duplicate_top': raw = raw[:-1]+',"authorized_calls":2}'
                elif malformed == 'duplicate_nested': raw = raw.replace('"maximum_final_texts": 1', '"maximum_final_texts": 1, "maximum_final_texts": 1')
                else: raw = raw.replace('"authorized_calls": 2', '"authorized_calls": '+malformed)
                locations['grant'].write_text(raw)
                with patch.object(live.LivePackage, 'verify', return_value=None), patch.object(live, 'read_only_reader_pins'), patch.object(live, '_make_existing_client') as factory:
                    with self.assertRaises(ValueError):
                        live.execute_admitted(root, 1, environment(), temporary_root=Path(temporary), git_reader=self.git_reader, clock=lambda: NOW)
                    factory.assert_not_called()
                    self.assertFalse(locations['directory'].exists())

    def test_interrupted_known_receipt_preserves_holds_and_reports_without_resuming(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as temporary:
            package, grant, launch, price, account, locations = self.fixture_files(root, Path(temporary))
            with patch.object(live.LivePackage, 'verify', return_value=None), patch.object(live, 'read_only_reader_pins'), patch.object(live, 'normalized_prechecks', return_value=(price, account)):
                transport = TestTransport(('not JSON',))
                live.execute_admitted(root, 1, environment(), temporary_root=Path(temporary), git_reader=self.git_reader,
                    client_factory=lambda: transport, clock=lambda: NOW)
                path = locations['directory']/'receipt.json'; receipt = live.load_json(path)
                receipt['status'] = 'RUNNING'
                for key in ('finished_at', 'elapsed_seconds', 'budget_state', 'remaining_authorized_calls', 'remaining_authorized_cny'):
                    receipt.pop(key)
                r.save(path, receipt)
                artifact = live.export_terminal(root, 1, environment())
                closed = artifact['original_receipt']
                self.assertEqual(closed['status'], 'STOPPED_NO_RETRY')
                self.assertTrue(closed['process_interrupted']); self.assertIsNone(closed['elapsed_seconds'])
                self.assertEqual(closed['reserved_cny'], '1.109664')
                self.assertEqual(closed['arms'][0]['orchestration_failure'], receipt['arms'][0]['orchestration_failure'])
                self.assertEqual(len(transport.calls), 1)
                self.assertEqual(live.export_terminal(root, 1, environment()), artifact)


if __name__ == '__main__': unittest.main()
