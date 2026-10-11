"""Exact-head offline witness for persistent real values and no-resend recovery."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from hcl import HCL, TaskRequest
from hcl.kernel.types import BudgetSlice, FormalProblem, Issue, Principal, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort


def witness():
    principal = Principal('synthetic-tenant', 'synthetic-owner')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'state.sqlite'
        store = StateStore.sqlite(path)
        store.create_session('session', principal)
        problem = FormalProblem(('Fa',), 'Ga', {'domain': [0], 'constants': {'a': 0}, 'predicates': {'F': [0], 'G': []}})
        handle = store.put_source('session', principal, 'formal', 'Synthetic source-bound model.', formal_problem=problem)
        request = TaskRequest('positive', 'Does this supplied interpretation refute the inference?', (handle,),
                              'session', principal, issue=Issue('logic', 'logic.check_interpretation', 'formal'))
        first = HCL(store, principal=principal).run_sync(request)
        assert first.status == 'COMPLETED'
        first_values = next(iter(first.execution_receipt['inference_values'].values()))
        assert first_values['is_countermodel'] is True
        store.close()
        store = StateStore.sqlite(path)
        replay = HCL(store, principal=principal).run_sync(request)
        assert replay.answer == first.answer and replay.claim_records == first.claim_records
        assert replay.execution_receipt['replayed'] and replay.usage['replay_new_mock_calls'] == 0
        rebuilt = store.rebuild_projections()
        assert rebuilt['inferences'] == rebuilt['tasks'] == 1
        opposite = replace(problem, interpretation={'domain': [0], 'constants': {'a': 0}, 'predicates': {'F': [0], 'G': [0]}})
        handle = store.put_source('session', principal, 'formal', 'Opposite explicit model.', formal_problem=opposite)
        second = HCL(store, principal=principal).run_sync(replace(request, request_id='opposite', source_handles=(handle,)))
        second_values = next(iter(second.execution_receipt['inference_values'].values()))
        assert second.status == 'COMPLETED' and second_values['is_countermodel'] is False
        assert second.answer != first.answer
        port = OfflineModelPort(fault='send_unknown')
        unknown_request = replace(request, request_id='unknown', source_handles=(handle,),
                                  issue=Issue('mock', 'model.respond'), budget=BudgetSlice(max_mock_calls=1))
        unknown = HCL(store, principal=principal, gateway=ModelGateway(store, port)).run_sync(unknown_request)
        assert unknown.status == 'SEND_UNKNOWN' and unknown.usage['mock_calls'] is None
        assert unknown.usage['held_mock_calls'] == 1 and port.attempts == 1
        store.close()
        store = StateStore.sqlite(path)
        replacement_port = OfflineModelPort()
        recovered = HCL(store, principal=principal, gateway=ModelGateway(store, replacement_port)).run_sync(unknown_request)
        assert recovered.status == 'SEND_UNKNOWN' and replacement_port.attempts == 0
        assert recovered.execution_receipt['replayed'] and recovered.usage['mock_usage_unknown']
        store.set_readers('session', principal, 'formal', frozenset())
        denied = HCL(store, principal=principal).run_sync(unknown_request)
        assert denied.status == 'DENIED' and not denied.answer
        store.close()
    root = Path(__file__).resolve().parents[1]
    paths = [root/'hcl/__init__.py', root/'hcl/api.py', root/'hcl/quantified_logic.py']
    for package in ('kernel', 'memory', 'models', 'operators', 'runtime'):
        paths.extend(sorted((root/'hcl'/package).glob('*.py')))
    return {
        'schema': 'hcl-unified-s1.2-witness-1',
        'checked_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'runtime_files_sha256': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'slice': 'S1.2', 'readiness': 'INTEGRATED_OFFLINE', 'stage_complete': False,
        'provider_calls': 0, 'provider_spend_usd': '0', 'sealed_content_reads': 0,
        'scope': 'SAME_FINITE_COMPUTATION_DURABILITY_AND_SIMULATED_CALL_ACCOUNTING_ONLY',
        'durable_store': True, 'replay_answer_equal': first.answer == replay.answer,
        'replay_claim_records_equal': first.claim_records == replay.claim_records,
        'projection_rebuild_counts': rebuilt,
        'cases': [{'name': name, 'answer': result.answer, 'values': thaw(values),
                   'receipt': thaw(result.execution_receipt),
                   'used_result_fields': [{'field': ref.field, 'value': thaw(ref.value)} for ref in result.claim_records[0].used_result_fields]}
                  for name, result, values in [('counterexample', first, first_values), ('opposite', second, second_values)]],
        'unknown_usage': thaw(unknown.usage), 'unknown_restart_status': recovered.status,
        'restart_new_mock_attempts': replacement_port.attempts, 'revoked_replay_status': denied.status,
        'not_established': ['S1.3 migration/compatibility', 'full T21/T22/T28/T29 families',
                            'ordinary-language compilation', 'LIVE_FUNCTIONAL', 'EFFECT_CONFIRMED'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print('S1.2_REAL_VALUES_DURABLE; REPLAY_EQUAL; UNKNOWN_HELD_NO_RESEND; ACL_DENIED; STAGE_COMPLETE=FALSE')
