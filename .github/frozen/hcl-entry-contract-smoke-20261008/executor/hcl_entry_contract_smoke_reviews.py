"""Load actual independently approved review bytes and verify exact non-circular targets.

Review artifacts bind source/runtime and a pre-package executable file set. They
never bind the later package hash that contains their own hashes. This loader
creates no approvals and never interprets a well-formed hash as a passing review.
"""
import json
from pathlib import Path
import re

import hcl_entry_contract_smoke_candidate as r

FROZEN = Path('.github/frozen/hcl-entry-contract-smoke-20261008')
CASE_FILE = FROZEN / 'cases.json'
CASE_REVIEW = FROZEN / 'reviews/case-review.json'
EXECUTOR_REVIEW = FROZEN / 'reviews/executor-review.json'
CASE_CHECKS = {'source_rubric_passed', 'native_admissibility_passed', 'native_capacity_passed', 'unchanged_frozen_packet_and_regression_exposure_declared', 'added_routing_rule_fixed_before_output'}
EXECUTOR_CHECKS = {'all_blockers_resolved', 'provider_free_regressions_passed', 'native_permission_required_before_external_work'}


def read_hashed_json(root, relative, expected_sha256, *, maximum=2 * 1024 * 1024):
    root = Path(root).resolve(); path = root / relative
    r.exact_sha(expected_sha256)
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root) or not 0 < path.stat().st_size <= maximum:
        raise ValueError('ACTUAL_BOUNDED_REVIEW_OR_CASE_ARTIFACT_REQUIRED')
    raw = path.read_bytes()
    if len(raw) > maximum or r.hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError('EXACT_REVIEW_OR_CASE_FILE_BYTES_REQUIRED')
    return json.loads(raw)


def _passing_checks(value, keys):
    return isinstance(value, dict) and set(value) == keys and all(item is True for item in value.values())


def verify_review_artifacts(package):
    value = package.value
    actual_packet = read_hashed_json(package.runtime_root, CASE_FILE, value['case_raw_file_sha256'])
    if actual_packet != package.packet or r.digest(actual_packet) != value['packet_sha256']:
        raise ValueError('RAW_FILE_AND_CANONICAL_CASE_IDENTITIES_REQUIRED')
    targets = dict(case_raw_file_sha256=value['case_raw_file_sha256'], case_canonical_packet_sha256=value['packet_sha256'], runtime_sha256=value['runtime_sha256'], runtime_commit=value['runtime_commit'])
    case = read_hashed_json(package.runtime_root, CASE_REVIEW, value['independent_case_review_sha256'])
    case_keys = {'schema', 'verdict', 'reviewer_role', *targets, 'checks', 'evidence_sha256', 'provider_calls', 'live_execution_authorized', 'efficacy_claimed'}
    if not isinstance(case, dict) or set(case) != case_keys or case['schema'] != 'hcl-entry-contract-smoke-independent-case-review-v1' or case['verdict'] != 'PASS_FOR_BOUNDED_DEVELOPMENT_ONLY' or case['reviewer_role'] != 'INDEPENDENT_REGRESSION_CASE_REVIEW_BEFORE_ENTRY_CONTRACT_SMOKE_OUTPUT' or any(case[key] != target for key, target in targets.items()) or not _passing_checks(case['checks'], CASE_CHECKS) or type(case['provider_calls']) is not int or case['provider_calls'] != 0 or case['live_execution_authorized'] is not False or case['efficacy_claimed'] is not False:
        raise ValueError('PASSING_TARGET_BOUND_INDEPENDENT_CASE_REVIEW_REQUIRED')
    evidence = case['evidence_sha256']
    if not isinstance(evidence, dict) or not 1 <= len(evidence) <= 16 or any(not isinstance(name, str) or re.fullmatch(r'[A-Za-z0-9_.-]{1,128}', name) is None for name in evidence):
        raise ValueError('BOUNDED_CASE_REVIEW_EVIDENCE_HASHES_REQUIRED')
    for sha in evidence.values(): r.exact_sha(sha)
    executor = read_hashed_json(package.runtime_root, EXECUTOR_REVIEW, value['independent_executor_review_sha256'])
    executor_keys = {'schema', 'verdict', 'reviewer_role', *targets, 'case_review_file_sha256', 'executor_files_sha256', 'workflow_files_sha256', 'read_only_reader_files_sha256', 'checks', 'verification', 'live_execution_authorized'}
    if not isinstance(executor, dict) or set(executor) != executor_keys or executor['schema'] != 'hcl-entry-contract-smoke-independent-executor-approval-v1' or executor['verdict'] != 'PASS_FOR_BOUNDED_EXECUTOR_PACKAGE' or executor['reviewer_role'] != 'INDEPENDENT_READ_ONLY_SECURITY_REVIEW' or any(executor[key] != target for key, target in targets.items()) or executor['case_review_file_sha256'] != value['independent_case_review_sha256'] or executor['executor_files_sha256'] != value['configuration']['executor_files'] or executor['workflow_files_sha256'] != value['workflow_files'] or executor['read_only_reader_files_sha256'] != value['read_only_reader_files'] or not _passing_checks(executor['checks'], EXECUTOR_CHECKS) or executor['live_execution_authorized'] is not False:
        raise ValueError('PASSING_TARGET_BOUND_INDEPENDENT_EXECUTOR_REVIEW_REQUIRED')
    verification = executor['verification']
    expected = {'provider_calls', 'account_queries', 'credentials_read', 'sdk_constructed', 'provider_free_tests_passed'}
    if not isinstance(verification, dict) or set(verification) != expected or any(type(verification[key]) is not int or verification[key] != 0 for key in ('provider_calls', 'account_queries')) or verification['credentials_read'] is not False or verification['sdk_constructed'] is not False or type(verification['provider_free_tests_passed']) is not int or verification['provider_free_tests_passed'] < 1:
        raise ValueError('EXACT_EXECUTOR_REVIEW_VERIFICATION_REQUIRED')
    return dict(case_review=case, executor_review=executor)
