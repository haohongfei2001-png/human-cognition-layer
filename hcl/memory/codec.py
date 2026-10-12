"""Versioned JSON for allowlisted contracts; never pickle or execute input."""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
import json

from hcl.kernel import types
from hcl.kernel.dependencies import IndexQuery, QueryDependency, QuerySnapshot, QueryDelta, RevisionIssue

from hcl.kernel.execution import ExecutionBudget, ExecutionIssue, LocalModel, ModelIssue, ExecutionCheckpoint, ResumeToken, ProjectedResultField, SnapshotRef
from hcl.runtime.context import ContextChunk
from hcl.semantics.segments import SourceSegment

FORMAT = "hcl-content-object-1"
CLASSES = {cls.__name__: cls for cls in (
    ExecutionBudget, ExecutionIssue, LocalModel, ModelIssue, ExecutionCheckpoint, ResumeToken, ProjectedResultField, SnapshotRef, ContextChunk, SourceSegment,
    types.Principal, types.AccessPolicy, types.SourceHandle, types.FormalProblem,
    types.SourceDocument, types.BudgetSlice, types.Issue, types.TaskRequest,
    types.Diagnostic, types.InferenceResult, types.Snapshot, types.Delta,
    types.OpResult, types.ResultField, types.AnswerClaim, types.AnswerContract,
    types.CommitResult, types.TaskResult, RevisionIssue, IndexQuery, QueryDependency, QuerySnapshot, QueryDelta,
)}


def encode(value):
    if is_dataclass(value) and type(value).__name__ in CLASSES and CLASSES[type(value).__name__] is type(value):
        return {"type": type(value).__name__, "fields": {f.name: encode(getattr(value, f.name)) for f in fields(value)}}
    if isinstance(value, Mapping):
        if any(type(key) is not str for key in value):
            raise ValueError("string map keys required")
        return {"map": {key: encode(item) for key, item in value.items()}}
    if type(value) in (tuple, list, frozenset):
        items = [encode(item) for item in value]
        if isinstance(value, frozenset):
            items.sort(key=canonical)
        return {type(value).__name__: items}
    if value is None or type(value) in (str, bool, int, float):
        return value
    raise ValueError("unsupported content type")


def decode(value):
    if type(value) is not dict:
        if value is None or type(value) in (str, bool, int, float):
            return value
        raise ValueError("invalid encoded value")
    if set(value) == {"type", "fields"} and value["type"] in CLASSES:
        cls = CLASSES[value["type"]]
        if set(value["fields"]) != {f.name for f in fields(cls)}:
            raise ValueError("contract fields changed")
        return cls(**{key: decode(item) for key, item in value["fields"].items()})
    if set(value) == {"map"}:
        return {key: decode(item) for key, item in value["map"].items()}
    for name, constructor in (("tuple", tuple), ("list", list), ("frozenset", frozenset)):
        if set(value) == {name}:
            return constructor(decode(item) for item in value[name])
    raise ValueError("unknown content encoding")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def dumps(value):
    # JSON escapes preserve even a malformed provider surrogate return exactly;
    # ingestion/delivery still reject invalid Unicode instead of rewriting it.
    return json.dumps({"schema": FORMAT, "value": encode(value)}, ensure_ascii=True,
                      sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def loads(body):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate content field")
            result[key] = value
        return result
    item = json.loads(body, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite value")))
    if set(item) != {"schema", "value"} or item["schema"] != FORMAT:
        raise ValueError("unsupported content schema")
    return decode(item["value"])
