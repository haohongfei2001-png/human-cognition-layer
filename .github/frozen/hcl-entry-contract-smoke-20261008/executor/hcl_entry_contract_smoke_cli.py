"""Guarded future GitHub Actions adapter. Candidate preparation invokes none of it.

No freeze/grant/trigger creation mode exists. Imports have no external effects.
The --execute branch is reachable only with an existing independently reviewed
final package/new grant/main first push/exact full history/prechecks/permission.
"""
from datetime import datetime, timezone
import importlib
import json
import os
from pathlib import Path
import subprocess

import hcl_entry_contract_smoke_candidate as r
import hcl_entry_contract_smoke_public as public
from hcl_entry_contract_smoke_native_public import validate_permission

REPOSITORY = 'haohongfei2001-png/human-cognition-layer'
FROZEN = Path('.github/frozen/hcl-entry-contract-smoke-20261008')
PACKAGE_PATH = FROZEN / 'package.json'
CASE_PATH = FROZEN / 'cases.json'
EXECUTOR_RELATIVE = FROZEN / 'executor'
# These read-only historical modules are never modified or used as old authority.
READER_PINS = {
    'scripts/two_stage_price.py': '32c9747dc3411f4d090517f07fc60a524d327f9aecc49b5cf0a10dfcd50451b0',
    'scripts/two_stage_account.py': '18bbb9085a3a0789115d2065d7aa498e485a547b477ada40aecdd4a67d58582b',
}
REPAIR_FIELDS = ('runtime_commit', 'source_guard_merge_commit', 'trusted_native_policy_merge_commit', 'pursuit_uncertainty_merge_commit', 'planner_lifecycle_contracts_merge_commit')


def utcnow():
    return datetime.now(timezone.utc)


def paths(root, stage, temporary_root=Path('/tmp')):
    if type(stage) is not int or stage not in (1,): raise ValueError('EXACT_STAGE_REQUIRED')
    root = Path(root).resolve(); prefix = f'hcl-entry-contract-smoke-20261008-{stage}'
    temp = Path(temporary_root) / prefix
    return dict(root=root, package=root / PACKAGE_PATH, cases=root / CASE_PATH,
                grant=root / f'.github/HCL_ENTRY_CONTRACT_SMOKE_20261008_{stage}_GRANT.json',
                marker=root / f'.github/HCL_ENTRY_CONTRACT_SMOKE_20261008_{stage}_TRIGGER.json',
                workflow=root / f'.github/workflows/hcl-entry-contract-smoke-20261008-{stage}-once.yml',
                temp=temp, price=temp / 'prices.json', account=temp / 'account.json',
                presence=temp / 'secret-presence.json', history=temp / 'runs.json',
                admission=temp / 'admission.json', consumed=temp / 'execution-consumed.json',
                directory=root / f'{prefix}-private', public=root / f'{prefix}-public.json',
                phase1_evidence=root / 'reports/HCL_ENTRY_CONTRACT_SMOKE_20261008_1_PUBLIC_EVIDENCE.json',
                phase1_review=root / 'reports/HCL_ENTRY_CONTRACT_SMOKE_20261008_1_SOURCE_REVIEW.json')


def load_json(path, maximum=16 * 1024 * 1024):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= maximum:
        raise ValueError('BOUNDED_REGULAR_JSON_FILE_REQUIRED')
    data = path.read_bytes()
    if len(data) > maximum: raise ValueError('BOUNDED_JSON_REQUIRED')
    return json.loads(data)


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
        # Never delete uncertain admission/consumption evidence or retry it.
        raise ValueError('DURABLE_ONE_USE_FILE_UNCERTAIN_NO_RETRY') from None


def read_only_reader_pins(root):
    root = Path(root).resolve()
    if any(r.file_sha(root / name) != digest for name, digest in READER_PINS.items()):
        raise ValueError('EXACT_READ_ONLY_READER_PINS_REQUIRED')
    return dict(READER_PINS)


def environment_identity(environment, stage):
    expected_workflow = f'{REPOSITORY}/.github/workflows/hcl-entry-contract-smoke-20261008-{stage}-once.yml@refs/heads/main'
    if environment.get('GITHUB_REF') != 'refs/heads/main' or environment.get('GITHUB_RUN_ATTEMPT') != '1' or environment.get('GITHUB_EVENT_NAME') != 'push' or environment.get('GITHUB_REPOSITORY') != REPOSITORY or environment.get('GITHUB_WORKFLOW_REF') != expected_workflow:
        raise ValueError('EXACT_TRUSTED_MAIN_FIRST_PUSH_ENVIRONMENT_REQUIRED')
    run_id = environment.get('GITHUB_RUN_ID'); head = environment.get('GITHUB_SHA')
    if not isinstance(run_id, str) or not run_id.isascii() or not run_id.isdecimal() or int(run_id) <= 0:
        raise ValueError('EXACT_RUN_ID_REQUIRED')
    r.exact_sha(head, 40)
    return dict(run_id=run_id, head_sha=head)


def load_final_inputs(root, stage, environment, now):
    locations = paths(root, stage); identity = environment_identity(environment, stage)
    packet = load_json(locations['cases']); package = r.FrozenPackage(load_json(locations['package']), packet, locations['root'])
    package.verify(); grant = load_json(locations['grant'], 64000)
    r.require_new_grant(package, grant, stage, now)
    read_only_reader_pins(root)
    # This Actions path cannot keep a public repository artifact private.
    # Do not spend the smoke budget while its review route is known unavailable.
    validate_permission(grant.get('public_native_evidence_permission'), package.value['packet_sha256'])
    if paths(root, stage)['directory'].exists(): raise ValueError('EXACT_RUN_DIRECTORY_ALREADY_CONSUMED')
    return package, grant, identity


def git_text(root, args):
    result = subprocess.run(['git', '-C', str(root), *args], check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if result.returncode != 0: raise ValueError('READ_ONLY_GIT_IDENTITY_CHECK_FAILED')
    return result.stdout.strip()


def read_launch(root, stage, package, grant, identity, environment, history_pages, *, git_reader=git_text):
    ancestry = git_reader(root, ['rev-list', '--parents', '-n', '1', 'HEAD']).split()
    if len(ancestry) != 2 or ancestry[0] != identity['head_sha']:
        raise ValueError('EXACT_SINGLE_PARENT_GRANT_MARKER_COMMIT_REQUIRED')
    executor_commit = grant['executor_commit']; grant_commit = ancestry[1]
    git_reader(root, ['merge-base', '--is-ancestor', executor_commit, grant_commit])
    grant_changed = git_reader(root, ['diff', '--name-only', executor_commit, grant_commit]).splitlines()
    if grant_changed != [f'.github/HCL_ENTRY_CONTRACT_SMOKE_20261008_{stage}_GRANT.json']:
        raise ValueError('ONLY_STAGE_GRANT_MAY_CHANGE_BETWEEN_EXECUTOR_AND_ADOPTION')
    changed = git_reader(root, ['diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD']).splitlines()
    for field in REPAIR_FIELDS:
        git_reader(root, ['merge-base', '--is-ancestor', package.value[field], 'HEAD'])
    # --is-ancestor returns no text on success and never changes repository state.
    rows = [row for page in history_pages for row in page.get('workflow_runs', [])] if isinstance(history_pages, list) else []
    current = [row for row in rows if row.get('id') == int(identity['run_id'])]
    if len(current) != 1: raise ValueError('EXACT_CURRENT_HISTORY_ROW_REQUIRED')
    marker = load_json(paths(root, stage)['marker'], 64000)
    launch = dict(run_id=int(identity['run_id']), attempt=1, pages=history_pages, workflow_id=current[0].get('workflow_id'), head_sha=identity['head_sha'], parent_sha=ancestry[1], event=environment['GITHUB_EVENT_NAME'], paths=changed, marker=marker, package_sha256=r.digest(package.value), grant_sha256=r.digest(grant), stage=stage, executor_commit=executor_commit, grant_commit=grant_commit, executor_ancestor_of_grant=True, grant_changed_paths=grant_changed)
    r.validate_launch_proposal(**launch)
    return launch


def normalized_prechecks(root, stage, identity, now, *, temporary_root=Path('/tmp')):
    locations = paths(root, stage, temporary_root)
    read_only_reader_pins(root)
    account_module = importlib.import_module('scripts.two_stage_account')
    price_module = importlib.import_module('scripts.two_stage_price')
    for module, path in ((account_module, 'scripts/two_stage_account.py'), (price_module, 'scripts/two_stage_price.py')):
        if Path(module.__file__).resolve() != (Path(root) / path).resolve():
            raise ValueError('IMPORTED_READER_PATH_MUST_MATCH_EXACT_PIN')
    presence = load_json(locations['presence'], 4096)
    if presence != dict(identity, existing_provider_secret='PRESENT'):
        raise ValueError('SAME_RUN_EXISTING_SECRET_PRESENCE_REQUIRED')
    price = load_json(locations['price'], 8192); old_account = load_json(locations['account'], 8192)
    price_module.validate_price_evidence(price, identity, now)
    account_module.validate(old_account, identity, now)
    # Projection only of old reader's approved readiness facts, never balance or key.
    account = dict(schema='hcl-entry-contract-smoke-account-readiness-v1', **identity, checked_at=old_account['checked_at'], currency=old_account['currency'], available=old_account['available'], model_calls=0, account_read_queries=1, existing_account_only=True)
    r.validate_readonly_prechecks(price, account, identity, now)
    return price, account


def admission_value(package, grant, identity, launch, price, account):
    return dict(schema='hcl-entry-contract-smoke-same-run-admission-v1', **identity, package_sha256=r.digest(package.value), grant_sha256=r.digest(grant), launch_sha256=r.digest(launch), price_sha256=r.digest(price), account_sha256=r.digest(account), native_public_permission_sha256=r.digest(grant['public_native_evidence_permission']))


def _make_existing_client():
    # Not called by preparation/tests. Future caller must pass every guard first.
    import importlib.metadata
    import logging
    if importlib.metadata.version('openai') != '2.14.0': raise ValueError('EXACT_PINNED_SDK_VERSION_REQUIRED')
    logging.disable(logging.CRITICAL); os.environ.pop('OPENAI_LOG', None)
    from openai import OpenAI
    key = os.environ.get('DEEPSEEK_API_KEY')
    if not key: raise ValueError('EXISTING_PROVIDER_SECRET_UNAVAILABLE')
    return OpenAI(api_key=key, base_url='https://api.deepseek.com', max_retries=0, timeout=r.WAIT)


def execute_admitted(root, stage, environment, *, now=None, temporary_root=Path('/tmp'), git_reader=git_text, client_factory=None, clock=utcnow):
    now = now or clock(); package, grant, identity = load_final_inputs(root, stage, environment, now)
    locations = paths(root, stage, temporary_root)
    history = load_json(locations['history']); launch = read_launch(root, stage, package, grant, identity, environment, history, git_reader=git_reader)
    price, account = normalized_prechecks(root, stage, identity, now, temporary_root=temporary_root)
    expected = admission_value(package, grant, identity, launch, price, account)
    if load_json(locations['admission'], 8192) != expected:
        raise ValueError('EXACT_SAME_RUN_ADMISSION_FILE_REQUIRED')
    phase1_evidence = phase1_review = None
    if stage == 2:
        phase1_evidence = load_json(locations['phase1_evidence']); phase1_review = load_json(locations['phase1_review'])
        if r.digest(phase1_review) != grant['phase1_source_review_sha256']:
            raise ValueError('EXACT_PHASE1_REVIEW_HASH_REQUIRED')
        public.validate_phase1_gate(package, phase1_evidence, phase1_review, native_permission=grant.get('public_native_evidence_permission'))
    exclusive_json(locations['consumed'], expected)
    r.require_time(clock())  # Approval time is checked again; per-stage dispatch margins are enforced by the ledger.
    client = (client_factory or _make_existing_client)()
    return r.run(client, package, grant, locations['directory'], launch=launch, price=price, account=account, identity=identity, phase1_evidence=phase1_evidence, phase1_review=phase1_review, clock=clock)


def close_interrupted_receipt(receipt, package):
    """No resumption, refund, fabricated usage or manufactured final result."""
    if receipt.get('status') in ('COMPLETED_ONE_PASS', 'STOPPED_NO_RETRY'):
        return receipt
    if receipt.get('status') != 'RUNNING' or receipt.get('package_sha256') != r.digest(package.value) or receipt.get('currency') != 'CNY' or type(receipt.get('stage')) is not int or receipt['stage'] not in (1,):
        raise ValueError('EXACT_INTERRUPTED_RECEIPT_REQUIRED')
    value = json.loads(r.canonical(receipt))
    for arm in value['arms']:
        calls = [c for c in value['calls'] if c['case_id'] == arm['case_id'] and c['arm'] == arm['arm']]
        if calls and arm['status'] == 'NOT_ATTEMPTED': arm['status'] = 'UNKNOWN_FAILURE_STOP'
        for call in calls:
            if call['invocation_status'] == 'INVOKED_OR_SEND_UNKNOWN':
                call.update(status='FAILED_OR_UNKNOWN', failure_code='UNKNOWN_SEND_USAGE_COST_OR_IDENTITY_STOP')
                arm['status'] = 'UNKNOWN_FAILURE_STOP'
    value.update(status='STOPPED_NO_RETRY', process_interrupted=True, elapsed_seconds=None, budget_state='CLOSED_NO_TRANSFER_NO_RETRY', remaining_authorized_calls=0, remaining_authorized_cny='0')
    return value


def export_terminal(root, stage, environment, *, now=None):
    locations = paths(root, stage); identity = environment_identity(environment, stage)
    package = r.FrozenPackage(load_json(locations['package']), load_json(locations['cases']), locations['root']); package.verify()
    grant = load_json(locations['grant'], 64000)
    # Validate static authority without reopening consumed execution. Cleanup
    # cannot send and has no calendar cutoff; it only closes/reports old holds.
    r.require_new_grant(package, grant, stage, r.timestamp(r.APPROVED))
    try:
        original = load_json(locations['directory'] / 'receipt.json')
        receipt = close_interrupted_receipt(original, package)
        # Validate ordinary identity/cost/final facts before replacing any local
        # receipt or attempting a native disclosure. Never invent missing totals.
        value = public.export(receipt, package, grant, identity, native_bundle=None)
    except Exception:
        value = dict(schema='hcl-entry-contract-smoke-public-integrity-unavailable-v1', authorization_ref=r.AUTH, currency='CNY', stage=stage, **identity, package_sha256=r.digest(package.value), status='RECEIPT_INTEGRITY_UNAVAILABLE_NO_RESUME', budget_state='CLOSED_NO_TRANSFER_NO_RETRY', remaining_authorized_calls=0, remaining_authorized_cny='0', prior_reservations='ALL_PREEXISTING_FULL_HOLDS_RETAINED_NO_RELEASE', reserved_cny=None, provider_calls=None, usage_rated_cny=None, invoice_cost_cny=None, usage_complete=False, native_publication_status='RECEIPT_INTEGRITY_UNAVAILABLE_GATE_CLOSED', approved_native_evidence=None, final_answers_unavailable=True)
        r.save(locations['public'], value)
        return value
    if receipt != original:
        r.save(locations['directory'] / 'receipt.json', receipt)
    bundle_path = locations['directory'] / 'native-review-private.json'
    if bundle_path.exists():
        try:
            bundle = load_json(bundle_path, 6 * 1048576)
            value = public.export(receipt, package, grant, identity, native_bundle=bundle)
        except Exception:
            # Reject the WHOLE native block. Preserve only the already-validated
            # ordinary closed receipt. Never copy exception or proposal text.
            value.update(native_publication_status='NATIVE_EXPORT_REJECTED_GATE_CLOSED', approved_native_evidence=None)
    r.save(locations['public'], value)
    return value


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Reviewed once-only reliability adapter; no creation or activation modes')
    parser.add_argument('--stage', type=int, choices=(1,), required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight', action='store_true'); mode.add_argument('--write-presence', action='store_true')
    mode.add_argument('--check-launch', action='store_true'); mode.add_argument('--execute', action='store_true'); mode.add_argument('--export', action='store_true')
    args = parser.parse_args(); os.umask(0o077)
    root = Path.cwd(); now = utcnow(); locations = paths(root, args.stage)
    if args.export:
        export_terminal(root, args.stage, os.environ, now=now)
        print('HCL_ENTRY_CONTRACT_SMOKE_APPROVED_PUBLIC_EXPORT_WRITTEN'); return
    package, grant, identity = load_final_inputs(root, args.stage, os.environ, now)
    if args.preflight:
        print('HCL_ENTRY_CONTRACT_SMOKE_EXACT_PREFLIGHT_PASS_ZERO_PROVIDER_CALLS'); return
    if args.write_presence:
        value = dict(identity, existing_provider_secret='PRESENT' if os.environ.get('SECRET_PRESENT') == 'true' else 'ABSENT')
        exclusive_json(locations['presence'], value)
        if value['existing_provider_secret'] != 'PRESENT': raise ValueError('EXISTING_SECRET_PRESENCE_REQUIRED')
        print('HCL_ENTRY_CONTRACT_SMOKE_EXISTING_SECRET_PRESENT'); return
    if args.check_launch:
        price, account = normalized_prechecks(root, args.stage, identity, now)
        launch = read_launch(root, args.stage, package, grant, identity, os.environ, load_json(locations['history']))
        exclusive_json(locations['admission'], admission_value(package, grant, identity, launch, price, account))
        print('HCL_ENTRY_CONTRACT_SMOKE_ONE_USE_LAUNCH_ADMITTED'); return
    execute_admitted(root, args.stage, os.environ)
    print('HCL_ENTRY_CONTRACT_SMOKE_TERMINATED_NO_RETRY')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # Never emit a traceback, provider exception body, private content or key.
        raise SystemExit('HCL_ENTRY_CONTRACT_SMOKE_ADAPTER_REFUSED_OR_STOPPED_NO_RETRY') from None
