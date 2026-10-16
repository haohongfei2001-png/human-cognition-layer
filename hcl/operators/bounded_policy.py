"""Exhaustive two-step, observation-conditioned policies, never hindsight plans.

One complete policy is evaluated across every dimension and retained world.
Only terminal states stop early. Norm applicability is fixed at decision time;
all actually reachable actions must satisfy those same hard requirements.
"""
from fractions import Fraction
from hashlib import sha256
from itertools import product
import json

from hcl.operators.agency import encoded, rational

MAX_POLICIES = 256


def joint_policy_outcomes(graph, dimensions, scenarios, actual_states, subjective_states, work):
    if graph['horizon'] != 2:
        raise ValueError('only the explicitly bounded two-step policy is supported')
    actual, subjective = set(actual_states), set(subjective_states)
    terminal = set(graph['terminal'])
    if not actual or not subjective or actual & terminal:
        raise ValueError('a nonterminal mapped decision state is required')
    distributions = []
    for scenario in scenarios:
        work.spend()
        distribution = {s: rational(p) for s, p in scenario['distribution'].items()}
        if (not distribution or not set(distribution) <= actual
                or any(p < 0 for p in distribution.values()) or sum(distribution.values()) != 1):
            raise ValueError('scenario probability support differs from actual M03 state')
        distributions.append((scenario, distribution))
    actions = graph['actions']
    rows = []

    def check(action, worlds, beliefs, step, observation=None):
        work.spend(len(worlds) + len(beliefs) + 1)
        worlds, beliefs = set(worlds) - terminal, set(beliefs) - terminal
        return dict(step=step, observation=observation, action_id=action['id'],
                    actual_states=sorted(worlds), subjective_states=sorted(beliefs),
                    world_feasible=worlds <= set(action['feasible']),
                    subjectively_enabled=beliefs <= set(action['enabled']),
                    subjectively_feasible=beliefs <= set(action['feasible']))

    for root in actions:
        first = check(root, actual, subjective, 1)
        groups = {}
        for kind, states in (('actual', actual), ('subjective', subjective)):
            for state in sorted(states):
                work.spend()
                target = root['transitions'][state]
                symbol = root['observations'][target]
                group = groups.setdefault(symbol, dict(actual=set(), subjective=set()))
                group[kind].add(target)
        symbols = sorted(symbol for symbol, group in groups.items()
                         if (group['actual'] | group['subjective']) - terminal)
        # Every branch assignment is shared by every scenario and dimension.
        # product is lazy: no exponential allocation ahead of the work fence.
        for continuation in product(actions, repeat=len(symbols)):
            work.spend()
            if len(rows) >= MAX_POLICIES:
                raise OverflowError('JUDGMENT_POLICY_FRONTIER')
            selected = dict(zip(symbols, continuation))
            policy = dict(root_action_id=root['id'], continuations={s: selected[s]['id'] for s in symbols})
            identity = 'policy:' + sha256(json.dumps(policy, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            checks = [first] + [check(selected[s], groups[s]['actual'], groups[s]['subjective'], 2, s) for s in symbols]
            world = all(c['world_feasible'] for c in checks)
            enabled = all(c['subjectively_enabled'] for c in checks)
            used = {root['id']} | {selected[s]['id'] for s in symbols if groups[s]['actual'] - terminal}
            row = dict(action_id=identity, policy=policy, reachable_actions=sorted(used), step_checks=checks,
                       world_feasible=world, subjectively_enabled=enabled,
                       subjectively_feasible=all(c['subjectively_feasible'] for c in checks),
                       feasible=world and enabled, scenarios=[])
            rows.append(row)
            if not row['feasible']:
                continue
            for scenario, distribution in distributions:
                vector = {d['id']: Fraction(0) for d in dimensions}
                paths = {}
                for state, probability in distribution.items():
                    if not probability:
                        continue
                    work.spend()
                    target = root['transitions'][state]
                    symbol = root['observations'][target]
                    path = [root['id']]
                    if target not in terminal:
                        follow = selected[symbol]
                        target = follow['transitions'][target]
                        path.append(follow['id'])
                    paths[state] = dict(actions=path, observation=symbol, final_state=target)
                    for dimension in dimensions:
                        work.spend()
                        vector[dimension['id']] += probability * (rational(dimension['state_values'][target])
                            - sum(rational(dimension['action_costs'][a]) for a in path))
                row['scenarios'].append(dict(scenario_id=scenario['id'], distribution=scenario['distribution'],
                    successors={s: p['final_state'] for s, p in paths.items()}, paths=paths,
                    vector={d: encoded(value) for d, value in vector.items()}))
    return rows
