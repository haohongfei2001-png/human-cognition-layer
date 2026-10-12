"""Synthetic local reference-erasure witness, not a real user-data operation.

Records actual inference/accounting and scoped original behavior. It does not
prove external-copy deletion, personal-memory semantics or full M10 acceptance.
"""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

import hcl
from hcl import HCL
from hcl.kernel.types import FormalProblem, HCLFailure, Issue, Principal, TaskRequest, thaw
from hcl.memory import codec
from hcl.memory.governance import verify_inventory
from hcl.memory.migrations.compile import source_key
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.revision_upgrade import RevisionCutover
from hcl.memory.migrations.types import LegacyRecord, LegacySnapshot, LegacySource
from hcl.memory.store import StateStore
from hcl.runtime.budget import TaskBudgetLedger


def witness():
    rows = []
    owner = Principal('synthetic-witness', 'owner')
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root/'current'/'state.sqlite'
        store = StateStore.sqlite(path, revision=True)
        store.create_session('s', owner)
        try:
            text = 'DISPOSABLE_ERASURE_CANARY'
            handle = store.put_source('s', owner, 'A', text, formal_problem=FormalProblem(
                ('Fa',), 'Ga', {'domain':[0], 'constants':{'a':0}, 'predicates':{'F':[0], 'G':[]}}))
            other = store.put_source('s', owner, 'B', 'INDEPENDENT_SYNTHETIC_ORIGINAL')
            request = TaskRequest('logic', 'Check the explicit finite interpretation.', (handle,), 's', owner,
                                  issue=Issue('logic', 'logic.check_interpretation', 'A'))
            result = HCL(store, principal=owner).run_sync(request)
            assert result.status == 'COMPLETED' and result.claim_records
            values = next(iter(result.execution_receipt['inference_values'].values()))
            assert values['is_countermodel'] is True
            b_request = replace(request, request_id='B', source_handles=(other,), issue=Issue('B', 'source.report', 'B'))
            b_result = HCL(store, principal=owner).run_sync(b_request)
            assert b_result.status == 'COMPLETED'
            snapshot = store.snapshot('s', owner, (handle,))
            unknown = replace(request, request_id='unknown', issue=Issue('m', 'model.respond'),
                              budget=replace(request.budget, max_mock_calls=1))
            ledger = TaskBudgetLedger(store)
            lease, _ = ledger.bind(unknown, snapshot)
            ledger.reserve(lease, snapshot, unknown.question, unknown.budget, 'response', 'SYNTHETIC_WIRE')
            ledger.transition(lease, 'response', 'RESERVED', 'SEND_STARTED', snapshot=snapshot)
            count = store._db.execute('SELECT count(*) FROM events').fetchone()[0]
            plan = store.plan_source_erasure('s', owner, 'A', expected_version=1)
            assert store._db.execute('SELECT count(*) FROM events').fetchone()[0] == count
            assert plan['accounting_to_preserve']['unknown_calls'] == 1
            store.begin_source_erasure('s', owner, 'A', expected_version=1, plan_hash=plan['plan_hash'], erasure_id='1'*32)
            try:
                ledger.transition(lease, 'response', 'SEND_STARTED', 'RETURNED', response='LATE_SYNTHETIC_RETURN')
                raise AssertionError('late return unexpectedly accepted')
            except HCLFailure as failure:
                assert failure.diagnostic.code == 'CONTENT_ERASED'
                assert failure.resource_usage['mock_calls'] is None
            receipt = store.resume_source_erasure('s', owner, '1'*32)
            assert receipt['status'] == 'LOCAL_REFERENCE_ERASURE_COMPLETE'
            verify_inventory(store._db)
            store.rebuild_projections()
            store.close();store=StateStore.sqlite(path)
            blocked = HCL(store, principal=owner).run_sync(request)
            unknown_result = HCL(store, principal=owner).run_sync(unknown)
            b_replay = HCL(store, principal=owner).run_sync(b_request)
            assert blocked.status == unknown_result.status == 'DENIED'
            assert not blocked.answer and not blocked.claim_records
            assert unknown_result.usage['mock_calls'] is None and unknown_result.usage['held_mock_calls'] == 1
            assert b_replay.answer == b_result.answer and b_replay.execution_receipt['replayed']
            scanned = 0
            for item in path.parent.rglob('*'):
                if item.is_file():
                    assert text.encode() not in item.read_bytes()
                    scanned += 1
            rows.append(dict(case='computed_reference_closure_and_no_resend',
                actual_countermodel=True, original_usage=thaw(result.usage), denied_usage=thaw(blocked.usage),
                unknown_usage=thaw(unknown_result.usage), receipt=receipt,
                independent_replay_equal=True, scanned_synthetic_managed_files=scanned))
        finally:
            store.close()
        imported = MigrationNamespace.import_snapshot(root/'legacy', LegacySnapshot(
            (LegacySource('A',1,'SYNTHETIC_LEGACY_A'), LegacySource('B',1,'B_LEGACY_ORIGINAL','WITHDRAWN')),
            (LegacyRecord('opaque','CUSTOM_OLD_KIND',{'text':'UNKNOWN_SYNTHETIC_PROVENANCE'}),)),
            namespace_id='scoped', owner=owner)
        original = imported.receipt(owner)
        target = RevisionCutover.upgrade(imported.path, root/'scoped', owner)
        current = target.open_store()
        try:
            session = original['session_id']
            a = original['source_mapping'][source_key('A',1)]['source_id']
            b = original['source_mapping'][source_key('B',1)]['source_id']
            current.prepare_legacy_capsules(session, owner)
            before = current.legacy_source_view(session, owner, (b,))
            plan = current.plan_source_erasure(session, owner, a, expected_version=1)
            current.begin_source_erasure(session, owner, a, expected_version=1,
                plan_hash=plan['plan_hash'], erasure_id='2'*32)
            receipt = current.resume_source_erasure(session, owner, '2'*32)
            assert receipt['status'] == 'PARTIAL_ERASURE_RETAINED_COPIES'
            assert set(receipt['limitations']) == {'UNKNOWN_LEGACY_PROVENANCE_RETAINED','PREDECESSOR_COPY_RETAINED'}
            current.rebuild_projections()
            target.rollback(owner)
            assert current.legacy_source_view(session, owner, (b,)) == before
            rows.append(dict(case='scoped_legacy_originals_and_honest_retained_copies',
                independent_original_exact_after_rollback=True, receipt=receipt,
                old_disposition='WITHDRAWN_NOT_RECLASSIFIED'))
        finally:
            current.close()
    root = Path(hcl.__file__).resolve().parents[1]
    return dict(schema='hcl-unified-memory-governance-witness-1',
        checked_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        runtime_hashes={str(path.relative_to(root)):sha256(path.read_bytes()).hexdigest() for path in sorted((root/'hcl').rglob('*.py'))},
        rows=rows,provider_calls=0,provider_spend_usd=0,sealed_content_reads=0,
        evidence_scope='SYNTHETIC_CURRENT_NAMESPACE_REFERENCE_ERASURE_AND_SCOPED_ORIGINALS',
        not_established=['REAL_USER_DATA_ERASURE','EXTERNAL_COPY_ERASURE','DEVICE_REMANENCE_ERASURE',
            'UNKNOWN_LEGACY_PROVENANCE_ERASURE','LAYERED_PERSONAL_DOMAIN_MEMORY','FULL_M10','FULL_T22','FULL_T24','FULL_T27','FULL_S4','LIVE_EFFECT'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    args.output.write_text(json.dumps(witness(),ensure_ascii=False,sort_keys=True,indent=2)+'\n')
