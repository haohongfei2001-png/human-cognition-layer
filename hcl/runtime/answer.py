"""Deterministic first-slice claim assembly from actual computed values."""
from __future__ import annotations

import json

from hcl.kernel.types import (
    AnswerClaim, AnswerContract, FORMAL_SCOPE, HCLFailure, InferenceResult,
    ResultField, Snapshot, thaw,
)


class AnswerAssembler:
    def _claim(self, result: InferenceResult) -> AnswerClaim:
        if result.kind == "CONDITIONAL_MECHANISM_DISCOVERY":
            return self._discovery_claim(result)
        if result.kind == "CONDITIONAL_ARGUMENT_ACCEPTANCE":
            return self._argument_claim(result)
        if result.kind == "CONDITIONAL_COGNITIVE_MODEL":
            return self._mental_claim(result)
        if result.kind == "CONDITIONAL_REVISION":
            return self._revision_claim(result)
        if result.kind == "CONDITIONAL_FOL":
            return self._semantic_claim(result)
        values = result.values
        if (result.kind != "EXACT_MODEL" or result.coverage != FORMAL_SCOPE
                or type(values.get("conclusion")) is not bool
                or type(values.get("is_countermodel")) is not bool
                or not isinstance(values.get("premises"), tuple)
                or any(type(value) is not bool for value in values["premises"])
                or values["is_countermodel"] != (all(values["premises"]) and not values["conclusion"])):
            raise HCLFailure("FAILED", "answer", "RESULT_CONTRACT_INVALID", "values",
                             "The actual computation does not satisfy the answer contract.")
        truth = "true" if values["conclusion"] else "false"
        if values["is_countermodel"]:
            conclusion = "All supplied premises hold, so this interpretation is a verified counterexample to entailment."
        elif not all(values["premises"]):
            conclusion = "At least one supplied premise is false, so this interpretation is not a counterexample. This does not establish entailment."
        else:
            conclusion = "This interpretation is not a counterexample. This does not establish entailment."
        text = (f"In the supplied finite interpretation, the conclusion is {truth}. {conclusion} "
                "These values concern only the explicit formal model, not real-world or private mental truth.")
        fields = tuple(ResultField(result.result_id, name, values[name])
                       for name in ("conclusion", "premises", "is_countermodel"))
        return AnswerClaim(text, f"claim:{result.result_id}", fields,
                                  result.assumption_environments, result.counterevidence_ids,
                                  "EXACT_MODEL")

    def _discovery_claim(self, result):
        from hcl.operators.discovery_model import verify_discovery, delivery_values
        try:
            values = delivery_values(result.values)
            verify_discovery(values)
            actuals = [record for column in result.values["prediction_matrix"].values() for record in column["actual_results"]]
            actuals.extend(record for probe in result.values["distinguishing_observations"]
                           for evaluated in probe["evaluations"].values() for record in evaluated["actual_results"])
            for record in actuals:
                if record["kind"] not in ("CONDITIONAL_COGNITIVE_MODEL", "CONDITIONAL_ARGUMENT_ACCEPTANCE"):
                    raise ValueError("unregistered domain prediction")
                self._claim(InferenceResult(record["result_id"],record["kind"],record["values"],
                            tuple(record["assumption_environments"]),tuple(record["source_versions"]),(),
                            result.rule_version,"CONDITIONAL_DOMAIN_PREDICTION"))
        except (ValueError, TypeError, KeyError, IndexError, StopIteration):
            raise HCLFailure("FAILED", "answer", "DISCOVERY_RESULT_MISMATCH", "prediction_matrix",
                             "Explanation claims differ from their actual mechanism predictions.") from None
        lines = ["Conditional mechanism comparison using actual domain predictions; candidate coverage is not established."]
        for key in values["pareto_programs"]:
            column = values["prediction_matrix"][key]
            lines.append("Program " + key[:12] + ": explained factors=" + str(len(column["profile"]["explained"]))
                         + ", contradicted=" + str(len(column["profile"]["contradicted"]))
                         + ", unmodeled/uncomputed=" + str(len(column["profile"]["unmodeled"])) + ".")
            for condition in column["domain_conditions"]:
                lines.append("Observed-fit context " + condition["context_hash"][:12] + " is conditional on "
                             + str(tuple(condition["assumption_environments"])) + ".")
        for key, column in values["prediction_matrix"].items():
            for limitation in column["domain_limitations"]:
                lines.append("Observed prediction " + key[:12] + " in context " + limitation["context_hash"][:12]
                             + " has domain limitations " + ", ".join(limitation["issues"]) + "; scope/details="
                             + json.dumps(thaw(limitation["models"]), ensure_ascii=False, sort_keys=True) + ".")
        computed_edits = sum(edit["evaluation_status"] == "RECOMPUTED" for edit in values["edit_history"])
        lines.append("Actually recomputed mechanism edits: " + str(computed_edits) + "; proposed=" + str(len(values["edit_history"])) + ".")
        for probe in values["distinguishing_observations"]:
            lines.append("Hypothetical probe " + probe["probe_id"] + " separates " + str(probe["separated_pairs"])
                         + " computed candidate pairs; incomplete=" + str(len(probe["incomplete"])) + ".")
            for key, limitations in probe["domain_limitations"].items():
                for limitation in limitations:
                    lines.append("Hypothetical probe " + probe["probe_id"] + ", candidate " + key[:12]
                                 + " has domain limitations " + ", ".join(limitation["issues"]) + "; scope/details="
                                 + json.dumps(thaw(limitation["models"]), ensure_ascii=False, sort_keys=True) + ".")
            for key, prediction in probe["predictions"].items():
                for condition in prediction["domain_conditions"]:
                    lines.append("Hypothetical probe " + probe["probe_id"] + ", candidate " + key[:12]
                                 + " is conditional on " + str(tuple(condition["assumption_environments"])) + ".")
        if values["frontier"]:
            lines.append("Unexplored: " + ", ".join(values["frontier"]) + ".")
        lines.append("Prediction equivalence concerns only the stated contexts and observations. "
                     "Source interpretation, mechanism truth and evidence independence remain unverified; no calibrated posterior is claimed.")
        names = ("programs", "initial_program_hashes", "prediction_matrix", "pareto_programs", "prediction_classes", "edit_history",
                 "distinguishing_observations", "domain_issues", "frontier", "semantic_certified", "candidate_completeness")
        fields = tuple(ResultField(result.result_id,name,result.values[name]) for name in names if name in result.values)
        return AnswerClaim(" ".join(lines),"claim:"+result.result_id,fields,result.assumption_environments,
                           result.counterevidence_ids,"CONDITIONAL_MECHANISM_COMPARISON_NOT_TRUTH")

    def qualification_issues(self, result):
        if result.kind != "CONDITIONAL_MECHANISM_DISCOVERY":
            return ()
        # _claim checks the complete retained computation, not just a label.
        self._claim(result)
        from hcl.operators.discovery_model import delivery_values
        return tuple(delivery_values(result.values)["domain_issues"])

    def _argument_claim(self, result):
        values = result.values
        if (values.get("semantic_certified") is not False
                or values.get("candidate_completeness") != "NOT_ESTABLISHED"
                or not isinstance(values.get("models"), tuple) or not values["models"]):
            raise HCLFailure("FAILED", "answer", "ARGUMENT_RESULT_CONTRACT", "models",
                             "The argument result lacks its conditional reconstruction boundary.")
        from hcl.operators.argumentation import ACCEPTANCE_SCOPE
        from hcl.semantics.argument_compiler import argument_source_segments
        lines = ["Conditional acceptance under the reconstructed argument models, within finite acyclic proofs. "
                 "Critical-edit minimality is limited to the declared retraction set."]
        for model in values["models"]:
            lines.append("Model " + model["model_id"] + " [" + model["frame_kind"] + "]:")
            if model.get("acceptance_scope") != ACCEPTANCE_SCOPE or model.get("namespace_source_id") != model["source_id"]:
                raise HCLFailure("FAILED", "answer", "ARGUMENT_RESULT_CONTRACT", "acceptance_scope",
                                 "The argument result lacks its bounded proof and attribution scope.")
            lines.append("Namespace source " + model["namespace_source_id"] + "; actual input sources: "
                         + ", ".join(sorted(model["input_source_versions"])) + ".")
            if model["excluded_circular_rules"]:
                lines.append("Excluded circular proof rules: " + ", ".join(model["excluded_circular_rules"]) + ".")
            arguments = {row["argument_id"]: row for row in model["arguments"]}
            for row in arguments.values():
                segments = argument_source_segments(model["source_records"], row["premises"], row["rules"])
                if (segments != row["source_segment_ids"] or not segments
                        or any(key not in model["source_bindings"] or model["source_bindings"][key]["kind"] != "SOURCE"
                               for key in segments)):
                    raise HCLFailure("FAILED", "answer", "ARGUMENT_PROVENANCE_MISMATCH", "source_segment_ids",
                                     "Proof evidence does not match its actual source-bound records.")
            for query in model["queries"]:
                if query["status"] == "COMPLETE":
                    positive = sorted(key for key, row in arguments.items()
                                      if row["conclusion"] == query["literal"] and model["labels"].get(key) == "IN")
                    opposed = sorted(key for key, row in arguments.items()
                                     if all(row["conclusion"][k] == query["literal"][k] for k in ("atom", "scope", "kind"))
                                     and row["conclusion"]["negative"] != query["literal"]["negative"]
                                     and model["labels"].get(key) == "IN")
                    if (tuple(positive) != query["accepted_arguments"] or tuple(opposed) != query["opposed_arguments"]
                            or bool(positive) != query["positive_accepted"] or bool(opposed) != query["opposed_accepted"]):
                        raise HCLFailure("FAILED", "answer", "ARGUMENT_ACCEPTANCE_MISMATCH", "queries",
                                         "The claim does not match actual grounded argument labels.")
                elif (query["positive_accepted"] is not None or query["opposed_accepted"] is not None
                      or query["accepted_arguments"] or query["opposed_arguments"]):
                    raise HCLFailure("FAILED", "answer", "ARGUMENT_ACCEPTANCE_MISMATCH", "queries",
                                     "An unfinished computation cannot license acceptance values.")
                lines.append("Query " + query["query_id"] + ": " + query["status"] + "; grounded accepted="
                             + str(query["positive_accepted"]) + ", opposed=" + str(query["opposed_accepted"]) + ".")
                if query["preferred"] is not None:
                    lines.append("Preferred-extension search: " + query["preferred"]["status"] + ".")
                if query["critical"] is not None:
                    lines.append("Critical retractions: " + query["critical"]["status"] + "; edits="
                                 + str(tuple(query["critical"]["edits"])) + ".")
            if model["strict_conflicts"]:
                lines.append("The strict reconstructed core is inconsistent; no explosive rule is added.")
            if model["inactive_assumptions"]:
                lines.append("Withdrawn assumptions: " + ", ".join(model["inactive_assumptions"]) + ".")
            if model["frontier"]:
                lines.append("Unexplored: " + ", ".join(model["frontier"]) + ".")
        lines.append("Argument acceptance is conditional on source interpretation, premises, rules and priorities; "
                     "it is not premise truth, philosophical truth or semantic certification.")
        fields=tuple(ResultField(result.result_id,key,values[key]) for key in ("models","semantic_certified","candidate_completeness"))
        return AnswerClaim(" ".join(lines),"claim:"+result.result_id,fields,result.assumption_environments,
                           result.counterevidence_ids,"CONDITIONAL_ARGUMENT_ACCEPTANCE_NOT_TRUTH")

    def _mental_claim(self, result):
        values = result.values
        if (values.get("semantic_certified") is not False
                or values.get("candidate_completeness") != "NOT_ESTABLISHED"
                or not isinstance(values.get("models"), tuple) or not values["models"]):
            raise HCLFailure("FAILED", "answer", "COGNITIVE_RESULT_CONTRACT", "models",
                             "The cognitive result does not satisfy the conditional model contract.")
        lines = ["Conditional computations for source-bound proposed cognitive models."]
        for model in values["models"]:
            lines.append("Model " + model["model_id"] + " [" + model["frame_kind"] + "]:")
            variables = {row["variable_id"]: row for row in model["shared_variables"]}
            if model["inactive_assumptions"]:
                lines.append("Withdrawn model assumptions: " + ", ".join(model["inactive_assumptions"]) + ".")
            for query in model["beliefs"]:
                lines.append("At " + str(query["at"]) + ", query " + query["query_id"] + " "
                             + json.dumps(thaw(query["formula"]), ensure_ascii=False, sort_keys=True)
                             + ": " + query["status"] + ", possible=" + str(tuple(query["possible_values"])) + ".")
            for plan in model["plans"]:
                from hcl.operators.agency import verify_plan_belief
                if plan["status"] == "SOLVED" and not verify_plan_belief(
                        variables.get(plan["belief_variable_id"]), plan):
                    raise HCLFailure("FAILED", "answer", "COGNITIVE_DEPENDENCY_MISSING", "belief_variable_id",
                                     "The action result lacks its actual computed belief dependency.")
                lines.append("Plan " + plan["plan_id"] + ": " + plan["status"] + "; Q="
                             + json.dumps(thaw(plan["q"]), ensure_ascii=False, sort_keys=True)
                             + "; best=" + ", ".join(plan["best_actions"]) + ".")
                if "policy" in plan:
                    lines.append("Declared mixture predicts " + json.dumps(thaw(plan["policy"]["probabilities"]), sort_keys=True) + ".")
            for causal in model["causal"]:
                lines.append("Causal query " + causal["query_id"] + ": " + causal["status"]
                             + "; possible=" + str(tuple(causal["possible_values"])) + ".")
            if model["frontier"]:
                lines.append("Unexplored: " + ", ".join(model["frontier"]) + ".")
        lines.append("Results depend on proposed observation, persistence, goal and causal mechanisms; "
                     "they are not private mental truth, semantic certification or calibrated human probabilities.")
        fields = tuple(ResultField(result.result_id, key, values[key])
                       for key in ("models", "semantic_certified", "candidate_completeness"))
        return AnswerClaim(" ".join(lines), "claim:" + result.result_id, fields,
                           result.assumption_environments, result.counterevidence_ids,
                           "CONDITIONAL_COGNITIVE_MODEL_NOT_PRIVATE_TRUTH")

    def _semantic_claim(self, result):
        values = result.values
        if (values.get('semantic_certified') is not False
                or values.get('candidate_completeness') != 'NOT_ESTABLISHED'
                or not isinstance(values.get('readings'), tuple) or not values['readings']):
            raise HCLFailure('FAILED', 'answer', 'SEMANTIC_RESULT_CONTRACT_INVALID', 'values',
                             'The conditional semantic result does not satisfy its contract.')
        lines = ['Conditional formal results for the supplied candidate readings. '
                 'The extraction is an injected offline fixture, not verified language understanding or world/private truth.']
        conclusions = {'True': 'follows in this formal reading', 'False': 'is contradicted in this formal reading',
                       'Uncertain': 'is neither entailed nor refuted in this formal reading'}
        for row in values['readings']:
            if row['status'] == 'CLASSIFIED':
                if row['label'] not in conclusions:
                    raise HCLFailure('FAILED', 'answer', 'INVALID_CONDITIONAL_LABEL', 'values.readings',
                                     'The conditional result has an invalid classification.')
                conclusion = conclusions[row['label']]
            elif row['status'] == 'INCONSISTENT_PREMISES':
                conclusion = 'has inconsistent premises; no conclusion is licensed by explosion'
            else:
                conclusion = 'remains unresolved (' + row['status'] + ')'
            lines.append('Reading ' + row['id'] + ' [' + row['frame_kind'] + ']: ' + row['query_reading'] + ' ' + conclusion + '.')
            if row['assumptions']:
                lines.append('Explicit candidate assumptions: ' + '; '.join(row['assumptions']) + '.')
            for witness in row['countermodels']:
                lines.append('A checked finite scenario has all premise values ' + str(tuple(witness['premise_values']))
                             + ' and original query value ' + str(witness['query_value']) + '. '
                             + 'This is a generated formal scenario, not an original quotation: '
                             + json.dumps(thaw(witness['scenario']), ensure_ascii=False, sort_keys=True))
            if row['unresolved']:
                lines.append('Unresolved obligations: ' + ', '.join(row['unresolved']) + '.')
        if values['status'] == 'READING_DEPENDENT':
            lines.append('The readings disagree. No unique unconditional answer is established.')
        lines.append('Source references and typed syntax were checked. Semantic alignment and completeness remain unverified.')
        text = '\n'.join(lines)
        fields = tuple(ResultField(result.result_id, name, values[name])
                       for name in ('status', 'label', 'readings', 'semantic_certified', 'candidate_completeness'))
        return AnswerClaim(
            text,
            "claim:" + result.result_id,
            fields,
            result.assumption_environments,
            result.counterevidence_ids,
            "CONDITIONAL_FORMAL_NOT_SEMANTIC_TRUTH",
        )

    def _revision_claim(self, result):
        values = result.values
        bits = values.get("support_bits", {})
        if (
            values.get("semantic_certified") is not False
            or values.get("candidate_completeness") != "NOT_ESTABLISHED"
            or any(
                type(bits.get(key)) is not bool
                for key in ("positive_support", "negative_support", "frontier_unexplored")
            )
            or bits.get("epistemic_status") != "CONDITIONAL_SUPPORT_NOT_TRUTH_OR_ARGUMENT_ACCEPTANCE"
        ):
            raise HCLFailure(
                "FAILED",
                "answer",
                "REVISION_RESULT_CONTRACT_INVALID",
                "values",
                "The conditional revision result does not satisfy its contract.",
            )
        positive, negative = values["query"]["positive"], values["query"]["negative"]
        state = values["kernel_state"]
        if (
            bool(state["supports"][positive]) != bits["positive_support"]
            or bool(state["supports"][negative]) != bits["negative_support"]
            or bool({positive, negative} & set(state["frontier"])) != bits["frontier_unexplored"]
        ):
            raise HCLFailure(
                "FAILED",
                "answer",
                "REVISION_SUPPORT_MISMATCH",
                "values",
                "Support fields differ from the actual rooted result.",
            )
        atom = values["claim_metadata"][positive]
        label = atom["predicate"] + "(" + ", ".join(atom["arguments"]) + ")"
        status = {
            (True, False): "positive support only",
            (False, True): "negative support only",
            (True, True): "both positive and negative support; no explosion",
            (False, False): "neither polarity has rooted support",
        }
        lines = [
            "In the supplied scoped candidate program ["
            + atom["frame_kind"]
            + "] at "
            + atom["at_point"]
            + " for perspective "
            + atom["perspective_id"]
            + ", "
            + label
            + " has "
            + status[(bits["positive_support"], bits["negative_support"])]
            + "."
        ]
        if bits["frontier_unexplored"]:
            lines.append("Relevant bounded search remains unexplored; missing support is not a disproof.")
        if values["known_at"] is not None:
            lines.append(
                "Evidence was selected at recorded ledger revision "
                + str(values["known_at"])
                + " before checking event and agent-access time."
            )
        lines.append(
            "Changed claims: "
            + str(len(values["changed_claims"]))
            + "; retained claims: "
            + str(len(values["retained_claims"]))
            + "."
        )
        if values["default_results"]:
            lines.append(
                "Default computations: " + ", ".join(sorted(set(values["default_results"].values()))) + "."
            )
        lines.append(
            "These are conditional rooted results under proposed interpretations and assumptions, not established world truth, character belief, or language understanding."
        )
        fields = tuple(
            ResultField(result.result_id, key, values[key])
            for key in (
                "support_bits",
                "query",
                "claim_metadata",
                "known_at",
                "changed_claims",
                "retained_claims",
                "default_results",
                "semantic_certified",
            )
        )
        return AnswerClaim(
            " ".join(lines),
            "claim:" + result.result_id,
            fields,
            result.assumption_environments,
            result.counterevidence_ids,
            "CONDITIONAL_REVISION_NOT_WORLD_OR_PRIVATE_TRUTH",
        )

    def build(
        self, snapshot: Snapshot, issues, accepted_results: tuple[InferenceResult, ...]
    ) -> AnswerContract:
        claims = tuple(self._claim(result) for result in accepted_results)
        contract = AnswerContract(
            "\n\n".join(claim.text for claim in claims),
            tuple(claims),
            "RESULT_FIELDS_VERIFIED",
            (
                "MODEL_INTERPRETATIONS_UNVERIFIED"
                if any(
                    result.kind in ("CONDITIONAL_FOL", "CONDITIONAL_REVISION", "CONDITIONAL_COGNITIVE_MODEL", "CONDITIONAL_ARGUMENT_ACCEPTANCE", "CONDITIONAL_MECHANISM_DISCOVERY") for result in accepted_results
                )
                else "EXPLICIT_FORMAL_INPUT_ONLY"
            ),
        )
        self.validate(contract, accepted_results)
        return contract

    def validate(self, contract: AnswerContract, results: tuple[InferenceResult, ...]) -> None:
        by_id = {result.result_id: result for result in results}
        for claim in contract.claims:
            for used in claim.used_result_fields:
                actual = by_id.get(used.result_id)
                if (
                    actual is None
                    or used.field not in actual.values
                    or type(actual.values[used.field]) is not type(used.value)
                    or json.dumps(thaw(actual.values[used.field]), sort_keys=True)
                    != json.dumps(thaw(used.value), sort_keys=True)
                ):
                    raise HCLFailure("FAILED", "answer", "RESULT_FIELD_MISMATCH", "used_result_fields",
                                     "An answer claim does not match the actual computation.")
        if results and contract.claims != tuple(self._claim(result) for result in results):
            raise HCLFailure("FAILED", "answer", "COMPUTED_CLAIM_MISMATCH", "claim_records",
                             "The formal claim text or its conditions differ from the checked result.")
        if contract.answer != "\n\n".join(claim.text for claim in contract.claims):
            raise HCLFailure("FAILED", "answer", "ANSWER_TEXT_MISMATCH", "answer",
                             "The delivered text does not match the checked claim records.")

    def source_report(self, snapshot: Snapshot) -> AnswerContract:
        claims = tuple(AnswerClaim(
            f"Source {source.handle.source_id} reports:\n{source.text}",
            f"report:{source.handle.source_id}@{source.handle.version}", (),
            (f"source:{source.handle.source_id}@{source.handle.version}",), (), "SOURCE_REPORT_NOT_TRUTH")
            for source in snapshot.immutable_views.values())
        return AnswerContract("\n\n".join(claim.text for claim in claims), claims,
                              "SOURCE_VERSION_VERIFIED", "NOT_SEMANTICALLY_CERTIFIED")

    def offline_reply(self, response: str) -> AnswerContract:
        claim = AnswerClaim(response, "offline-model-response", (), (), (), "UNVERIFIED_OFFLINE_FIXTURE")
        return AnswerContract(response, (claim,), "VISIBLE_RETURN_VERIFIED", "OFFLINE_FIXTURE_ONLY")

    def compact_claim(self, result):
        """Deterministic verified projection; full proof/model stays in the store."""
        from hcl.kernel.execution import ProjectedResultField
        checked = self._claim(result)
        projections = []
        value = result.values
        if result.kind == "CONDITIONAL_MECHANISM_DISCOVERY":
            text = checked.text
            names = ("programs", "initial_program_hashes", "pareto_programs", "prediction_classes", "edit_history", "observations",
                     "source_bindings", "context_bindings", "probe_bindings", "domain_issues", "frontier", "semantic_certified", "candidate_completeness", "posterior",
                     "scope", "factor_independence", "evidence_factor_ids", "equivalence_scope", "unmodeled_segments")
            for key, column in value["prediction_matrix"].items():
                keys = ("program_hash", "cells", "profile", "complexity", "work", "domain_conditions", "domain_limitations")
                keys = tuple(name for name in keys if name in column)
                projections.append(ProjectedResultField(result.result_id,"prediction_matrix",
                                   {name:column[name] for name in keys},(key,),keys))
            for i, probe in enumerate(value["distinguishing_observations"]):
                keys = ("probe_id", "query_id", "tested_members", "hypothetical", "partitions", "separated_pairs", "incomplete", "information_gain", "domain_limitations")
                keys = tuple(name for name in keys if name in probe)
                projections.append(ProjectedResultField(result.result_id,"distinguishing_observations",
                                   {name:probe[name] for name in keys},(str(i),),keys))
                for key, prediction in probe["predictions"].items():
                    selected = tuple(name for name in ("prediction","domain_conditions","domain_limitations") if name in prediction)
                    projections.append(ProjectedResultField(result.result_id,"distinguishing_observations",
                                       {name:prediction[name] for name in selected},
                                       (str(i),"predictions",key),selected))
            if "domain_issues" not in value:
                # A pre-fix inference has no synthesized qualification fields.
                # Bind the current explanation to its actual historical evidence
                # at every evaluated context, including incomplete probes.
                groups = [("prediction_matrix", (key,"actual_results"), column["actual_results"])
                          for key,column in value["prediction_matrix"].items()]
                groups.extend(("distinguishing_observations",(str(i),"evaluations",key,"actual_results"),evaluation["actual_results"])
                              for i,probe in enumerate(value["distinguishing_observations"])
                              for key,evaluation in probe["evaluations"].items())
                for field,path,records in groups:
                    for i,record in enumerate(records):
                        selected=("result_id","program_hash","context_hash","kind","issues","assumption_environments","source_versions")
                        projections.append(ProjectedResultField(result.result_id,field,
                                           {name:record[name] for name in selected},(*path,str(i)),selected))
                        for j,model in enumerate(record["values"].get("models",())):
                            selected=tuple(name for name in ("model_id","acceptance_scope","theory_consistency","excluded_circular_rules","strict_conflicts","inactive_assumptions","frontier") if name in model)
                            projections.append(ProjectedResultField(result.result_id,field,
                                               {name:model[name] for name in selected},(*path,str(i),"values","models",str(j)),selected))
                names = tuple(name for name in names if name in value)
        elif result.kind == "CONDITIONAL_ARGUMENT_ACCEPTANCE":
            text = checked.text
            names = ("semantic_certified", "candidate_completeness", "scope")
            for i, model in enumerate(value["models"]):
                keys=("model_id","source_id","frame_kind","assumptions","inactive_assumptions","unmodeled_segments",
                      "frontier","labels","grounded","strict_conflicts","theory_consistency",
                      "namespace_source_id","input_source_versions","source_bindings","source_records",
                      "acceptance_scope","excluded_circular_rules","iterations")
                projections.append(ProjectedResultField(result.result_id,"models",{key:model[key] for key in keys},(str(i),),keys))
                for j, query in enumerate(model["queries"]):
                    keys=tuple(query)
                    projections.append(ProjectedResultField(result.result_id,"models",dict(query),(str(i),"queries",str(j)),keys))
        elif result.kind == "CONDITIONAL_COGNITIVE_MODEL":
            text = checked.text
            names = ("semantic_certified", "candidate_completeness", "scope")
            for i, model in enumerate(value["models"]):
                keys = ("model_id", "source_id", "frame_kind", "assumptions", "inactive_assumptions", "unmodeled_segments", "frontier")
                projections.append(ProjectedResultField(result.result_id, "models", {key:model[key] for key in keys}, (str(i),), keys))
                selections = {
                    "beliefs": ("query_id", "at", "formula", "status", "possible_values", "assumptions"),
                    "shared_variables": ("variable_id", "actor", "at", "remaining_states", "remaining_world_ids", "status", "assumptions"),
                    "plans": ("plan_id", "actor", "at", "belief_variable_id", "status", "q", "best_actions", "belief", "subjective_feasibility", "world_feasibility", "actual_possible_states", "planning_states", "state_bindings", "belief_world_bindings", "actual_world_bindings", "policy"),
                    "causal": ("query_id", "status", "possible_values", "observations", "interventions", "scope", "identification"),
                }
                for field, selected in selections.items():
                    for j, row in enumerate(model[field]):
                        keys = tuple(key for key in selected if key in row)
                        projections.append(ProjectedResultField(result.result_id, "models", {key:row[key] for key in keys}, (str(i), field, str(j)), keys))
        elif result.kind == "CONDITIONAL_FOL":
            descriptions = []
            for i, row in enumerate(value["readings"]):
                descriptions.append(row["id"] + " [" + row["frame_kind"] + "]: " + row["query_reading"]
                                    + "; " + row["status"] + "; label=" + str(row["label"]))
                keys = ("id", "frame_kind", "query_reading", "status", "label")
                projections.append(ProjectedResultField(result.result_id, "readings", {key: row[key] for key in keys},
                                                        (str(i),), keys))
            text = ("Supplied formal readings: " + value["status"] + "; conditional label=" + str(value["label"])
                    + ". " + "; ".join(descriptions) + ". Semantic alignment and completeness remain unverified.")
            names = ("status", "label", "semantic_certified", "candidate_completeness")
        elif result.kind == "CONDITIONAL_REVISION":
            positive = value["query"]["positive"]
            atom = value["claim_metadata"][positive]
            projections.append(ProjectedResultField(result.result_id, "claim_metadata", atom, (positive,)))
            text = ("Conditional scoped program [" + atom["frame_kind"] + "] at " + atom["at_point"]
                    + " for perspective " + atom["perspective_id"] + ": " + atom["predicate"]
                    + "(" + ", ".join(atom["arguments"]) + "), positive=" + str(value["support_bits"]["positive_support"])
                    + ", negative=" + str(value["support_bits"]["negative_support"])
                    + ", frontier=" + str(value["support_bits"]["frontier_unexplored"])
                    + "; recorded cutoff=" + str(value["known_at"])
                    + ". Supplied-model support is not world or private mental truth; missing support is not disproof.")
            names = ("support_bits", "query", "known_at", "semantic_certified", "candidate_completeness")
        else:
            text = checked.text
            names = tuple(field.field for field in checked.used_result_fields)
        if "local_model" in value:
            names = (*names, "local_model")
            qualifications = value["local_model"]
            if qualifications["fit_residuals"] or qualifications["unmodeled_observations"]:
                text += (" Model fit residuals and unmodeled observations remain unresolved: "
                         + str(len(qualifications["fit_residuals"])) + "/" + str(len(qualifications["unmodeled_observations"])) + ".")
        return AnswerClaim(text, checked.claim_id,
                           tuple(ResultField(result.result_id, name, value[name]) for name in names) + tuple(projections),
                           checked.support_envs, checked.counterevidence, checked.epistemic_status)

    def validate_compact(self, contract, results):
        from hcl.kernel.execution import ProjectedResultField
        expected = tuple(self.compact_claim(result) for result in results)
        if contract.claims != expected or contract.answer != "\n\n".join(claim.text for claim in expected):
            raise HCLFailure("FAILED", "answer", "COMPACT_RESULT_MISMATCH", "claim_records",
                             "The compact delivery differs from verified actual result fields.")
        by_id = {result.result_id: result for result in results}
        for claim in contract.claims:
            for used in claim.used_result_fields:
                actual = by_id[used.result_id].values[used.field]
                if type(used) is ProjectedResultField:
                    for key in used.path:
                        actual = actual[int(key)] if isinstance(actual, tuple) else actual[key]
                    if used.selection:
                        from hcl.kernel.types import freeze
                        actual = freeze({key: actual[key] for key in used.selection})
                if actual != used.value or type(actual) is not type(used.value):
                    raise HCLFailure("FAILED", "answer", "PROJECTED_FIELD_MISMATCH", "claim_records",
                                     "The projected field is not an exact value of the accepted computation.")
