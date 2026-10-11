"""Source-bound adapter to the existing pure finite-model checker.

This is explicit formal input, not natural-language semantic compilation. No
Z3, network, store writer, model callback or evaluation scorer is reachable.
"""
from __future__ import annotations

from hashlib import sha256
import json

from hcl import quantified_logic
from hcl.kernel.types import (
    BudgetSlice, Delta, FORMAL_SCOPE, HCLFailure, InferenceResult, Issue,
    OpResult, Snapshot, thaw,
)


class FiniteLogicOperator:
    operation_id = "logic.check_interpretation"
    version = "1"

    def run(self, snapshot: Snapshot, issue: Issue, allowance: BudgetSlice) -> OpResult:
        source = snapshot.immutable_views.get(issue.source_id)
        if source is None:
            raise HCLFailure("DENIED", "operator", "SOURCE_OUTSIDE_SNAPSHOT",
                             "issue.source_id", "The operation's source is not authorized.")
        problem = source.formal_problem
        if problem is None or problem.representation != "legacy-formal-v1":
            raise HCLFailure("NEEDS_EVIDENCE", "operator", "FORMAL_INPUT_REQUIRED",
                             "formal_problem", "An explicit formal interpretation is required.")
        formulas = (*problem.premises, problem.conclusion)
        if any(not isinstance(formula, str) for formula in formulas):
            raise HCLFailure("INVALID_REQUEST", "operator", "INVALID_FORMULA",
                             "formal_problem", "Formulas must use the bounded formal grammar.")
        if (len(problem.premises) > min(allowance.max_premises, 32)
                or len(formulas) > min(allowance.max_local_evaluations, 33)
                or sum(map(len, formulas)) > min(allowance.max_formula_chars, 16000)):
            raise HCLFailure("BUDGET_EXHAUSTED", "operator", "LOCAL_BUDGET_EXHAUSTED",
                             "budget", "The formal task exceeds its local computation allowance.")
        # The old checker expects ordinary dict/list values. Only private copies
        # cross this adapter; the shared Snapshot remains recursively immutable.
        try:
            premises = [quantified_logic.parse(item) for item in problem.premises]
            conclusion = quantified_logic.parse(problem.conclusion)
            values = quantified_logic.check_countermodel(
                premises, conclusion, thaw(problem.interpretation))
        except quantified_logic.FormulaError as error:
            if str(error) == "evaluation work limit":
                raise HCLFailure("BUDGET_EXHAUSTED", "operator", "EVALUATION_FUEL_EXHAUSTED",
                                 "formal_problem", "A valid finite formula exhausted evaluator fuel.",
                                 resource_usage={"local_evaluation_batches_started": 1,
                                                 "local_evaluation_fuel_exhausted": True}) from None
            raise HCLFailure("INVALID_REQUEST", "operator", "INVALID_FORMAL_INTERPRETATION",
                             "formal_problem", "The formal grammar, signature or finite model is invalid.") from None
        environment = f"source:{source.handle.source_id}@{source.handle.version}:explicit-model"
        result_digest = sha256(json.dumps({
            "session": snapshot.session_id, "revision": snapshot.revision,
            "source": source.handle.source_id, "version": source.handle.version,
            "issue": issue.issue_id, "values": values,
        }, sort_keys=True).encode()).hexdigest()[:24]
        result = InferenceResult(
            result_id=f"finite:{result_digest}", kind="EXACT_MODEL", values=values,
            assumption_environments=(environment,),
            premise_ids=tuple(f"{environment}:premise:{i}" for i in range(len(premises))),
            counterevidence_ids=((f"{environment}:conclusion",) if values["is_countermodel"] else ()),
            rule_version=snapshot.rule_version, coverage=FORMAL_SCOPE,
        )
        read_set = {source.handle.source_id: source.handle.version}
        delta = Delta(snapshot.session_id, snapshot.principal, snapshot.revision,
                      snapshot.access_epoch, snapshot.rule_version, read_set, (result,))
        return OpResult(self.operation_id, self.version, read_set, ("append_inference",),
                        (result.result_id,), (), {"local_evaluations": len(formulas)}, (), delta)
