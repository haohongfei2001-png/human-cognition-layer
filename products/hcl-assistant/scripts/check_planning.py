"""Provider-free L0 control-plane checks; never import or inspect research assets.

This validates planning structure and declared boundaries, not cognition efficacy.
Run from the product tree or its standalone export. No network calls are made.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


class PlanningError(ValueError):
    """An adopted planning invariant or reference is invalid."""


REQUIRED_DOCS = (
    'README.md', 'STATUS.md', 'DEVELOPMENT_PLAN.md', 'AGENTS.md',
    'HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md',
    'contracts/PRODUCT_CONTRACTS_V1.md', 'contracts/catalog.json',
    'contracts/capabilities.json', 'contracts/capability-manifest.schema.json',
    'control/plan.json', 'docs/L0_L2_WORK_PACKAGES.md',
    'docs/ACCEPTANCE_MATRIX.md', 'docs/UX_SPEC.md',
    'docs/BOUNDARY_AND_ISOLATION.md', 'docs/RESEARCH_BASELINE.md',
)
CONTRACT_IDS = {'interaction_controller', 'context', 'revision',
                'answer_synthesis', 'explain_projection', 'capability_manifest',
                'run_receipt'}
CONTEXT_KINDS = {'USER_REPORTED_EVENT', 'USER_GUESS', 'CHARACTER_SELF_REPORT',
                 'THIRD_PARTY_REPORT', 'SYSTEM_INTERPRETATION', 'HYPOTHETICAL',
                 'CONDITIONAL_RULE', 'CORRECTION', 'RETRACTION'}
REVISION_ACTIONS = {'ADD', 'CORRECT', 'RETRACT', 'SUPERSEDE',
                    'HYPOTHETICAL_BRANCH', 'STOP_USING', 'DELETE'}
PERMISSIONS = {'ACCOUNT_DATA_ACCESS', 'PERSON_PERSPECTIVE_ACCESS',
               'PERSISTENCE_REUSE_PERMISSION'}
IGNORED_DIRS = {'.git', '.venv', '__pycache__', 'node_modules', 'dist', 'coverage', '.tmp', '.local'}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PlanningError(message)


def safe_path(root: Path, relative: str) -> Path:
    require(isinstance(relative, str) and bool(relative), 'nonempty relative path required')
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts, 'outside product path')
    current = root
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), 'symlinks are not allowed in product export')
    require(current.resolve().is_relative_to(root.resolve()), 'outside product root')
    return current


def load_json(root: Path, relative: str) -> Any:
    return json.loads(safe_path(root, relative).read_text(encoding='utf-8'))


def validate_plan(plan: dict[str, Any]) -> None:
    require(plan.get('schema_version') == '1.0', 'plan version')
    require(plan.get('research_sequence') == ['I02', 'I03', 'I04', 'I05', 'I06'], 'research sequence changed')
    inv = plan.get('invariants', {})
    for key in ('assistant_first', 'controller_required_for_production_answer'):
        require(inv.get(key) is True, f'required invariant: {key}')
    for key in ('frontend_hcl_toggle', 'production_base_bypass',
                'lab_compare_enabled_in_l2', 'hidden_chain_of_thought_storage',
                'historical_model_output_is_independent_evidence',
                'mock_may_be_relabelled_real', 'confirmation_material_allowed'):
        require(inv.get(key) is False, f'forbidden invariant: {key}')
    require(type(inv.get('max_provider_calls_l0_l2')) is int and inv['max_provider_calls_l0_l2'] == 0,
            'L0-L2 provider calls must be zero')
    boundary = plan.get('boundary', {})
    require(boundary.get('research_import_allowed') is False, 'research import forbidden')
    if boundary.get('physical_repository_split') is not True:
        require(boundary.get('real_data_allowed') is False and boundary.get('public_deployment_allowed') is False,
                'unsplit boundary cannot allow real data or public deployment')
    packages = plan.get('packages', [])
    require(len(packages) == 9, 'nine coherent L0-L2 packages required')
    seen: set[str] = set()
    for row in packages:
        key = row.get('id')
        require(isinstance(key, str) and key not in seen, 'duplicate or invalid package id')
        require(re.fullmatch(r'L[012]-\d{2}', key) is not None, 'invalid package id')
        require(row.get('stage') == key[:2], 'package stage mismatch')
        require(set(row.get('depends_on', [])) <= seen, 'unknown or forward/cyclic dependency')
        require(bool(row.get('delta')), 'product delta required')
        seen.add(key)
    next_id = plan.get('next_package_id')
    require(next_id in seen, 'unknown next package')
    require(plan.get('next_ready', '').startswith(next_id + '_'), 'NEXT_READY id mismatch')
    require(plan.get('adoption_gate') == 'MERGED_MAIN_AND_EXACT_SHA_PLANNING_PASS', 'adoption gate required')
    require('PHYSICAL_PRODUCT_REPOSITORY_SPLIT' in plan.get('l3_gates', []), 'L3 split gate missing')
    require('I06_DISPOSITION' in plan.get('l3_gates', []), 'I06 gate missing')


def validate_catalog(catalog: dict[str, Any]) -> None:
    rows = catalog.get('contracts', [])
    require(len(rows) == len(CONTRACT_IDS) and {r.get('id') for r in rows} == CONTRACT_IDS,
            'missing or duplicate stable contract')
    for row in rows:
        require(row.get('version') == '1.0', 'contract version mismatch')
        require(bool(row.get('required') or row.get('required_input')), 'empty contract fields')
    enums = catalog.get('enums', {})
    require(set(enums.get('context_kinds', [])) == CONTEXT_KINDS, 'context distinctions missing')
    require(set(enums.get('revision_actions', [])) == REVISION_ACTIONS, 'revision distinctions missing')
    require(set(catalog.get('permission_dimensions', [])) == PERMISSIONS, 'three separate permissions required')
    require(catalog.get('research_package_ids_are_product_keys') is False, 'package-based UI keys forbidden')
    require(catalog.get('explain_new_model_calls_default') == 0, 'Explain must not manufacture reasons')
    require(catalog.get('uncalibrated_probability_claims_allowed') is False, 'uncalibrated probabilities forbidden')
    require(catalog.get('semantics_verified_by_schema') is False, 'schema is not semantic proof')
    controller = next(r for r in rows if r['id'] == 'interaction_controller')
    require({'event', 'scope', 'expected_state_version', 'allowed_memory_scope', 'source_refs',
             'model_resource_policy', 'idempotency_key'} <= set(controller['required_input']),
            'controller input incomplete')
    require({'accepted_change_ids', 'invalidated_state_ids', 'selected_context', 'route',
             'explain_projection', 'run_receipt', 'unresolved_updates'} <= set(controller['required_output']),
            'controller output incomplete')


def validate_capabilities(manifest: dict[str, Any], schema: dict[str, Any], catalog: dict[str, Any]) -> None:
    # A targeted dependency-free contract checker; the JSON Schema is published
    # separately for interoperable validation. This is not a generic schema engine.
    require(manifest.get('schema_version') == '1.0', 'manifest version')
    require(schema.get('$schema') == 'https://json-schema.org/draft/2020-12/schema', 'schema dialect')
    definition = schema.get('$defs', {}).get('capability', {})
    required = set(definition.get('required', []))
    expected = next(r['required'] for r in catalog['contracts'] if r['id'] == 'capability_manifest')
    require(set(expected) <= required, 'manifest schema omits required fields')
    dispositions = set(catalog['enums']['dispositions'])
    seen: set[str] = set()
    rows = manifest.get('capabilities', [])
    require(isinstance(rows, list) and bool(rows), 'capability candidates required')
    for row in rows:
        require(required <= set(row), 'missing capability field')
        key = row['capability_id']
        require(isinstance(key, str) and re.fullmatch(r'[a-z][a-z0-9_]+', key) is not None,
                'stable product capability id required')
        require(key not in seen, 'duplicate capability id')
        seen.add(key)
        require(row['contract_version'] == '1.0', 'capability version')
        for field in ('supported_input', 'language', 'planned_languages', 'output_objects', 'limitations'):
            values = row[field]
            require(isinstance(values, list) and all(isinstance(x, str) and x for x in values),
                    f'invalid capability {field}')
            require(len(values) == len(set(values)), f'duplicate {field}')
        require(bool(row['limitations']), 'limitations required')
        require(row['i06_disposition'] in dispositions, 'unknown disposition')
        policy = row['product_activation_policy']
        require(type(policy.get('production_enabled')) is bool, 'boolean production policy required')
        require(policy.get('mode') in {'MOCK_ONLY', 'DISABLED', 'EXPERIMENTAL', 'SCOPE_DEFAULT'}, 'activation mode')
        if row['i06_disposition'] == 'PENDING_I06':
            require(row['runtime_implementation'] is None and policy['production_enabled'] is False
                    and policy['mode'] in {'MOCK_ONLY', 'DISABLED'}, 'pending I06 cannot be live')
        if row['i06_disposition'] == 'DISABLE':
            require(policy['mode'] == 'DISABLED' and not policy['production_enabled'], 'disabled capability is active')
        if policy['production_enabled']:
            require(isinstance(row['runtime_implementation'], dict) and bool(row['language'])
                    and policy['mode'] == 'SCOPE_DEFAULT', 'production implementation/language gate missing')
        if row['evidence_status'] == 'DESIGN_ONLY':
            require(not policy['production_enabled'] and row['runtime_implementation'] is None
                    and row['language'] == [], 'design-only cannot claim live coverage')


def product_files(root: Path) -> list[Path]:
    import os
    found = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in list(dirs):
            child = Path(directory) / name
            require(not child.is_symlink(), 'symlink directory forbidden')
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
        for name in files:
            path = Path(directory) / name
            require(not path.is_symlink(), 'symlink file forbidden')
            if path.suffix == '.pyc':
                continue
            found.append(path)
    return sorted(found)


def validate_tree(root: Path) -> dict[str, Any]:
    root = root.resolve()
    for relative in REQUIRED_DOCS:
        require(safe_path(root, relative).is_file(), f'missing product file: {relative}')
    files = product_files(root)
    plan = load_json(root, 'control/plan.json')
    catalog = load_json(root, 'contracts/catalog.json')
    validate_plan(plan)
    validate_catalog(catalog)
    validate_capabilities(load_json(root, 'contracts/capabilities.json'),
                          load_json(root, 'contracts/capability-manifest.schema.json'), catalog)
    for name in ('STATUS.md', 'DEVELOPMENT_PLAN.md'):
        text = safe_path(root, name).read_text(encoding='utf-8')
        require(plan['next_ready'] in text, f'{name} NEXT_READY mismatch')
    package_text = safe_path(root, 'docs/L0_L2_WORK_PACKAGES.md').read_text(encoding='utf-8')
    for row in plan['packages']:
        require(f"## {row['id']} " in package_text, f"missing package detail: {row['id']}")
    fingerprints = {}
    for path in files:
        relative = path.relative_to(root).as_posix()
        data = path.read_bytes()
        fingerprints[relative] = hashlib.sha256(data).hexdigest()
        if path.suffix == '.md':
            for link in re.findall(r'\]\(([^)]+)\)', data.decode('utf-8')):
                if link.startswith(('https://', 'http://', '#', 'mailto:')):
                    continue
                target = link.split('#')[0]
                if not target:
                    continue
                combined = (path.parent / target).resolve()
                require(combined.is_relative_to(root), f'out-of-bound local doc link: {relative}')
                require(combined.exists(), f'broken doc link: {relative}: {target}')
    digest = hashlib.sha256(json.dumps(fingerprints, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return {'check': 'L0_PLANNING_ONLY', 'package_count': len(plan['packages']),
            'capability_candidates': len(load_json(root, 'contracts/capabilities.json')['capabilities']),
            'next_ready': plan['next_ready'], 'product_content_sha256': digest,
            'file_count': len(files), 'provider_calls': 0, 'efficacy': 'NOT_TESTED'}


if __name__ == '__main__':
    import sys
    try:
        print(json.dumps(validate_tree(Path(__file__).resolve().parents[1]), ensure_ascii=False, indent=2))
    except (PlanningError, ValueError, KeyError, TypeError, OSError) as exc:
        print(f'PLANNING CHECK FAILED: {exc}', file=sys.stderr)
        raise SystemExit(1)
