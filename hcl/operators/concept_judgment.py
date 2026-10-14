"""Joint semantic version interventions with actual M13 and M14 recomputation."""
from copy import deepcopy
from dataclasses import replace
from itertools import combinations
from types import SimpleNamespace

from hcl.kernel.types import Delta, HCLFailure, InferenceResult, OpResult, Issue, Principal, thaw
from hcl.kernel.execution import ExecutionBudget
from hcl.memory import codec
from hcl.operators.concept_versions import compute_versions
from hcl.operators.judgment import JudgmentWork
from hcl.semantics.concept_version_compiler import digest
from hcl.semantics.judgment_concept_compiler import verify_concept_program

VERSION = "s4-concept-sensitive-judgment-2"
KIND = "CONDITIONAL_CONCEPT_JUDGMENT"
REPAIR_KIND = "CONDITIONAL_CONCEPT_REPAIR_JUDGMENT"
REPAIR_VERSION = "s4-counterexample-concept-judgment-3"


def bind_classifications(model, group, classifications, out, argument, actual07, work):
    """Bind one consistent branch after actual M03/M05/M07, before real M13.

    All aliases/polarities of a conceptual atom move together. Rule-applicability
    atoms remain rule identities. Ordinary unbound atoms retain their identities.
    """
    premises = {p["id"]: p for p in argument["premises"]}
    literals = {l["id"]: l for l in argument["literals"]}
    atoms, bindings = {}, []
    for binding in group:
        work.spend()
        use = classifications[binding["use_id"]]
        key = "concept:" + binding["use_id"]
        if key in {f["id"] for f in model["facts"]}:
            raise ValueError("computed conceptual fact identity collision")
        classification = deepcopy(use)
        pin = use["commitment"]
        if pin is not None:
            actual = next((c for c in actual07["values"]["models"][0]["commitments"] if c["commitment_id"] == pin["id"]), None)
            classification["original_commitment"] = actual
            classification["commitment_result_id"] = actual07["result_id"]
            if actual is None:
                classification["actual"] = dict(classification["actual"], status="ORIGINAL_COMMITMENT_UNCOMPUTED", possible_values=[False, True])
            elif actual["terms"]["version"] != pin["terms_version"] or actual["terms"]["offered_at"] != use["at"]:
                raise ValueError("computed commitment pin differs from original terms")
        result_id = "concept-classification:" + digest([classification, out["source_versions"]])
        out["facts"][key] = dict(fact_id=key, kind="CONCEPT_CLASSIFICATION", role="CONCEPT", actual=classification,
            possible_values=classification["actual"]["possible_values"], status=classification["actual"]["status"],
            result_id=result_id, reference=dict(use_id=use["use_id"], definition_version=use["definition_version"]),
            scope="CONDITIONAL_DIRECTIONAL_DEFINITION_NOT_WORLD_TRUTH")
        literal = literals[premises[binding["premise_id"]]["literal"]]
        old = (literal["kind"], literal["atom"])
        generated = "concept-atom:" + digest([old, use["concept_id"], use["definition_version"], use["case_id"]])
        if any(l["atom"] == generated for l in literals.values()):
            raise ValueError("conceptual atom collides with source proposal")
        if atoms.setdefault(old, generated) != generated:
            raise ValueError("concept literal aliases disagree")
        bindings.append(dict(premise_id=binding["premise_id"], fact_id=key, expected=binding["expected"], segment_ids=binding["segment_ids"]))
    for literal in argument["literals"]:
        old = (literal["kind"], literal["atom"])
        if old in atoms:
            literal["atom"] = atoms[old]
    return bindings


def decision_key(source, model, decision):
    return "decision:" + digest([source, model, decision])


def decision_projection(actual):
    return {decision_key(m["source_id"], m["model_id"], d["decision_id"]):
            dict(source_id=m["source_id"], model_id=m["model_id"], decision_id=d["decision_id"], status=d["status"], recommended=d["robust_across_frameworks"],
                 norm_states=[[b["states"] for b in f["branches"]] for f in d["frameworks"]],
                 permission=[[b["result"]["eligibility"] for b in f["branches"]] for f in d["frameworks"]],
                 responsibility=d["responsibility"])
            for m in actual["models"] for d in m["decisions"]}


def classification_semantics(value):
    actual = value["actual"]
    return dict(status=actual["status"], possible_values=actual["possible_values"])


def decision_semantics(value):
    """Separate changed judgments from versioned proof/evidence identities."""
    # Preferred extensions are sets. Their proof-derived enumeration order can
    # change under a meaning intervention even when every joint judgment agrees.
    # Preserve the state/permission pairing: separate marginal sorts would hide
    # genuine changes in which permissions belong to which norm extension.
    frameworks = [sorted({codec.canonical([states, permission])
        for states, permission in zip(norms, permissions, strict=True)})
        for norms, permissions in zip(value["norm_states"], value["permission"], strict=True)]
    return dict(status=value["status"], recommended=value["recommended"],
        joint_framework_branches=frameworks,
        responsibility=[dict(query_id=r["query_id"], status=r["status"],
            unresolved_facts=r["unresolved_facts"],
            positive_accepted=None if r["actual"] is None else r["actual"]["positive_accepted"],
            opposed_accepted=None if r["actual"] is None else r["actual"]["opposed_accepted"])
            for r in value["responsibility"]])


class ConceptJudgmentOperator:
    def run(self, snapshot, issue, allowance, program):
        try:
            return self._run(snapshot, issue, allowance, thaw(program))
        except (ValueError, TypeError, KeyError, IndexError, RecursionError, StopIteration):
            raise HCLFailure("INVALID_REQUEST", "judgment", "INVALID_CONCEPT_JUDGMENT", "concepts",
                             "The conceptual judgment violates its bound joint-version contract.") from None

    def _run(self, snapshot, issue, allowance, program):
        from hcl.operators.judgment_model import JudgmentModelOperator
        repair = program.get("schema") == "hcl-judgment-candidates-3"
        expansion = None
        if repair:
            from hcl.semantics.concept_repair_compiler import verify_repair_program
            verify_repair_program(program, snapshot, allowance)
        else:
            verify_concept_program(program, snapshot, allowance)
        work = JudgmentWork(allowance.max_local_evaluations)
        if repair:
            from hcl.operators.concept_repairs import expand_repairs
            expansion = expand_repairs(program, work.limit)
            work.spend(expansion["work"])
        concepts = compute_versions(program["concepts"] if expansion is None else expansion["concepts"], work.limit-work.used)
        work.spend(concepts["local_evaluations"])
        branches, issues, environments = [], list(concepts["frontier"]), set(concepts["assumption_environments"])
        if expansion is not None:
            issues.extend(expansion["frontier"])
        shared_upstream = {}
        try:
            for branch in concepts["branches"]:
                if not branch["complete"]:
                    continue
                work.spend()
                op = JudgmentModelOperator()._run(snapshot, issue, replace(allowance, max_local_evaluations=work.limit - work.used),
                    program["base_program"], concept_context=dict(bindings=program["concept_bindings"],
                                                                 classifications=branch["classifications"], shared_upstream=shared_upstream))
                work.spend(op.resource_usage["local_evaluations"])
                inference = op.candidate_delta.new_inferences[0]
                actual = thaw(inference.values)
                complete = (not any(m["frontier"] or not m["decisions"] or m["actual_argument"] is None
                                    or any(a["frontier"] for a in m["actual_argument"]["values"]["models"])
                                    or any(d["status"] != "COMPUTED" for d in m["decisions"])
                                    for m in actual["models"]))
                branches.append(dict(branch_id=branch["branch_id"], selections=branch["selections"],
                    classifications=branch["classifications"], actual_judgment=actual, result_id=inference.result_id,
                    complete=complete, decision_projection=decision_projection(actual)))
                environments.update(inference.assumption_environments)
                issues.extend(op.issues)
                if not complete:
                    issues.append("CONCEPT_JUDGMENT_BRANCH_INCOMPLETE")
        except OverflowError:
            issues.append("CONCEPT_JUDGMENT_WORK_FRONTIER")
        complete = (expansion is None or not expansion["frontier"]) and bool(branches) and concepts["complete"] and len(branches) == len(concepts["branches"]) and all(b["complete"] for b in branches)
        robust, sensitivity = {}, []
        try:
            if complete:
                keys = set(branches[0]["decision_projection"])
                if any(set(b["decision_projection"]) != keys for b in branches):
                    raise ValueError("joint decision identity changed")
                for key in sorted(keys):
                    work.spend(len(branches))
                    robust[key] = sorted(set.intersection(*(set(b["decision_projection"][key]["recommended"]) for b in branches)))
                for left, right in combinations(branches, 2):
                    work.spend(len(keys) + len(left["classifications"]) + len(left["selections"]))
                    changed = [c for c in left["selections"] if left["selections"][c] != right["selections"][c]]
                    if len(changed) != 1:
                        continue
                    sensitivity.append(dict(before=left["branch_id"], after=right["branch_id"], changed_choice=changed[0],
                        changed_classifications=[k for k in left["classifications"]
                            if classification_semantics(left["classifications"][k]) != classification_semantics(right["classifications"][k])],
                        changed_decisions=[k for k in sorted(keys) if decision_semantics(left["decision_projection"][k]) != decision_semantics(right["decision_projection"][k])],
                        changed_recommendations=[k for k in sorted(keys) if left["decision_projection"][k]["recommended"] != right["decision_projection"][k]["recommended"]],
                        classification_trace_changes=[k for k in left["classifications"] if left["classifications"][k] != right["classifications"][k]],
                        decision_trace_changes=[k for k in sorted(keys) if left["decision_projection"][k] != right["decision_projection"][k]],
                        scope="ACTUAL_SINGLE_VERSION_REPLACEMENT_NOT_MINIMAL_EDIT_PROOF"))
        except OverflowError:
            complete = False
            robust = {}
            issues.append("CONCEPT_SENSITIVITY_WORK_FRONTIER")
        if not complete:
            issues.append("CONCEPT_JUDGMENT_INCOMPLETE_VERSION_FRONTIER")
        if program["concepts"]["unmodeled_segments"]:
            issues.append("UNMODELED_CONCEPT_SOURCE")
        values = dict(operator_version=REPAIR_VERSION if repair else VERSION, issue_id=issue.issue_id, rule_version=snapshot.rule_version,
            source_versions=dict(snapshot.source_versions), program=program, concepts=concepts, branches=branches,
            complete=complete, robust_recommended=robust, sensitivity=sensitivity, local_evaluations=work.used,
            execution_allowance=work.limit, issues=sorted(set(issues)), semantic_certified=False,
            scope="FINITE_DECLARED_JOINT_VERSION_SENSITIVITY_NOT_GLOBAL_PROPAGATION")
        if expansion is not None:
            values.update(repairs=expansion["repairs"], generated_concepts=expansion["concepts"],
                scope="FINITE_COUNTEREXAMPLE_PARTITION_REPAIR_NOT_ADOPTION_OR_GLOBAL_OPTIMALITY")
        result = InferenceResult("concept-judgment:" + digest([issue.issue_id, values]), REPAIR_KIND if repair else KIND, values,
            tuple(sorted(environments)), tuple(sorted(snapshot.source_versions)), tuple(concepts["counterevidence_ids"]),
            snapshot.rule_version, "CONDITIONAL_CONCEPT_SENSITIVE_JUDGMENT")
        return OpResult("judgment.concept_versions", REPAIR_VERSION if repair else VERSION, snapshot.source_versions, ("append_inference",),
            (result.result_id,), tuple(sorted(set(issues))), dict(local_evaluations=work.used), (),
            Delta(snapshot.session_id, snapshot.principal, snapshot.revision, snapshot.access_epoch,
                  snapshot.rule_version, snapshot.source_versions, (result,)))


def verify_concept_judgment(values):
    data = thaw(values)
    data.pop("local_model", None)
    host = data["program"]["host_context"]
    if type(data["execution_allowance"]) is not int or not 0 <= data["execution_allowance"] <= 10000000:
        raise ValueError("bounded conceptual certificate required")
    snapshot = SimpleNamespace(session_id=host["session_id"], principal=Principal(**host["principal"]),
        revision=0, access_epoch=0, rule_version=data["rule_version"], source_versions=data["source_versions"])
    expected = ConceptJudgmentOperator()._run(snapshot, Issue(data["issue_id"], "judgment.evaluate"),
        replace(ExecutionBudget(), max_local_evaluations=data["execution_allowance"]), data["program"])
    if codec.canonical(thaw(expected.candidate_delta.new_inferences[0].values)) != codec.canonical(data):
        raise ValueError("conceptual judgment differs from actual joint computation")
    return expected
