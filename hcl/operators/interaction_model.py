"""Shared M03 views -> M07 message games/lifecycle -> actual M05 choice values."""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

from hcl.kernel.types import Delta, HCLFailure, InferenceResult, OpResult, thaw
from hcl.memory import codec
from hcl.operators.epistemic import remaining_states, EpistemicLimits
from hcl.operators.mental_scene import MentalSceneOperator, variable_id
from hcl.operators.agency import solve_action_values
from hcl.operators.interaction import (
    VERSION,
    interpreted_event,
    message_game,
    listener_actions,
    speaker_choices,
    commitment_history,
    acknowledgment_chains,
)
from hcl.semantics.model_compiler import planning_model
from hcl.semantics.interaction_compiler import query_id, relevant_times

KIND = "CONDITIONAL_INTERACTION_MODEL"


def receipts(model, actual):
    """Only actual APPLIED M03 events can establish receipt or interpretation."""
    computed = actual["values"]["models"][0]
    effective = set(model["mental"]["assumptions"])
    qualified = {}
    source_events = {e["id"]: e for e in model["mental"]["events"]}
    for row in computed["events"]:
        event = source_events[row["event_id"]]
        if row["computation"]["status"] != "APPLIED":
            continue
        if (
            row["at"] != event["at"]
            or row["received_by"] != event["received_by"]
            or set(row["computation"]["assumptions"]) != set(event["assumptions"])
            or not set(event["assumptions"])
            <= set(model["mental"]["active_assumptions"])
        ):
            raise ValueError("receipt differs from actual M03 event")
        effective.update(event["assumptions"])
        qualified[event["id"]] = dict(
            result_id=actual["result_id"],
            assumption_environments=tuple(sorted(effective)),
        )
    events = {e["id"]: e for e in model["mental"]["events"]}
    deliveries, interpretations = [], []
    for message in model["utterances"]:
        for delivery in message["deliveries"]:
            event = events[delivery["event_id"]]
            if event["id"] not in qualified or event["at"] > model["through"]:
                continue
            evidence = qualified[event["id"]]
            for actor in event["received_by"]:
                deliveries.append(
                    dict(
                        message_id=message["id"],
                        actor=actor,
                        at=event["at"],
                        event_id=event["id"],
                        **evidence,
                    )
                )
            for reading in delivery["readings"]:
                interpretations.append(
                    dict(
                        message_id=message["id"],
                        actor=reading["actor"],
                        at=event["at"],
                        versions=reading["versions"],
                        contents=reading["contents"],
                        event_id=event["id"],
                        **evidence,
                    )
                )
    return deliveries, interpretations


def commitment_facts(model, terms, actual):
    """Retain each genuine query's status; absent frontier environments are unknown."""
    mental = actual["values"]["models"][0]
    beliefs = {q["query_id"]: q for q in mental["beliefs"]}
    facts = []
    for at in relevant_times(model, terms):
        fact = dict(at=at, result_refs={}, query_status={}, frontier=[])
        assumptions, missing = set(), False
        for field in ("condition", "outcome"):
            qid = query_id(terms, field, at)
            query = beliefs[qid]
            if query["formula"] != terms[field] or query["at"] != at:
                raise ValueError("commitment query identity changed")
            fact["query_status"][field] = query["status"]
            if query["status"] == "FRONTIER_UNEXPLORED":
                missing |= "assumptions" not in query
                assumptions.update(query.get("assumptions", ()))
                fact["frontier"].extend(
                    query.get("frontier", ())
                    or mental["frontier"]
                    or ("MENTAL_QUERY_UNEXPLORED",)
                )
            else:
                assumptions.update(query["assumptions"])
            fact[field] = (
                query["possible_values"]
                if query["status"] == "DETERMINATE"
                else [False, True]
            )
            fact["result_refs"][field] = dict(
                result_id=actual["result_id"], query_id=qid
            )
        fact["assumption_environments"] = sorted(assumptions)
        fact["assumption_status"] = (
            "NOT_FULLY_COMPUTED" if missing else "BOUND_TO_QUERY_RESULTS"
        )
        fact["frontier"] = sorted(set(fact["frontier"]))
        facts.append(fact)
    return facts


def qualified_commitment_history(
    terms, facts, acts, deliveries, interpretations, *, through
):
    """An unexecuted query is not evidence of absent acceptance or fulfillment."""
    unresolved = [
        fact for fact in facts if "FRONTIER_UNEXPLORED" in fact["query_status"].values()
    ]
    if not unresolved:
        return commitment_history(
            terms, facts, acts, deliveries, interpretations, through=through
        )
    cut = min(fact["at"] for fact in unresolved)
    earlier = [f for f in facts if f["at"] < cut]
    prefix_at = max((f["at"] for f in earlier), default=terms["offered_at"] - 1)
    prefix = commitment_history(
        terms, earlier, acts, deliveries, interpretations, through=prefix_at
    )
    return dict(
        prefix,
        status="FRONTIER_UNEXPLORED",
        unresolved_from=cut,
        frontier=tuple(
            sorted(
                set(prefix["frontier"])
                | {"COMMITMENT_MENTAL_FRONTIER"}
                | {f for fact in unresolved for f in fact["frontier"]}
            )
        ),
    )


def truth(node, valuation):
    if type(node) is bool:
        return node
    if node["op"] == "atom":
        return valuation[node["name"]]
    if node["op"] == "not":
        return not truth(node["arg"], valuation)
    if node["op"] in ("and", "or"):
        values = [truth(arg, valuation) for arg in node["args"]]
        return all(values) if node["op"] == "and" else any(values)
    raise ValueError("nonmodal state binding required")


def map_view(view, plan):
    if view["frontier"] or not view["worlds"]:
        return dict(status="UNRESOLVED_VIEW", states=(), world_bindings={})
    bindings = {}
    for world, valuation in zip(view["worlds"], view["values"]):
        selected = [b["state"] for b in plan["bindings"] if truth(b["when"], valuation)]
        if len(selected) != 1:
            return dict(status="AMBIGUOUS_STATE_MAPPING", states=(), world_bindings={})
        bindings[world] = selected[0]
    return dict(
        status="MAPPED",
        states=tuple(sorted(set(bindings.values()))),
        world_bindings=bindings,
    )


def derived_game(game, plan, views, state_q, allowance):
    """All strategic inputs are actual shared perspectives and computed Qs."""
    output, used = {}, 0
    for role in ("expected_listener", "actual_listener"):
        support = views[role]["mapping"]["states"]
        distribution = message_game(
            plan["graph"]["states"],
            game["messages"],
            game["prior"],
            beta=game["beta"],
            depth=game["depth"],
            available_states=support,
            max_work=max(0, allowance - used),
        )
        used += distribution["work"]
        predictions = {
            key: dict(
                posterior=p, actions=listener_actions(p, state_q, game["listener_beta"])
            )
            for key, p in distribution["listener"].items()
        }
        output[role] = dict(distribution=distribution, predictions=predictions)
    output["speaker"] = speaker_choices(
        views["speaker"]["mapping"]["states"],
        game["speaker_prior"],
        game["messages"],
        output["expected_listener"]["predictions"],
        goal=game["goal"],
        utilities=game["utilities"],
        beta=game["beta"],
        sincere=game["sincere"],
    )
    output["message_conditions"] = tuple(
        dict(
            message_id=m["id"],
            actual_literal_values=tuple(
                sorted(
                    {
                        state in m["meaning"]
                        for state in views["actual"]["mapping"]["states"]
                    }
                )
            ),
            speaker_literal_values=tuple(
                sorted(
                    {
                        state in m["meaning"]
                        for state in views["speaker"]["mapping"]["states"]
                    }
                )
            ),
            scope="LITERAL_TRUTH_AND_BELIEF_SEPARATE_NO_INTENT_VERDICT",
        )
        for m in game["messages"]
    )
    output["work"] = used
    return output


class InteractionModelOperator:
    def run(self, snapshot, issue, allowance, program):
        try:
            return self._run(snapshot, issue, allowance, thaw(program))
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            RecursionError,
            ZeroDivisionError,
            OverflowError,
        ):
            raise HCLFailure(
                "INVALID_REQUEST",
                "interaction",
                "INVALID_INTERACTION_MODEL",
                "model",
                "The conditional interaction is outside its executable finite model.",
            ) from None

    def _run(self, snapshot, issue, allowance, program):
        used, outputs, issues = 0, [], []
        limit = allowance.max_local_evaluations
        for model in program["models"]:
            original = model["mental"]
            augmented = deepcopy(original)
            events = {e["id"]: e for e in original["events"]}
            overrides = {}
            for message in model["utterances"]:
                for delivery in message["deliveries"]:
                    event = events[delivery["event_id"]]
                    overrides[(original["id"], event["id"])] = interpreted_event(
                        event,
                        delivery["readings"],
                        tuple(a["id"] for a in original["agents"]),
                    )
            for c in model["commitments"]:
                for at in relevant_times(model, c):
                    for field in ("condition", "outcome"):
                        augmented["queries"].append(
                            dict(
                                id=query_id(c, field, at),
                                at=at,
                                formula=c[field],
                                segment_ids=c["segment_ids"],
                            )
                        )
            trace = {}
            operation = MentalSceneOperator()._run(
                snapshot,
                issue,
                replace(allowance, max_local_evaluations=max(0, limit - used)),
                dict(models=[augmented]),
                event_overrides=overrides,
                trace=trace,
                trace_times={
                    original["id"]: tuple(
                        sorted(
                            {
                                *(g["at"] for g in model["games"]),
                                *(
                                    a["at"]
                                    for a in model["acts"]
                                    if a["at"] <= model["through"]
                                ),
                                *(
                                    events[d["event_id"]]["at"]
                                    for u in model["utterances"]
                                    for d in u["deliveries"]
                                    if events[d["event_id"]]["at"] <= model["through"]
                                ),
                            }
                        )
                    )
                },
            )
            used += operation.resource_usage["local_evaluations"]
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
                assumption_environments=actual.assumption_environments,
                domain_issues=operation.issues,
                shared_variables=[],
                commitments=[],
                games=[],
                acknowledgments={},
                frontier=[],
            )
            outputs.append(output)
            if mental["inactive_assumptions"] or original["id"] not in trace:
                output["frontier"].append("INTERACTION_MENTAL_STATE_UNAVAILABLE")
                issues.extend(output["frontier"])
                continue
            timeline, environments = trace[original["id"]]
            deliveries, interpretations = receipts(model, output["actual_mental"])
            for c in model["commitments"]:
                if used >= limit:
                    output["frontier"].append("COMMITMENT_BUDGET_FRONTIER")
                    break
                used += 1
                facts = commitment_facts(model, c, output["actual_mental"])
                offer = next(u for u in model["utterances"] if u["id"] == c["offer_id"])
                terms = dict(c, offered_at=offer["at"], offer_literal=offer["literal"])
                result = qualified_commitment_history(
                    terms,
                    facts,
                    model["acts"],
                    deliveries,
                    interpretations,
                    through=model["through"],
                )
                output["frontier"].extend(result["frontier"])
                output["commitments"].append(
                    dict(
                        commitment_id=c["id"],
                        terms=terms,
                        facts=facts,
                        assumption_status=(
                            "NOT_FULLY_COMPUTED"
                            if any(
                                f["assumption_status"] == "NOT_FULLY_COMPUTED"
                                for f in facts
                            )
                            else "BOUND_TO_QUERY_RESULTS"
                        ),
                        assumption_environments=sorted(
                            {
                                a
                                for fact in facts
                                for a in fact["assumption_environments"]
                            }
                        ),
                        **result,
                    )
                )
            if used < limit:
                used += 1
                output["acknowledgments"] = acknowledgment_chains(
                    model["utterances"],
                    model["acts"],
                    deliveries,
                    interpretations,
                    through=model["through"],
                    max_depth=model["max_ack_depth"],
                )
                output["frontier"].extend(
                    d["reason"]
                    for d in output["acknowledgments"]["diagnostics"]
                    if d["reason"].endswith("FRONTIER")
                )
            else:
                output["frontier"].append("ACKNOWLEDGMENT_BUDGET_FRONTIER")
            shared = {}
            for game in model["games"]:
                plan = next(p for p in original["plans"] if p["id"] == game["plan_id"])
                row = dict(
                    game_id=game["id"],
                    input=game,
                    plan=plan,
                    status="UNCOMPUTED",
                    views={},
                    state_q_results={},
                    computation={},
                )
                output["games"].append(row)
                cognitive = timeline.get(game["at"])
                if cognitive is None or used + 4 > limit:
                    output["frontier"].append("INTERACTION_VIEW_FRONTIER")
                    continue
                for role, path in (
                    ("actual", ()),
                    ("speaker", (game["speaker"],)),
                    ("expected_listener", (game["speaker"], game["listener"])),
                    ("actual_listener", (game["listener"],)),
                ):
                    used += 1
                    view = remaining_states(
                        cognitive, path, EpistemicLimits(max_depth=16)
                    )
                    identity = variable_id(
                        original, path[0] if len(path) == 1 else path, game["at"]
                    )
                    variable = dict(
                        variable_id=identity,
                        perspective_path=path,
                        at=game["at"],
                        view=view,
                        assumptions=environments[game["at"]],
                        history=cognitive.history,
                    )
                    if identity in shared and shared[identity] != variable:
                        raise ValueError(
                            "one interaction perspective has different computed states"
                        )
                    shared[identity] = variable
                    row["views"][role] = dict(
                        variable_id=identity, mapping=map_view(view, plan)
                    )
                row["assumption_environments"] = list(environments[game["at"]])
                if any(
                    v["mapping"]["status"] != "MAPPED" for v in row["views"].values()
                ):
                    output["frontier"].append("INTERACTION_STATE_MAPPING_FRONTIER")
                    continue
                states = sorted(
                    {s for v in row["views"].values() for s in v["mapping"]["states"]}
                )
                for state in states:
                    if used >= limit:
                        break
                    value = solve_action_values(
                        planning_model(plan["graph"]),
                        {state: "1"},
                        1,
                        max_expansions=max(1, limit - used),
                    )
                    used += value["expansions"]
                    row["state_q_results"][state] = value
                if set(row["state_q_results"]) != set(states) or any(
                    v["status"] != "SOLVED" for v in row["state_q_results"].values()
                ):
                    output["frontier"].append("INTERACTION_PLANNING_FRONTIER")
                    continue
                row["computation"] = derived_game(
                    game,
                    plan,
                    row["views"],
                    {s: v["q"] for s, v in row["state_q_results"].items()},
                    limit - used,
                )
                used += row["computation"]["work"]
                row["status"] = "COMPUTED"
                row["game_allowance"] = limit - used + row["computation"]["work"]
                for role in ("expected_listener", "actual_listener"):
                    output["frontier"].extend(
                        row["computation"][role]["distribution"]["frontier"]
                    )
                output["frontier"].extend(row["computation"]["speaker"]["frontier"])
            output["shared_variables"] = list(shared.values())
            issues.extend(output["frontier"])
        values = dict(
            operator_version=VERSION,
            models=outputs,
            semantic_certified=False,
            candidate_completeness="NOT_ESTABLISHED",
            local_evaluations=used,
            source_versions=dict(snapshot.source_versions),
            scope="FINITE_SOURCE_BOUND_INTERACTION_NOT_PRIVATE_INTENT_OR_MORAL_TRUTH",
        )
        inference = InferenceResult(
            "interaction-result:"
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
            "CONDITIONAL_FINITE_INTERACTION",
        )
        return OpResult(
            "interaction.execute",
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


def verify_interaction(values):
    data = thaw(values)
    if (
        data["semantic_certified"] is not False
        or data["candidate_completeness"] != "NOT_ESTABLISHED"
    ):
        raise ValueError("conditional interaction boundary missing")
    for model in data["models"]:
        inputs = model["inputs"]
        actual = model["actual_mental"]
        deliveries, interpretations = receipts(inputs, actual)
        if (
            actual["source_versions"] != data["source_versions"]
            or actual["values"]["source_versions"] != data["source_versions"]
        ):
            raise ValueError("interaction source dependency mismatch")
        if model["domain_issues"] != actual["issues"]:
            raise ValueError("interaction domain qualifications changed")
        if model["assumption_environments"] != actual["assumption_environments"]:
            raise ValueError(
                "interaction assumptions differ from actual domain computation"
            )
        for commitment in model["commitments"]:
            c = next(
                c
                for c in inputs["commitments"]
                if c["id"] == commitment["commitment_id"]
            )
            offer = next(u for u in inputs["utterances"] if u["id"] == c["offer_id"])
            terms = dict(c, offered_at=offer["at"], offer_literal=offer["literal"])
            if codec.canonical(terms) != codec.canonical(commitment["terms"]):
                raise ValueError("original commitment terms changed")
            expected_facts = commitment_facts(inputs, c, actual)
            if codec.canonical(expected_facts) != codec.canonical(commitment["facts"]):
                raise ValueError("commitment facts differ from actual M03 queries")
            if commitment["assumption_status"] != (
                "NOT_FULLY_COMPUTED"
                if any(
                    f["assumption_status"] == "NOT_FULLY_COMPUTED"
                    for f in expected_facts
                )
                else "BOUND_TO_QUERY_RESULTS"
            ):
                raise ValueError("commitment assumption qualification changed")
            if commitment["assumption_environments"] != sorted(
                {
                    a
                    for fact in commitment["facts"]
                    for a in fact["assumption_environments"]
                }
            ):
                raise ValueError("commitment assumptions changed")
            if tuple(f["at"] for f in commitment["facts"]) != relevant_times(inputs, c):
                raise ValueError("commitment time coverage mismatch")
            expected = qualified_commitment_history(
                terms,
                commitment["facts"],
                inputs["acts"],
                deliveries,
                interpretations,
                through=inputs["through"],
            )
            if any(
                codec.canonical(commitment[k]) != codec.canonical(v)
                for k, v in expected.items()
            ):
                raise ValueError("commitment lifecycle mismatch")
        if model["acknowledgments"]:
            expected = acknowledgment_chains(
                inputs["utterances"],
                inputs["acts"],
                deliveries,
                interpretations,
                through=inputs["through"],
                max_depth=inputs["max_ack_depth"],
            )
            if codec.canonical(expected) != codec.canonical(model["acknowledgments"]):
                raise ValueError(
                    "acknowledgment differs from actual historical receipt"
                )
        variables = {v["variable_id"]: v for v in model["shared_variables"]}
        for game in model["games"]:
            if game["status"] != "COMPUTED":
                if game["computation"]:
                    raise ValueError("uncomputed game contains predictions")
                continue
            source_game = next(g for g in inputs["games"] if g["id"] == game["game_id"])
            plan = next(
                p
                for p in inputs["mental"]["plans"]
                if p["id"] == source_game["plan_id"]
            )
            if source_game != game["input"] or plan != game["plan"]:
                raise ValueError("game model binding mismatch")
            paths = dict(
                actual=(),
                speaker=(source_game["speaker"],),
                expected_listener=(source_game["speaker"], source_game["listener"]),
                actual_listener=(source_game["listener"],),
            )
            for role, path in paths.items():
                ref = game["views"][role]
                variable = variables[ref["variable_id"]]
                expected_id = variable_id(
                    inputs["mental"],
                    path[0] if len(path) == 1 else path,
                    source_game["at"],
                )
                if (
                    variable["variable_id"] != expected_id
                    or tuple(variable["perspective_path"]) != path
                    or variable["at"] != source_game["at"]
                ):
                    raise ValueError("speaker/listener perspective changed")
                if codec.canonical(map_view(variable["view"], plan)) != codec.canonical(
                    ref["mapping"]
                ):
                    raise ValueError(
                        "strategy state mapping differs from actual M03 view"
                    )
            expected_assumptions = sorted(
                {
                    a
                    for ref in game["views"].values()
                    for a in variables[ref["variable_id"]]["assumptions"]
                }
            )
            if game["assumption_environments"] != expected_assumptions:
                raise ValueError("game assumptions differ from actual perspectives")
            state_q = {}
            for state, result in game["state_q_results"].items():
                if (
                    result["status"] != "SOLVED"
                    or result["belief"] != {state: "1"}
                    or result["horizon"] != 1
                ):
                    raise ValueError("actual M05 per-state computation missing")
                state_q[state] = result["q"]
            expected = derived_game(
                source_game, plan, game["views"], state_q, game["game_allowance"]
            )
            if codec.canonical(expected) != codec.canonical(game["computation"]):
                raise ValueError(
                    "interaction predictions differ from computed views and Q"
                )
