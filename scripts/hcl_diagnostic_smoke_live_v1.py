"""Load-only adapter for the separately approved Oct 8 diagnostic smoke.

Preparation/imports never inspect credentials or construct a provider SDK. The
only execution entry requires the new frozen package, new grant, first main push,
complete workflow history, fresh same-run prechecks and a durable consumed file.
Archived modules supply bounded mechanisms, never their old authority or CLI.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import importlib
import json
import os
from pathlib import Path
import subprocess
import time

from scripts import hcl_offline_diagnostic_export_v1 as r
from scripts import hcl_offline_diagnostic_public_v1 as p
from scripts.hcl_offline_diagnostic_reference import _reference as ref, _native as native, PINS

AUTH = 'HCL_DIAGNOSTIC_SMOKE_20261008_1'
APPROVED = '2026-10-08T12:30:14Z'
APPROVAL_MESSAGE_ID = 'Sentinel_5c7e13ffe0688191a2ba34b2791f2e65'
MODE = 'LIVE_EXISTING_ACCOUNT'
PREFIX = 'hcl-diagnostic-smoke'
PACKAGE_SCHEMA = PREFIX + '-final-package-v1'
RECEIPT_SCHEMA = PREFIX + '-private-receipt-v1'
PUBLIC_SCHEMA = PREFIX + '-public-evidence-v1'
ARTIFACT_SCHEMA = PREFIX + '-public-artifact-v1'
REVIEW_SCHEMA = PREFIX + '-source-review-v1'
NATIVE_SCHEMA = PREFIX + '-native-evidence-v1'
REPOSITORY = 'haohongfei2001-png/human-cognition-layer'
DESTINATION = 'https://github.com/' + REPOSITORY
FROZEN = Path('.github/frozen/hcl-diagnostic-smoke-20261008')
PACKAGE_PATH = FROZEN / 'package.json'
CASE_PATH = Path('.github/frozen/hcl-entry-contract-smoke-20261008/cases.json')
CASE_REVIEW = FROZEN / 'reviews/case-review.json'
EXECUTOR_REVIEW = FROZEN / 'reviews/executor-review.json'
GRANT_PATH = Path('.github/' + AUTH + '_GRANT.json')
MARKER_PATH = Path('.github/' + AUTH + '_TRIGGER.json')
WORKFLOW_PATH = Path('.github/workflows/hcl-diagnostic-smoke-20261008-1-once.yml')
RUNTIME_SHA256 = 'f5d155b9a8f8efd8e94143ff622d955028f5b83f43a6f1e76c7e2fa033d06940'
RUNTIME_COMMIT = '226aae8e74bdfbfd7c398188c7154f2995994e7a'
CASE_RAW_SHA256 = '5f89c5de74111a3ae9a396ebc194c393684f851bb73ec2e42a42d2a48cc18409'
PACKET_SHA256 = 'fa39ec373700214c1280ea5413fa46cbfe006641d02a8a094757b87f05507e2f'
PLANNING_SHA256 = '955c24a417e291e447d7723e1174945c13b1aa5a0038eaadf0aaa0e0c8bdae00'
READER_PINS = {
    'scripts/two_stage_price.py': '32c9747dc3411f4d090517f07fc60a524d327f9aecc49b5cf0a10dfcd50451b0',
    'scripts/two_stage_account.py': '18bbb9085a3a0789115d2065d7aa498e485a547b477ada40aecdd4a67d58582b',
}
IMPLEMENTATION_FILES = (
    'scripts/hcl_diagnostic_smoke_live_v1.py',
    'scripts/hcl_offline_diagnostic_export_v1.py',
    'scripts/hcl_offline_diagnostic_public_v1.py',
    'scripts/hcl_offline_diagnostic_reference.py',
    'scripts/hcl_offline_diagnostic_preflight_v1.py',
    'scripts/hcl_offline_diagnostic_preflight_v1.json',
    'tests/test_hcl_diagnostic_smoke_live_v1.py',
    'tests/test_hcl_diagnostic_shared_core.py',
    'tests/test_hcl_offline_diagnostic_export_v1.py',
    'tests/test_hcl_offline_diagnostic_preflight_v1.py',
)
CASE_CHECKS = {'source_rubric_passed', 'native_admissibility_passed', 'native_capacity_passed',
               'unchanged_public_regression_exposure_declared', 'diagnostic_no_efficacy_claim'}
EXECUTOR_CHECKS = {'all_blockers_resolved', 'provider_free_regressions_passed',
                   'native_permission_required_before_external_work', 'original_receipt_and_capture_bound'}


def utcnow():
    return datetime.now(timezone.utc)


def require_time(now):
    if not isinstance(now, datetime) or now.tzinfo is None or now < ref.timestamp(APPROVED):
        raise ValueError('NEW_DIAGNOSTIC_APPROVAL_TIME_REQUIRED')


def load_json(path, maximum=2 * 1024 * 1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise ValueError('BOUNDED_REGULAR_JSON_FILE_REQUIRED')
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError('BOUNDED_REGULAR_JSON_FILE_REQUIRED')
    def unique_object(pairs):
        value = {}
        for key, child in pairs:
            if key in value:
                raise ValueError('DUPLICATE_JSON_KEY_REFUSED')
            value[key] = child
        return value
    def reject_constant(_value):
        raise ValueError('NONFINITE_JSON_CONSTANT_REFUSED')
    value = json.loads(raw, object_pairs_hook=unique_object, parse_constant=reject_constant)
    r.require_plain_json(value)
    return value


def hashed_json(root, relative, expected):
    path = Path(root) / relative
    if not path.resolve().is_relative_to(Path(root).resolve()) or r.file_sha(path) != r.exact_sha(expected):
        raise ValueError('EXACT_REVIEW_OR_CASE_FILE_BYTES_REQUIRED')
    return load_json(path)


def build_configuration(packet, root):
    """Pure current request/control snapshot, with no archived grant identity."""
    value = r.OfflinePackage.build(packet, root).value
    excluded = {'schema', 'mode', 'authorization_ref', 'live_execution_authorized',
                'actual_spend_cny', 'implementation_files', 'reference_helper_files'}
    result = {key: val for key, val in value.items() if key not in excluded}
    result.update(authorization_ref=AUTH, approved_at_bound=APPROVED, expires_at=None,
                  currency='CNY', usd_reference_only=True, openai_sdk_version='2.14.0',
                  z3_solver_version='4.15.4.0', planning_completion_includes_reasoning=True,
                  public_native_maximum_case_records=1, public_native_maximum_operations_per_record=3,
                  public_native_maximum_record_bytes=1048576, reference_helper_files=dict(PINS))
    return result


def case_review_targets(value):
    return dict({key: value[key] for key in ('case_raw_file_sha256', 'packet_sha256', 'runtime_sha256', 'runtime_commit')},
                configuration_sha256=r.digest(value['configuration']),
                implementation_files=value['implementation_files'])


def executor_review_targets(value):
    return dict(case_review_targets(value), configuration_sha256=r.digest(value['configuration']),
                implementation_files=value['implementation_files'], workflow_files=value['workflow_files'],
                read_only_reader_files=value['read_only_reader_files'],
                case_review_file_sha256=value['independent_case_review_sha256'])


def _checks(value, keys):
    return type(value) is dict and set(value) == keys and all(item is True for item in value.values())


def verify_review_artifacts(package):
    value = package.value
    case = hashed_json(package.runtime_root, CASE_REVIEW, value['independent_case_review_sha256'])
    expected = dict(schema=PREFIX + '-independent-case-review-v1', authorization_ref=AUTH,
        verdict='PASS_FOR_BOUNDED_DEVELOPMENT_ONLY',
        reviewer_role='INDEPENDENT_REGRESSION_CASE_REVIEW_BEFORE_DIAGNOSTIC_SMOKE_OUTPUT',
        targets=case_review_targets(value), checks={key: True for key in CASE_CHECKS},
        provider_calls=0, live_execution_authorized=False, efficacy_claimed=False)
    if r.canonical(case) != r.canonical(expected) or type(case.get('provider_calls')) is not int or not _checks(case.get('checks'), CASE_CHECKS):
        raise ValueError('PASSING_TARGET_BOUND_INDEPENDENT_CASE_REVIEW_REQUIRED')
    review = hashed_json(package.runtime_root, EXECUTOR_REVIEW, value['independent_executor_review_sha256'])
    verification = review.get('verification')
    expected = dict(schema=PREFIX + '-independent-executor-approval-v1', authorization_ref=AUTH,
        verdict='PASS_FOR_BOUNDED_EXECUTOR_PACKAGE', reviewer_role='INDEPENDENT_READ_ONLY_SECURITY_REVIEW',
        targets=executor_review_targets(value), checks={key: True for key in EXECUTOR_CHECKS},
        verification=verification, live_execution_authorized=False)
    keys = {'provider_calls', 'account_queries', 'credentials_read', 'sdk_constructed', 'provider_free_tests_passed'}
    if r.canonical(review) != r.canonical(expected) or not _checks(review.get('checks'), EXECUTOR_CHECKS) or type(verification) is not dict or set(verification) != keys or any(type(verification[k]) is not int or verification[k] != 0 for k in ('provider_calls', 'account_queries')) or verification['credentials_read'] is not False or verification['sdk_constructed'] is not False or type(verification['provider_free_tests_passed']) is not int or verification['provider_free_tests_passed'] < 1:
        raise ValueError('PASSING_TARGET_BOUND_INDEPENDENT_EXECUTOR_REVIEW_REQUIRED')
    return case, review


class LivePackage(ref.FrozenPackage):
    """The subclass is only for the archived configuration reader's dispatch.

    All verification is new and code-owned. The archived exact-type grant gate
    rejects this type; no inherited grant, launch, run, or CLI is invoked.
    """
    def verify(self):
        value = self.value
        r.require_plain_json(value); r.require_plain_json(self.packet)
        required = {'schema', 'status', 'authorization_ref', 'approval_message_id', 'approved_at_bound',
                    'currency', 'packet_sha256', 'case_raw_file_sha256', 'runtime_sha256', 'runtime_commit',
                    'configuration', 'implementation_files', 'workflow_files', 'read_only_reader_files',
                    'independent_case_review_sha256', 'independent_executor_review_sha256'}
        if type(value) is not dict or set(value) != required or value['schema'] != PACKAGE_SCHEMA or value['status'] != 'FROZEN_BEFORE_THIS_DIAGNOSTIC_SMOKE_OUTPUT' or value['authorization_ref'] != AUTH or value['approval_message_id'] != APPROVAL_MESSAGE_ID or value['approved_at_bound'] != APPROVED or value['currency'] != 'CNY':
            raise ValueError('EXACT_NEW_DIAGNOSTIC_PACKAGE_REQUIRED')
        if value['runtime_sha256'] != RUNTIME_SHA256 or value['runtime_commit'] != RUNTIME_COMMIT or value['case_raw_file_sha256'] != CASE_RAW_SHA256 or value['packet_sha256'] != PACKET_SHA256 or r.digest(self.packet) != PACKET_SHA256:
            raise ValueError('EXACT_ORIGINAL_CASE_AND_CURRENT_RUNTIME_REQUIRED')
        if hashed_json(self.runtime_root, CASE_PATH, CASE_RAW_SHA256) != self.packet:
            raise ValueError('EXACT_ORIGINAL_CASE_BYTES_REQUIRED')
        configuration = build_configuration(self.packet, self.runtime_root)
        if r.canonical(value['configuration']) != r.canonical(configuration) or configuration['runtime_sha256'] != RUNTIME_SHA256:
            raise ValueError('FINAL_DIAGNOSTIC_CONFIGURATION_OR_RUNTIME_DRIFT')
        planning = configuration['requests'][self.cases[0]['case_id'] + ':HCL:planning']
        if planning['full_request_utf8_bytes'] != 28333 or planning['full_request_sha256'] != PLANNING_SHA256:
            raise ValueError('EXACT_CURRENT_PLANNING_REQUEST_REQUIRED')
        for field, names in (('implementation_files', IMPLEMENTATION_FILES),
                             ('workflow_files', (str(WORKFLOW_PATH),)),
                             ('read_only_reader_files', tuple(READER_PINS))):
            files = value[field]
            if type(files) is not dict or set(files) != set(names) or any(r.file_sha(Path(self.runtime_root) / name) != r.exact_sha(sha) for name, sha in files.items()):
                raise ValueError('EXACT_NEW_DIAGNOSTIC_FILE_PINS_REQUIRED')
        if value['read_only_reader_files'] != READER_PINS:
            raise ValueError('EXACT_ARCHIVED_READ_ONLY_READER_PINS_REQUIRED')
        helper_root = Path(self.runtime_root) / CASE_PATH.parent / 'executor'
        if any(r.file_sha(helper_root / name) != sha for name, sha in PINS.items()):
            raise ValueError('EXACT_ARCHIVED_MECHANISM_PINS_REQUIRED')
        verify_review_artifacts(self)


def require_package(package):
    if type(package) is not LivePackage:
        raise ValueError('EXACT_NEW_LIVE_DIAGNOSTIC_PACKAGE_REQUIRED')
    package.verify()


def validate_permission(permission, packet_sha256):
    expected = dict(schema=PREFIX + '-public-permission-v1', authorization_ref=AUTH,
        approval_message_id=APPROVAL_MESSAGE_ID, approved_at_bound=APPROVED, destination=DESTINATION,
        packet_sha256=packet_sha256, maximum_final_texts=1, maximum_native_records=1,
        maximum_operations_per_record=3, maximum_native_record_bytes=1048576,
        safe_error_codes_and_stages=True, budget_and_closing_records=True,
        source_validated_native_arguments_and_results=True, full_planner_response=False,
        hidden_reasoning=False, private_sources=False, credentials=False)
    r.require_plain_json(permission)
    if permission != expected or packet_sha256 != PACKET_SHA256 or any(type(permission[k]) is not type(v) for k, v in expected.items()):
        raise ValueError('EXACT_NEW_BOUNDED_PUBLICATION_PERMISSION_REQUIRED')
    return True


def require_new_grant(package, grant, stage, now):
    require_package(package); require_time(now)
    if type(stage) is not int or stage != 1 or type(grant) is not dict:
        raise ValueError('EXACT_NEW_DIAGNOSTIC_GRANT_REQUIRED')
    r.require_plain_json(grant)
    expected = dict(schema=PREFIX + '-new-grant-v1', status='READY', authorization_ref=AUTH,
        approval_message_id=APPROVAL_MESSAGE_ID, currency='CNY', stage=1,
        package_sha256=r.digest(package.value), approved_at_bound=APPROVED, expires_at=None,
        authorized_calls=2, authorized_cny='2.30', executor_commit=grant.get('executor_commit'),
        public_native_evidence_permission=grant.get('public_native_evidence_permission'),
        retries=0, historical_budget_transfer=False, other_stage_budget_transfer=False)
    if grant != expected or any(type(grant[k]) is not type(v) for k, v in expected.items()):
        raise ValueError('EXACT_NEW_DIAGNOSTIC_GRANT_REQUIRED')
    r.exact_sha(grant['executor_commit'], 40)
    validate_permission(grant['public_native_evidence_permission'], package.value['packet_sha256'])
    return True


def paths(root, stage=1, temporary_root=Path('/tmp')):
    if type(stage) is not int or stage != 1:
        raise ValueError('EXACT_STAGE_ONE_ONLY_REQUIRED')
    root = Path(root).resolve(); prefix = 'hcl-diagnostic-smoke-20261008-1'
    temp = Path(temporary_root) / prefix
    return dict(root=root, package=root / PACKAGE_PATH, cases=root / CASE_PATH,
                grant=root / GRANT_PATH, marker=root / MARKER_PATH, workflow=root / WORKFLOW_PATH,
                temp=temp, price=temp / 'prices.json', account=temp / 'account.json',
                presence=temp / 'secret-presence.json', history=temp / 'runs.json',
                admission=temp / 'admission.json', consumed=temp / 'execution-consumed.json',
                directory=root / (prefix + '-private'), public=root / (prefix + '-public.json'))


def environment_identity(environment, stage=1):
    paths('.', stage)
    if environment.get('GITHUB_REF') != 'refs/heads/main' or environment.get('GITHUB_RUN_ATTEMPT') != '1' or environment.get('GITHUB_EVENT_NAME') != 'push' or environment.get('GITHUB_REPOSITORY') != REPOSITORY or environment.get('GITHUB_WORKFLOW_REF') != f'{REPOSITORY}/{WORKFLOW_PATH}@refs/heads/main':
        raise ValueError('EXACT_TRUSTED_NEW_WORKFLOW_MAIN_FIRST_PUSH_REQUIRED')
    identity = dict(run_id=environment.get('GITHUB_RUN_ID'), head_sha=environment.get('GITHUB_SHA'))
    validate_identity(identity)
    return identity


def validate_identity(identity):
    if type(identity) is not dict or set(identity) != {'run_id', 'head_sha'} or type(identity['run_id']) is not str or not identity['run_id'].isascii() or not identity['run_id'].isdecimal() or int(identity['run_id']) <= 0:
        raise ValueError('EXACT_SAME_RUN_IDENTITY_REQUIRED')
    r.exact_sha(identity['head_sha'], 40)


def validate_launch_proposal(*, run_id, attempt, pages, workflow_id, head_sha, parent_sha,
        event, paths, marker, package_sha256, grant_sha256, stage, executor_commit,
        grant_commit, executor_ancestor_of_grant, grant_changed_paths):
    """New identity only; complete history and E→G→M checks are fail closed."""
    for sha in (head_sha, parent_sha, executor_commit, grant_commit): r.exact_sha(sha, 40)
    r.exact_sha(package_sha256); r.exact_sha(grant_sha256)
    if parent_sha != grant_commit or len({head_sha, executor_commit, grant_commit}) != 3 or executor_ancestor_of_grant is not True or grant_changed_paths != [str(GRANT_PATH)]:
        raise ValueError('EXACT_EXECUTOR_TO_GRANT_ADOPTION_REQUIRED')
    if type(stage) is not int or stage != 1 or type(attempt) is not int or attempt != 1 or event != 'push' or type(run_id) is not int or run_id <= 0 or type(workflow_id) is not int or workflow_id <= 0:
        raise ValueError('EXACT_FIRST_PUSH_REQUIRED')
    if type(pages) is not list or not pages or any(type(page) is not dict or set(page) != {'total_count', 'workflow_runs'} or type(page['total_count']) is not int or type(page['workflow_runs']) is not list for page in pages):
        raise ValueError('COMPLETE_RUN_HISTORY_REQUIRED')
    rows = [row for page in pages for row in page['workflow_runs']]
    if any(type(row) is not dict for row in rows) or len({row.get('id') for row in rows}) != len(rows) or any(page['total_count'] != len(rows) for page in pages) or len(rows) != 1:
        raise ValueError('COMPLETE_SINGLE_USE_RUN_HISTORY_REQUIRED')
    row = rows[0]
    if type(row.get('id')) is not int or row['id'] != run_id or type(row.get('workflow_id')) is not int or row['workflow_id'] != workflow_id or row.get('head_branch') != 'main' or row.get('path') != str(WORKFLOW_PATH) or type(row.get('run_attempt')) is not int or row['run_attempt'] != 1 or row.get('head_sha') != head_sha or row.get('event') != 'push':
        raise ValueError('EXACT_NEW_WORKFLOW_HISTORY_REQUIRED')
    require_time(ref.timestamp(row['created_at']))
    expected = dict(schema=PREFIX + '-marker-proposal-v1', authorization_ref=AUTH, stage=1,
        package_sha256=package_sha256, grant_sha256=grant_sha256,
        executor_commit=executor_commit, grant_commit=grant_commit)
    if paths != [str(MARKER_PATH)] or marker != expected or type(marker.get('stage')) is not int:
        raise ValueError('EXACT_NEW_MARKER_ONLY_LAUNCH_REQUIRED')
    return True


def git_text(root, args):
    result = subprocess.run(['git', '-C', str(root), *args], check=False,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if result.returncode:
        raise ValueError('READ_ONLY_GIT_IDENTITY_CHECK_FAILED')
    return result.stdout.strip()


def read_launch(root, stage, package, grant, identity, environment, history_pages, *, git_reader=git_text):
    ancestry = git_reader(root, ['rev-list', '--parents', '-n', '1', 'HEAD']).split()
    if len(ancestry) != 2 or ancestry[0] != identity['head_sha']:
        raise ValueError('EXACT_SINGLE_PARENT_GRANT_MARKER_COMMIT_REQUIRED')
    executor = grant['executor_commit']; adopted = ancestry[1]
    git_reader(root, ['merge-base', '--is-ancestor', executor, adopted])
    git_reader(root, ['merge-base', '--is-ancestor', package.value['runtime_commit'], executor])
    changed_grant = git_reader(root, ['diff', '--name-only', executor, adopted]).splitlines()
    changed_marker = git_reader(root, ['diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD']).splitlines()
    rows = [row for page in history_pages for row in page.get('workflow_runs', [])] if type(history_pages) is list else []
    current = [row for row in rows if type(row) is dict and row.get('id') == int(identity['run_id'])]
    if len(current) != 1: raise ValueError('EXACT_CURRENT_HISTORY_ROW_REQUIRED')
    launch = dict(run_id=int(identity['run_id']), attempt=1, pages=history_pages,
        workflow_id=current[0].get('workflow_id'), head_sha=identity['head_sha'], parent_sha=adopted,
        event=environment['GITHUB_EVENT_NAME'], paths=changed_marker,
        marker=load_json(paths(root, stage)['marker'], 64000), package_sha256=r.digest(package.value),
        grant_sha256=r.digest(grant), stage=stage, executor_commit=executor, grant_commit=adopted,
        executor_ancestor_of_grant=True, grant_changed_paths=changed_grant)
    validate_launch_proposal(**launch)
    return launch


def validate_readonly_prechecks(price, account, identity, now):
    validate_identity(identity); require_time(now)
    r.require_plain_json(price); r.require_plain_json(account)
    expected_price = {'run_id', 'head_sha', 'url', 'checked_at', 'sha256', 'rates'}
    rates = dict(currency='CNY', input='9.0', output='27.0', model=r.MODEL, version='DeepSeek-V4-Pro-0813')
    if type(price) is not dict or set(price) != expected_price or any(price[k] != v for k, v in identity.items()) or price['url'] != 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing/' or price['rates'] != rates:
        raise ValueError('EXACT_CURRENT_OFFICIAL_PEAK_PRICE_REQUIRED')
    r.exact_sha(price['sha256'])
    expected = dict(schema=PREFIX + '-account-readiness-v1', **identity, checked_at=account.get('checked_at'),
                    currency='CNY', available=True, model_calls=0, account_read_queries=1, existing_account_only=True)
    if account != expected or any(type(account[k]) is not type(v) for k, v in expected.items()):
        raise ValueError('SAME_EXISTING_CNY_ACCOUNT_REQUIRED')
    if any(not timedelta(0) <= now - ref.timestamp(row['checked_at']) <= timedelta(minutes=10) for row in (price, account)):
        raise ValueError('FRESH_SAME_RUN_PRECHECK_REQUIRED')
    return True


def read_only_reader_pins(root):
    if any(r.file_sha(Path(root) / name) != sha for name, sha in READER_PINS.items()):
        raise ValueError('EXACT_READ_ONLY_READER_PINS_REQUIRED')
    return dict(READER_PINS)


def normalized_prechecks(root, stage, identity, now, *, temporary_root=Path('/tmp')):
    locations = paths(root, stage, temporary_root); read_only_reader_pins(root)
    account_module = importlib.import_module('scripts.two_stage_account')
    price_module = importlib.import_module('scripts.two_stage_price')
    for module, name in ((account_module, 'scripts/two_stage_account.py'), (price_module, 'scripts/two_stage_price.py')):
        if Path(module.__file__).resolve() != (Path(root) / name).resolve():
            raise ValueError('IMPORTED_READER_PATH_MUST_MATCH_EXACT_PIN')
    if load_json(locations['presence'], 4096) != dict(identity, existing_provider_secret='PRESENT'):
        raise ValueError('SAME_RUN_EXISTING_SECRET_PRESENCE_REQUIRED')
    price = load_json(locations['price'], 8192); original = load_json(locations['account'], 8192)
    price_module.validate_price_evidence(price, identity, now); account_module.validate(original, identity, now)
    if type(original.get('account_read_queries')) is not int:
        raise ValueError('EXACT_EXISTING_ACCOUNT_READ_COUNT_REQUIRED')
    account = dict(schema=PREFIX + '-account-readiness-v1', **identity, checked_at=original['checked_at'],
                   currency=original['currency'], available=original['available'], model_calls=0,
                   account_read_queries=1, existing_account_only=True)
    validate_readonly_prechecks(price, account, identity, now)
    return price, account


def load_final_inputs(root, stage, environment, now):
    locations = paths(root, stage); identity = environment_identity(environment, stage)
    package = LivePackage(load_json(locations['package']), load_json(locations['cases']), locations['root'])
    require_package(package)
    grant = load_json(locations['grant'], 64000); require_new_grant(package, grant, stage, now)
    read_only_reader_pins(root)
    if locations['directory'].exists(): raise ValueError('EXACT_RUN_DIRECTORY_ALREADY_CONSUMED')
    return package, grant, identity


def admission_value(package, grant, identity, launch, price, account):
    return dict(schema=PREFIX + '-same-run-admission-v1', **identity,
        authorization_ref=AUTH, package_sha256=r.digest(package.value), grant_sha256=r.digest(grant),
        launch_sha256=r.digest(launch), price_sha256=r.digest(price), account_sha256=r.digest(account),
        native_public_permission_sha256=r.digest(grant['public_native_evidence_permission']))


def exclusive_json(path, value):
    path = Path(path); path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(r.canonical(value) + b'\n'); stream.flush(); os.fsync(stream.fileno())
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try: os.fsync(directory_fd)
        finally: os.close(directory_fd)
    except Exception:
        raise ValueError('DURABLE_ONE_USE_FILE_UNCERTAIN_NO_RETRY') from None


class BoundedPort(ref.BoundedPort):
    provider_free = False

    def _validate_client(self):
        if isinstance(self.client, r.FakeClient) or getattr(self.client, 'offline_synthetic', False) is True:
            raise ValueError('OFFLINE_FAKE_CANNOT_ENTER_LIVE_ADAPTER')
        super()._validate_client()


class Ledger(ref.Ledger):
    authorization_ref = AUTH

    def __init__(self, directory, package, stage, clock, monotonic, *, identity, admission_hashes):
        require_package(package); require_time(clock()); validate_identity(identity)
        if type(stage) is not int or stage != 1:
            raise ValueError('EXACT_STAGE_ONE_ONLY_REQUIRED')
        super().__init__(directory, package, stage, clock, monotonic, offline=False,
                         identity=identity, admission_hashes=admission_hashes)

    def persist(self):
        # Dynamic dispatch also applies to the archived constructor's FIRST save.
        self.value.update(schema=RECEIPT_SCHEMA, authorization_ref=AUTH,
                          mode=MODE, live_execution_authorized=True)
        for arm in self.value['arms']:
            arm.setdefault('orchestration_failure', None); arm.setdefault('capture_failure', None)
        super().persist()

    def make_port(self, client, arm_id):
        return BoundedPort(client, self, arm_id)

    def require_final_dispatch_margin(self):
        if self.stopped: raise ValueError('BATCH_STOPPED_NO_RETRY')
        if self.monotonic() - self.started + r.WAIT >= r.ELAPSED[self.stage]:
            raise ValueError('FINAL_STAGE_SEND_MARGIN_INVALID')
        require_time(self.clock())

    def admit(self):
        self.validate_ledger(); self.require_final_dispatch_margin(); require_package(self.package)


def _make_existing_client():
    """Reached only AFTER every new-authority guard and durable consumption."""
    import importlib.metadata
    import logging
    if importlib.metadata.version('openai') != '2.14.0':
        raise ValueError('EXACT_PINNED_SDK_VERSION_REQUIRED')
    if importlib.metadata.version('z3-solver') != '4.15.4.0':
        raise ValueError('EXACT_PINNED_SOLVER_VERSION_REQUIRED')
    logging.disable(logging.CRITICAL); os.environ.pop('OPENAI_LOG', None)
    from openai import OpenAI
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key: raise ValueError('EXISTING_PROVIDER_SECRET_UNAVAILABLE')
    return OpenAI(api_key=key, base_url='https://api.deepseek.com', max_retries=0, timeout=r.WAIT)


def execute_admitted(root, stage, environment, *, now=None, temporary_root=Path('/tmp'),
                     git_reader=git_text, client_factory=None, clock=utcnow, monotonic=time.monotonic):
    now = now or clock(); package, grant, identity = load_final_inputs(root, stage, environment, now)
    locations = paths(root, stage, temporary_root)
    launch = read_launch(root, stage, package, grant, identity, environment,
                         load_json(locations['history']), git_reader=git_reader)
    price, account = normalized_prechecks(root, stage, identity, now, temporary_root=temporary_root)
    expected = admission_value(package, grant, identity, launch, price, account)
    if load_json(locations['admission'], 8192) != expected:
        raise ValueError('EXACT_SAME_RUN_ADMISSION_FILE_REQUIRED')
    exclusive_json(locations['consumed'], expected)
    require_new_grant(package, grant, stage, clock())
    validate_readonly_prechecks(price, account, identity, clock())
    ledger = Ledger(locations['directory'], package, stage, clock, monotonic, identity=identity,
                    admission_hashes={key: expected[key] for key in ('grant_sha256', 'launch_sha256', 'price_sha256', 'account_sha256')})
    try:
        client = (client_factory or _make_existing_client)()
        if isinstance(client, r.FakeClient): raise ValueError('OFFLINE_FAKE_CANNOT_ENTER_LIVE_ADAPTER')
        return r._run_with_ledger(ledger, client)
    except BaseException:
        if ledger.value['status'] == 'RUNNING':
            ledger.stopped = True; ledger.close()
        raise


# The original closed receipt is itself an approved budget/closing record. Its
# complete exact bytes are published only after these CLOSED nested whitelists.
RECEIPT_REQUIRED = {'schema', 'stage', 'mode', 'currency', 'usd_reference_only', 'authorization_ref',
    'package_sha256', 'status', 'calls', 'arms', 'reserved_cny', 'reserved_usd', 'started_at',
    'identity', 'admission_hashes', 'elapsed_seconds', 'budget_state', 'remaining_authorized_calls',
    'remaining_authorized_cny', 'live_execution_authorized'}
ARM_REQUIRED = {'case_id', 'arm', 'status', 'final_text', 'final_fields', 'final_answer_sha256',
    'citations_accepted', 'selected_capabilities', 'executed_capabilities', 'checked_treatment',
    'native_results', 'final_delivery_code', 'request_diagnostics', 'runtime_final_context_metrics',
    'native_review_sha256', 'native_review_available', 'native_projection_sha256',
    'native_projection_status', 'native_integrity_status', 'entry_requirements',
    'full_request_metrics_unavailable_reason', 'orchestration_failure', 'capture_failure'}
CALL_REQUIRED = {'call_id', 'case_id', 'arm', 'phase', 'request_sha256', 'request_bytes',
    'reserved_cny', 'exact_request_reservation_cny', 'reserved_usd', 'exact_request_reservation_usd',
    'status', 'invocation_status', 'provider_call', 'offline_transport_call'}


def _closed_keys(value, required, optional=()):
    if type(value) is not dict or not required <= set(value) or set(value) - required - set(optional):
        raise ValueError('CLOSED_PUBLIC_ORIGINAL_RECEIPT_WHITELIST_REQUIRED')


def _plain_strings(value, keys):
    if any(type(value[key]) is not str for key in keys):
        raise ValueError('EXACT_RECEIPT_STRING_FIELDS_REQUIRED')


def _same_json(original, cleaned):
    if r.canonical(original) != r.canonical(cleaned):
        raise ValueError('EXACT_CLEAN_ORIGINAL_RECEIPT_FIELD_REQUIRED')


def _money(value):
    try:
        return p.money(value)
    except Exception:
        raise ValueError('BOUNDED_FINITE_MONEY_STRING_REQUIRED') from None


def _validate_arm_fields(arm):
    """Validate every value that will remain in the original published arm."""
    _closed_keys(arm, ARM_REQUIRED, {'arm_seconds', 'sdk_seconds', 'non_sdk_seconds'})
    _plain_strings(arm, ('case_id', 'arm', 'status', 'final_delivery_code',
                         'native_projection_status', 'native_integrity_status'))
    if any(type(arm[key]) is not bool for key in ('citations_accepted', 'native_review_available')) or type(arm['native_results']) is not int:
        raise ValueError('EXACT_RECEIPT_ARM_BOOLEAN_AND_COUNT_REQUIRED')
    for key in ('final_answer_sha256', 'native_review_sha256', 'native_projection_sha256'):
        if arm[key] is not None: r.exact_sha(arm[key])
    final = arm['final_text']
    if final is not None and (type(final) is not str or len(final) > 64000):
        raise ValueError('BOUNDED_UNCHANGED_FINAL_REQUIRED')
    _same_json(arm['final_fields'], r.final_fields(final))
    for key in ('selected_capabilities', 'executed_capabilities', 'checked_treatment'):
        if type(arm[key]) is not list or len(arm[key]) > 3 or any(type(item) is not str or item not in r.CATALOG for item in arm[key]):
            raise ValueError('EXACT_BOUNDED_NATIVE_IDENTITIES_REQUIRED')
    diagnostics = arm['request_diagnostics']
    if type(diagnostics) is not list or len(diagnostics) > 2:
        raise ValueError('EXACT_BOUNDED_PHASE_DIAGNOSTICS_REQUIRED')
    for row in diagnostics: _same_json(row, p.clean_metrics(row))
    runtime = arm['runtime_final_context_metrics']
    if type(runtime) is dict and set(runtime) == {'utf8_encoding_available'} and runtime['utf8_encoding_available'] is not False:
        raise ValueError('EXACT_RUNTIME_ENCODING_FLAG_REQUIRED')
    _same_json(runtime, p.clean_runtime_metrics(runtime))
    _same_json(arm['entry_requirements'], p.clean_entry_requirements(arm['entry_requirements']))
    _same_json(arm['orchestration_failure'], p.clean_diagnostic_field(arm))
    _same_json(arm['capture_failure'], p.clean_capture_field(arm))
    reason = arm['full_request_metrics_unavailable_reason']
    if reason is not None and type(reason) is not str:
        raise ValueError('EXACT_REQUEST_METRIC_AVAILABILITY_REQUIRED')
    for key in ('arm_seconds', 'sdk_seconds', 'non_sdk_seconds'):
        if key in arm: p.duration(arm[key])


def _validate_call_fields(call):
    """The exact durable call state cannot disguise an unknown send as zero cost."""
    _closed_keys(call, CALL_REQUIRED, {'response_metadata', 'sdk_seconds', 'failure_code',
                                      'usage', 'usage_rated_cny', 'usage_rated_usd'})
    _plain_strings(call, ('call_id', 'case_id', 'arm', 'phase', 'status', 'invocation_status'))
    if type(call['provider_call']) is not bool or call['offline_transport_call'] is not False:
        raise ValueError('EXACT_LIVE_CALL_TRANSPORT_FLAGS_REQUIRED')
    if type(call['request_bytes']) is not int or not 0 < call['request_bytes'] <= r.MAX_REQUEST_BYTES:
        raise ValueError('ADMITTED_FULL_REQUEST_BOUND_REQUIRED')
    r.exact_sha(call['request_sha256'])
    phase = call['phase']
    if phase not in r.TOKENS: raise ValueError('EXACT_CALL_PHASE_REQUIRED')
    for key in ('reserved_cny', 'exact_request_reservation_cny', 'reserved_usd', 'exact_request_reservation_usd'):
        _money(call[key])
    usage_keys = {'usage', 'usage_rated_cny', 'usage_rated_usd'}
    present = set(call) & usage_keys
    if present not in (set(), usage_keys):
        raise ValueError('COMPLETE_USAGE_AND_BOTH_RATED_AMOUNTS_REQUIRED')
    has_usage = present == usage_keys
    if has_usage:
        counts = call['usage']
        _closed_keys(counts, {'prompt_tokens', 'completion_tokens'})
        if any(type(counts[key]) is not int or counts[key] <= 0 for key in counts) or counts['prompt_tokens'] > 2 * call['request_bytes'] + 2048 or counts['completion_tokens'] > r.TOKENS[phase] + 32:
            raise ValueError('BOUNDED_EXACT_USAGE_COUNTS_REQUIRED')
        for key in ('usage_rated_cny', 'usage_rated_usd'): _money(call[key])
    if 'response_metadata' in call:
        _same_json(call['response_metadata'], p.clean_response_metadata(call['response_metadata'], phase))
    if 'sdk_seconds' in call: p.duration(call['sdk_seconds'])
    failure = call.get('failure_code')
    if 'failure_code' in call and (type(failure) is not str or failure not in p.FAILURES):
        raise ValueError('EXACT_SAFE_CALL_FAILURE_CODE_REQUIRED')
    status = call['status']; invoked = call['invocation_status']; provider = call['provider_call']
    metadata = 'response_metadata' in call
    if status == 'RESERVED_BEFORE_CALL':
        valid = invoked == 'NOT_INVOKED' and not provider and not has_usage and not metadata and 'failure_code' not in call
    elif status == 'RETURNED':
        valid = invoked == 'RETURNED' and provider and has_usage and metadata and 'failure_code' not in call
    elif status == 'RETURNED_REJECTED':
        valid = invoked == 'RESPONSE_RETURNED_REJECTED' and provider and has_usage and metadata and failure in ref.KNOWN_RETURN_FAILURES
    elif status == 'FAILED_OR_UNKNOWN' and invoked == 'NOT_INVOKED':
        valid = not provider and not has_usage and not metadata and failure in {
            'FINAL_DISPATCH_MARGIN_REJECTED_NO_CALL', 'UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP'}
    elif status == 'FAILED_OR_UNKNOWN' and invoked == 'INVOKED_OR_SEND_UNKNOWN':
        valid = provider and (not has_usage or metadata) and failure == 'UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP'
    else:
        valid = False
    if not valid:
        raise ValueError('EXACT_CALL_STATUS_INVOCATION_TRANSPORT_USAGE_CONTRACT_REQUIRED')


def validate_original_receipt(receipt, package, grant, identity):
    r.require_plain_json(receipt)
    _closed_keys(receipt, RECEIPT_REQUIRED, {'finished_at', 'process_interrupted'})
    _plain_strings(receipt, ('schema', 'mode', 'currency', 'authorization_ref', 'package_sha256',
        'status', 'reserved_cny', 'reserved_usd', 'started_at', 'budget_state', 'remaining_authorized_cny'))
    if type(receipt['stage']) is not int or type(receipt['remaining_authorized_calls']) is not int or receipt['usd_reference_only'] is not True or receipt['live_execution_authorized'] is not True:
        raise ValueError('EXACT_ORIGINAL_RECEIPT_BOOLEAN_AND_COUNT_REQUIRED')
    if type(receipt['arms']) is not list or len(receipt['arms']) != 1 or type(receipt['calls']) is not list or len(receipt['calls']) > 2:
        raise ValueError('EXACT_ORIGINAL_RECEIPT_ARM_AND_CALL_BOUNDS_REQUIRED')
    for key in ('reserved_cny', 'reserved_usd', 'remaining_authorized_cny'): _money(receipt[key])
    if receipt['elapsed_seconds'] is None:
        if receipt.get('process_interrupted') is not True:
            raise ValueError('NULL_ELAPSED_REQUIRES_EXPLICIT_INTERRUPTION')
    else:
        p.duration(receipt['elapsed_seconds'])
    r.exact_sha(receipt['package_sha256']); validate_identity(receipt['identity'])
    require_new_grant(package, grant, 1, ref.timestamp(receipt['started_at']))
    validate_identity(identity)
    if receipt['identity'] != identity or receipt['live_execution_authorized'] is not True:
        raise ValueError('EXACT_ORIGINAL_LIVE_IDENTITY_REQUIRED')
    admission = receipt['admission_hashes']
    _closed_keys(admission, {'grant_sha256', 'launch_sha256', 'price_sha256', 'account_sha256'})
    for sha in admission.values(): r.exact_sha(sha)
    if admission['grant_sha256'] != r.digest(grant): raise ValueError('EXACT_ORIGINAL_GRANT_HASH_REQUIRED')
    if 'finished_at' in receipt:
        _plain_strings(receipt, ('finished_at',))
        if ref.timestamp(receipt['finished_at']) < ref.timestamp(receipt['started_at']):
            raise ValueError('ORDERED_ORIGINAL_RECEIPT_TIMESTAMPS_REQUIRED')
    elif receipt.get('process_interrupted') is not True:
        raise ValueError('EXACT_ORIGINAL_CLOSING_TIME_REQUIRED')
    if 'process_interrupted' in receipt and receipt['process_interrupted'] is not True:
        raise ValueError('EXACT_INTERRUPTED_RECEIPT_FLAG_REQUIRED')
    for arm in receipt['arms']:
        _validate_arm_fields(arm)
    for call in receipt['calls']:
        _validate_call_fields(call)
        phase = call['phase']
        if phase not in r.HOLD_USD or Decimal(_money(call['reserved_usd'])) != r.HOLD_USD[phase] or Decimal(_money(call['exact_request_reservation_usd'])) != r.quote(call['request_bytes'], phase, currency='USD'):
            raise ValueError('EXACT_REFERENCE_USD_HOLDS_REQUIRED')
        if 'usage_rated_usd' in call:
            usage = call.get('usage', {})
            if set(usage) != {'prompt_tokens', 'completion_tokens'}:
                raise ValueError('EXACT_REFERENCE_USD_USAGE_REQUIRED')
            usd = (Decimal(usage['prompt_tokens']) * ref.INPUT_RATE + Decimal(usage['completion_tokens']) * ref.OUTPUT_RATE) / 1000000
            if Decimal(_money(call['usage_rated_usd'])) != usd:
                raise ValueError('EXACT_REFERENCE_USD_USAGE_REQUIRED')
    if Decimal(_money(receipt['reserved_usd'])) != sum((Decimal(row['reserved_usd']) for row in receipt['calls']), Decimal(0)):
        raise ValueError('EXACT_REFERENCE_USD_TOTAL_REQUIRED')
    # Shared projection now checks the already-typed original fields' semantic
    # relationships, exact request identities, rates, bounds and aggregate sums.
    output = p._export_ordinary(receipt, package, receipt_schema=RECEIPT_SCHEMA,
        public_schema=PUBLIC_SCHEMA, mode=MODE, authorization_ref=AUTH, offline=False)
    output.update(live_execution_authorized=True, cost_basis='USAGE_RATED_PEAK_NOT_INVOICE')
    return output


def export(receipt, package, grant, identity, *, native_bundle=None):
    """Return ordinary evidence; no offline labels or invented zero actual spend."""
    require_package(package)
    output = validate_original_receipt(receipt, package, grant, identity)
    output.update(native_publication_status='NATIVE_UNAVAILABLE_GATE_CLOSED', approved_native_evidence=None)
    if native_bundle is not None:
        validate_permission(grant['public_native_evidence_permission'], package.value['packet_sha256'])
        records = p._validated_native_records(native_bundle, receipt, package)
        # The single public projection must reconstruct ALL original capture.
        for record in records:
            arm = next(arm for arm in receipt['arms'] if arm['case_id'] == record['case_id'])
            if len(record['operations']) != len(arm['selected_capabilities']):
                raise ValueError('COMPLETE_ORIGINAL_CAPTURE_REQUIRED_FOR_PUBLICATION')
        value = dict(schema=NATIVE_SCHEMA, package_sha256=r.digest(package.value),
            packet_sha256=package.value['packet_sha256'], receipt_sha256=r.digest(receipt),
            stage=1, records=records, record_count=len(records), semantic_certification=False,
            live_execution_authorized=True)
        native._bind_published_to_receipt(value, receipt, package)
        output.update(native_publication_status='APPROVED_BOUNDED_NATIVE_EVIDENCE', approved_native_evidence=value)
        p.validate_actual_entry_requirements(output, package)
    return output


def artifact_from_evidence(receipt, evidence):
    """One original final and one native record; no duplicated private bundle."""
    return dict(schema=ARTIFACT_SCHEMA, authorization_ref=AUTH,
                package_sha256=evidence['package_sha256'], original_receipt=receipt,
                native_publication_status=evidence['native_publication_status'],
                approved_native_evidence=evidence['approved_native_evidence'])


def evidence_from_artifact(artifact, package, grant, identity):
    """Validate disclosed integrity; authenticity requires caller-retained originals."""
    require_package(package); r.require_plain_json(artifact)
    _closed_keys(artifact, {'schema', 'authorization_ref', 'package_sha256', 'original_receipt',
                          'native_publication_status', 'approved_native_evidence'})
    if artifact['schema'] != ARTIFACT_SCHEMA or artifact['authorization_ref'] != AUTH or artifact['package_sha256'] != r.digest(package.value):
        raise ValueError('EXACT_NEW_PUBLIC_ARTIFACT_REQUIRED')
    receipt = artifact['original_receipt']; captured = artifact['approved_native_evidence']
    output = export(receipt, package, grant, identity)
    status = artifact['native_publication_status']
    if captured is None:
        if status not in {'NATIVE_UNAVAILABLE_GATE_CLOSED', 'NATIVE_EXPORT_REJECTED_GATE_CLOSED'}:
            raise ValueError('EXACT_NATIVE_PUBLICATION_STATE_REQUIRED')
        output['native_publication_status'] = status
        return output
    expected_keys = {'schema', 'package_sha256', 'packet_sha256', 'receipt_sha256', 'stage',
                     'records', 'record_count', 'semantic_certification', 'live_execution_authorized'}
    if type(captured) is not dict or set(captured) != expected_keys or captured['schema'] != NATIVE_SCHEMA or captured['package_sha256'] != r.digest(package.value) or captured['packet_sha256'] != PACKET_SHA256 or captured['receipt_sha256'] != r.digest(receipt) or type(captured['stage']) is not int or captured['stage'] != 1 or captured['semantic_certification'] is not False or captured['live_execution_authorized'] is not True or status != 'APPROVED_BOUNDED_NATIVE_EVIDENCE':
        raise ValueError('EXACT_LIVE_NATIVE_ENVELOPE_REQUIRED')
    records = captured['records']
    if type(records) is not list or len(records) != 1 or type(captured['record_count']) is not int or captured['record_count'] != 1:
        raise ValueError('EXACT_ONE_NATIVE_RECORD_REQUIRED')
    operations = records[0]['operations']
    if type(operations) is not list or not 0 <= len(operations) <= 3 or len(operations) != len(receipt['arms'][0]['selected_capabilities']):
        raise ValueError('COMPLETE_ORIGINAL_CAPTURE_REQUIRED_FOR_PUBLICATION')
    bundle = dict(schema='hcl-entry-contract-smoke-private-native-review-bundle-v1',
        package_sha256=r.digest(package.value), stage=1, reviews=[ref.private_native_review(package.cases[0],
        dict(plan={'operations': [op['source_validated_arguments'] for op in operations]},
             operations=[op['native_result_and_policy'] for op in operations]))])
    fresh = export(receipt, package, grant, identity, native_bundle=bundle)
    if r.canonical(fresh['approved_native_evidence']) != r.canonical(captured):
        raise ValueError('EXACT_DISCLOSED_ORIGINAL_CAPTURE_REQUIRED')
    return fresh


def validate_review_binding(package, evidence, review):
    require_package(package)
    if evidence.get('live_execution_authorized') is not True or evidence.get('cost_basis') != 'USAGE_RATED_PEAK_NOT_INVOICE' or 'actual_spend_cny' in evidence or 'simulated_usage_rated_cny' in evidence:
        raise ValueError('EXACT_LIVE_ACCOUNTING_ENVELOPE_REQUIRED')
    captured = evidence.get('approved_native_evidence')
    if captured is not None and (type(captured) is not dict or captured.get('live_execution_authorized') is not True or captured.get('semantic_certification') is not False):
        raise ValueError('EXACT_LIVE_NATIVE_ENVELOPE_REQUIRED')
    return p._validate_review_binding(package, evidence, review, public_schema=PUBLIC_SCHEMA,
        review_schema=REVIEW_SCHEMA, native_schema=NATIVE_SCHEMA, mode=MODE, authorization_ref=AUTH)


def validate_phase1_gate(package, artifact, review, *, grant, identity,
                         original_receipt, original_native_bundle):
    """No self-authentication: success always requires separately trusted originals."""
    require_package(package); p._require_original_artifacts(original_receipt, original_native_bundle)
    evidence = evidence_from_artifact(artifact, package, grant, identity)
    if r.canonical(artifact['original_receipt']) != r.canonical(original_receipt):
        raise ValueError('EXACT_TRUSTED_ORIGINAL_RECEIPT_REQUIRED')
    original_export = export(original_receipt, package, grant, identity, native_bundle=original_native_bundle)
    p._validate_original_binding(evidence, original_receipt=original_receipt,
        original_native_bundle=original_native_bundle, original_export=original_export)
    p._validate_success_identity(package, evidence, public_schema=PUBLIC_SCHEMA, mode=MODE,
                                authorization_ref=AUTH, offline=False)
    p._validate_success_native_records(evidence, package)
    validate_review_binding(package, evidence, review)
    return p._validate_success_contents(package, evidence, review, offline=False)


def export_terminal(root, stage, environment, *, now=None):
    locations = paths(root, stage); identity = environment_identity(environment, stage)
    package = LivePackage(load_json(locations['package']), load_json(locations['cases']), locations['root'])
    require_package(package); grant = load_json(locations['grant'], 64000)
    require_new_grant(package, grant, stage, ref.timestamp(APPROVED))
    try:
        original = load_json(locations['directory'] / 'receipt.json')
        receipt = p._close_interrupted_receipt(original, package, receipt_schema=RECEIPT_SCHEMA,
            mode=MODE, authorization_ref=AUTH)
        evidence = export(receipt, package, grant, identity)
    except Exception:
        # Original bytes cannot be authenticated: never copy any of them, infer
        # missing calls/cost/diagnosis, free holds, resume, or declare success.
        artifact = dict(schema=PREFIX + '-public-integrity-unavailable-v1',
            authorization_ref=AUTH, currency='CNY', stage=1, **identity,
            package_sha256=r.digest(package.value), status='RECEIPT_INTEGRITY_UNAVAILABLE_NO_RESUME',
            budget_state='CLOSED_NO_TRANSFER_NO_RETRY', remaining_authorized_calls=0,
            remaining_authorized_cny='0', prior_reservations='ALL_PREEXISTING_FULL_HOLDS_RETAINED_NO_RELEASE',
            reserved_cny=None, provider_calls=None, usage_rated_cny=None, invoice_cost_cny=None,
            usage_complete=False, native_publication_status='RECEIPT_INTEGRITY_UNAVAILABLE_GATE_CLOSED',
            approved_native_evidence=None, final_answers_unavailable=True)
        r.save(locations['public'], artifact)
        return artifact
    if receipt != original: r.save(locations['directory'] / 'receipt.json', receipt)
    # Write checked ordinary diagnostic/closing facts BEFORE touching native data.
    artifact = artifact_from_evidence(receipt, evidence); r.save(locations['public'], artifact)
    native_path = locations['directory'] / 'native-review-private.json'
    if native_path.exists():
        try:
            evidence = export(receipt, package, grant, identity, native_bundle=load_json(native_path))
        except Exception:
            evidence.update(native_publication_status='NATIVE_EXPORT_REJECTED_GATE_CLOSED', approved_native_evidence=None)
        artifact = artifact_from_evidence(receipt, evidence); r.save(locations['public'], artifact)
    return artifact


def main():
    import argparse
    parser = argparse.ArgumentParser(description='New reviewed diagnostic once-only adapter; no creation modes')
    parser.add_argument('--stage', type=int, choices=(1,), required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    for name in ('preflight', 'write-presence', 'check-launch', 'execute', 'export'):
        group.add_argument('--' + name, action='store_true')
    args = parser.parse_args(); os.umask(0o077); root = Path.cwd(); now = utcnow()
    locations = paths(root, args.stage)
    if args.export:
        export_terminal(root, args.stage, os.environ, now=now)
        print('HCL_DIAGNOSTIC_SMOKE_APPROVED_PUBLIC_ARTIFACT_WRITTEN'); return
    package, grant, identity = load_final_inputs(root, args.stage, os.environ, now)
    if args.preflight:
        print('HCL_DIAGNOSTIC_SMOKE_EXACT_PREFLIGHT_PASS_ZERO_PROVIDER_CALLS'); return
    if args.write_presence:
        value = dict(identity, existing_provider_secret='PRESENT' if os.environ.get('SECRET_PRESENT') == 'true' else 'ABSENT')
        exclusive_json(locations['presence'], value)
        if value['existing_provider_secret'] != 'PRESENT': raise ValueError('EXISTING_SECRET_PRESENCE_REQUIRED')
        print('HCL_DIAGNOSTIC_SMOKE_EXISTING_SECRET_PRESENT'); return
    if args.check_launch:
        launch = read_launch(root, args.stage, package, grant, identity, os.environ, load_json(locations['history']))
        price, account = normalized_prechecks(root, args.stage, identity, now)
        exclusive_json(locations['admission'], admission_value(package, grant, identity, launch, price, account))
        print('HCL_DIAGNOSTIC_SMOKE_ONE_USE_LAUNCH_ADMITTED'); return
    execute_admitted(root, args.stage, os.environ)
    print('HCL_DIAGNOSTIC_SMOKE_TERMINATED_NO_RETRY')


if __name__ == '__main__':
    try: main()
    except Exception:
        raise SystemExit('HCL_DIAGNOSTIC_SMOKE_ADAPTER_REFUSED_OR_STOPPED_NO_RETRY') from None
