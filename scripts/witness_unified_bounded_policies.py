"""Offline witness for bounded observation-conditioned two-step M14 policies."""
import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

import hcl
from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from scripts.witness_unified_judgment import SCENE, PRINCIPLES, QUESTION, propose as single_step


def two_step(candidate):
    model = candidate['models'][0]
    plan = model['mental']['plans'][0]
    decision = model['decisions'][0]
    states = ['risk', 'clear', 'r', 'c', 'protected', 'ignored', 'safe-end']
    terminal = ['protected', 'ignored', 'safe-end']
    actions = []
    for key, enabled, targets in [
        ('inspect', ['risk', 'clear'], dict(risk='r', clear='c')),
        ('protect', ['r', 'c'], dict(r='protected', c='protected')),
        ('ignore', ['r', 'c'], dict(r='ignored', c='ignored')),
        ('safe', ['risk', 'clear'], dict(risk='safe-end', clear='safe-end')),
    ]:
        actions.append(dict(id=key, cost='0', enabled=enabled, feasible=enabled[:],
            transitions={s: targets.get(s, s) for s in states}, observations={s: s for s in states}))
    plan['graph'] = dict(states=states, terminal=terminal,
                        utilities={s: '0' for s in states}, actions=actions, horizon=2)
    decision['policy_horizon'] = 2
    for dimension in decision['dimensions']:
        dimension['state_values'] = {s: '0' for s in states}
        dimension['state_values'].update(protected='10' if dimension['id'] == 'care' else '0',
                                         ignored='0' if dimension['id'] == 'care' else '20', **{'safe-end': '3'})
        dimension['action_costs'] = {a['id']: '0' for a in actions}
    frame = decision['frameworks'][0]
    frame['weights'] = dict(care='1/2', convenience='1/2')
    frame['norms'][0]['permitted_actions'] = ['inspect', 'protect', 'safe']
    model['facts'][1]['reference']['action_id'] = 'inspect'
    return candidate


SCENE_POLICY = SCENE + " The analyst models inspect followed by protection or ignoring, or safe immediate stopping; risk/clear inspections reveal distinct observations."
PRINCIPLES_POLICY = PRINCIPLES + " These fixed action-time principles constrain every reachable step; final-state value minus executed costs is evaluated under the same complete policy."


def propose(snapshot, question):
    return two_step(single_step(snapshot, question))


def witness():
    owner = Principal('synthetic-policy-witness', 'owner')
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        store = StateStore.sqlite(Path(directory) / 'state.sqlite', revision=True)
        store.create_session('s', owner, {'bob'})
        handles = (store.put_source('s', owner, 'scene', SCENE_POLICY),
                   store.put_source('s', owner, 'principles', PRINCIPLES_POLICY))
        try:
            for mode in ('known-duty', 'no-receipt', 'priority-reversed', 'later-infeasible', 'unknown-guard', 'unknown-weights', 'budget'):
                request = TaskRequest(mode, QUESTION, handles, 's', owner,
                    budget=ExecutionBudget(max_mock_calls=1, max_feedback=0,
                        max_local_evaluations=15 if mode == 'budget' else 100000,
                        max_request_bytes=1048576, max_context_tokens=1048576,
                        max_output_bytes=1048576, max_total_output_bytes=8000000,
                        max_visible_output_tokens=1048576),
                    issue=ExecutionIssue('root', goals=(Issue(mode, 'judgment.evaluate'),)))
                candidate = propose(store.snapshot('s', owner, handles), QUESTION)
                model = candidate['models'][0]
                frame = model['decisions'][0]['frameworks'][0]
                if mode == 'no-receipt':
                    for key in ('received_by', 'understood_by', 'trusted_by'):
                        model['mental']['events'][0][key] = []
                elif mode == 'priority-reversed':
                    model['argument']['priorities'][0].update(better='liberty', worse='care-duty')
                elif mode == 'later-infeasible':
                    model['mental']['plans'][0]['graph']['actions'][1]['feasible'] = []
                elif mode == 'unknown-guard':
                    model['mental']['variables'][1]['initial'] = None
                    frame['norms'][0].update(guard_fact_ids=['promise'], argument_query_id=None)
                elif mode == 'unknown-weights':
                    frame.update(weights=None, decision_rule='PARETO', norms=[])
                port = OfflineModelPort(json.dumps(candidate, ensure_ascii=False))
                result = HCL(store, principal=owner, gateway=ModelGateway(store, port)).run_sync(request)
                assert result.status == 'PARTIAL', result.diagnostics
                actual = next(r for r in store.inferences('s', owner) if r.result_id in result.execution_receipt['result_ids'])
                decisions = actual.values['models'][0]['decisions']
                if mode not in ('budget', 'unknown-weights'):
                    decision = decisions[0]
                    winners = [r['policy'] for r in decision['outcomes'] if r['action_id'] in decision['robust_across_frameworks']]
                    assert winners
                    if mode == 'later-infeasible':
                        assert all(p['root_action_id'] == 'safe' for p in winners)
                    else:
                        follow = 'ignore' if mode in ('no-receipt', 'priority-reversed') else 'protect'
                        assert all(p['root_action_id'] == 'inspect' and p['continuations']['r'] == follow for p in winners)
                else:
                    assert all(not d['robust_across_frameworks'] for d in decisions)
                replay_port = OfflineModelPort('NO_NEW_SEND')
                replay = HCL(store, principal=owner, gateway=ModelGateway(store, replay_port)).run_sync(request)
                assert replay.answer == result.answer and replay_port.attempts == 0
                rows.append(dict(case=mode, status=result.status, usage=thaw(result.usage), actual=thaw(actual.values),
                    answer=result.answer, claim_fields=[f.field for c in result.claim_records for f in c.used_result_fields],
                    offline_attempts=port.attempts, replay_new_attempts=0))
        finally:
            store.close()
    root = Path(hcl.__file__).resolve().parents[1]
    return dict(schema='hcl-unified-bounded-policy-witness-1',
        checked_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        runtime_hashes={str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in sorted((root / 'hcl').rglob('*.py'))},
        rows=rows, provider_calls=0, provider_spend_usd=0, sealed_content_reads=0,
        evidence_scope='INTEGRATED_OFFLINE_PARTIAL_TWO_STEP_FIXED_NORM_OBSERVATION_POLICIES',
        not_established=['OPEN_EXTRACTION_ACCURACY', 'CANDIDATE_COMPLETENESS', 'USER_AUTHENTICATED_PRINCIPLE_ADOPTION',
            'MORAL_TRUTH', 'EVOLVING_FUTURE_NORM_GUARDS', 'GENERAL_MULTI_STEP_POLICIES', 'UNBOUNDED_POLICY_SEARCH',
            'FULL_M14', 'FULL_T17', 'FULL_T18', 'FULL_T19', 'FULL_S3', 'FULL_S4', 'LIVE_EFFECT'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
