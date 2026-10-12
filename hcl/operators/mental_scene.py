"""Actual shared belief -> planning computations over source-bound proposals."""

from dataclasses import replace
from fractions import Fraction
from hashlib import sha256
from itertools import product

from hcl.kernel.types import Delta, HCLFailure, InferenceResult, OpResult, thaw
from hcl.memory import codec
from hcl.operators.epistemic import (
    EpistemicModel,
    EventModel,
    EpistemicLimits,
    EpistemicFrontier,
    Work,
    _evaluate,
    query_belief,
    remaining_states,
    update_perspectives,
)
from hcl.operators.agency import solve_action_values, mixed_policy, rational
from hcl.operators.causal import evaluate_counterfactual
from hcl.semantics.model_compiler import planning_model, structural_model

VERSION = "s3-finite-mental-scene-1"
RESULT_KIND = "CONDITIONAL_COGNITIVE_MODEL"


def variable_id(model, actor, at):
    return (
        "mental-variable:"
        + sha256(codec.dumps([model["source_id"], model["id"], actor, at])).hexdigest()
    )


def initial_model(proposal, limits):
    atoms = tuple(row["id"] for row in proposal["variables"])
    agents = tuple(row["id"] for row in proposal["agents"])
    if 2 ** len(atoms) > limits.max_worlds:
        return None, "WORLD_FRONTIER"
    worlds = {
        "initial:"
        + "".join("1" if value else "0" for value in bits): dict(zip(atoms, bits))
        for bits in product((False, True), repeat=len(atoms))
    }
    designated = tuple(
        key
        for key, values in worlds.items()
        if all(
            row["initial"] is None or values[row["id"]] == row["initial"]
            for row in proposal["variables"]
        )
    )
    relations = {}
    edges = 0
    for agent in agents:
        observed = tuple(
            row["id"] for row in proposal["variables"] if agent in row["observed_by"]
        )
        groups = {}
        for identity, values in worlds.items():
            groups.setdefault(tuple(values[key] for key in observed), []).append(
                identity
            )
        edges += sum(len(group) ** 2 for group in groups.values())
        if edges > limits.max_edges:
            return None, "RELATION_FRONTIER"
        relations[agent] = {
            identity: tuple(groups[tuple(values[key] for key in observed)])
            for identity, values in worlds.items()
        }
    return EpistemicModel(atoms, agents, worlds, relations, designated), None


def event_model(event, agents):
    if event["kind"] == "change":
        variants = {
            "actual": {"pre": True, "post": dict(event["effects"])},
            "skip": {"pre": True, "post": {}},
        }
        relations = {
            agent: {
                "actual": ("actual",) if agent in event["seen_by"] else ("skip",),
                "skip": ("skip",),
            }
            for agent in agents
        }
    else:
        # Private reception does not create common belief that others received,
        # understood or accepted it. Distinct virtual events keep those views apart.
        accepted = (
            set(event["received_by"])
            & set(event["understood_by"])
            & set(event["trusted_by"])
        )
        variants = {
            "actual": {"pre": True, "post": {}},
            "skip": {"pre": True, "post": {}},
        }
        variants.update(
            {
                "accepted:" + agent: {"pre": True, "post": dict(event["effects"])}
                for agent in accepted
            }
        )
        relations = {}
        for agent in agents:
            own = "accepted:" + agent
            relations[agent] = {
                key: (
                    (own,)
                    if agent in accepted and key in ("actual", own)
                    else ("skip",)
                )
                for key in variants
            }
    return EventModel(
        event["id"], variants, relations, ("actual",), tuple(event["assumptions"])
    )


class MentalSceneOperator:
    def run(self, snapshot, issue, allowance, program):
        try:
            return self._run(snapshot, issue, allowance, program)
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            RecursionError,
            ZeroDivisionError,
        ):
            raise HCLFailure(
                "INVALID_REQUEST",
                "mental_model",
                "INVALID_MENTAL_MODEL",
                "model",
                "The declared cognitive model is outside its executable finite contract.",
            ) from None

    def _run(self, snapshot, issue, allowance, program):
        used = 0
        issues = []
        outputs = []
        limits = EpistemicLimits(max_depth=16)

        def batch():
            nonlocal used
            if used >= allowance.max_local_evaluations:
                issues.append("COGNITIVE_BATCH_BUDGET_FRONTIER")
                result["frontier"].append("COGNITIVE_BATCH_BUDGET_FRONTIER")
                return False
            used += 1
            return True

        for proposal in program["models"]:
            result = dict(
                model_id=proposal["id"],
                source_id=proposal["source_id"],
                frame_kind=proposal["frame_kind"],
                assumptions=proposal["assumptions"],
                unmodeled_segments=proposal["unmodeled_segments"],
                inactive_assumptions=[],
                beliefs=[],
                shared_variables=[],
                plans=[],
                causal=[],
                events=[],
                frontier=[],
            )
            outputs.append(result)
            active = set(proposal["active_assumptions"])
            inactive = set(proposal["assumptions"]) - active
            if inactive:
                result["inactive_assumptions"] = sorted(inactive)
                issues.append("MODEL_ASSUMPTION_RETRACTED")
                continue
            if not batch():
                result["frontier"].append("COGNITIVE_BATCH_BUDGET_FRONTIER")
                continue
            model, frontier = initial_model(proposal, limits)
            if frontier:
                issues.append(frontier)
                result["frontier"].append(frontier)
                continue
            required_times = sorted(
                {row["at"] for kind in ("queries", "plans") for row in proposal[kind]}
            )
            timeline = {}
            environments = {}
            effective = set(proposal["assumptions"])
            events = iter(sorted(proposal["events"], key=lambda row: row["at"]))
            pending = next(events, None)
            for point in required_times:
                while (
                    pending is not None and pending["at"] <= point and model is not None
                ):
                    inactive = set(pending["assumptions"]) - active
                    if inactive:
                        result["inactive_assumptions"].extend(sorted(inactive))
                        issues.append("EVENT_ASSUMPTION_RETRACTED")
                        model = None
                        break
                    effective.update(pending["assumptions"])
                    if not batch():
                        model = None
                        result["frontier"].append("COGNITIVE_BATCH_BUDGET_FRONTIER")
                        break
                    model, receipt = update_perspectives(
                        model, event_model(pending, model.agents), limits
                    )
                    result["events"].append(
                        dict(
                            event_id=pending["id"],
                            at=pending["at"],
                            kind=pending["kind"],
                            seen_by=pending["seen_by"],
                            received_by=pending["received_by"],
                            understood_by=pending["understood_by"],
                            trusted_by=pending["trusted_by"],
                            computation=receipt,
                        )
                    )
                    if model is None:
                        result["frontier"].extend(
                            receipt["frontier"] or [receipt["status"]]
                        )
                    pending = next(events, None)
                timeline[point] = model
                environments[point] = tuple(sorted(effective))
            for query in proposal["queries"]:
                mental = timeline[query["at"]]
                if mental is None or not batch():
                    result["beliefs"].append(
                        dict(
                            query_id=query["id"],
                            at=query["at"],
                            formula=query["formula"],
                            status="FRONTIER_UNEXPLORED",
                            possible_values=[False, True],
                        )
                    )
                    continue
                computed = query_belief(mental, query["formula"], limits)
                result["beliefs"].append(
                    dict(
                        query_id=query["id"],
                        at=query["at"],
                        formula=query["formula"],
                        assumptions=environments[query["at"]],
                        **computed
                    )
                )
                result["frontier"].extend(computed["frontier"])
            shared = {}
            for plan in proposal["plans"]:
                mental = timeline[plan["at"]]
                identity = variable_id(proposal, plan["actor"], plan["at"])
                if mental is None or not batch():
                    result["plans"].append(
                        dict(
                            plan_id=plan["id"],
                            belief_variable_id=identity,
                            status="FRONTIER_UNEXPLORED",
                            q={},
                            best_actions=[],
                        )
                    )
                    continue
                view = remaining_states(mental, (plan["actor"],), limits)
                actual = remaining_states(mental, (), limits)
                if view["frontier"] or actual["frontier"]:
                    result["frontier"].extend((*view["frontier"], *actual["frontier"]))
                    result["plans"].append(
                        dict(
                            plan_id=plan["id"],
                            belief_variable_id=identity,
                            status="FRONTIER_UNEXPLORED",
                            q={},
                            best_actions=[],
                        )
                    )
                    continue
                bindings = plan["bindings"]
                mapping_work = Work(limits)

                def mapped(worlds):
                    states = {}
                    for world in worlds:
                        matches = [
                            row["state"]
                            for row in bindings
                            if _evaluate(mental, world, row["when"], mapping_work)
                            == frozenset((True,))
                        ]
                        if len(matches) != 1:
                            return None
                        states[world] = matches[0]
                    return states

                try:
                    selected_map = mapped(view["worlds"])
                    actual_map = mapped(actual["worlds"])
                    selected = (
                        None if selected_map is None else set(selected_map.values())
                    )
                    actual_states = (
                        None if actual_map is None else set(actual_map.values())
                    )
                except EpistemicFrontier:
                    result["plans"].append(
                        dict(
                            plan_id=plan["id"],
                            belief_variable_id=identity,
                            status="FRONTIER_UNEXPLORED",
                            q={},
                            best_actions=[],
                        )
                    )
                    result["frontier"].append("STATE_MAPPING_FRONTIER")
                    continue
                mental_variable = dict(
                    variable_id=identity,
                    actor=plan["actor"],
                    at=plan["at"],
                    remaining_states=tuple(dict(v) for v in view["values"]),
                    remaining_world_ids=view["worlds"],
                    status=view["status"],
                    assumptions=environments[plan["at"]],
                    history=mental.history,
                )
                if identity in shared and shared[identity] != mental_variable:
                    raise ValueError(
                        "one shared mental variable must have one actual perspective value"
                    )
                shared[identity] = mental_variable
                if not selected or actual_states is None:
                    result["plans"].append(
                        dict(
                            plan_id=plan["id"],
                            belief_variable_id=identity,
                            status="UNMAPPED_OR_INCONSISTENT_BELIEF",
                            q={},
                            best_actions=[],
                        )
                    )
                    issues.append("UNMAPPED_OR_INCONSISTENT_BELIEF")
                    continue
                weights = plan["weights"]
                if weights is None:
                    if len(selected) != 1:
                        result["plans"].append(
                            dict(
                                plan_id=plan["id"],
                                belief_variable_id=identity,
                                status="UNSPECIFIED_BELIEF_WEIGHTS",
                                q={},
                                best_actions=[],
                            )
                        )
                        issues.append("UNSPECIFIED_BELIEF_WEIGHTS")
                        continue
                    weights = {next(iter(selected)): "1"}
                if {
                    key for key, value in weights.items() if rational(value) > 0
                } != selected:
                    raise ValueError(
                        "belief weights must bind every remaining planning state and no inaccessible state"
                    )
                computed = solve_action_values(
                    planning_model(plan["graph"]),
                    weights,
                    plan["graph"]["horizon"],
                    actual_state=(
                        next(iter(actual_states)) if len(actual_states) == 1 else None
                    ),
                )
                value = dict(
                    plan_id=plan["id"],
                    actor=plan["actor"],
                    at=plan["at"],
                    belief_variable_id=identity,
                    actual_possible_states=sorted(actual_states),
                    planning_states=sorted(selected),
                    state_bindings=bindings,
                    belief_world_bindings=selected_map,
                    actual_world_bindings=actual_map,
                    **computed
                )
                if (
                    computed["status"] == "SOLVED"
                    and computed["q"]
                    and plan["policy"] is not None
                ):
                    value["policy"] = mixed_policy(
                        computed["q"], **dict(plan["policy"])
                    )
                result["plans"].append(value)
                result["frontier"].extend(computed["frontier"])
            result["shared_variables"] = list(shared.values())
            for causal in proposal["causal"]:
                if not batch():
                    result["frontier"].append("COGNITIVE_BATCH_BUDGET_FRONTIER")
                    break
                computed = evaluate_counterfactual(
                    structural_model(causal["model"]),
                    causal["target"],
                    observations=dict(causal["observations"]),
                    interventions=dict(causal["interventions"]),
                )
                result["causal"].append(dict(query_id=causal["id"], **computed))
                result["frontier"].extend(computed["frontier"])
            issues.extend(result["frontier"])
            if proposal["unmodeled_segments"]:
                issues.append("UNMODELED_SOURCE_SEGMENTS")
        values = dict(
            operator_version=VERSION,
            models=outputs,
            semantic_certified=False,
            candidate_completeness="NOT_ESTABLISHED",
            batch_evaluations=used,
            scope="SOURCE_BOUND_CANDIDATE_MECHANISMS_NOT_PRIVATE_TRUTH",
            source_versions=dict(snapshot.source_versions),
        )
        inference = InferenceResult(
            "mental-result:"
            + sha256(
                codec.dumps([issue.issue_id, snapshot.source_versions, program, values])
            ).hexdigest(),
            RESULT_KIND,
            values,
            tuple(
                sorted(
                    {
                        a
                        for m in program["models"]
                        for a in (
                            *m["assumptions"],
                            *(a for e in m["events"] for a in e["assumptions"]),
                        )
                        if a in m["active_assumptions"]
                    }
                )
            ),
            tuple(snapshot.source_versions),
            (),
            snapshot.rule_version,
            "CONDITIONAL_FINITE_COGNITIVE_MODEL",
        )
        delta = Delta(
            snapshot.session_id,
            snapshot.principal,
            snapshot.revision,
            snapshot.access_epoch,
            snapshot.rule_version,
            snapshot.source_versions,
            (inference,),
        )
        return OpResult(
            "mental_scene.execute",
            VERSION,
            snapshot.source_versions,
            ("append_inference",),
            (inference.result_id,),
            tuple(sorted(set(issues))),
            {"local_evaluations": used},
            (),
            delta,
        )
