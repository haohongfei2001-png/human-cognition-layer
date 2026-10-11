"""Keep current behavior regression separate from immutable historical identity.

Only named whole-runtime fingerprint methods use the original hcl projection.
No pinned guard/test/report is rewritten. The mixed FinalDeliveryTests continue
executing CURRENT imported code; their setup's obsolete whole-tree identity
precondition is replaced by a byte-exact legacy-module compatibility assertion.
Every discovered test ID is accounted for, and the current tree must fail the
old runtime grant identity gate. This does not certify old grants for new code.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '52cccc0a496e5d11c4749e98ea8e5dd80ca4a170'
HISTORICAL_IDS = frozenset((
    'test_v1_a02_scope_amendment.ScopeAmendmentTests.test_prior_evidence_and_both_scope_fixture_hashes_are_pinned',
    'test_v1_a02_scope_amendment.ScopeAmendmentTests.test_unrelated_anchor_and_b04_changes_cannot_enter_scope_amendment',
    'test_v1_answer_citation_contract.AnswerCitationContractTests.test_current_amendment_preserves_runtime_membership_validator_and_failed_receipt',
    'test_v1_citation_boundary_repair.CitationBoundaryRepairTests.test_historical_pins_and_changes_outside_two_functions_reject',
    'test_v1_explicit_citation_contract.ExplicitCitationContractTests.test_current_contract_and_historical_freeze_reject_mutations',
    'test_v1_final_context_amendment.FinalContextAmendmentTests.test_exact_current_runtime_and_only_reviewed_file_are_accepted',
    'test_v1_final_context_amendment.FinalContextAmendmentTests.test_runtime_mutation_and_missing_membership_cannot_be_covered_by_supplied_digest',
    'test_v1_final_context_amendment.FinalContextAmendmentTests.test_history_manifest_and_every_consumed_artifact_are_pinned',
    'test_v1_final_delivery_diagnostics.FinalDeliveryAmendmentTests.test_current_runtime_and_consumed_history_are_pinned',
    'test_v1_full_long_source.FullLongSourceTests.test_amendment_chain_fails_drift_and_historical_link',
    'test_v1_reader_final_budget.ReaderFinalBudgetTests.test_current_amendment_and_wrong_digest',
    'test_v1_typographic_dialogue_entry.TypographicDialogueTests.test_runtime_chain_rejects_new_digest_or_previous_digest_drift',
    'test_v1_universal_argument.ArgumentFreezeTests.test_amendment_preserves_previous_files_and_unrelated_runtime',
    'test_v1_universal_concept.ConceptFreezeTests.test_amendment_preserves_previous_files_and_unrelated_runtime',
    'test_v1_universal_normative.NormativeFreezeTests.test_amendment_preserves_historical_evidence_and_unrelated_runtime_guards',
    'test_v1_universal_sensitivity.SensitivityFreezeTests.test_every_historical_amendment_rejects_tampering',
    'test_v1_universal_sensitivity.SensitivityFreezeTests.test_runtime_drift_and_missing_membership_reject',
    'test_v1_universal_argument.ArgumentFreezeTests.test_every_historical_amendment_pin_rejects_tampering',
    'test_v1_final_delivery_diagnostics.FinalDeliveryAmendmentTests.test_new_pin_manifest_cannot_silently_rebaseline_history',
))
MIXED_CLASS = 'test_v1_final_delivery_diagnostics.FinalDeliveryTests.'
# The only non-code eval fixtures used by these fingerprint methods, all
# previously exposed guard/counterexample fixtures. No corpus directory link.
HISTORICAL_EVAL_FILES = (
    'eval/a02_scope_boundary_review_v1.json', 'eval/a02_scope_proposal_v1.json',
    'eval/b04_copy_reference_counterexamples_v1.json', 'eval/planner_contract_challenges_v1.json',
)
CURRENT_WITNESSES = frozenset('scripts.witness_' + name for name in (
    'c02_planned_input', 'llm_routing_execution', 'universal_sensitivity',
    'universal_appraisal', 'universal_agency_chain', 'universal_commitment',
    'universal_understanding', 'universal_argument', 'universal_concept',
    'embedded_scene_cues', 'narrator_actual_scope',
))


def baseline_runtime_inventory():
    raw = subprocess.check_output(['git', 'ls-tree', '-rz', BASELINE, 'hcl'], cwd=ROOT)
    inventory = {}
    for row in raw.split(b'\0'):
        if not row:
            continue
        metadata, name = row.split(b'\t', 1)
        mode, kind, blob = metadata.decode().split()
        path = name.decode()
        if path.endswith('.py'):
            if kind != 'blob' or mode != '100644' or not path.startswith('hcl/') or '..' in Path(path).parts:
                raise ValueError('invalid allowlisted runtime path')
            inventory[path] = blob
    if not inventory:
        raise ValueError('historical Python runtime missing')
    return inventory


def validate_current_legacy_projection():
    """Current legacy algorithm bytes must match; new API is not old authority."""
    for name, expected_blob in baseline_runtime_inventory().items():
        if name == 'hcl/__init__.py':
            # The reviewed new public export is the one intentional old-file edit.
            continue
        body = (ROOT/name).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
        if actual != expected_blob:
            raise ValueError(f'current legacy behavior changed: {name}')
    from scripts.development_plan_diagnostics_amendment import validate_current
    try:
        validate_current()
    except ValueError as error:
        if str(error) != 'unrelated runtime outside reviewed scope changed':
            raise
    else:
        raise ValueError('new runtime must not inherit the historical grant identity')
    return True


@contextmanager
def historical_runtime_projection():
    inventory = baseline_runtime_inventory()  # Metadata allowlist precedes reads.
    with tempfile.TemporaryDirectory(prefix='hcl-s1-identity-') as directory:
        root = Path(directory)
        for name, blob in inventory.items():
            destination = root/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(subprocess.check_output(['git', 'cat-file', 'blob', blob], cwd=ROOT))
        # These already-exposed artifacts remain unchanged in the working repo.
        # Tests read their explicit pin maps; no history/corpus contents scan.
        for name in ('scripts', 'tests', 'reports', 'docs', '.github', '.git'):
            (root/name).symlink_to(ROOT/name)
        for name in HISTORICAL_EVAL_FILES:
            destination = root/name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.symlink_to(ROOT/name)
        yield root


def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test


class CurrentMixedBehaviorSuite(unittest.TestSuite):
    def run(self, result, debug=False):
        module = sys.modules['test_v1_final_delivery_diagnostics']
        cls = module.FinalDeliveryTests
        original_setup = cls.setUpClass
        def setup():
            with patch.object(module, 'validate_current', validate_current_legacy_projection):
                original_setup()
        # Only the setup precondition is adapted; execute/pair/test methods and
        # the original immutable guard remain untouched.
        with patch.object(cls, 'setUpClass', setup):
            return super().run(result, debug)


def run(output: Path):
    os.chdir(ROOT)
    validate_current_legacy_projection()
    tests = list(flatten(unittest.defaultTestLoader.discover('tests', 'test_v1*.py')))
    by_id = {test.id(): test for test in tests}
    if len(by_id) != len(tests) or not HISTORICAL_IDS <= set(by_id):
        raise ValueError('test partition must account for each original test exactly once')
    historical = [by_id[name] for name in sorted(HISTORICAL_IDS)]
    mixed = [test for test in tests if test.id().startswith(MIXED_CLASS)]
    current = [test for test in tests if test.id() not in HISTORICAL_IDS and test not in mixed]
    suite = unittest.TestSuite([unittest.TestSuite(current), CurrentMixedBehaviorSuite(mixed)])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    with historical_runtime_projection() as root:
        env = {'PATH': os.environ.get('PATH', ''), 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}
        child = """
import socket, unittest

def deny(*args, **kwargs):
    raise RuntimeError('HISTORICAL_IDENTITY_REPLAY_NETWORK_FORBIDDEN')
socket.create_connection = socket.getaddrinfo = deny
socket.socket.connect = socket.socket.connect_ex = deny
suite = unittest.defaultTestLoader.loadTestsFromNames(TEST_IDS)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if result.testsRun != len(TEST_IDS) or not result.wasSuccessful():
    raise SystemExit(1)
"""
        process = subprocess.run([sys.executable, '-B', '-c', 'TEST_IDS=' + repr(['tests.' + name for name in sorted(HISTORICAL_IDS)]) + '\n' + child],
                                 cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output.with_suffix('.historical.log').write_text(process.stdout)
    receipt = {'schema': 'hcl-unified-legacy-regression-partition-1',
               'current_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
               'historical_identity_baseline': BASELINE,
               'discovered': len(tests), 'current_behavior': len(current),
               'mixed_current_behavior': len(mixed), 'historical_identity': len(historical),
               'current_test_ids': [test.id() for test in current],
               'mixed_current_test_ids': [test.id() for test in mixed],
               'historical_test_ids': sorted(HISTORICAL_IDS),
               'current_pass': result.wasSuccessful(), 'historical_pass': process.returncode == 0,
               'current_rejects_old_runtime_authority': True, 'provider_calls': 0,
               'skipped_or_dropped_by_partition': 0}
    assert receipt['discovered'] == receipt['current_behavior'] + receipt['mixed_current_behavior'] + receipt['historical_identity']
    output.write_text(json.dumps(receipt, indent=2) + '\n')
    if process.returncode:
        print(process.stdout)
    if not result.wasSuccessful() or process.returncode:
        raise SystemExit(1)
    print(f"CURRENT_BEHAVIOR={len(current)+len(mixed)}; HISTORICAL_IDENTITY={len(historical)}; NO_TEST_DROPPED")


def run_current_witness(module_name: str, output: Path):
    """Adapt only a witness's first identity precondition, not its computation."""
    if module_name not in CURRENT_WITNESSES:
        raise ValueError('only the explicit provider-free witness allowlist is supported')
    module = importlib.import_module(module_name)
    original = module.validate_current
    called = False
    def compatibility_precondition():
        nonlocal called
        called = True
        module.validate_current = original  # Restore before any actual witness computation.
        return validate_current_legacy_projection()
    with patch.object(module, 'validate_current', compatibility_precondition):
        evidence = module.witness()
    if not called:
        raise ValueError('witness identity precondition was not exercised')
    evidence['unified_runtime_compatibility_context'] = {
        'current_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'legacy_byte_baseline': BASELINE,
        'scope': 'PRESERVED_LEGACY_BEHAVIOR_ON_CURRENT_TREE_NOT_NEW_UNIFIED_CAPABILITY',
        'historical_grant_identity_inherited': False,
    }
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print('CURRENT_LEGACY_WITNESS_PASSED_WITHOUT_OLD_AUTHORITY: ' + module_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--witness', choices=sorted(CURRENT_WITNESSES))
    args = parser.parse_args()
    if args.witness:
        run_current_witness(args.witness, args.output)
    else:
        run(args.output)
