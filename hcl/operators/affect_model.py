"""Actual M03 perspectives -> goal appraisal -> M05 coping -> hypothetical updates."""

from dataclasses import replace
from fractions import Fraction
from hashlib import sha256
from hcl.kernel.types import Delta, HCLFailure, InferenceResult, OpResult, thaw
from hcl.memory import codec
from hcl.operators.mental_scene import MentalSceneOperator, variable_id
from hcl.operators.epistemic import remaining_states, EpistemicLimits
from hcl.operators.agency import solve_action_values, encoded, rational
from hcl.operators.interaction_model import map_view
from hcl.operators.affect import (
    VERSION,
    appraise,
    control,
    generate_affect_hypotheses,
    update_coping,
    changed_goals,
    validate_observation_coarsening,
    goal_model_description,
)
from hcl.semantics.model_compiler import planning_model

KIND = "CONDITIONAL_AFFECT_MODEL"


def weights_for(states, weights):
    states = set(states)
    if weights is None:
        return {next(iter(states)): "1"} if len(states) == 1 else None
    parsed = {s: rational(v) for s, v in weights.items()}
    if (
        any(v < 0 for v in parsed.values())
        or sum(parsed.values()) != 1
        or {s for s, v in parsed.items() if v > 0} != states
    ):
        raise ValueError("affect weights differ from actual perspective support")
    return {s: encoded(v) for s, v in parsed.items() if v > 0}


def forecast(episode, plan, previous):
    if episode["forecast_action"] is None:
        return dict(status="NO_PROSPECTIVE_MODEL", states=None, weights=None)
    action = next(
        a for a in plan["graph"]["actions"] if a["id"] == episode["forecast_action"]
    )
    states = previous["mapping"]["states"]
    if not set(states) <= set(action["enabled"]) or not set(states) <= set(
        action["feasible"]
    ):
        return dict(status="FORECAST_OPPORTUNITY_UNRESOLVED", states=None, weights=None)
    distribution = weights_for(states, episode["previous_weights"])
    predicted = tuple(sorted({action["transitions"][s] for s in states}))
    mass = None
    if distribution is not None:
        mass = {s: Fraction(0) for s in predicted}
        for s, value in distribution.items():
            mass[action["transitions"][s]] += Fraction(value)
        mass = {s: encoded(v) for s, v in mass.items() if v > 0}
    return dict(
        status="COMPUTED",
        states=predicted,
        weights=mass,
        action_id=action["id"],
        input_variable_id=previous["variable_id"],
        transitions=action["transitions"],
        scope="PROSPECTIVE_SOURCE_TRANSITION_HYPOTHESIS_NOT_PREVIOUS_STATE",
    )


def coping_graph(plan, coping, utilities):
    model = planning_model(plan["graph"])
    for action in model.actions:
        if action.action_id in coping["observation_overrides"]:
            validate_observation_coarsening(
                action.observations, coping["observation_overrides"][action.action_id]
            )
    actions = tuple(
        replace(
            a,
            observations=coping["observation_overrides"].get(
                a.action_id, a.observations
            ),
        )
        for a in model.actions
        if a.action_id in coping["action_ids"]
    )
    return replace(model, utilities=utilities, actions=actions)


def consequences(episode, plan, profiles, coping, branch, computed):
    """Real declared transitions produce hypothetical future appraisal, not events."""
    outcomes = []
    distribution = computed.get("belief", {})
    actions = {a["id"]: a for a in plan["graph"]["actions"]}
    for action_id in computed.get("q", {}):
        action = actions[action_id]
        mass = {}
        for state, weight in distribution.items():
            target = action["transitions"][state]
            mass[target] = mass.get(target, Fraction(0)) + Fraction(weight)
        next_weights = {s: encoded(v) for s, v in mass.items() if v > 0}
        next_profiles = []
        for goal in episode["goals"]:
            next_profiles.append(
                dict(
                    goal_id=goal["id"],
                    appraisal=appraise(
                        goal["utilities"],
                        tuple(distribution),
                        tuple(next_weights),
                        previous_weights=distribution,
                        current_weights=next_weights,
                    ),
                )
            )
        outcomes.append(
            dict(
                action_id=action_id,
                status=(
                    "PREDICTED_IF_FEASIBLE"
                    if computed["subjective_feasibility"][action_id]
                    else "COUNTERFACTUAL_INFEASIBLE_UNDER_DECLARED_MODEL"
                ),
                subjectively_feasible=computed["subjective_feasibility"][action_id],
                predicted_weights=next_weights,
                next_profiles=next_profiles,
                hypothetical=True,
                actually_occurred="NOT_ESTABLISHED",
                planning_horizon=coping["horizon"],
                scope="ONE_TRANSITION_APPRAISAL_NOT_FULL_HORIZON_OUTCOME",
            )
        )
    return outcomes


def derive_episode(
    episode, plan, views, state_plans, prior, channels, solve, *, allowance
):
    """Derived values depend on actual perspectives and actual solver records."""
    previous, current, actual = views["previous"], views["current"], views["actual"]
    before = previous["mapping"]["states"]
    after = current["mapping"]["states"]
    before_weights = weights_for(before, episode["previous_weights"])
    current_weights = weights_for(after, episode["current_weights"])
    predicted = forecast(episode, plan, previous)
    profiles = []
    frontier = (
        [predicted["status"]]
        if predicted["status"] not in ("COMPUTED", "NO_PROSPECTIVE_MODEL")
        else []
    )
    for goal in episode["goals"]:
        plans = state_plans.get(goal["id"], {})
        computed = control(
            goal["utilities"],
            {s: plans[s] for s in after if s in plans},
            weights=current_weights,
            actual_states=actual["mapping"]["states"],
            actual_plans=plans,
        )
        if set(after) - set(plans):
            computed = dict(
                status="UNCOMPUTED",
                actions={},
                robust_improvement=(),
                possible_improvement=(),
                frontier=("AFFECT_PLANNING_FRONTIER",),
            )
        profile = dict(
            goal_id=goal["id"],
            goal=goal,
            goal_model=goal_model_description(plan, goal),
            appraisal=appraise(
                goal["utilities"],
                before,
                after,
                previous_weights=before_weights,
                current_weights=current_weights,
                expected_states=predicted["states"],
                expected_weights=predicted["weights"],
            ),
            control=computed,
            source_variable_ids=(previous["variable_id"], current["variable_id"]),
            attribution=dict(status="NOT_MODELED"),
            normative_relevance=dict(status="NOT_MODELED"),
            identity_relevance=dict(status="NOT_MODELED"),
        )
        frontier.extend(computed["frontier"])
        profiles.append(profile)
    previous_labels = tuple(
        h["label"]
        for h in prior.get("hypotheses", ())
        if h["status"] == "SUPPORTED_CONDITIONAL"
    )
    possible_labels = tuple(
        h["label"] for h in prior.get("hypotheses", ()) if h["status"] == "POSSIBLE"
    )
    hypotheses = generate_affect_hypotheses(
        profiles,
        episode["mappings"],
        previous=previous_labels,
        possible_previous=possible_labels,
    )
    alternatives = []
    utilities = {g["id"]: g["utilities"] for g in episode["goals"]}
    for coping in episode["coping"]:
        generated = update_coping(coping, profiles, utilities, coping["priorities"])
        frontier.extend(generated["frontier"])
        rows = []
        for branch in generated["branches"]:
            row = dict(input=branch, computation={}, consequences=[])
            rows.append(row)
            if branch["status"] != "COMPUTED":
                row["status"] = branch["status"]
                continue
            if current_weights is None:
                row["status"] = "UNSPECIFIED_BELIEF_WEIGHTS"
                frontier.append("COPING_PROBABILITY_UNSPECIFIED")
                continue
            try:
                graph = coping_graph(plan, coping, branch["utilities"])
            except ValueError:
                # Derived rational denominators can exceed the old input numeric
                # bound. Preserve the appraisal instead of misclassifying input.
                row["status"] = "FRONTIER_UNEXPLORED"
                frontier.append("AFFECT_DERIVED_NUMERIC_FRONTIER")
                continue
            computation = solve(graph, current_weights, coping["horizon"])
            row["computation"] = computation
            row["status"] = computation["status"]
            frontier.extend(computation["frontier"])
            if computation["status"] == "SOLVED":
                row["consequences"] = consequences(
                    episode, plan, profiles, coping, branch, computation
                )
        alternatives.append(
            dict(
                coping_id=coping["id"],
                kind=coping["kind"],
                input=coping,
                generated=generated,
                branches=rows,
                actually_used="NOT_ESTABLISHED",
            )
        )
    coping_work = sum(
        row["computation"].get("expansions", 0)
        for alternative in alternatives
        for row in alternative["branches"]
    )
    comparison = (
        changed_goals(
            prior.get("profiles", ()),
            profiles,
            max_work=max(0, allowance - coping_work),
        )
        if prior
        else dict(changes=(), work=0, frontier=())
    )
    frontier.extend(comparison["frontier"])
    return dict(
        status="COMPUTED",
        profiles=profiles,
        forecast=predicted,
        hypotheses=hypotheses,
        coping=alternatives,
        channels=tuple(
            c
            for c in channels
            if c["actor"] == episode["actor"] and c["at"] <= episode["at"]
        ),
        reappraisal=dict(
            previous_id=episode["previous_id"],
            kind=episode["revision_kind"],
            changes=comparison["changes"],
            comparison_work=comparison["work"],
            frontier=comparison["frontier"],
            character_reappraisal=(
                "NOT_ESTABLISHED_ANALYST_ALTERNATIVE"
                if episode["revision_kind"] == "ANALYST_REINTERPRETATION"
                else "CONDITIONAL_ON_SOURCE_MODEL"
            ),
        ),
        frontier=tuple(sorted(set(frontier))),
        attribution_scope="UNMODELED_NOT_ZERO_BLAME",
        calibration="QUALITATIVE_UNCALIBRATED_MODEL_NOT_PRIVATE_EMOTION_MEASUREMENT",
    )


class AffectModelOperator:
    def run(self, snapshot, issue, allowance, program):
        try:
            return self._run(snapshot, issue, allowance, thaw(program))
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            RecursionError,
            OverflowError,
            ZeroDivisionError,
        ):
            raise HCLFailure(
                "INVALID_REQUEST",
                "affect",
                "INVALID_AFFECT_MODEL",
                "model",
                "The conditional appraisal is outside its finite executable model.",
            ) from None

    def _run(self, snapshot, issue, allowance, program, *, shared_cognition=None):
        used = 0
        limit = allowance.max_local_evaluations
        outputs = []
        issues = []

        def solve(model, weights, horizon, actual_state=None):
            nonlocal used
            if used >= limit:
                return dict(
                    status="FRONTIER_UNEXPLORED",
                    q={},
                    best_actions=[],
                    expansions=0,
                    frontier=["AFFECT_PLANNING_FRONTIER"],
                )
            result = solve_action_values(
                model,
                weights,
                horizon,
                max_expansions=max(1, limit - used),
                actual_state=actual_state,
            )
            used += result["expansions"]
            return result

        for model in program["models"]:
            original = model["mental"]
            if shared_cognition is None:
                trace = {}
                times = {t for e in model["episodes"] for t in (e["before"], e["at"])}
                operation = MentalSceneOperator()._run(
                    snapshot,
                    issue,
                    replace(allowance, max_local_evaluations=max(0, limit - used)),
                    dict(models=[original]),
                    trace=trace,
                    trace_times={original["id"]: tuple(sorted(times))},
                )
                used += operation.resource_usage["local_evaluations"]
            else:
                operation, trace = shared_cognition[
                    (original["source_id"], original["id"])
                ].bind(snapshot, original)
            issues.extend(operation.issues)
            actual = operation.candidate_delta.new_inferences[0]
            mental = thaw(actual.values)["models"][0]
            output = dict(
                model_id=original["id"],
                source_id=original["source_id"],
                frame_kind=original["frame_kind"],
                inputs=model,
                actual_mental=dict(
                    result_id=actual.result_id,
                    kind=actual.kind,
                    values=thaw(actual.values),
                    assumption_environments=actual.assumption_environments,
                    source_versions=dict(operation.read_set),
                    issues=operation.issues,
                ),
                domain_issues=operation.issues,
                episodes=[],
                frontier=[],
            )
            outputs.append(output)
            if original["id"] not in trace:
                output["frontier"].append("AFFECT_MENTAL_STATE_UNAVAILABLE")
                issues.extend(output["frontier"])
                continue
            timeline, environments = trace[original["id"]]
            completed = {}
            for episode in model["episodes"]:
                plan = next(
                    p for p in original["plans"] if p["id"] == episode["plan_id"]
                )
                row = dict(
                    episode_id=episode["id"],
                    input=episode,
                    plan=plan,
                    views={},
                    state_plans={},
                    derived={},
                    status="UNCOMPUTED",
                )
                output["episodes"].append(row)
                for role, at, actor in (
                    ("previous", episode["before"], episode["actor"]),
                    ("current", episode["at"], episode["actor"]),
                    ("actual", episode["at"], None),
                ):
                    if timeline.get(at) is None or used >= limit:
                        break
                    used += 1
                    view = remaining_states(
                        timeline[at],
                        () if actor is None else (actor,),
                        EpistemicLimits(max_depth=16),
                    )
                    row["views"][role] = dict(
                        variable_id=variable_id(
                            original, () if actor is None else actor, at
                        ),
                        actor=actor,
                        at=at,
                        result_id=actual.result_id,
                        source_versions=dict(snapshot.source_versions),
                        assumptions=environments[at],
                        view=view,
                        mapping=map_view(view, plan),
                        history=timeline[at].history,
                    )
                if set(row["views"]) != {"previous", "current", "actual"} or any(
                    v["mapping"]["status"] != "MAPPED" for v in row["views"].values()
                ):
                    output["frontier"].append("AFFECT_VIEW_FRONTIER")
                    continue
                row["assumption_environments"] = sorted(
                    {a for v in row["views"].values() for a in v["assumptions"]}
                )
                states = sorted(
                    set(row["views"]["current"]["mapping"]["states"])
                    | set(row["views"]["actual"]["mapping"]["states"])
                )
                for goal in episode["goals"]:
                    graph = replace(
                        planning_model(plan["graph"]), utilities=goal["utilities"]
                    )
                    row["state_plans"][goal["id"]] = {
                        state: solve(graph, {state: "1"}, 1, actual_state=state)
                        for state in states
                    }
                start = used
                calls = []

                def recorded_solve(graph, weights, horizon):
                    remaining = max(0, limit - used)
                    result = solve(graph, weights, horizon)
                    calls.append(
                        dict(
                            allowance=remaining,
                            weights=weights,
                            horizon=horizon,
                            result=result,
                        )
                    )
                    return result

                prior = completed.get(episode["previous_id"], {})
                if episode["previous_id"] is not None and not prior:
                    output["frontier"].append("AFFECT_PREVIOUS_VERSION_UNAVAILABLE")
                    continue
                row["derived"] = derive_episode(
                    episode,
                    plan,
                    row["views"],
                    row["state_plans"],
                    prior,
                    model["channels"],
                    recorded_solve,
                    allowance=limit - start,
                )
                used += row["derived"]["reappraisal"]["comparison_work"]
                row["coping_solver_calls"] = calls
                row["status"] = "COMPUTED"
                row["derived_allowance"] = limit - start
                completed[episode["id"]] = row["derived"]
                output["frontier"].extend(row["derived"]["frontier"])
            issues.extend(output["frontier"])
        values = dict(
            operator_version=VERSION,
            models=outputs,
            semantic_certified=False,
            candidate_completeness="NOT_ESTABLISHED",
            source_versions=dict(snapshot.source_versions),
            local_evaluations=used,
            scope="CONDITIONAL_GOAL_APPRAISAL_AND_COPING_NOT_PRIVATE_EMOTION_OR_DIAGNOSIS",
        )
        inference = InferenceResult(
            "affect-result:"
            + sha256(codec.dumps([issue.issue_id, values])).hexdigest(),
            KIND,
            values,
            tuple(
                sorted(
                    {
                        a
                        for m in program["models"]
                        for a in m["mental"]["active_assumptions"]
                    }
                )
            ),
            tuple(snapshot.source_versions),
            (),
            snapshot.rule_version,
            "CONDITIONAL_FINITE_AFFECT",
        )
        return OpResult(
            "affect.execute",
            VERSION,
            snapshot.source_versions,
            ("append_inference",),
            (inference.result_id,),
            tuple(sorted(set(issues))),
            dict(local_evaluations=used),
            (),
            Delta(
                snapshot.session_id,
                snapshot.principal,
                snapshot.revision,
                snapshot.access_epoch,
                snapshot.rule_version,
                snapshot.source_versions,
                (inference,),
            ),
        )


def verify_affect(values, *, shared_cognition=None):
    """Recompute finite dependencies before consuming any composed appraisal."""
    from hcl.operators.mental_scene import initial_model, event_model
    from hcl.operators.epistemic import update_perspectives

    canonical = lambda value: codec.canonical(thaw(value))
    data = thaw(values)
    if (
        data["semantic_certified"] is not False
        or data["candidate_completeness"] != "NOT_ESTABLISHED"
    ):
        raise ValueError("conditional affect boundary missing")
    for output in data["models"]:
        model = output["inputs"]
        original = model["mental"]
        actual = output["actual_mental"]
        if (output["model_id"], output["source_id"], output["frame_kind"]) != (
            original["id"],
            original["source_id"],
            original["frame_kind"],
        ):
            raise ValueError("affect model identity changed")
        if actual["kind"] != "CONDITIONAL_COGNITIVE_MODEL":
            raise ValueError("actual cognitive result kind changed")
        if [e["episode_id"] for e in output["episodes"]] != [
            e["id"] for e in model["episodes"]
        ]:
            if output["episodes"] or output["frontier"] != [
                "AFFECT_MENTAL_STATE_UNAVAILABLE"
            ]:
                raise ValueError("affect episode coverage changed")
        mental = actual["values"]["models"]
        if len(mental) != 1 or (
            mental[0]["model_id"],
            mental[0]["source_id"],
            mental[0]["frame_kind"],
        ) != (original["id"], original["source_id"], original["frame_kind"]):
            raise ValueError("nested cognitive identity changed")
        if (
            actual["source_versions"] != data["source_versions"]
            or actual["values"]["source_versions"] != data["source_versions"]
            or output["domain_issues"] != actual["issues"]
        ):
            raise ValueError("affect domain binding changed")
        limits = EpistemicLimits(max_depth=16)
        if shared_cognition is not None:
            bundle = shared_cognition[(original["source_id"], original["id"])]
            if codec.canonical(thaw(bundle.original)) != canonical(original):
                raise ValueError("shared affect cognition input mismatch")
            nested = bundle.operation.candidate_delta.new_inferences[0]
            if actual["result_id"] != nested.result_id or canonical(
                actual["values"]
            ) != canonical(nested.values):
                raise ValueError("affect is not consuming the shared cognitive result")
            states, environments = bundle.trace.get(original["id"], ({}, {}))
        else:
            cognitive, frontier = initial_model(original, limits)
            effective = set(original["assumptions"])
            if not effective <= set(original["active_assumptions"]):
                cognitive = None
            events = iter(sorted(original["events"], key=lambda e: e["at"]))
            pending = next(events, None)
            times = sorted(
                {v["at"] for row in output["episodes"] for v in row["views"].values()}
            )
            states = {}
            environments = {}
            for at in times:
                while (
                    pending is not None
                    and pending["at"] <= at
                    and cognitive is not None
                ):
                    if not set(pending["assumptions"]) <= set(
                        original["active_assumptions"]
                    ):
                        cognitive = None
                        break
                    effective.update(pending["assumptions"])
                    cognitive, _ = update_perspectives(
                        cognitive, event_model(pending, cognitive.agents), limits
                    )
                    pending = next(events, None)
                states[at] = cognitive
                environments[at] = tuple(sorted(effective))
        completed = {}
        for row in output["episodes"]:
            episode = next(e for e in model["episodes"] if e["id"] == row["episode_id"])
            plan = next(p for p in original["plans"] if p["id"] == episode["plan_id"])
            if episode != row["input"] or plan != row["plan"]:
                raise ValueError("affect episode input binding changed")
            for coping in episode["coping"]:
                for action_id, observations in coping["observation_overrides"].items():
                    original_action = next(
                        a for a in plan["graph"]["actions"] if a["id"] == action_id
                    )
                    validate_observation_coarsening(
                        original_action["observations"], observations
                    )
            roles = {
                "previous": (episode["before"], episode["actor"]),
                "current": (episode["at"], episode["actor"]),
                "actual": (episode["at"], None),
            }
            for role, variable in row["views"].items():
                at, actor = roles[role]
                cognitive = states[at]
                if cognitive is None:
                    raise ValueError("view from uncomputed mental time")
                view = remaining_states(
                    cognitive, () if actor is None else (actor,), limits
                )
                expected = dict(
                    variable_id=variable_id(
                        original, () if actor is None else actor, at
                    ),
                    actor=actor,
                    at=at,
                    result_id=actual["result_id"],
                    source_versions=data["source_versions"],
                    assumptions=environments[at],
                    view=view,
                    mapping=map_view(view, plan),
                    history=cognitive.history,
                )
                if canonical(expected) != canonical(variable):
                    raise ValueError(
                        "affect view differs from actual M03 event mechanism"
                    )
            if row["status"] != "COMPUTED":
                if row["derived"]:
                    raise ValueError("uncomputed affect contains conclusions")
                continue
            if set(row["views"]) != set(roles):
                raise ValueError("affect perspective missing")
            environments_expected = sorted(
                {a for v in row["views"].values() for a in v["assumptions"]}
            )
            if row["assumption_environments"] != environments_expected:
                raise ValueError("affect assumptions changed")
            support = set(row["views"]["current"]["mapping"]["states"]) | set(
                row["views"]["actual"]["mapping"]["states"]
            )
            if set(row["state_plans"]) != {g["id"] for g in episode["goals"]}:
                raise ValueError("goal plan missing")
            for goal in episode["goals"]:
                graph = replace(
                    planning_model(plan["graph"]), utilities=goal["utilities"]
                )
                plans = row["state_plans"][goal["id"]]
                if set(plans) != support:
                    raise ValueError("goal plan state coverage changed")
                for state, result in plans.items():
                    if result["expansions"] == 0:
                        expected = dict(
                            status="FRONTIER_UNEXPLORED",
                            q={},
                            best_actions=[],
                            expansions=0,
                            frontier=["AFFECT_PLANNING_FRONTIER"],
                        )
                    else:
                        expected = solve_action_values(
                            graph,
                            {state: "1"},
                            1,
                            max_expansions=result["expansions"],
                            actual_state=state,
                        )
                    if canonical(result) != canonical(expected):
                        raise ValueError("goal Q differs from actual M05 computation")
            calls = iter(row["coping_solver_calls"])

            def checked_solve(graph, weights, horizon):
                call = next(calls)
                if call["weights"] != weights or call["horizon"] != horizon:
                    raise ValueError("coping solver input changed")
                if call["allowance"] <= 0:
                    expected = dict(
                        status="FRONTIER_UNEXPLORED",
                        q={},
                        best_actions=[],
                        expansions=0,
                        frontier=["AFFECT_PLANNING_FRONTIER"],
                    )
                else:
                    expected = solve_action_values(
                        graph, weights, horizon, max_expansions=call["allowance"]
                    )
                if canonical(expected) != canonical(call["result"]):
                    raise ValueError("coping Q differs from actual M05 computation")
                return expected

            prior = completed.get(episode["previous_id"], {})
            if episode["previous_id"] is not None and not prior:
                raise ValueError("previous appraisal unavailable")
            expected = derive_episode(
                episode,
                plan,
                row["views"],
                row["state_plans"],
                prior,
                model["channels"],
                checked_solve,
                allowance=row["derived_allowance"],
            )
            if next(calls, None) is not None or canonical(expected) != canonical(
                row["derived"]
            ):
                raise ValueError("affect composition differs from actual dependencies")
            if not set(row["derived"]["frontier"]) <= set(output["frontier"]):
                raise ValueError("affect limitations missing")
            completed[episode["id"]] = row["derived"]
