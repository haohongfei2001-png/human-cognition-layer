"""One actual shared cognition -> commitments -> argument dispute -> decision.

Certificates replay the complete local computation. They confer no source read,
write, policy adoption or delivery permission; the engine owns those gates.
"""

from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

from hcl.kernel.types import Delta, HCLFailure, InferenceResult, OpResult, Issue, Principal, thaw
from hcl.kernel.execution import ExecutionBudget
from hcl.memory import codec
from hcl.operators.agency import solve_action_values
from hcl.operators.argument_model import ArgumentModelOperator
from hcl.operators.commitment_qualification import commitment_condition
from hcl.operators.epistemic import query_belief, remaining_states, EpistemicLimits
from hcl.operators.interaction_model import InteractionModelOperator, map_view
from hcl.operators.shared_cognition import compute_shared_cognition, cognitive_record
from hcl.operators.judgment import VERSION, JudgmentWork, joint_outcomes, compare_framework
from hcl.semantics.model_compiler import planning_model

KIND = "CONDITIONAL_ACTION_JUDGMENT"


def record(operation):
    actual = operation.candidate_delta.new_inferences[0]
    return dict(result_id=actual.result_id, kind=actual.kind, values=thaw(actual.values),
                assumption_environments=actual.assumption_environments,
                premise_ids=tuple(sorted(actual.premise_ids)), counterevidence_ids=actual.counterevidence_ids,
                source_versions=dict(operation.read_set), issues=operation.issues)


def unresolved_argument_dependencies(program, bindings, facts):
    """Conservative influence closure, including contrary attacks and undercuts.

    A missing unknown fact premise is not a negative fact. Solving the currently
    established subtheory alone could otherwise make its opponent win. Track all
    queries reachable from that premise before allowing such a permission.
    """
    literals = {q["id"]: (q["kind"], q["atom"]) for q in program["literals"]}
    premises = {p["id"]: p for p in program["premises"]}
    gaps = {}
    for binding in bindings:
        if len(facts[binding["fact_id"]]["possible_values"]) == 1:
            continue
        affected = {literals[premises[binding["premise_id"]]["literal"]]}
        while True:
            before = set(affected)
            for rule in program["rules"]:
                if (any(literals[p] in affected for p in rule["premises"])
                        or ("RULE_APPLICABLE", rule["id"]) in affected):
                    affected.add(literals[rule["conclusion"]])
            if affected == before:
                break
        for query in program["queries"]:
            if literals[query["literal"]] in affected:
                gaps.setdefault(query["id"], []).append(binding["fact_id"])
    return {q: sorted(set(values)) for q, values in gaps.items()}


def norm_branches(framework, facts, argument, unresolved_queries=()):
    """Joint M13 extensions, never Cartesian independent norm truth assignments."""
    queries = {q["query_id"]: q for q in argument["queries"]}

    def state(norm, extension=None):
        guards = [facts[key]["possible_values"] for key in norm["guard_fact_ids"]]
        if any(tuple(values) == (False,) for values in guards):
            return "INAPPLICABLE"
        if any(tuple(values) != (True,) for values in guards):
            return "UNRESOLVED"
        if norm["argument_query_id"] is None:
            return "ACTIVE"
        if norm["argument_query_id"] in unresolved_queries:
            return "UNRESOLVED"
        query = queries.get(norm["argument_query_id"])
        if query is None or argument["strict_conflicts"] or argument["frontier"] or argument["inactive_assumptions"]:
            return "UNRESOLVED"
        if extension is None:
            positive, opposed = query["positive_accepted"], query["opposed_accepted"]
        else:
            literal = query["literal"]
            accepted = [a["conclusion"] for a in argument["arguments"] if a["argument_id"] in extension]
            positive = literal in accepted
            opposed = any(all(v[k] == literal[k] for k in ("atom", "scope", "kind"))
                          and v["negative"] != literal["negative"] for v in accepted)
        return "ACTIVE" if positive and not opposed else "REJECTED" if opposed and not positive else "UNRESOLVED"

    base = {norm["id"]: state(norm) for norm in framework["norms"]}
    if "UNRESOLVED" not in base.values():
        return [dict(basis="GROUNDED", extension=None, states=base)]
    preferred = next((q["preferred"] for q in argument["queries"]
                      if q["preferred"] is not None and not q["preferred"]["frontier"]), None)
    if preferred is None or argument["frontier"] or argument["strict_conflicts"]:
        return [dict(basis="CONSERVATIVE_UNRESOLVED", extension=None, states=base)]
    # Every branch is a real extension of the same jointly solved theory.
    branches = [dict(basis="PREFERRED_CONDITIONAL", extension=list(extension),
                     states={norm["id"]: state(norm, extension) for norm in framework["norms"]})
                for extension in preferred["preferred"]]
    return branches or [dict(basis="CONSERVATIVE_UNRESOLVED", extension=None, states=base)]


class JudgmentModelOperator:
    def run(self, snapshot, issue, allowance, program):
        try:
            return self._run(snapshot, issue, allowance, thaw(program))
        except (ValueError, TypeError, KeyError, IndexError, RecursionError, ZeroDivisionError):
            raise HCLFailure("INVALID_REQUEST", "judgment", "INVALID_JUDGMENT_MODEL", "model",
                             "The conditional judgment is outside its finite executable contract.") from None

    def _run(self, snapshot, issue, allowance, program, *, concept_context=None):
        from hcl.semantics.judgment_compiler import verify_program_bindings
        verify_program_bindings(program, snapshot, allowance)
        if dict(program["source_versions"]) != dict(snapshot.source_versions):
            raise ValueError("judgment sources differ from immutable snapshot")
        work = JudgmentWork(allowance.max_local_evaluations)
        outputs, issues = [], []
        environments = set()

        def remaining():
            return replace(allowance, max_local_evaluations=work.limit - work.used)

        for model_index, model in enumerate(program["models"]):
            mental = model["mental"]
            interaction = dict(model["interaction"], mental=mental)
            plans = {p["id"]: p for p in mental["plans"]}
            cache = None if concept_context is None else concept_context["shared_upstream"]
            reused = cache is not None and model_index in cache
            if reused:
                bundle, op07 = cache[model_index]
            else:
                bundle = compute_shared_cognition(snapshot, issue, remaining(), interaction,
                                                   tuple(sorted({p["at"] for p in plans.values()})))
                work.spend(bundle.operation.resource_usage["local_evaluations"])
                op07 = InteractionModelOperator()._run(snapshot, issue, remaining(), dict(models=[interaction]),
                    shared_cognition={(mental["source_id"], mental["id"]): bundle})
                work.spend(op07.resource_usage["local_evaluations"])
                if cache is not None:
                    cache[model_index] = (bundle, op07)
            actual_cognition = record(bundle.operation)
            environments.update(actual_cognition["assumption_environments"])
            actual07 = record(op07)
            environments.update(actual07["assumption_environments"])
            out = dict(model_id=mental["id"], source_id=mental["source_id"],
                       cognition=cognitive_record(bundle), actual_interaction=actual07,
                       opportunities={}, facts={}, argument_input=None, actual_argument=None, argument_dependency_gaps={},
                       fact_bindings=[], decisions=[], frontier=[])
            outputs.append(out)
            issues.extend((*bundle.operation.issues, *op07.issues))
            cognitive = actual_cognition["values"]["models"][0]
            timeline, envs = bundle.trace.get(mental["id"], ({}, {}))
            beliefs = {q["query_id"]: q for q in cognitive["beliefs"]}
            try:
                for plan in plans.values():
                    state = timeline.get(plan["at"])
                    if state is None:
                        out["opportunities"][plan["id"]] = dict(status="UNRESOLVED", actual={}, subjective={}, state_results={})
                        continue
                    work.spend(2)
                    actual = map_view(remaining_states(state, (), EpistemicLimits(max_depth=16)), plan)
                    subjective = map_view(remaining_states(state, (plan["actor"],), EpistemicLimits(max_depth=16)), plan)
                    value = dict(status="MAPPED" if actual["status"] == subjective["status"] == "MAPPED" else "UNRESOLVED",
                                 actual=actual, subjective=subjective, state_results={},
                                 actor=plan["actor"], at=plan["at"], cognitive_result_id=actual_cognition["result_id"],
                                 actual_plan=next((p for p in cognitive["plans"] if p["plan_id"] == plan["id"]), None),
                                 assumption_environments=envs[plan["at"]])
                    out["opportunities"][plan["id"]] = value
                    if value["status"] != "MAPPED":
                        continue
                    for selected in sorted(set(actual["states"]) | set(subjective["states"])):
                        if work.used >= work.limit:
                            raise OverflowError("JUDGMENT_WORK_FRONTIER")
                        computed = solve_action_values(planning_model(plan["graph"]), {selected: "1"}, 1,
                            actual_state=selected, max_expansions=max(1, work.limit - work.used))
                        work.spend(computed["expansions"])
                        value["state_results"][selected] = computed
                        if computed["frontier"]:
                            value["status"] = "UNRESOLVED"
                for fact in model["facts"]:
                    work.spend()
                    ref = fact["reference"]
                    row = dict(fact_id=fact["id"], role=fact["role"], kind=fact["kind"], reference=ref,
                               possible_values=[False, True], status="UNRESOLVED", actual=None,
                               result_id=actual_cognition["result_id"],
                               scope="CONDITIONAL_COMPUTATION_NOT_WORLD_OR_PRIVATE_TRUTH")
                    out["facts"][fact["id"]] = row
                    if fact["kind"] == "MENTAL_QUERY":
                        value = beliefs.get(ref["query_id"])
                        row["actual"] = value
                        if value is not None and value["status"] != "FRONTIER_UNEXPLORED":
                            row["possible_values"] = list(value["possible_values"])
                            if fact["role"] == "KNOWLEDGE":
                                formula = value["formula"]
                                if not isinstance(formula, dict) or formula.get("op") != "believes":
                                    raise ValueError("knowledge must reference an explicit belief query")
                                # A believed proposition need not be true. Retain
                                # actual truth and belief as independent outputs.
                                work.spend()
                                joint = query_belief(timeline[value["at"]], dict(op="and", args=[formula["arg"], formula]), EpistemicLimits(max_depth=16))
                                row["knowledge_truth_and_belief"] = joint
                                row["possible_values"] = list(joint["possible_values"])
                    elif fact["kind"] == "OPPORTUNITY":
                        opportunity = out["opportunities"][ref["plan_id"]]
                        row["actual"] = opportunity
                        if opportunity["status"] == "MAPPED":
                            states = opportunity["actual" if ref["view"] == "WORLD" else "subjective"]["states"]
                            values = {opportunity["state_results"][s]["world_feasibility"][ref["action_id"]] for s in states}
                            if values:
                                row["possible_values"] = sorted(values)
                    elif fact["kind"] == "COMMITMENT":
                        proof = commitment_condition(ref, actual07["values"]["models"][0], actual07["result_id"], work.limit - work.used)
                        work.spend(proof["work"])
                        row.update(actual=proof, possible_values=list(proof["possible_values"]), result_id=actual07["result_id"])
                    else:
                        value = next((c for c in cognitive["causal"] if c["query_id"] == ref["query_id"]), None)
                        row["actual"] = value
                        if value is not None and not value["frontier"] and value["possible_values"]:
                            row["possible_values"] = sorted({v == ref["expected"] for v in value["possible_values"]})
                    if len(row["possible_values"]) == 1:
                        row["status"] = "DETERMINATE_IN_MODEL"
                argument = deepcopy(model["argument"])
                all_bindings = list(model["fact_bindings"])
                if concept_context is not None:
                    from hcl.operators.concept_judgment import bind_classifications
                    out["source_versions"] = dict(snapshot.source_versions)
                    all_bindings.extend(bind_classifications(model, concept_context["bindings"][model_index],
                        concept_context["classifications"], out, argument, actual07, work))
                premise_map = {p["id"]: p for p in argument["premises"]}
                for binding in all_bindings:
                    guard = "judgment-fact:" + sha256(codec.dumps([mental["source_id"], mental["id"], binding])).hexdigest()
                    if any(guard in p["assumptions"] for p in argument["premises"]) or guard in argument["active_assumptions"]:
                        raise ValueError("computed fact guard identity collision")
                    premise_map[binding["premise_id"]]["assumptions"].append(guard)
                    values = out["facts"][binding["fact_id"]]["possible_values"]
                    included = tuple(values) == (binding["expected"],)
                    if included:
                        argument["active_assumptions"].append(guard)
                    out["fact_bindings"].append(dict(binding, guard=guard, included=included,
                        fact_result_id=out["facts"][binding["fact_id"]]["result_id"]))
                norm_queries = {n["argument_query_id"] for d in model["decisions"] for f in d["frameworks"] for n in f["norms"]}
                for q in argument["queries"]:
                    if q["id"] in norm_queries:
                        q["preferred"] = True
                out["argument_input"] = argument
                out["argument_dependency_gaps"] = unresolved_argument_dependencies(argument, all_bindings, out["facts"])
                op13 = ArgumentModelOperator().run(snapshot, issue, remaining(), dict(models=[argument]), meter_work=concept_context is not None)
                work.spend(op13.resource_usage["local_evaluations"])
                actual13 = record(op13)
                out["actual_argument"] = actual13
                environments.update(actual13["assumption_environments"])
                issues.extend(op13.issues)
                theory = actual13["values"]["models"][0]
                for decision in model["decisions"]:
                    plan = plans[decision["plan_id"]]
                    opportunity = out["opportunities"][plan["id"]]
                    row = dict(decision_id=decision["id"], actor=plan["actor"], at=plan["at"],
                               plan_id=plan["id"], status="UNCOMPUTED", outcomes=[], frameworks=[],
                               robust_across_frameworks=[], responsibility=[], frontier=[],
                               cognitive_result_id=actual_cognition["result_id"],
                               interaction_result_id=actual07["result_id"], argument_result_id=actual13["result_id"])
                    out["decisions"].append(row)
                    if opportunity["status"] != "MAPPED":
                        row["frontier"].append("JUDGMENT_OPPORTUNITY_UNRESOLVED")
                        continue
                    scenarios = decision["scenarios"] or [dict(id="actual-state:" + s, distribution={s: "1"}, segment_ids=[])
                                                            for s in opportunity["actual"]["states"]]
                    row["scenario_scope"] = ("DECLARED_PROBABILITY_HYPOTHESES" if decision["scenarios"] else "SEPARATE_POSSIBLE_STATES_NO_PROBABILITY_ASSUMPTION")
                    if any(f["decision_rule"] == "EXPECTED" for f in decision["frameworks"]) and len(scenarios) != 1:
                        row["frontier"].append("EXPECTED_PROBABILITIES_UNSPECIFIED")
                        # Other frameworks remain useful; do not hide their work.
                    if set(opportunity["actual"]["states"]) & set(plan["graph"]["terminal"]):
                        row["frontier"].append("TERMINAL_OR_UNRESOLVED_DECISION_STATE")
                        continue
                    row["outcomes"] = joint_outcomes(plan["graph"], decision["dimensions"], scenarios,
                        opportunity["actual"]["states"], opportunity["subjective"]["states"], work)
                    accepted_sets = []
                    for framework in decision["frameworks"]:
                        environments.update(framework["active_assumptions"])
                        frame = dict(framework_id=framework["id"], label=framework["label"], origin=framework["origin"],
                                     adoption_status="SOURCE_RECONSTRUCTION_NOT_AUTHENTICATED_USER_AUTHORIZATION",
                                     assumptions=framework["assumptions"], active_assumptions=framework["active_assumptions"],
                                     weights=framework["weights"], decision_rule=framework["decision_rule"],
                                     status="UNCOMPUTED", branches=[], robust_recommended=[], revision_conditions={})
                        row["frameworks"].append(frame)
                        if set(framework["assumptions"]) - set(framework["active_assumptions"]):
                            frame["status"] = "FRAMEWORK_ASSUMPTION_RETRACTED"
                            row["frontier"].append("JUDGMENT_FRAMEWORK_ASSUMPTION_RETRACTED")
                            continue
                        if framework["decision_rule"] == "EXPECTED" and len(scenarios) != 1:
                            frame["status"] = "EXPECTED_PROBABILITIES_UNSPECIFIED"
                            continue
                        branches = norm_branches(framework, out["facts"], theory, out["argument_dependency_gaps"])
                        winners = []
                        for branch in branches:
                            result = compare_framework(framework, row["outcomes"], branch["states"], decision["dimensions"], work)
                            frame["branches"].append(dict(branch, result=result))
                            winners.append(set(result["recommended"]))
                        frame["robust_recommended"] = sorted(set.intersection(*winners)) if winners else []
                        frame["status"] = "COMPUTED"
                        frame["revision_conditions"] = dict(
                            factual_guards={key: out["facts"][key] for norm in framework["norms"] for key in norm["guard_fact_ids"]},
                            argument_disputes=[q for q in theory["queries"] if q["query_id"] in {n["argument_query_id"] for n in framework["norms"]}],
                            unresolved_argument_facts=out["argument_dependency_gaps"],
                            change_scope="Change facts, principle priorities, declared value scales/weights or retained joint scenarios and recompute; none is automatically a user preference.")
                        accepted_sets.append(set(frame["robust_recommended"]))
                    if len(accepted_sets) == len(row["frameworks"]) and accepted_sets:
                        row["robust_across_frameworks"] = sorted(set.intersection(*accepted_sets))
                    for responsibility in decision["responsibility_queries"]:
                        query = next((q for q in theory["queries"] if q["query_id"] == responsibility["query_id"]), None)
                        row["responsibility"].append(dict(query_id=responsibility["query_id"], actual=query,
                            status="UNRESOLVED_FACT_DEPENDENCY" if responsibility["query_id"] in out["argument_dependency_gaps"] else "CONDITIONAL_ARGUMENT_RESULT",
                            unresolved_facts=out["argument_dependency_gaps"].get(responsibility["query_id"], []),
                            factors={key: out["facts"][key] for key in responsibility["factor_ids"]},
                            scope="FRAMEWORK_CONDITIONAL_ARGUMENT_ACCEPTANCE_NOT_BLAME_OR_PRIVATE_INTENTION"))
                    row["status"] = "COMPUTED" if not row["frontier"] else "PARTIAL"
            except OverflowError:
                out["frontier"].append("JUDGMENT_WORK_FRONTIER")
                # Partly enumerated choices are never complete recommendations.
                for decision in out["decisions"]:
                    if decision["status"] == "UNCOMPUTED":
                        decision["frontier"].append("JUDGMENT_WORK_FRONTIER")
                        decision["robust_across_frameworks"] = []
            issues.extend(out["frontier"])
            issues.extend(f for d in out["decisions"] for f in d["frontier"])
        values = dict(operator_version=VERSION if concept_context is None else "s4-concept-branch-judgment-2", issue_id=issue.issue_id,
                      rule_version=snapshot.rule_version, source_versions=dict(snapshot.source_versions),
                      program=program, models=outputs, execution_allowance=work.limit,
                      local_evaluations=work.used, issues=sorted(set(issues)),
                      semantic_certified=False, candidate_completeness="NOT_ESTABLISHED",
                      scope="SOURCE_BOUND_FINITE_SINGLE_STEP_CONDITIONAL_JUDGMENT_NOT_MORAL_TRUTH")
        inference = InferenceResult("judgment-result:" + sha256(codec.dumps([issue.issue_id, values])).hexdigest(), KIND, values,
                                    tuple(sorted(environments)), tuple(sorted(snapshot.source_versions)), (), snapshot.rule_version,
                                    "CONDITIONAL_SINGLE_STEP_ACTION_JUDGMENT")
        return OpResult("judgment.execute", VERSION, snapshot.source_versions, ("append_inference",),
                        (inference.result_id,), tuple(sorted(set(issues))), dict(local_evaluations=work.used), (),
                        Delta(snapshot.session_id, snapshot.principal, snapshot.revision, snapshot.access_epoch,
                              snapshot.rule_version, snapshot.source_versions, (inference,)))


def verify_judgment(values):
    data = thaw(values)
    data.pop("local_model", None)
    allowance = data["execution_allowance"]
    if type(allowance) is not int or not 0 <= allowance <= 10000000:
        raise ValueError("invalid judgment certificate bound")
    snapshot = SimpleNamespace(session_id="pure-certificate", principal=Principal("pure", "certificate"),
                               revision=0, access_epoch=0, rule_version=data["rule_version"],
                               source_versions=data["source_versions"])
    expected = JudgmentModelOperator()._run(snapshot, Issue(data["issue_id"], "judgment.evaluate"),
        replace(ExecutionBudget(), max_local_evaluations=allowance), data["program"])
    if codec.canonical(thaw(expected.candidate_delta.new_inferences[0].values)) != codec.canonical(data):
        raise ValueError("judgment certificate differs from actual shared computation")
    return expected
