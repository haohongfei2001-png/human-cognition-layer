"""One durable reading fragment per ordinary graph scheduling step.

This coordinator supplies no literary interpretations. It uses the existing task
lease, exact call reservations, UNKNOWN holds and governed response objects.
The registered compiler/composer remains responsible for semantic candidates.
"""

from hashlib import sha256

from hcl.kernel.types import HCLFailure, freeze, thaw
from hcl.models.gateway import AuthorizedContext, CallSpec
from hcl.runtime.execution_ledger import stopped
from hcl.runtime.reading_fragments import (
    call_identity,
    materialize,
    validated_partition,
)

PROTOCOL = "reading-coordinator-1"


def initial_state(plan):
    return dict(
        protocol=PROTOCOL,
        plan=freeze(plan),
        ordinal=0,
        records=[
            dict(
                state="PENDING",
                attempt=0,
                feedback=None,
                call_id=None,
                response_hash=None,
                candidate_sha256=None,
            )
            for _ in plan["fragments"]
        ],
    )


def copy_state(value):
    # Preserve the immutable partition identity. Recopying its whole source
    # descriptor graph once per fragment would reintroduce quadratic work.
    result = {key: thaw(item) for key, item in value.items() if key != "plan"}
    result["plan"] = value["plan"]
    return result


class ReadingCoordinator:
    def __init__(self, runner, validate_fragment):
        self.runner = runner
        self.validate_fragment = validate_fragment
        self._cached = None

    def _selected(self, request, node):
        state = node["reading"]
        if state["protocol"] != PROTOCOL or len(state["records"]) != len(
            state["plan"]["fragments"]
        ):
            raise stopped("READING_CHECKPOINT_CONTRACT", "FAILED", "storage")
        snapshot = self.runner.snapshots[node["goal"].issue_id]
        cached = self._cached
        if (
            cached is None
            or cached[0] is not snapshot
            or cached[1] is not state["plan"]
            or cached[2] != request.question
        ):
            cached = (
                snapshot,
                state["plan"],
                request.question,
                validated_partition(snapshot, request.question, state["plan"]),
            )
            self._cached = cached
        return snapshot, cached[3]

    async def advance(self, request, node):
        """Return True only when all fragments are durably validated.

        The caller has already ticked this graph node. False requires leaving it
        PENDING, so the next fragment incurs another shared execution step.
        """
        runner = self.runner
        snapshot, selected = self._selected(request, node)
        runner.store.validate_snapshot(snapshot)
        state = copy_state(node["reading"])
        ordinal = state["ordinal"]
        if type(ordinal) is not int or not 0 <= ordinal <= len(state["records"]):
            raise stopped("READING_CHECKPOINT_CONTRACT", "FAILED", "storage")
        if ordinal == len(state["records"]):
            return True
        record = state["records"][ordinal]
        if record["state"] != "PENDING":
            raise stopped("READING_CHECKPOINT_CONTRACT", "FAILED", "storage")
        chunk, wire = materialize(
            runner.context,
            snapshot,
            request.question,
            selected,
            ordinal,
            feedback=record["feedback"],
        )
        call_id = call_identity(
            node["goal"].issue_id, state["plan"], ordinal, record["attempt"]
        )
        node.update(
            call_id=call_id,
            call_snapshot=snapshot,
            wire_hash=sha256(wire.encode()).hexdigest(),
        )
        record["call_id"] = call_id
        node["reading"] = state
        runner._save()
        row = runner.ledger.tasks.call(runner.lease, call_id)
        if row is not None:
            if row["state"] != "RETURNED" or row["response_hash"] is None:
                raise stopped(
                    "PRIOR_READING_CALL_NOT_REUSABLE",
                    "SEND_UNKNOWN" if row["attempted"] is None else "FAILED",
                    "model",
                )
            if runner.store._get_object(row["request_hash"]) != wire:
                raise stopped("READING_CALL_CONTEXT_CHANGED", "DENIED", "model")
            raw = runner.store._get_object(row["response_hash"])
        else:
            response = await runner.gateway.generate(
                AuthorizedContext(
                    snapshot,
                    request.question,
                    chunk.purpose,
                    runner.engine._semantic.profile,
                    chunk,
                ),
                CallSpec(request.request_id, request.budget, runner.lease, call_id),
            )
            raw = response.visible_text
            row = runner.ledger.tasks.call(runner.lease, call_id)
        if type(raw) is not str or not raw.strip():
            raise stopped("INVALID_MODEL_RETURN", "FAILED", "model")
        try:
            size = len(raw.encode())
        except UnicodeEncodeError:
            raise stopped("INVALID_MODEL_ENCODING", "FAILED", "model") from None
        caps = [
            request.budget.max_output_bytes,
            request.budget.max_visible_output_tokens,
        ]
        if runner.gateway.capabilities.output_tokens is not None:
            caps.append(runner.gateway.capabilities.output_tokens)
        if size > min(caps):
            raise stopped("READING_OUTPUT_CAPACITY", "BUDGET_EXHAUSTED", "model")
        runner.store.validate_snapshot(snapshot)
        # Retain the failed current return for field-specific feedback only.
        # Successful returns are not duplicated into the execution checkpoint.
        node["raw_return"] = raw
        try:
            self.validate_fragment(snapshot, chunk, raw, request.budget)
        except HCLFailure as error:
            runner.ledger.tasks.transition(
                runner.lease,
                call_id,
                "RETURNED",
                "RETURNED",
                validation_code="READING_COMPILE_REJECTED:" + error.diagnostic.code,
            )
            raise
        runner.ledger.tasks.transition(
            runner.lease,
            call_id,
            "RETURNED",
            "RETURNED",
            validation_code="READING_FRAGMENT_COMPILED",
        )
        record.update(
            state="COMPILED",
            response_hash=row["response_hash"],
            candidate_sha256=sha256(raw.encode()).hexdigest(),
        )
        state["ordinal"] += 1
        node["reading"] = state
        node.pop("raw_return", None)
        runner._save()
        runner.store._checkpoint("reading_fragment_compiled")
        return state["ordinal"] == len(state["records"])

    def candidates(self, request, node):
        runner = self.runner
        snapshot, selected = self._selected(request, node)
        runner.store.validate_snapshot(snapshot)
        state = node["reading"]
        if state["ordinal"] != len(state["records"]):
            raise stopped(
                "READING_INCOMPLETE", "NEEDS_EVIDENCE", "literature_composition"
            )
        result = []
        for ordinal, record in enumerate(state["records"]):
            if record["state"] != "COMPILED":
                raise stopped("READING_CHECKPOINT_CONTRACT", "FAILED", "storage")
            chunk, wire = materialize(
                runner.context,
                snapshot,
                request.question,
                selected,
                ordinal,
                feedback=record["feedback"],
            )
            expected_id = call_identity(
                node["goal"].issue_id, state["plan"], ordinal, record["attempt"]
            )
            row = runner.ledger.tasks.call(runner.lease, expected_id)
            if (
                row is None
                or row["state"] != "RETURNED"
                or record["call_id"] != expected_id
                or row["response_hash"] != record["response_hash"]
                or runner.store._get_object(row["request_hash"]) != wire
            ):
                raise stopped("READING_CALL_CONTEXT_CHANGED", "DENIED", "model")
            raw = runner.store._get_object(row["response_hash"])
            if (
                type(raw) is not str
                or sha256(raw.encode()).hexdigest() != record["candidate_sha256"]
            ):
                raise stopped("READING_RETURN_CHANGED", "FAILED", "storage")
            result.append((chunk, raw))
        runner.store.validate_snapshot(snapshot)
        return tuple(result)

    @staticmethod
    def repair(node, obligation):
        """The engine must first charge its one shared feedback allowance."""
        state = copy_state(node["reading"])
        if state["ordinal"] >= len(state["records"]):
            return False  # A global composition error is not a final-fragment fault.
        record = state["records"][state["ordinal"]]
        record.update(
            attempt=record["attempt"] + 1,
            state="PENDING",
            feedback=dict(obligation),
            call_id=None,
            response_hash=None,
            candidate_sha256=None,
        )
        node["reading"] = state
        return True
