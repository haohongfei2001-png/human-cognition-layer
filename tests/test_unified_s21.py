"""Injected extraction proposals, general compilation and actual solver outcomes.

Fixtures contain AST proposals, never answer labels. They prove downstream
computation and controls, not that a model learned ordinary-language semantics.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from threading import Event
import unittest
from unittest.mock import patch

from hcl import HCL
from hcl.compat import CognitionWorkspace
from hcl.kernel.types import BudgetSlice, HCLFailure, Issue, Principal, TaskRequest, thaw
from hcl.memory.sqlite_store import SQLiteStateStore
from hcl.models.gateway import AuthorizedContext, CallSpec, ModelGateway, OfflineModelPort
from hcl.operators.semantic_logic import ReadingLogicOperator
from hcl.quantified_logic import check_countermodel, parse
from hcl.runtime.answer import AnswerAssembler
from hcl.semantics.compiler import SemanticCompiler
from hcl.semantics.frames import SemanticProfile
from hcl.semantics.segments import segment_snapshot


def atom(predicate, *entities):
    return {'op': 'atom', 'predicate': predicate, 'args': [{'entity': entity} for entity in entities or ('person',)]}


def var_atom(predicate, *variables):
    return {'op': 'atom', 'predicate': predicate, 'args': [{'var': variable} for variable in variables]}


def unary(op, body, variable=None):
    return {'op': op, 'arg': body} if op == 'not' else {'op': op, 'var': variable, 'body': body}


def binary(op, left, right):
    return {'op': op, 'left': left, 'right': right}


class SemanticExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary.name)/'state.sqlite'
        self.owner = Principal('tenant', 'alice')
        self.store = SQLiteStateStore(self.path)
        self.store.create_session('s', self.owner, frozenset({'bob'}))
        self.text = '如果张三收到通知，他就会出席。\r\n张三收到通知。\n'
        self.question = '能推出张三会出席吗？'
        self.handle = self.store.put_source('s', self.owner, 'source', self.text)
        self.request = TaskRequest('semantic', self.question, (self.handle,), 's', self.owner,
            budget=BudgetSlice(max_mock_calls=1, max_output_bytes=131072),
            issue=Issue('reason', 'logic.compare_semantic_readings'))
        self.snapshot = self.store.snapshot('s', self.owner, (self.handle,))
        self.segments = segment_snapshot(self.snapshot, self.question)
        self.p, self.q = atom('received'), atom('attends')

    def tearDown(self):
        try:
            self.store.close()
        except Exception:
            pass
        self.temporary.cleanup()

    def fixture(self, cases=None, *, entities=True, relational=False):
        source_refs = [s.segment_id for s in self.segments if s.kind == 'SOURCE']
        query_refs = [s.segment_id for s in self.segments if s.kind == 'QUESTION']
        labels = [('received', '收到通知', 1), ('attends', '出席', 1)]
        if relational:
            labels = [('relation', 'admires', 2)]
        data = {'schema': 'hcl-semantic-candidates-1',
            'frames': [{'id': 'source-reading', 'kind': 'SOURCE_DISCOURSE', 'parent': None, 'segment_ids': source_refs}],
            'entities': [{'id': 'person', 'label': '张三', 'source_id': 'source', 'segment_ids': source_refs}] if entities else [],
            'predicates': [{'id': key, 'label': label, 'arity': arity, 'segment_ids': source_refs+query_refs}
                           for key, label, arity in labels], 'readings': []}
        if cases is None:
            cases = [([binary('implies', self.p, self.q), self.p], self.q)]
        for i, (premises, query) in enumerate(cases):
            def meaning(ast, j, question=False):
                return {'id': f'meaning-{i}-{j}', 'natural_reading': 'A proposed interpretation, not certified meaning.',
                        'ast': ast, 'frame': 'source-reading', 'segment_ids': query_refs if question else source_refs,
                        'origin': 'INTERPRETATION'}
            data['readings'].append({'id': f'reading-{i}', 'frame': 'source-reading', 'assumptions': [],
                'premises': [meaning(ast, j) for j, ast in enumerate(premises)], 'query': meaning(query, 'query', True),
                'unparsed_segments': [], 'alignment': {'judgment': 'SUPPORTED', 'explanation': 'Injected proposal only.'}})
        return data

    def run_candidate(self, candidate, *, request=None, profile=None, port=None):
        port = port or OfflineModelPort(json.dumps(candidate, ensure_ascii=False))
        engine = HCL(self.store, principal=self.owner, gateway=ModelGateway(self.store, port), semantic_profile=profile)
        return engine.run_sync(request or self.request), port

    @staticmethod
    def values(result):
        return next(iter(result.execution_receipt['inference_values'].values()))

    def test_chinese_conditional_real_computation_and_actual_result_consumption(self):
        result, port = self.run_candidate(self.fixture())
        self.assertEqual(result.status, 'COMPLETED', result.diagnostics)
        values = self.values(result)
        self.assertEqual(values['label'], 'True')
        self.assertIn('follows in this formal reading', result.answer)
        used = {ref.field: ref.value for ref in result.claim_records[0].used_result_fields}
        self.assertEqual(used['readings'], values['readings'])
        self.assertFalse(values['semantic_certified'])
        self.assertEqual(port.attempts, 1)
        self.assertEqual(result.usage['classification_batches_completed'], 1)
        self.assertEqual(result.usage['solver_checks_upper_bound'], 15)
        self.assertEqual(result.usage['provider_calls'], 0)

    def test_negation_missing_condition_converse_and_inconsistency_change_actual_results(self):
        cases = [([unary('not', self.q)], self.q),
                 ([binary('implies', self.p, self.q), unary('not', self.p)], self.q),
                 ([binary('implies', self.p, self.q), self.q], self.p),
                 ([self.p, unary('not', self.p)], self.q)]
        result, _ = self.run_candidate(self.fixture(cases))
        self.assertEqual(result.status, 'PARTIAL')
        rows = self.values(result)['readings']
        self.assertEqual([r['label'] for r in rows], ['False', 'Uncertain', 'Uncertain', None])
        self.assertEqual(rows[-1]['status'], 'INCONSISTENT_PREMISES')
        self.assertIn('no conclusion is licensed by explosion', result.answer)
        self.assertTrue(rows[2]['countermodels'])
        self.assertTrue(any(w['query_value'] is False for w in rows[2]['countermodels']))

    def test_english_negation_scope_ambiguity_is_not_silently_selected(self):
        handle = self.store.put_source('s', self.owner, 'source', "Everyone didn't attend.\n")
        self.request = replace(self.request, question='Did Mary Jane attend?', source_handles=(handle,))
        self.snapshot = self.store.snapshot('s', self.owner, (handle,))
        self.segments = segment_snapshot(self.snapshot, self.request.question)
        attend_x = var_atom('attends', 'x')
        candidate = self.fixture([([unary('not', unary('all', attend_x, 'x'))], self.q),
                                  ([unary('all', unary('not', attend_x), 'x')], self.q)])
        candidate['entities'][0]['label'] = 'Mary Jane'
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, 'PARTIAL')
        values = self.values(result)
        self.assertEqual(values['status'], 'READING_DEPENDENT')
        self.assertEqual([r['label'] for r in values['readings']], ['Uncertain', 'False'])
        self.assertIn('No unique unconditional answer', result.answer)
        self.assertIn('Mary Jane', result.answer)

    def test_quantifier_order_uses_an_independently_checked_domain_two_countermodel(self):
        relation = var_atom('relation', 'x', 'y')
        p = unary('all', unary('some', relation, 'y'), 'x')
        q = unary('some', unary('all', relation, 'x'), 'y')
        result, _ = self.run_candidate(self.fixture([([p], q)], entities=False, relational=True))
        self.assertEqual(result.status, 'COMPLETED', result.diagnostics)
        row = self.values(result)['readings'][0]
        self.assertEqual(row['label'], 'Uncertain')
        witness = next(w for w in row['countermodels'] if w['check_target'] == 'QUERY_FALSE')
        self.assertEqual(witness['model']['domain'], (0, 1))
        checked = check_countermodel([parse(f) for f in row['formal_premises']], parse(row['formal_query']), thaw(witness['model']))
        self.assertTrue(checked['is_countermodel'])
        self.assertEqual(witness['scenario']['kind'], 'GENERATED_FORMAL_SCENARIO_NOT_SOURCE_QUOTATION')

    def test_original_and_negated_query_witnesses_have_distinct_true_values(self):
        result, _ = self.run_candidate(self.fixture([([self.p], self.q)]))
        witnesses = self.values(result)['readings'][0]['countermodels']
        self.assertEqual({(w['check_target'], w['query_value']) for w in witnesses}, {('QUERY_FALSE', False), ('QUERY_TRUE', True)})
        self.assertTrue(all(w['target_value'] is False and all(w['premise_values']) for w in witnesses))

    def test_unseen_propositional_compositions_against_boolean_oracle(self):
        def evaluate(tree, p, q):
            op = tree['op']
            if op == 'atom':
                return p if tree['predicate'] == 'received' else q
            if op == 'not':
                return not evaluate(tree['arg'], p, q)
            a, b = evaluate(tree['left'], p, q), evaluate(tree['right'], p, q)
            return {'and': a and b, 'or': a or b, 'implies': not a or b, 'iff': a == b}[op]
        cases, expected = [], []
        for op in ('and', 'or', 'implies', 'iff'):
            for negated in (False, True):
                premise = binary(op, self.p, unary('not', self.q) if negated else self.q)
                query = unary('not', binary('and', unary('not', self.p), self.q))
                possibilities = {evaluate(query, p, q) for p, q in itertools.product((False, True), repeat=2)
                                 if evaluate(premise, p, q)}
                expected.append('True' if possibilities == {True} else 'False' if possibilities == {False} else 'Uncertain')
                cases.append(([premise], query))
        result, _ = self.run_candidate(self.fixture(cases))
        self.assertEqual([row['label'] for row in self.values(result)['readings']], expected)
        self.assertEqual(result.usage['classification_batches_completed'], 8)

    def test_source_segments_preserve_unicode_crlf_bytes_and_repeated_locations(self):
        text = 'Mary Jane: e\u0301🙂。\r\n重复。 重复。\n'
        handle = self.store.put_source('s', self.owner, 'u', text)
        snapshot = self.store.snapshot('s', self.owner, (handle,))
        segments = [s for s in segment_snapshot(snapshot, 'What?') if s.kind == 'SOURCE']
        self.assertEqual(''.join(s.text for s in segments), text)
        for segment in segments:
            self.assertEqual(text[segment.start:segment.end], segment.text)
            self.assertEqual(text.encode()[segment.byte_start:segment.byte_end].decode(), segment.text)
        self.assertEqual(segments, [s for s in segment_snapshot(snapshot, 'What?') if s.kind == 'SOURCE'])
        self.assertEqual(len({s.segment_id for s in segments}), len(segments))
        other = self.store.put_source('s', self.owner, 'u', text)
        changed = segment_snapshot(self.store.snapshot('s', self.owner, (other,)), 'What?')
        self.assertFalse({s.segment_id for s in segments} & {s.segment_id for s in changed})

    def test_gateway_really_sends_segment_ids_exact_original_and_unchanged_question(self):
        seen = []
        original = OfflineModelPort.generate
        async def capture(port, serialized):
            seen.append(json.loads(serialized))
            return await original(port, serialized)
        with patch.object(OfflineModelPort, 'generate', capture):
            result, _ = self.run_candidate(self.fixture())
        self.assertEqual(result.status, 'COMPLETED', result.diagnostics)
        wire = seen[0]
        self.assertEqual(wire['question'], self.question)
        self.assertEqual(wire['untrusted_sources'][0]['text'], self.text)
        self.assertEqual({s['segment_id'] for s in wire['semantic_task']['segments']}, {s.segment_id for s in self.segments})
        self.assertEqual(wire['semantic_task']['candidate_schema']['additionalProperties'], False)
        self.assertNotIn('gold', json.dumps(wire))

    def test_gateway_schema_carries_the_actual_configured_profile(self):
        profile = SemanticProfile(max_readings=3, max_frames=7)
        port = OfflineModelPort(json.dumps(self.fixture()))
        seen = []
        original = OfflineModelPort.generate
        async def capture(port, serialized):
            seen.append(json.loads(serialized))
            return await original(port, serialized)
        with patch.object(OfflineModelPort, 'generate', capture):
            result, _ = self.run_candidate(self.fixture(), profile=profile, port=port)
        self.assertEqual(result.status, 'COMPLETED')
        wire = seen[0]['semantic_task']
        self.assertEqual(wire['execution_profile']['max_readings'], 3)
        self.assertEqual(wire['candidate_schema']['properties']['readings']['maxItems'], 3)
        self.assertEqual(wire['candidate_schema']['properties']['frames']['maxItems'], 7)

    def test_opaque_and_cross_frame_candidates_remain_unresolved_without_solver(self):
        candidate = self.fixture()
        candidate['readings'][0]['premises'][0]['ast'] = {'op': 'opaque', 'text': 'ironic intent', 'reason': 'not grounded'}
        with patch.object(ReadingLogicOperator, '_solve', side_effect=AssertionError('must not solve opaque text')):
            result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, 'PARTIAL')
        self.assertEqual(result.usage['classification_batches_completed'], 0)
        candidate = self.fixture()
        candidate['frames'].append({**candidate['frames'][0], 'id': 'quotation', 'parent': 'source-reading', 'kind': 'QUOTATION'})
        candidate['readings'][0]['premises'][0]['frame'] = 'quotation'
        with patch.object(ReadingLogicOperator, '_solve', side_effect=AssertionError('bridge required')):
            result, _ = self.run_candidate(candidate, request=replace(self.request, request_id='frame'))
        self.assertEqual(result.status, 'PARTIAL')
        self.assertIn('FRAME_BRIDGE_REQUIRED', result.answer)

    def test_omitted_segment_stays_unresolved_and_wrong_alignment_never_certifies(self):
        candidate = self.fixture()
        first = next(s.segment_id for s in self.segments if s.kind == 'SOURCE')
        for premise in candidate['readings'][0]['premises']:
            premise['segment_ids'] = [first]
        # Syntactically valid, deliberately wrong proposal; no checker can label
        # it semantically correct just because all source IDs exist.
        candidate['readings'][0]['premises'][0]['ast'] = binary('implies', self.q, self.p)
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, 'PARTIAL')
        values = self.values(result)
        self.assertFalse(values['semantic_certified'])
        self.assertIn('SOURCE_COVERAGE_UNRESOLVED', values['readings'][0]['unresolved'])
        self.assertIn('remain unverified', result.answer)

    def test_unknown_fields_fake_spans_answer_labels_and_executable_syntax_are_rejected(self):
        mutations = [lambda d: d.update(answer='True'),
                     lambda d: d['readings'][0].update(label='True'),
                     lambda d: d['readings'][0]['premises'][0].update(segment_ids=['invented']),
                     lambda d: d['readings'][0]['query']['ast'].update(op='__import__'),
                     lambda d: d['readings'][0]['query'].update(frame=[]),
                     lambda d: d['readings'][0]['query']['ast'].update(args=[{'var': 'free'}])]
        for index, mutate in enumerate(mutations):
            candidate = self.fixture()
            mutate(candidate)
            with patch.object(ReadingLogicOperator, '_solve', side_effect=AssertionError('invalid candidate dispatched')):
                result, port = self.run_candidate(candidate, request=replace(self.request, request_id=f'bad-{index}'))
            self.assertEqual(result.status, 'INVALID_REQUEST', (index, result))
            self.assertEqual(result.answer, '')
            self.assertEqual(port.attempts, 1)
            self.assertEqual(result.usage['mock_calls'], 1)
            self.assertNotIn('张三', repr(result))

    def test_duplicate_json_fields_and_bounded_compilation_refuse_before_solver(self):
        raw = json.dumps(self.fixture())
        raw = raw.replace('"schema": "hcl-semantic-candidates-1"', '"schema":"x","schema":"hcl-semantic-candidates-1"')
        result, _ = self.run_candidate(None, port=OfflineModelPort(raw))
        self.assertEqual(result.status, 'INVALID_REQUEST')
        with patch.object(ReadingLogicOperator, '_solve', side_effect=AssertionError('exceeds local allowance')):
            request = replace(self.request, request_id='limit', budget=replace(self.request.budget, max_local_evaluations=0))
            result, _ = self.run_candidate(self.fixture(), request=request)
        self.assertEqual(result.status, 'BUDGET_EXHAUSTED')

    def test_durable_partial_replay_same_engine_compat_stream_and_no_resend(self):
        candidate = self.fixture([([self.p], self.q), ([self.q], self.q)])
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, 'PARTIAL')
        self.store.close()
        self.store = SQLiteStateStore(self.path)
        port = OfflineModelPort('must never be consumed on replay')
        facade = CognitionWorkspace(self.store, principal=self.owner, session_id='s', gateway=ModelGateway(self.store, port))
        replay = asyncio.run(facade.run(self.request))
        async def stream():
            return [event async for event in facade.stream(self.request)]
        self.assertEqual(replay.answer, result.answer)
        self.assertEqual(asyncio.run(stream())[-1].result.answer, result.answer)
        self.assertTrue(replay.execution_receipt['replayed'])
        self.assertEqual(port.attempts, 0)

    def test_source_change_and_revoke_after_model_return_cannot_commit_or_leak(self):
        for revoke in (False, True):
            request = replace(self.request, request_id=f'change-{revoke}', source_handles=(self.handle,))
            original = OfflineModelPort.generate
            async def changed(port, serialized):
                output = await original(port, serialized)
                if revoke:
                    self.store.set_readers('s', self.owner, 'source', {'bob'})
                else:
                    self.handle = self.store.put_source('s', self.owner, 'source', self.text)
                return output
            with patch.object(OfflineModelPort, 'generate', changed):
                result, _ = self.run_candidate(self.fixture(), request=request)
            self.assertIn(result.status, ('STALE_STATE', 'DENIED'))
            self.assertEqual(result.answer, '')
            self.assertNotIn('张三', repr(result))

    def test_countermodel_tamper_fails_independent_original_query_check(self):
        result, _ = self.run_candidate(self.fixture([([self.p], self.q)]))
        values = self.values(result)
        row = values['readings'][0]
        check = thaw(row['checks']['entailment_check'])
        model = check['countermodel']['model']
        # The original query must be false for this target; force its extension true.
        query_predicate = parse(row['formal_query'])[1]
        model['predicates'][query_predicate] = list(model['domain'])
        forest = SemanticCompiler().compile(self.snapshot, self.segments, json.dumps(self.fixture([([self.p], self.q)])), self.request.budget)
        with self.assertRaises(HCLFailure):
            ReadingLogicOperator.checked_witness([parse(f) for f in row['formal_premises']], parse(row['formal_query']),
                check, 'QUERY_FALSE', forest.symbol_map, forest.entities, forest.predicates)

    def test_answer_text_and_used_computed_values_cannot_be_silently_changed(self):
        result, _ = self.run_candidate(self.fixture())
        accepted = self.store.inferences('s', self.owner)
        contract = AnswerAssembler().build(self.snapshot, (self.request.issue,), accepted)
        bad_claim = replace(contract.claims[0], text='Opposite answer')
        with self.assertRaises(HCLFailure):
            AnswerAssembler().validate(replace(contract, answer='Opposite answer', claims=(bad_claim,)), accepted)
        used = list(contract.claims[0].used_result_fields)
        used[1] = replace(used[1], value='False')
        with self.assertRaises(HCLFailure):
            AnswerAssembler().validate(replace(contract, claims=(replace(contract.claims[0], used_result_fields=tuple(used)),)), accepted)

    def test_real_parent_wall_deadline_kills_and_reaps_hung_worker(self):
        profile = SemanticProfile(worker_wall_seconds=1)
        real_popen = subprocess.Popen
        children = []
        def hang(*args, **kwargs):
            child = real_popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            children.append(child)
            return child
        started = time.monotonic()
        with patch('hcl.operators.semantic_logic.subprocess.Popen', side_effect=hang):
            result, _ = self.run_candidate(self.fixture(), profile=profile)
        self.assertLess(time.monotonic()-started, 5)
        self.assertEqual(result.status, 'BUDGET_EXHAUSTED')
        self.assertEqual(result.diagnostics[0].code, 'SOLVER_WALL_LIMIT')
        self.assertIsNotNone(children[0].poll())
        self.assertIsNone(result.usage['local_evaluations'])
        self.assertEqual(result.usage['mock_calls'], 1)
        self.assertEqual(result.answer, '')


    def test_solver_unknown_is_not_semantic_uncertainty(self):
        fake = {'readings': [{'id': 'reading-0', 'result': {'status': 'UNKNOWN', 'label': None,
                    'consistency_check': {'status': 'UNKNOWN'}}}],
                'classification_batches_completed': 1, 'solver_checks_upper_bound': 15, 'solver_version': 'fixture-unknown'}
        with patch.object(ReadingLogicOperator, '_solve', return_value=fake):
            result, _ = self.run_candidate(self.fixture())
        self.assertEqual(result.status, 'PARTIAL')
        row = self.values(result)['readings'][0]
        self.assertEqual(row['status'], 'UNKNOWN')
        self.assertIsNone(row['label'])
        self.assertEqual(row['countermodels'], ())
        self.assertNotIn('neither entailed nor refuted', result.answer)

    def test_full_fol_non_equivalence_without_finite_model_is_not_invented(self):
        fake = {'readings': [{'id': 'reading-0', 'result': {
            'status': 'CLASSIFIED', 'label': 'Uncertain',
            'consistency_check': {'status': 'NOT_EQUIVALENT'},
            'entailment_check': {'status': 'NOT_EQUIVALENT', 'scope': 'FULL_FOL_FORMAL_INPUT_ONLY'},
            'refutation_check': {'status': 'NOT_EQUIVALENT', 'scope': 'FULL_FOL_FORMAL_INPUT_ONLY'}}}],
            'classification_batches_completed': 1, 'solver_checks_upper_bound': 15, 'solver_version': 'fixture-no-model'}
        with patch.object(ReadingLogicOperator, '_solve', return_value=fake):
            result, _ = self.run_candidate(self.fixture())
        self.assertEqual(self.values(result)['readings'][0]['countermodels'], ())
        self.assertNotIn('checked finite scenario', result.answer)

    def test_same_name_source_local_entities_are_not_silently_merged(self):
        second = self.store.put_source('s', self.owner, 'other-source', '张三 received a notice in a separate account.')
        self.request = replace(self.request, source_handles=(self.handle, second))
        self.snapshot = self.store.snapshot('s', self.owner, self.request.source_handles)
        self.segments = segment_snapshot(self.snapshot, self.question)
        source_refs = [s.segment_id for s in self.segments if s.source_id == 'source']
        other_refs = [s.segment_id for s in self.segments if s.source_id == 'other-source']
        candidate = self.fixture([([self.p], atom('received', 'other-person'))])
        candidate['entities'][0]['segment_ids'] = source_refs
        candidate['entities'].append({'id': 'other-person', 'label': '张三', 'source_id': 'other-source', 'segment_ids': other_refs})
        result, _ = self.run_candidate(candidate)
        values = self.values(result)
        self.assertEqual(values['readings'][0]['label'], 'Uncertain')
        self.assertNotEqual(values['symbol_map']['constants']['person'], values['symbol_map']['constants']['other-person'])
        self.assertEqual({row['source_id'] for row in values['entities'].values()}, {'source', 'other-source'})

    def test_cross_source_entity_ref_and_question_as_premise_are_rejected(self):
        candidate = self.fixture()
        candidate['entities'][0]['source_id'] = 'not-authorized'
        result, _ = self.run_candidate(candidate)
        self.assertEqual(result.status, 'INVALID_REQUEST')
        candidate = self.fixture()
        candidate['readings'][0]['premises'][0]['segment_ids'] = candidate['readings'][0]['query']['segment_ids']
        result, _ = self.run_candidate(candidate, request=replace(self.request, request_id='question-root'))
        self.assertEqual(result.status, 'INVALID_REQUEST')

    def test_async_solver_does_not_block_concurrent_revocation_or_deliver_stale_results(self):
        entered, release = Event(), Event()
        original = ReadingLogicOperator._solve
        def waiting(operator, readings):
            entered.set()
            if not release.wait(5):
                raise AssertionError('async loop did not run the concurrent revocation')
            return original(operator, readings)
        port = OfflineModelPort(json.dumps(self.fixture(), ensure_ascii=False))
        engine = HCL(self.store, principal=self.owner, gateway=ModelGateway(self.store, port))
        async def concurrent():
            task = asyncio.create_task(engine.run(self.request))
            ready = await asyncio.to_thread(entered.wait, 5)
            self.assertTrue(ready)
            peer = SQLiteStateStore(self.path)
            try:
                peer.set_readers('s', self.owner, 'source', {'bob'})
            finally:
                peer.close()
            release.set()
            return await task
        with patch.object(ReadingLogicOperator, '_solve', waiting):
            result = asyncio.run(concurrent())
        self.assertEqual(result.status, 'DENIED')
        self.assertEqual(result.answer, '')
        self.assertNotIn('source_segments', result.execution_receipt)
        self.assertNotIn('张三', repr(result))
        self.assertEqual(result.usage['classification_batches_completed'], 1)
        self.assertEqual(self.store._db.execute('SELECT count(*) FROM inferences').fetchone()[0], 0)

    def test_late_semantic_delivery_revoke_and_cached_replay_never_leak_ir(self):
        port = OfflineModelPort(json.dumps(self.fixture(), ensure_ascii=False))
        engine = HCL(self.store, principal=self.owner, gateway=ModelGateway(self.store, port))
        def revoked(stage):
            if stage == 'task_finished':
                self.store.set_readers('s', self.owner, 'source', {'bob'})
        with patch.object(self.store, '_checkpoint', side_effect=revoked):
            result = engine.run_sync(self.request)
        self.assertEqual(result.status, 'DENIED')
        self.assertNotIn('inference_values', result.execution_receipt)
        self.assertNotIn('张三', repr(result))
        replay = engine.run_sync(self.request)
        self.assertEqual(replay.status, 'DENIED')
        self.assertEqual(port.attempts, 1)

    def test_hypothetical_frame_stays_visible_and_background_prior_requires_assumptions(self):
        candidate = self.fixture()
        candidate['frames'][0]['kind'] = 'HYPOTHETICAL'
        result, _ = self.run_candidate(candidate)
        self.assertIn('[HYPOTHETICAL]', result.answer)
        self.assertFalse(self.values(result)['semantic_certified'])
        candidate = self.fixture()
        candidate['readings'][0]['premises'][0]['origin'] = 'BACKGROUND_PRIOR'
        candidate['readings'][0]['premises'][0]['segment_ids'] = []
        result, _ = self.run_candidate(candidate, request=replace(self.request, request_id='prior'))
        self.assertEqual(result.status, 'INVALID_REQUEST')
        candidate['readings'][0]['assumptions'] = ['This background premise is explicitly assumed, not sourced.']
        result, _ = self.run_candidate(candidate, request=replace(self.request, request_id='assumed-prior'))
        self.assertEqual(result.status, 'COMPLETED')
        self.assertIn('explicitly assumed', result.answer)


if __name__ == '__main__':
    unittest.main()


class SolverClassificationContractTests(unittest.TestCase):
    def test_forged_labels_and_absent_checks_cannot_be_consumed(self):
        operator = ReadingLogicOperator()
        valid = {'status': 'CLASSIFIED', 'label': 'True',
                 'consistency_check': {'status': 'NOT_EQUIVALENT'},
                 'entailment_check': {'status': 'EQUIVALENT'},
                 'refutation_check': {'status': 'NOT_EQUIVALENT'}}
        operator._validate_classification(valid)
        invalid = [dict(valid, label='False'), dict(valid, status='UNKNOWN', label=None),
                   dict(valid, consistency_check={'status': 'EQUIVALENT'}),
                   dict(valid, refutation_check={'status': 'UNKNOWN'}),
                   {'status': 'CLASSIFIED', 'label': 'True'},
                   dict(valid, entailment_check={'status': 'NO_COUNTERMODEL_IN_THIS_DOMAIN'})]
        for result in invalid:
            with self.subTest(result=result), self.assertRaises(HCLFailure):
                operator._validate_classification(result)
