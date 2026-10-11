"""Synthetic actual legacy snapshots, durable side copies and same-engine behavior."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import types
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.compat import CognitionWorkspace
from hcl.cognition.core import ClaimKind, Scope
from hcl.cognition.semantic import AuthorizedText
from hcl.cognition.workspace import CognitionWorkspace as OldWorkspace
from hcl.kernel.types import BudgetSlice, FormalProblem, HCLFailure, Issue, Principal, TaskRequest, thaw
from hcl.memory import codec
from hcl.memory.migrations.compile import source_key
from hcl.memory.migrations.legacy import LegacyAdapter
from hcl.memory.migrations.namespace import MigrationNamespace
from hcl.memory.migrations.types import LegacyRecord, LegacySnapshot, LegacySource
from hcl.memory.sqlite_store import SQLiteStateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.budget import TaskBudgetLedger
from hcl.runtime.recovery import RecoveryManager


class Crash(BaseException):
    pass


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.owner = Principal('tenant', 'alice')
        self.problem = FormalProblem(('Fa',), 'Ga', {'domain': [0], 'constants': {'a': 0},
                                                    'predicates': {'F': [0], 'G': []}})
        self.text = 'Alex: “秘密\r\nα𝄞.”\r\nAlex: unchanged.\n'
        self.source = LegacyAdapter.authorized_text(AuthorizedText('old-source', self.text, version=3,
                                                    permitted_observers=('story-only',)), formal_problem=self.problem)
        self.snapshot = LegacySnapshot((self.source,))
        self.connections = []

    def tearDown(self):
        for store in self.connections:
            try:
                store.close()
            except sqlite3.ProgrammingError:
                pass
        self.tmp.cleanup()

    def imported(self, snapshot=None, name='namespace', **kw):
        return MigrationNamespace.import_snapshot(self.root/name, snapshot or self.snapshot,
            namespace_id=name, owner=self.owner, **kw)

    def opened(self, namespace):
        store = namespace.open_store()
        self.connections.append(store)
        return store

    def facade(self, namespace, store=None, gateway=None):
        receipt = namespace.receipt(self.owner)
        return CognitionWorkspace(store or self.opened(namespace), principal=self.owner,
                                  session_id=receipt['session_id'], gateway=gateway)

    def request(self, namespace, *, kind='source.report', request_id='request'):
        facade = self.facade(namespace)
        mapped = namespace.receipt(self.owner)['source_mapping'][source_key('old-source', 3)]
        return facade.prepare('Use the actual authorized source.', source_ids=(mapped['source_id'],),
                              issue_kind=kind, request_id=request_id)

    def test_exact_unicode_original_same_engine_real_logic_and_restart(self):
        ns = self.imported()
        req = self.request(ns)
        store = self.opened(ns)
        result = HCL(store, principal=self.owner).run_sync(req)
        self.assertEqual(result.status, 'COMPLETED')
        self.assertIn(self.text, result.answer)
        self.assertEqual(result.claim_records[0].epistemic_status, 'SOURCE_REPORT_NOT_TRUTH')
        restored = codec.decode(thaw(ns.legacy_view(self.owner)))
        self.assertEqual(restored['sources'][0]['text'], self.text)
        self.assertEqual(sha256(restored['sources'][0]['text'].encode()).digest(), sha256(self.text.encode()).digest())
        logic = self.request(ns, kind='logic.check_interpretation', request_id='logic')
        computed = HCL(store, principal=self.owner).run_sync(logic)
        self.assertIn('conclusion is false', computed.answer)
        self.assertTrue(next(iter(computed.execution_receipt['inference_values'].values()))['is_countermodel'])
        store.close()
        replay = HCL(self.opened(ns), principal=self.owner).run_sync(logic)
        self.assertEqual(replay.answer, computed.answer)
        self.assertTrue(replay.execution_receipt['replayed'])

    def test_opposite_explicit_interpretation_changes_actual_values_and_answer(self):
        first = self.imported(name='first')
        other = replace(self.problem, interpretation={'domain': [0], 'constants': {'a': 0},
                                                      'predicates': {'F': [0], 'G': [0]}})
        second = self.imported(LegacySnapshot((replace(self.source, formal_problem=other),)), name='second')
        results = [HCL(self.opened(ns), principal=self.owner).run_sync(self.request(ns, kind='logic.check_interpretation'))
                   for ns in (first, second)]
        self.assertNotEqual(results[0].answer, results[1].answer)
        self.assertEqual([next(iter(r.execution_receipt['inference_values'].values()))['conclusion'] for r in results], [False, True])

    def test_idempotence_restart_zero_new_events_and_collision_no_overwrite(self):
        ns = self.imported()
        before = ns.audit(self.owner)
        original = ns.path.read_bytes()
        again = self.imported()
        self.assertEqual(before, again.audit(self.owner))
        self.assertEqual(original, ns.path.read_bytes())
        with self.assertRaises(ValueError):
            self.imported(LegacySnapshot((replace(self.source, text='different'),)))
        self.assertEqual(before, ns.audit(self.owner))
        self.assertEqual(original, ns.path.read_bytes())

    def test_original_workspace_is_unchanged_and_lifecycles_preserved(self):
        old = OldWorkspace()
        old.put_source('changing', 'old source')
        old.put_source('changing', 'new source')
        old.put_source('removed', 'withdrawn source')
        old.remove_source('removed')
        before = repr((old._documents, old._versions, old.core.spans, old.core.withdrawn))
        snapshot = LegacyAdapter.workspace(old)
        ns = self.imported(snapshot)
        self.assertEqual(before, repr((old._documents, old._versions, old.core.spans, old.core.withdrawn)))
        rows = ns.receipt(self.owner)['records']
        sources = [r for r in rows if r['kind'] == 'SOURCE_DOCUMENT']
        self.assertEqual({r['lifecycle'] for r in sources}, {'CURRENT', 'HISTORICAL', 'WITHDRAWN'})
        self.assertTrue(all(r['disposition'] == 'QUARANTINED' for r in sources if r['lifecycle'] != 'CURRENT'))
        self.assertEqual(ns.audit(self.owner)['counts']['sources'], 1)

    def test_real_old_support_groups_interpretation_and_revisions_do_not_become_truth(self):
        old = OldWorkspace()
        old.put_source('s', 'Alex says this.')
        scope = Scope(actor='Alex', source_ids=('s',))
        report = old.core.claim(scope, ClaimKind.SOURCE_REPORT, {'said': 'this'})
        old.core.support(report, old._spans['s'])
        interpretation = old.core.claim(scope, ClaimKind.SYSTEM_INTERPRETATION, {'maybe': 'that'})
        old.core.support(interpretation, report)
        old.core.interpret(interpretation, required_premises=(report,), unknown_conditions=('missing-world-evidence',))
        ns = self.imported(LegacyAdapter.workspace(old))
        rows = ns.receipt(self.owner)['records']
        target = next(r for r in rows if r['old_key'] == interpretation)
        self.assertEqual(target['kind'], 'SYSTEM_INTERPRETATION')
        self.assertEqual(target['truth'], 'NOT_ESTABLISHED')
        self.assertFalse(target['converted']['interpretation_executable'])
        self.assertEqual(target['converted']['grounding_meaning'], 'RECORDED_DERIVATION_ROOTS_ONLY')
        self.assertEqual(ns.audit(self.owner)['counts']['inferences'], 0)
        original = codec.decode(thaw(ns.legacy_view(self.owner)))
        record = next(r for r in original['records'] if r['old_id'] == interpretation)
        self.assertTrue(record['payload']['grounded'])
        self.assertEqual(record['payload']['interpretation']['required_premises'], [report])

    def test_incomplete_unknown_and_scoped_records_are_recoverably_quarantined(self):
        rows = (LegacyRecord('unknown', 'CUSTOM_OLD_KIND', {'recover': 'private retained field'}),
                LegacyRecord('broken', 'SYSTEM_INTERPRETATION', {'supports': [['absent']], 'grounded': True}),
                LegacyAdapter.receipt({'schema': 'hcl-shared-evidence-v1', 'claims': [], 'spans': []}))
        ns = self.imported(LegacySnapshot((self.source,), rows))
        records = [r for r in ns.receipt(self.owner)['records'] if r['kind'] != 'SOURCE_DOCUMENT']
        self.assertTrue(all(r['disposition'] == 'QUARANTINED' for r in records))
        self.assertIn('recover', records[0]['recoverable_fields'])
        self.assertIn('private retained field', str(ns.legacy_view(self.owner)))

    def test_artificial_order_dates_preserved_without_calendar_or_global_actor(self):
        from hcl.v1.narrative import prepare_narrative
        events, _, _, _ = prepare_narrative('Alex attended the meeting. Alex left.', 'Why did Alex attend?')
        records = tuple(LegacyAdapter.event(event, provenance='v1.prepare_narrative') for event in events)
        ns = self.imported(LegacySnapshot((self.source,), records))
        original = codec.decode(thaw(ns.legacy_view(self.owner)))
        self.assertEqual(original['records'][0]['payload']['original']['valid_time'], events[0].valid_time)
        self.assertEqual(original['records'][0]['payload']['time_kind'], 'SOURCE_ORDER')
        self.assertIsNone(original['records'][0]['payload']['event_time'])
        regular = LegacyAdapter.event(replace(events[0], source_id='ordinary'), provenance='caller_event_snapshot')
        self.assertEqual(regular.payload['time_kind'], 'UNVERIFIED_LEGACY_TIME_LABEL')
        self.assertFalse(regular.payload['calendar_time_established'])

    def test_report_families_and_order_anchors_preserve_actual_old_types(self):
        from hcl.cognition.report_provenance import ReportAssessment
        from hcl.narrative_order import Anchor, Before, NarrativeOrder
        report = ReportAssessment(Scope(source_ids=('old-source',)), 'What was reported?',
                                  '[{"expression_id":"r1"},{"expression_id":"r2"}]',
                                  '[{"members":["r1","r2"],"relation":"COPIED"}]', '[]')
        order = NarrativeOrder('source-local', 'A before B', {'A': Anchor(0, 1, 'A'), 'B': Anchor(9, 10, 'B')},
                               [Before('A', 'B', Anchor(0, 10, 'A before B'))])
        records = (LegacyAdapter.report(report), LegacyAdapter.order(order))
        ns = self.imported(LegacySnapshot((self.source,), records))
        original = codec.decode(thaw(ns.legacy_view(self.owner)))['records']
        self.assertIsNone(original[0]['payload']['independent_support_count'])
        self.assertEqual(original[0]['payload']['families'][0]['members'], ['r1', 'r2'])
        self.assertEqual(original[1]['payload']['relations'][0]['evidence']['quote'], 'A before B')
        self.assertEqual(order.compare('A', 'B')['relation'], 'BEFORE')

    def test_story_observers_do_not_provision_system_access_and_foreign_metadata_denied(self):
        ns = self.imported()
        req = self.request(ns)
        stranger = Principal('tenant', 'story-only')
        denied = HCL(self.opened(ns), principal=stranger).run_sync(replace(req, principal=stranger))
        self.assertEqual(denied.status, 'DENIED')
        for actor in (stranger, Principal('foreign', 'alice')):
            for operation in (ns.receipt, ns.legacy_view, ns.audit):
                with self.assertRaises(HCLFailure) as caught:
                    operation(actor)
                self.assertEqual(caught.exception.status, 'DENIED')

    def test_revoked_owner_cannot_read_legacy_content_or_metadata(self):
        ns = self.imported(readers={'old-source': ('alice', 'bob')})
        req = self.request(ns)
        self.opened(ns).set_readers(req.session_id, self.owner, req.source_handles[0].source_id, {'bob'})
        for operation in (ns.receipt, ns.legacy_view):
            with self.assertRaises(HCLFailure):
                operation(self.owner)
        ns.rollback(self.owner, expected_generation=1)
        with self.assertRaises(HCLFailure):
            ns.legacy_view(self.owner)

    def test_compat_same_run_stream_and_callback_never_called(self):
        ns = self.imported()
        req = self.request(ns, kind='logic.check_interpretation')
        facade = self.facade(ns)
        direct = HCL(facade.store, principal=self.owner).run_sync(req)
        replay = asyncio.run(facade.run(req))
        self.assertEqual(replay.answer, direct.answer)
        async def stream():
            return [event async for event in facade.stream(req)]
        self.assertEqual(asyncio.run(stream())[-1].result.answer, direct.answer)
        called = []
        with self.assertRaises(ValueError):
            facade.answer('q', lambda _: called.append(True), source_ids=(req.source_handles[0].source_id,))
        self.assertEqual(called, [])
        with self.assertRaises(ValueError):
            facade.prepare('q', source_ids=(req.source_handles[0].source_id,), through_order=1)

    def test_prepared_compat_task_rejects_source_change(self):
        ns = self.imported()
        facade = self.facade(ns)
        req = self.request(ns)
        facade.put_source(req.source_handles[0].source_id, 'new source')
        result = asyncio.run(facade.run(req))
        self.assertEqual(result.status, 'STALE_STATE')
        self.assertEqual(result.answer, '')

    def test_import_fault_never_publishes_partial_namespace(self):
        for stage in ('import_before_commit', 'import_committed_unpublished'):
            with patch.object(MigrationNamespace, '_checkpoint', side_effect=lambda value: (_ for _ in ()).throw(Crash()) if value == stage else None):
                with self.assertRaises(Crash):
                    self.imported(name=stage)
            self.assertFalse((self.root/stage).exists())
            self.assertEqual(self.imported(name=stage).audit(self.owner)['counts']['sources'], 1)

    def test_atomic_rollback_preserves_original_and_new_events_and_blocks_old_connections(self):
        ns = self.imported()
        req = self.request(ns)
        writer, peer = self.opened(ns), self.opened(ns)
        self.assertEqual(HCL(writer, principal=self.owner).run_sync(req).status, 'COMPLETED')
        original, audit = ns.legacy_view(self.owner), ns.audit(self.owner)
        control = ns.rollback(self.owner, expected_generation=1)
        self.assertEqual(control['generation'], 2)
        self.assertEqual(ns.legacy_view(self.owner), original)
        self.assertEqual(ns.audit(self.owner)['counts'], audit['counts'])
        for store in (writer, peer, self.opened(ns)):
            self.assertEqual(HCL(store, principal=self.owner).run_sync(req).status, 'DENIED')
            for operation in (lambda: store.put_source(req.session_id, self.owner, 'new', 'not committed'),
                              lambda: store.set_readers(req.session_id, self.owner, req.source_handles[0].source_id, {'alice'}),
                              store.rebuild_projections):
                with self.assertRaises(HCLFailure) as caught:
                    operation()
                self.assertEqual(caught.exception.diagnostic.code, 'NAMESPACE_READ_ONLY')
        self.assertEqual(ns.audit(self.owner)['counts'], audit['counts'])
        self.assertEqual(self.imported().receipt(self.owner)['mode'], 'LEGACY_READ_ONLY')

    def test_rollback_transaction_fault_changes_neither_mode_nor_generation(self):
        ns = self.imported()
        before = ns.receipt(self.owner)
        with patch.object(MigrationNamespace, '_checkpoint', side_effect=Crash):
            with self.assertRaises(Crash):
                ns.rollback(self.owner, expected_generation=1)
        self.assertEqual(ns.receipt(self.owner), before)
        ns.rollback(self.owner, expected_generation=1)
        with self.assertRaises(HCLFailure):
            ns.rollback(self.owner, expected_generation=1)

    def test_cached_old_wal_result_cannot_cross_rollback_delivery(self):
        for streamed in (False, True):
            ns = self.imported(name=f'cached-{streamed}')
            req = self.request(ns)
            store = self.opened(ns)
            engine = HCL(store, principal=self.owner)
            self.assertEqual(engine.run_sync(req).status, 'COMPLETED')
            get = store._get_object
            fired = []
            def revoke(digest):
                result = get(digest)
                from hcl.kernel.types import TaskResult
                if isinstance(result, TaskResult) and not fired:
                    fired.append(True)
                    ns.rollback(self.owner, expected_generation=1)
                return result
            async def stream():
                return [event async for event in engine.stream(req)]
            with patch.object(store, '_get_object', side_effect=revoke):
                result = asyncio.run(stream())[-1].result if streamed else engine.run_sync(req)
            self.assertEqual(result.status, 'DENIED')
            self.assertEqual(result.answer, '')
            self.assertNotIn('old-source', repr(result))
            self.assertNotIn('秘密', repr(result))

    def test_unknown_budget_hold_survives_terminal_rollback_without_resend(self):
        ns = self.imported()
        req = replace(self.request(ns, kind='model.respond'), budget=BudgetSlice(max_mock_calls=1))
        store = self.opened(ns)
        port = OfflineModelPort(fault='send_unknown')
        gateway = ModelGateway(store, port=port)
        self.assertEqual(HCL(store, principal=self.owner, gateway=gateway).run_sync(req).status, 'SEND_UNKNOWN')
        before = ns.audit(self.owner)
        ns.rollback(self.owner, expected_generation=1)
        after = HCL(store, principal=self.owner, gateway=gateway).run_sync(req)
        self.assertEqual(after.status, 'DENIED')
        self.assertEqual(port.attempts, 1)
        self.assertEqual(ns.audit(self.owner)['calls'], before['calls'])
        with self.assertRaises(HCLFailure):
            RecoveryManager(store).recover_abandoned(self.owner, req.session_id, req.request_id, expected_owner_id=store.owner_id)

    def test_new_ledger_write_and_rollback_race_is_serialized(self):
        ns = self.imported()
        req = self.request(ns)
        store = self.opened(ns)
        barrier = Barrier(2)
        def writing():
            barrier.wait()
            try:
                store.put_source(req.session_id, self.owner, 'extra', 'atomic source')
                return 'committed'
            except HCLFailure:
                return 'fenced'
        def rollback():
            barrier.wait()
            return ns.rollback(self.owner, expected_generation=1)
        with ThreadPoolExecutor(max_workers=2) as executor:
            write = executor.submit(writing)
            back = executor.submit(rollback)
            outcome = write.result()
            back.result()
        self.assertEqual(ns.audit(self.owner)['counts']['sources'], 2 if outcome == 'committed' else 1)

    def test_schema_two_missing_control_or_corrupt_package_fails_closed(self):
        ns = self.imported()
        receipt = ns.receipt(self.owner)
        blob = ns.directory/'state.sqlite.objects'/receipt['package_hash']
        original = blob.read_bytes()
        blob.write_bytes(b'corrupt')
        with self.assertRaises(HCLFailure):
            ns.legacy_view(self.owner)
        blob.write_bytes(original)
        with sqlite3.connect(ns.path) as db:
            db.execute('DELETE FROM namespace_control')
        with self.assertRaises(HCLFailure):
            ns.open_store()

    def test_rebuild_keeps_control_and_legacy_schema_one_refuses_controlled_schema(self):
        ns = self.imported()
        before = ns.receipt(self.owner)
        self.opened(ns).rebuild_projections()
        self.assertEqual(before, ns.receipt(self.owner))
        with sqlite3.connect(ns.path) as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
        self.assertEqual(version, 2)
        # Execute the actual known predecessor module, never a rewritten gate.
        source = subprocess.check_output(['git', 'show',
            '21b63e227ead583ded0575f2ab65b073ba26733c:hcl/memory/sqlite_store.py'], text=True)
        old = types.ModuleType('s12_predecessor_store')
        exec(compile(source, 'fixed-s12-sqlite_store.py', 'exec'), old.__dict__)
        with self.assertRaisesRegex(ValueError, 'unsupported store schema'):
            old.SQLiteStateStore(ns.path)
        ordinary = SQLiteStateStore(self.root/'ordinary.sqlite')
        self.connections.append(ordinary)
        self.assertEqual(ordinary._db.execute('PRAGMA user_version').fetchone()[0], 1)


    def test_partial_span_exact_hash_and_offset_failure_is_quarantined(self):
        old = OldWorkspace()
        old.put_source('old-source', self.text)
        snapshot = LegacyAdapter.workspace(old)
        records = list(snapshot.records)
        original = records[0]
        records[0] = replace(original, payload={**dict(original.payload), 'quote': 'not original'})
        ns = self.imported(replace(snapshot, records=tuple(records)))
        record = next(r for r in ns.receipt(self.owner)['records'] if r['kind'] == 'SOURCE_SPAN')
        self.assertEqual(record['reasons'], ('SOURCE_SPAN_IDENTITY_MISMATCH',))
        self.assertEqual(record['disposition'], 'QUARANTINED')

    def test_invalid_unicode_and_ambiguous_current_are_preserved_but_not_executable(self):
        invalid = replace(self.source, text='bad\ud800')
        ns = self.imported(LegacySnapshot((invalid,)))
        self.assertEqual(ns.audit(self.owner)['counts']['sources'], 0)
        self.assertEqual(ns.receipt(self.owner)['records'][0]['reasons'], ('INVALID_SOURCE_ENCODING',))
        ambiguous = self.imported(LegacySnapshot((self.source, replace(self.source, version=4))), name='ambiguous')
        self.assertEqual(ambiguous.audit(self.owner)['counts']['sources'], 0)
        self.assertTrue(all('AMBIGUOUS_CURRENT_VERSION' in r['reasons'] for r in ambiguous.receipt(self.owner)['records']))

    def test_namespace_legacy_delivery_rechecks_after_old_read_snapshot(self):
        for method in ('legacy_view', 'receipt'):
            ns = self.imported(name=method, readers={'old-source': ('alice', 'bob')})
            request = self.request(ns)
            store = self.opened(ns)
            get = ns._package
            fired = []
            def revoke(row):
                value = get(row)
                if not fired:
                    fired.append(True)
                    store.set_readers(request.session_id, self.owner, request.source_handles[0].source_id, {'bob'})
                return value
            with patch.object(ns, '_package', side_effect=revoke):
                with self.assertRaises(HCLFailure):
                    getattr(ns, method)(self.owner)

    def test_rollback_after_logic_finish_clears_all_delivery_fields(self):
        for streamed in (False, True):
            ns = self.imported(name=f'finish-{streamed}')
            req = self.request(ns, kind='logic.check_interpretation')
            store = self.opened(ns)
            def stop(stage):
                if stage == 'task_finished':
                    ns.rollback(self.owner, expected_generation=1)
            async def run():
                return [event async for event in HCL(store, principal=self.owner).stream(req)]
            with patch.object(store, '_checkpoint', side_effect=stop):
                result = asyncio.run(run())[-1].result if streamed else HCL(store, principal=self.owner).run_sync(req)
            self.assertEqual(result.status, 'DENIED')
            self.assertEqual(result.answer, '')
            self.assertEqual(result.claim_records, ())
            self.assertNotIn('inference_values', result.execution_receipt)
            self.assertNotIn('source_versions', result.execution_receipt)
            self.assertEqual(ns.audit(self.owner)['counts']['inferences'], 1)

    def test_inflight_send_cannot_commit_or_redeliver_after_rollback(self):
        ns = self.imported()
        req = replace(self.request(ns, kind='model.respond'), budget=BudgetSlice(max_mock_calls=1))
        store = self.opened(ns)
        port = OfflineModelPort('private model response')
        gateway = ModelGateway(store, port=port)
        original = OfflineModelPort.generate
        async def stop(port, text):
            ns.rollback(self.owner, expected_generation=1)
            return await original(port, text)
        with patch.object(OfflineModelPort, 'generate', stop):
            result = HCL(store, principal=self.owner, gateway=gateway).run_sync(req)
        self.assertEqual(result.answer, '')
        self.assertNotIn('private model response', repr(result))
        self.assertEqual(port.attempts, 1)
        self.assertEqual(ns.audit(self.owner)['calls'][0]['state'], 'SEND_STARTED')
        self.assertEqual(ns.audit(self.owner)['calls'][0]['attempted'], None)

    def test_version_bundle_is_fixed_and_no_reactivation_bypass(self):
        ns = self.imported()
        with patch('hcl.memory.migrations.control.version_bundle', return_value={'different': True}):
            with self.assertRaisesRegex(ValueError, 'version mismatch'):
                ns.open_store()
        ns.rollback(self.owner, expected_generation=1)
        self.assertFalse(hasattr(ns, 'activate'))
        self.assertEqual(self.imported().receipt(self.owner)['generation'], 2)

    def test_real_and_or_groups_and_withdrawn_analyst_revision_are_preserved(self):
        old = OldWorkspace()
        old.put_source('s', 'A and B are reported.')
        scope = Scope(actor='Alex', source_ids=('s',))
        reports = [old.core.claim(scope, ClaimKind.SOURCE_REPORT, {'report': value}) for value in ('a', 'b')]
        for report in reports:
            old.core.support(report, old._spans['s'])
        prior = old.core.claim(scope, ClaimKind.SYSTEM_INTERPRETATION, {'reading': 'prior'})
        old.core.support(prior, *reports)
        old.core.support(prior, reports[0])
        new = old.core.claim(scope, ClaimKind.SYSTEM_INTERPRETATION, {'reading': 'revised'})
        old.core.support(new, reports[0])
        old.core.replace_interpretation(prior, new, reasons=(reports[0],))
        ns = self.imported(LegacyAdapter.workspace(old))
        receipt = ns.receipt(self.owner)
        record = next(row for row in receipt['records'] if row['old_key'] == prior)
        self.assertEqual(sorted(map(len, record['converted']['support_groups'])), [1, 2])
        self.assertEqual(record['lifecycle'], 'WITHDRAWN')
        revision = next(row for row in receipt['records'] if row['kind'] == 'INTERPRETATION_REVISION')
        self.assertEqual(revision['converted']['old'], receipt['record_mapping'][prior])
        self.assertEqual(revision['converted']['new'], receipt['record_mapping'][new])
        self.assertEqual(revision['converted']['kind'], 'ANALYST_INTERPRETATION_REVISION_NOT_CHARACTER_CHANGE')

    def test_quarantined_conflicting_versions_cannot_bypass_package_acl(self):
        for mixed in (False, True):
            secret = (LegacySource('private', 1, 'BOB_ONLY_QUARANTINE_CANARY'),
                      LegacySource('private', 2, 'BOB_ONLY_QUARANTINE_CANARY_V2'))
            sources = secret + ((self.source,) if mixed else ())
            readers = {'private': ('bob',)}
            if mixed:
                readers['old-source'] = ('alice',)
            ns = self.imported(LegacySnapshot(sources), name=f'quarantine-{mixed}', readers=readers)
            self.assertEqual(ns.audit(self.owner)['counts']['sources'], int(mixed))
            for rolled_back in (False, True):
                if rolled_back:
                    ns.rollback(self.owner, expected_generation=1)
                for method in (ns.receipt, ns.legacy_view):
                    with self.assertRaises(HCLFailure) as caught:
                        method(self.owner)
                    self.assertEqual(caught.exception.status, 'DENIED')
                    self.assertNotIn('BOB_ONLY', str(caught.exception))
                    self.assertNotIn('private', str(caught.exception))

    def test_historical_and_withdrawn_originals_also_require_explicit_import_acl(self):
        for status in ('HISTORICAL', 'WITHDRAWN'):
            snapshot = LegacySnapshot((self.source, LegacySource('old-private', 1, 'HISTORICAL_PRIVATE', status)))
            with self.assertRaises(ValueError):
                self.imported(snapshot, name=f'missing-{status}', readers={'old-source': ('alice',)})
            ns = self.imported(snapshot, name=status, readers={'old-source': ('alice',), 'old-private': ('bob',)})
            for method in (ns.receipt, ns.legacy_view):
                with self.assertRaises(HCLFailure):
                    method(self.owner)


if __name__ == '__main__':
    unittest.main()
