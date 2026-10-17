"""Exact 222-file predecessor, real v1/v2 processes, no rewritten old pins.

Only hcl Python blobs are projected from the identified shipped git tree. All
ledger contents below are synthetic. No provider, sealed data or older test
assertion is needed to manufacture a predecessor identity.
"""

from dataclasses import fields
from hashlib import sha256
import inspect
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
    PERSISTENT_CONCEPT_PREDECESSOR_CODE_HASH,
    RevisionCutover,
)
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.answer import AnswerAssembler
from hcl.runtime.recovery import RecoveryManager
from scripts import witness_unified_concept_judgment as concept_judgment
from scripts import witness_unified_judgment as judgment
from tests import test_unified_s23_upgrade as fixtures


BASELINE = "5c9080559b00b067b31f99cc6ed0ff0c92120feb"
BASELINE_TREE = "9dd64c7a00e50cd1f0ff59874ab19aa3d5461f74"
ADDITIVE_CONTRACTS = {
    "ConceptBinding", "ConceptAdoptionIssue", "ConceptFollowIssue",
    "ConceptQuery", "ConceptDependency",
}
CANDIDATE_SHAPES = {
    "CandidateAuthorization": ["authorization_id", "provider", "model", "source_versions",
        "max_calls", "max_cost_nanos", "max_input_tokens", "max_output_tokens", "rate_version",
        "input_nanos_per_token", "cached_input_nanos_per_token", "output_nanos_per_token",
        "task_fingerprint", "mode"],
    "MeteredCandidateRequest": ["protocol", "authorization", "task_fingerprint", "context", "body"],
    "MeteredCandidateReturn": ["protocol", "visible_text", "provider_response_id", "model",
        "finish_reason", "input_tokens", "cached_input_tokens", "output_tokens", "settled_nanos",
        "validation_code"],
}

PROPOSALS = (
    "from copy import deepcopy\n"
    "from hcl.semantics.segments import segment_snapshot\n"
    + inspect.getsource(judgment.atom)
    + inspect.getsource(judgment.propose).replace("def propose(", "def base_propose(")
    + inspect.getsource(concept_judgment.term)
    + inspect.getsource(concept_judgment.propose).replace("def propose(", "def concept_propose(")
    + "SCENE = " + repr(concept_judgment.SCENE) + "\n"
    + "PRINCIPLES = " + repr(concept_judgment.PRINCIPLES) + "\n"
)

OLD_PROGRAM = PROPOSALS + r'''
from dataclasses import fields
from hashlib import sha256
import json
from pathlib import Path
import sys
from unittest.mock import patch
from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue
from hcl.memory import codec
from hcl.memory.store import StateStore
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.types import LegacySnapshot, LegacySource
from hcl.memory.migrations.revision_upgrade import RevisionCutover, _history
from hcl.memory.migrations.control import version_bundle
from hcl.models.gateway import ModelGateway, OfflineModelPort

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
for dialect, proposer in [('v1', base_propose), ('v2', concept_propose)]:
    for state, seam in [('completed', None), ('returned', 'return_persisted'),
                        ('unknown', 'send_started'), ('computed', 'execution_computed'),
                        ('committed', 'execution_effects_committed')]:
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
        client = HCL(store, principal=owner, gateway=ModelGateway(store, port))
        crashed = False

        def stop(stage):
            global crashed
            if stage == seam and not crashed:
                crashed = True
                raise Crash()

        try:
            with patch.object(store, '_checkpoint', stop):
                result = client.run_sync(request)
        except Crash:
            pass
        if seam:
            assert crashed, key
        else:
            assert result.status == 'PARTIAL', (key, result.diagnostics)

        task = dict(store._db.execute('SELECT * FROM tasks WHERE request_id=?', (key,)).fetchone())
        calls = [dict(row) for row in store._db.execute(
            'SELECT * FROM calls WHERE task_key=?', (task['task_key'],))]
        assert len(calls) == 1, key
        assert calls[0]['state'] == ('SEND_STARTED' if state == 'unknown' else 'RETURNED'), calls
        assert port.attempts == (0 if state == 'unknown' else 1), key
        value = store._get_object(task['result_hash'])
        expected = {}
        if state in ('computed', 'committed'):
            for node in value.nodes.values():
                operation = node.get('result')
                if node.get('operation') == 'compute' and operation is not None:
                    expected.update({item.result_id: sha256(codec.dumps(item)).hexdigest()
                                     for item in operation.candidate_delta.new_inferences})
            assert expected, key
        if state == 'completed':
            expected = {item.result_id: sha256(codec.dumps(item)).hexdigest()
                        for item in store.inferences(session, owner)
                        if item.result_id in result.execution_receipt['result_ids']}
            assert expected, key
        requests[key] = dict(request=codec.dumps(request).decode(), owner_id=store.owner_id,
            task=task, calls=calls, inference_hashes=expected,
            answer_sha256=sha256(value.answer.encode()).hexdigest() if state == 'completed' else None,
            claims_sha256=sha256(codec.dumps(value.claim_records)).hexdigest() if state == 'completed' else None)

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


class PersistentConceptPredecessorUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = subprocess.check_output(
            ['git', 'rev-parse', BASELINE + '^{tree}'], cwd=fixtures.ROOT, text=True).strip()
        if tree != BASELINE_TREE:
            raise AssertionError('exact predecessor tree identity changed')

        class FrozenRuntime(fixtures.RuntimeUpgradeTests):
            baseline = BASELINE
            code_hash = PERSISTENT_CONCEPT_PREDECESSOR_CODE_HASH
            file_count = 222
            old_program = OLD_PROGRAM

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

    def test_exact_v1_v2_checkpoints_preserve_bytes_and_unknown_holds(self):
        fixture = self.fixture()
        for schema in (3, 4):
            source, old, process = fixture.old(schema, 'old-' + str(schema))
            current_shapes = {name: [field.name for field in fields(cls)]
                              for name, cls in codec.CLASSES.items()}
            self.assertEqual(set(current_shapes) - set(old['shapes']),
                             ADDITIVE_CONTRACTS | CANDIDATE_SHAPES.keys())
            self.assertEqual({name: current_shapes[name] for name in CANDIDATE_SHAPES}, CANDIDATE_SHAPES)
            self.assertEqual(old['shapes'], {name: current_shapes[name] for name in old['shapes']})
            with sqlite3.connect(source) as db:
                db.row_factory = sqlite3.Row
                original_rows = self.rows(db)
                original_control = dict(db.execute('SELECT * FROM revision_control').fetchone())
            retained_hashes = set(old['retained_hashes'])
            objects = {path.name: path.read_bytes()
                       for path in source.with_name(source.name + '.objects').iterdir()}
            with self.assertRaises(ValueError):
                StateStore.sqlite(source)
            target = RevisionCutover.upgrade(source, fixture.root / ('new-' + str(schema)), fixture.owner)
            store = target.open_store()
            self.addCleanup(store.close)
            self.assertEqual(store._schema, schema)
            self.assertEqual(store._revision_control['governance_salt'], old['salt'])
            self.assertEqual(self.rows(store._db), original_rows)
            verify_inventory(store._db)
            for digest in retained_hashes:
                body = objects[digest]
                self.assertEqual((store.object_root / digest).read_bytes(), body)
                self.assertEqual(sha256(body).hexdigest(), digest)

            for name, metadata in old['requests'].items():
                with self.subTest(schema=schema, checkpoint=name):
                    request = codec.loads(metadata['request'].encode())
                    self.assertEqual(codec.dumps(request), metadata['request'].encode())
                    port = OfflineModelPort('NO_NEW_SEND')
                    client = HCL(store, principal=fixture.owner, gateway=ModelGateway(store, port))
                    if name.endswith('unknown'):
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
                        if not name.endswith('completed'):
                            RecoveryManager(store).resume_execution(request, expected_owner_id=metadata['owner_id'])
                        if name.endswith('returned'):
                            result = client.run_sync(request)
                        else:
                            with patch.object(LocalModelOperator, 'run',
                                              side_effect=AssertionError('accepted effects cannot recompute')):
                                result = client.run_sync(request)
                        self.assertEqual(result.status, 'PARTIAL', result.diagnostics)
                        self.assertEqual(result.usage['mock_calls'], 1)
                        if name.endswith('completed'):
                            self.assertTrue(result.execution_receipt['replayed'])
                            self.assertEqual(sha256(result.answer.encode()).hexdigest(), metadata['answer_sha256'])
                            self.assertEqual(sha256(codec.dumps(result.claim_records)).hexdigest(), metadata['claims_sha256'])
                            self.assertEqual((store.object_root / metadata['task']['result_hash']).read_bytes(),
                                             objects[metadata['task']['result_hash']])
                        for result_id, digest in metadata['inference_hashes'].items():
                            row = store._db.execute('SELECT object_hash FROM inferences WHERE result_id=?',
                                                    (result_id,)).fetchone()
                            self.assertEqual(row['object_hash'], digest)
                            self.assertEqual(sha256(codec.dumps(store._get_object(digest))).hexdigest(), digest)
                        for inference in store.inferences(old['session'], fixture.owner):
                            if inference.result_id in result.execution_receipt['result_ids']:
                                AnswerAssembler().compact_claim(inference)
                                self.assertIn(inference.kind,
                                    ('CONDITIONAL_ACTION_JUDGMENT', 'CONDITIONAL_CONCEPT_JUDGMENT'))
                    self.assertEqual(port.attempts, 0)

            # The upgrade and known-return resumption do not opt old requests
            # into a new persistent registry or follow-current subscription.
            self.assertTrue(all(inference.kind not in (
                'CONCEPT_ADOPTION', 'CONCEPT_SUBSCRIPTION', 'CONDITIONAL_PERSISTENT_CONCEPT_JUDGMENT')
                for inference in store.inferences(old['session'], fixture.owner)))
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
                if digest in retained_hashes:
                    self.assertEqual((store.object_root / digest).read_bytes(), body)
            RevisionCutover.upgrade(source, target.directory, fixture.owner)
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

    def test_new_pin_rejects_changed_hash_indexes_governance_and_split_controls(self):
        fixture = self.fixture()
        for schema in (3, 4):
            source, old, process = fixture.old(schema, 'reject-' + str(schema))
            with sqlite3.connect(source) as db:
                original = db.execute('SELECT versions FROM revision_control').fetchone()[0]
                namespace = (db.execute('SELECT versions FROM namespace_control').fetchone()[0]
                             if schema == 4 else None)
            cases = ('hash', 'indexes', 'governance') + (('namespace',) if schema == 4 else ())
            for mutation in cases:
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

    def test_exact_predecessor_cutover_crashes_preserve_one_target_and_known_results(self):
        class Crash(BaseException):
            pass

        fixture = self.fixture()
        for seam in ('prepared', 'source_fenced', 'target_activated_unpublished', 'published'):
            with self.subTest(seam=seam):
                source, old, process = fixture.old(4, 'crash-' + seam)
                destination = fixture.root / ('recovered-' + seam)

                def stop(stage):
                    if stage == seam:
                        raise Crash()

                with patch.object(RevisionCutover, '_checkpoint', side_effect=stop), self.assertRaises(Crash):
                    RevisionCutover.upgrade(source, destination, fixture.owner)
                self.assertEqual(fixture.command(process, action='snapshot')['ok'], seam == 'prepared')
                if seam == 'target_activated_unpublished':
                    stage = destination.with_name('.' + destination.name + '.unpublished') / 'state.sqlite'
                    with self.assertRaises((ValueError, HCLFailure)):
                        StateStore.sqlite(stage)
                target = RevisionCutover.upgrade(source, destination, fixture.owner)
                store = target.open_store()
                self.addCleanup(store.close)
                self.assertEqual(store._revision_control['governance_salt'], old['salt'])
                verify_inventory(store._db)
                for dialect in ('v1', 'v2'):
                    completed = old['requests'][dialect + '-completed']
                    port = OfflineModelPort('NO_RECOVERY_SEND')
                    result = HCL(store, principal=fixture.owner, gateway=ModelGateway(store, port)).run_sync(
                        codec.loads(completed['request'].encode()))
                    self.assertEqual(result.status, 'PARTIAL', result.diagnostics)
                    self.assertEqual(sha256(result.answer.encode()).hexdigest(), completed['answer_sha256'])
                    self.assertEqual(sha256(codec.dumps(result.claim_records)).hexdigest(), completed['claims_sha256'])
                    unknown = old['requests'][dialect + '-unknown']
                    request = codec.loads(unknown['request'].encode())
                    with self.assertRaises(HCLFailure) as caught:
                        RecoveryManager(store).resume_execution(request, expected_owner_id=unknown['owner_id'])
                    self.assertEqual(caught.exception.diagnostic.code, 'UNKNOWN_SEND_NO_RESUME')
                    held = HCL(store, principal=fixture.owner, gateway=ModelGateway(store, port)).run_sync(request)
                    self.assertIsNone(held.usage['mock_calls'])
                    self.assertEqual(held.usage['held_mock_calls'], 1)
                    self.assertFalse(held.answer or held.claim_records)
                    self.assertEqual(port.attempts, 0)
                self.assertFalse(fixture.command(process, action='write')['ok'])
                self.assertEqual(RevisionCutover.upgrade(source, destination, fixture.owner).path, target.path)
                with self.assertRaises(ValueError):
                    RevisionCutover.upgrade(source, fixture.root / ('foreign-' + seam), fixture.owner)
