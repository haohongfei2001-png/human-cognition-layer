"""Frozen three-argument executable operator protocol for S3/S4 consumers."""

from dataclasses import replace
from hashlib import sha256
from hcl.memory import codec

from hcl.kernel.execution import LocalModel, ModelIssue, PROTOCOL
from hcl.kernel.types import HCLFailure, thaw
from hcl.operators.logic import FiniteLogicOperator
from hcl.operators.semantic_logic import ReadingLogicOperator
from hcl.semantics.compiler import SemanticCompiler
from hcl.semantics.segments import SourceSegment, question_segments


class LocalModelOperator:
    operation_id = "local_model.execute"
    version = PROTOCOL

    def __init__(self, semantic_profile=None):
        self.semantic_profile = semantic_profile
        from hcl.runtime.context import ContextCompiler

        self.context = ContextCompiler(semantic_profile)

    def run(self, snapshot, issue, allowance):
        try:
            return self._run(snapshot, issue, allowance)
        except (ValueError, KeyError, TypeError, RecursionError):
            raise HCLFailure(
                "INVALID_REQUEST",
                "operator",
                "LOCAL_MODEL_AST",
                "ast",
                "The local model does not satisfy its executable typed dialect.",
            ) from None

    def _run(self, snapshot, issue, allowance):
        if type(issue) is not ModelIssue or type(issue.model) is not LocalModel:
            raise HCLFailure(
                "INVALID_REQUEST",
                "operator",
                "LOCAL_MODEL_REQUIRED",
                "issue.model",
                "The executable issue requires a versioned local model.",
            )
        model = issue.model
        if dict(model.source_versions) != dict(snapshot.source_versions):
            raise HCLFailure(
                "STALE_STATE",
                "operator",
                "LOCAL_MODEL_INPUT_CHANGED",
                "source_versions",
                "The model input binding differs from the immutable snapshot.",
            )
        ast = thaw(model.ast)
        if model.dialect == "finite-interpretation-1":
            if set(ast) != {"source_id"} or ast["source_id"] != issue.source_id:
                raise HCLFailure(
                    "INVALID_REQUEST",
                    "operator",
                    "LOCAL_MODEL_AST",
                    "ast",
                    "The finite adapter accepts only an authorized source interpretation reference.",
                )
            result = FiniteLogicOperator().run(snapshot, issue, allowance)
        elif model.dialect == "semantic-readings-1":
            if set(ast) != {"candidate", "segments", "question"}:
                raise HCLFailure(
                    "INVALID_REQUEST",
                    "operator",
                    "LOCAL_MODEL_AST",
                    "ast",
                    "The semantic adapter requires source-bound typed candidates.",
                )
            segments = tuple(SourceSegment(**s) for s in ast["segments"])
            # The same exact-source validator used by model packing also guards
            # operator callers. Question anchors are rebuilt rather than trusted.
            from hcl.runtime.context import ContextCompiler, ContextChunk

            source_segments = tuple(s for s in segments if s.kind == "SOURCE")
            self.context.serialize(
                snapshot, ast["question"], ContextChunk("semantic_compile", source_segments, 0, 1)
            )
            questions = question_segments(ast["question"])
            if tuple(s for s in segments if s.kind == "QUESTION") != questions:
                raise HCLFailure(
                    "INVALID_REQUEST",
                    "operator",
                    "QUESTION_ANCHOR_MISMATCH",
                    "segments",
                    "Question anchors differ from the bound query.",
                )
            forest = SemanticCompiler(self.semantic_profile).compile(
                snapshot, segments, ast["candidate"], allowance
            )
            result = ReadingLogicOperator(self.semantic_profile).run(snapshot, issue, allowance, forest)
        elif model.dialect in ("mental-scene-1", "argument-model-1", "discovery-model-1", "interaction-model-1", "affect-model-1", "relationship-model-1", "structural-model-1", "judgment-model-1"):
            from hcl.semantics.model_compiler import LocalModelCompiler
            from hcl.operators.mental_scene import MentalSceneOperator
            from hcl.runtime.context import ContextChunk

            if set(ast) != {"candidate", "segments", "question"}:
                raise ValueError("source-bound mental model fields required")
            segments = tuple(SourceSegment(**row) for row in ast["segments"])
            sources = tuple(row for row in segments if row.kind == "SOURCE")
            purpose = {"mental-scene-1":"mental_compile", "argument-model-1":"argument_compile", "discovery-model-1":"discovery_compile", "interaction-model-1":"interaction_compile", "affect-model-1":"affect_compile", "relationship-model-1":"relationship_compile", "structural-model-1":"concept_compile", "judgment-model-1":"judgment_compile"}[model.dialect]
            self.context.serialize(snapshot, ast["question"], ContextChunk(purpose, sources, 0, 1))
            if tuple(row for row in segments if row.kind == "QUESTION") != question_segments(
                ast["question"]
            ):
                raise ValueError("query anchors changed")
            from hcl.semantics.argument_compiler import ArgumentCompiler
            from hcl.operators.argument_model import ArgumentModelOperator
            from hcl.semantics.discovery_compiler import DiscoveryCompiler
            from hcl.operators.discovery_model import DiscoveryModelOperator
            from hcl.semantics.interaction_compiler import InteractionCompiler
            from hcl.operators.interaction_model import InteractionModelOperator
            from hcl.semantics.affect_compiler import AffectCompiler
            from hcl.operators.affect_model import AffectModelOperator
            from hcl.semantics.relationship_compiler import RelationshipCompiler
            from hcl.operators.relationship_model import RelationshipModelOperator
            from hcl.semantics.concept_compiler import ConceptCompiler
            from hcl.operators.concepts import ConceptOperator
            from hcl.semantics.judgment_compiler import JudgmentCompiler
            from hcl.operators.judgment_model import JudgmentModelOperator
            compiler = {"mental-scene-1":LocalModelCompiler, "argument-model-1":ArgumentCompiler,
                        "discovery-model-1":DiscoveryCompiler, "interaction-model-1":InteractionCompiler, "affect-model-1":AffectCompiler, "relationship-model-1":RelationshipCompiler, "structural-model-1":ConceptCompiler, "judgment-model-1":JudgmentCompiler}[model.dialect]()
            operator = {"mental-scene-1":MentalSceneOperator, "argument-model-1":ArgumentModelOperator,
                        "discovery-model-1":DiscoveryModelOperator, "interaction-model-1":InteractionModelOperator, "affect-model-1":AffectModelOperator, "relationship-model-1":RelationshipModelOperator, "structural-model-1":ConceptOperator, "judgment-model-1":JudgmentModelOperator}[model.dialect]()
            program = compiler.compile(snapshot, segments, ast["candidate"], allowance)
            result = (operator.run(snapshot, issue, allowance, program, segments) if model.dialect == "discovery-model-1"
                      else operator.run(snapshot, issue, allowance, program))
        elif model.dialect == "literature-model-1":
            from hcl.semantics.literature_compiler import LiteratureCompiler
            from hcl.operators.literature import LiteratureOperator
            program = LiteratureCompiler().compile_model(snapshot, ast, allowance)
            result = LiteratureOperator().run(snapshot, issue, allowance, program)
        elif model.dialect == "scoped-revision-1":
            if set(ast) != {"query"}:
                raise HCLFailure(
                    "INVALID_REQUEST",
                    "operator",
                    "LOCAL_MODEL_AST",
                    "ast",
                    "The revision adapter requires an indexed query and prior computed state.",
                )
            from hcl.kernel.dependencies import QuerySnapshot
            from hcl.operators.revision import RevisionOperator

            if type(snapshot) is not QuerySnapshot:
                raise HCLFailure(
                    "INVALID_REQUEST",
                    "operator",
                    "QUERY_SNAPSHOT_REQUIRED",
                    "snapshot",
                    "The scoped revision model needs exact query dependencies.",
                )
            result = RevisionOperator().run(snapshot, issue, allowance, ast["query"], issue.previous)
        else:
            raise HCLFailure(
                "INVALID_REQUEST",
                "operator",
                "LOCAL_MODEL_DIALECT",
                "dialect",
                "The proposed local dialect has no installed solver.",
            )
        # An executable effect is an actual candidate append, not a success flag.
        if result.result_refs != tuple(r.result_id for r in result.candidate_delta.new_inferences):
            raise HCLFailure(
                "FAILED",
                "operator",
                "RESULT_EFFECT_MISMATCH",
                "effects",
                "The declared inference effects differ from actual computed results.",
            )
        from hcl.kernel.dependencies import QueryDelta, QuerySnapshot
        from hcl.kernel.retrieval import RetrievalDependency
        if type(snapshot) is QuerySnapshot and any(type(d) is RetrievalDependency for d in snapshot.query_dependencies):
            delta = result.candidate_delta
            if type(delta) is not QueryDelta:
                from dataclasses import fields
                delta = QueryDelta(**{field.name: getattr(delta, field.name) for field in fields(delta)},
                                   query_dependencies=snapshot.query_dependencies)
            result = replace(result, candidate_delta=delta)
            from hcl.operators.retrieval import retrieval_issues
            result = replace(result,
                             issues=tuple((*result.issues, *retrieval_issues(snapshot.query_views["0"]))),
                             candidate_delta=replace(delta, new_inferences=tuple(
                                 replace(value, values=dict(value.values, retrieval=snapshot.query_views["0"]))
                                 for value in delta.new_inferences)))
        qualifications = dict(
            model_id=model.model_id,
            version=model.version,
            dialect=model.dialect,
            domain_assumptions=list(model.domain_assumptions),
            fit_residuals=list(model.fit_residuals),
            unmodeled_observations=list(model.unmodeled_observations),
        )
        # Content identity alone cannot identify a commit after an authorization
        # or indexed-query dependency change. Bind only the top-level effect to
        # its immutable Delta context; nested pure certificates remain reusable.
        # Unrelated base-revision changes intentionally do not alter this identity.
        from hcl.kernel.dependencies import QueryDelta, pack_dependencies

        delta = result.candidate_delta
        commit_context = dict(
            schema="local-model-commit-identity-1",
            session_id=delta.session_id,
            principal=delta.principal,
            access_epoch=delta.access_epoch,
            rule_version=delta.rule_version,
            dependencies=pack_dependencies(
                delta.read_set,
                delta.query_dependencies if type(delta) is QueryDelta else (),
            ),
        )
        inferences = tuple(
            replace(
                value,
                result_id="model-result:"
                + sha256(codec.dumps([value.result_id, qualifications, commit_context])).hexdigest(),
                values=dict(value.values, local_model=qualifications),
                assumption_environments=tuple(
                    (
                        *value.assumption_environments,
                        *(
                            "local-model:" + model.model_id + ":assumption:" + str(i)
                            for i in range(len(model.domain_assumptions))
                        ),
                    )
                ),
            )
            for value in result.candidate_delta.new_inferences
        )
        unresolved = (
            *result.issues,
            *(("LOCAL_MODEL_FIT_RESIDUALS",) if model.fit_residuals else ()),
            *(("UNMODELED_OBSERVATIONS",) if model.unmodeled_observations else ()),
        )
        return replace(
            result,
            effects=("append_inference",),
            result_refs=tuple(value.result_id for value in inferences),
            issues=unresolved,
            candidate_delta=replace(result.candidate_delta, new_inferences=inferences),
        )
