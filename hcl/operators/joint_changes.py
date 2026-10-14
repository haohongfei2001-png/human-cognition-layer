"""Exhaustive finite joint changes, through the existing M12/M13/M14 runner.

Layers are cardinalities of declared selector replacements and scoped argument
activation retractions. Every smaller layer and the entire first winning layer
must finish before *all* minimum witnesses are certified. No adoption is implied.
"""
from copy import deepcopy
from dataclasses import replace
from itertools import combinations
from math import comb
from types import SimpleNamespace

from hcl.kernel.execution import ExecutionBudget
from hcl.kernel.types import Delta, HCLFailure, InferenceResult, Issue, OpResult, Principal, thaw
from hcl.memory import codec
from hcl.operators.concept_judgment import decision_key, decision_projection, decision_semantics
from hcl.operators.concept_versions import compute_versions
from hcl.operators.judgment import JudgmentWork
from hcl.semantics.concept_version_compiler import digest
from hcl.semantics.joint_change_compiler import node_count, verify_joint_program

KIND = "CONDITIONAL_JOINT_CHANGE_JUDGMENT"
VERSION = "s4-finite-joint-change-judgment-4"
COVERAGE = "CONDITIONAL_FINITE_JOINT_CHANGES_NOT_ADOPTION"
MAX_CERTIFICATE_BYTES = 4 * 1024 * 1024


def deactivate_arguments(argument, bindings, retractions, work):
    """Keep original rows/facts; deactivate only their hypothetical proof use.

    A second, filtered view is used ONLY for unknown-dependency reachability:
    a deliberately absent premise/rule cannot transmit unknown evidence. The
    actual argument certificate retains every row, with explicit inactive guards.
    """
    selected = {"premises": set(), "rules": set()}
    proof = []
    for atom in retractions:
        work.spend()
        row = atom["edit"]
        category = "premises" if row["kind"] == "PREMISE_RETRACT" else "rules"
        item = next(v for v in argument[category] if v["id"] == row["item_id"])
        guard = "joint-retraction:" + digest([atom["atom_id"], row])
        if guard in argument["active_assumptions"] or any(guard in r["assumptions"] for k in selected for r in argument[k]):
            raise ValueError("joint activation guard collides with original assumptions")
        item["assumptions"].append(guard)
        selected[category].add(row["item_id"])
        proof.append(dict(atom_id=atom["atom_id"], kind=row["kind"], item_id=row["item_id"], inactive_guard=guard,
                          scope="HYPOTHETICAL_ARGUMENT_ACTIVATION_ONLY_NOT_FACT_OR_COMMITMENT_RETRACTION"))
    gap = dict(argument, **{k: [v for v in argument[k] if v["id"] not in ids] for k, ids in selected.items()})
    return gap, [b for b in bindings if b["premise_id"] not in selected["premises"]], proof


def target_projection(actual, target):
    """Only cognitive semantics; proof IDs, argument enumeration and labels are not targets."""
    missing = dict(kind=target["kind"], resolved=False, semantics=None)
    model = next((m for m in actual["models"] if (m["source_id"], m["model_id"]) ==
                  (target["source_id"], target["model_id"])), None)
    if model is None or model["actual_argument"] is None:
        return missing
    theory = model["actual_argument"]["values"]["models"][0]
    computed = not (model["frontier"] or theory["frontier"] or theory["strict_conflicts"] or theory["inactive_assumptions"])
    if target["kind"] == "M13_ACCEPTANCE":
        query = next((q for q in theory["queries"] if q["query_id"] == target["query_id"]), None)
        if query is None:
            return missing
        literal = query["literal"]
        def sign(conclusion):
            if all(conclusion[k] == literal[k] for k in ("atom", "scope", "kind")):
                return 1 if conclusion["negative"] == literal["negative"] else -1
            return 0
        signs = {a["argument_id"]: sign(a["conclusion"]) for a in theory["arguments"]}
        preferred = query["preferred"]
        variants = None if preferred is None else sorted({
            (any(signs[k] == 1 for k in extension), any(signs[k] == -1 for k in extension))
            for extension in preferred.get("preferred", ())})
        resolved = (computed and target["query_id"] not in model["argument_dependency_gaps"]
                    and preferred is not None and not preferred["frontier"])
        return dict(kind=target["kind"], resolved=resolved, semantics=dict(
            positive_supported=any(s == 1 for s in signs.values()), opposed_supported=any(s == -1 for s in signs.values()),
            positive_accepted=query["positive_accepted"], opposed_accepted=query["opposed_accepted"],
            preferred_acceptance=None if variants is None else [list(v) for v in variants]))
    decision = next((d for d in model["decisions"] if d["decision_id"] == target["decision_id"]), None)
    if decision is None:
        return missing
    source_model = next(m for m in actual["program"]["models"]
                        if (m["mental"]["source_id"], m["mental"]["id"]) == (target["source_id"], target["model_id"]))
    source_decision = next(d for d in source_model["decisions"] if d["id"] == target["decision_id"])
    queries = {n["argument_query_id"] for f in source_decision["frameworks"] for n in f["norms"]}
    queries.update(q["query_id"] for q in source_decision["responsibility_queries"])
    guards = {k for f in source_decision["frameworks"] for n in f["norms"] for k in n["guard_fact_ids"]}
    resolved = (computed and decision["status"] == "COMPUTED" and not decision["frontier"]
                and not queries.intersection(model["argument_dependency_gaps"])
                and all(len(model["facts"][k]["possible_values"]) == 1 for k in guards))
    key = decision_key(target["source_id"], target["model_id"], target["decision_id"])
    return dict(kind=target["kind"], resolved=resolved, semantics=decision_semantics(decision_projection(actual)[key]))


def apply_atoms(program, selected, work):
    declaration = program["joint_changes"]
    selection = dict(declaration["baseline"])
    replacements, retractions = {}, {}
    models = {(m["mental"]["source_id"], m["mental"]["id"]): i for i, m in enumerate(program["base_program"]["models"])}
    for atom in selected:
        work.spend()
        row = atom["edit"]
        if row["kind"] == "CHOICE_REPLACE":
            if row["choice_id"] in replacements:
                return None
            replacements[row["choice_id"]] = row["version_id"]
        else:
            retractions.setdefault(models[(row["source_id"], row["model_id"])] , []).append(atom)
    selection.update(replacements)
    for constraint in program["concepts"]["constraints"]:
        work.spend(1 + len(constraint["allowed_pairs"]))
        if [selection[constraint["left"]], selection[constraint["right"]]] not in constraint["allowed_pairs"]:
            return None
    # Complete assignment is checked once; single-edit intermediate states are irrelevant.
    return selection, retractions


class JointChangeOperator:
    def run(self, snapshot, issue, allowance, program):
        try:
            return self._run(snapshot, issue, allowance, thaw(program))
        except (ValueError, TypeError, KeyError, IndexError, RecursionError, StopIteration):
            raise HCLFailure("INVALID_REQUEST", "joint_changes", "INVALID_JOINT_CHANGE_JUDGMENT", "joint_changes",
                "The joint-change proposal violates its bounded source and target contract.") from None

    def _run(self, snapshot, issue, allowance, program):
        from hcl.operators.judgment_model import JudgmentModelOperator
        verify_joint_program(program, snapshot, allowance)
        work = JudgmentWork(allowance.max_local_evaluations)
        declaration = program["joint_changes"]
        atoms, target = declaration["atoms"], declaration["target"]
        evaluations, layers, candidates, frontier = [], [], [], []
        environments, counters = set(), set()
        concepts, baseline, minimum = None, None, None
        complete, unknown = False, False
        shared_upstream, model_cache = {}, {}
        # Leave room for search summaries and the ordinary local-model envelope.
        proof_bytes = len(codec.dumps(program))
        try:
            # Compiler/source validation, finite atom validation and replay binding
            # are charged before any search, even though malformed inputs always fail.
            work.spend(program["validation_units"] + node_count(declaration))
            concepts = compute_versions(program["concepts"], work.limit - work.used)
            work.spend(concepts["local_evaluations"])
            environments.update(concepts["assumption_environments"])
            counters.update(concepts["counterevidence_ids"])
            proof_bytes += len(codec.dumps(concepts))
            if not concepts["complete"]:
                frontier.extend(concepts["frontier"])
                raise OverflowError("INCOMPLETE_CONCEPT_LANGUAGE")
            branches = {codec.canonical(b["selections"]): b for b in concepts["branches"]}
            for size in range(len(atoms) + 1):
                layer = dict(cardinality=size, total=comb(len(atoms), size), generated=0, legal=0,
                             evaluated=0, resolved=0, changed=0, complete=False)
                layers.append(layer)
                for selected in combinations(atoms, size):
                    work.spend(1 + len(selected))  # Candidate generation, not free iteration.
                    layer["generated"] += 1
                    terminal = apply_atoms(program, selected, work)
                    if terminal is None:
                        continue
                    selection, retractions = terminal
                    layer["legal"] += 1
                    branch = branches[codec.canonical(selection)]
                    work.spend(1 + len(branch["classifications"]))
                    operation = JudgmentModelOperator()._run(snapshot, issue,
                        replace(allowance, max_local_evaluations=work.limit - work.used), program["base_program"],
                        concept_context=dict(bindings=program["concept_bindings"], classifications=branch["classifications"],
                            shared_upstream=shared_upstream,
                            joint_search=dict(retractions=retractions, model_cache=model_cache, target=target)))
                    work.spend(operation.resource_usage["local_evaluations"])
                    inference = operation.candidate_delta.new_inferences[0]
                    actual = thaw(inference.values)
                    # Target calculation/comparison/validation is also charged.
                    projection = target_projection(actual, target)
                    work.spend(node_count(projection) + len(selected) + 1)
                    all_computed = (len(actual["models"]) == len(program["base_program"]["models"])
                        and all(m["actual_argument"] is not None and not m["frontier"]
                            and not any(t["frontier"] for t in m["actual_argument"]["values"]["models"])
                            and all(d["status"] == "COMPUTED" and not d["frontier"] for d in m["decisions"])
                            for m in actual["models"]))
                    resolved = all_computed and projection["resolved"]
                    projection["resolved"] = resolved
                    identifiers = [a["atom_id"] for a in selected]
                    flat_retractions = [a["edit"] for rows in retractions.values() for a in rows]
                    identity = "joint-evaluation:" + digest([selection, identifiers])
                    evaluation = dict(evaluation_id=identity, atom_ids=identifiers, selections=selection,
                        retractions=flat_retractions, classifications=branch["classifications"], actual_judgment=actual,
                        target=projection, complete=resolved)
                    proof_bytes += len(codec.dumps(evaluation))
                    if proof_bytes > MAX_CERTIFICATE_BYTES - 262144:
                        frontier.append("JOINT_CHANGE_AUDIT_CAPACITY_FRONTIER")
                        raise OverflowError("BOUNDED_AUDIT_PROOF")
                    evaluations.append(evaluation)
                    environments.update(inference.assumption_environments)
                    environments.update("joint-counterfactual:" + a["atom_id"] for a in selected)
                    counters.update(inference.counterevidence_ids)
                    layer["evaluated"] += 1
                    layer["resolved"] += int(resolved)
                    if not resolved:
                        unknown = True
                        frontier.append("JOINT_CHANGE_TARGET_UNRESOLVED")
                    if size == 0:
                        baseline = projection
                    elif baseline is not None and baseline["resolved"] and resolved and projection["semantics"] != baseline["semantics"]:
                        layer["changed"] += 1
                        candidates.append(dict(atom_ids=identifiers, cardinality=size, selections=selection,
                            retractions=flat_retractions, evaluation_id=identity, target=projection))
                # A winning layer must finish; do not stop at its first witness.
                layer["complete"] = layer["generated"] == layer["total"] and layer["evaluated"] == layer["legal"]
                if layer["changed"]:
                    complete = not unknown and all(l["complete"] for l in layers)
                    minimum = size if complete else None
                    break
            else:
                complete = not unknown and all(l["complete"] for l in layers)
        except OverflowError:
            frontier.append("JOINT_CHANGE_WORK_OR_PROOF_FRONTIER")
        if not complete and not frontier:
            frontier.append("JOINT_CHANGE_INCOMPLETE_SEARCH")
        search = dict(language=declaration["language"], cost_unit=declaration["cost_unit"],
            complete=complete, status="FOUND_ALL_MINIMUM" if complete and minimum is not None else
                "NO_EXPRESSIBLE_CHANGE" if complete else "PARTIAL",
            minimum_cardinality=minimum, minimum_witnesses=candidates if complete and minimum is not None else [],
            candidate_witnesses=candidates, layers=layers, frontier=sorted(set(frontier)), baseline=baseline,
            adoption_authorized=False, scope="ALL_MINIMUM_CARDINALITY_SETS_ONLY_WITHIN_DECLARED_FINITE_EDIT_LANGUAGE")
        values = dict(operator_version=VERSION, issue_id=issue.issue_id, rule_version=snapshot.rule_version,
            source_versions=dict(snapshot.source_versions), program=program, concepts=concepts,
            evaluations=evaluations, joint_search=search, complete=complete,
            local_evaluations=work.used, execution_allowance=work.limit, issues=sorted(set(frontier)),
            semantic_certified=False, scope=COVERAGE)
        result = InferenceResult("joint-change:" + digest([issue.issue_id, values]), KIND, values,
            tuple(sorted(environments)), tuple(sorted(snapshot.source_versions)), tuple(sorted(counters)),
            snapshot.rule_version, COVERAGE)
        if len(codec.dumps(result)) > MAX_CERTIFICATE_BYTES:
            raise HCLFailure("BUDGET_EXHAUSTED", "joint_changes", "JOINT_CHANGE_AUDIT_CAPACITY", "proof",
                "The finite joint-change proof exceeds the unchanged audit capacity.")
        return OpResult("judgment.joint_changes", VERSION, snapshot.source_versions, ("append_inference",),
            (result.result_id,), tuple(sorted(set(frontier))), dict(local_evaluations=work.used), (),
            Delta(snapshot.session_id, snapshot.principal, snapshot.revision, snapshot.access_epoch,
                  snapshot.rule_version, snapshot.source_versions, (result,)))


def verify_joint_changes(values):
    data = thaw(values)
    data.pop("local_model", None)
    if type(data["execution_allowance"]) is not int or not 0 <= data["execution_allowance"] <= 10000000:
        raise ValueError("bounded joint-change certificate required")
    host = data["program"]["host_context"]
    snapshot = SimpleNamespace(session_id=host["session_id"], principal=Principal(**host["principal"]),
        revision=0, access_epoch=0, rule_version=data["rule_version"], source_versions=data["source_versions"])
    expected = JointChangeOperator()._run(snapshot, Issue(data["issue_id"], "judgment.evaluate"),
        replace(ExecutionBudget(), max_local_evaluations=data["execution_allowance"]), data["program"])
    if codec.canonical(thaw(expected.candidate_delta.new_inferences[0].values)) != codec.canonical(data):
        raise ValueError("joint edits, target, ties or minimum proof differs from exhaustive replay")
    return expected
