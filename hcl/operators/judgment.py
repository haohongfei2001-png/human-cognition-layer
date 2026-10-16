"""Exact finite single-step choice under explicit, revisable normative conditions.

Each action has one jointly computed vector in each complete scenario. We never
optimize dimensions separately, infer missing weights, or compensate a violated
hard constraint with utility. Numeric scales are declared model conditions.
"""

from fractions import Fraction
from itertools import combinations

from hcl.operators.agency import encoded, rational

VERSION = "s4-joint-single-step-judgment-1"


class JudgmentWork:
    def __init__(self, limit):
        if type(limit) is not int or limit < 0:
            raise ValueError("nonnegative judgment work allowance required")
        self.limit, self.used = limit, 0

    def spend(self, units=1):
        if self.used + units > self.limit:
            raise OverflowError("JUDGMENT_WORK_FRONTIER")
        self.used += units


def joint_outcomes(graph, dimensions, scenarios, actual_states, subjective_states, work):
    """Apply the *same action* to all dimensions/worlds, then take expectations.

    Scenario probabilities are source-declared hypotheses; absent probabilities
    are handled by singleton scenarios by the caller, never by a uniform prior.
    Feasibility is checked separately from M05's utility-optimal action list.
    """
    actions = graph["actions"]
    actual, subjective = set(actual_states), set(subjective_states)
    if not actual or not subjective or actual & set(graph["terminal"]):
        raise ValueError("a nonterminal mapped decision state is required")
    rows = []
    for action in actions:
        work.spend()
        enabled = subjective <= set(action["enabled"])
        world = actual <= set(action["feasible"])
        subjective_feasible = subjective <= set(action["feasible"])
        row = dict(action_id=action["id"], world_feasible=world,
                   subjectively_enabled=enabled, subjectively_feasible=subjective_feasible,
                   feasible=world and enabled, scenarios=[])
        rows.append(row)
        if not row["feasible"]:
            continue
        for scenario in scenarios:
            distribution = {s: rational(p) for s, p in scenario["distribution"].items()}
            if (not distribution or not set(distribution) <= actual
                    or any(p < 0 for p in distribution.values()) or sum(distribution.values()) != 1):
                raise ValueError("scenario probability support differs from actual M03 state")
            successors = {s: action["transitions"][s] for s, p in distribution.items() if p}
            vector = {}
            for dimension in dimensions:
                work.spend()
                vector[dimension["id"]] = encoded(sum(
                    p * (rational(dimension["state_values"][action["transitions"][s]])
                         - rational(dimension["action_costs"][action["id"]]))
                    for s, p in distribution.items()))
            row["scenarios"].append(dict(scenario_id=scenario["id"],
                                         distribution=scenario["distribution"],
                                         successors=successors, vector=vector))
    return rows


def compare_framework(framework, outcomes, norm_states, dimensions, work):
    """Return conservative permission, Pareto and exact conditional recommendations.

    UNRESOLVED norms constrain definite permission; satisfying all possible hard
    requirements can still justify a positive choice. Disputed exclusions are
    retained separately from known prohibitions. Preferred-extension variants
    are computed jointly by the M13 consumer, not independent norm marginals.
    """
    ids = tuple(d["id"] for d in dimensions)
    norms = {n["id"]: n for n in framework["norms"]}
    feasible = [row for row in outcomes if row["feasible"]]
    eligibility, safe = [], []
    for row in outcomes:
        work.spend()
        action = row["action_id"]
        used_actions = set(row.get("reachable_actions", [action]))
        forbidden = [key for key, state in norm_states.items()
                     if state == "ACTIVE" and not used_actions <= set(norms[key]["permitted_actions"])]
        unresolved = [key for key, state in norm_states.items()
                      if state == "UNRESOLVED" and not used_actions <= set(norms[key]["permitted_actions"])]
        status = ("INFEASIBLE" if not row["feasible"] else "PROHIBITED" if forbidden
                  else "PERMISSION_UNRESOLVED" if unresolved else "PERMITTED_IN_DECLARED_FRAMEWORK")
        eligibility.append(dict(action_id=action, status=status,
                                prohibiting_norms=forbidden, unresolved_norms=unresolved))
        if status == "PERMITTED_IN_DECLARED_FRAMEWORK":
            safe.append(row)
    weights = framework["weights"]
    scores, comparisons = {}, []
    vectors = {row["action_id"]: {s["scenario_id"]: s["vector"] for s in row["scenarios"]}
               for row in safe}
    if weights is not None:
        for action, scenarios in vectors.items():
            scores[action] = {}
            for key, vector in scenarios.items():
                work.spend(len(ids))
                scores[action][key] = encoded(sum(rational(weights[d]) * Fraction(vector[d]) for d in ids))
    dominated = set()
    inequalities = []
    for left, right in combinations(vectors, 2):
        coefficients = {}
        deltas = []
        reverse = []
        for scenario in vectors[left]:
            work.spend(len(ids))
            difference = {d: Fraction(vectors[left][scenario][d]) - Fraction(vectors[right][scenario][d]) for d in ids}
            coefficients[scenario] = {d: encoded(v) for d, v in difference.items()}
            values = ([Fraction(scores[left][scenario]) - Fraction(scores[right][scenario])]
                      if weights is not None else list(difference.values()))
            deltas.extend(values)
            reverse.extend(-value for value in values)
        direction = None
        if all(v >= 0 for v in deltas) and any(v > 0 for v in deltas):
            dominated.add(right)
            direction = left
        elif all(v >= 0 for v in reverse) and any(v > 0 for v in reverse):
            dominated.add(left)
            direction = right
        comparisons.append(dict(left=left, right=right, dominates=direction,
                                joint_scenario_differences=coefficients,
                                minimum_weighted_difference=(encoded(min(deltas)) if weights is not None else None)))
        inequalities.append(dict(left=left, right=right, coefficients=coefficients,
                                 condition="For every retained scenario, sum(weight[d] * coefficient[d]) >= 0; at least one strict for dominance.",
                                 weights_inferred=False))
    frontier = sorted(set(vectors) - dominated)
    worst = {}
    if weights is None:
        recommended = frontier if len(frontier) == 1 else []
        reason = "UNIQUE_PARETO_OPTION" if recommended else "VALUE_CHOICE_REQUIRED"
    elif framework["decision_rule"] == "EXPECTED":
        if any(len(values) != 1 for values in scores.values()):
            raise ValueError("expected choice requires one explicit probability scenario")
        totals = {a: Fraction(next(iter(values.values()))) for a, values in scores.items()}
        best = max(totals.values()) if totals else None
        recommended = sorted(a for a, value in totals.items() if value == best)
        reason = "EXACT_EXPECTED_UTILITY"
    else:
        # Scalarize *within each joint scenario first*. Independent dimension
        # minima would manufacture an outcome vector that never occurred.
        worst = {a: encoded(min(Fraction(v) for v in values.values())) for a, values in scores.items()}
        best = max((Fraction(v) for v in worst.values()), default=None)
        recommended = sorted(a for a, value in worst.items() if Fraction(value) == best and (a in frontier or any("policy" in row for row in outcomes)))
        reason = "DECLARED_JOINT_SCENARIO_MAXIMIN"
    if not safe:
        reason = ("NO_FEASIBLE_ACTION" if not feasible else "NO_DEFINITELY_PERMITTED_ACTION")
    alternatives = []
    for choice in recommended:
        for other in safe:
            action = other["action_id"]
            if action == choice:
                continue
            losses = []
            for scenario, vector in vectors[choice].items():
                work.spend(len(ids))
                for dimension in ids:
                    delta = Fraction(vector[dimension]) - Fraction(vectors[action][scenario][dimension])
                    if delta < 0:
                        losses.append(dict(scenario_id=scenario, dimension_id=dimension,
                                           difference=encoded(delta)))
            alternatives.append(dict(recommendation=choice, alternative=action,
                                     alternative_on_frontier=action in frontier,
                                     costs_of_recommendation=losses,
                                     alternative_worst_score=worst.get(action)))
    constraint_tradeoffs = []
    status_by_action = {r["action_id"]: r for r in eligibility}
    for choice in recommended:
        for other in feasible:
            action = other["action_id"]
            if action in vectors:
                continue
            gains = []
            for scenario in other["scenarios"]:
                work.spend(len(ids))
                for dimension in ids:
                    delta = Fraction(scenario["vector"][dimension]) - Fraction(vectors[choice][scenario["scenario_id"]][dimension])
                    if delta > 0:
                        gains.append(dict(scenario_id=scenario["scenario_id"], dimension_id=dimension,
                                          foregone_value=encoded(delta)))
            constraint_tradeoffs.append(dict(recommendation=choice, excluded_alternative=action,
                eligibility=status_by_action[action], foregone_gains=gains,
                condition="Reconsider only if the excluding hard norm or unresolved applicability changes; gains do not override it."))
    return dict(eligibility=eligibility, norm_states=norm_states, pareto=frontier,
                comparisons=comparisons, scenario_scores=scores, worst_scores=worst,
                recommended=recommended, recommendation_basis=reason,
                alternatives=alternatives, constraint_tradeoffs=constraint_tradeoffs, value_change_conditions=inequalities,
                weight_status="EXPLICIT_CONDITIONAL_WEIGHTS" if weights is not None else "UNKNOWN_NOT_UNIFORM",
                scope="FINITE_DECLARED_FRAMEWORK_AND_SCENARIOS_NOT_UNIVERSAL_MORAL_RANKING")
