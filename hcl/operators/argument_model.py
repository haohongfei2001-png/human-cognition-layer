"""Execute source-bound arguments and consume their actual defeat semantics."""

from dataclasses import asdict
from hashlib import sha256

from hcl.kernel.types import Delta, HCLFailure, InferenceResult, OpResult
from hcl.memory import codec
from hcl.operators.argumentation import (
    ACCEPTANCE_SCOPE,
    evaluate_arguments,
    claim_acceptance,
    preferred_extensions,
    critical_retractions,
)
from hcl.semantics.argument_compiler import argument_theory, argument_source_segments

VERSION = "s4-structured-arguments-1"
KIND = "CONDITIONAL_ARGUMENT_ACCEPTANCE"


class ArgumentModelOperator:
    def run(self, snapshot, issue, allowance, program, *, meter_work=False):
        used, batches = 0, 0
        issues = []
        models = []

        def batch():
            nonlocal used, batches
            if used >= allowance.max_local_evaluations:
                issues.append("ARGUMENT_BATCH_FRONTIER")
                return False
            used += 1
            batches += 1
            return True

        for proposal in program["models"]:
            model = dict(
                model_id=proposal["id"],
                source_id=proposal["source_id"],
                namespace_source_id=proposal["source_id"],
                input_source_versions=proposal["input_source_versions"],
                source_bindings=proposal["source_bindings"],
                source_records={
                    key: proposal[key]
                    for key in (
                        "literals",
                        "premises",
                        "rules",
                        "priorities",
                        "queries",
                    )
                },
                acceptance_scope=ACCEPTANCE_SCOPE,
                excluded_circular_rules=[],
                iterations=[],
                frame_kind=proposal["frame_kind"],
                assumptions=proposal["assumptions"],
                inactive_assumptions=sorted(
                    set(proposal["assumptions"]) - set(proposal["active_assumptions"])
                ),
                unmodeled_segments=proposal["unmodeled_segments"],
                arguments=[],
                attacks=[],
                defeats=[],
                labels={},
                grounded=[],
                strict_conflicts=[],
                theory_consistency="NOT_COMPUTED",
                queries=[],
                frontier=[],
            )
            models.append(model)
            if model["inactive_assumptions"]:
                issues.append("ARGUMENT_MODEL_ASSUMPTION_RETRACTED")
                continue
            if not batch():
                model["frontier"].append("ARGUMENT_BATCH_FRONTIER")
                continue
            theory, literals = argument_theory(proposal)
            computed = evaluate_arguments(theory, max_arguments=256,
                max_work=min(100000, allowance.max_local_evaluations - used + 1) if meter_work else 100000)
            if meter_work:
                used += computed["work"] - 1
            model.update(
                arguments=[
                    dict(
                        argument_id=a.argument_id,
                        conclusion=asdict(a.conclusion),
                        top=a.top,
                        top_kind=a.top_kind,
                        children=a.children,
                        subarguments=sorted(a.subarguments),
                        ancestry_literals=[
                            asdict(v) for v in sorted(a.ancestry_literals)
                        ],
                        premises=sorted(a.premises),
                        rules=sorted(a.rules),
                        bases=sorted(a.bases),
                        assumptions=sorted(a.assumptions),
                        source_segment_ids=argument_source_segments(
                            model["source_records"], a.premises, a.rules
                        ),
                    )
                    for a in computed["arguments"].values()
                ],
                attacks=computed["attacks"],
                defeats=computed["defeats"],
                labels=computed["labels"],
                grounded=computed["grounded"],
                frontier=list(computed["frontier"]),
                strict_conflicts=computed.get("strict_conflicts", ()),
                theory_consistency=computed.get("theory_consistency", "NOT_COMPUTED"),
                excluded_circular_rules=computed.get("excluded_circular_rules", ()),
                iterations=computed["iterations"],
                work=computed["work"],
            )
            if computed.get("excluded_circular_rules"):
                issues.append("CYCLIC_PROOF_FRAGMENT_EXCLUDED")
            if computed.get("strict_conflicts"):
                issues.append("INCONSISTENT_STRICT_CORE")
            for query in proposal["queries"]:
                literal = literals[query["literal"]]
                result = dict(
                    query_id=query["id"],
                    literal=asdict(literal),
                    status=computed["status"],
                    positive_accepted=None,
                    opposed_accepted=None,
                    accepted_arguments=[],
                    opposed_arguments=[],
                    preferred=None,
                    critical=None,
                )
                model["queries"].append(result)
                if computed["frontier"]:
                    continue
                positive, opposed = claim_acceptance(computed, literal)
                result.update(
                    positive_accepted=positive,
                    opposed_accepted=opposed,
                    accepted_arguments=sorted(
                        key
                        for key, arg in computed["arguments"].items()
                        if arg.conclusion == literal
                        and computed["labels"].get(key) == "IN"
                    ),
                    opposed_arguments=sorted(
                        key
                        for key, arg in computed["arguments"].items()
                        if literal.contrary(arg.conclusion)
                        and computed["labels"].get(key) == "IN"
                    ),
                )
                if query["preferred"]:
                    if len(computed["arguments"]) > 24:
                        result["preferred"] = dict(
                            status="FRONTIER_UNEXPLORED",
                            preferred=(),
                            frontier=("PREFERRED_ARGUMENT_BOUND",),
                        )
                    elif batch():
                        result["preferred"] = preferred_extensions(
                            computed["arguments"], computed["defeats"],
                            max_work=min(100000, allowance.max_local_evaluations - used + 1) if meter_work else 100000
                        )
                    else:
                        result["preferred"] = dict(
                            status="FRONTIER_UNEXPLORED",
                            preferred=(),
                            frontier=("ARGUMENT_BATCH_FRONTIER",),
                        )
                    if meter_work and "work" in result["preferred"]:
                        used += result["preferred"]["work"] - 1
                    model["frontier"].extend(result["preferred"]["frontier"])
                if query["critical_candidates"]:
                    if batch():
                        result["critical"] = critical_retractions(
                            theory,
                            literal,
                            query["critical_candidates"],
                            max_work=min(100000, allowance.max_local_evaluations - used + 1) if meter_work else 100000,
                        )
                    else:
                        result["critical"] = dict(
                            status="FRONTIER_UNEXPLORED",
                            edits=(),
                            minimum_cardinality=None,
                        )
                    if meter_work and "work" in result["critical"]:
                        used += result["critical"]["work"] - 1
                    if result["critical"]["status"] == "FRONTIER_UNEXPLORED":
                        model["frontier"].append("CRITICAL_EDIT_FRONTIER")
            issues.extend(model["frontier"])
            if proposal["unmodeled_segments"]:
                issues.append("UNMODELED_ARGUMENT_SOURCE")
        values = dict(
            operator_version=VERSION,
            models=models,
            batch_evaluations=batches if meter_work else used,
            semantic_certified=False,
            candidate_completeness="NOT_ESTABLISHED",
            source_versions=dict(snapshot.source_versions),
            scope="DECLARED_ARGUMENT_THEORY_ACCEPTANCE_NOT_PREMISE_OR_PHILOSOPHICAL_TRUTH",
        )
        if meter_work:
            values.update(operator_version="s4-structured-arguments-metered-2", accounting="ACTUAL_SOLVER_WORK_UNITS", local_evaluations=used)
        inference = InferenceResult(
            "argument-result:"
            + sha256(
                codec.dumps([issue.issue_id, snapshot.source_versions, program, values])
            ).hexdigest(),
            KIND,
            values,
            tuple(
                sorted({a for m in program["models"] for a in m["active_assumptions"]})
            ),
            tuple(snapshot.source_versions),
            (),
            snapshot.rule_version,
            "CONDITIONAL_ARGUMENT_MODEL",
        )
        return OpResult(
            "argument_model.execute",
            values["operator_version"],
            snapshot.source_versions,
            ("append_inference",),
            (inference.result_id,),
            tuple(sorted(set(issues))),
            {"local_evaluations": used},
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
