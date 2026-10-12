"""Ephemeral typed semantic candidates; no persisted contract fields are changed."""
from dataclasses import dataclass, field
from typing import Mapping

from hcl.kernel.types import freeze


@dataclass(frozen=True)
class SemanticProfile:
    max_readings: int = 8
    max_entities: int = 18
    max_predicates: int = 26
    max_frames: int = 32
    max_ast_nodes: int = 512
    max_ast_depth: int = 48
    solver_timeout_ms: int = 100
    worker_wall_seconds: int = 15
    worker_cpu_seconds: int = 12
    worker_memory_bytes: int = 768 * 1024 * 1024

    def __post_init__(self):
        bounds = {'max_readings': (1, 64), 'max_entities': (1, 18), 'max_predicates': (1, 26),
                  'max_frames': (1, 128), 'max_ast_nodes': (1, 512), 'max_ast_depth': (1, 64),
                  'solver_timeout_ms': (1, 2000), 'worker_wall_seconds': (1, 120),
                  'worker_cpu_seconds': (1, 120), 'worker_memory_bytes': (128*1024*1024, 2*1024*1024*1024)}
        for name, (low, high) in bounds.items():
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError('bounded semantic execution profile required')


@dataclass(frozen=True)
class Frame:
    frame_id: str
    kind: str
    parent_id: str | None
    segment_ids: tuple[str, ...]


@dataclass(frozen=True)
class Proposition:
    meaning_id: str
    natural_reading: str
    typed_ast: Mapping
    frame_id: str
    segment_ids: tuple[str, ...]
    origin: str
    formula: str | None

    def __post_init__(self):
        object.__setattr__(self, 'typed_ast', freeze(self.typed_ast))


@dataclass(frozen=True)
class Reading:
    reading_id: str
    frame_id: str
    assumptions: tuple[str, ...]
    premises: tuple[Proposition, ...]
    query: Proposition
    unparsed_segments: tuple[str, ...]
    unresolved: tuple[str, ...]
    alignment: Mapping

    def __post_init__(self):
        object.__setattr__(self, 'alignment', freeze(self.alignment))


@dataclass(frozen=True)
class ParseForest:
    readings: tuple[Reading, ...]
    frames: tuple[Frame, ...]
    entities: Mapping
    predicates: Mapping
    symbol_map: Mapping
    segments: tuple
    source_versions: Mapping
    model_evidence: str = 'OFFLINE_FIXTURE_NOT_SEMANTIC_VALIDATION'

    def __post_init__(self):
        for field_name in ('entities', 'predicates', 'symbol_map', 'source_versions'):
            object.__setattr__(self, field_name, freeze(getattr(self, field_name)))
