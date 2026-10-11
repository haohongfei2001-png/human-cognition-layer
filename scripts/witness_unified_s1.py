"""Reproducible synthetic S1.1 result-consumption witness; zero providers."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from hcl import HCL, TaskRequest
from hcl.kernel.types import FormalProblem, Issue, Principal, thaw
from hcl.memory.store import StateStore


def witness():
    store = StateStore()
    principal = Principal('synthetic-tenant', 'synthetic-owner')
    store.create_session('synthetic-session', principal)
    client = HCL(store, principal=principal)
    cases = []
    for name, extension in [('counterexample', []), ('opposite-input', [0])]:
        problem = FormalProblem(('∀x(Fx→Gx)', 'Ga'), 'Fa', {
            'domain': [0], 'constants': {'a': 0}, 'predicates': {'F': extension, 'G': [0]}})
        handle = store.put_source('synthetic-session', principal, 'formal',
                                 'Synthetic explicit finite model.', formal_problem=problem)
        result = client.run_sync(TaskRequest(name, 'Does this supplied interpretation refute the inference?',
            (handle,), 'synthetic-session', principal,
            issue=Issue('check-counterexample', 'logic.check_interpretation', 'formal')))
        assert result.status == 'COMPLETED'
        values = next(iter(result.execution_receipt['inference_values'].values()))
        assert values['conclusion'] == bool(extension)
        assert values['is_countermodel'] == (not extension)
        cases.append({'name': name, 'answer': result.answer, 'values': thaw(values),
                      'used_result_fields': [
                          {'result_id': ref.result_id, 'field': ref.field, 'value': thaw(ref.value)}
                          for ref in result.claim_records[0].used_result_fields],
                      'receipt': thaw(result.execution_receipt)})
    assert cases[0]['answer'] != cases[1]['answer']
    before = store.snapshot('synthetic-session', principal, (handle,))
    store.set_readers('synthetic-session', principal, 'formal', frozenset())
    denied = client.run_sync(TaskRequest('revoked', 'Show source', (handle,), 'synthetic-session', principal))
    assert denied.status == 'DENIED' and not denied.answer
    root = Path(__file__).resolve().parents[1]
    paths = [root/'hcl/__init__.py', root/'hcl/api.py', root/'hcl/quantified_logic.py']
    for package in ('kernel', 'memory', 'models', 'operators', 'runtime'):
        paths.extend(sorted((root/'hcl'/package).glob('*.py')))
    return {
        'schema': 'hcl-unified-s1.1-witness-1',
        'checked_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'runtime_files_sha256': {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in paths},
        'slice': 'S1.1', 'readiness': 'INTEGRATED_OFFLINE', 'stage_complete': False,
        'provider_calls': 0, 'provider_spend_usd': '0', 'sealed_content_reads': 0,
        'scope': 'EXPLICIT_FINITE_MODEL_AND_CONTROL_CONTRACTS_ONLY',
        'cases': cases, 'revoked_source_status': denied.status,
        'durable_store': store.durable, 'access_epoch_before_revocation': before.access_epoch,
        'not_established': ['S1.2 persistence/recovery', 'S1.3 migration/compatibility',
                            'full T20/T21/T22/T28 acceptance families', 'ordinary-language compilation',
                            'LIVE_FUNCTIONAL', 'EFFECT_CONFIRMED'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = witness()
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print('S1.1_REAL_FINITE_VALUES_CONSUMED; ACL_DENIED; PROVIDER_CALLS=0; STAGE_COMPLETE=FALSE')
