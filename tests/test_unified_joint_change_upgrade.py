"""Exact PR443 predecessor processes survive the additive joint-change upgrade.

Only the 230 hcl Python files at the pinned predecessor tree are projected.
Real old processes create the ledgers, v1/v2/v3 judgments, capsule-1 proofs and
interrupted two-subscriber adoptions. Synthetic workloads have separate stores
so neither the 4 MiB audit limit nor the 128 MiB migration limit is enlarged.
"""

from contextlib import contextmanager
from dataclasses import fields, replace
from hashlib import sha256
import inspect
import json
import sqlite3
import subprocess
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure, thaw
from hcl.memory import codec
from hcl.memory.governance import verify_inventory
from hcl.memory.migrations import revision_upgrade
from hcl.memory.migrations.revision_upgrade import RevisionCutover
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.concept_proof import unpack_proof
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.execution_ledger import ExecutionLedger
from hcl.runtime.recovery import RecoveryManager
from scripts import witness_unified_concept_repairs as repairs
from tests import test_unified_s23_upgrade as fixtures
from tests.test_unified_persistent_concept_upgrade import PROPOSALS


BASELINE = "efe7d78b83e50a3723f46280163bb786be74b7f1"
BASELINE_TREE = "ded6a65a18763b3d1aa78b0010dd7664ea7ed143"
BASELINE_CODE_HASH = "8310ca28dad0ceeadb24b2dc432827a280680b84e30c014d8e38203bf003413f"

# These functions supply synthetic data to the isolated predecessor. No current
# runtime object, store, certificate, version pin or implementation is copied in.
OLD_PROPOSALS = (
    PROPOSALS
    + inspect.getsource(repairs.propose)
        .replace("def propose(", "def repair_propose(")
        .replace("base_propose(snapshot,question)", "concept_propose(snapshot,question)")
    + "REPAIR_SCENE = " + repr(repairs.SCENE) + "\n"
    + "REPAIR_PRINCIPLES = " + repr(repairs.PRINCIPLES) + "\n"
)

OLD_PROGRAM = OLD_PROPOSALS + r'''
from dataclasses import fields, replace
from hashlib import sha256
import json
from pathlib import Path
import sys
from unittest.mock import patch
from hcl import (HCL, ExecutionBudget, ExecutionIssue, ConceptAdoptionIssue,
                 ConceptFollowIssue, ConceptBinding)
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.types import LegacySnapshot, LegacySource
from hcl.memory.migrations.revision_upgrade import RevisionCutover, _history
from hcl.memory.migrations.control import version_bundle
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.concept_proof import unpack_proof
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
repair_mode = '-v3' in MODE
handles = (store.put_source(session, owner, 'scene', REPAIR_SCENE if repair_mode else SCENE),
           store.put_source(session, owner, 'principles', REPAIR_PRINCIPLES if repair_mode else PRINCIPLES))

class Crash(BaseException):
    pass

requests, request_objects, capsules = {}, {}, {}

def capture_capsules(value):
    if isinstance(value, dict):
        if value.get('schema') == 'hcl-concept-proof-capsule-1':
            proof = unpack_proof(value)
            assert proof.kind == 'CONDITIONAL_CONCEPT_REPAIR_JUDGMENT'
            assert sha256(codec.dumps(proof)).hexdigest() == value['sha256']
            wire = codec.dumps(value)
            capsules[sha256(wire).hexdigest()] = wire.decode()
        else:
            for item in value.values():
                capture_capsules(item)
    elif isinstance(value, list):
        for item in value:
            capture_capsules(item)


def remember(request, state, family, result=None):
    task = dict(store._db.execute('SELECT * FROM tasks WHERE request_id=?',
                                 (request.request_id,)).fetchone())
    calls = [dict(row) for row in store._db.execute('SELECT * FROM calls WHERE task_key=?',
                                                  (task['task_key'],))]
    value = store._get_object(task['result_hash'])
    accepted = []
    if state in ('computed', 'committed'):
        for node in value.nodes.values():
            operation = node.get('result')
            if node.get('operation') == 'compute' and operation is not None:
                accepted.extend(operation.candidate_delta.new_inferences)
        assert accepted, request.request_id
    elif state == 'completed':
        accepted = ExecutionLedger(store).delivery_inferences(
            request, result.execution_receipt['result_ids'])
        assert accepted, request.request_id
    for item in accepted:
        capture_capsules(thaw(item.values))
    requests[request.request_id] = dict(
        request=codec.dumps(request).decode(), owner_id=store.owner_id, state=state,
        family=family, task=task, calls=calls,
        inference_hashes={item.result_id: sha256(codec.dumps(item)).hexdigest() for item in accepted},
        inference_kinds={item.result_id: item.kind for item in accepted},
        answer=result.answer if result is not None else None,
        claims=codec.dumps(result.claim_records).decode() if result is not None else None)
    request_objects[request.request_id] = request


dialect = MODE.split('-')[1] if MODE != 'pins' else None
proposer = {'v1': base_propose, 'v2': concept_propose, 'v3': repair_propose}.get(dialect)
checkpoints = [('completed', None), ('returned', 'return_persisted'),
               ('unknown', 'send_started'), ('computed', 'execution_computed'),
               ('committed', 'execution_effects_committed')]
for state, seam in (checkpoints if MODE.startswith('judgment-') else checkpoints[:1]
                    if MODE.startswith('persistent-') else []):
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


if MODE.startswith('persistent-'):
    state = MODE.split('-')[2]
    seam = {'completed': None, 'computed': 'execution_computed',
            'committed': 'execution_effects_committed'}[state]
    base_request = request_objects[dialect + '-completed']
    base_id = next(iter(requests[dialect + '-completed']['inference_hashes']))
    proof = ExecutionLedger(store).delivery_inferences(base_request, (base_id,))[0]
    assert proof.kind == ('CONDITIONAL_CONCEPT_REPAIR_JUDGMENT' if repair_mode else
                          'CONDITIONAL_CONCEPT_JUDGMENT')
    label = 'revised'
    if repair_mode:
        repair = proof.values['repairs'][0]
        assert repair['complete'] and not repair['adopted']
        label = next(item['version_label'] for item in repair['candidates']
                     if item['id'] in repair['minimum_consistent_candidate_ids'])
    def local_request(name, goal):
        return replace(base_request, request_id=name, source_handles=(),
            budget=replace(base_request.budget, max_mock_calls=0),
            issue=ExecutionIssue('root', goals=(goal,)))
    def run_local(request):
        port = OfflineModelPort('NO_LOCAL_MODEL_SEND')
        result = HCL(store, principal=owner, gateway=ModelGateway(store, port)).run_sync(request)
        assert port.attempts == 0
        return result
    stream = 'institution-' + MODE
    a = local_request('A', ConceptAdoptionIssue('A', stream_id=stream,
        support_result_ids=(base_id,), version_labels=('original',)))
    adopted = run_local(a)
    assert adopted.status == 'COMPLETED', adopted.diagnostics
    remember(a, 'completed', 'persistent', adopted)
    head = adopted.execution_receipt['result_ids'][0]
    prior = {}
    for name in ('B', 'C'):
        follow = local_request(name, ConceptFollowIssue(name, base_result_id=base_id,
            bindings=(ConceptBinding('meaning', stream),)))
        followed = run_local(follow)
        assert followed.status == 'PARTIAL', followed.diagnostics
        remember(follow, 'completed', 'persistent', followed)
        prior[name] = dict(store._db.execute('SELECT * FROM tasks WHERE request_id=?',
                                           (name,)).fetchone())
    request = local_request('D', ConceptAdoptionIssue('D', stream_id=stream,
        support_result_ids=(base_id,), version_labels=(label,), expected_head=head))
    ordinal = 0
    crashed = False
    def stop(stage):
        global ordinal, crashed
        if stage == seam:
            ordinal += 1
            # Adoption, committed B successor, then computed/committed C.
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
        assert {row['original_request_id'] for row in result.execution_receipt['concept_successors']} == {'B', 'C'}
    remember(request, state, 'persistent', result)
    assert requests['D']['calls'] == []
    for name, before in prior.items():
        assert before == dict(store._db.execute('SELECT * FROM tasks WHERE request_id=?',
                                               (name,)).fetchone())
    if repair_mode:
        assert capsules, 'real v3 adoption/follow must persist capsule-1 proofs'

# Record real predecessor delivery, including B/C invalidation after adoption.
for name, metadata in requests.items():
    if metadata['state'] != 'completed':
        continue
    port = OfflineModelPort('NO_PREDECESSOR_REPLAY_SEND')
    result = HCL(store, principal=owner, gateway=ModelGateway(store, port)).run_sync(request_objects[name])
    assert port.attempts == 0
    expected = 'STALE_STATE' if name in ('B', 'C') else 'COMPLETED' if name == 'A' else 'PARTIAL'
    assert result.status == expected, (name, result.diagnostics)
    metadata.update(replay_status=result.status, replay_answer=result.answer,
                    replay_claims=codec.dumps(result.claim_records).decode())

retained = _history(store._db, store.object_root)[1]
assert sum((store.object_root / digest).stat().st_size for digest in retained) <= 128 * 1024 * 1024
assert all((store.object_root / digest).stat().st_size <= 4 * 1024 * 1024 for digest in retained)
print(json.dumps(dict(path=str(store.path), session=session, owner_id=store.owner_id,
    requests=requests, capsules=capsules, mode=MODE, bundle=version_bundle(schema=schema),
    shapes={name: [field.name for field in fields(cls)] for name, cls in codec.CLASSES.items()},
    retained_hashes=retained, salt=store._revision_control['governance_salt'])), flush=True)
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


class JointChangePredecessorUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = subprocess.check_output(
            ['git', 'rev-parse', BASELINE + '^{tree}'], cwd=fixtures.ROOT, text=True).strip()
        if (tree != BASELINE_TREE or
                revision_upgrade.JOINT_CHANGE_PREDECESSOR_CODE_HASH != BASELINE_CODE_HASH):
            raise AssertionError('exact joint-change predecessor identity changed')

        # Keep the inherited test case local: unittest must not discover and
        # rerun all of the unrelated S2.3 test methods through an imported alias.
        class FrozenRuntime(fixtures.RuntimeUpgradeTests):
            baseline = BASELINE
            code_hash = BASELINE_CODE_HASH
            file_count = 230
            old_program = OLD_PROGRAM

            def old(self, schema=3, name='old', *, mode='pins'):
                self.old_program = 'MODE = ' + repr(mode) + '\n' + OLD_PROGRAM
                return super().old(schema, name)

        cls.runtime = FrozenRuntime
        cls.runtime.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.runtime.tearDownClass()

    @contextmanager
    def fixture(self):
        fixture = self.runtime()
        fixture.setUp()
        try:
            yield fixture
        finally:
            fixture.doCleanups()
            fixture.tearDown()

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
            body = (store.object_root / digest).read_bytes()
            self.assertEqual(sha256(body).hexdigest(), digest)
            value = store._get_object(digest)
            self.assertEqual(codec.dumps(value), body)
            self.assertEqual(value.kind, metadata['inference_kinds'][result_id])
            self.assertNotIn('JOINT_CHANGE', value.kind)

    def assert_capsules_unchanged(self, store, old):
        observed = {}
        def visit(value):
            if isinstance(value, dict):
                if value.get('schema') == 'hcl-concept-proof-capsule-1':
                    wire = codec.dumps(value)
                    observed[sha256(wire).hexdigest()] = wire.decode()
                    proof = unpack_proof(value)
                    self.assertEqual(proof.kind, 'CONDITIONAL_CONCEPT_REPAIR_JUDGMENT')
                    self.assertEqual(sha256(codec.dumps(proof)).hexdigest(), value['sha256'])
                else:
                    for child in value.values():
                        visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        for row in store._db.execute('SELECT object_hash FROM inferences'):
            visit(thaw(store._get_object(row['object_hash']).values))
        self.assertTrue(old['capsules'])
        self.assertEqual(observed, old['capsules'])

    def exercise_workload(self, fixture, schema, mode, *, erase=False):
        suffix = str(schema) + '-' + mode
        source, old, process = fixture.old(schema, 'old-' + suffix, mode=mode)
        shapes = {name: [field.name for field in fields(cls)] for name, cls in codec.CLASSES.items()}
        self.assertEqual(old['shapes'], {name: shapes[name] for name in old['shapes']})
        self.assertEqual(len(old['requests']), 5)
        with sqlite3.connect(source) as db:
            db.row_factory = sqlite3.Row
            original_rows = self.rows(db)
            original_control = dict(db.execute('SELECT * FROM revision_control').fetchone())
        objects = {path.name: path.read_bytes()
                   for path in source.with_name(source.name + '.objects').iterdir()}
        retained = set(old['retained_hashes'])
        self.assertLessEqual(sum(len(objects[key]) for key in retained), 128 * 1024 * 1024)
        self.assertTrue(all(len(objects[key]) <= 4 * 1024 * 1024 for key in retained))
        with self.assertRaises(ValueError):
            StateStore.sqlite(source)
        target = RevisionCutover.upgrade(source, fixture.root / ('new-' + suffix), fixture.owner)
        store = target.open_store()
        fixture.addCleanup(store.close)
        self.assertEqual(store._schema, schema)
        self.assertEqual(store._revision_control['governance_salt'], old['salt'])
        self.assertEqual(self.rows(store._db), original_rows)
        verify_inventory(store._db)
        for digest in retained:
            self.assertEqual((store.object_root / digest).read_bytes(), objects[digest])
            self.assertEqual(sha256(objects[digest]).hexdigest(), digest)

        for name, metadata in old['requests'].items():
            with self.subTest(schema=schema, mode=mode, request=name):
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
                    if name == 'D':
                        self.assertEqual({row['original_request_id'] for row in
                            result.execution_receipt['concept_successors']}, {'B', 'C'})
                        inferred = ExecutionLedger(store).delivery_inferences(
                            request, result.execution_receipt['result_ids'])
                        kind = ('CONDITIONAL_PERSISTENT_CONCEPT_REPAIR_JUDGMENT' if '-v3-' in mode
                                else 'CONDITIONAL_PERSISTENT_CONCEPT_JUDGMENT')
                        successors = [item for item in inferred if item.kind == kind]
                        self.assertEqual(len(successors), 2)
                        for item in successors:
                            AnswerAssembler().compact_claim(item)
                            self.assertEqual(item.values['branches'][0]['classifications']
                                             ['current']['actual']['status'], 'MEMBER')
                        # The old expected head remains a compare-and-adopt
                        # fence after cutover, even under a new request identity.
                        stale = replace(request, request_id='stale-adoption')
                        rejected = client.run_sync(stale)
                        self.assertEqual(rejected.status, 'STALE_STATE', rejected.diagnostics)
                        self.assertFalse(rejected.answer or rejected.claim_records)
                self.assertEqual(port.attempts, 0)
                for before in metadata['calls']:
                    after = store._db.execute(
                        'SELECT * FROM calls WHERE task_key=? AND call_id=?',
                        (before['task_key'], before['call_id'])).fetchone()
                    for field in ('request_hash', 'request_bytes', 'response_hash', 'output_bytes'):
                        self.assertEqual(after[field], before[field])

        kinds = {store._get_object(row['object_hash']).kind
                 for row in store._db.execute('SELECT object_hash FROM inferences')}
        self.assertFalse(any('JOINT_CHANGE' in kind for kind in kinds))
        if mode.startswith('judgment-'):
            self.assertTrue(kinds.isdisjoint({'CONCEPT_ADOPTION', 'CONCEPT_SUBSCRIPTION',
                'CONDITIONAL_PERSISTENT_CONCEPT_JUDGMENT',
                'CONDITIONAL_PERSISTENT_CONCEPT_REPAIR_JUDGMENT'}))
        if mode.startswith('persistent-v3-'):
            self.assert_capsules_unchanged(store, old)
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
            self.assertEqual(denied.status, 'DENIED', denied.diagnostics)
            self.assertFalse(denied.answer or denied.claim_records)
            self.assertEqual(port.attempts, 0)
        if erase:
            store.set_readers(old['session'], fixture.owner, 'principles', {'alice'})
            handle = store.current_handles(old['session'], fixture.owner, ('principles',))[0]
            plan = store.plan_source_erasure(old['session'], fixture.owner, 'principles',
                                            expected_version=handle.version)
            store.begin_source_erasure(old['session'], fixture.owner, 'principles',
                expected_version=handle.version, plan_hash=plan['plan_hash'], erasure_id='e' * 32)
            receipt = store.resume_source_erasure(old['session'], fixture.owner, 'e' * 32)
            self.assertTrue(receipt['database_scrubbed'])
            self.assertTrue(plan['objects_to_unlink'])
            self.assertTrue(all(not (store.object_root / digest).exists()
                                for digest in plan['objects_to_unlink']))
            store.rebuild_projections()
            verify_inventory(store._db)
            for metadata in old['requests'].values():
                port = OfflineModelPort('NO_ERASURE_BYPASS')
                denied = HCL(store, principal=fixture.owner, gateway=ModelGateway(store, port)).run_sync(
                    codec.loads(metadata['request'].encode()))
                self.assertFalse(denied.answer or denied.claim_records)
                self.assertNotIn(denied.status, ('COMPLETED', 'PARTIAL'))
                self.assertEqual(port.attempts, 0)

    def test_real_v1_v2_v3_checkpoints_preserve_bytes_unknown_holds_and_zero_resends(self):
        for schema in (3, 4):
            for dialect in ('v1', 'v2', 'v3'):
                with self.subTest(schema=schema, dialect=dialect), self.fixture() as fixture:
                    self.exercise_workload(fixture, schema, 'judgment-' + dialect)

    def test_real_adoption_successors_and_capsule1_survive_every_checkpoint(self):
        # The older exact-pin suite already covers all v2 persistent seams.
        # This predecessor adds the real compressed v3 proof path to each seam.
        for schema in (3, 4):
            for state in ('completed', 'computed', 'committed'):
                mode = 'persistent-v3-' + state
                with self.subTest(schema=schema, workload=mode), self.fixture() as fixture:
                    self.exercise_workload(fixture, schema, mode, erase=state == 'completed')

    def test_exact_pin_rejects_changed_hash_indexes_governance_and_split_controls(self):
        for schema in (3, 4):
            with self.fixture() as fixture:
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


if __name__ == '__main__':
    unittest.main()
