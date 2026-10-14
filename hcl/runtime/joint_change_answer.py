"""Full-replay delivery of finite joint-change certificates, never adoption."""
from hcl.kernel.execution import PROTOCOL
from hcl.kernel.types import AnswerClaim, HCLFailure, ResultField, thaw
from hcl.operators.joint_changes import verify_joint_changes
from hcl.semantics.judgment_concept_compiler import concept_judgment_qualifications


def joint_change_claim(result):
    try:
        expected = verify_joint_changes(result.values).candidate_delta.new_inferences[0]
        local = result.values.get("local_model")
        conditions = ()
        if local is not None:
            assumptions, residuals = concept_judgment_qualifications(result.values["program"])
            qualification = dict(model_id="judgment-proposal:" + result.values["program"]["candidate_identity"],
                version=PROTOCOL, dialect="judgment-model-4", domain_assumptions=list(assumptions),
                fit_residuals=[], unmodeled_observations=list(residuals))
            if thaw(local) != qualification:
                raise ValueError("joint-change local qualifications changed")
            conditions = tuple("local-model:" + local["model_id"] + ":assumption:" + str(i)
                               for i in range(len(local["domain_assumptions"])))
        elif result.result_id != expected.result_id:
            raise ValueError("pure joint result identity changed")
        if (result.kind != expected.kind or result.assumption_environments != (*expected.assumption_environments, *conditions)
                or result.premise_ids != expected.premise_ids or result.counterevidence_ids != expected.counterevidence_ids
                or result.rule_version != expected.rule_version or result.coverage != expected.coverage or result.diagnostics):
            raise ValueError("joint-change inference metadata changed")
    except (ValueError, KeyError, TypeError, IndexError, StopIteration, RecursionError, OverflowError, HCLFailure):
        raise HCLFailure("FAILED", "answer", "JOINT_CHANGE_RESULT_MISMATCH", "values",
            "The joint-change result differs from its source-bound finite language, actual targets or complete winning layer.") from None
    value = result.values
    search = value["joint_search"]
    declaration = value["program"]["joint_changes"]
    lines = ["Conditional finite joint-change analysis. One edit is one declared selector replacement or one scoped argument-activation retraction.",
        "Baseline target: " + repr(thaw(search["baseline"])) + "."]
    atoms = {a["atom_id"]: a["edit"] for a in declaration["atoms"]}
    if search["status"] == "FOUND_ALL_MINIMUM":
        lines.append("All minimum-cardinality witnesses within the declared finite language: " + str(search["minimum_cardinality"]) + " edits.")
    elif search["status"] == "NO_EXPRESSIBLE_CHANGE":
        lines.append("Every legal edit set in this declared finite language was checked; none changes the target semantics.")
    else:
        lines.append("Search is partial. No complete minimum or robust judgment is certified; retained witnesses are candidates only.")
    for witness in search["candidate_witnesses"]:
        lines.append("Joint changes " + repr(tuple(thaw(atoms[key]) for key in witness["atom_ids"]))
                     + " produce target " + repr(thaw(witness["target"])) + ".")
    lines.append("The calculation preserves source evidence, original pinned meanings and actual knowledge, feasibility and commitments. "
                 "These are hypothetical argument interventions, not changes to those facts, concept adoption or moral truth. "
                 "Mixed withdrawal proposals cannot be adopted through concept-only adoption.")
    if value["issues"]:
        lines.append("Unresolved: " + ", ".join(value["issues"]) + ".")
    names = ("joint_search", "evaluations", "complete", "source_versions", "issues", "local_evaluations", "semantic_certified", "scope")
    return AnswerClaim(" ".join(lines), "claim:" + result.result_id,
        tuple(ResultField(result.result_id, name, value[name]) for name in names),
        result.assumption_environments, result.counterevidence_ids, "CONDITIONAL_FINITE_JOINT_CHANGES_NOT_ADOPTION")
