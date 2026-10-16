"""Exact bounded-policy weight-domain composition; synthetic offline inputs only."""
import argparse
from copy import deepcopy
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
from scripts.witness_unified_bounded_policies import (
    SCENE_POLICY, PRINCIPLES_POLICY, QUESTION, propose as policy_propose)


def propose(snapshot, question, rule='EXPECTED', *, uncertain=False, observable=True):
    candidate = policy_propose(snapshot, question)
    model = candidate['models'][0]
    decision = model['decisions'][0]
    frame = decision['frameworks'][0]
    frame.update(weights=None, decision_rule='PARETO')
    if uncertain:
        model['mental']['variables'][0].update(initial=None, observed_by=['ning', 'qing'])
        model['mental']['events'] = []
        model['mental']['active_assumptions'] = ['interpretation']
        frame['norms'] = []
        graph = model['mental']['plans'][0]['graph']
        graph['actions'][1]['transitions']['c'] = 'ignored'
        graph['actions'][2]['transitions']['c'] = 'protected'
        if not observable:
            graph['actions'][0]['observations'].update(r='same', c='same')
        if rule == 'EXPECTED':
            decision['scenarios'] = [dict(id='declared-mixture', distribution={'risk': '1/3', 'clear': '2/3'},
                                          segment_ids=decision['segment_ids'])]
    candidate['schema'] = 'hcl-judgment-candidates-5'
    candidate['weight_domains'] = [dict(id='policy-values', source_id=model['mental']['source_id'],
        model_id=model['mental']['id'], decision_id=decision['id'], framework_id=frame['id'],
        decision_rule=rule, constraints=[], origin=deepcopy(frame['origin']), segment_ids=frame['segment_ids'])]
    return candidate


def witness():
    owner = Principal('synthetic-policy-weight-witness', 'owner')
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        store = StateStore.sqlite(Path(directory) / 'state.sqlite', revision=True)
        store.create_session('s', owner, {'bob'})
        handles = (store.put_source('s', owner, 'scene', SCENE_POLICY),
                   store.put_source('s', owner, 'principles', PRINCIPLES_POLICY + ' Declared weight domains are conditional constraints, not adopted preferences.'))
        try:
            for mode, rule in [('expected', 'EXPECTED'), ('maximin', 'MAXIMIN'), ('regret', 'MINIMAX_REGRET'),
                               ('hidden-observation', 'MAXIMIN'), ('narrow-domain', 'EXPECTED'),
                               ('unknown-norm', 'EXPECTED'), ('empty-domain', 'EXPECTED'), ('budget', 'MINIMAX_REGRET')]:
                request = TaskRequest(mode, QUESTION, handles, 's', owner,
                    budget=ExecutionBudget(max_mock_calls=1, max_feedback=0, max_local_evaluations=300000,
                        max_request_bytes=1048576, max_context_tokens=1048576, max_output_bytes=1048576,
                        max_total_output_bytes=8000000, max_visible_output_tokens=1048576),
                    issue=ExecutionIssue('root', goals=(Issue(mode, 'judgment.evaluate'),)))
                candidate = propose(store.snapshot('s', owner, handles), QUESTION, rule,
                    uncertain=mode in ('maximin', 'regret', 'hidden-observation', 'budget'),
                    observable=mode != 'hidden-observation')
                model = candidate['models'][0]; domain = candidate['weight_domains'][0]
                if mode == 'narrow-domain':
                    domain['constraints'] = [dict(id='care-floor', coefficients={'care': '-1', 'convenience': '0'}, rhs='-1/2', relation='LE', segment_ids=domain['segment_ids'])]
                elif mode == 'empty-domain':
                    domain['constraints'] = [dict(id='impossible', coefficients={'care': '1', 'convenience': '1'}, rhs='0', relation='LE', segment_ids=domain['segment_ids'])]
                elif mode == 'unknown-norm':
                    model['mental']['variables'][1]['initial'] = None
                    model['decisions'][0]['frameworks'][0]['norms'][0].update(guard_fact_ids=['promise'], argument_query_id=None)
                elif mode == 'budget':
                    request = replace(request, budget=replace(request.budget, max_local_evaluations=9000))
                port = OfflineModelPort(json.dumps(candidate, ensure_ascii=False))
                result = HCL(store, principal=owner, gateway=ModelGateway(store, port)).run_sync(request)
                assert result.status == 'PARTIAL', result.diagnostics
                proof = next(r for r in store.inferences('s', owner) if r.result_id in result.execution_receipt['result_ids'])
                value = proof.values
                if mode in ('unknown-norm', 'budget'):
                    assert not value['complete'] and all(not a['robust_recommended'] and not a['possible_recommended'] for a in value['analyses'])
                else:
                    assert value['complete'], value['issues']
                    if mode == 'empty-domain':
                        assert not value['analyses'][0]['possible_recommended']
                    else:
                        assert value['analyses'][0]['policy_catalog'] and 'after observation' in result.answer
                replay_port = OfflineModelPort('NO_NEW_SEND')
                replay = HCL(store, principal=owner, gateway=ModelGateway(store, replay_port)).run_sync(request)
                assert replay.answer == result.answer and replay_port.attempts == 0
                rows.append(dict(case=mode, status=result.status, actual=thaw(value), answer=result.answer,
                    usage=thaw(result.usage), claim_fields=[f.field for c in result.claim_records for f in c.used_result_fields],
                    offline_attempts=port.attempts, replay_new_attempts=0))
        finally:
            store.close()
    root = Path(hcl.__file__).resolve().parents[1]
    return dict(schema='hcl-unified-policy-weight-region-witness-1',
        checked_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        runtime_hashes={str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in sorted((root / 'hcl').rglob('*.py'))},
        rows=rows, provider_calls=0, provider_spend_usd=0, sealed_content_reads=0,
        evidence_scope='INTEGRATED_OFFLINE_PARTIAL_TWO_STEP_POLICY_WEIGHT_DOMAINS',
        not_established=['OPEN_EXTRACTION_ACCURACY', 'CANDIDATE_COMPLETENESS', 'USER_AUTHENTICATED_PRINCIPLE_ADOPTION',
                        'EVOLVING_FUTURE_NORM_GUARDS', 'GENERAL_MULTI_STEP_POLICIES', 'FULL_M05', 'FULL_M14', 'FULL_S3', 'FULL_S4', 'LIVE_EFFECT'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    args = parser.parse_args()
    Path(args.output).write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + '\n')
