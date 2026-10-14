"""S2.3 executable contracts. Existing S1/S2 wire classes remain unchanged.

Only these allowlisted, versioned data dialects may cross the planner/operator
boundary. A LocalModel is a proposal, never Python or a source mutation.
"""

from dataclasses import dataclass, field
from collections.abc import Mapping
from types import MappingProxyType

from .types import BudgetSlice, Issue, ResultField, freeze

PROTOCOL = "hcl-execution-1"
DIALECTS = frozenset(
    {"finite-interpretation-1", "semantic-readings-1", "scoped-revision-1", "mental-scene-1", "argument-model-1", "discovery-model-1", "interaction-model-1", "affect-model-1", "relationship-model-1", "literature-model-1", "structural-model-1", "judgment-model-1", "judgment-model-2", "judgment-model-3", "judgment-model-4"}
)


@dataclass(frozen=True)
class ExecutionBudget(BudgetSlice):
    max_steps: int = 64
    max_feedback: int = 2
    max_context_tokens: int = 65536
    max_visible_output_tokens: int = 16384
    max_total_request_bytes: int = 1048576
    max_total_output_bytes: int = 262144


@dataclass(frozen=True)
class ExecutionIssue(Issue):
    kind: str = "cognition.execute"
    goals: tuple[Issue, ...] = ()

    def __post_init__(self):
        object.__setattr__(self, "goals", tuple(self.goals))


@dataclass(frozen=True)
class LocalModel:
    model_id: str
    dialect: str
    ast: object
    source_versions: object
    domain_assumptions: tuple[str, ...] = ()
    fit_residuals: tuple[str, ...] = ()
    unmodeled_observations: tuple[str, ...] = ()
    version: str = PROTOCOL

    def __post_init__(self):
        if self.dialect not in DIALECTS or self.version != PROTOCOL:
            raise ValueError("unsupported local model dialect/version")
        if not isinstance(self.ast, Mapping) or not isinstance(self.source_versions, Mapping):
            raise ValueError("typed local model data required")
        for name in ("ast", "source_versions"):
            object.__setattr__(self, name, freeze(getattr(self, name)))
        for name in ("domain_assumptions", "fit_residuals", "unmodeled_observations"):
            values = tuple(getattr(self, name))
            if len(values) > 1024 or any(type(v) is not str for v in values):
                raise ValueError("bounded explicit model qualifications required")
            object.__setattr__(self, name, values)


@dataclass(frozen=True)
class ModelIssue(Issue):
    model: LocalModel | None = None
    previous: object = None


@dataclass(frozen=True)
class ExecutionCheckpoint:
    """Internal complete audit channel; not automatically a model context."""

    protocol: str
    owner_id: str
    mode: str
    nodes: object
    trace: tuple
    counters: object
    snapshots: object

    def __post_init__(self):
        if self.protocol != PROTOCOL or self.mode not in ("RUNNING", "RESUMABLE", "FINISHED"):
            raise ValueError("invalid execution checkpoint")

        # Nodes/snapshots contain registered contracts, not arbitrary objects.
        def immutable(value):
            if isinstance(value, Mapping):
                return MappingProxyType({key: immutable(item) for key, item in value.items()})
            if isinstance(value, (tuple, list)):
                return tuple(immutable(item) for item in value)
            return value

        object.__setattr__(self, "nodes", immutable(self.nodes))
        object.__setattr__(self, "snapshots", immutable(self.snapshots))
        object.__setattr__(self, "trace", immutable(self.trace))
        object.__setattr__(self, "counters", freeze(self.counters))


@dataclass(frozen=True)
class ResumeToken:
    task_key: str
    request_fingerprint: str
    owner_id: str
    protocol: str = PROTOCOL


@dataclass(frozen=True)
class ProjectedResultField(ResultField):
    """Exact nested field path; never a model-generated summarization."""

    path: tuple[str, ...] = ()
    selection: tuple[str, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        object.__setattr__(self, "path", tuple(self.path))
        object.__setattr__(self, "selection", tuple(self.selection))


@dataclass(frozen=True)
class SnapshotRef:
    """Checkpoint-local content identity, not an external or lazy permission."""

    digest: str
