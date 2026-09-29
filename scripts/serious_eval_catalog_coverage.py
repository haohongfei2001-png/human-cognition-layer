"""I02 structural scope report without modifying the frozen I01 validator.

Historical calibration packages hash serious_eval_contract.py. This module
reuses its case and freeze guards and never approves provider access.
"""
import argparse
import json
from pathlib import Path

from scripts.serious_eval_contract import FAMILIES, FREEZE, validate_candidate, validate_freeze


def audit_catalog_coverage(freeze, cases):
    """Validate all case boundaries, then describe restricted or full coverage."""
    validate_freeze(freeze)
    if not isinstance(cases, list) or not cases:
        raise ValueError('nonempty independent case catalog required')
    for case in cases:
        validate_candidate(freeze, case)
    if len({c['case_id'] for c in cases}) != len(cases):
        raise ValueError('duplicate case identity')
    for key in ('source_group_id', 'author_id', 'template_id', 'writing_system_id'):
        groups = {}
        for case in cases:
            group = case[key]
            prior = groups.setdefault(group, case['split'])
            if prior != case['split']:
                raise ValueError(f'{key} crosses calibration/confirmation')
    present = {c['task_family'] for c in cases}
    writing_systems = {c['writing_system_id'] for c in cases}
    return {
        'schema': 'hcl-i02-structural-catalog-coverage-v1',
        'case_count': len(cases),
        'calibration_case_count': sum(c['split'] == 'CALIBRATION' for c in cases),
        'confirmation_case_count': sum(c['split'] == 'CONFIRMATION' for c in cases),
        'task_families_present': [family for family in FAMILIES if family in present],
        'task_families_missing': [family for family in FAMILIES if family not in present],
        'independent_writing_system_count': len(writing_systems),
        'minimum_independent_writing_systems': freeze['minimum_independent_writing_systems'],
        'full_maturity_source_coverage': (
            present == set(FAMILIES) and
            len(writing_systems) >= freeze['minimum_independent_writing_systems']),
        'provider_approved': False,
        'efficacy_claim_qualified': False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', required=True, type=Path,
        help='JSON case catalog; output contains structural metadata only')
    parser.add_argument('--require-full-coverage', action='store_true',
        help='fail if the I01 full four-family/three-system target is absent')
    args = parser.parse_args()
    freeze = json.loads(FREEZE.read_text())
    cases = json.loads(args.catalog.read_text())
    report = audit_catalog_coverage(freeze, cases)
    if args.require_full_coverage and not report['full_maturity_source_coverage']:
        raise ValueError('catalog below I01 full maturity source coverage')
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == '__main__':
    main()
