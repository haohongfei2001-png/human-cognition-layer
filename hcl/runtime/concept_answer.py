"""Verified v2 concept/version/joint-decision delivery, independent of v1 text."""
from hcl.kernel.types import AnswerClaim, HCLFailure, ResultField, thaw
from hcl.kernel.execution import PROTOCOL
from hcl.operators.concept_judgment import verify_concept_judgment
from hcl.semantics.judgment_concept_compiler import concept_judgment_qualifications


def concept_judgment_claim(result):
    try:
        expected = verify_concept_judgment(result.values).candidate_delta.new_inferences[0]
        environments = set(expected.assumption_environments)
        local = result.values.get("local_model")
        if local is not None:
            assumptions, residuals = concept_judgment_qualifications(result.values["program"])
            qualifications = dict(model_id="judgment-proposal:" + result.values["program"]["candidate_identity"],
                version=PROTOCOL, dialect="judgment-model-3" if result.kind=="CONDITIONAL_CONCEPT_REPAIR_JUDGMENT" else "judgment-model-2", domain_assumptions=list(assumptions),
                fit_residuals=[], unmodeled_observations=list(residuals))
            if thaw(local) != qualifications:
                raise ValueError("conceptual model qualifications changed")
            environments.update("local-model:" + local["model_id"] + ":assumption:" + str(i)
                                for i in range(len(local["domain_assumptions"])))
        if result.kind != expected.kind:
            raise ValueError("concept result dialect kind changed")
        if (set(result.assumption_environments) != environments or result.premise_ids != expected.premise_ids
                or result.counterevidence_ids != expected.counterevidence_ids or result.rule_version != expected.rule_version
                or result.coverage != expected.coverage):
            raise ValueError("concept result premise/environment changed")
    except (ValueError, KeyError, TypeError, IndexError, StopIteration, RecursionError, OverflowError, HCLFailure):
        raise HCLFailure("FAILED", "answer", "CONCEPT_JUDGMENT_RESULT_MISMATCH", "values",
                         "The judgment differs from its actual concept definitions, original terms or joint calculations.") from None
    value = result.values
    lines = ["Conditional concept-sensitive judgment. Definition direction, examples and source interpretation remain explicit hypotheses."]
    for repair in value.get("repairs", ()):
        lines.append("Counterexample repair " + repair["id"] + ": " + repair["status"]
            + "; language=" + repair.get("language", "WITHDRAWN")
            + "; finite minimum-structure candidates=" + repr(tuple(repair.get("minimum_consistent_candidate_ids", ())))
            + "; Pareto proposals=" + repr(tuple(repair.get("pareto_candidate_ids", ())))
            + ". Proposals and comparison do not authorize adoption.")
    for definition in value["concepts"]["definitions"]:
        lines.append("Definition " + definition["id"] + "=" + definition["definition_version"] + "; purpose="
                     + definition["semantic_definition"]["purpose"] + ".")
    for branch in value["branches"]:
        lines.append("Joint version selection " + repr(thaw(branch["selections"])) + ".")
        for use in branch["classifications"].values():
            actual = use["actual"]
            lines.append("Case " + use["case_id"] + " at use " + use["use_id"] + " under " + use["version_label"]
                         + ": " + actual["status"] + "; support=" + repr(tuple(actual["support"]))
                         + "; exclusion=" + repr(tuple(actual["exclusion"])) + "; unresolved=" + repr(tuple(actual["uncertain"])) + ".")
            if use["commitment"]:
                lines.append("Original commitment " + use["commitment"]["id"] + " terms " + use["commitment"]["terms_version"]
                             + " retain pinned definition " + use["definition_version"] + " at " + str(use["at"]) + ".")
        for key, decision in branch["decision_projection"].items():
            lines.append("Decision " + key + ": " + decision["status"] + "; recommended=" + repr(tuple(decision["recommended"]))
                         + "; normative branches=" + repr(thaw(decision["norm_states"])) + ".")
    lines.append("Stable across every complete compatible declared version branch: " + repr(thaw(value["robust_recommended"]))
                 + "." if value["complete"] else "Version exploration is incomplete; no complete robust recommendation is certified.")
    for change in value["sensitivity"]:
        lines.append("Changing " + change["changed_choice"] + " changes classifications " + repr(tuple(change["changed_classifications"]))
                     + " and decisions " + repr(tuple(change["changed_decisions"])) + ".")
    lines.append("Reconsider if directional criteria, examples, case evidence or explicit version choices change. This is finite recomputation, not automatic global propagation, authenticated value adoption or moral truth.")
    if value["issues"]:
        lines.append("Unresolved: " + ", ".join(value["issues"]) + ".")
    names = ("concepts", "branches", "robust_recommended", "sensitivity", "complete", "source_versions", "issues", "local_evaluations", "semantic_certified", "scope")
    if "repairs" in value:
        names = (*names, "repairs")
    return AnswerClaim(" ".join(lines), "claim:" + result.result_id,
        tuple(ResultField(result.result_id, name, value[name]) for name in names),
        result.assumption_environments, result.counterevidence_ids, "CONDITIONAL_CONCEPT_SENSITIVE_NOT_MORAL_TRUTH")
