"""Separate the immutable Oct 8 diagnostic identity from current fake behavior.

No old package, approval, pin or implementation is changed. The twelve original
identity-bound tests run on a small, explicit baseline projection. The other 39
original tests run on current code. Additional current controls retain the real
diagnostic behavior with a newly built, offline-only test fixture; the unchanged
historical preflight and live gates must reject the current tree before I/O.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts.run_unified_legacy_regressions import (
    BASELINE, ROOT, baseline_runtime_inventory, flatten,
    validate_current_legacy_projection,
)

PREFLIGHT_MODULE = 'tests.test_hcl_offline_diagnostic_preflight_v1'
LIVE_MODULE = 'tests.test_hcl_diagnostic_smoke_live_v1'
MODULES = (PREFLIGHT_MODULE, 'tests.test_hcl_diagnostic_shared_core', LIVE_MODULE)
HISTORICAL_LIVE_IDS = frozenset(LIVE_MODULE + '.AuthorityTests.' + name for name in (
    'test_full_package_freeze_checks_actual_source_and_noncircular_review_targets',
    'test_current_request_and_runtime_stay_exact_and_old_authority_excluded',
))
CURRENT_CONTROL_METHODS = (
    'test_fixed_controls_persist_distinct_diagnostics_and_failed_source_bindings',
    'test_trusted_originals_reload_and_fail_closed_on_mutation_or_staleness',
    'test_post_runtime_capture_failure_preserves_diagnostic_without_invented_native',
    'test_declared_capture_missing_or_changed_preserves_public_diagnosis_but_rejects_binding',
    'test_unknown_control_and_existing_output_cannot_start_another_fake_call',
)
# Explicit source/fixture allowlist. No eval directory, grant or trigger is read.
# The archived candidate computes hashes of all twelve helper files, but only
# the three load-only helpers are imported. Reader code is hashed, never invoked.
DIAGNOSTIC_FILES = (
    'scripts/hcl_diagnostic_smoke_live_v1.py',
    'scripts/hcl_offline_diagnostic_export_v1.py',
    'scripts/hcl_offline_diagnostic_public_v1.py',
    'scripts/hcl_offline_diagnostic_reference.py',
    'scripts/hcl_offline_diagnostic_preflight_v1.py',
    'scripts/hcl_offline_diagnostic_preflight_v1.json',
    'scripts/two_stage_price.py', 'scripts/two_stage_account.py',
    'tests/test_hcl_diagnostic_smoke_live_v1.py',
    'tests/test_hcl_diagnostic_shared_core.py',
    'tests/test_hcl_offline_diagnostic_export_v1.py',
    'tests/test_hcl_offline_diagnostic_preflight_v1.py',
    '.github/frozen/hcl-entry-contract-smoke-20261008/cases.json',
    '.github/frozen/hcl-diagnostic-smoke-20261008/package.json',
    '.github/frozen/hcl-diagnostic-smoke-20261008/reviews/case-review.json',
    '.github/frozen/hcl-diagnostic-smoke-20261008/reviews/executor-review.json',
    '.github/workflows/hcl-diagnostic-smoke-20261008-1-once.yml',
) + tuple('.github/frozen/hcl-entry-contract-smoke-20261008/executor/' + name for name in (
    'hcl_entry_contract_smoke_candidate.py', 'hcl_entry_contract_smoke_public.py',
    'hcl_entry_contract_smoke_native_public.py', 'hcl_entry_contract_smoke_cli.py',
    'hcl_entry_contract_smoke_reviews.py',
    'tests/test_hcl_entry_contract_smoke_candidate.py',
    'tests/test_hcl_entry_contract_smoke_adapter.py',
    'tests/test_hcl_entry_contract_smoke_revision3.py',
    'tests/test_hcl_entry_contract_smoke_native_regressions.py',
    'tests/test_hcl_entry_contract_smoke_time_and_diagnostics.py',
    'tests/test_hcl_entry_contract_smoke_routing_gate.py',
    'tests/test_hcl_entry_contract_smoke_prefinal_gate.py',
))


def diagnostic_inventory():
    inventory = baseline_runtime_inventory()
    for name in DIAGNOSTIC_FILES:
        metadata = subprocess.check_output(['git', 'ls-tree', BASELINE, '--', name], cwd=ROOT).decode()
        parts = metadata.strip().split()
        if len(parts) != 4 or parts[:2] != ['100644', 'blob'] or parts[3] != name:
            raise ValueError('diagnostic baseline must contain the exact regular allowlisted file')
        inventory[name] = parts[2]
        # A future behavior change must explicitly revisit this migration.
        current = subprocess.check_output(['git', 'hash-object', '--', name], cwd=ROOT).decode().strip()
        if current != parts[2]:
            raise ValueError('diagnostic implementation/fixture changed: ' + name)
    return inventory


@contextmanager
def diagnostic_projection():
    inventory = diagnostic_inventory()  # Resolve metadata before any content read.
    with tempfile.TemporaryDirectory(prefix='hcl-diagnostic-identity-') as directory:
        root = Path(directory)
        for name, blob in inventory.items():
            target = root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(subprocess.check_output(['git', 'cat-file', 'blob', blob], cwd=ROOT))
        yield root


@contextmanager
def current_offline_control_fixture():
    """TEST ONLY: bind the unchanged fake mechanics to the current runtime.

    This never changes a signed manifest or runtime digest, never adapts any
    live gate, and is restored on exit. Original admission rejection is tested
    separately. Every FakeClient reservation still verifies the current package.
    """
    from scripts import hcl_offline_diagnostic_preflight_v1 as f
    from scripts import hcl_offline_diagnostic_export_v1 as r
    validate_current_legacy_projection()
    manifest = f._read_json(f.MANIFEST)
    packet = f._read_json(ROOT/manifest['cases_file'], file_sha256=manifest['cases_file_sha256'])
    package = r.OfflinePackage.build(packet, ROOT)
    if package.value['live_execution_authorized'] is not False or package.value['actual_spend_cny'] != '0':
        raise ValueError('offline fixture cannot carry live authority')
    with patch.object(f, 'preflight', return_value=package):
        yield package


def run(output: Path):
    os.chdir(ROOT)
    validate_current_legacy_projection()
    tests = list(flatten(unittest.defaultTestLoader.loadTestsFromNames(MODULES)))
    by_id = {test.id(): test for test in tests}
    historical_ids = {name for name in by_id if name.startswith(PREFLIGHT_MODULE + '.')}
    historical_ids |= HISTORICAL_LIVE_IDS
    if len(tests) != len(by_id) or not historical_ids <= set(by_id) or len(historical_ids) != 12:
        raise ValueError('explicit diagnostic test partition changed')
    current = [test for test in tests if test.id() not in historical_ids]
    extra = list(flatten(unittest.defaultTestLoader.loadTestsFromName('tests.test_unified_diagnostic_migration')))
    if len(current) != 39 or len(extra) != 9:
        raise ValueError('diagnostic behavior inventory changed; review the explicit partition')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(current + extra))
    current_pass = result.wasSuccessful() and not result.skipped and result.testsRun == len(current) + len(extra)
    child = """
import socket, sys, unittest
def deny(*args, **kwargs):
    raise AssertionError('DIAGNOSTIC_IDENTITY_REPLAY_NETWORK_FORBIDDEN')
class NoLiveImports:
    def find_spec(self, fullname, *args):
        if fullname.split('.')[0] in ('openai', 'requests', 'httpx') or fullname in ('scripts.two_stage_account', 'scripts.two_stage_price', 'hcl_entry_contract_smoke_cli'):
            raise AssertionError('DIAGNOSTIC_IDENTITY_REPLAY_LIVE_IMPORT_FORBIDDEN')
sys.meta_path.insert(0, NoLiveImports())
socket.create_connection = socket.getaddrinfo = deny
socket.socket.connect = socket.socket.connect_ex = deny
suite = unittest.defaultTestLoader.loadTestsFromNames(TEST_IDS)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if result.testsRun != len(TEST_IDS) or result.skipped or not result.wasSuccessful():
    raise SystemExit(1)
from pathlib import Path
from scripts import hcl_diagnostic_smoke_live_v1 as live
root = Path.cwd()
live.LivePackage(live.load_json(root/live.PACKAGE_PATH), live.load_json(root/live.CASE_PATH), root).verify()
print('HISTORICAL_DIAGNOSTIC_PACKAGE_AND_REVIEWS_VERIFIED_ZERO_PROVIDER_CALLS')
"""
    with diagnostic_projection() as root:
        env = {'PATH': os.environ.get('PATH', ''), 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}
        process = subprocess.run([sys.executable, '-B', '-c', 'TEST_IDS=' + repr(sorted(historical_ids)) + '\n' + child],
                                 cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output.with_suffix('.historical.log').write_text(process.stdout)
    receipt = {
        'schema': 'hcl-unified-diagnostic-regression-partition-1',
        'current_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'historical_identity_baseline': BASELINE,
        'discovered': len(tests), 'current_behavior': len(current), 'historical_identity': len(historical_ids),
        'current_test_ids': [test.id() for test in current], 'historical_test_ids': sorted(historical_ids),
        'additional_current_test_ids': [test.id() for test in extra],
        'original_control_methods_repeated_on_current_offline_fixture': list(CURRENT_CONTROL_METHODS),
        'current_pass': current_pass, 'historical_pass': process.returncode == 0,
        'historical_package_verified': process.returncode == 0,
        'current_rejects_old_runtime_authority': current_pass,
        'skipped_or_dropped_by_partition': 0, 'provider_calls': 0,
        'scope': 'DIAGNOSTIC_MIGRATION_REGRESSION_NOT_UNIFIED_COGNITIVE_ACCEPTANCE',
    }
    assert receipt['discovered'] == receipt['current_behavior'] + receipt['historical_identity']
    output.write_text(json.dumps(receipt, indent=2) + '\n')
    if process.returncode:
        print(process.stdout)
    if not current_pass or process.returncode:
        raise SystemExit(1)
    print(f'DIAGNOSTIC_CURRENT={len(current)}; HISTORICAL_IDENTITY={len(historical_ids)}; EXTRA_CURRENT={len(extra)}; NO_TEST_DROPPED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output)
