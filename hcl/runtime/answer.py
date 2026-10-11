"""Deterministic first-slice claim assembly from actual computed values."""
from __future__ import annotations

import json

from hcl.kernel.types import (
    AnswerClaim, AnswerContract, FORMAL_SCOPE, HCLFailure, InferenceResult,
    ResultField, Snapshot, thaw,
)


class AnswerAssembler:
    def _claim(self, result: InferenceResult) -> AnswerClaim:
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

    def build(self, snapshot: Snapshot, issues, accepted_results: tuple[InferenceResult, ...]) -> AnswerContract:
        claims = tuple(self._claim(result) for result in accepted_results)
        contract = AnswerContract("\n\n".join(claim.text for claim in claims), tuple(claims),
                                  "RESULT_FIELDS_VERIFIED", "EXPLICIT_FORMAL_INPUT_ONLY")
        self.validate(contract, accepted_results)
        return contract

    def validate(self, contract: AnswerContract, results: tuple[InferenceResult, ...]) -> None:
        by_id = {result.result_id: result for result in results}
        for claim in contract.claims:
            for used in claim.used_result_fields:
                actual = by_id.get(used.result_id)
                if (actual is None or used.field not in actual.values
                        or type(actual.values[used.field]) is not type(used.value)
                        or json.dumps(thaw(actual.values[used.field]), sort_keys=True)
                        != json.dumps(thaw(used.value), sort_keys=True)):
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
