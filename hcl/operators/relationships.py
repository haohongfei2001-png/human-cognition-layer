"""Finite longitudinal model comparison; no automatic character verdict.

Only actual downstream prediction cells enter this search. Candidate labels are
not evidence, repeated reports share one factor, and a truncated search cannot
claim a globally preferred change point.
"""

from hashlib import sha256
from hcl.memory import codec
from hcl.operators.abduction import compare_prediction, factor_profile, pareto_frontier


def path_identity(path):
    return "trajectory:" + sha256(codec.canonical(path).encode()).hexdigest()


def segments(path, times):
    result = []
    for i, model in enumerate(path):
        if not result or result[-1]["model_id"] != model:
            result.append(
                dict(
                    model_id=model,
                    start_index=i,
                    end_index=i,
                    from_time=times[i],
                    through_time=times[i],
                )
            )
        else:
            result[-1].update(end_index=i, through_time=times[i])
    return result


def longitudinal_search(
    matrix, observations, mechanisms, *, max_segments, max_work, max_states
):
    """Bounded dynamic expansion including every zero-change candidate first.

    Evidence factors are recomputed over complete paths, never summed across time
    or domain projections. No prefix is pruned by its current fit: a later report
    can refer to the same factor and change the qualification of that factor.
    Only exactly equal parameter paths are coalesced. This intentionally preserves
    ambiguity; resource saturation is explicit rather than a heuristic winner.
    """
    if (
        not observations
        or not mechanisms
        or min(max_segments, max_states) < 1
        or max_work < 0
    ):
        raise ValueError("finite nonempty longitudinal search required")
    ordered = tuple(sorted(mechanisms))
    times = tuple(o["at"] for o in observations)
    if tuple(sorted(times)) != times:
        raise ValueError("event times must be ordered")
    if set(matrix) != set(ordered) or any(
        len(matrix[key]) != len(observations) for key in ordered
    ):
        raise ValueError("complete actual prediction matrix required")
    work = 0
    frontier = set()
    completed = {}

    def evaluate(path):
        cells = []
        for i, key in enumerate(path):
            prediction = matrix[key][i]
            observation = observations[i]
            cells.append(
                dict(
                    observation_id=observation["id"],
                    factor_id=observation["factor_id"],
                    model_id=key,
                    relation=compare_prediction(prediction, observation),
                    prediction=dict(
                        status=prediction["status"], values=prediction["values"]
                    ),
                    actual_prediction_ref=dict(mechanism_id=key, observation_index=i),
                )
            )
        runs = segments(path, times)
        return dict(
            trajectory_id=path_identity(path),
            path=path,
            segments=runs,
            change_points=tuple(r["from_time"] for r in runs[1:]),
            cells=cells,
            profile=factor_profile(cells),
            complexity=sum(mechanisms[r["model_id"]]["complexity"] for r in runs)
            + len(runs)
            - 1,
            work=len(cells),
            posterior="NOT_CALIBRATED",
            scope="CONDITIONAL_FINITE_LIBRARY_NOT_STABLE_CHARACTER_TRUTH",
        )

    # Do not let early branching starve the required stable-value alternatives.
    for key in ordered:
        if work + len(observations) > max_work or len(completed) >= max_states:
            frontier.add("LONGITUDINAL_SEARCH_FRONTIER")
            break
        work += len(observations)
        path = (key,) * len(observations)
        completed[path] = evaluate(path)
    layer = [(key,) for key in ordered]
    for length in () if max_segments == 1 else range(1, len(observations)):
        next_layer = []
        halted = False
        for path in layer:
            for key in ordered:
                if times[length] == times[length - 1] and key != path[-1]:
                    continue
                if len(segments((*path, key), times[: length + 1])) > max_segments:
                    continue
                if work >= max_work or len(next_layer) >= max_states:
                    frontier.add("LONGITUDINAL_SEARCH_FRONTIER")
                    halted = True
                    break
                work += 1
                next_layer.append((*path, key))
            if halted:
                break
        if halted:
            break
        layer = next_layer
        if length + 1 == len(observations):
            for path in layer:
                if path in completed:
                    continue
                if len(completed) >= max_states:
                    frontier.add("LONGITUDINAL_CANDIDATE_CAPACITY")
                    break
                if work + len(observations) > max_work:
                    frontier.add("LONGITUDINAL_SEARCH_FRONTIER")
                    break
                work += len(observations)
                completed[path] = evaluate(path)
    if len(observations) == 1 and len(completed) < len(ordered):
        frontier.add("LONGITUDINAL_SEARCH_FRONTIER")
    columns = {v["trajectory_id"]: v for v in completed.values()}
    preferred = pareto_frontier(columns)
    return dict(
        status="PARTIAL" if frontier else "COMPLETE_WITHIN_DECLARED_LIBRARY",
        trajectories=tuple(columns[key] for key in sorted(columns)),
        pareto_explored=preferred,
        global_comparison=(
            "NOT_ESTABLISHED" if frontier else "EXACT_WITHIN_DECLARED_LIBRARY"
        ),
        evidence_factor_ids=tuple(sorted({o["factor_id"] for o in observations})),
        factor_independence="NOT_STATISTICALLY_ASSUMED",
        work=work,
        frontier=tuple(sorted(frontier)),
    )


def relationship_history(hypotheses, prior, factors, *, max_work):
    """Exact finite conditional likelihood update, with shared evidence factors.

    Likelihoods are explicit source-model parameters under a declared conditional
    independence hypothesis, never a verified independence fact or human-trust
    constant.
    Null prior retains compatible hypotheses without inventing equal weights.
    """
    from fractions import Fraction
    from hcl.operators.agency import rational, encoded

    identities = tuple(sorted(hypotheses))
    if not identities or max_work < 0:
        raise ValueError("finite relationship hypotheses required")
    initial = None if prior is None else {k: rational(v) for k, v in prior.items()}
    if initial is not None and (
        set(initial) != set(identities)
        or any(v < 0 for v in initial.values())
        or sum(initial.values()) != 1
    ):
        raise ValueError("explicit normalized hypothesis prior required")
    weights = initial
    possible = (
        set(identities) if initial is None else {k for k, v in initial.items() if v > 0}
    )
    registry = {}
    history = []
    work = 0
    frontier = set()
    last_at = -1
    for factor in factors:
        if factor["at"] < last_at:
            raise ValueError("ordered relationship evidence required")
        last_at = factor["at"]
        likelihoods = {k: rational(v) for k, v in factor["likelihoods"].items()}
        if set(likelihoods) != set(identities) or any(
            not 0 <= v <= 1 for v in likelihoods.values()
        ):
            raise ValueError(
                "a conditional likelihood for every hypothesis is required"
            )
        old = registry.get(factor["factor_id"])
        established = factor["qualification"] == "ESTABLISHED_IN_CONDITIONAL_MODEL"
        if old is not None and (old["conflict"] or old["likelihoods"] != likelihoods):
            update = "CORRELATED_CONFLICT_FACTOR_RETRACTED"
            new = dict(
                likelihoods=likelihoods, applied=False, conflict=True, unresolved=False
            )
        elif old is not None and old["applied"]:
            update = "REPEATED_FACTOR_NOT_MULTIPLIED"
            new = old
        else:
            update = (
                "CONDITIONAL_LIKELIHOOD_APPLIED"
                if established
                else (
                    "INAPPLICABLE_NOT_APPLIED"
                    if factor["qualification"] == "INAPPLICABLE"
                    else "UNRESOLVED_NOT_APPLIED"
                )
            )
            new = dict(
                likelihoods=likelihoods,
                applied=established,
                conflict=False,
                unresolved=factor["qualification"] == "UNRESOLVED",
            )
        tentative = dict(registry, **{factor["factor_id"]: new})
        applied = [row["likelihoods"] for row in tentative.values() if row["applied"]]
        cost = 1 if old == new else 1 + len(identities) * len(applied)
        if work + cost > max_work:
            frontier.add("RELATIONSHIP_UPDATE_FRONTIER")
            break
        work += cost
        registry = tentative
        if old != new:
            # A conflicting repeated report retracts only its own prior update;
            # independent factors survive. Earlier history rows are not rewritten.
            weights = None if initial is None else dict(initial)
            possible = (
                set(identities)
                if initial is None
                else {k for k, v in initial.items() if v > 0}
            )
            for likelihood in applied:
                possible &= {k for k, v in likelihood.items() if v > 0}
                if weights is not None:
                    weights = {k: v * likelihood[k] for k, v in weights.items()}
            if weights is not None:
                total = sum(weights.values(), Fraction(0))
                weights = (
                    None if not total else {k: v / total for k, v in weights.items()}
                )
        history.append(
            dict(
                factor,
                update=update,
                weights=(
                    None
                    if weights is None
                    else {k: encoded(v) for k, v in weights.items()}
                ),
                compatible_hypotheses=tuple(sorted(possible)),
                unresolved_factor_ids=tuple(
                    sorted(k for k, v in registry.items() if v.get("unresolved"))
                ),
                conflicting_factor_ids=tuple(
                    sorted(k for k, v in registry.items() if v["conflict"])
                ),
            )
        )
    if any(row["conflict"] for row in registry.values()):
        frontier.add("RELATIONSHIP_CORRELATED_FACTOR_CONFLICT")
    if any(row.get("unresolved") for row in registry.values()):
        frontier.add("RELATIONSHIP_EVIDENCE_UNRESOLVED")
    if not possible:
        frontier.add("RELATIONSHIP_MODEL_CONTRADICTED")
    return dict(
        history=tuple(history),
        weights=(
            None if weights is None else {k: encoded(v) for k, v in weights.items()}
        ),
        compatible_hypotheses=tuple(sorted(possible)),
        processed_factor_ids=tuple(sorted(registry)),
        applied_factor_ids=tuple(
            sorted(key for key, row in registry.items() if row["applied"])
        ),
        work=work,
        frontier=tuple(sorted(frontier)),
        status="PARTIAL" if frontier else "COMPUTED_CONDITIONAL",
        calibration="NOT_ESTABLISHED",
        factorization="SOURCE_DECLARED_CONDITIONAL_INDEPENDENCE_MODEL",
        scope="DIRECTED_DOMAIN_DIMENSION_HYPOTHESES_NOT_CHARACTER_TRUTH",
    )


def role_reconciliation(requirements, opportunities, *, max_work):
    """Enumerate unresolved role applicability; intersect real M05 opportunities.

    Self-identification, other attribution and observed actions are not role
    constraints. Only declared applicable requirements enter this computation.
    """
    from itertools import product, combinations

    work = 0
    branches = []
    frontier = set()
    statuses = tuple(r["condition_values"] for r in requirements)
    if any(not values or not set(values) <= {False, True} for values in statuses):
        raise ValueError("qualified Boolean role applicability required")
    for flags in product(*statuses):
        if work >= max_work:
            frontier.add("ROLE_RECONCILIATION_FRONTIER")
            break
        work += 1
        selected = [r for r, flag in zip(requirements, flags) if flag]
        required = [set(r["actions"]) for r in selected]
        joint = set(opportunities)
        for actions in required:
            joint &= actions
        # Every minimal incompatible set is retained within the explicit budget.
        conflicts = []
        for size in range(1, len(selected) + 1):
            for indices in combinations(range(len(selected)), size):
                if any(set(old) <= set(indices) for old in conflicts):
                    continue
                if work >= max_work:
                    frontier.add("ROLE_CONFLICT_SEARCH_FRONTIER")
                    break
                work += 1
                allowed = set(opportunities)
                for i in indices:
                    allowed &= required[i]
                if not allowed:
                    conflicts.append(indices)
            if "ROLE_CONFLICT_SEARCH_FRONTIER" in frontier:
                break
        branches.append(
            dict(
                active_role_ids=tuple(r["id"] for r in selected),
                feasible_reconciliation_actions=tuple(sorted(joint)),
                minimal_incompatible_role_sets=tuple(
                    tuple(selected[i]["id"] for i in indices) for indices in conflicts
                ),
                conflict_search_complete="ROLE_CONFLICT_SEARCH_FRONTIER"
                not in frontier,
            )
        )
        if frontier:
            break
    return dict(
        branches=tuple(branches),
        work=work,
        frontier=tuple(sorted(frontier)),
        status="PARTIAL" if frontier else "COMPLETE_WITHIN_DECLARED_REQUIREMENTS",
        scope="CONDITIONAL_ROLE_REQUIREMENTS_NOT_IDENTITY_OR_MORAL_VERDICT",
    )
