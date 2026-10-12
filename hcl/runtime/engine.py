"""The single run/stream engine with optional S1.2 persistence and recovery.

Legacy public entrypoints are retained unchanged until their planned migration;
new requests never call their provider callbacks. No paid/live path exists here.
"""
from __future__ import annotations

from dataclasses import fields
import asyncio

from hcl.kernel.types import (
    BudgetSlice, DeliveryEvent, HCLFailure, Issue, Principal, SCHEMA_VERSION,
    SourceHandle, TaskRequest, TaskResult,
)
from hcl.memory.store import StateStore
from hcl.models.gateway import AuthorizedContext, CallSpec, ModelGateway
from hcl.operators.logic import FiniteLogicOperator
from hcl.runtime.answer import AnswerAssembler


class Engine:
    def __init__(self, store: StateStore, principal: Principal, gateway: ModelGateway | None = None,
                 *, semantic_profile=None):
        self.store = store
        self.principal = principal  # Authenticated by the embedding host, not a source claim.
        if gateway is not None and gateway._store is not store:
            raise ValueError("The engine and gateway must share one state store")
        self.gateway = gateway if gateway is not None else ModelGateway(store)
        self._logic = FiniteLogicOperator()
        from hcl.operators.semantic_logic import ReadingLogicOperator
        from hcl.semantics.compiler import SemanticCompiler
        from hcl.semantics.frames import SemanticProfile
        if semantic_profile is not None and type(semantic_profile) is not SemanticProfile:
            raise ValueError("typed semantic execution profile required")
        self._semantic = SemanticCompiler(semantic_profile)
        self._reading_logic = ReadingLogicOperator(semantic_profile)
        from hcl.semantics.revision import RevisionCompiler
        from hcl.operators.revision import RevisionOperator
        self._revision_compiler = RevisionCompiler()
        self._revision_operator = RevisionOperator()
        self._assembler = AnswerAssembler()
        self._requests: set[tuple[str, str]] = set()
        from hcl.runtime.budget import TaskBudgetLedger
        self._ledger = TaskBudgetLedger(store) if store.durable else None

    def _admit(self, request: TaskRequest) -> None:
        if request.principal != self.principal:
            raise HCLFailure(
                "DENIED",
                "admission",
                "PRINCIPAL_MISMATCH",
                "principal",
                "The request principal does not match the authenticated host identity.",
            )
        for name in ("request_id", "session_id", "question"):
            value = getattr(request, name)
            if not isinstance(value, str) or not value.strip():
                raise HCLFailure(
                    "INVALID_REQUEST",
                    "admission",
                    "REQUIRED_FIELD",
                    name,
                    "A nonempty request field is required.",
                )
            try:
                value.encode("utf-8")
            except UnicodeEncodeError:
                raise HCLFailure(
                    "INVALID_REQUEST",
                    "admission",
                    "INVALID_TEXT_ENCODING",
                    name,
                    "The request field must be valid Unicode text.",
                ) from None
        if request.output_contract != "natural-language-with-claims-v1" or request.epistemic_profile not in (
            "balanced",
            "deep",
        ):
            raise HCLFailure(
                "INVALID_REQUEST",
                "admission",
                "UNSUPPORTED_CONTRACT",
                "output_contract",
                "The requested contract or epistemic profile is unsupported.",
            )
        if not isinstance(request.budget, BudgetSlice) or any(
            type(getattr(request.budget, item.name)) is not int or getattr(request.budget, item.name) < 0
            for item in fields(BudgetSlice)
        ):
            raise HCLFailure(
                "INVALID_REQUEST",
                "admission",
                "INVALID_BUDGET",
                "budget",
                "Budget limits must be nonnegative integers.",
            )
        if any(
            not isinstance(handle, SourceHandle)
            or not isinstance(handle.source_id, str)
            or not handle.source_id
            or type(handle.version) is not int
            or handle.version < 1
            for handle in request.source_handles
        ):
            raise HCLFailure(
                "INVALID_REQUEST",
                "admission",
                "INVALID_HANDLE",
                "source_handles",
                "Versioned source handles are required.",
            )
        if len({handle.source_id for handle in request.source_handles}) != len(request.source_handles):
            raise HCLFailure(
                "INVALID_REQUEST",
                "admission",
                "DUPLICATE_SOURCE",
                "source_handles",
                "A source was requested more than once.",
            )
        if not isinstance(request.issue, Issue):
            raise HCLFailure(
                "INVALID_REQUEST", "admission", "INVALID_ISSUE", "issue", "A typed issue is required."
            )
        if request.issue.kind not in (
            "logic.check_interpretation",
            "source.report",
            "model.respond",
            "logic.compare_semantic_readings",
            "revision.evaluate",
        ):
            raise HCLFailure(
                "INVALID_REQUEST",
                "admission",
                "UNSUPPORTED_ISSUE",
                "issue.kind",
                "This issue is outside the implemented execution slice.",
            )
        if request.issue.kind == "revision.evaluate":
            from hcl.kernel.dependencies import RevisionIssue

            if (
                type(request.issue) is not RevisionIssue
                or not self.store.durable
                or (
                    request.issue.known_at is not None
                    and (type(request.issue.known_at) is not int or request.issue.known_at < 0)
                )
            ):
                raise HCLFailure(
                    "INVALID_REQUEST",
                    "admission",
                    "INVALID_REVISION_ISSUE",
                    "issue",
                    "Revision requires a durable store and an explicitly bound optional recorded cutoff.",
                )
        if not isinstance(request.issue.issue_id, str) or not request.issue.issue_id:
            raise HCLFailure(
                "INVALID_REQUEST",
                "admission",
                "INVALID_ISSUE",
                "issue.issue_id",
                "A nonempty issue ID is required.",
            )
        if request.issue.source_id is not None and not isinstance(request.issue.source_id, str):
            raise HCLFailure(
                "INVALID_REQUEST",
                "admission",
                "INVALID_ISSUE_SOURCE",
                "issue.source_id",
                "An issue source ID must be a string.",
            )
        try:
            for value in (
                request.issue.issue_id,
                request.issue.source_id,
                *(handle.source_id for handle in request.source_handles),
            ):
                if value is not None:
                    value.encode("utf-8")
        except UnicodeEncodeError:
            raise HCLFailure(
                "INVALID_REQUEST",
                "admission",
                "INVALID_TEXT_ENCODING",
                "source_handles/issue",
                "Source and issue identifiers must be valid Unicode text.",
            ) from None
        key = (request.session_id, request.request_id)
        if self._ledger is None and key in self._requests:
            raise HCLFailure(
                "FAILED",
                "admission",
                "REQUEST_ALREADY_BOUND",
                "request_id",
                "This request is already bound; it cannot silently execute again.",
            )
        if self._ledger is None:
            self._requests.add(key)

    async def run(self, request: TaskRequest) -> TaskResult:
        if not isinstance(request, TaskRequest):
            raise TypeError("TaskRequest required")
        usage = {"provider_calls": 0, "provider_spend_usd": "0", "mock_calls": 0, "local_evaluations": 0}
        receipt = {
            "schema": SCHEMA_VERSION,
            "engine": "unified-engine-v1",
            "request_id": request.request_id if type(request.request_id) is str else None,
            "store_durable": self.store.durable,
            "evidence_level": "INTEGRATED_OFFLINE_SLICE_ONLY",
        }
        failure_receipt = dict(receipt)
        owns_current_call = False
        committed_revision = None
        lease = None
        snapshot = None
        read_set = {}
        try:
            self._admit(request)
            if self._ledger is not None:
                replay = self._ledger.resume(request)
                if replay is not None:
                    self._ledger.validate_cached_delivery(request)
                    return replay
            snapshot = (self.store.revision_snapshot(request.session_id,self.principal,request.source_handles,known_at=request.issue.known_at)
                        if request.issue.kind=='revision.evaluate' else self.store.snapshot(request.session_id, self.principal, request.source_handles))
            if self._ledger is not None:
                lease, replay = self._ledger.bind(request, snapshot)
                if replay is not None:
                    self._ledger.validate_cached_delivery(request)
                    return replay
            results = ()
            unresolved = ()
            operation_ids = ()
            read_set = snapshot.source_versions
            state_revision = snapshot.revision
            if request.issue.kind == "logic.check_interpretation":
                operation = self._logic.run(snapshot, request.issue, request.budget)
                usage.update(operation.resource_usage)
                results = operation.candidate_delta.new_inferences
                contract = self._assembler.build(snapshot, (request.issue,), results)
                read_set = operation.read_set
                committed = self.store.commit(snapshot.revision, read_set, snapshot.access_epoch,
                                              operation.candidate_delta)
                if committed.result_ids != operation.result_refs:
                    raise HCLFailure("FAILED", "commit", "COMMIT_RESULT_MISMATCH", "result_refs",
                                     "The store did not commit the proposed computation identities.")
                state_revision = committed.revision
                committed_revision = committed.revision
                operation_ids = (operation.operation_id,)
            elif request.issue.kind == "logic.compare_semantic_readings":
                from hcl.semantics.segments import segment_snapshot
                segments = segment_snapshot(snapshot, request.question)
                owns_current_call = self._ledger is None and self.gateway.call_state(
                    self.principal, request.session_id, request.request_id) is None
                response = await self.gateway.generate(AuthorizedContext(snapshot, request.question, "semantic_compile",
                                                                                self._semantic.profile),
                                                       CallSpec(request.request_id, request.budget, lease))
                usage.update(mock_calls=1, request_bytes=response.request_bytes, output_bytes=response.output_bytes)
                if response.resource_usage is not None:
                    usage.update(response.resource_usage)
                forest = self._semantic.compile(snapshot, segments, response.visible_text, request.budget)
                operation = await asyncio.to_thread(self._reading_logic.run, snapshot, request.issue, request.budget, forest)
                usage.update(operation.resource_usage)
                results = operation.candidate_delta.new_inferences
                contract = self._assembler.build(snapshot, (request.issue,), results)
                read_set = operation.read_set
                committed = self.store.commit(snapshot.revision, read_set, snapshot.access_epoch,
                                              operation.candidate_delta)
                if committed.result_ids != operation.result_refs:
                    raise HCLFailure("FAILED", "commit", "COMMIT_RESULT_MISMATCH", "result_refs",
                                     "The store did not commit the proposed computation identities.")
                state_revision = committed_revision = committed.revision
                unresolved = operation.issues
                operation_ids = (operation.operation_id,)
            elif request.issue.kind == "revision.evaluate":
                from hashlib import sha256
                from hcl.kernel.dependencies import QueryDelta, IndexQuery
                from hcl.kernel.types import Delta, InferenceResult
                from hcl.memory import codec
                from hcl.semantics.segments import segment_snapshot

                response = await self.gateway.generate(
                    AuthorizedContext(snapshot, request.question, "revision_compile"),
                    CallSpec(request.request_id, request.budget, lease),
                )
                usage.update(
                    mock_calls=1, request_bytes=response.request_bytes, output_bytes=response.output_bytes
                )
                if response.resource_usage is not None:
                    usage.update(response.resource_usage)
                indexes, query = self._revision_compiler.compile(
                    snapshot,
                    segment_snapshot(snapshot, request.question),
                    response.visible_text,
                    request.budget,
                )
                # Each proposal retains ALL source inputs actually exposed in its
                # extraction call. A span check alone cannot prove that model text
                # did not copy another authorized source into this interpretation.
                for index in indexes:
                    identity = (
                        "source-index:"
                        + sha256(codec.dumps([index, snapshot.revision, request.request_id])).hexdigest()
                    )
                    indexed = InferenceResult(
                        identity,
                        "revision.source_index",
                        index,
                        (),
                        (),
                        (),
                        snapshot.rule_version,
                        "PROPOSED_SOURCE_BOUND_INDEX_ONLY",
                    )
                    if snapshot.historical_sources:
                        source_queries = tuple(
                            item for item in snapshot.query_dependencies if item.query.source_only
                        )
                        candidate = QueryDelta(
                            snapshot.session_id,
                            snapshot.principal,
                            snapshot.revision,
                            snapshot.access_epoch,
                            snapshot.rule_version,
                            {},
                            (indexed,),
                            source_queries,
                        )
                    else:
                        candidate = Delta(
                            snapshot.session_id,
                            snapshot.principal,
                            snapshot.revision,
                            snapshot.access_epoch,
                            snapshot.rule_version,
                            snapshot.source_versions,
                            (indexed,),
                        )
                    committed = self.store.commit(
                        snapshot.revision, candidate.read_set, snapshot.access_epoch, candidate
                    )
                    committed_revision = committed.revision
                # Leave the compilation snapshot and capture the actual current
                # program/absence dependencies, including newly persisted IR.
                snapshot = self.store.query_snapshot(
                    request.session_id,
                    self.principal,
                    (),
                    (IndexQuery({"kind": "program"}, history=True, known_at=request.issue.known_at),),
                )
                from hcl.semantics.revision import programs_from_view

                queries = [snapshot.query_dependencies[0].query]
                for program in programs_from_view(snapshot.query_views["0"]):
                    for default in program["defaults"]:
                        watch = IndexQuery(
                            dict(default["query"]), history=True, known_at=request.issue.known_at
                        )
                        if watch not in queries:
                            queries.append(watch)
                if len(queries) > 64:
                    raise HCLFailure(
                        "BUDGET_EXHAUSTED",
                        "revision",
                        "ABSENCE_WATCH_BOUND",
                        "defaults",
                        "The bounded query-watch allowance was exceeded.",
                    )
                if len(queries) > 1:
                    watched = self.store.query_snapshot(
                        request.session_id, self.principal, (), tuple(queries)
                    )
                    if watched.query_dependencies[0] != snapshot.query_dependencies[0]:
                        raise HCLFailure(
                            "STALE_STATE",
                            "QUERY_DEPENDENCY_CHANGED",
                            "query_dependencies",
                            "The program changed while binding its query watches.",
                        )
                    snapshot = watched
                previous = self.store._revision_previous(snapshot, query, request.issue.known_at)
                operation = self._revision_operator.run(
                    snapshot, request.issue, request.budget, query, previous
                )
                usage.update(operation.resource_usage)
                results = operation.candidate_delta.new_inferences
                contract = self._assembler.build(snapshot, (request.issue,), results)
                read_set = operation.read_set
                committed = self.store.commit(
                    snapshot.revision, read_set, snapshot.access_epoch, operation.candidate_delta
                )
                if committed.result_ids != operation.result_refs:
                    raise HCLFailure(
                        "FAILED",
                        "commit",
                        "COMMIT_RESULT_MISMATCH",
                        "result_refs",
                        "Committed revision results differ from their proposal.",
                    )
                state_revision = committed_revision = committed.revision
                unresolved = operation.issues
                operation_ids = (operation.operation_id,)
            elif request.issue.kind == "source.report":
                if not snapshot.immutable_views:
                    raise HCLFailure("NEEDS_EVIDENCE", "answer", "NO_SOURCES", "source_handles",
                                     "A source report needs an authorized source.")
                contract = self._assembler.source_report(snapshot)
            else:
                # This lookup is reached only after type/auth/session/ACL checks.
                # Denied requests never get a side channel into previous calls.
                owns_current_call = self._ledger is None and self.gateway.call_state(
                    self.principal, request.session_id, request.request_id) is None
                response = await self.gateway.generate(AuthorizedContext(snapshot, request.question),
                                                       CallSpec(request.request_id, request.budget, lease))
                usage.update(mock_calls=1, request_bytes=response.request_bytes, output_bytes=response.output_bytes)
                if response.resource_usage is not None:
                    usage.update(response.resource_usage)
                contract = self._assembler.offline_reply(response.visible_text)
            if len(contract.answer.encode("utf-8")) > request.budget.max_output_bytes:
                raise HCLFailure("BUDGET_EXHAUSTED", "answer", "OUTPUT_BYTES_EXCEEDED", "budget.max_output_bytes",
                                 "The complete answer exceeds the output allowance.")
            if self._ledger is not None:
                self.store.validate_snapshot(snapshot, read_set)
            else:
                self.store.validate_snapshot(snapshot)
            self._assembler.validate(contract, results)
            receipt.update(
                base_revision=snapshot.revision, commit_revision=state_revision,
                source_versions=dict(snapshot.source_versions), access_epoch=snapshot.access_epoch,
                rule_version=snapshot.rule_version, read_set=dict(read_set),
                result_ids=tuple(result.result_id for result in results),
                inference_values={result.result_id: result.values for result in results},
                mechanical_validation=contract.mechanical_validation,
                semantic_validation=contract.semantic_validation,
                operation_ids=operation_ids,
            )
            result = TaskResult(contract.answer, contract.claims, "PARTIAL" if unresolved else "COMPLETED",
                                unresolved, receipt, usage, state_revision)
            if self._ledger is not None:
                self._ledger.finish(lease, snapshot, read_set, result)
                self.store._checkpoint("task_finished")
                self.store.validate_snapshot(snapshot, read_set)
            return result
        except HCLFailure as error:
            # On failure/revocation do not export snapshot contents, source IDs,
            # candidate results, exception payloads, or partially checked prose.
            receipt = dict(failure_receipt)
            call_state = (self.gateway.call_state(self.principal, request.session_id, request.request_id)
                          if owns_current_call else None)
            if call_state is not None:
                receipt["mock_call_state"] = call_state
                usage["mock_calls"] = int(call_state not in ("RESERVED_IN_MEMORY_ONLY", "FAILED"))
            facts = dict(error.resource_usage)
            if "mock_call_state" in facts:
                receipt["mock_call_state"] = facts.pop("mock_call_state")
            usage.update(facts)
            # A delivery-size refusal can follow a successful computation commit.
            # Expose its existence only when access remains valid, never on denial.
            if committed_revision is not None and error.status != "DENIED":
                receipt["intermediate_commit_revision"] = committed_revision
            issue_id = (request.issue.issue_id if isinstance(request.issue, Issue)
                        and type(request.issue.issue_id) is str else "invalid_issue")
            result = TaskResult("", (), error.status, (issue_id,), receipt,
                                usage, committed_revision if error.status != "DENIED" else None,
                                (error.diagnostic,))
            if self._ledger is not None and lease is not None:
                try:
                    self._ledger.finish(lease, snapshot, read_set, result)
                except HCLFailure:
                    # The existing durable reservation remains. No recovery or
                    # repeated transport is attempted merely to write a failure.
                    pass
            return result

    async def stream(self, request: TaskRequest):
        yield DeliveryEvent("status", "RUNNING")
        # Exactly the same semantic path; no unchecked claim/token is published.
        result = await self.run(request)
        yield DeliveryEvent("result", result.status, result)
