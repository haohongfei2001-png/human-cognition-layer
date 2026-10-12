"""Shared cognition -> directed relationship/role models -> longitudinal predictions."""

from copy import deepcopy
from dataclasses import replace
from fractions import Fraction
from hashlib import sha256
from itertools import product
from hcl.kernel.types import Delta, HCLFailure, InferenceResult, OpResult, thaw
from hcl.operators.commitment_qualification import commitment_condition
from hcl.memory import codec
from hcl.operators.agency import encoded, rational, solve_action_values
from hcl.operators.epistemic import query_belief, EpistemicLimits
from hcl.operators.interaction_model import InteractionModelOperator
from hcl.operators.affect_model import AffectModelOperator, weights_for
from hcl.operators.shared_cognition import compute_shared_cognition, cognitive_record
from hcl.operators.relationships import (
    relationship_history,
    role_reconciliation,
    longitudinal_search,
)
from hcl.semantics.model_compiler import planning_model

VERSION = "s3-conditional-longitudinal-1"
KIND = "CONDITIONAL_RELATIONSHIP_MODEL"


def mechanism_identity(mechanism):
    # Only presentation fields are omitted; goal/hypothesis dictionary keys are
    # semantic identifiers even when literally named "id" or "label".
    semantic = {
        k: v for k, v in mechanism.items() if k not in ("id", "label", "segment_ids")
    }
    semantic["relationship_effects"] = sorted(
        (
            {k: v for k, v in effect.items() if k != "segment_ids"}
            for effect in mechanism["relationship_effects"]
        ),
        key=lambda e: e["relationship_id"],
    )
    return "mechanism:" + sha256(codec.canonical(semantic).encode()).hexdigest()


def actual_record(operation):
    result = operation.candidate_delta.new_inferences[0]
    return dict(
        result_id=result.result_id,
        kind=result.kind,
        values=thaw(result.values),
        assumption_environments=result.assumption_environments,
        source_versions=dict(operation.read_set),
        issues=operation.issues,
    )


def factor_identity(source, actor, at, refs):
    return (
        "factor:"
        + sha256(
            codec.canonical([source, actor, at, sorted(set(refs))]).encode()
        ).hexdigest()
    )


class RelationshipModelOperator:
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
                "relationships",
                "INVALID_RELATIONSHIP_MODEL",
                "model",
                "The conditional longitudinal model is outside its executable finite contract.",
            ) from None

    def _run(self, snapshot, issue, allowance, program):
        used = 0
        outputs = []
        issues = []
        limit = allowance.max_local_evaluations

        def remaining():
            return replace(allowance, max_local_evaluations=max(0, limit - used))

        for model in program["models"]:
            mental = model["mental"]
            episodes = {e["id"]: e for e in model["affect"]["episodes"]}
            interaction = dict(model["interaction"], mental=mental)
            affect = dict(model["affect"], mental=mental)
            times = {
                t
                for episode in episodes.values()
                for t in (episode["before"], episode["at"])
            }
            times.update(u["at"] for r in model["relationships"] for u in r["updates"])
            bundle = compute_shared_cognition(
                snapshot, issue, remaining(), interaction, tuple(sorted(times))
            )
            used += bundle.operation.resource_usage["local_evaluations"]
            shared = {(mental["source_id"], mental["id"]): bundle}
            op07 = InteractionModelOperator()._run(
                snapshot,
                issue,
                remaining(),
                dict(models=[interaction]),
                shared_cognition=shared,
            )
            used += op07.resource_usage["local_evaluations"]
            op08 = AffectModelOperator()._run(
                snapshot,
                issue,
                remaining(),
                dict(models=[affect]),
                shared_cognition=shared,
            )
            used += op08.resource_usage["local_evaluations"]
            record07, record08 = actual_record(op07), actual_record(op08)
            issues.extend((*bundle.operation.issues, *op07.issues, *op08.issues))
            out = dict(
                model_id=mental["id"],
                source_id=mental["source_id"],
                inputs=model,
                cognition=cognitive_record(bundle),
                actual_interaction=record07,
                actual_affect=record08,
                relationships=[],
                roles=[],
                identity_narratives=model["identities"],
                prediction_matrix={},
                forecasts={},
                mechanisms=[],
                longitudinal={},
                frontier=[],
            )
            outputs.append(out)
            timeline, environments = bundle.trace.get(mental["id"], ({}, {}))
            computed_events = {
                e["event_id"]: e
                for e in bundle.operation.candidate_delta.new_inferences[0].values[
                    "models"
                ][0]["events"]
            }
            source_events = {e["id"]: e for e in mental["events"]}
            commitments = {
                c["commitment_id"]: c
                for c in record07["values"]["models"][0]["commitments"]
            }
            derived = {
                e["episode_id"]: e for e in record08["values"]["models"][0]["episodes"]
            }

            def condition(at, actor, formula):
                nonlocal used
                cognitive = timeline.get(at)
                if cognitive is None or used >= limit:
                    return dict(
                        status="FRONTIER_UNEXPLORED",
                        possible_values=[False, True],
                        assumptions=(),
                        frontier=["RELATIONSHIP_CONDITION_FRONTIER"],
                    )
                used += 1
                value = query_belief(
                    cognitive,
                    dict(op="believes", agent=actor, arg=formula),
                    EpistemicLimits(max_depth=16),
                )
                return dict(value, assumptions=environments[at])

            for relation in model["relationships"]:
                factors = []
                for update in relation["updates"]:
                    event = source_events[update["event_id"]]
                    receipt = computed_events.get(event["id"])
                    before_condition = used
                    check = condition(
                        update["at"], relation["observer"], update["condition"]
                    )
                    condition_work = used - before_condition
                    event_known = (
                        receipt is not None
                        and receipt["computation"]["status"] == "APPLIED"
                    )
                    received = relation["observer"] in (
                        event["seen_by"]
                        if event["kind"] == "change"
                        else set(event["received_by"]) & set(event["understood_by"])
                    )
                    qualification = "UNRESOLVED"
                    if event_known and not received:
                        qualification = "INAPPLICABLE"
                    elif event_known and check["status"] != "FRONTIER_UNEXPLORED":
                        if tuple(check["possible_values"]) == (True,):
                            qualification = "ESTABLISHED_IN_CONDITIONAL_MODEL"
                        elif tuple(check["possible_values"]) == (False,):
                            qualification = "INAPPLICABLE"
                    dependency = None
                    qualification_proof = None
                    if update["commitment_id"] is not None:
                        commit = commitments.get(update["commitment_id"])
                        historical = (
                            []
                            if commit is None
                            else [
                                r for r in commit["history"] if r["at"] <= update["at"]
                            ]
                        )
                        dependency = None if not historical else historical[-1]
                        # The existing metered condition unit also checks the
                        # finite lifecycle prefix. Uncertain Boolean completions
                        # consume additional shared units. No second M03 is run.
                        proof = commitment_condition(
                            dict(
                                commitment_id=update["commitment_id"],
                                at=update["at"],
                                status=update["commitment_status"],
                            ),
                            record07["values"]["models"][0],
                            record07["result_id"],
                            max(0, limit - used) + condition_work,
                        )
                        used += max(0, proof["work"] - condition_work)
                        if proof["possible_values"] == (False,):
                            qualification = "INAPPLICABLE"
                        elif (
                            proof["possible_values"] != (True,)
                            and qualification != "INAPPLICABLE"
                        ):
                            qualification = "UNRESOLVED"
                        # Preserve known legacy factor shapes/usage. The original
                        # exact interaction history already witnesses definite
                        # states; newly uncertain/expanded histories additionally
                        # carry the full current qualification and its limits.
                        if proof["frontier"] or proof["explored_completions"] > 1:
                            qualification_proof = {
                                key: value
                                for key, value in proof.items()
                                if key
                                not in ("history", "original_terms", "evidence_events")
                            }
                            qualification_proof["bookkeeping_prefix_status"] = (
                                None
                                if proof["history"] is None
                                else proof["history"]["status"]
                            )
                            qualification_proof["history_reference"] = dict(
                                result_id=record07["result_id"],
                                commitment_id=update["commitment_id"],
                                through=update["at"],
                                source="actual_interaction.values.models[0].commitments",
                            )
                    # Display aliases cannot manufacture additional independent evidence.
                    fid = factor_identity(
                        mental["source_id"],
                        relation["observer"],
                        event["at"],
                        update["segment_ids"],
                    )
                    factors.append(
                        dict(
                            update_id=update["id"],
                            at=update["at"],
                            factor_id=fid,
                            likelihoods=update["likelihoods"],
                            qualification=qualification,
                            event_id=event["id"],
                            event_applied=event_known,
                            event_received=received,
                            condition=check,
                            commitment=dependency,
                            cognitive_result_id=out["cognition"]["actual"]["result_id"],
                            interaction_result_id=record07["result_id"],
                            assumption_environments=environments.get(update["at"], ()),
                        )
                    )
                    if qualification_proof is not None:
                        factors[-1]["commitment_qualification"] = qualification_proof
                history = relationship_history(
                    {h["id"]: h for h in relation["hypotheses"]},
                    relation["prior"],
                    factors,
                    max_work=max(0, limit - used),
                )
                used += history["work"]
                out["relationships"].append(
                    dict(
                        relationship_id=relation["id"],
                        observer=relation["observer"],
                        target=relation["target"],
                        domain=relation["domain"],
                        dimension=relation["dimension"],
                        source_model=relation,
                        **history
                    )
                )
                out["frontier"].extend(history["frontier"])
            relation_results = {r["relationship_id"]: r for r in out["relationships"]}
            contexts = (*model["observations"], *model["forecasts"])
            role_results = {}
            for context in contexts:
                episode = episodes[context["episode_id"]]
                actual = derived.get(episode["id"])
                plan = next(p for p in mental["plans"] if p["id"] == episode["plan_id"])
                support = (
                    ()
                    if actual is None or "current" not in actual["views"]
                    else actual["views"]["current"]["mapping"]["states"]
                )
                opportunities = tuple(
                    a["id"]
                    for a in plan["graph"]["actions"]
                    if support
                    and set(support) <= set(a["enabled"]) & set(a["feasible"])
                )
                requirements = []
                checks = []
                for role in model["roles"]:
                    if (
                        role["actor"] != episode["actor"]
                        or episode["id"] not in role["episode_actions"]
                        or not role["from_time"]
                        <= episode["at"]
                        <= role["through_time"]
                    ):
                        continue
                    check = condition(
                        episode["at"], episode["actor"], role["condition"]
                    )
                    checks.append(dict(role_id=role["id"], condition=check))
                    requirements.append(
                        dict(
                            id=role["id"],
                            condition_values=check["possible_values"],
                            actions=role["episode_actions"][episode["id"]],
                        )
                    )
                if actual is None or actual["status"] != "COMPUTED" or not support:
                    computed = dict(
                        branches=(),
                        work=0,
                        frontier=("ROLE_OPPORTUNITY_UNRESOLVED",),
                        status="UNCOMPUTED",
                        scope="CONDITIONAL_ROLE_REQUIREMENTS_NOT_IDENTITY_OR_MORAL_VERDICT",
                    )
                else:
                    computed = role_reconciliation(
                        requirements, opportunities, max_work=max(0, limit - used)
                    )
                used += computed["work"]
                role_row = dict(
                    context_id=context["id"],
                    episode_id=episode["id"],
                    at=episode["at"],
                    actor=episode["actor"],
                    requirements=requirements,
                    condition_results=checks,
                    subjective_opportunities=opportunities,
                    actual_view=(
                        None if actual is None else actual["views"].get("actual")
                    ),
                    cognitive_result_id=out["cognition"]["actual"]["result_id"],
                    **computed
                )
                out["roles"].append(role_row)
                role_results[context["id"]] = role_row
                out["frontier"].extend(computed["frontier"])
            unique = {}
            aliases = {}
            for mechanism in model["mechanisms"]:
                key = mechanism_identity(mechanism)
                unique.setdefault(key, mechanism)
                aliases.setdefault(key, []).append(mechanism["id"])
            for key, mechanism in sorted(unique.items()):
                complexity = (
                    1
                    + sum(
                        rational(v) != 1 for v in mechanism["goal_multipliers"].values()
                    )
                    + int(mechanism["respect_roles"])
                    + int(mechanism["coping_id"] is not None)
                    + sum(
                        len(e["multipliers"]) for e in mechanism["relationship_effects"]
                    )
                )
                out["mechanisms"].append(
                    dict(
                        mechanism_id=key,
                        source_aliases=aliases[key],
                        input=mechanism,
                        complexity=complexity,
                        complexity_scope="DECLARED_AST_STRUCTURE_NOT_PSYCHOLOGICAL_PRIOR",
                    )
                )
                predictions = []
                future = []
                for context in contexts:
                    episode = episodes[context["episode_id"]]
                    actual = derived.get(episode["id"])
                    role = role_results[context["id"]]
                    row = dict(
                        context_id=context["id"],
                        episode_id=episode["id"],
                        at=episode["at"],
                        status="UNCOMPUTED",
                        values=[],
                        branches=[],
                        relation_conditions=[],
                        frontier=[],
                        source_variable_ids=(),
                        affect_result_id=record08["result_id"],
                        cognitive_result_id=out["cognition"]["actual"]["result_id"],
                        assumption_environments=environments.get(episode["at"], ()),
                        hypothetical=context in model["forecasts"],
                    )
                    (
                        predictions if context in model["observations"] else future
                    ).append(row)
                    if actual is None or actual["status"] != "COMPUTED":
                        row["frontier"].append("LONGITUDINAL_AFFECT_UNAVAILABLE")
                        continue
                    row["source_variable_ids"] = [
                        v["variable_id"] for v in actual["views"].values()
                    ]
                    if mechanism["coping_id"] is None:
                        bases = [
                            dict(
                                priorities=mechanism["priorities"],
                                action_ids=None,
                                observation_overrides={},
                                horizon=None,
                                coping_id=None,
                                adjustment_history=(),
                            )
                        ]
                    else:
                        coping = next(
                            c
                            for c in actual["derived"]["coping"]
                            if c["coping_id"] == mechanism["coping_id"]
                        )
                        bases = [
                            dict(
                                priorities=b["input"]["priorities"],
                                action_ids=coping["input"]["action_ids"],
                                observation_overrides=coping["input"][
                                    "observation_overrides"
                                ],
                                horizon=coping["input"]["horizon"],
                                coping_id=coping["coping_id"],
                                adjustment_history=b["input"]["adjustment_history"],
                            )
                            for b in coping["branches"]
                            if b["input"]["status"] == "COMPUTED"
                        ]
                    goal_ids = tuple(g["id"] for g in episode["goals"])
                    adjustments = [
                        {
                            g: rational(mechanism["goal_multipliers"][g])
                            for g in goal_ids
                        }
                    ]
                    for effect in mechanism["relationship_effects"]:
                        relation = relation_results[effect["relationship_id"]]
                        history = [
                            r for r in relation["history"] if r["at"] <= episode["at"]
                        ]
                        current = (
                            history[-1]
                            if history
                            else dict(
                                weights=relation["source_model"]["prior"],
                                compatible_hypotheses=[
                                    h["id"]
                                    for h in relation["source_model"]["hypotheses"]
                                ],
                                unresolved_factor_ids=[],
                                conflicting_factor_ids=[],
                            )
                        )
                        row["relation_conditions"].append(
                            dict(
                                relationship_id=relation["relationship_id"],
                                at=episode["at"],
                                state=current,
                                scope="EXPECTED_PRIORITY_MULTIPLIER_MODEL_NOT_JOINT_POSTERIOR",
                            )
                        )
                        if (
                            current.get("unresolved_factor_ids")
                            or current.get("conflicting_factor_ids")
                            or len(history)
                            < len(
                                [
                                    u
                                    for u in relation["source_model"]["updates"]
                                    if u["at"] <= episode["at"]
                                ]
                            )
                        ):
                            row["frontier"].append("RELATIONSHIP_DEPENDENCY_UNRESOLVED")
                            break
                        if current["weights"] is None:
                            possibilities = [
                                {
                                    g: rational(effect["multipliers"][h][g])
                                    for g in goal_ids
                                }
                                for h in current["compatible_hypotheses"]
                            ]
                        else:
                            possibilities = [
                                {
                                    g: sum(
                                        Fraction(w)
                                        * rational(effect["multipliers"][h][g])
                                        for h, w in current["weights"].items()
                                    )
                                    for g in goal_ids
                                }
                            ]
                        adjustments = [
                            {g: a[g] * b[g] for g in goal_ids}
                            for a, b in product(adjustments, possibilities)
                        ]
                        if len(adjustments) > 32:
                            row["frontier"].append(
                                "RELATIONSHIP_PREDICTION_BRANCH_FRONTIER"
                            )
                            break
                    if row["frontier"]:
                        continue
                    allowed = (
                        [role["subjective_opportunities"]]
                        if not mechanism["respect_roles"]
                        else [
                            b["feasible_reconciliation_actions"]
                            for b in role["branches"]
                        ]
                    )
                    if mechanism["respect_roles"] and role["frontier"]:
                        row["frontier"].extend(role["frontier"])
                        continue
                    plan = actual["plan"]
                    weights = weights_for(
                        actual["views"]["current"]["mapping"]["states"],
                        episode["current_weights"],
                    )
                    if weights is None:
                        row["frontier"].append(
                            "LONGITUDINAL_BELIEF_WEIGHTS_UNSPECIFIED"
                        )
                        continue
                    if len(bases) * len(adjustments) * len(allowed) > 64:
                        row["frontier"].append(
                            "LONGITUDINAL_PREDICTION_BRANCH_FRONTIER"
                        )
                        continue
                    for base, adjustment, actions in product(
                        bases, adjustments, allowed
                    ):
                        if base["action_ids"] is not None:
                            actions = tuple(
                                a for a in actions if a in base["action_ids"]
                            )
                        scores = {
                            g: Fraction(base["priorities"][g]) * adjustment[g]
                            for g in goal_ids
                        }
                        total = sum(scores.values())
                        if not total:
                            row["frontier"].append("LONGITUDINAL_ZERO_PRIORITY")
                            continue
                        priorities = {g: v / total for g, v in scores.items()}
                        utilities = {
                            s: encoded(
                                sum(
                                    priorities[g["id"]] * rational(g["utilities"][s])
                                    for g in episode["goals"]
                                )
                            )
                            for s in plan["graph"]["states"]
                        }
                        if not actions:
                            row["branches"].append(
                                dict(
                                    priorities={
                                        g: encoded(v) for g, v in priorities.items()
                                    },
                                    actions=[],
                                    coping_basis=base,
                                    status="NO_FEASIBLE_ACTION",
                                    computation={},
                                    values=[None],
                                )
                            )
                            continue
                        graph = deepcopy(plan["graph"])
                        graph["utilities"] = utilities
                        if base["horizon"] is not None:
                            graph["horizon"] = base["horizon"]
                        graph["actions"] = [
                            a for a in graph["actions"] if a["id"] in actions
                        ]
                        for action in graph["actions"]:
                            action["enabled"] = list(action["feasible"])
                            if action["id"] in base["observation_overrides"]:
                                action["observations"] = base["observation_overrides"][
                                    action["id"]
                                ]
                        if used >= limit:
                            row["frontier"].append("LONGITUDINAL_PLANNING_FRONTIER")
                            break
                        try:
                            typed = planning_model(graph)
                        except ValueError:
                            row["frontier"].append(
                                "LONGITUDINAL_DERIVED_NUMERIC_FRONTIER"
                            )
                            break
                        value = solve_action_values(
                            typed,
                            weights,
                            graph["horizon"],
                            max_expansions=max(1, limit - used),
                        )
                        used += value["expansions"]
                        row["frontier"].extend(value["frontier"])
                        row["branches"].append(
                            dict(
                                priorities={
                                    g: encoded(v) for g, v in priorities.items()
                                },
                                actions=actions,
                                coping_basis=base,
                                status=value["status"],
                                computation=value,
                                values=value["best_actions"],
                            )
                        )
                    if not row["frontier"] and row["branches"]:
                        row["status"] = "COMPUTED"
                        row["values"] = sorted(
                            {a for b in row["branches"] for a in b["values"]},
                            key=codec.canonical,
                        )
                for prediction in (*predictions, *future):
                    if (
                        prediction["status"] != "COMPUTED"
                        and not prediction["frontier"]
                    ):
                        prediction["frontier"].append(
                            "LONGITUDINAL_PREDICTION_UNAVAILABLE"
                        )
                out["prediction_matrix"][key] = predictions
                out["forecasts"][key] = future
                out["frontier"].extend(
                    f for r in (*predictions, *future) for f in r["frontier"]
                )
            observations = [
                dict(
                    id=c["id"],
                    at=episodes[c["episode_id"]]["at"],
                    context_id=c["context_id"],
                    factor_id=factor_identity(
                        mental["source_id"],
                        episodes[c["episode_id"]]["actor"],
                        episodes[c["episode_id"]]["at"],
                        c["segment_ids"],
                    ),
                    values=[c["action"]],
                )
                for c in model["observations"]
            ]
            out["observations"] = observations
            out["longitudinal"] = longitudinal_search(
                out["prediction_matrix"],
                observations,
                {m["mechanism_id"]: m for m in out["mechanisms"]},
                max_segments=model["search"]["max_segments"],
                max_work=max(0, limit - used),
                max_states=model["search"]["max_candidates"],
            )
            used += out["longitudinal"]["work"]
            out["preferred_forecasts"] = [
                dict(
                    trajectory_id=t["trajectory_id"],
                    last_mechanism_id=t["path"][-1],
                    change_points=t["change_points"],
                    global_comparison=out["longitudinal"]["global_comparison"],
                    hypothetical=True,
                    predictions=[
                        dict(
                            context_id=r["context_id"],
                            status=r["status"],
                            values=r["values"],
                            frontier=r["frontier"],
                            actual_prediction_ref=dict(
                                mechanism_id=t["path"][-1], forecast_index=i
                            ),
                        )
                        for i, r in enumerate(out["forecasts"][t["path"][-1]])
                    ],
                )
                for t in out["longitudinal"]["trajectories"]
                if t["trajectory_id"] in out["longitudinal"]["pareto_explored"]
            ]
            out["frontier"].extend(out["longitudinal"]["frontier"])
            out["frontier"] = sorted(set(out["frontier"]))
            issues.extend(out["frontier"])
        values = dict(
            operator_version=VERSION,
            models=outputs,
            source_versions=dict(snapshot.source_versions),
            rule_version=snapshot.rule_version,
            issue_id=issue.issue_id,
            execution_allowance=limit,
            local_evaluations=used,
            semantic_certified=False,
            candidate_completeness="NOT_ESTABLISHED",
            scope="SOURCE_BOUND_LONGITUDINAL_HYPOTHESES_NOT_PRIVATE_TRUST_IDENTITY_OR_STABLE_VALUES",
        )
        inference = InferenceResult(
            "relationship-result:"
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
                    | {
                        "relationship-model:"
                        + m["mental"]["source_id"]
                        + ":"
                        + m["mental"]["id"]
                        + ":"
                        + r["id"]
                        + ":conditional-independence"
                        for m in program["models"]
                        for r in m["relationships"]
                    }
                )
            ),
            tuple(snapshot.source_versions),
            (),
            snapshot.rule_version,
            "CONDITIONAL_FINITE_LONGITUDINAL_MODEL",
        )
        return OpResult(
            "relationships.execute",
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


def verify_relationships(values):
    """Recompute the finite certificate without reading sources or committing state."""
    from types import SimpleNamespace
    from hcl.kernel.types import Principal, Issue
    from hcl.kernel.execution import ExecutionBudget

    data = thaw(values)
    data.pop("local_model", None)
    snapshot = SimpleNamespace(
        session_id="pure-certificate",
        principal=Principal("pure", "certificate"),
        revision=0,
        access_epoch=0,
        rule_version=data["rule_version"],
        source_versions=data["source_versions"],
    )
    expected = RelationshipModelOperator()._run(
        snapshot,
        Issue(data["issue_id"], "relationship.evaluate"),
        replace(ExecutionBudget(), max_local_evaluations=data["execution_allowance"]),
        dict(models=[m["inputs"] for m in data["models"]]),
    )
    if codec.canonical(
        thaw(expected.candidate_delta.new_inferences[0].values)
    ) != codec.canonical(data):
        raise ValueError(
            "longitudinal claims differ from their actual shared computations"
        )
    return expected
