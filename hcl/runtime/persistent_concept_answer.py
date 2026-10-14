"""Mechanical delivery of actual finite persistent concept revision results."""
from hcl.kernel.types import AnswerClaim, HCLFailure, ResultField, thaw
from hcl.semantics.concept_version_compiler import digest


def adoption_claim(result):
    value = result.values
    if (result.result_id != "concept-adoption:"+value["stream_token"]+":"+digest(thaw(value))
            or result.assumption_environments or result.premise_ids or result.counterevidence_ids
            or result.coverage != "EXPLICIT_HOST_ADOPTION_NOT_GLOBAL_TRUTH"):
        raise HCLFailure("FAILED","answer","CONCEPT_ADOPTION_MISMATCH","values","The recorded adoption contract changed.")
    text = "Recorded the explicit concept adoption " + value["definition_version"] + "."
    return AnswerClaim(text,"claim:"+result.result_id,
        tuple(ResultField(result.result_id,key,value[key]) for key in ("definition_version","effective_at","expected_head")),
        (),(),"EXPLICIT_ADOPTION_NOT_SEMANTIC_TRUTH")


def persistent_claim(result):
    from hcl.operators.persistent_concepts import verify_persistent_inference
    try:
        verify_persistent_inference(result)
    except (ValueError,KeyError,TypeError,IndexError,StopIteration,RecursionError,OverflowError,HCLFailure):
        raise HCLFailure("FAILED","answer","PERSISTENT_CONCEPT_RESULT_MISMATCH","values",
                         "The successor differs from its immutable evidence and actual local computations.") from None
    value = result.values
    lines = ["Conditional persistent concept revision. Original source interpretations and commitments remain fixed."]
    for branch in value["branches"]:
        for use in branch["classifications"].values():
            lines.append("Case "+use["case_id"]+" at "+use["use_id"]+": "+use["actual"]["status"]+".")
        for key,decision in branch["decision_projection"].items():
            lines.append("Decision "+key+": recommended="+repr(tuple(decision["recommended"]))+"; normative branches="+repr(thaw(decision["norm_states"]))+".")
    lines.append("Stable across the complete selected branches: "+repr(thaw(value["robust_recommended"]))+"."
                 if value["complete"] else "Local computation is incomplete; no complete robust recommendation is certified.")
    lines.append("This is bounded same-session adoption propagation; open semantic alignment and full M12/M13/M14 remain unproved.")
    fields = ("branches","concepts","robust_recommended","complete","issues","source_versions","local_evaluations")
    return AnswerClaim(" ".join(lines),"claim:"+result.result_id,
        tuple(ResultField(result.result_id,k,value[k]) for k in fields),result.assumption_environments,
        result.counterevidence_ids,"CONDITIONAL_PERSISTENT_REVISION_NOT_MORAL_TRUTH")
