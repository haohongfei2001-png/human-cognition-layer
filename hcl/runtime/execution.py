"""Budgeted graph execution under the same authenticated run/stream entrypoint.

Evidence is complete in the store/checkpoint. Context packets and final claims
are independently bounded projections. All writes remain in this controller.
"""

from dataclasses import asdict, replace
from hashlib import sha256
import asyncio
import json

from hcl.kernel.execution import (
    ExecutionBudget,
    ExecutionIssue,
    ExecutionCheckpoint,
    LocalModel,
    ModelIssue,
    PROTOCOL,
    SnapshotRef,
)
from hcl.kernel.retrieval import RetrievalIssue, RetrievalQuery
from hcl.kernel.types import AnswerContract, Delta, HCLFailure, InferenceResult, Issue, TaskResult, thaw
from hcl.kernel.dependencies import RevisionIssue, QueryDelta, IndexQuery, pack_dependencies
from hcl.memory import codec
from hcl.models.gateway import AuthorizedContext, CallSpec
from hcl.operators.local_model import LocalModelOperator
from hcl.semantics.segments import SourceSegment, question_segments
from .context import ContextCompiler, ContextChunk
from .execution_ledger import ExecutionLedger, stopped
from .planner import IssuePlanner, progress_key


class ExecutionRunner:
    def __init__(self, engine):
        self.engine, self.store, self.gateway = engine, engine.store, engine.gateway
        self.planner = IssuePlanner()
        self.context = ContextCompiler(engine._semantic.profile)
        self.operator = LocalModelOperator(engine._semantic.profile)
        self.ledger = ExecutionLedger(self.store) if self.store.durable else None
        self.lease = None
        self.nodes, self.snapshots, self.trace, self.counters = {}, {}, [], {}

    def _validate(self, request):
        if (
            type(request.issue) is not ExecutionIssue
            or type(request.budget) is not ExecutionBudget
            or not self.store.durable
            or self.store._schema not in (3, 4)
            or not 1 <= len(request.issue.goals) <= 32
        ):
            raise stopped("EXECUTION_CONTRACT_REQUIRED", "INVALID_REQUEST", "admission")
        bounds = {
            "max_steps": 1024,
            "max_feedback": 16,
            "max_context_tokens": 4194304,
            "max_visible_output_tokens": 1048576,
            "max_total_request_bytes": 67108864,
            "max_total_output_bytes": 16777216,
        }
        for name, maximum in bounds.items():
            value = getattr(request.budget, name)
            if type(value) is not int or not 0 <= value <= maximum:
                raise stopped("EXECUTION_BUDGET_INVALID", "INVALID_REQUEST", "admission")
        ids = set()
        for goal in request.issue.goals:
            if (
                type(goal) not in (Issue, RevisionIssue, RetrievalIssue)
                or type(goal.issue_id) is not str
                or not goal.issue_id
                or len(goal.issue_id) > 128
                or goal.issue_id in ids
                or type(goal.kind) is not str
                or (goal.source_id is not None and type(goal.source_id) is not str)
            ):
                raise stopped("EXECUTION_GOALS_INVALID", "INVALID_REQUEST", "admission")
            goal.issue_id.encode("utf-8")
            if goal.source_id is not None:
                goal.source_id.encode("utf-8")
            if (
                type(goal) is RevisionIssue
                and goal.known_at is not None
                and (type(goal.known_at) is not int or goal.known_at < 0)
            ):
                raise stopped("INVALID_RECORDED_CUTOFF", "INVALID_REQUEST", "admission")
            if goal.kind == "revision.evaluate" and type(goal) is not RevisionIssue:
                raise stopped("REVISION_ISSUE_REQUIRED", "INVALID_REQUEST", "admission")
            if type(goal) is RetrievalIssue and (type(goal.query) is not RetrievalQuery or goal.source_id is not None
                    or goal.kind not in ("memory.retrieve", "logic.compare_semantic_readings", "argument.evaluate")):
                raise stopped("RETRIEVAL_ISSUE_INVALID", "INVALID_REQUEST", "admission")
            if goal.kind == "memory.retrieve" and type(goal) is not RetrievalIssue:
                raise stopped("RETRIEVAL_QUERY_REQUIRED", "INVALID_REQUEST", "admission")
            ids.add(goal.issue_id)
        cuts = {
            g.known_at for g in request.issue.goals if type(g) is RevisionIssue and g.known_at is not None
        }
        if cuts and (
            len(cuts) != 1
            or any(type(g) is not RevisionIssue or g.known_at not in cuts for g in request.issue.goals)
        ):
            raise stopped("MIXED_HISTORICAL_CUTOFF", "INVALID_REQUEST", "admission")

    def _snapshot(self, request, goal=None):
        if type(goal) is RetrievalIssue:
            return self.store.search_snapshot(request.session_id, request.principal, goal.query)
        handles = request.source_handles
        if goal is not None and goal.source_id is not None:
            handles = tuple(h for h in handles if h.source_id == goal.source_id)
            if not handles:
                raise stopped("OBLIGATION_SOURCE_DENIED", "DENIED", "access")
        if goal is not None and type(goal) is RevisionIssue:
            return self.store.revision_snapshot(
                request.session_id, request.principal, handles, known_at=goal.known_at
            )
        return self.store.snapshot(request.session_id, request.principal, handles)

    def _initial(self, request):
        goals, chunks = [], {}
        for goal in request.issue.goals:
            snapshot = self._snapshot(request, goal)
            if (
                sum(len(source.text.encode()) for source in snapshot.immutable_views.values())
                > 4 * 1024 * 1024
            ):
                raise stopped("EXECUTION_SOURCE_CAPACITY", "BUDGET_EXHAUSTED", "context")
            if goal.kind in (
                "logic.compare_semantic_readings",
                "revision.evaluate",
                "mental.simulate",
                "argument.evaluate",
                "hypothesis.discover",
                "interaction.evaluate",
                "affect.evaluate",
                "relationship.evaluate",
                "model.respond",
            ):
                purpose = {
                    "logic.compare_semantic_readings": "semantic_compile",
                    "revision.evaluate": "revision_compile",
                    "mental.simulate": "mental_compile",
                    "argument.evaluate": "argument_compile",
                    "hypothesis.discover": "discovery_compile",
                    "interaction.evaluate": "interaction_compile",
                    "affect.evaluate": "affect_compile",
                    "relationship.evaluate": "relationship_compile",
                    "model.respond": "answer",
                }[goal.kind]
                if type(goal) is RetrievalIssue:
                    view = snapshot.query_views["0"]
                    parts = (ContextChunk(purpose, tuple(SourceSegment(**row) for row in view["packet"]["segments"]), 0, 1),)
                    if len(self.context.serialize(snapshot, request.question, parts[0]).encode()) > self.context.limit(request.budget, self.gateway.capabilities):
                        raise stopped("RETRIEVAL_CLOSURE_CONTEXT_CAPACITY", "BUDGET_EXHAUSTED", "context")
                else:
                    parts = self.context.chunks(
                        snapshot, request.question, purpose, request.budget, self.gateway.capabilities
                    )
                if goal.kind in ("revision.evaluate", "mental.simulate", "argument.evaluate", "hypothesis.discover", "interaction.evaluate", "affect.evaluate", "relationship.evaluate") and len(parts) > 1:
                    # Cross-packet rule/identity IDs need a future composition
                    # compiler; never publish the final fragment as a full index.
                    raise stopped(
                        {
                            "revision.evaluate": "REVISION_COMPOSITION_CAPACITY",
                            "mental.simulate": "MENTAL_COMPOSITION_CAPACITY",
                            "argument.evaluate": "ARGUMENT_COMPOSITION_CAPACITY",
                            "hypothesis.discover": "DISCOVERY_COMPOSITION_CAPACITY",
                            "interaction.evaluate": "INTERACTION_COMPOSITION_CAPACITY",
                            "affect.evaluate": "AFFECT_COMPOSITION_CAPACITY",
                            "relationship.evaluate": "RELATIONSHIP_COMPOSITION_CAPACITY",
                        }[goal.kind],
                        "BUDGET_EXHAUSTED",
                        "context",
                    )
                for part in parts:
                    piece = (
                        goal
                        if len(parts) == 1
                        else replace(goal, issue_id=goal.issue_id + "/chunk-" + str(part.ordinal))
                    )
                    goals.append(piece)
                    chunks[piece.issue_id] = part
                    self.snapshots[piece.issue_id] = snapshot
                if len(parts) > 1:
                    self.trace.append(
                        dict(
                            event="UNRESOLVED", goal=goal.issue_id, code="CROSS_CHUNK_COMPOSITION_UNPROVED"
                        )
                    )
            else:
                goals.append(goal)
                self.snapshots[goal.issue_id] = snapshot
        self.nodes = self.planner.expand(goals)
        for node in self.nodes.values():
            if node["operation"] in ("compile", "respond") and node["goal"].issue_id in chunks:
                node["chunk"] = chunks[node["goal"].issue_id]
        self.counters = dict(
            steps=0,
            local_reserved=0,
            local_observed=0,
            local_unknown=False,
            feedback=0,
            semantic_profile=asdict(self.engine._semantic.profile),
            model_capabilities=asdict(self.gateway.capabilities),
        )
        return self._checkpoint()

    def _checkpoint(self):
        # Repeated chunks/branches share one immutable source snapshot in this
        # complete audit object. This is lossless interning, not summarization.
        values = {}

        def intern(snapshot):
            digest = sha256(codec.dumps(snapshot)).hexdigest()
            values.setdefault(digest, snapshot)
            return SnapshotRef(digest)

        goals = {key: intern(snapshot) for key, snapshot in self.snapshots.items()}
        nodes = {}
        for key, original in self.nodes.items():
            node = dict(original)
            for name in ("call_snapshot", "compute_snapshot"):
                if name in node:
                    node[name] = intern(node[name])
            nodes[key] = node
        return ExecutionCheckpoint(
            PROTOCOL,
            self.store.owner_id,
            "RUNNING",
            nodes,
            tuple(self.trace),
            self.counters,
            dict(values=values, goals=goals),
        )

    def _save(self):
        self.ledger.save(self.lease, self._checkpoint())

    def _restore(self, checkpoint):
        self.nodes = {key: dict(node) for key, node in checkpoint.nodes.items()}
        values = checkpoint.snapshots["values"]

        def resolve(reference):
            if type(reference) is not SnapshotRef or reference.digest not in values:
                raise stopped("CHECKPOINT_SNAPSHOT_REFERENCE", "FAILED", "storage")
            snapshot = values[reference.digest]
            if sha256(codec.dumps(snapshot)).hexdigest() != reference.digest:
                raise stopped("CHECKPOINT_SNAPSHOT_HASH", "FAILED", "storage")
            return snapshot

        self.snapshots = {key: resolve(value) for key, value in checkpoint.snapshots["goals"].items()}
        for node in self.nodes.values():
            for name in ("call_snapshot", "compute_snapshot"):
                if name in node:
                    node[name] = resolve(node[name])
        self.trace, self.counters = list(checkpoint.trace), dict(checkpoint.counters)
        if self.counters.get("semantic_profile") != asdict(
            self.engine._semantic.profile
        ) or self.counters.get("model_capabilities") != asdict(self.gateway.capabilities):
            raise stopped("EXECUTION_PROFILE_CHANGED", "INVALID_REQUEST", "recovery")
        for node in self.nodes.values():
            if node["state"] == "RUNNING":
                # Returned transport is read from its existing call row. Pure
                # work may resume only with its prior reservation still held.
                if node.get("local_hold") and node.get("result") is None:
                    self.counters["local_unknown"] = True
                node["state"] = "PENDING"

    def _tick(self, request, node):
        if self.counters["steps"] >= request.budget.max_steps:
            raise stopped("EXECUTION_STEP_BUDGET", "BUDGET_EXHAUSTED", "planning")
        self.counters["steps"] += 1
        node["state"] = "RUNNING"
        self.trace.append(dict(event="START", node=node["id"], operation=node["operation"]))
        self._save()

    async def _compile(self, request, node):
        goal, chunk = node["goal"], node["chunk"]
        snapshot = self.snapshots[goal.issue_id]
        feedback = node["feedback"][-1] if node["feedback"] else None
        chunk = replace(chunk, feedback=feedback)
        call_id = goal.issue_id + ":proposal:" + str(node["attempts"])
        wire = self.context.serialize(snapshot, request.question, chunk)
        node.update(call_id=call_id, call_snapshot=snapshot, wire_hash=sha256(wire.encode()).hexdigest())
        self._save()
        row = self.ledger.tasks.call(self.lease, call_id)
        if row is not None:
            if row["state"] != "RETURNED" or row["response_hash"] is None:
                raise stopped(
                    "PRIOR_CALL_NOT_REUSABLE",
                    "SEND_UNKNOWN" if row["attempted"] is None else "FAILED",
                    "model",
                )
            raw = self.store._get_object(row["response_hash"])
            if type(raw) is not str or not raw.strip():
                raise stopped("INVALID_MODEL_RETURN", "FAILED", "model")
            try:
                output_bytes = len(raw.encode("utf-8"))
            except UnicodeEncodeError:
                raise stopped("INVALID_MODEL_ENCODING", "FAILED", "model") from None
            cap = min(
                request.budget.max_output_bytes,
                request.budget.max_visible_output_tokens,
                self.gateway.capabilities.output_tokens or request.budget.max_visible_output_tokens,
            )
            if output_bytes > cap:
                raise stopped("OUTPUT_CAPACITY", "BUDGET_EXHAUSTED", "model")
            self.store.validate_snapshot(snapshot)
        else:
            response = await self.gateway.generate(
                AuthorizedContext(
                    snapshot, request.question, chunk.purpose, self.engine._semantic.profile, chunk
                ),
                CallSpec(request.request_id, request.budget, self.lease, call_id),
            )
            raw = response.visible_text
        node["raw_return"] = raw
        self._save()
        if node["operation"] == "respond":
            node["result"] = raw
            return
        source_segments = chunk.segments
        questions = question_segments(request.question)
        segments = (*source_segments, *questions)
        try:
            if goal.kind == "logic.compare_semantic_readings":
                forest = self.engine._semantic.compile(snapshot, segments, raw, request.budget)
                residuals = tuple(sorted({s for r in forest.readings for s in r.unparsed_segments}))
                assumptions = tuple(sorted({a for r in forest.readings for a in r.assumptions}))
                model = LocalModel(
                    "candidate:" + sha256(raw.encode()).hexdigest(),
                    "semantic-readings-1",
                    dict(candidate=raw, segments=[asdict(s) for s in segments], question=request.question),
                    snapshot.source_versions,
                    assumptions,
                    (),
                    residuals,
                )
                node["result"] = model
            elif goal.kind in ("mental.simulate", "argument.evaluate", "hypothesis.discover", "interaction.evaluate", "affect.evaluate", "relationship.evaluate"):
                from hcl.semantics.model_compiler import LocalModelCompiler

                from hcl.semantics.argument_compiler import ArgumentCompiler
                from hcl.semantics.discovery_compiler import DiscoveryCompiler
                from hcl.semantics.interaction_compiler import InteractionCompiler
                from hcl.semantics.affect_compiler import AffectCompiler
                from hcl.semantics.relationship_compiler import RelationshipCompiler
                compiler = {"mental.simulate": LocalModelCompiler, "argument.evaluate": ArgumentCompiler,
                            "hypothesis.discover": DiscoveryCompiler, "interaction.evaluate": InteractionCompiler, "affect.evaluate": AffectCompiler, "relationship.evaluate": RelationshipCompiler}[goal.kind]()
                program = compiler.compile(snapshot, segments, raw, request.budget)
                if goal.kind == "hypothesis.discover":
                    assumptions = tuple(sorted({a for c in (*program["contexts"], *(p["context"] for p in program["probes"])) for m in c["template"]["models"] for a in m["active_assumptions"]}))
                    residuals = tuple(program["unmodeled_segments"])
                elif goal.kind in ("interaction.evaluate", "affect.evaluate", "relationship.evaluate"):
                    assumptions = tuple(sorted({a for model in program["models"] for a in model["mental"]["active_assumptions"]}))
                    residuals = tuple(sorted({s for model in program["models"] for s in model["mental"]["unmodeled_segments"]}))
                else:
                    assumptions = tuple(sorted({a for model in program["models"] for a in model["active_assumptions"]}))
                    residuals = tuple(sorted({s for model in program["models"] for s in model["unmodeled_segments"]}))
                node["result"] = LocalModel(
                    {"mental.simulate":"mental-proposal:", "argument.evaluate":"argument-proposal:", "hypothesis.discover":"discovery-proposal:", "interaction.evaluate":"interaction-proposal:", "affect.evaluate":"affect-proposal:", "relationship.evaluate":"relationship-proposal:"}[goal.kind] + sha256(raw.encode()).hexdigest(),
                    {"mental.simulate":"mental-scene-1", "argument.evaluate":"argument-model-1", "hypothesis.discover":"discovery-model-1", "interaction.evaluate":"interaction-model-1", "affect.evaluate":"affect-model-1", "relationship.evaluate":"relationship-model-1"}[goal.kind],
                    dict(candidate=raw, segments=[asdict(s) for s in segments], question=request.question),
                    snapshot.source_versions,
                    assumptions,
                    (),
                    residuals,
                )
            else:
                indexes, query = self.engine._revision_compiler.compile(
                    snapshot, segments, raw, request.budget
                )
                node["result"] = dict(indexes=indexes, query=query)
        except HCLFailure as error:
            self.ledger.tasks.transition(
                self.lease,
                call_id,
                "RETURNED",
                "RETURNED",
                validation_code="COMPILE_REJECTED:" + error.diagnostic.code,
            )
            raise
        self.ledger.tasks.transition(
            self.lease, call_id, "RETURNED", "RETURNED", validation_code="COMPILED_CANDIDATE"
        )

    def _commit(self, operation):
        if operation.effects != ("append_inference",) or dict(operation.read_set) != dict(
            operation.candidate_delta.read_set
        ):
            raise stopped("OPERATOR_EFFECT_CONTRACT", "FAILED", "commit")
        delta = operation.candidate_delta
        if (
            operation.result_refs != tuple(result.result_id for result in delta.new_inferences)
            or delta.session_id != self.request.session_id
            or delta.principal != self.request.principal
        ):
            raise stopped("OPERATOR_EFFECT_CONTRACT", "FAILED", "commit")
        # Computed candidates are checkpointed before committing. A process death
        # after commit may only recognize byte-identical already committed effects.
        with self.store._transaction() as db:
            session = self.store._session(db, delta.session_id, delta.principal)
            self.store._validate_dependencies(
                db,
                session,
                delta.principal,
                pack_dependencies(
                    delta.read_set, delta.query_dependencies if type(delta) is QueryDelta else ()
                ),
                delta.access_epoch,
                delta.rule_version,
            )
            rows = [
                db.execute(
                    "SELECT * FROM inferences WHERE session_id=? AND result_id=?",
                    (delta.session_id, value.result_id),
                ).fetchone()
                for value in delta.new_inferences
            ]
            if rows and all(rows):
                if any(
                    self.store._get_object(row["object_hash"]) != value
                    or json.loads(row["read_set"])
                    != pack_dependencies(
                        delta.read_set, delta.query_dependencies if type(delta) is QueryDelta else ()
                    )
                    or row["epoch"] != delta.access_epoch
                    for row, value in zip(rows, delta.new_inferences)
                ):
                    raise stopped("COMMITTED_EFFECT_MISMATCH", "FAILED", "commit")
                return max(row["commit_revision"] for row in rows)
            if any(rows):
                raise stopped("PARTIAL_EFFECT_COLLISION", "FAILED", "commit")
        committed = self.store.commit(delta.base_revision, delta.read_set, delta.access_epoch, delta)
        if committed.result_ids != operation.result_refs:
            raise stopped("COMMIT_RESULT_MISMATCH", "FAILED", "commit")
        self.store._checkpoint("execution_effects_committed")
        return committed.revision

    def _revision_model(self, request, node, compiled):
        from hcl.kernel.types import OpResult

        goal = node["goal"]
        source = self.snapshots[goal.issue_id]
        if "index_operation" not in node:
            results = tuple(
                InferenceResult(
                    "execution-index:"
                    + sha256(codec.dumps([request.request_id, goal.issue_id, index])).hexdigest(),
                    "revision.source_index",
                    index,
                    (),
                    (),
                    (),
                    source.rule_version,
                    "PROPOSED_SOURCE_BOUND_INDEX_ONLY",
                )
                for index in compiled["indexes"]
            )
            if source.historical_sources:
                queries = tuple(q for q in source.query_dependencies if q.query.source_only)
                delta = QueryDelta(
                    source.session_id,
                    source.principal,
                    source.revision,
                    source.access_epoch,
                    source.rule_version,
                    {},
                    results,
                    queries,
                )
            else:
                delta = Delta(
                    source.session_id,
                    source.principal,
                    source.revision,
                    source.access_epoch,
                    source.rule_version,
                    source.source_versions,
                    results,
                )
            node["index_operation"] = OpResult(
                "revision.index",
                "1",
                delta.read_set,
                ("append_inference",),
                tuple(r.result_id for r in results),
                (),
                {},
                (),
                delta,
            )
            self._save()
        self._commit(node["index_operation"])
        snapshot = self.store.query_snapshot(
            request.session_id,
            request.principal,
            (),
            (IndexQuery({"kind": "program"}, history=True, known_at=goal.known_at),),
        )
        from hcl.semantics.revision import programs_from_view

        queries = [snapshot.query_dependencies[0].query]
        for program in programs_from_view(snapshot.query_views["0"]):
            for default in program["defaults"]:
                query = IndexQuery(dict(default["query"]), history=True, known_at=goal.known_at)
                if query not in queries:
                    queries.append(query)
        if len(queries) > 64:
            raise stopped("ABSENCE_WATCH_BOUND", "BUDGET_EXHAUSTED", "revision")
        if len(queries) > 1:
            watched = self.store.query_snapshot(request.session_id, request.principal, (), tuple(queries))
            if watched.query_dependencies[0] != snapshot.query_dependencies[0]:
                raise stopped("QUERY_DEPENDENCY_CHANGED", "STALE_STATE", "revision")
            snapshot = watched
        previous = self.store._revision_previous(snapshot, compiled["query"], goal.known_at)
        model = LocalModel(
            "revision-query:" + sha256(codec.dumps(compiled["query"])).hexdigest(),
            "scoped-revision-1",
            dict(query=compiled["query"]),
            snapshot.source_versions,
            ("SOURCE_BOUND_INTERPRETATIONS_ONLY",),
            (),
            tuple(
                sorted(
                    {
                        segment
                        for program in programs_from_view(snapshot.query_views["0"])
                        for segment in program["unparsed_segments"]
                    }
                )
            ),
        )
        node["compute_snapshot"] = snapshot
        return ModelIssue(goal.issue_id, goal.kind, goal.source_id, model, previous)

    async def _compute(self, request, node):
        goal = node["goal"]
        snapshot = self.snapshots[goal.issue_id]
        if node.get("result") is not None:
            node["commit_revision"] = self._commit(node["result"])
            self._mark_committed(node, node["result"])
            return
        if goal.kind == "memory.retrieve":
            issue = goal
            cost = 1
        elif goal.kind == "logic.check_interpretation":
            model = LocalModel(
                "source-interpretation:" + str(goal.source_id),
                "finite-interpretation-1",
                dict(source_id=goal.source_id),
                snapshot.source_versions,
                ("EXPLICIT_FINITE_INTERPRETATION",),
            )
            issue = ModelIssue(goal.issue_id, goal.kind, goal.source_id, model)
            source = snapshot.immutable_views.get(goal.source_id)
            cost = (
                len(source.formal_problem.premises) + 1
                if source is not None and source.formal_problem
                else 0
            )
        elif goal.kind == "logic.compare_semantic_readings":
            compiled = self.nodes[node["requires"][0]]["result"]
            issue = ModelIssue(goal.issue_id, goal.kind, goal.source_id, compiled)
            forest = self.engine._semantic.compile(
                snapshot,
                tuple(SourceSegment(**s) for s in thaw(compiled.ast)["segments"]),
                compiled.ast["candidate"],
                request.budget,
            )
            cost = len(forest.readings)
        elif goal.kind in ("mental.simulate", "argument.evaluate", "hypothesis.discover", "interaction.evaluate", "affect.evaluate", "relationship.evaluate"):
            compiled = self.nodes[node["requires"][0]]["result"]
            issue = ModelIssue(goal.issue_id, goal.kind, goal.source_id, compiled)
            cost = request.budget.max_local_evaluations - self.counters["local_reserved"]
        else:
            issue = self._revision_model(request, node, self.nodes[node["requires"][0]]["result"])
            snapshot = node["compute_snapshot"]
            cost = request.budget.max_local_evaluations - self.counters["local_reserved"]
        remaining = request.budget.max_local_evaluations - self.counters["local_reserved"]
        if cost > remaining or (cost == 0 and goal.kind in ("revision.evaluate", "mental.simulate", "argument.evaluate", "hypothesis.discover", "interaction.evaluate", "affect.evaluate", "relationship.evaluate")):
            if any(
                other is not node
                and other["operation"] == "compute"
                and other["state"] == "RUNNING"
                and other.get("local_hold")
                for other in self.nodes.values()
            ):
                raise stopped("LOCAL_BUDGET_IN_USE", "DEFERRED", "planning")
            raise stopped("SHARED_LOCAL_BUDGET", "BUDGET_EXHAUSTED", "operator")
        self.counters["local_reserved"] += cost
        node["local_model"] = getattr(issue, "model", None)
        node["local_hold"] = cost
        self._save()
        allowance = replace(request.budget, max_local_evaluations=cost)
        if goal.kind == "memory.retrieve":
            from hcl.operators.retrieval import RetrievalOperator
            operation = await asyncio.to_thread(RetrievalOperator().run, snapshot, issue, allowance)
        else:
            operation = await asyncio.to_thread(self.operator.run, snapshot, issue, allowance)
        delta = operation.candidate_delta
        if (
            delta.session_id != snapshot.session_id
            or delta.principal != snapshot.principal
            or delta.base_revision != snapshot.revision
            or delta.access_epoch != snapshot.access_epoch
            or delta.rule_version != snapshot.rule_version
            or any(
                snapshot.source_versions.get(key) != version for key, version in operation.read_set.items()
            )
            or (type(delta) is QueryDelta and delta.query_dependencies != snapshot.query_dependencies)
        ):
            raise stopped("OPERATOR_SNAPSHOT_CONTRACT", "FAILED", "operator")
        if type(goal) is RetrievalIssue and any(
            value.values.get("retrieval") != snapshot.query_views["0"] for value in delta.new_inferences
        ):
            raise stopped("RETRIEVAL_EFFECT_BINDING_MISMATCH", "FAILED", "operator")
        actual = operation.resource_usage.get("local_evaluations")
        if type(actual) is not int or not 0 <= actual <= cost:
            raise stopped("OPERATOR_RESOURCE_CONTRACT", "FAILED", "operator")
        self.counters["local_reserved"] -= cost - actual
        self.counters["local_observed"] += actual
        node["local_hold"] = actual
        node["result"], node["compute_snapshot"] = operation, snapshot
        self._save()
        self.store._checkpoint("execution_computed")
        node["commit_revision"] = self._commit(operation)
        self._mark_committed(node, operation)

    def _feedback(self, request, node, error=None):
        result = None
        if node.get("result") is not None and node["operation"] == "compute":
            results = node["result"].candidate_delta.new_inferences
            result = results[0] if len(results) == 1 else None
        obligation = self.planner.feedback(error=error, result=result)
        if obligation is None:
            return False
        target = node if node["operation"] == "compile" else self.nodes[node["requires"][0]]
        raw = target.get("raw_return", "")
        try:
            value = json.loads(
                raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite candidate"))
            )

            def semantic(item):
                if isinstance(item, dict):
                    return {
                        k: semantic(v)
                        for k, v in item.items()
                        if k not in ("confidence", "certainty", "explanation")
                    }
                if isinstance(item, list):
                    return [semantic(v) for v in item]
                return item

            normalized = semantic(value)
        except (ValueError, TypeError, RecursionError):
            normalized = raw
        key = progress_key(
            target["goal"],
            self.gateway.capabilities.model_id,
            self.snapshots[target["goal"].issue_id].source_versions,
            target["operation"],
            [obligation, normalized],
        )
        if key in target["progress"]:
            self.trace.append(dict(event="UNRESOLVED", goal=target["goal"].issue_id, code="NO_PROGRESS"))
            return False
        target["progress"] = (*target["progress"], key)
        if self.counters["feedback"] >= request.budget.max_feedback:
            return False
        self.counters["feedback"] += 1
        target["feedback"] = (*target["feedback"], obligation)
        target["attempts"] += 1
        target["state"] = "PENDING"
        # Keep failed raw returns and computed intermediate proofs in the audit.
        self.trace.append(
            dict(
                event="REPAIR",
                node=target["id"],
                obligation=obligation,
                previous_candidate=sha256(raw.encode()).hexdigest(),
            )
        )
        target["result"] = None
        if node is not target:
            if self._accepted(node, node["result"]):
                node["previous_results"] = (*node.get("previous_results", ()), node["result"])
            node["result"] = None
            node["state"] = "PENDING"
        self._save()
        return True

    def _invalidate_changed_queries(self, request):
        changed = False
        for node in self.nodes.values():
            if node["operation"] != "compute" or node["state"] != "DONE" or node.get("result") is None:
                continue
            try:
                self.store.validate_snapshot(node["compute_snapshot"], node["result"].read_set)
            except HCLFailure as error:
                if (
                    error.diagnostic.code != "QUERY_DEPENDENCY_CHANGED"
                    or node["goal"].kind not in ("revision.evaluate", "memory.retrieve")
                    or self.counters["steps"] >= request.budget.max_steps
                ):
                    raise
                node["invalidated_results"] = (*node.get("invalidated_results", ()), node["result"])
                node["result"], node["state"] = None, "PENDING"
                if node["goal"].kind == "memory.retrieve":
                    self.snapshots[node["goal"].issue_id] = self._snapshot(request, node["goal"])
                self.nodes[node["goal"].issue_id + ":deliver"]["state"] = "PENDING"
                self.trace.append(dict(event="LOCAL_RECOMPUTE", node=node["id"]))
                changed = True
        if changed:
            self._save()
        return changed

    async def _execute_node(self, request, node):
        try:
            self._tick(request, node)
            if node["operation"] in ("compile", "respond"):
                await self._compile(request, node)
            elif node["operation"] == "compute":
                await self._compute(request, node)
                if self._feedback(request, node):
                    return
            node["state"] = "DONE"
            self.trace.append(dict(event="DONE", node=node["id"]))
        except HCLFailure as error:
            if error.diagnostic.code == "LOCAL_BUDGET_IN_USE":
                node["state"] = "PENDING"
                self.trace.append(dict(event="WAIT_LOCAL_RESERVATION", node=node["id"]))
                self._save()
                return
            if node["operation"] == "compute" and node.get("local_hold") and node.get("result") is None:
                self.counters["local_unknown"] = True
            if error.status in ("DENIED", "SEND_UNKNOWN"):
                raise
            node["error"], node["error_status"] = error.diagnostic, error.status
            self.trace.append(dict(event="FAILED", node=node["id"], diagnostic=error.diagnostic))
            if (
                error.status == "STALE_STATE"
                and error.diagnostic.code == "QUERY_DEPENDENCY_CHANGED"
                and node["operation"] == "compute"
                and node["goal"].kind in ("revision.evaluate", "memory.retrieve")
                and self.counters["steps"] < request.budget.max_steps
            ):
                # The exact model response remains; only the dependent local
                # calculation is invalidated. No paid/fixture call is resent.
                if node.get("result") is not None:
                    node["invalidated_results"] = (*node.get("invalidated_results", ()), node["result"])
                node["result"] = None
                node["state"] = "PENDING"
                if node["goal"].kind == "memory.retrieve":
                    self.snapshots[node["goal"].issue_id] = self._snapshot(request, node["goal"])
                self.trace.append(dict(event="LOCAL_RECOMPUTE", node=node["id"]))
            elif self._feedback(request, node, error):
                return
            else:
                node["state"] = "FAILED"
                self.planner.block_dependents(self.nodes, node["id"])
        self._save()

    @staticmethod
    def _mark_committed(node, operation):
        # Eligibility is a successful commit of the complete immutable effect,
        # never an ID left behind by an earlier repair iteration.
        digest = sha256(codec.dumps(operation)).hexdigest()
        node["committed_operations"] = tuple(sorted({*node.get("committed_operations", ()), digest}))

    @staticmethod
    def _accepted(node, operation):
        return operation is not None and sha256(codec.dumps(operation)).hexdigest() in node.get(
            "committed_operations", ()
        )

    @classmethod
    def _operation(cls, node):
        current = node.get("result")
        if cls._accepted(node, current):
            return current
        return next(
            (
                previous
                for previous in reversed(node.get("previous_results", ()))
                if cls._accepted(node, previous)
            ),
            None,
        )

    def _bindings(self):
        result = []
        for node in self.nodes.values():
            if node["operation"] == "compute" and self._operation(node) is not None:
                operation = self._operation(node)
                result.append((node["compute_snapshot"], operation.read_set))
            elif node["operation"] == "deliver" and node["state"] == "DONE" and not node["requires"]:
                snapshot = self.snapshots[node["goal"].issue_id]
                result.append((snapshot, snapshot.source_versions))
            elif node["operation"] == "respond" and node["state"] == "DONE":
                snapshot = self.snapshots[node["goal"].issue_id]
                result.append((snapshot, snapshot.source_versions))
        return result

    @staticmethod
    def _check_delivery(request, result):
        size = len(codec.dumps(result))
        if (
            size > request.budget.max_output_bytes
            or len(result.answer.encode()) > request.budget.max_visible_output_tokens
            or result.usage.get("observed_output_bytes", 0) + size > request.budget.max_total_output_bytes
        ):
            raise HCLFailure(
                "BUDGET_EXHAUSTED",
                "answer",
                "DELIVERY_CAPACITY",
                "execution",
                "The actual delivery exceeds its unchanged task allowance.",
                resource_usage=result.usage,
            )

    def _qualify_replay(self, request, replay):
        """Reassemble pre-fix M04 delivery from unchanged committed evidence.

        History stays byte-identical. No model/operator is reexecuted and no
        accepted-operation digest is rewritten. Late ACL and capacity checks
        happen on the actual newly qualified delivery in the caller.
        """
        old = [
            claim
            for claim in replay.claim_records
            if claim.epistemic_status == "CONDITIONAL_MECHANISM_COMPARISON_NOT_TRUTH"
            and not any(
                field.field == "domain_issues" for field in claim.used_result_fields
            )
        ]
        if not old:
            return replay
        try:
            ids = tuple(
                sorted(
                    {
                        field.result_id
                        for claim in old
                        for field in claim.used_result_fields
                    }
                )
            )
            if not ids or not set(ids) <= set(
                replay.execution_receipt.get("result_ids", ())
            ):
                raise stopped("CACHED_RESULT_BINDING_INVALID")
            results = self.ledger.delivery_inferences(request, ids)
            assembler = self.engine._assembler
            claims = tuple(assembler.compact_claim(result) for result in results)
            contract = AnswerContract(
                "\n\n".join(claim.text for claim in claims),
                claims,
                "ACTUAL_RESULT_FIELDS",
                "NOT_CERTIFIED",
            )
            assembler.validate_compact(contract, results)
            replacements = {claim.claim_id: claim for claim in claims}
            if set(replacements) != {claim.claim_id for claim in old}:
                raise stopped("CACHED_RESULT_BINDING_INVALID")
            claims = tuple(
                replacements.get(claim.claim_id, claim)
                for claim in replay.claim_records
            )
            unresolved = tuple(
                sorted(
                    set(replay.unresolved_issues)
                    | {
                        code
                        for result in results
                        for code in assembler.qualification_issues(result)
                    }
                )
            )
            return replace(
                replay,
                answer="\n\n".join(claim.text for claim in claims),
                claim_records=claims,
                unresolved_issues=unresolved,
                status=(
                    "PARTIAL"
                    if unresolved and replay.status == "COMPLETED"
                    else replay.status
                ),
                execution_receipt=dict(
                    replay.execution_receipt,
                    discovery_delivery_qualification="SCOPED_DOMAIN_LIMITATIONS_V1",
                ),
            )
        except HCLFailure as error:
            raise HCLFailure(
                error.status,
                error.diagnostic.stage,
                error.diagnostic.code,
                error.diagnostic.field_path,
                error.diagnostic.message,
                resource_usage=replay.usage,
            ) from None

    def _deliver_replay(self, request, replay):
        """Retain all known historical usage even if late delivery is refused."""
        try:
            replay = self._qualify_replay(request, replay)
            self.ledger.tasks.validate_cached_delivery(request)
            self._check_delivery(request, replay)
            return replay
        except HCLFailure as error:
            usage = dict(replay.usage)
            usage.update(error.resource_usage)
            raise HCLFailure(
                error.status, error.diagnostic.stage, error.diagnostic.code,
                error.diagnostic.field_path, error.diagnostic.message,
                resource_usage=usage,
            ) from None

    async def run(self, request):
        self.request = request
        safe = dict(
            schema=PROTOCOL,
            engine="unified-engine-v1",
            request_id=request.request_id,
            store_durable=True,
            evidence_level="INTEGRATED_OFFLINE_SLICE_ONLY",
        )
        try:
            self._validate(request)
            # Read cached results before compiling contexts; changed current handles
            # not actually used by a prior result do not force unnecessary work.
            try:
                replay = self.ledger.tasks.resume(request)
            except HCLFailure as error:
                if error.diagnostic.code != "TASK_IN_PROGRESS":
                    raise
                replay = None
            if replay is not None:
                return self._deliver_replay(request, replay)
            initial = self._initial(request)
            root_goal = request.issue.goals[0] if type(request.issue.goals[0]) is RevisionIssue else None
            if root_goal is not None and root_goal.known_at is not None:
                root = self.store.historical_snapshot(
                    request.session_id,
                    request.principal,
                    request.source_handles,
                    known_at=root_goal.known_at,
                )
            else:
                root = self._snapshot(request)
            self.lease, checkpoint, replay = self.ledger.open(request, root, initial)
            if replay is not None:
                return self._deliver_replay(request, replay)
            self._restore(checkpoint)
            while True:
                ready = self.planner.ready(self.nodes)
                if not ready:
                    if self._invalidate_changed_queries(request):
                        continue
                    break
                computations = [node for node in ready if node["operation"] == "compute"]
                other = [node for node in ready if node["operation"] != "compute"]
                # Pure operators run in worker threads; checkpoints, accounting
                # and all commits execute on this one event-loop controller.
                if computations:
                    outcomes = await asyncio.gather(
                        *(self._execute_node(request, node) for node in computations),
                        return_exceptions=True
                    )
                    for outcome in outcomes:
                        if isinstance(outcome, BaseException):
                            raise outcome
                for node in other:
                    await self._execute_node(request, node)
            results, extra_claims, unresolved = [], [], []
            for node in self.nodes.values():
                if node["state"] in ("FAILED", "BLOCKED", "PENDING"):
                    unresolved.append(node["id"])
                if node["operation"] == "compute" and self._operation(node) is not None:
                    results.extend(self._operation(node).candidate_delta.new_inferences)
                    unresolved.extend(self._operation(node).issues)
                if node["operation"] == "deliver" and node["state"] == "DONE" and not node["requires"]:
                    snapshot = self.snapshots[node["goal"].issue_id]
                    if not snapshot.immutable_views:
                        unresolved.append(node["id"] + ":NO_SOURCES")
                    extra_claims.extend(self.engine._assembler.source_report(snapshot).claims)
                if node["operation"] == "respond" and node["state"] == "DONE":
                    extra_claims.extend(self.engine._assembler.offline_reply(node["result"]).claims)
            unresolved.extend(row["code"] for row in self.trace if row["event"] == "UNRESOLVED")
            unresolved.extend(code for result in results
                              for code in self.engine._assembler.qualification_issues(result))
            compact = tuple(self.engine._assembler.compact_claim(result) for result in results)
            computed = AnswerContract(
                "\n\n".join(c.text for c in compact), compact, "ACTUAL_RESULT_FIELDS", "NOT_CERTIFIED"
            )
            self.engine._assembler.validate_compact(computed, tuple(results))
            claims = (*compact, *extra_claims)
            answer = "\n\n".join(claim.text for claim in claims)
            diagnostics = tuple(
                n["error"] for n in self.nodes.values() if n.get("error") and n["state"] == "FAILED"
            )
            failures = [
                n["error_status"]
                for n in self.nodes.values()
                if n.get("error_status") and n["state"] == "FAILED"
            ]
            status = "PARTIAL" if unresolved else "COMPLETED"
            if not claims:
                status = failures[0] if failures else "NEEDS_EVIDENCE"
            usage = self.ledger.usage(self.lease)
            usage.update(
                provider_calls=0,
                provider_spend_usd="0",
                local_evaluations=(
                    None if self.counters["local_unknown"] else self.counters["local_observed"]
                ),
                observed_local_evaluations=self.counters["local_observed"],
                held_local_evaluations=self.counters["local_reserved"],
                execution_steps=self.counters["steps"],
                repair_calls=self.counters["feedback"],
                tokenizer="UTF8_BYTES_CONSERVATIVE_UPPER_BOUND",
            )
            receipt = dict(
                safe,
                operation_ids=tuple(n["id"] for n in self.nodes.values() if n["state"] == "DONE"),
                result_ids=tuple(r.result_id for r in results),
                checkpoint_audit="AUTHORIZED_TASK_EVENT_LOG",
                protocol=PROTOCOL,
            )
            revisions = [n["commit_revision"] for n in self.nodes.values() if "commit_revision" in n]
            result = TaskResult(
                answer,
                tuple(claims),
                status,
                tuple(sorted(set(unresolved))),
                receipt,
                usage,
                max(revisions) if revisions else root.revision,
                diagnostics,
            )
            self._check_delivery(request, result)
            bindings = self._bindings()
            self.ledger.finalize(self.lease, self._checkpoint(), result, bindings)
            self.ledger.tasks.validate_cached_delivery(request)
            return result
        except UnicodeEncodeError:
            return TaskResult(
                "",
                (),
                "INVALID_REQUEST",
                ("execution",),
                safe,
                {},
                None,
                (stopped("INVALID_TEXT_ENCODING", "INVALID_REQUEST", "admission").diagnostic,),
            )
        except HCLFailure as error:
            usage = dict(provider_calls=0, provider_spend_usd="0", mock_calls=0)
            if self.lease is not None:
                try:
                    usage.update(self.ledger.usage(self.lease))
                except HCLFailure:
                    usage.update(mock_calls=None, mock_usage_unknown=True)
            if self.counters:
                usage.update(
                    local_evaluations=(
                        None if self.counters["local_unknown"] else self.counters["local_observed"]
                    ),
                    observed_local_evaluations=self.counters["local_observed"],
                    held_local_evaluations=self.counters["local_reserved"],
                    execution_steps=self.counters["steps"],
                )
            usage.update(error.resource_usage)
            result = TaskResult(
                "", (), error.status, ("execution",), safe, usage, None, (error.diagnostic,)
            )
            if (
                self.lease is not None
                and error.status not in ("DENIED", "SEND_UNKNOWN")
                and error.diagnostic.code != "EXECUTION_PROFILE_CHANGED"
            ):
                try:
                    self.ledger.finalize(self.lease, self._checkpoint(), result, self._bindings())
                except HCLFailure:
                    pass  # Original reservation/checkpoint remains; never resend.
            return result
