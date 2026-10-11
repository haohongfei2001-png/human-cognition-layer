"""Real finite computation, durable restart, independent connections and faults.

All sources are synthetic. The only model port is the built-in offline fixture.
No provider, evaluation corpus, SDK, credentials, or network is needed.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import BudgetSlice, FormalProblem, HCLFailure, Issue, Principal, SourceHandle, TaskRequest, TaskResult
from hcl.memory.store import StateStore
from hcl.memory.sqlite_store import SQLiteStateStore
from hcl.models.gateway import AuthorizedContext, CallSpec, ModelGateway, OfflineModelPort
from hcl.operators.logic import FiniteLogicOperator
from hcl.runtime.budget import TaskBudgetLedger
from hcl.runtime.recovery import RecoveryManager


class Crash(BaseException):
    pass


class DurableRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name)/'state.sqlite'
        self.connections = []
        self.store = self.open()
        self.alice = Principal('tenant', 'alice')
        self.bob = Principal('tenant', 'bob')
        self.store.create_session('session', self.alice, frozenset({'bob'}))
        self.problem = FormalProblem(('Fa',), 'Ga', {
            'domain': [0], 'constants': {'a': 0}, 'predicates': {'F': [0], 'G': []}})
        self.handle = self.store.put_source('session', self.alice, 'source', 'PRIVATE_SYNTHETIC_SOURCE_CANARY',
                                           formal_problem=self.problem)

    def open(self):
        store = StateStore.sqlite(self.path)
        self.connections.append(store)
        return store

    def tearDown(self):
        for store in self.connections:
            try:
                store.close()
            except sqlite3.ProgrammingError:
                pass
        self.temporary.cleanup()

    def request(self, **changes):
        request = TaskRequest('request', 'Does this model refute the conclusion?', (self.handle,),
                              'session', self.alice, issue=Issue('check', 'logic.check_interpretation', 'source'))
        return replace(request, **changes)

    def model_request(self, **changes):
        return self.request(**dict(dict(issue=Issue('light', 'model.respond'), budget=BudgetSlice(max_mock_calls=1)), **changes))

    def snapshot(self, store=None):
        return (store or self.store).snapshot('session', self.alice, (self.handle,))

    def bind(self, request=None):
        request = request or self.model_request()
        snapshot = self.store.snapshot(request.session_id, request.principal, request.source_handles)
        ledger = TaskBudgetLedger(self.store)
        lease, replay = ledger.bind(request, snapshot)
        self.assertIsNone(replay)
        return ledger, lease, snapshot, request

    def test_original_logic_is_persisted_and_replayed_after_reopen(self):
        first = HCL(self.store, principal=self.alice).run_sync(self.request())
        self.assertEqual(first.status, 'COMPLETED')
        self.assertTrue(first.execution_receipt['store_durable'])
        result_id = first.claim_records[0].used_result_fields[0].result_id
        self.assertTrue(first.execution_receipt['inference_values'][result_id]['is_countermodel'])
        reopened = self.open()
        with patch.object(FiniteLogicOperator, 'run', side_effect=AssertionError('must reuse committed result')):
            second = HCL(reopened, principal=self.alice).run_sync(self.request())
        self.assertEqual(first.answer, second.answer)
        self.assertEqual(first.claim_records, second.claim_records)
        self.assertTrue(second.execution_receipt['replayed'])
        self.assertEqual(second.usage['replay_new_mock_calls'], 0)
        self.assertEqual(first.state_revision, second.state_revision)
        self.assertEqual(reopened.inferences('session', self.alice)[0].result_id, result_id)

    def test_opposite_model_after_restart_changes_real_answer(self):
        first = HCL(self.store, principal=self.alice).run_sync(self.request())
        reopened = self.open()
        opposite = replace(self.problem, interpretation={'domain': [0], 'constants': {'a': 0}, 'predicates': {'F': [0], 'G': [0]}})
        handle = reopened.put_source('session', self.alice, 'source', 'changed explicit model', formal_problem=opposite)
        second = HCL(reopened, principal=self.alice).run_sync(self.request(request_id='opposite', source_handles=(handle,)))
        self.assertEqual(second.status, 'COMPLETED')
        self.assertNotEqual(first.answer, second.answer)
        values = next(iter(second.execution_receipt['inference_values'].values()))
        self.assertFalse(values['is_countermodel'])

    def test_projection_rebuild_preserves_sources_inferences_tasks_and_calls(self):
        formal = HCL(self.store, principal=self.alice).run_sync(self.request())
        port = OfflineModelPort('durable offline text')
        model = HCL(self.store, principal=self.alice, gateway=ModelGateway(self.store, port)).run_sync(self.model_request(request_id='mock'))
        self.assertEqual(model.status, 'COMPLETED')
        before = self.snapshot()
        with self.store._transaction(True) as db:
            for table in ('sessions', 'sources', 'inferences', 'tasks', 'calls'):
                db.execute('DELETE FROM ' + table)
        counts = self.store.rebuild_projections()
        self.assertEqual(counts, dict(sessions=1, sources=1, inferences=1, tasks=2, calls=1))
        self.assertEqual(before, self.snapshot())
        replay = HCL(self.open(), principal=self.alice).run_sync(self.request())
        self.assertEqual(replay.answer, formal.answer)
        self.assertTrue(replay.execution_receipt['replayed'])

    def test_real_process_exit_after_send_started_recovers_without_resend(self):
        code = """
import os, socket, sys, json
from pathlib import Path
class NoSDK:
    def find_spec(self, name, *args):
        if name.split('.')[0] in ('openai', 'requests', 'httpx'):
            raise AssertionError('NO_PROVIDER_SDK')
sys.meta_path.insert(0, NoSDK())
def deny(*args, **kwargs):
    raise AssertionError('NO_NETWORK')
socket.create_connection = socket.getaddrinfo = socket.socket.connect = deny
from hcl import HCL
from hcl.kernel.types import Principal, TaskRequest, SourceHandle, Issue, BudgetSlice
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
store = StateStore.sqlite(sys.argv[1])
port = OfflineModelPort('never delivered')
request = TaskRequest('process-crash', 'Does this model refute the conclusion?', (SourceHandle('source', 1),),
    'session', Principal('tenant', 'alice'), issue=Issue('light', 'model.respond'), budget=BudgetSlice(max_mock_calls=1))
def checkpoint(stage):
    if stage == 'send_started':
        Path(sys.argv[2]).write_text(json.dumps(dict(owner=store.owner_id, attempts=port.attempts)))
        os._exit(7)
store._checkpoint = checkpoint
HCL(store, principal=request.principal, gateway=ModelGateway(store, port)).run_sync(request)
raise AssertionError('crash not exercised')
"""
        marker = Path(self.temporary.name)/'crash-marker.json'
        process = subprocess.run([sys.executable, '-B', '-c', code, str(self.path), str(marker)],
                                 cwd=Path(__file__).resolve().parents[1], capture_output=True,
                                 env={'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1'}, timeout=30)
        self.assertEqual(process.returncode, 7, process.stderr.decode())
        observed = json.loads(marker.read_text())
        self.assertEqual(observed['attempts'], 0)
        reopened = self.open()
        recovery = RecoveryManager(reopened)
        self.assertEqual(recovery.pending(self.alice, 'session')[0]['owner_id'], observed['owner'])
        recovery.recover_abandoned(self.alice, 'session', 'process-crash', expected_owner_id=observed['owner'])
        self.assertEqual(TaskBudgetLedger(reopened).state(self.alice, 'session', 'process-crash'), 'UNKNOWN')
        port = OfflineModelPort()
        result = HCL(reopened, principal=self.alice, gateway=ModelGateway(reopened, port)).run_sync(self.model_request(request_id='process-crash'))
        self.assertEqual(result.diagnostics[0].code, 'TASK_INTERRUPTED_NO_RESEND')
        self.assertEqual(port.attempts, 0)

    def test_event_metadata_has_no_plain_source_question_or_raw_response(self):
        port = OfflineModelPort('RAW_RETURN_PRIVATE_CANARY')
        request = self.model_request(question='PRIVATE_QUESTION_CANARY')
        result = HCL(self.store, principal=self.alice, gateway=ModelGateway(self.store, port)).run_sync(request)
        self.assertEqual(result.status, 'COMPLETED')
        rows = self.store._db.execute('SELECT payload FROM events').fetchall()
        metadata = json.dumps([row[0] for row in rows])
        for canary in ('PRIVATE_SYNTHETIC_SOURCE_CANARY', 'RAW_RETURN_PRIVATE_CANARY', 'PRIVATE_QUESTION_CANARY'):
            self.assertNotIn(canary, metadata)

    def test_torn_source_transactions_do_not_publish_half_state(self):
        for stage in ('object_persisted', 'event_appended', 'projection_updated', 'before_commit'):
            with self.subTest(stage=stage):
                def stop(current):
                    if current == stage:
                        raise Crash(stage)
                with patch.object(self.store, '_checkpoint', stop), self.assertRaises(Crash):
                    self.store.put_source('session', self.alice, 'source', 'never committed', formal_problem=self.problem)
                reopened = self.open()
                self.assertEqual(self.snapshot(reopened).immutable_views['source'].text, 'PRIVATE_SYNTHETIC_SOURCE_CANARY')
                self.assertEqual(reopened.rebuild_projections()['sources'], 1)
                self.assertEqual(self.snapshot(reopened).revision, 1)

    def test_object_corruption_and_event_corruption_fail_closed(self):
        row = self.store._db.execute('SELECT object_hash FROM sources').fetchone()
        path = self.store.object_root/row[0]
        body = path.read_bytes()
        path.write_bytes(b'corrupt')
        result = HCL(self.store, principal=self.alice).run_sync(self.request())
        self.assertEqual(result.status, 'FAILED')
        self.assertEqual(result.diagnostics[0].code, 'STATE_CORRUPT')
        self.assertEqual(result.answer, '')
        with self.assertRaises(HCLFailure):
            self.store.rebuild_projections()
        path.write_bytes(body)
        self.store._db.execute("UPDATE events SET event_hash='bad' WHERE seq=1")
        with self.assertRaises(HCLFailure):
            self.store.rebuild_projections()
        self.assertEqual(self.snapshot().revision, 1)  # Failed rebuild rolled back.

    def test_future_store_schema_cannot_be_written_by_old_code(self):
        self.store._db.execute('PRAGMA user_version=999')
        with self.assertRaisesRegex(ValueError, 'unsupported store schema'):
            SQLiteStateStore(self.path)

    def test_unrelated_revisions_rebase_disjoint_inference_appends(self):
        snapshot = self.snapshot()
        operator = FiniteLogicOperator()
        a = operator.run(snapshot, Issue('a', 'logic.check_interpretation', 'source'), BudgetSlice())
        b = operator.run(snapshot, Issue('b', 'logic.check_interpretation', 'source'), BudgetSlice())
        peer = self.open()
        peer.put_source('session', self.alice, 'unrelated', 'unrelated revision')
        first = self.store.commit(snapshot.revision, a.read_set, snapshot.access_epoch, a.candidate_delta)
        second = peer.commit(snapshot.revision, b.read_set, snapshot.access_epoch, b.candidate_delta)
        self.assertEqual((first.revision, second.revision), (3, 4))
        self.assertEqual(len(self.store.inferences('session', self.alice)), 2)
        rows = self.store._db.execute('SELECT base_revision,commit_revision FROM inferences ORDER BY commit_revision').fetchall()
        self.assertEqual([tuple(row) for row in rows], [(1, 3), (1, 4)])

    def test_engine_rebases_only_actual_read_set_and_replays_after_unused_change(self):
        unused = self.store.put_source('session', self.alice, 'unused', 'not consumed by logic')
        request = self.request(source_handles=(self.handle, unused))
        peer = self.open()
        original = FiniteLogicOperator.run
        def changed(operator, snapshot, issue, allowance):
            operation = original(operator, snapshot, issue, allowance)
            peer.put_source('session', self.alice, 'unused', 'concurrent unrelated update')
            return operation
        with patch.object(FiniteLogicOperator, 'run', changed):
            result = HCL(self.store, principal=self.alice).run_sync(request)
        self.assertEqual(result.status, 'COMPLETED')
        self.assertEqual(dict(result.execution_receipt['read_set']), {'source': 1})
        self.assertEqual((result.execution_receipt['base_revision'], result.execution_receipt['commit_revision']), (2, 4))
        replay = HCL(self.open(), principal=self.alice).run_sync(request)
        self.assertEqual(replay.answer, result.answer)
        self.assertTrue(replay.execution_receipt['replayed'])

    def test_related_change_and_acl_restore_still_reject(self):
        snapshot = self.snapshot()
        op = FiniteLogicOperator().run(snapshot, self.request().issue, BudgetSlice())
        peer = self.open()
        peer.put_source('session', self.alice, 'source', 'changed', formal_problem=self.problem)
        with self.assertRaises(HCLFailure) as caught:
            self.store.commit(snapshot.revision, op.read_set, snapshot.access_epoch, op.candidate_delta)
        self.assertEqual(caught.exception.diagnostic.code, 'READ_SET_CHANGED')
        peer.set_readers('session', self.alice, 'source', frozenset({'bob'}))
        peer.set_readers('session', self.alice, 'source', frozenset({'alice', 'bob'}))
        with self.assertRaises(HCLFailure) as caught:
            self.store.validate_snapshot(snapshot)
        self.assertEqual(caught.exception.diagnostic.code, 'ACCESS_EPOCH_CHANGED')

    def test_future_revision_boolean_versions_and_index_claim_reject(self):
        snapshot = self.snapshot()
        op = FiniteLogicOperator().run(snapshot, self.request().issue, BudgetSlice())
        for change in ({'base_revision': 500}, {'read_set': {'source': True}}, {'rule_version': 'future'}):
            delta = replace(op.candidate_delta, **change)
            with self.subTest(change=change), self.assertRaises(HCLFailure):
                self.store.commit(delta.base_revision, delta.read_set, delta.access_epoch, delta)
        with self.assertRaises(HCLFailure):
            self.store.validate_snapshot(replace(snapshot, index_versions={'unsupported-index': 1}))
        self.assertEqual(len(self.store.inferences('session', self.alice)), 0)

    def test_two_connections_cannot_overwrite_same_inference(self):
        snapshot = self.snapshot()
        op = FiniteLogicOperator().run(snapshot, self.request().issue, BudgetSlice())
        peer = self.open()
        barrier = Barrier(2)
        def write(store):
            barrier.wait()
            try:
                store.commit(snapshot.revision, op.read_set, snapshot.access_epoch, op.candidate_delta)
                return 'COMMITTED'
            except HCLFailure as error:
                return error.diagnostic.code
        with ThreadPoolExecutor(2) as executor:
            outcomes = list(executor.map(write, (self.store, peer)))
        self.assertCountEqual(outcomes, ['COMMITTED', 'RESULT_ID_COLLISION'])
        self.assertEqual(len(self.store.inferences('session', self.alice)), 1)

    def test_task_budget_shared_by_two_gateways_and_independent_connections(self):
        ledger, lease, snapshot, request = self.bind()
        stores = [self.store, self.open()]
        ports = [OfflineModelPort('first'), OfflineModelPort('second')]
        barrier = Barrier(2)
        def call(index):
            barrier.wait()
            gateway = ModelGateway(stores[index], ports[index])
            try:
                asyncio.run(gateway.generate(AuthorizedContext(snapshot, request.question),
                    CallSpec(request.request_id, request.budget, lease, 'branch-' + str(index))))
                return 'RETURNED'
            except HCLFailure as error:
                return error.diagnostic.code
        with ThreadPoolExecutor(2) as executor:
            outcomes = list(executor.map(call, (0, 1)))
        self.assertCountEqual(outcomes, ['RETURNED', 'MOCK_CALL_BUDGET'])
        self.assertEqual(sum(port.attempts for port in ports), 1)
        self.assertEqual(self.store._db.execute('SELECT count(*) FROM calls').fetchone()[0], 1)

    def test_budget_and_task_input_cannot_be_rebound_or_enlarged(self):
        ledger, lease, snapshot, request = self.bind()
        for changed in (replace(request, question='different'), replace(request, budget=BudgetSlice(max_mock_calls=2))):
            with self.assertRaises(HCLFailure) as caught:
                TaskBudgetLedger(self.open()).bind(changed, snapshot)
            self.assertEqual(caught.exception.diagnostic.code, 'REQUEST_FINGERPRINT_MISMATCH')
        port = OfflineModelPort()
        with self.assertRaises(HCLFailure) as caught:
            asyncio.run(ModelGateway(self.open(), port).generate(AuthorizedContext(snapshot, request.question),
                CallSpec(request.request_id, BudgetSlice(max_mock_calls=10), lease)))
        self.assertEqual(caught.exception.diagnostic.code, 'TASK_CONTEXT_MISMATCH')
        self.assertEqual(port.attempts, 0)

    def test_return_is_persisted_before_output_validation(self):
        ledger, lease, snapshot, request = self.bind(self.model_request(budget=BudgetSlice(max_mock_calls=1, max_output_bytes=2)))
        port = OfflineModelPort('unacceptable complete response')
        with self.assertRaises(HCLFailure):
            asyncio.run(ModelGateway(self.store, port).generate(AuthorizedContext(snapshot, request.question),
                CallSpec(request.request_id, request.budget, lease)))
        row = TaskBudgetLedger(self.open()).call(lease, 'response')
        self.assertEqual(row['state'], 'VALIDATION_REJECTED')
        self.assertEqual(row['attempted'], 1)
        self.assertEqual(self.store._get_object(row['response_hash']), 'unacceptable complete response')
        self.assertEqual(row['validation_code'], 'OUTPUT_BYTES_EXCEEDED')

    def test_restart_usage_aggregates_all_known_and_unknown_branch_holds(self):
        request = self.model_request(budget=BudgetSlice(max_mock_calls=2))
        ledger, lease, snapshot, request = self.bind(request)
        empty = HCL(self.open(), principal=self.alice).run_sync(request)
        self.assertEqual((empty.usage['mock_calls'], empty.usage['held_mock_calls']), (0, 0))
        for call_id, port in (('known', OfflineModelPort()), ('unknown', OfflineModelPort(fault='send_unknown'))):
            try:
                asyncio.run(ModelGateway(self.open(), port).generate(AuthorizedContext(snapshot, request.question),
                    CallSpec(request.request_id, request.budget, lease, call_id)))
            except HCLFailure as error:
                self.assertEqual(error.status, 'SEND_UNKNOWN')
        reopened = self.open()
        for recovered in (False, True):
            if recovered:
                RecoveryManager(reopened).recover_abandoned(self.alice, 'session', request.request_id, expected_owner_id=lease.owner_id)
            result = HCL(reopened, principal=self.alice).run_sync(request)
            self.assertIsNone(result.usage['mock_calls'])
            self.assertEqual(result.usage['observed_mock_calls'], 1)
            self.assertEqual(result.usage['held_mock_calls'], 2)
            self.assertTrue(result.usage['mock_usage_unknown'])

    def test_invalid_return_encoding_is_preserved_without_rewrite(self):
        ledger, lease, snapshot, request = self.bind()
        port = OfflineModelPort('\ud800')
        with self.assertRaises(HCLFailure) as caught:
            asyncio.run(ModelGateway(self.store, port).generate(AuthorizedContext(snapshot, request.question),
                CallSpec(request.request_id, request.budget, lease)))
        self.assertEqual(caught.exception.diagnostic.code, 'INVALID_MODEL_ENCODING')
        row = ledger.call(lease, 'response')
        self.assertEqual(row['state'], 'VALIDATION_REJECTED')
        self.assertEqual(self.store._get_object(row['response_hash']), '\ud800')

    def test_all_offline_faults_persist_without_resend_after_reopen(self):
        for fault, status, attempts, state in (
            ('before_send', 'FAILED', 0, 'FAILED_BEFORE_SEND'),
            ('send_unknown', 'SEND_UNKNOWN', 1, 'UNKNOWN'),
            ('invalid_return', 'FAILED', 1, 'VALIDATION_REJECTED'),
        ):
            with self.subTest(fault=fault):
                request = self.model_request(request_id=fault)
                port = OfflineModelPort(fault=fault)
                first = HCL(self.store, principal=self.alice, gateway=ModelGateway(self.store, port)).run_sync(request)
                self.assertEqual(first.status, status)
                self.assertEqual(first.execution_receipt['mock_call_state'], state)
                self.assertEqual(port.attempts, attempts)
                restarted = self.open()
                new_port = OfflineModelPort()
                second = HCL(restarted, principal=self.alice, gateway=ModelGateway(restarted, new_port)).run_sync(request)
                self.assertEqual(second.status, status)
                self.assertTrue(second.execution_receipt['replayed'])
                self.assertEqual(new_port.attempts, 0)
                if fault == 'send_unknown':
                    self.assertIsNone(first.usage['mock_calls'])
                    self.assertTrue(first.usage['mock_usage_unknown'])
                    self.assertEqual(first.usage['held_mock_calls'], 1)

    def test_crash_boundaries_recover_only_explicitly_and_never_resend(self):
        for stage, expected, attempts in (
            ('call_reserved', 'FAILED_BEFORE_SEND', 0), ('send_started', 'UNKNOWN', 0),
            ('response_received', 'UNKNOWN', 1), ('return_persisted', 'RETURNED', 1),
        ):
            with self.subTest(stage=stage):
                request = self.model_request(request_id=stage)
                port = OfflineModelPort('persist me')
                def stop(current):
                    if current == stage:
                        raise Crash(stage)
                with patch.object(self.store, '_checkpoint', stop), self.assertRaises(Crash):
                    HCL(self.store, principal=self.alice, gateway=ModelGateway(self.store, port)).run_sync(request)
                reopened = self.open()
                replacement = OfflineModelPort()
                client = HCL(reopened, principal=self.alice, gateway=ModelGateway(reopened, replacement))
                pending = client.run_sync(request)
                self.assertEqual(pending.diagnostics[0].code, 'TASK_IN_PROGRESS')
                self.assertEqual(pending.usage['held_mock_calls'], 1)
                self.assertEqual(pending.usage['mock_usage_unknown'], stage in ('send_started', 'response_received'))
                if stage in ('send_started', 'response_received'):
                    self.assertIsNone(pending.usage['mock_calls'])
                recovery = RecoveryManager(reopened)
                with self.assertRaises(HCLFailure):
                    recovery.recover_abandoned(self.alice, 'session', stage, expected_owner_id='wrong')
                recovery.recover_abandoned(self.alice, 'session', stage, expected_owner_id=self.store.owner_id)
                interrupted = client.run_sync(request)
                self.assertEqual(interrupted.diagnostics[0].code, 'TASK_INTERRUPTED_NO_RESEND')
                self.assertEqual(interrupted.usage['held_mock_calls'], 1)
                self.assertEqual(interrupted.usage['mock_usage_unknown'], expected == 'UNKNOWN')
                if expected == 'UNKNOWN':
                    self.assertIsNone(interrupted.usage['mock_calls'])
                self.assertEqual(TaskBudgetLedger(reopened).state(self.alice, 'session', stage), expected)
                self.assertEqual((port.attempts, replacement.attempts), (attempts, 0))

    def test_crash_after_result_commit_replays_once_without_new_call(self):
        request = self.model_request()
        port = OfflineModelPort('durable final')
        def stop(stage):
            if stage == 'task_finished':
                raise Crash(stage)
        with patch.object(self.store, '_checkpoint', stop), self.assertRaises(Crash):
            HCL(self.store, principal=self.alice, gateway=ModelGateway(self.store, port)).run_sync(request)
        reopened = self.open()
        replacement = OfflineModelPort('must not be used')
        result = HCL(reopened, principal=self.alice, gateway=ModelGateway(reopened, replacement)).run_sync(request)
        self.assertEqual(result.answer, 'durable final')
        self.assertTrue(result.execution_receipt['replayed'])
        self.assertEqual((port.attempts, replacement.attempts), (1, 0))

    def test_ledger_failure_before_reservation_means_no_attempt(self):
        ledger, lease, snapshot, request = self.bind()
        port = OfflineModelPort()
        with patch.object(self.store, '_record', side_effect=sqlite3.OperationalError('synthetic write failure')):
            with self.assertRaises(HCLFailure) as caught:
                asyncio.run(ModelGateway(self.store, port).generate(AuthorizedContext(snapshot, request.question),
                    CallSpec(request.request_id, request.budget, lease)))
        self.assertEqual(caught.exception.diagnostic.code, 'STORAGE_FAILURE')
        self.assertEqual(port.attempts, 0)
        self.assertIsNone(ledger.call(lease, 'response'))

    def test_ledger_failure_after_return_retains_unknown_hold_and_no_resend(self):
        ledger, lease, snapshot, request = self.bind()
        port = OfflineModelPort('returned before durable write failed')
        original = self.store._record
        def failure(db, table, record, revision):
            if table == 'calls' and record['state'] == 'RETURNED':
                raise sqlite3.OperationalError('synthetic response persistence failure')
            return original(db, table, record, revision)
        with patch.object(self.store, '_record', failure), self.assertRaises(HCLFailure) as caught:
            asyncio.run(ModelGateway(self.store, port).generate(AuthorizedContext(snapshot, request.question),
                CallSpec(request.request_id, request.budget, lease)))
        self.assertEqual(caught.exception.diagnostic.code, 'STORAGE_FAILURE')
        row = TaskBudgetLedger(self.open()).call(lease, 'response')
        self.assertEqual(row['state'], 'UNKNOWN')
        self.assertIsNone(row['attempted'])
        self.assertEqual(port.attempts, 1)
        with self.assertRaises(HCLFailure):
            asyncio.run(ModelGateway(self.open(), OfflineModelPort()).generate(AuthorizedContext(snapshot, request.question),
                CallSpec(request.request_id, request.budget, lease)))

    def test_object_io_failures_are_safe_results_with_no_attempt(self):
        for operation in ('fsync', 'replace'):
            with self.subTest(operation=operation):
                port = OfflineModelPort()
                client = HCL(self.store, principal=self.alice, gateway=ModelGateway(self.store, port))
                with patch('hcl.memory.sqlite_store.os.' + operation, side_effect=OSError('DISK_PRIVATE_PATH_CANARY')):
                    result = client.run_sync(self.model_request(request_id=operation))
                self.assertEqual(result.status, 'FAILED')
                self.assertEqual(result.diagnostics[0].code, 'STORAGE_FAILURE')
                self.assertEqual(port.attempts, 0)
                self.assertNotIn('DISK_PRIVATE_PATH_CANARY', repr(result))
        original = self.store._put_object
        def fail_result(value):
            if isinstance(value, TaskResult):
                raise OSError('FINISH_PRIVATE_PATH_CANARY')
            return original(value)
        with patch.object(self.store, '_put_object', fail_result):
            result = HCL(self.store, principal=self.alice).run_sync(self.request(request_id='finish-io'))
        self.assertEqual(result.status, 'FAILED')
        self.assertEqual(result.diagnostics[0].code, 'STORAGE_FAILURE')
        self.assertNotIn('FINISH_PRIVATE_PATH_CANARY', repr(result))
        self.assertNotIn('inference_values', result.execution_receipt)
        self.assertIsNotNone(result.execution_receipt['intermediate_commit_revision'])

    def test_revoke_before_send_and_before_delivery_has_no_private_text(self):
        for point, attempts in (('call_reserved', 0), ('return_persisted', 1), ('task_finished', 1)):
            self.store.set_readers('session', self.alice, 'source', frozenset({'alice', 'bob'}))
            port = OfflineModelPort('PRIVATE_RETURN_CANARY')
            peer = self.open()
            def revoke(stage):
                if stage == point:
                    peer.set_readers('session', self.alice, 'source', frozenset({'bob'}))
            with patch.object(self.store, '_checkpoint', revoke):
                result = HCL(self.store, principal=self.alice, gateway=ModelGateway(self.store, port)).run_sync(self.model_request(request_id=point))
            self.assertEqual(result.status, 'DENIED')
            self.assertEqual(result.answer, '')
            self.assertEqual(port.attempts, attempts)
            self.assertNotIn('PRIVATE_RETURN_CANARY', repr(result))

    def test_object_io_failure_at_reserve_response_and_finish_keeps_truthful_hold(self):
        for point, attempts, state in (('reserve', 0, None), ('response', 1, 'UNKNOWN'), ('finish', 1, 'RETURNED')):
            with self.subTest(point=point):
                request = self.model_request(request_id='io-' + point)
                original = self.store._put_object
                def fail(value):
                    matched = ((point == 'reserve' and isinstance(value, str) and 'hcl-offline-context-1' in value)
                               or (point == 'response' and value == 'RESPONSE_IO_CANARY')
                               or (point == 'finish' and isinstance(value, TaskResult)))
                    if matched:
                        raise OSError('PRIVATE_IO_FAILURE_CANARY')
                    return original(value)
                port = OfflineModelPort('RESPONSE_IO_CANARY')
                with patch.object(self.store, '_put_object', fail):
                    result = HCL(self.store, principal=self.alice, gateway=ModelGateway(self.store, port)).run_sync(request)
                self.assertEqual(result.status, 'FAILED')
                self.assertEqual(result.diagnostics[0].code, 'STORAGE_FAILURE')
                self.assertEqual(port.attempts, attempts)
                self.assertNotIn('PRIVATE_IO_FAILURE_CANARY', repr(result))
                reopened = self.open()
                self.assertEqual(TaskBudgetLedger(reopened).state(self.alice, 'session', request.request_id), state)
                replacement = OfflineModelPort()
                retry = HCL(reopened, principal=self.alice, gateway=ModelGateway(reopened, replacement)).run_sync(request)
                self.assertEqual(replacement.attempts, 0)
                if point == 'response':
                    self.assertIsNone(retry.usage['mock_calls'])
                    self.assertEqual(retry.usage['held_mock_calls'], 1)
                elif point == 'finish':
                    self.assertEqual(retry.usage['mock_calls'], 1)
                    self.assertEqual(retry.usage['held_mock_calls'], 1)

    def test_replayed_output_rechecks_acl_and_epoch_even_after_restore(self):
        first = HCL(self.store, principal=self.alice).run_sync(self.request())
        self.assertEqual(first.status, 'COMPLETED')
        self.store.set_readers('session', self.alice, 'source', frozenset({'bob'}))
        client = HCL(self.open(), principal=self.alice)
        self.assertEqual(client.run_sync(self.request()).status, 'DENIED')
        self.store.set_readers('session', self.alice, 'source', frozenset({'alice', 'bob'}))
        result = client.run_sync(self.request())
        self.assertEqual(result.status, 'DENIED')
        self.assertEqual(result.answer, '')

    def test_final_revocation_redacts_entire_logic_and_model_delivery_and_replay(self):
        for kind in ('logic.check_interpretation', 'model.respond'):
            for stream in (False, True):
                with self.subTest(kind=kind, stream=stream):
                    private_id = 'PRIVATE_SOURCE_ID_' + kind + str(stream)
                    handle = self.store.put_source('session', self.alice, private_id, 'PRIVATE_CONTENT_CANARY', formal_problem=self.problem)
                    request = self.request(request_id=kind + str(stream), source_handles=(handle,),
                        issue=Issue('test', kind, private_id), budget=BudgetSlice(max_mock_calls=1))
                    peer = self.open()
                    def revoke(stage):
                        if stage == 'task_finished':
                            peer.set_readers('session', self.alice, private_id, frozenset({'bob'}))
                    client = HCL(self.store, principal=self.alice)
                    with patch.object(self.store, '_checkpoint', revoke):
                        if stream:
                            async def collect():
                                return [event async for event in client.stream(request)]
                            result = asyncio.run(collect())[-1].result
                        else:
                            result = client.run_sync(request)
                    for delivered in (result, HCL(self.open(), principal=self.alice).run_sync(request)):
                        self.assertEqual(delivered.status, 'DENIED')
                        self.assertEqual(delivered.answer, '')
                        self.assertEqual(delivered.claim_records, ())
                        self.assertIsNone(delivered.state_revision)
                        for field in ('source_versions', 'read_set', 'result_ids', 'inference_values',
                                      'operation_ids', 'base_revision', 'commit_revision', 'access_epoch'):
                            self.assertNotIn(field, delivered.execution_receipt)
                        self.assertNotIn(private_id, repr(delivered))
                        self.assertNotIn('PRIVATE_CONTENT_CANARY', repr(delivered))

    def test_cached_replay_rechecks_after_loading_old_wal_snapshot(self):
        for stream in (False, True):
            for hook in ('result_object', 'before_commit'):
                with self.subTest(stream=stream, hook=hook):
                    source_id = 'PRIVATE_REPLAY_SOURCE_' + str(stream) + hook
                    handle = self.store.put_source('session', self.alice, source_id, 'PRIVATE_REPLAY_CONTENT_CANARY')
                    request = self.request(request_id=source_id, source_handles=(handle,), issue=Issue('report', 'source.report'))
                    self.assertEqual(HCL(self.store, principal=self.alice).run_sync(request).status, 'COMPLETED')
                    reading, peer = self.open(), self.open()
                    original = reading._get_object
                    revoked = False
                    def revoke():
                        nonlocal revoked
                        if not revoked:
                            peer.set_readers('session', self.alice, source_id, frozenset({'bob'}))
                            revoked = True
                    def get(digest):
                        value = original(digest)
                        if isinstance(value, TaskResult):
                            revoke()
                        return value
                    def checkpoint(stage):
                        if stage == 'before_commit':
                            revoke()
                    context = patch.object(reading, '_get_object', get) if hook == 'result_object' else patch.object(reading, '_checkpoint', checkpoint)
                    client = HCL(reading, principal=self.alice)
                    with context:
                        if stream:
                            async def collect():
                                return [event async for event in client.stream(request)]
                            result = asyncio.run(collect())[-1].result
                        else:
                            result = client.run_sync(request)
                    self.assertTrue(revoked)
                    self.assertEqual(result.status, 'DENIED')
                    self.assertEqual(result.answer, '')
                    self.assertNotIn('source_versions', result.execution_receipt)
                    self.assertNotIn('PRIVATE_REPLAY_CONTENT_CANARY', repr(result))

    def test_foreign_task_probe_matches_missing_task_and_has_zero_attempts(self):
        request = self.model_request()
        HCL(self.store, principal=self.alice).run_sync(request)
        outsider = Principal('foreign', 'mallory')
        port = OfflineModelPort()
        client = HCL(self.open(), principal=outsider)
        present = client.run_sync(replace(request, principal=outsider))
        absent = client.run_sync(replace(request, principal=outsider, request_id='absent'))
        self.assertEqual(present.status, 'DENIED')
        self.assertEqual(present.usage, absent.usage)
        self.assertEqual(present.diagnostics, absent.diagnostics)
        self.assertNotIn('mock_call_state', present.execution_receipt)

    def test_durable_stream_uses_same_checked_final_result(self):
        async def stream():
            return [event async for event in HCL(self.store, principal=self.alice).stream(self.request())]
        events = asyncio.run(stream())
        self.assertEqual([event.kind for event in events], ['status', 'result'])
        self.assertEqual(events[-1].status, 'COMPLETED')
        replay = HCL(self.open(), principal=self.alice).run_sync(self.request())
        self.assertEqual(events[-1].result.answer, replay.answer)


if __name__ == '__main__':
    unittest.main()
