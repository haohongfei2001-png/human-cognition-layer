"""Frozen three-argument executable operator protocol for S3/S4 consumers."""

from dataclasses import replace
from hashlib import sha256
from hcl.memory import codec

from hcl.kernel.execution import LocalModel, ModelIssue, PROTOCOL
from hcl.kernel.types import HCLFailure, thaw
from hcl.operators.logic import FiniteLogicOperator
from hcl.operators.semantic_logic import ReadingLogicOperator
from hcl.semantics.compiler import SemanticCompiler
from hcl.semantics.segments import SourceSegment, segment_snapshot


class LocalModelOperator:
    operation_id = "local_model.execute"
    version = PROTOCOL

    def __init__(self, semantic_profile=None):
        self.semantic_profile = semantic_profile

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
            ContextCompiler(self.semantic_profile).serialize(
                snapshot, ast["question"], ContextChunk("semantic_compile", source_segments, 0, 1)
            )
            questions = tuple(
                s for s in segment_snapshot(snapshot, ast["question"]) if s.kind == "QUESTION"
            )
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
        qualifications = dict(
            model_id=model.model_id,
            version=model.version,
            dialect=model.dialect,
            domain_assumptions=list(model.domain_assumptions),
            fit_residuals=list(model.fit_residuals),
            unmodeled_observations=list(model.unmodeled_observations),
        )
        inferences = tuple(
            replace(
                value,
                result_id="model-result:"
                + sha256(codec.dumps([value.result_id, qualifications])).hexdigest(),
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
