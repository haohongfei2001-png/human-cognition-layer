"""Exact rational hyperplane arrangements inside a declared bounded simplex.

Strict Fourier--Motzkin elimination supplies either a rational witness or a
nonnegative linear-combination contradiction. Every cell split is exhaustive
(<, =, >); no grid, floating point, sampled robustness, or default weights.
"""
from fractions import Fraction
from itertools import combinations
from math import gcd, lcm

from hcl.operators.agency import encoded, rational
from hcl.memory import codec


def inequality(coefficients, rhs, strict=False):
    return dict(coefficients=[encoded(Fraction(x)) for x in coefficients], rhs=encoded(Fraction(rhs)), strict=bool(strict))


def feasible(constraints, dimension, work):
    """A checked primal witness or exact Farkas/Motzkin infeasibility witness."""
    count = len(constraints)
    rows = []
    for i, row in enumerate(constraints):
        work.spend(1 + dimension)
        a = tuple(Fraction(v) for v in row['coefficients'])
        if len(a) != dimension or type(row['strict']) is not bool:
            raise ValueError('invalid linear inequality')
        rows.append((a, Fraction(row['rhs']), row['strict'], {i: Fraction(1)}))
    stages = []

    def simplify(items):
        unique = {}
        for a, b, strict, proof in items:
            work.spend(1 + len(a) + len(proof))
            nonzero = next((abs(x) for x in a if x), None)
            if nonzero is None:
                if b < 0 or (b == 0 and strict):
                    return None, dict(status='EMPTY', multipliers={str(i): encoded(v) for i, v in sorted(proof.items())},
                                      rhs=encoded(b), strict=strict)
                continue
            a = tuple(x/nonzero for x in a)
            b /= nonzero
            proof = {i: x/nonzero for i, x in proof.items()}
            old = unique.get(a)
            if old is None or b < old[1] or (b == old[1] and strict and not old[2]):
                unique[a] = (a, b, strict, proof)
        return list(unique.values()), None

    for _ in range(dimension):
        rows, contradiction = simplify(rows)
        if contradiction is not None:
            verify_feasibility(constraints, dimension, contradiction, work)
            return contradiction
        stages.append(rows)
        positive = [r for r in rows if r[0][-1] > 0]
        negative = [r for r in rows if r[0][-1] < 0]
        reduced = [(a[:-1], b, s, p) for a, b, s, p in rows if a[-1] == 0]
        for a, b, strict, proof in positive:
            for c, d, other_strict, other_proof in negative:
                work.spend(1 + len(a) + len(proof) + len(other_proof))
                x, y = -c[-1], a[-1]
                p = {i: x*v for i, v in proof.items()}
                for i, v in other_proof.items():
                    p[i] = p.get(i, Fraction(0)) + y*v
                reduced.append((tuple(x*u+y*v for u, v in zip(a[:-1], c[:-1])),
                                x*b+y*d, strict or other_strict, p))
        rows = reduced
    rows, contradiction = simplify(rows)
    if contradiction is not None:
        verify_feasibility(constraints, dimension, contradiction, work)
        return contradiction
    point = []
    for rows in reversed(stages):
        lower, upper = None, None
        for a, b, strict, _ in rows:
            work.spend(1 + len(a))
            if not a[-1]:
                continue
            limit = (b-sum(x*y for x, y in zip(a[:-1], point)))/a[-1]
            if a[-1] < 0:
                if lower is None or limit > lower[0]: lower = (limit, strict)
                elif limit == lower[0]: lower = (limit, strict or lower[1])
            else:
                if upper is None or limit < upper[0]: upper = (limit, strict)
                elif limit == upper[0]: upper = (limit, strict or upper[1])
        if lower is not None and upper is not None:
            value = (lower[0]+upper[0])/2
        elif lower is not None: value = lower[0] + (1 if lower[1] else 0)
        elif upper is not None: value = upper[0] - (1 if upper[1] else 0)
        else: value = Fraction(0)
        point.append(value)
    result = dict(status='NONEMPTY', point=[encoded(x) for x in point])
    verify_feasibility(constraints, dimension, result, work)
    return result


def verify_feasibility(constraints, dimension, certificate, work):
    """Algebra-only certificate checker, separate from the elimination search."""
    if certificate['status'] == 'NONEMPTY':
        point = [Fraction(v) for v in certificate['point']]
        if len(point) != dimension: raise ValueError('wrong witness dimension')
        for row in constraints:
            work.spend(1 + dimension)
            value = sum(Fraction(a)*x for a, x in zip(row['coefficients'], point))
            rhs = Fraction(row['rhs'])
            if value > rhs or (row['strict'] and value == rhs): raise ValueError('invalid feasible witness')
        return
    if certificate['status'] != 'EMPTY': raise ValueError('unknown feasibility result')
    coefficients, rhs, strict = [Fraction(0)]*dimension, Fraction(0), False
    for key, value in certificate['multipliers'].items():
        work.spend(1 + dimension)
        i, multiplier = int(key), Fraction(value)
        if not 0 <= i < len(constraints) or multiplier <= 0: raise ValueError('invalid dual multiplier')
        row = constraints[i]
        coefficients = [a+multiplier*Fraction(b) for a, b in zip(coefficients, row['coefficients'])]
        rhs += multiplier*Fraction(row['rhs'])
        strict |= row['strict']
    if (any(coefficients) or not (rhs < 0 or (rhs == 0 and strict))
            or encoded(rhs) != certificate['rhs'] or strict != certificate['strict']):
        raise ValueError('invalid infeasibility certificate')


def domain_constraints(domain, ids):
    """Eliminate the last normalized weight: w[-1] = 1 - sum(w[:-1])."""
    n = len(ids)-1
    constraints = [inequality([-int(i == j) for i in range(n)], 0) for j in range(n)]
    constraints.append(inequality([1]*n, 1))
    for row in domain['constraints']:
        values = [rational(row['coefficients'][d]) for d in ids]
        a = [v-values[-1] for v in values[:-1]]
        b = rational(row['rhs'])-values[-1]
        constraints.append(inequality(a, b, row['relation'] == 'LT'))
        if row['relation'] == 'EQ': constraints.append(inequality([-v for v in a], -b))
    return constraints


def normalized_hyperplane(values):
    scale = lcm(*(v.denominator for v in values))
    integers = [int(v*scale) for v in values]
    divisor = gcd(*integers)
    if not divisor: return None
    integers = [v//divisor for v in integers]
    if next(v for v in integers if v) < 0: integers = [-v for v in integers]
    return tuple(integers)


def sign_constraints(hyperplane, sign):
    a, b = hyperplane[:-1], -hyperplane[-1]
    if sign == -1: return [inequality(a, b, True)]
    if sign == 1: return [inequality([-v for v in a], -b, True)]
    return [inequality(a, b), inequality([-v for v in a], -b)]


def point_result(vectors, ids, point, rule, work):
    weights = [*map(Fraction, point), 1-sum(map(Fraction, point))]
    scores = {}
    for action, scenarios in vectors.items():
        scores[action] = {}
        for scenario, vector in scenarios.items():
            work.spend(1+len(ids))
            scores[action][scenario] = sum(w*Fraction(vector[d]) for w, d in zip(weights, ids))
    dominated, comparisons = set(), []
    for left, right in combinations(scores, 2):
        work.spend(1+len(scores[left]))
        deltas = [scores[left][s]-scores[right][s] for s in scores[left]]
        direction = left if all(v >= 0 for v in deltas) and any(v > 0 for v in deltas) else (
            right if all(v <= 0 for v in deltas) and any(v < 0 for v in deltas) else None)
        if direction is not None: dominated.add(right if direction == left else left)
        comparisons.append(dict(left=left, right=right, dominates=direction))
    worst = {a: min(s.values()) for a, s in scores.items()}
    best = max(worst.values(), default=None)
    recommended = sorted(a for a in scores if worst[a] == best and (rule == 'EXPECTED' or a not in dominated))
    return dict(recommended=recommended, dominated=sorted(dominated), comparisons=comparisons,
        worst_scenarios={a: sorted(s for s, v in values.items() if v == worst[a]) for a, values in scores.items()},
        witness_weights={d: encoded(w) for d, w in zip(ids, weights)},
        witness_scores={a: {s: encoded(v) for s, v in values.items()} for a, values in scores.items()})


def interval(constraints):
    lower, upper, lc, uc = Fraction(0), Fraction(1), True, True
    for row in constraints:
        a = Fraction(row['coefficients'][0]); b = Fraction(row['rhs'])
        if a < 0:
            value = b/a
            if value > lower: lower, lc = value, not row['strict']
            elif value == lower: lc &= not row['strict']
        if a > 0:
            value = b/a
            if value < upper: upper, uc = value, not row['strict']
            elif value == upper: uc &= not row['strict']
    return dict(lower=encoded(lower), upper=encoded(upper), lower_closed=lc, upper_closed=uc)


def solve_regions(domain, vectors, ids, rule, work, *, max_cells=256, max_proof_bytes=786432):
    """Public pure finite solver; vectors are actual per-action joint scenarios.

    Outputs partial certified cells on budget exhaustion, never universal claims.
    Coverage includes every sign branch, including exact lower-dimensional ties.
    """
    if rule not in ('EXPECTED', 'MAXIMIN') or not 1 <= len(ids) <= 4: raise ValueError('bounded weight domain required')
    scenario_ids = None
    for scenarios in vectors.values():
        if not scenarios or (rule == 'EXPECTED' and len(scenarios) != 1): raise ValueError('joint scenarios required')
        if scenario_ids is None: scenario_ids = set(scenarios)
        if set(scenarios) != scenario_ids or any(set(v) != set(ids) for v in scenarios.values()): raise ValueError('joint vector scope differs')
    result = dict(status='PARTIAL', complete=False, domain_status='UNKNOWN', domain_certificate=None,
        hyperplanes=[], coverage=[], cells=[], pending_cells=[], frontier=[], recommendation_partition=[],
        robust_recommended=[], unique_robust_recommended=[], possible_recommended=[], tie_boundaries=[],
        scope='EXACT_DECLARED_WEIGHT_DOMAIN_CONDITIONAL_ON_FIXED_JOINT_BRANCH')
    try:
        work.spend(1 + (len(domain["constraints"])+len(ids))*len(ids))
        base = domain_constraints(domain, ids)
        certificate = feasible(base, len(ids)-1, work)
        result['domain_certificate'] = certificate
        result['domain_status'] = certificate['status']
        if certificate['status'] == 'EMPTY':
            result.update(status='EMPTY_DOMAIN', complete=True)
            return result
        lines = []
        for action in sorted(vectors):
            for scenario in sorted(vectors[action]):
                work.spend(1+len(ids))
                v = [Fraction(vectors[action][scenario][d]) for d in ids]
                lines.append(tuple([x-v[-1] for x in v[:-1]]+[v[-1]]))
        planes = set()
        for left, right in combinations(lines, 2):
            work.spend(1+len(ids))
            h = normalized_hyperplane(tuple(a-b for a, b in zip(left, right)))
            # Constant nonzero comparisons need no subdivision.
            if h is not None and any(h[:-1]): planes.add(h)
        result['hyperplanes'] = [list(h) for h in sorted(planes)]
        proof_bytes = len(codec.dumps([base, certificate, result['hyperplanes']]))
        active = [dict(signs=[], constraints=base, certificate=certificate)]
        for index, h in enumerate(result['hyperplanes']):
            following = []
            result['pending_cells'] = [dict(signs=c['signs'], certificate=c['certificate']) for c in active]
            for cell in active:
                step = dict(parent=cell['signs'], hyperplane=index, children=[])
                result['coverage'].append(step)
                for sign in (-1, 0, 1):
                    work.spend()  # Sign candidate generation is metered too.
                    constraints = cell['constraints'] + sign_constraints(h, sign)
                    proof = feasible(constraints, len(ids)-1, work)
                    child = dict(sign=sign, certificate=proof)
                    proof_bytes += len(codec.dumps(child))
                    if proof_bytes > max_proof_bytes: raise OverflowError('WEIGHT_PROOF_CAPACITY_FRONTIER')
                    step['children'].append(child)
                    if proof['status'] == 'NONEMPTY':
                        following.append(dict(signs=cell['signs']+[sign], constraints=constraints, certificate=proof))
                        if len(following) > max_cells: raise OverflowError('WEIGHT_CELL_CAPACITY_FRONTIER')
            active = following
        result['pending_cells'] = [dict(signs=c['signs'], certificate=c['certificate']) for c in active]
        for index, cell in enumerate(active):
            work.spend()
            row = dict(cell_id='cell:'+str(index), signs=cell['signs'], constraints=cell['constraints'], certificate=cell['certificate'],
                       **point_result(vectors, ids, cell['certificate']['point'], rule, work))
            if len(ids) == 2: row['interval'] = interval(cell['constraints'])
            proof_bytes += len(codec.dumps(row))
            if proof_bytes > max_proof_bytes: raise OverflowError('WEIGHT_PROOF_CAPACITY_FRONTIER')
            result['cells'].append(row)
            result['pending_cells'].pop(0)
        cells = result['cells']
        work.spend(1+sum(len(c['recommended'])+1 for c in cells))
        result.update(status='COMPLETE', complete=True,
            robust_recommended=sorted(set.intersection(*(set(c['recommended']) for c in cells))) if cells else [],
            possible_recommended=sorted({a for c in cells for a in c['recommended']}),
            tie_boundaries=[c['cell_id'] for c in cells if len(c['recommended']) > 1])
        if cells and all(c['recommended'] == cells[0]['recommended'] and len(c['recommended']) == 1 for c in cells):
            result['unique_robust_recommended'] = cells[0]['recommended']
        if len(ids) == 2:
            ordered = sorted(cells, key=lambda c: (Fraction(c['interval']['lower']), Fraction(c['interval']['upper'])))
            partition = []
            for cell in ordered:
                work.spend()
                bounds = cell['interval']
                if (partition and partition[-1]['recommended'] == cell['recommended'] and partition[-1]['upper'] == bounds['lower']
                        and (partition[-1]['upper_closed'] or bounds['lower_closed'])):
                    partition[-1].update(upper=bounds['upper'], upper_closed=bounds['upper_closed'])
                    partition[-1]['cell_ids'].append(cell['cell_id'])
                else: partition.append(dict(bounds, recommended=cell['recommended'], cell_ids=[cell['cell_id']]))
            result['recommendation_partition'] = partition
    except OverflowError as error:
        result.update(status='PARTIAL', complete=False, robust_recommended=[], unique_robust_recommended=[], possible_recommended=[])
        result['frontier'].append(str(error))
    return result
