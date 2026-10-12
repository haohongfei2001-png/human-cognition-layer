"""Execute the shared discoverer using real mental/planning/causal/argument code."""

from copy import deepcopy
from dataclasses import replace
import json

from hcl.kernel.types import (
    Delta,
    HCLFailure,
    InferenceResult,
    Issue,
    OpResult,
    thaw,
    freeze,
)
from hcl.memory import codec
from hcl.operators.abduction import (
    VERSION,
    discover,
    evaluate_expression,
    identity,
    program_hash,
    context_identity,
    domain_conditions,
    edit_evaluation,
)
from hcl.operators.mental_scene import MentalSceneOperator
from hcl.operators.argument_model import ArgumentModelOperator
from hcl.semantics.model_compiler import LocalModelCompiler
from hcl.semantics.argument_compiler import ArgumentCompiler

KIND = "CONDITIONAL_MECHANISM_DISCOVERY"


def domain_limitations(records):
    """Keep solver caveats attached to their exact program/context/result.

    The issue list is not a claim of no limitations: material structured
    argument caveats remain visible even if an adapter drops its summary code.
    """
    result = []
    for record in records:
        codes = set(record.get("issues", ()))
        models = []
        for model in record.get("values", {}).get("models", ()):
            details = {
                name: model[name]
                for name in (
                    "model_id",
                    "acceptance_scope",
                    "theory_consistency",
                    "excluded_circular_rules",
                    "strict_conflicts",
                    "inactive_assumptions",
                    "frontier",
                )
                if name in model
            }
            codes.update(model.get("frontier", ()))
            if model.get("excluded_circular_rules"):
                codes.add("CYCLIC_PROOF_FRAGMENT_EXCLUDED")
            if (
                model.get("strict_conflicts")
                or model.get("theory_consistency") == "INCONSISTENT_STRICT_CORE"
            ):
                codes.add("INCONSISTENT_STRICT_CORE")
            models.append(details)
        if codes:
            result.append(
                dict(
                    result_id=record["result_id"],
                    program_hash=record["program_hash"],
                    context_hash=record["context_hash"],
                    kind=record["kind"],
                    issues=tuple(sorted(codes)),
                    scope=record["values"].get("scope"),
                    models=tuple(models),
                )
            )
    return tuple(result)


def qualify_domain_results(values):
    """A computed prediction can still be materially partial in its domain."""
    all_limitations = []
    for column in values["prediction_matrix"].values():
        column["domain_limitations"] = domain_limitations(column["actual_results"])
        all_limitations.extend(column["domain_limitations"])
    for probe in values["distinguishing_observations"]:
        probe["domain_limitations"] = {
            key: domain_limitations(value["actual_results"])
            for key, value in probe["evaluations"].items()
        }
        for limitations in probe["domain_limitations"].values():
            all_limitations.extend(limitations)
        for prediction in probe["predictions"].values():
            prediction["domain_limitations"] = domain_limitations(
                prediction["actual_results"]
            )
    values["domain_issues"] = tuple(
        sorted({code for row in all_limitations for code in row["issues"]})
    )
    return values


def delivery_values(values):
    """Qualify historical facts without modifying their immutable record.

    Shipped M04 records predate the scoped qualification fields. All fields must
    be absent for that historical shape; a partially stripped current record is
    invalid. The current verifier still checks every retained domain prediction.
    """
    containers = [values]
    containers.extend(values["prediction_matrix"].values())
    for probe in values["distinguishing_observations"]:
        containers.append(probe)
        containers.extend(probe["predictions"].values())
    present = ["domain_issues" in values] + [
        "domain_limitations" in row for row in containers[1:]
    ]
    if not any(present):
        return freeze(qualify_domain_results(thaw(values)))
    if not all(present):
        raise ValueError("incomplete domain qualification contract")
    return values


def instantiate(program, context):
    template = deepcopy(context["template"])
    model = template["models"][0]
    features, latent = context["features"], program["latent"]
    constraints = [
        evaluate_expression(expr, features, latent) for expr in program["constraint"]
    ]
    if any(type(value) is not bool for value in constraints):
        raise ValueError("Boolean mechanism constraints required")
    if not all(constraints):
        return None
    for binding in program["observe"]:
        event = next(row for row in model["events"] if row["id"] == binding["event_id"])
        members = set(event[binding["channel"]])
        when = evaluate_expression(binding["when"], features, latent)
        if type(when) is not bool:
            raise ValueError("Boolean observation condition required")
        if when:
            members.add(binding["actor"])
        else:
            members.discard(binding["actor"])
        event[binding["channel"]] = sorted(members)
    for binding in program["transition"]:
        target = binding["target"]
        value = evaluate_expression(binding["value"], features, latent)
        if target["kind"] in ("utility", "cost"):
            plan = next(row for row in model["plans"] if row["id"] == target["plan_id"])
            if type(value) not in (str, int):
                raise ValueError("rational mechanism value required")
            if target["kind"] == "utility":
                plan["graph"]["utilities"][target["state"]] = str(value)
            else:
                action = next(
                    a
                    for a in plan["graph"]["actions"]
                    if a["id"] == target["action_id"]
                )
                action["cost"] = str(value)
        else:
            if type(value) is not bool:
                raise ValueError("Boolean argument mechanism value required")
            if target["kind"] == "ordinary":
                row = next(
                    r for r in model["premises"] if r["id"] == target["premise_id"]
                )
                row["ordinary"] = value
            else:
                row = next(r for r in model["rules"] if r["id"] == target["rule_id"])
                row["strict"] = value
    return template


def extract_prediction(inference, selector):
    values = inference["values"]
    model = values["models"][0]
    field = selector["field"]
    group, name, identity_key = {
        "belief.possible_values": ("beliefs", "possible_values", "query_id"),
        "plan.best_actions": ("plans", "best_actions", "plan_id"),
        "causal.possible_values": ("causal", "possible_values", "query_id"),
        "argument.acceptance": ("queries", None, "query_id"),
    }[field]
    match = next(
        (
            (i, row)
            for i, row in enumerate(model[group])
            if row[identity_key] == selector["record_id"]
        ),
        None,
    )
    if match is None:
        return dict(status="UNMODELED", values=[], result_refs=[])
    index, row = match
    acceptable = {
        "belief.possible_values": {"DETERMINATE", "UNRESOLVED"},
        "plan.best_actions": {"SOLVED"},
        "causal.possible_values": {"DETERMINATE", "UNDERDETERMINED"},
        "argument.acceptance": {"COMPLETE"},
    }[field]
    # The SCM's own status taxonomy is retained. A finite nonempty result with
    # no frontier is usable except explicitly inconsistent/unsupported cases.
    if field == "causal.possible_values":
        complete = (
            bool(row["possible_values"])
            and not row.get("frontier")
            and row["status"] not in {"INCONSISTENT", "NO_COMPATIBLE_WORLDS"}
        )
    else:
        complete = row["status"] in acceptable and not row.get("frontier")
    if not complete:
        return dict(
            status="UNCOMPUTED", values=[], result_refs=[], diagnostic=row["status"]
        )
    if field == "argument.acceptance":
        predicted = [
            dict(positive=row["positive_accepted"], opposed=row["opposed_accepted"])
        ]
        selected = ("positive_accepted", "opposed_accepted")
    else:
        predicted = list(row[name])
        selected = (name,)
    return dict(
        status="COMPUTED",
        values=predicted,
        result_refs=[
            dict(
                result_id=inference["result_id"],
                path=("models", "0", group, str(index)),
                fields=selected,
                selector=dict(selector),
            )
        ],
    )


class DiscoveryModelOperator:
    def run(self, snapshot, issue, allowance, program, segments):
        data = thaw(program)

        def evaluate(hypothesis, context, remaining):
            try:
                template = instantiate(hypothesis, context)
                if template is None:
                    return dict(
                        status="UNMODELED",
                        predictions={},
                        work=0,
                        actual_results=[],
                        diagnostic="HYPOTHESIS_CONSTRAINT_INAPPLICABLE",
                    )
                mental = hypothesis["adapter"] == "mental-scene-1"
                compiler = LocalModelCompiler() if mental else ArgumentCompiler()
                typed = compiler.compile(
                    snapshot,
                    segments,
                    json.dumps(template, ensure_ascii=False),
                    allowance,
                )
            except HCLFailure as error:
                if error.status not in ("INVALID_REQUEST", "BUDGET_EXHAUSTED"):
                    raise
                return dict(
                    status=(
                        "UNMODELED"
                        if error.status == "INVALID_REQUEST"
                        else "UNCOMPUTED"
                    ),
                    predictions={},
                    work=0,
                    actual_results=[],
                    diagnostic=error.diagnostic.code,
                )
            except (ValueError, TypeError, KeyError, StopIteration, ZeroDivisionError):
                return dict(
                    status="UNMODELED",
                    predictions={},
                    work=0,
                    actual_results=[],
                    diagnostic="INADMISSIBLE_EDITED_MECHANISM",
                )
            operator = MentalSceneOperator() if mental else ArgumentModelOperator()
            operation = operator.run(
                snapshot,
                Issue(
                    "prediction:" + identity([hypothesis, context]),
                    "hypothesis.predict",
                ),
                replace(allowance, max_local_evaluations=remaining),
                typed,
            )
            inference = operation.candidate_delta.new_inferences[0]
            actual = dict(
                result_id=inference.result_id,
                kind=inference.kind,
                values=thaw(inference.values),
                source_versions=dict(operation.read_set),
                resource_usage=dict(operation.resource_usage),
                issues=operation.issues,
                program_hash=program_hash(hypothesis),
                context_hash=context_identity(context),
                assumption_environments=inference.assumption_environments,
            )
            predictions = {
                selector["id"]: extract_prediction(actual, selector)
                for selector in hypothesis["predict"]
            }
            return dict(
                status="COMPUTED",
                predictions=predictions,
                work=operation.resource_usage["local_evaluations"],
                actual_results=[actual],
            )

        values = discover(
            data["programs"],
            data["observations"],
            data["contexts"],
            data["probes"],
            data["grammar"],
            evaluate,
            max_evaluations=allowance.max_local_evaluations,
            **data["search"],
            scope=dict(
                source_versions=dict(snapshot.source_versions),
                rule_version=snapshot.rule_version,
                contexts=identity(data["contexts"]),
                observations=identity(data["observations"]),
            )
        )
        values.update(
            observations=data["observations"],
            context_bindings={c["id"]: context_identity(c) for c in data["contexts"]},
            probe_bindings={
                p["id"]: dict(
                    context_hash=context_identity(p["context"]), query_id=p["query_id"]
                )
                for p in data["probes"]
            },
            source_bindings=data["source_bindings"],
            unmodeled_segments=data["unmodeled_segments"],
            source_versions=dict(snapshot.source_versions),
            scope="CONDITIONAL_DECLARED_MECHANISM_PREDICTIONS_NOT_CAUSAL_OR_PRIVATE_TRUTH",
            factor_independence="NOT_ESTABLISHED",
            grammar=data["grammar"],
            search=data["search"],
        )
        qualify_domain_results(values)
        issues = [*values["frontier"], *values["domain_issues"]]
        if values["unmodeled_segments"]:
            issues.append("UNMODELED_DISCOVERY_SOURCE")
        if any(c["profile"]["unmodeled"] for c in values["prediction_matrix"].values()):
            issues.append("UNCOMPUTED_OR_UNMODELED_PREDICTION")
        inference = InferenceResult(
            "discovery-result:"
            + identity([issue.issue_id, dict(snapshot.source_versions), values]),
            KIND,
            values,
            tuple(
                sorted(
                    {
                        a
                        for col in values["prediction_matrix"].values()
                        for r in col["actual_results"]
                        for a in r["assumption_environments"]
                    }
                    | {
                        a
                        for probe in values["distinguishing_observations"]
                        for item in probe["evaluations"].values()
                        for r in item["actual_results"]
                        for a in r["assumption_environments"]
                    }
                )
            ),
            tuple(snapshot.source_versions),
            (),
            snapshot.rule_version,
            "CONDITIONAL_MECHANISM_DISCOVERY",
        )
        return OpResult(
            "abduction.execute",
            VERSION,
            snapshot.source_versions,
            ("append_inference",),
            (inference.result_id,),
            tuple(sorted(set(issues))),
            {"local_evaluations": values["local_evaluations"]},
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


def verify_discovery(values):
    """Recheck matrix claims against the retained actual domain solver fields."""
    from hcl.operators.abduction import (
        expression_size,
        compare_prediction,
        factor_profile,
        pareto_frontier,
        prediction_classes,
        program_hash,
    )

    data = thaw(values)
    if (
        data["semantic_certified"] is not False
        or data["candidate_completeness"] != "NOT_ESTABLISHED"
        or data["posterior"] != "NOT_CALIBRATED"
    ):
        raise ValueError("conditional discovery boundary missing")
    expected_qualifications = qualify_domain_results(deepcopy(data))
    if data["domain_issues"] != list(expected_qualifications["domain_issues"]):
        raise ValueError("domain issue summary mismatch")
    for key, column in data["prediction_matrix"].items():
        if codec.canonical(column["domain_limitations"]) != codec.canonical(
            expected_qualifications["prediction_matrix"][key]["domain_limitations"]
        ):
            raise ValueError("observed domain limitations mismatch")
    for index, probe in enumerate(data["distinguishing_observations"]):
        expected = expected_qualifications["distinguishing_observations"][index]
        if codec.canonical(probe["domain_limitations"]) != codec.canonical(
            expected["domain_limitations"]
        ):
            raise ValueError("probe evaluation limitations mismatch")
        for key, prediction in probe["predictions"].items():
            if codec.canonical(prediction["domain_limitations"]) != codec.canonical(
                expected["predictions"][key]["domain_limitations"]
            ):
                raise ValueError("probe prediction limitations mismatch")
    observations = data["observations"]
    programs, columns = data["programs"], data["prediction_matrix"]
    if set(programs) != set(columns) or not programs:
        raise ValueError("program matrix mismatch")

    def check_prediction(prediction, actual_results, selector, key, context_hash):
        if prediction["status"] != "COMPUTED":
            if prediction["values"] or prediction["result_refs"]:
                raise ValueError("unknown prediction contains asserted values")
            return
        if len(prediction["result_refs"]) != 1:
            raise ValueError("actual prediction reference required")
        ref = prediction["result_refs"][0]
        actual = next(
            (r for r in actual_results if r["result_id"] == ref["result_id"]), None
        )
        if (
            actual is None
            or actual["source_versions"] != data["source_versions"]
            or actual["program_hash"] != key
            or actual["context_hash"] != context_hash
        ):
            raise ValueError("prediction dependency mismatch")
        expected = extract_prediction(actual, selector)
        if codec.canonical(expected) != codec.canonical(prediction):
            raise ValueError("prediction differs from actual solver fields")

    for key, column in columns.items():
        if (
            key != program_hash(programs[key])
            or key != column["program_hash"]
            or len(column["cells"]) != len(observations)
        ):
            raise ValueError("mechanism identity mismatch")
        if column["complexity"] != expression_size(
            {k: v for k, v in programs[key].items() if k != "id"}
        ):
            raise ValueError("mechanism complexity mismatch")
        if column["work"] != sum(
            r["resource_usage"]["local_evaluations"] for r in column["actual_results"]
        ):
            raise ValueError("domain work mismatch")
        conditions = [
            dict(
                result_id=r["result_id"],
                context_hash=r["context_hash"],
                assumption_environments=r["assumption_environments"],
            )
            for r in column["actual_results"]
        ]
        if codec.canonical(conditions) != codec.canonical(column["domain_conditions"]):
            raise ValueError("prediction condition mismatch")
        selectors = {p["id"]: p for p in programs[key]["predict"]}
        for observation, cell in zip(observations, column["cells"]):
            if any(
                cell[k] != observation[v]
                for k, v in (
                    ("observation_id", "id"),
                    ("context_id", "context_id"),
                    ("factor_id", "factor_id"),
                    ("provenance_group", "provenance_group"),
                )
            ):
                raise ValueError("observation matrix mismatch")
            check_prediction(
                cell["prediction"],
                column["actual_results"],
                selectors[observation["query_id"]],
                key,
                data["context_bindings"][observation["context_id"]],
            )
            if cell["relation"] != compare_prediction(cell["prediction"], observation):
                raise ValueError("prediction relation mismatch")
        if codec.canonical(column["profile"]) != codec.canonical(
            factor_profile(column["cells"])
        ):
            raise ValueError("evidence factor mismatch")
    if tuple(data["pareto_programs"]) != pareto_frontier(columns):
        raise ValueError("Pareto result mismatch")
    if codec.canonical(data["prediction_classes"]) != codec.canonical(
        prediction_classes(columns, observations, data["equivalence_scope"])
    ):
        raise ValueError("prediction equivalence mismatch")
    from itertools import combinations

    expected_members = tuple(
        sorted(
            {
                member
                for group in data["prediction_classes"]
                if set(group["members"]) & set(data["pareto_programs"])
                for member in group["members"]
            }
        )
    )
    for probe in data["distinguishing_observations"]:
        if (
            probe["hypothetical"] is not True
            or probe["information_gain"] != "NOT_CALIBRATED"
        ):
            raise ValueError("hypothetical uncalibrated probe boundary missing")
        binding = data["probe_bindings"][probe["probe_id"]]
        if (
            probe["query_id"] != binding["query_id"]
            or tuple(probe["tested_members"]) != expected_members
        ):
            raise ValueError("probe obligation mismatch")
        if set(probe["predictions"]) & set(probe["incomplete"]) or set(
            probe["predictions"]
        ) | set(probe["incomplete"]) != set(expected_members):
            raise ValueError("probe member coverage mismatch")
        groups = {}
        for key, value in probe["predictions"].items():
            selector = next(
                p for p in programs[key]["predict"] if p["id"] == binding["query_id"]
            )
            if codec.canonical(value["domain_conditions"]) != codec.canonical(
                domain_conditions(value["actual_results"])
            ):
                raise ValueError("probe conditions mismatch")
            check_prediction(
                value["prediction"],
                value["actual_results"],
                selector,
                key,
                binding["context_hash"],
            )
            signature = codec.canonical(
                sorted(codec.canonical(v) for v in value["prediction"]["values"])
            )
            groups.setdefault(signature, []).append(key)
        partitions = tuple(
            tuple(sorted(members)) for _, members in sorted(groups.items())
        )
        if codec.canonical(partitions) != codec.canonical(probe["partitions"]) or probe[
            "separated_pairs"
        ] != sum(len(a) * len(b) for a, b in combinations(partitions, 2)):
            raise ValueError("probe separation mismatch")

    total = sum(c["work"] for c in columns.values())
    for probe in data["distinguishing_observations"]:
        if set(probe["evaluations"]) != set(probe["tested_members"]):
            raise ValueError("probe audit mismatch")
        for evaluated in probe["evaluations"].values():
            if evaluated["work"] != sum(
                r["resource_usage"]["local_evaluations"]
                for r in evaluated["actual_results"]
            ):
                raise ValueError("probe work mismatch")
            total += evaluated["work"]
    if total != data["local_evaluations"]:
        raise ValueError("discovery work mismatch")
    if tuple(data["evidence_factor_ids"]) != tuple(
        sorted({o["factor_id"] for o in observations})
    ):
        raise ValueError("factor registration mismatch")

    initial = set(data["initial_program_hashes"])
    if not initial or not initial <= set(programs):
        raise ValueError("initial mechanism identity mismatch")
    creation_round = {key: 0 for key in initial}
    seen_children = set()
    last_round = 0
    for edit in data["edit_history"]:
        parent_key, child_key = edit["parent_hash"], edit["child_hash"]
        if (
            parent_key not in programs
            or child_key not in programs
            or child_key in seen_children
            or parent_key == child_key
            or child_key in initial
            or parent_key not in creation_round
        ):
            raise ValueError("invalid mechanism lineage")
        seen_children.add(child_key)
        if (
            type(edit["round"]) is not int
            or not 1 <= edit["round"] <= data["search"]["max_rounds"]
        ):
            raise ValueError("invalid mechanism edit round")
        if edit["round"] < last_round or creation_round[parent_key] >= edit["round"]:
            raise ValueError("invalid mechanism chronology")
        last_round = creation_round[child_key] = edit["round"]
        residuals = tuple(
            sorted(
                c["observation_id"]
                for c in columns[parent_key]["cells"]
                if c["relation"] != "EXPLAINED"
            )
        )
        if not residuals or tuple(edit["residual_ids"]) != residuals:
            raise ValueError("edit is not rooted in actual residuals")
        proposed = deepcopy(programs[parent_key])
        path, after = edit["path"], edit["after"]
        if len(path) == 3 and path[0] == "observe" and path[2] == "when":
            index = int(path[1])
            old = proposed["observe"][index]["when"]
            if (
                index < 0
                or expression_size(after) > data["grammar"]["max_expression_size"]
            ):
                raise ValueError("invalid channel edit bound")
            allowed = []
            for feature in data["grammar"]["observation_features"]:
                term = {"feature": feature}
                allowed.extend(
                    [
                        ("replace_channel", term),
                        ("extend_channel", {"op": "or", "args": [old, term]}),
                        ("restrict_channel", {"op": "and", "args": [old, term]}),
                    ]
                )
            allowed.append(("negate_channel", {"op": "not", "args": [old]}))
            if not any(
                operation == edit["operation"]
                and codec.canonical(value) == codec.canonical(after)
                for operation, value in allowed
            ):
                raise ValueError("unregistered channel edit")
            proposed["observe"][index]["when"] = after
        elif (
            len(path) == 2
            and path[0] == "latent"
            and edit["operation"] == "replace_latent"
        ):
            old = proposed["latent"][path[1]]
            if not any(
                codec.canonical(choice) == codec.canonical(after)
                for choice in data["grammar"]["latent_domains"][path[1]]
            ):
                raise ValueError("undeclared parameter edit")
            proposed["latent"][path[1]] = after
        else:
            raise ValueError("unregistered edit path")
        if (
            codec.canonical(old) != codec.canonical(edit["before"])
            or program_hash(proposed) != child_key
        ):
            raise ValueError("edit differs from actual child mechanism")
        if edit["evaluation_status"] != edit_evaluation(columns[child_key]):
            raise ValueError("edit recomputation status mismatch")

    if seen_children != set(programs) - initial:
        raise ValueError("missing mechanism edit lineage")
