"""Exact-head same-engine migration/rollback witness with real legacy objects."""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

from hcl import HCL
from hcl.compat import CognitionWorkspace
from hcl.cognition.core import ClaimKind, Scope
from hcl.cognition.workspace import CognitionWorkspace as LegacyWorkspace
from hcl.kernel.types import FormalProblem, thaw
from hcl.memory.migrations.legacy import LegacyAdapter
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.types import LegacySnapshot
from hcl.kernel.types import Principal
from hcl.v1.narrative import prepare_narrative


def witness():
    owner = Principal('synthetic', 'owner')
    legacy = LegacyWorkspace()
    legacy.put_source('source', 'Alex said: “A report is not proof.”\r\n')
    scope = Scope(actor='Alex', source_ids=('source',))
    claim = legacy.core.claim(scope, ClaimKind.SYSTEM_INTERPRETATION, {'hypothesis': 'conditional interpretation'})
    legacy.core.support(claim, legacy._spans['source'])
    legacy.core.interpret(claim, unknown_conditions=('world_truth_not_established',))
    snapshot = LegacyAdapter.workspace(legacy)
    problem = FormalProblem(('Fa',), 'Ga', {'domain': [0], 'constants': {'a': 0}, 'predicates': {'F': [0], 'G': []}})
    events, _, _, _ = prepare_narrative('Alex attended the meeting.', 'Why did Alex attend?')
    snapshot = LegacySnapshot(tuple(replace(source, formal_problem=problem) for source in snapshot.sources),
                              snapshot.records + tuple(LegacyAdapter.event(e, provenance='v1.prepare_narrative') for e in events),
                              snapshot.origin)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'migration'
        ns = MigrationNamespace.import_snapshot(path, snapshot, namespace_id='witness', owner=owner)
        receipt = ns.receipt(owner)
        imported_id = next(iter(receipt['source_mapping'].values()))['source_id']
        store = ns.open_store()
        facade = CognitionWorkspace(store, principal=owner, session_id=receipt['session_id'])
        request = facade.prepare('Check the explicitly supplied model.', source_ids=(imported_id,),
                                 issue_kind='logic.check_interpretation', request_id='formal')
        result = HCL(store, principal=owner).run_sync(request)
        assert result.status == 'COMPLETED'
        values = next(iter(result.execution_receipt['inference_values'].values()))
        assert values['conclusion'] is False and values['is_countermodel'] is True
        assert 'conclusion is false' in result.answer
        old_view = ns.legacy_view(owner)
        before = ns.audit(owner)
        again = MigrationNamespace.import_snapshot(path, snapshot, namespace_id='witness', owner=owner)
        assert again.audit(owner) == before
        store.close()
        store = ns.open_store()
        replay = HCL(store, principal=owner).run_sync(request)
        assert replay.answer == result.answer and replay.execution_receipt['replayed']
        rollback = ns.rollback(owner, expected_generation=1)
        fenced = HCL(store, principal=owner).run_sync(request)
        assert fenced.status == 'DENIED' and fenced.answer == ''
        assert ns.legacy_view(owner) == old_view and ns.audit(owner)['counts'] == before['counts']
        interpretation = next(row for row in receipt['records'] if row['kind'] == 'SYSTEM_INTERPRETATION')
        assert interpretation['truth'] == 'NOT_ESTABLISHED' and not interpretation['converted']['interpretation_executable']
        order = next(row for row in receipt['records'] if row['kind'] == 'ORDER_EVENT')
        assert order['converted']['time_kind'] == 'SOURCE_ORDER'
        store.close()
    root = Path(__file__).resolve().parents[1]
    return dict(schema='hcl-unified-s1.3-witness-1', slice='S1.3', readiness='INTEGRATED_OFFLINE', stage_complete=False,
        checked_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        runtime_files_sha256={str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in sorted((root/'hcl').rglob('*.py'))},
        provider_calls=0, provider_spend_usd='0', sealed_content_reads=0,
        scope='BOUNDED_TYPED_IMPORT_COMPATIBILITY_AND_TERMINAL_READ_ONLY_ROLLBACK',
        actual_values=thaw(values), answer=result.answer, legacy_grounded_remains_not_truth=True,
        source_order_is_not_calendar=True, import_idempotent_event_counts=thaw(before['counts']),
        replay_answer_equal=True, rollback=thaw(rollback), old_connection_replay_status=fenced.status,
        original_view_unchanged=True, isolated_new_ledger_retained=True,
        not_established=['full S1 and T20/T24/T30 families', 'S5 global legacy cutover', 'automatic reactivation',
                         'ordinary-language compilation', 'LIVE_FUNCTIONAL', 'EFFECT_CONFIRMED'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
    print('S1.3_REAL_IMPORTED_VALUES; IDEMPOTENT; LEGACY_NOT_TRUTH; ROLLBACK_FENCED; STAGE_COMPLETE=FALSE')
