"""Source-bound candidate fixtures -> real FOL -> checked scenarios -> answer.

Inputs describe proposed meanings only. No fixture contains an answer label or
solver result. This is an offline integration witness, not model-semantic proof.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

from hcl import HCL
from hcl.kernel.types import BudgetSlice, Issue, Principal, TaskRequest, thaw
from hcl.memory.sqlite_store import SQLiteStateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.semantics.segments import segment_snapshot


def atom(name, variable=False):
    return {'op': 'atom', 'predicate': name, 'args': [{'var': 'x'} if variable else {'entity': 'person'}]}


def neg(body):
    return {'op': 'not', 'arg': body}


def all_people(body):
    return {'op': 'all', 'var': 'x', 'body': body}


def proposal(segments, cases, label):
    source = [s.segment_id for s in segments if s.kind == 'SOURCE']
    question = [s.segment_id for s in segments if s.kind == 'QUESTION']
    candidate = {'schema': 'hcl-semantic-candidates-1',
        'frames': [{'id': 'source', 'kind': 'SOURCE_DISCOURSE', 'parent': None, 'segment_ids': source}],
        'entities': [{'id': 'person', 'label': label, 'source_id': 'original', 'segment_ids': source}],
        'predicates': [{'id': 'received', 'label': 'received a notice / 收到通知', 'arity': 1, 'segment_ids': source+question},
                       {'id': 'attends', 'label': 'attends / 出席', 'arity': 1, 'segment_ids': source+question}],
        'readings': []}
    for index, (premises, query) in enumerate(cases):
        def meaning(tree, suffix, query=False):
            return {'id': f'm-{index}-{suffix}', 'natural_reading': 'Injected candidate; source meaning not certified.',
                    'ast': tree, 'frame': 'source', 'segment_ids': question if query else source, 'origin': 'INTERPRETATION'}
        candidate['readings'].append({'id': f'r-{index}', 'frame': 'source', 'assumptions': [],
            'premises': [meaning(tree, i) for i, tree in enumerate(premises)], 'query': meaning(query, 'query', True),
            'unparsed_segments': [], 'alignment': {'judgment': 'SUPPORTED', 'explanation': 'Fixture proposal, not an independent semantic check.'}})
    return candidate


def witness():
    p, q = atom('received'), atom('attends')
    conditional = {'op': 'implies', 'left': p, 'right': q}
    scenarios = [('positive', '如果张三收到通知，他就会出席。张三收到通知。', '能推出张三会出席吗？', '张三', [([conditional, p], q)]),
                 ('negation', '张三不会出席。', '能推出张三会出席吗？', '张三', [([neg(q)], q)]),
                 ('missing_condition', '如果张三收到通知，他就会出席。张三没有收到通知。', '能推出张三会出席吗？', '张三', [([conditional, neg(p)], q)]),
                 ('ambiguity', "Everyone didn't attend.", 'Did Mary Jane attend?', 'Mary Jane',
                  [([neg(all_people(atom('attends', True)))], q), ([all_people(neg(atom('attends', True)))], q)])]
    rows = []
    owner = Principal('synthetic', 'owner')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'state.sqlite'
        store = SQLiteStateStore(path)
        store.create_session('witness', owner)
        requests = []
        for name, text, question, label, cases in scenarios:
            handle = store.put_source('witness', owner, 'original', text)
            request = TaskRequest(name, question, (handle,), 'witness', owner,
                budget=BudgetSlice(max_mock_calls=1, max_output_bytes=131072),
                issue=Issue('semantic', 'logic.compare_semantic_readings'))
            snapshot = store.snapshot('witness', owner, (handle,))
            candidate = proposal(segment_snapshot(snapshot, question), cases, label)
            port = OfflineModelPort(json.dumps(candidate, ensure_ascii=False))
            result = HCL(store, principal=owner, gateway=ModelGateway(store, port)).run_sync(request)
            assert result.status in ('COMPLETED', 'PARTIAL'), result.diagnostics
            values = next(iter(result.execution_receipt['inference_values'].values()))
            consumed = {ref.field: ref.value for ref in result.claim_records[0].used_result_fields}
            assert consumed['readings'] == values['readings'] and not values['semantic_certified']
            assert port.attempts == 1 and result.usage['provider_calls'] == 0
            rows.append(dict(name=name, original=text, question=question, candidate=candidate,
                             status=result.status, actual_values=thaw(values), answer=result.answer,
                             result_consumption=thaw(consumed), usage=thaw(result.usage)))
            requests.append(request)
        assert [row['actual_values']['label'] for row in rows[:3]] == ['True', 'False', 'Uncertain']
        assert [row['label'] for row in rows[-1]['actual_values']['readings']] == ['Uncertain', 'False']
        assert rows[-1]['status'] == 'PARTIAL' and rows[-1]['actual_values']['status'] == 'READING_DEPENDENT'
        countermodels = [w for row in rows for reading in row['actual_values']['readings'] for w in reading['countermodels']]
        assert countermodels and all(all(w['premise_values']) and w['target_value'] is False for w in countermodels)
        store.close()
        store = SQLiteStateStore(path)
        replay = HCL(store, principal=owner).run_sync(requests[-1])
        assert replay.status == 'PARTIAL' and replay.answer == rows[-1]['answer'] and replay.execution_receipt['replayed']
        stale = HCL(store, principal=owner).run_sync(requests[0])
        assert stale.status == 'STALE_STATE' and not stale.answer
        store.close()
    root = Path(__file__).resolve().parents[1]
    return dict(schema='hcl-unified-s2.1-witness-1', slice='S2.1', readiness='INTEGRATED_OFFLINE', stage_complete=False,
        checked_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        runtime_files_sha256={str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in sorted((root/'hcl').rglob('*.py'))},
        provider_calls=0, provider_spend_usd='0', sealed_content_reads=0,
        model_evidence='INJECTED_EXTRACTION_PROPOSALS_ONLY', actual_cases=rows,
        partial_replay_answer_equal=True, changed_source_old_request_status=stale.status,
        not_established=['open natural-language semantic extraction', 'independent semantic alignment',
                         'reading completeness', 'full S1/S2 and T01/T02/T09/T20 acceptance',
                         'proof objects for full-FOL unsat', 'LIVE_FUNCTIONAL', 'EFFECT_CONFIRMED'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(witness(), ensure_ascii=False, indent=2)+'\n')
    print('S2.1_REAL_FOL_VALUES; CHECKED_COUNTERMODEL_ROUNDTRIP; FIXTURE_EXTRACTION_ONLY; STAGE_COMPLETE=FALSE')
