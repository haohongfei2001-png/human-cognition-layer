"""Minimal end-to-end runtime for HCL v0.4."""

from __future__ import annotations

import json
from typing import Protocol

from .model import (
    CheckerResult,
    EventRecord,
    IngestResult,
    QueryContext,
    ResponseResult,
    SemanticPatch,
)
from .schema import SchemaValidationError
from .semantic import (
    SemanticBackend,
    patch_from_mapping,
    patch_to_mapping,
    propose_patch,
    propose_patch_with_diagnostics,
    repair_patch_for_invariant,
)
from .store import CognitionStore


class ResponseBackend(SemanticBackend, Protocol):
    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> str:
        ...


ANSWER_SYSTEM = """You are the response stage of HCL v0.4.

Use the supplied QueryContext as a fallible, evidence-linked cognitive model.
Raw evidence outranks a conflicting derived assertion.
Do not infer that receiving a proposition means accepting or believing it.
Do not infer that a source assertion is world truth.
Preserve underdetermination when the evidence does not decide the latent state.
A supported BELIEF_ESTIMATE is the current best estimate of that person's belief
until later evidence changes its applicability. SOURCE_ASSERTION or
INFORMATION_EXPOSURE alone does not supersede an existing supported belief.
Ordinary exposure also does not imply a new belief. However, when a prior
BELIEF_ESTIMATE is marked projection_status=STALE_AFTER_REVISION_EXPOSURE, use it
only as historical evidence: the agent received a proposition that explicitly
revised the old one, but receipt does not establish acceptance or rejection, so
the current stance remains unresolved until later stance evidence exists.
When multiple BELIEF_ESTIMATE records exist for the same issue, prefer the
latest evidence-supported stance while preserving explicit uncertainty where
the evidence genuinely does not decide.
Answer the user's actual query concisely.
Do not mention HCL internals unless the user asks.
"""


CHECK_SYSTEM = """You are the source-grounded checker for HCL v0.4.

Check the exact candidate answer against the supplied QueryContext.

The derived cognition state is NOT unconditionally authoritative. Use its source
evidence and provenance to detect a state-grounding problem as well as an answer
problem.

Return JSON only:
{
  "status": "PASS|REVISE",
  "violations": ["..."],
  "reason": "..."
}

PASS is valid only when violations is empty.
"""


REVISION_SYSTEM = """Revise the candidate answer using the supplied QueryContext
and checker findings. Raw evidence outranks a conflicting derived assertion.
Return only the revised user-facing answer.
"""


def _merge_repair_with_preserved(
    event: EventRecord,
    rejected: SemanticPatch,
    repaired: SemanticPatch,
    preserved_assertions,
    *,
    semantic_version: str,
) -> SemanticPatch:
    """Preserve independently valid assertions across bounded repair."""
    proposition_map: dict[str, dict] = {}
    for payload in (
        patch_to_mapping(rejected).get("propositions", []),
        patch_to_mapping(repaired).get("propositions", []),
    ):
        for item in payload:
            proposition_map[item["proposition_id"]] = item

    assertion_map: dict[str, dict] = {
        item["assertion_id"]: item
        for item in patch_to_mapping(repaired).get("assertions", [])
    }
    preserved_ids = {a.assertion_id for a in preserved_assertions}
    rejected_map = {
        item["assertion_id"]: item
        for item in patch_to_mapping(rejected).get("assertions", [])
    }
    for assertion_id in preserved_ids:
        assertion_map[assertion_id] = rejected_map[assertion_id]

    payload = {
        "propositions": list(proposition_map.values()),
        "assertions": list(assertion_map.values()),
    }
    return patch_from_mapping(
        event,
        payload,
        semantic_version=semantic_version,
    )


class HCLV04Runtime:
    def __init__(self, store: CognitionStore | None = None) -> None:
        self.store = store or CognitionStore()

    def append_event(self, event: EventRecord):
        return self.store.append_event(event)

    def propose_patch(
        self,
        event_id: str,
        backend: SemanticBackend,
        *,
        semantic_version: str = "v04.1",
    ) -> SemanticPatch:
        event = self.store.get_event(event_id)
        return propose_patch(
            event,
            backend,
            known_propositions=self.store.proposition_catalog(),
            semantic_version=semantic_version,
        )

    def apply_patch(self, expected_version: int, patch: SemanticPatch):
        return self.store.apply_patch(expected_version, patch)

    def ingest_event(
        self,
        event: EventRecord,
        backend: SemanticBackend,
        *,
        semantic_version: str = "v04.1",
    ) -> IngestResult:
        event_receipt = self.append_event(event)
        stored_event = self.store.get_event(event.event_id)
        patch, proposal_repairs, proposal_reason = propose_patch_with_diagnostics(
            stored_event,
            backend,
            known_propositions=self.store.proposition_catalog(),
            semantic_version=semantic_version,
        )
        rejected_patch = None
        repair_reason = proposal_reason
        repair_count = proposal_repairs

        try:
            state_receipt = self.apply_patch(self.store.state_version, patch)
        except SchemaValidationError as exc:
            rejected_patch = patch
            store_repair_reason = str(exc)
            repair_reason = (
                f"{repair_reason}; store invariant repair: {store_repair_reason}"
                if repair_reason
                else store_repair_reason
            )
            preserved_assertions = self.store.independently_valid_assertions(patch)
            repaired = repair_patch_for_invariant(
                stored_event,
                patch,
                store_repair_reason,
                backend,
                semantic_version=semantic_version,
            )
            patch = _merge_repair_with_preserved(
                stored_event,
                rejected_patch,
                repaired,
                preserved_assertions,
                semantic_version=semantic_version,
            )
            repair_count += 1
            state_receipt = self.apply_patch(self.store.state_version, patch)

        return IngestResult(
            event_receipt=event_receipt,
            state_receipt=state_receipt,
            committed_patch=patch,
            rejected_patch=rejected_patch,
            semantic_repair_count=repair_count,
            repair_reason=repair_reason,
        )

    def build_view(
        self,
        viewer: str | None,
        event_time: str | None,
        knowledge_cutoff: str | None,
        query: str,
    ) -> QueryContext:
        return self.store.build_view(
            viewer,
            event_time,
            knowledge_cutoff,
            query,
        )

    def invalidate(self, affected_records, reason: str):
        return self.store.invalidate(affected_records, reason)

    def rebuild(self, scope: str = "all", checkpoint: int | None = None):
        return self.store.rebuild(scope=scope, checkpoint=checkpoint)

    def _parse_check(self, raw: str) -> CheckerResult:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return CheckerResult(
                status="REVISE",
                violations=("CHECKER_INVALID_JSON",),
                reason="checker returned invalid JSON",
            )
        status = str(payload.get("status", "REVISE")).upper()
        violations_raw = payload.get("violations") or []
        if not isinstance(violations_raw, list):
            violations_raw = ["CHECKER_INVALID_VIOLATIONS"]
        violations = tuple(str(v) for v in violations_raw if str(v).strip())
        reason = str(payload.get("reason", ""))

        if status not in {"PASS", "REVISE"}:
            return CheckerResult(
                status="REVISE",
                violations=("CHECKER_INVALID_STATUS",) + violations,
                reason=reason,
            )
        if status == "PASS" and violations:
            status = "REVISE"
        return CheckerResult(status=status, violations=violations, reason=reason)

    def _check(
        self,
        context: QueryContext,
        query: str,
        answer: str,
        backend: ResponseBackend,
    ) -> CheckerResult:
        raw = backend.complete_json(
            [
                {"role": "system", "content": CHECK_SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "query": query,
                            "query_context": context.as_dict(),
                            "candidate_answer": answer,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                },
            ],
            max_tokens=1024,
            temperature=0.0,
        )
        return self._parse_check(raw)

    def respond(
        self,
        query: str,
        backend: ResponseBackend,
        *,
        viewer: str | None = None,
        event_time: str | None = None,
        knowledge_cutoff: str | None = None,
    ) -> ResponseResult:
        context = self.build_view(
            viewer,
            event_time,
            knowledge_cutoff,
            query,
        )
        draft = backend.complete(
            [
                {"role": "system", "content": ANSWER_SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "query": query,
                            "query_context": context.as_dict(),
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                },
            ],
            max_tokens=2048,
            temperature=0.0,
        ).strip()

        check = self._check(context, query, draft, backend)
        if check.passed:
            return ResponseResult(
                answer=draft,
                check=check,
                verified=True,
                state_version=context.state_version,
                answer_version=1,
            )

        revision = backend.complete(
            [
                {"role": "system", "content": REVISION_SYSTEM},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "query": query,
                            "query_context": context.as_dict(),
                            "candidate_answer": draft,
                            "checker": {
                                "status": check.status,
                                "violations": list(check.violations),
                                "reason": check.reason,
                            },
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                },
            ],
            max_tokens=2048,
            temperature=0.0,
        ).strip()

        final_check = self._check(context, query, revision, backend)
        return ResponseResult(
            answer=revision,
            check=final_check,
            verified=final_check.passed,
            state_version=context.state_version,
            answer_version=2,
        )


__all__ = [
    "ANSWER_SYSTEM",
    "CHECK_SYSTEM",
    "HCLV04Runtime",
    "REVISION_SYSTEM",
]
