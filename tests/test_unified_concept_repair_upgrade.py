"""Exact PR442 runtime process -> counterexample-repair runtime side-copy.

Only the 227 hcl Python files at the pinned shipped tree are projected. Every
store, request, answer and interrupted operation is produced by that runtime in
an isolated subprocess. All proposal inputs are synthetic and provider-free.
"""

from dataclasses import fields
from hashlib import sha256
import json
import sqlite3
import subprocess
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.governance import verify_inventory
from hcl.memory.migrations.revision_upgrade import (
    CONCEPT_REPAIR_PREDECESSOR_CODE_HASH,
    RevisionCutover,
)
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.execution_ledger import ExecutionLedger
from hcl.runtime.recovery import RecoveryManager
from tests.test_unified_persistent_concept_upgrade import PROPOSALS
from tests import test_unified_s23_upgrade as fixtures


BASELINE = "f813ca5fb93ff62b167dd33268cdae4ec0e247d3"
BASELINE_TREE = "0bd1ebd1b1d8f461313a50f65a01ccca324102c0"
BASELINE_CODE_HASH = "5aadaf9bfed53e096e2258badb69b0d807f2303443411ef630e436769ad14de0"

OLD_PROGRAM = PROPOSALS + r'''
from dataclasses import fields, replace
from hashlib import sha256
import json
from pathlib import Path
import sys
from unittest.mock import patch
from hcl import (HCL, ExecutionBudget, ExecutionIssue, ConceptAdoptionIssue,
                 ConceptFollowIssue, ConceptBinding)
from hcl.kernel.types import Principal, TaskRequest, Issue
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.types import LegacySnapshot, LegacySource
from hcl.memory.migrations.revision_upgrade import RevisionCutover, _history
from hcl.memory.migrations.control import version_bundle
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.execution_ledger import ExecutionLedger

root = Path(sys.argv[1])
schema = int(sys.argv[2])
owner = Principal('tenant', 'alice')
if schema == 4:
    imported = MigrationNamespace.import_snapshot(
        root / 'imported', LegacySnapshot((LegacySource('independent', 1, 'SYNTHETIC_ORIGINAL'),)),
        namespace_id='legacy', owner=owner)
    session = imported.receipt(owner)['session_id']
    namespace = RevisionCutover.upgrade(imported.path, root / 'old4', owner)
    store = namespace.open_store()
    store.prepare_legacy_capsules(session, owner)
else:
    store = StateStore.sqlite(root / 'old.sqlite', revision=True)
    session = 's'
    store.create_session(session, owner, {'bob'})
handles = (store.put_source(session, owner, 'scene', SCENE),
           store.put_source(session, owner, 'principles', PRINCIPLES))

class Crash(BaseException):
    pass

requests = {}
request_objects = {}

def remember(request, state, family, result=None):
    task = dict(store._db.execute('SELECT * FROM tasks WHERE request_id=?',
                                 (request.request_id,)).fetchone())
    calls = [dict(row) for row in store._db.execute('SELECT * FROM calls WHERE task_key=?',
                                                  (task['task_key'],))]
    value = store._get_object(task['result_hash'])
    expected = {}
    if state in ('computed', 'committed'):
        for node in value.nodes.values():
            operation = node.get('result')
            if node.get('operation') == 'compute' and operation is not None:
                expected.update({item.result_id: sha256(codec.dumps(item)).hexdigest()
                                 for item in operation.candidate_delta.new_inferences})
        assert expected, request.request_id
    elif state == 'completed':
        expected = {item.result_id: sha256(codec.dumps(item)).hexdigest()
                    for item in ExecutionLedger(store).delivery_inferences(
                        request, result.execution_receipt['result_ids'])}
        assert expected, request.request_id
    requests[request.request_id] = dict(
        request=codec.dumps(request).decode(), owner_id=store.owner_id, state=state,
        family=family, task=task, calls=calls, inference_hashes=expected,
        answer=result.answer if result is not None else None,
        claims=codec.dumps(result.claim_records).decode() if result is not None else None)
    request_objects[request.request_id] = request

dialects = ([('v1', base_propose), ('v2', concept_propose)] if MODE == 'baseline'
            else [] if MODE == 'pins' else [('v2', concept_propose)])
checkpoints = [('completed', None), ('returned', 'return_persisted'),
               ('unknown', 'send_started'), ('computed', 'execution_computed'),
               ('committed', 'execution_effects_committed')]
for dialect, proposer in dialects:
    for state, seam in checkpoints if MODE == 'baseline' else checkpoints[:1]:
        key = dialect + '-' + state
        request = TaskRequest(key, 'Evaluate the explicit conditional principles and commitment scope.',
            handles, session, owner,
            budget=ExecutionBudget(max_mock_calls=1, max_feedback=0, max_local_evaluations=100000,
                max_request_bytes=1048576, max_context_tokens=1048576,
                max_output_bytes=1048576, max_total_output_bytes=8000000,
                max_visible_output_tokens=1048576),
            issue=ExecutionIssue('root', goals=(Issue(key, 'judgment.evaluate'),)))
        candidate = proposer(store.snapshot(session, owner, handles), request.question)
        assert candidate['schema'] == 'hcl-judgment-candidates-' + dialect[1:]
        port = OfflineModelPort(json.dumps(candidate))
        crashed = False
        def stop(stage):
            global crashed
            if stage == seam and not crashed:
                crashed = True
                raise Crash()
        result = None
        try:
            with patch.object(store, '_checkpoint', stop):
                result = HCL(store, principal=owner, gateway=ModelGateway(store, port)).run_sync(request)
        except Crash:
            pass
        if seam:
            assert crashed, key
        else:
            assert result.status == 'PARTIAL', (key, result.diagnostics)
        remember(request, state, dialect, result)
        calls = requests[key]['calls']
        assert len(calls) == 1, key
        assert calls[0]['state'] == ('SEND_STARTED' if state == 'unknown' else 'RETURNED')
        assert port.attempts == (0 if state == 'unknown' else 1), key

base_request = request_objects.get('v2-completed')
base_id = next(iter(requests['v2-completed']['inference_hashes'])) if base_request else None

def local_request(name, goal):
    return replace(base_request, request_id=name, source_handles=(),
        budget=replace(base_request.budget, max_mock_calls=0),
        issue=ExecutionIssue('root', goals=(goal,)))

def run_local(request):
    port = OfflineModelPort('NO_LOCAL_MODEL_SEND')
    result = HCL(store, principal=owner, gateway=ModelGateway(store, port)).run_sync(request)
    assert port.attempts == 0
    return result

# Each stream has real A adoption, independent B/C subscriptions, then D.
# The interrupted D stops at its second successor, after the first successor
# was already committed; both retained computations must be reused on upgrade.
persistent_seams = {'completed': None, 'computed': 'execution_computed',
                    'committed': 'execution_effects_committed'}
for state in (MODE,) if MODE in persistent_seams else ():
    seam = persistent_seams[state]
    stream = 'institution-' + state
    a = local_request('A-' + state, ConceptAdoptionIssue('A-' + state,
        stream_id=stream, support_result_ids=(base_id,), version_labels=('original',)))
    adopted = run_local(a)
    assert adopted.status == 'COMPLETED', adopted.diagnostics
    remember(a, 'completed', 'persistent', adopted)
    head = adopted.execution_receipt['result_ids'][0]
    prior = {}
    for name in ('B', 'C'):
        request = local_request(name + '-' + state, ConceptFollowIssue(name + '-' + state,
            base_result_id=base_id, bindings=(ConceptBinding('meaning', stream),)))
        result = run_local(request)
        assert result.status == 'PARTIAL', result.diagnostics
        remember(request, 'completed', 'persistent', result)
        prior[name] = dict(store._db.execute('SELECT * FROM tasks WHERE request_id=?',
                                           (request.request_id,)).fetchone())
    request = local_request('D-' + state, ConceptAdoptionIssue('D-' + state,
        stream_id=stream, support_result_ids=(base_id,), version_labels=('revised',),
        expected_head=head))
    ordinal = 0
    crashed = False
    def stop(stage):
        global ordinal, crashed
        if stage == seam:
            ordinal += 1
            if ordinal == 3:
                crashed = True
                raise Crash()
    result = None
    try:
        with patch.object(store, '_checkpoint', stop):
            result = run_local(request)
    except Crash:
        pass
    if seam:
        assert crashed, (state, ordinal)
    else:
        assert result.status == 'PARTIAL', result.diagnostics
        assert {row['original_request_id'] for row in result.execution_receipt['concept_successors']} == {
            'B-' + state, 'C-' + state}
    remember(request, state, 'persistent', result)
    assert requests[request.request_id]['calls'] == []
    for name, before in prior.items():
        after = dict(store._db.execute('SELECT * FROM tasks WHERE request_id=?',
                                      (name + '-' + state,)).fetchone())
        assert before == after

# Capture the predecessor's fresh delivery behavior too: superseded B/C must
# remain stale, while their original immutable answer/claim objects are kept.
for name, metadata in requests.items():
    if metadata['state'] != 'completed':
        continue
    port = OfflineModelPort('NO_PREDECESSOR_REPLAY_SEND')
    result = HCL(store, principal=owner, gateway=ModelGateway(store, port)).run_sync(request_objects[name])
    assert port.attempts == 0
    expected_status = ('STALE_STATE' if name.startswith(('B-', 'C-')) else
                       'COMPLETED' if name.startswith('A-') else 'PARTIAL')
    assert result.status == expected_status, (name, result.diagnostics)
    metadata['replay_status'] = result.status
    metadata['replay_answer'] = result.answer
    metadata['replay_claims'] = codec.dumps(result.claim_records).decode()

print(json.dumps(dict(path=str(store.path), session=session, owner_id=store.owner_id,
    requests=requests, bundle=version_bundle(schema=schema),
    shapes={name: [field.name for field in fields(cls)] for name, cls in codec.CLASSES.items()},
    retained_hashes=_history(store._db, store.object_root)[1],
    salt=store._revision_control['governance_salt'])), flush=True)
for line in sys.stdin:
    command = json.loads(line)
    try:
        action = command['action']
        if action == 'close':
            break
        if action == 'write':
            store.put_source(session, owner, 'late', 'SYNTHETIC_LATE_WRITE')
        elif action == 'snapshot':
            store.snapshot(session, owner, handles)
        elif action == 'open':
            opened = StateStore.sqlite(command['path'])
            opened.close()
        print(json.dumps({'ok': True}), flush=True)
    except Exception as error:
        print(json.dumps({'ok': False, 'error': type(error).__name__}), flush=True)
store.close()
'''


class ConceptRepairPredecessorUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = subprocess.check_output(
            ['git', 'rev-parse', BASELINE + '^{tree}'], cwd=fixtures.ROOT, text=True).strip()
        if tree != BASELINE_TREE or CONCEPT_REPAIR_PREDECESSOR_CODE_HASH != BASELINE_CODE_HASH:
            raise AssertionError('exact PR442 predecessor identity changed')

        class FrozenRuntime(fixtures.RuntimeUpgradeTests):
            baseline = BASELINE
            code_hash = CONCEPT_REPAIR_PREDECESSOR_CODE_HASH
            file_count = 227
            old_program = OLD_PROGRAM

            def old(self, schema=3, name='old', *, mode='baseline'):
                # Select synthetic workloads only; never alter projected code
                # or version pins. Separate stores honor the 128 MiB bound.
                self.old_program = 'MODE = ' + repr(mode) + '\n' + OLD_PROGRAM
                return super().old(schema, name)

        cls.runtime = FrozenRuntime
        cls.runtime.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.runtime.tearDownClass()

    def fixture(self):
        fixture = self.runtime()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        return fixture

    @staticmethod
    def rows(db):
        names = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
                 if row[0] not in ('revision_control', 'namespace_control', 'cutover_control')]
        return {name: sorted((dict(row) for row in db.execute('SELECT * FROM ' + name)),
                             key=codec.canonical) for name in names}

    def assert_inferences_unchanged(self, store, metadata):
        for result_id, digest in metadata['inference_hashes'].items():
            row = store._db.execute('SELECT object_hash FROM inferences WHERE result_id=?',
                                   (result_id,)).fetchone()
            self.assertIsNotNone(row, result_id)
            self.assertEqual(row['object_hash'], digest)
            self.assertEqual(sha256(codec.dumps(store._get_object(digest))).hexdigest(), digest)

    def test_exact_v1_v2_and_persistent_checkpoints_preserve_bytes_without_resends(self):
        fixture = self.fixture()
        modes = ('baseline', 'completed', 'computed', 'committed')
        for schema, mode in ((schema, mode) for schema in (3, 4) for mode in modes):
            with self.subTest(schema=schema, workload=mode):
                source, old, process = fixture.old(schema, 'old-' + str(schema) + '-' + mode, mode=mode)
                shapes = {name: [field.name for field in fields(cls)]
                          for name, cls in codec.CLASSES.items()}
                self.assertEqual(old['shapes'], {name: shapes[name] for name in old['shapes']})
                self.assertEqual(len(old['requests']), 10 if mode == 'baseline' else 5)
                with sqlite3.connect(source) as db:
                    db.row_factory = sqlite3.Row
                    original_rows = self.rows(db)
                    original_control = dict(db.execute('SELECT * FROM revision_control').fetchone())
                retained = set(old['retained_hashes'])
                objects = {path.name: path.read_bytes()
                           for path in source.with_name(source.name + '.objects').iterdir()}
                with self.assertRaises(ValueError):
                    StateStore.sqlite(source)
                target = RevisionCutover.upgrade(source, fixture.root / ('new-' + str(schema) + '-' + mode), fixture.owner)
                store = target.open_store()
                self.addCleanup(store.close)
                self.assertEqual(store._schema, schema)
                self.assertEqual(store._revision_control['governance_salt'], old['salt'])
                self.assertEqual(self.rows(store._db), original_rows)
                verify_inventory(store._db)
                for digest in retained:
                    self.assertEqual((store.object_root / digest).read_bytes(), objects[digest])
                    self.assertEqual(sha256(objects[digest]).hexdigest(), digest)

                for name, metadata in old['requests'].items():
                    with self.subTest(schema=schema, checkpoint=name):
                        request = codec.loads(metadata['request'].encode())
                        self.assertEqual(codec.dumps(request), metadata['request'].encode())
                        port = OfflineModelPort('NO_UPGRADE_SEND')
                        client = HCL(store, principal=fixture.owner, gateway=ModelGateway(store, port))
                        state = metadata['state']
                        if state == 'unknown':
                            with self.assertRaises(HCLFailure) as caught:
                                RecoveryManager(store).resume_execution(request, expected_owner_id=metadata['owner_id'])
                            self.assertEqual(caught.exception.diagnostic.code, 'UNKNOWN_SEND_NO_RESUME')
                            result = client.run_sync(request)
                            self.assertEqual(result.diagnostics[0].code, 'TASK_INTERRUPTED_NO_RESEND')
                            self.assertIsNone(result.usage['mock_calls'])
                            self.assertEqual(result.usage['observed_mock_calls'], 0)
                            self.assertEqual(result.usage['held_mock_calls'], 1)
                            self.assertTrue(result.usage['mock_usage_unknown'])
                            self.assertFalse(result.answer or result.claim_records)
                            call = dict(store._db.execute('SELECT * FROM calls WHERE task_key=?',
                                (metadata['task']['task_key'],)).fetchone())
                            self.assertEqual(call['state'], 'UNKNOWN')
                            self.assertIsNone(call['attempted'])
                            self.assertEqual(call['owner_id'], metadata['owner_id'])
                            for field in ('request_hash', 'request_bytes', 'response_hash', 'output_bytes'):
                                self.assertEqual(call[field], metadata['calls'][0][field])
                        else:
                            if state != 'completed':
                                RecoveryManager(store).resume_execution(request, expected_owner_id=metadata['owner_id'])
                            if state == 'returned':
                                result = client.run_sync(request)
                            else:
                                with patch.object(LocalModelOperator, 'run', side_effect=AssertionError(
                                        'accepted model computation cannot run again')), patch(
                                        'hcl.operators.persistent_concepts.compute_persistent',
                                        side_effect=AssertionError('accepted successor cannot run again')):
                                    result = client.run_sync(request)
                            if state == 'completed':
                                self.assertEqual(result.status, metadata['replay_status'], result.diagnostics)
                                self.assertEqual(result.answer.encode(), metadata['replay_answer'].encode())
                                self.assertEqual(codec.dumps(result.claim_records), metadata['replay_claims'].encode())
                                persisted = store._get_object(metadata['task']['result_hash'])
                                self.assertEqual(persisted.answer.encode(), metadata['answer'].encode())
                                self.assertEqual(codec.dumps(persisted.claim_records), metadata['claims'].encode())
                                self.assertEqual(dict(store._db.execute('SELECT * FROM tasks WHERE task_key=?',
                                    (metadata['task']['task_key'],)).fetchone()), metadata['task'])
                            else:
                                self.assertEqual(result.status, 'PARTIAL', result.diagnostics)
                            if result.status != 'STALE_STATE':
                                self.assertEqual(result.usage['mock_calls'],
                                                 0 if metadata['family'] == 'persistent' else 1)
                            self.assert_inferences_unchanged(store, metadata)
                            if name.startswith('D-'):
                                self.assertEqual({row['original_request_id'] for row in
                                    result.execution_receipt['concept_successors']},
                                    {'B-' + state, 'C-' + state})
                                inferred = ExecutionLedger(store).delivery_inferences(
                                    request, result.execution_receipt['result_ids'])
                                successors = [item for item in inferred
                                    if item.kind == 'CONDITIONAL_PERSISTENT_CONCEPT_JUDGMENT']
                                self.assertEqual(len(successors), 2)
                                for item in successors:
                                    AnswerAssembler().compact_claim(item)
                                    self.assertEqual(item.values['branches'][0]['classifications']
                                                     ['current']['actual']['status'], 'MEMBER')
                        self.assertEqual(port.attempts, 0)

                # No call was added and historical requests never become repair tasks.
                self.assertEqual(store._db.execute('SELECT count(*) FROM calls').fetchone()[0],
                                 len(original_rows['calls']))
                for action in ('snapshot', 'write'):
                    self.assertFalse(fixture.command(process, action=action)['ok'])
                self.assertFalse(fixture.command(process, action='open', path=str(target.path))['ok'])
                with sqlite3.connect(source) as db:
                    db.row_factory = sqlite3.Row
                    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 91)
                    self.assertEqual(dict(db.execute('SELECT * FROM revision_control').fetchone()),
                                     dict(original_control, mode='TERMINAL_SOURCE'))
                    self.assertEqual(self.rows(db), original_rows)
                for digest, body in objects.items():
                    self.assertEqual((source.with_name(source.name + '.objects') / digest).read_bytes(), body)
                    if digest in retained:
                        self.assertEqual((store.object_root / digest).read_bytes(), body)
                self.assertEqual(RevisionCutover.upgrade(source, target.directory, fixture.owner).path, target.path)
                store.rebuild_projections()
                verify_inventory(store._db)
                store.set_readers(old['session'], fixture.owner, 'principles', {'bob'})
                for metadata in old['requests'].values():
                    port = OfflineModelPort('NO_ACL_BYPASS')
                    denied = HCL(store, principal=fixture.owner, gateway=ModelGateway(store, port)).run_sync(
                        codec.loads(metadata['request'].encode()))
                    self.assertEqual(denied.status, 'DENIED')
                    self.assertFalse(denied.answer or denied.claim_records)
                    self.assertEqual(port.attempts, 0)

    def test_exact_pin_rejects_changed_hash_indexes_governance_and_split_controls(self):
        fixture = self.fixture()
        for schema in (3, 4):
            source, _, process = fixture.old(schema, 'reject-' + str(schema), mode='pins')
            with sqlite3.connect(source) as db:
                original = db.execute('SELECT versions FROM revision_control').fetchone()[0]
                namespace = (db.execute('SELECT versions FROM namespace_control').fetchone()[0]
                             if schema == 4 else None)
            for mutation in ('hash', 'indexes', 'governance') + (('namespace',) if schema == 4 else ()):
                with self.subTest(schema=schema, mutation=mutation):
                    bundle = json.loads(original)
                    if mutation in ('hash', 'namespace'):
                        bundle['code_sha256'] = '0' * 64
                    elif mutation == 'indexes':
                        bundle['indexes']['revision'] = 2
                    else:
                        bundle.pop('governance')
                    with sqlite3.connect(source) as db:
                        table = 'namespace_control' if mutation == 'namespace' else 'revision_control'
                        db.execute('UPDATE ' + table + ' SET versions=?', (codec.canonical(bundle),))
                    destination = fixture.root / ('rejected-' + str(schema) + '-' + mutation)
                    with self.assertRaises((ValueError, HCLFailure)):
                        RevisionCutover.upgrade(source, destination, fixture.owner)
                    self.assertFalse(destination.exists())
                    with sqlite3.connect(source) as db:
                        self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], schema)
                        self.assertEqual(db.execute('SELECT mode FROM revision_control').fetchone()[0], 'ACTIVE')
                        self.assertFalse(db.execute("SELECT 1 FROM sqlite_master WHERE name='cutover_control'").fetchone())
                        db.execute('UPDATE revision_control SET versions=?', (original,))
                        if namespace is not None:
                            db.execute('UPDATE namespace_control SET versions=?', (namespace,))
                    self.assertTrue(fixture.command(process, action='snapshot')['ok'])
            self.assertTrue(fixture.command(process, action='write')['ok'])
