"""Conditional goal appraisal and coping consequences, never emotion measurement.

Inputs are source-bound utility/transition hypotheses and actual M03/M05 values.
Unknown probability stays an interval; conflicting goals are never silently
collapsed into a single score. Semantic emotion mappings remain hypotheses.
"""

from fractions import Fraction

from hcl.operators.agency import rational, encoded

VERSION = "s3-finite-affect-1"


def validate_observation_coarsening(original, proposed):
    """Attention may merge or rename source observations, never reveal more."""
    if set(original) != set(proposed):
        raise ValueError("attention projection must cover original state codebook")
    projected = {}
    for state, symbol in original.items():
        if symbol in projected and projected[symbol] != proposed[state]:
            raise ValueError("attention cannot refine the source observation partition")
        projected[symbol] = proposed[state]


def interval(values, weights=None):
    """Exact expectation only with declared weights; otherwise the convex range."""
    values = {key: Fraction(value) for key, value in values.items()}
    if not values:
        return dict(status="NO_SUPPORTED_STATES", lower=None, upper=None)
    if weights is None:
        lower, upper = min(values.values()), max(values.values())
        status = "EXACT" if lower == upper else "UNWEIGHTED_POSSIBILITIES"
    else:
        parsed = {key: Fraction(value) for key, value in weights.items()}
        if (
            any(v < 0 for v in parsed.values())
            or sum(parsed.values()) != 1
            or {key for key, v in parsed.items() if v > 0} != set(values)
        ):
            raise ValueError("weights must bind exactly the actual perspective support")
        lower = upper = sum(parsed[key] * value for key, value in values.items())
        status = "DECLARED_EXPECTATION"
    return dict(status=status, lower=encoded(lower), upper=encoded(upper))


def directions(bounds):
    if bounds["lower"] is None:
        return ("UNCOMPUTED",)
    low, high = Fraction(bounds["lower"]), Fraction(bounds["upper"])
    return tuple(
        label
        for label, present in (
            ("NEGATIVE", low < 0),
            ("ZERO", low <= 0 <= high),
            ("POSITIVE", high > 0),
        )
        if present
    )


def difference(current, previous):
    if current["lower"] is None or previous["lower"] is None:
        return dict(status="UNCOMPUTED", lower=None, upper=None)
    lower = Fraction(current["lower"]) - Fraction(previous["upper"])
    upper = Fraction(current["upper"]) - Fraction(previous["lower"])
    return dict(
        status="EXACT" if lower == upper else "CONSERVATIVE_UNPAIRED_RANGE",
        lower=encoded(lower),
        upper=encoded(upper),
    )


def appraise(
    utilities,
    previous_states,
    current_states,
    *,
    previous_weights=None,
    current_weights=None,
    expected_states=None,
    expected_weights=None
):
    """Each goal's desirability and expected-value change from actual views.

    The same outcome can benefit one goal and harm another. Without a declared
    cross-time joint distribution, subtracting ranges preserves every compatible
    change rather than pretending the two time slices are correlated.
    """
    values = {key: rational(value) for key, value in utilities.items()}
    if not set(previous_states) <= set(values) or not set(current_states) <= set(
        values
    ):
        raise ValueError("every supported state needs a declared goal consequence")
    before = interval({s: values[s] for s in previous_states}, previous_weights)
    after = interval({s: values[s] for s in current_states}, current_weights)
    change = difference(after, before)
    expected = (
        dict(status="NO_PROSPECTIVE_MODEL", lower=None, upper=None)
        if expected_states is None
        else interval({s: values[s] for s in expected_states}, expected_weights)
    )
    gap = difference(after, expected)
    return dict(
        previous_value=before,
        current_value=after,
        state_change=change,
        expected_value=expected,
        expectation_gap=gap,
        desirability=directions(after),
        change_direction=directions(change),
        expectation_gap_direction=directions(gap),
        scope="GOAL_CONSEQUENCE_UNDER_ACTUAL_PERSPECTIVES_NOT_FELT_EMOTION",
    )


def control(
    utilities, state_plans, *, weights=None, actual_states=(), actual_plans=None
):
    """Consume actual per-state M05 Q and separate opportunity from value.

    A positive Q for an enabled yet infeasible action is not control. Each action
    retains possible/robust subjective feasibility, plus separate actual-world
    feasibility. No interpersonal or normative authority is inferred.
    """
    utilities = {s: rational(value) for s, value in utilities.items()}
    if not state_plans or any(
        p["status"] not in ("SOLVED", "TERMINAL", "NO_AVAILABLE_ACTIONS")
        for p in state_plans.values()
    ):
        return dict(
            status="UNCOMPUTED",
            actions={},
            robust_improvement=(),
            possible_improvement=(),
            frontier=("AFFECT_PLANNING_FRONTIER",),
        )
    actions = sorted({a for plan in state_plans.values() for a in plan["q"]})
    rows = {}
    world_plans = state_plans if actual_plans is None else actual_plans
    world_frontier = any(
        s not in world_plans
        or world_plans[s]["status"]
        not in ("SOLVED", "TERMINAL", "NO_AVAILABLE_ACTIONS")
        for s in actual_states
    )
    for action in actions:
        available = {s for s, p in state_plans.items() if action in p["q"]}
        feasible = {
            s
            for s in available
            if state_plans[s]["subjective_feasibility"].get(action) is True
        }
        robust = feasible == set(state_plans)
        q = {s: state_plans[s]["q"][action] for s in available}
        gains = {s: Fraction(q[s]) - utilities[s] for s in feasible}
        # A conditional value on only some states cannot consume full-view weights.
        value = interval(q, weights if available == set(state_plans) else None)
        gain = interval(gains)
        expected_gain = (
            interval(gains, weights) if robust and weights is not None else None
        )
        world = {
            s: (
                world_plans[s].get("world_feasibility", {}).get(action)
                if s in world_plans
                else None
            )
            for s in actual_states
        }
        rows[action] = dict(
            q=value,
            gain=gain,
            expected_gain=expected_gain,
            subjective_available_states=tuple(sorted(available)),
            subjective_feasible_states=tuple(sorted(feasible)),
            robust_subjective_feasibility=robust,
            actual_world_feasibility=world,
            scope="CONDITIONAL_ACTION_MODEL_NOT_AUTHORITY_OR_EXECUTION",
        )
    return dict(
        status="COMPUTED",
        actions=rows,
        robust_improvement=tuple(
            a
            for a, row in rows.items()
            if row["robust_subjective_feasibility"]
            and row["gain"]["lower"] is not None
            and Fraction(row["gain"]["lower"]) > 0
        ),
        possible_improvement=tuple(
            a
            for a, row in rows.items()
            if row["gain"]["upper"] is not None and Fraction(row["gain"]["upper"]) > 0
        ),
        frontier=("AFFECT_ACTUAL_OPPORTUNITY_FRONTIER",) if world_frontier else (),
        scope="COMPUTED_GOAL_SPECIFIC_CONTROL_NOT_EMOTION_LABEL",
    )


def predicate(profile, condition):
    """Three-valued evaluation of a declared qualitative semantic hypothesis."""
    dimension, expected = condition["dimension"], condition["value"]
    if dimension in ("desirability", "change_direction", "expectation_gap_direction"):
        possibilities = set(profile["appraisal"][dimension])
        if "UNCOMPUTED" in possibilities:
            return "UNKNOWN"
        return (
            "TRUE"
            if possibilities == {expected}
            else "UNKNOWN" if expected in possibilities else "FALSE"
        )
    if dimension == "attribution":
        from hcl.operators.affect_attribution import attribution_predicate
        return attribution_predicate(profile, condition)
    if dimension == "control":
        computed = profile["control"]
        if computed["status"] != "COMPUTED":
            return "UNKNOWN"
        robust, possible = (
            computed["robust_improvement"],
            computed["possible_improvement"],
        )
        if expected == "IMPROVABLE":
            return "TRUE" if robust else "UNKNOWN" if possible else "FALSE"
        if expected == "NO_IMPROVEMENT":
            return "FALSE" if robust else "UNKNOWN" if possible else "TRUE"
    raise ValueError("unsupported qualitative appraisal predicate")


def generate_affect_hypotheses(
    profiles, mappings, *, previous=(), possible_previous=()
):
    """Competing mappings operate on computed mechanisms, not expression labels."""
    by_goal = {p["goal_id"]: p for p in profiles}
    results = []
    for mapping in mappings:
        tests = [predicate(by_goal[c["goal_id"]], c) for c in mapping["conditions"]]
        memory = mapping.get("requires_previous", ())
        if memory:
            tests.append(
                "TRUE"
                if set(memory) <= set(previous)
                else (
                    "UNKNOWN"
                    if set(memory) <= set(previous) | set(possible_previous)
                    else "FALSE"
                )
            )
        state = (
            "REFUTED"
            if "FALSE" in tests
            else "POSSIBLE" if "UNKNOWN" in tests else "SUPPORTED_CONDITIONAL"
        )
        results.append(
            dict(
                mapping_id=mapping["id"],
                label=mapping["label"],
                status=state,
                antecedent_results=tuple(tests),
                previous_hypotheses=tuple(previous),
                possible_previous_hypotheses=tuple(possible_previous),
                goal_refs=tuple(c["goal_id"] for c in mapping["conditions"]),
                scope="DECLARED_MAPPING_HYPOTHESIS_NOT_PRIVATE_FEELING",
            )
        )
    return tuple(results)


def goal_model_description(plan, goal):
    """Retain the complete finite goal/transition model without source labels."""
    from hcl.memory import codec
    from hcl.kernel.types import thaw

    graph = plan["graph"]
    return dict(
        states=sorted(graph["states"]),
        terminal=sorted(graph["terminal"]),
        utilities={s: encoded(rational(v)) for s, v in goal["utilities"].items()},
        bindings={
            s: sorted(
                codec.canonical(thaw(b["when"]))
                for b in plan["bindings"]
                if b["state"] == s
            )
            for s in graph["states"]
        },
        actions={
            a["id"]: dict(
                cost=encoded(rational(a["cost"])),
                enabled=sorted(a["enabled"]),
                feasible=sorted(a["feasible"]),
                transitions=dict(a["transitions"]),
                observations=dict(a["observations"]),
            )
            for a in graph["actions"]
        },
    )


def compare_goal_models(left, right, *, max_work):
    """Exact bounded state-alias isomorphism, not a color-histogram heuristic.

    Every matched state preserves goal consequence, source predicate, terminality,
    all labeled transitions/opportunities and the observation equivalence relation.
    Raw state/observation symbols may change. Unexplored bijections stay unresolved.
    """
    from hcl.kernel.types import thaw

    left, right = thaw(left), thaw(right)
    work = 0

    class Bound(Exception):
        pass

    def step():
        nonlocal work
        if work >= max_work:
            raise Bound()
        work += 1

    def result(status, mapping=None):
        return dict(
            status=status,
            state_aliases={} if mapping is None else mapping,
            work=work,
            scope="EXACT_FINITE_STATE_ALIAS_COMPARISON_NOT_OPEN_SEMANTIC_EQUIVALENCE",
        )

    try:
        step()
        if left == right:
            return result("EQUIVALENT", {s: s for s in left["states"]})
        if len(left["states"]) != len(right["states"]) or set(left["actions"]) != set(
            right["actions"]
        ):
            return result("DIFFERENT")
        actions = sorted(left["actions"])
        if any(
            left["actions"][a]["cost"] != right["actions"][a]["cost"] for a in actions
        ):
            return result("DIFFERENT")

        def colors(model):
            return {
                s: (
                    model["utilities"][s],
                    s in model["terminal"],
                    tuple(model["bindings"][s]),
                    tuple(
                        (
                            s in model["actions"][a]["enabled"],
                            s in model["actions"][a]["feasible"],
                        )
                        for a in actions
                    ),
                )
                for s in model["states"]
            }

        lcolors, rcolors = colors(left), colors(right)
        choices = {
            s: tuple(t for t in right["states"] if lcolors[s] == rcolors[t])
            for s in left["states"]
        }
        if any(not values for values in choices.values()):
            return result("DIFFERENT")

        def extend(mapping, reverse, first, target):
            mapping, reverse = dict(mapping), dict(reverse)
            pending = [(first, target)]
            while pending:
                s, t = pending.pop()
                if s in mapping:
                    if mapping[s] != t:
                        return None
                    continue
                if t in reverse or lcolors[s] != rcolors[t]:
                    return None
                step()
                for action in actions:
                    a, b = left["actions"][action], right["actions"][action]
                    if any(
                        (a["observations"][s] == a["observations"][u])
                        != (b["observations"][t] == b["observations"][v])
                        for u, v in mapping.items()
                    ):
                        return None
                    pending.append((a["transitions"][s], b["transitions"][t]))
                mapping[s] = t
                reverse[t] = s
            return mapping, reverse

        def search(mapping, reverse):
            if len(mapping) == len(left["states"]):
                return mapping
            s = min(
                (s for s in left["states"] if s not in mapping),
                key=lambda s: sum(t not in reverse for t in choices[s]),
            )
            for t in choices[s]:
                if t in reverse:
                    continue
                extended = extend(mapping, reverse, s, t)
                if extended is not None:
                    found = search(*extended)
                    if found is not None:
                        return found
            return None

        mapping = search({}, {})
        return result("DIFFERENT" if mapping is None else "EQUIVALENT", mapping)
    except Bound:
        return result("UNRESOLVED")


def changed_goals(previous, current, *, max_work):
    """Separate changed appraisal dimensions from newly acquired evidence.

    State-code/variable identities remain in both immutable profiles, but a renamed
    or newly supported state with exactly the same consequences and opportunities
    is not itself a changed appraisal. Numeric, feasibility and frontier changes
    still count, including changes with unchanged qualitative emotion hypotheses.
    """
    from hcl.kernel.types import thaw
    from hcl.memory import codec

    before = {p["goal_id"]: p for p in previous}
    after = {p["goal_id"]: p for p in current}

    def semantic(profile):
        result = thaw(profile)
        result.pop("source_variable_ids", None)
        goal = result.pop("goal")
        result["goal_identity"] = {key: goal[key] for key in ("id", "label")}
        result.pop("goal_model")
        if result["attribution"].get("status") == "CONDITIONAL_FINITE_ATTRIBUTION":
            from hcl.operators.affect_attribution import attribution_semantics
            result["attribution"] = attribution_semantics(result["attribution"])
        for row in result["control"].get("actions", {}).values():
            available = row.pop("subjective_available_states", ())
            feasible = row.pop("subjective_feasible_states", ())
            row["possible_subjective_availability"] = bool(available)
            row["possible_subjective_feasibility"] = bool(feasible)
            row["actual_world_feasibility"] = sorted(
                set(row["actual_world_feasibility"].values()), key=str
            )
        return result

    rows = []
    used = 0
    frontier = set()
    for goal in sorted(set(before) | set(after)):
        old, new = before.get(goal), after.get(goal)
        comparison = None
        unresolved = ()
        if old is None or new is None:
            change = "ADDED" if old is None else "REMOVED"
            dimensions = tuple(sorted(semantic(new or old)))
        else:
            left, right = semantic(old), semantic(new)
            dimensions = tuple(
                key
                for key in sorted(set(left) | set(right))
                if codec.canonical(left.get(key)) != codec.canonical(right.get(key))
            )
            comparison = compare_goal_models(
                old["goal_model"], new["goal_model"], max_work=max(0, max_work - used)
            )
            used += comparison["work"]
            if comparison["status"] == "DIFFERENT":
                dimensions = (*dimensions, "goal_model")
            elif comparison["status"] == "UNRESOLVED":
                unresolved = ("goal_model",)
                frontier.add("AFFECT_GOAL_COMPARISON_FRONTIER")
            change = (
                "REVISED" if dimensions else "UNRESOLVED" if unresolved else "UNCHANGED"
            )
        rows.append(
            dict(
                goal_id=goal,
                change=change,
                changed_dimensions=dimensions,
                unresolved_dimensions=unresolved,
                goal_model_comparison=comparison,
                evidence_changed=codec.canonical(thaw(old))
                != codec.canonical(thaw(new)),
                previous=old,
                current=new,
            )
        )
    return dict(changes=tuple(rows), work=used, frontier=tuple(sorted(frontier)))


def update_coping(model, profiles, utilities, priorities):
    """An explicit appraisal-conditioned priority model, not an enacted strategy.

    The normalized priorities are a modeled strategy parameter. Conditions consume
    actual appraisal dimensions; unresolved conditions keep both mechanisms rather
    than selecting the more convenient outcome. The caller solves every returned
    M05 goal model and keeps these branches hypothetical.
    """
    by_goal = {p["goal_id"]: p for p in profiles}
    base = {g: rational(v) for g, v in priorities.items()}
    if (
        set(base) != set(utilities)
        or any(v < 0 for v in base.values())
        or sum(base.values()) != 1
    ):
        raise ValueError("declared normalized priorities for every goal required")
    states = set(next(iter(utilities.values())))
    if any(set(values) != states for values in utilities.values()):
        raise ValueError("goal consequences must use the same declared state codebook")
    branches = [(base, ())]
    frontier = set()
    for rule in model["adjustments"]:
        evaluations = tuple(
            predicate(by_goal[c["goal_id"]], c) for c in rule["conditions"]
        )
        qualification = (
            "FALSE"
            if "FALSE" in evaluations
            else "UNKNOWN" if "UNKNOWN" in evaluations else "TRUE"
        )
        factors = {g: rational(v) for g, v in rule["multipliers"].items()}
        if set(factors) != set(base) or any(v < 0 for v in factors.values()):
            raise ValueError("bounded nonnegative goal adjustment required")
        next_branches = []
        for weights, history in branches:
            if sum(weights.values()) == 0:
                next_branches.append((weights, history))
                continue
            if qualification != "TRUE":
                next_branches.append(
                    (
                        weights,
                        (
                            *history,
                            dict(
                                rule_id=rule["id"],
                                applied=False,
                                condition_results=evaluations,
                            ),
                        ),
                    )
                )
            if qualification != "FALSE":
                changed = {g: weights[g] * factors[g] for g in weights}
                total = sum(changed.values())
                if total == 0:
                    frontier.add("COPING_ZERO_PRIORITY_UNDEFINED")
                next_branches.append(
                    (
                        {g: v / total if total else v for g, v in changed.items()},
                        (
                            *history,
                            dict(
                                rule_id=rule["id"],
                                applied=True,
                                condition_results=evaluations,
                            ),
                        ),
                    )
                )
        branches = next_branches
        if len(branches) > 16:
            return dict(
                status="FRONTIER_UNEXPLORED",
                branches=(),
                frontier=("COPING_BRANCH_FRONTIER",),
            )
    results = []
    for weights, history in branches:
        consequence = (
            {
                s: sum(weights[g] * rational(utilities[g][s]) for g in weights)
                for s in states
            }
            if sum(weights.values())
            else None
        )
        results.append(
            dict(
                status="COMPUTED" if consequence is not None else "UNDEFINED_PRIORITY",
                priorities={g: encoded(v) for g, v in weights.items()},
                utilities=(
                    None
                    if consequence is None
                    else {s: encoded(v) for s, v in consequence.items()}
                ),
                adjustment_history=history,
                hypothetical=True,
                actually_used="NOT_ESTABLISHED",
            )
        )
    return dict(
        status="PARTIAL" if frontier else "COMPUTED",
        branches=tuple(results),
        frontier=tuple(sorted(frontier)),
        scope="APPRAISAL_CONDITIONED_COPING_MODEL_NOT_ACTUAL_CHARACTER_ACTION",
    )
