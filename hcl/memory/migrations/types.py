"""Immutable caller-supplied legacy snapshots, not an invented legacy database."""
from dataclasses import dataclass, field
from typing import Mapping

from hcl.kernel.types import FormalProblem, freeze


@dataclass(frozen=True)
class LegacySource:
    source_id: str
    version: int
    text: str | None
    status: str = "CURRENT"
    metadata: Mapping = field(default_factory=dict)
    formal_problem: FormalProblem | None = None

    def __post_init__(self):
        object.__setattr__(self, "metadata", freeze(self.metadata))


@dataclass(frozen=True)
class LegacyRecord:
    old_id: str
    kind: str
    payload: Mapping
    status: str = "LEGACY_ONLY"

    def __post_init__(self):
        object.__setattr__(self, "payload", freeze(self.payload))


@dataclass(frozen=True)
class LegacySnapshot:
    sources: tuple[LegacySource, ...]
    records: tuple[LegacyRecord, ...] = ()
    origin: str = "CALLER_SUPPLIED_TYPED_SNAPSHOT"

    def __post_init__(self):
        object.__setattr__(self, "sources", tuple(self.sources))
        object.__setattr__(self, "records", tuple(self.records))
