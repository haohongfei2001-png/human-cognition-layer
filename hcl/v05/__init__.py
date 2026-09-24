"""HCL v0.5 issue-centered current-stance core."""

from .stance import (
    CurrentStance,
    StanceEvent,
    StanceSignal,
    StanceStatus,
    project_all_current_stances,
    project_current_stance,
)

__all__ = [
    "CurrentStance",
    "StanceEvent",
    "StanceSignal",
    "StanceStatus",
    "project_all_current_stances",
    "project_current_stance",
]

from .runtime import HCLV05Runtime, V05IngestResult
from .semantic import (
    ExtractionResult,
    SemanticExtractionError,
    catalog_from_events,
    extract_stance_events,
)

__all__ += [
    "ExtractionResult",
    "HCLV05Runtime",
    "SemanticExtractionError",
    "V05IngestResult",
    "catalog_from_events",
    "extract_stance_events",
]

from .store import V05Store
__all__ += ["V05Store"]
