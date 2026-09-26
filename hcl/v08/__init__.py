"""HCL v0.8 evidence-constrained affect and appraisal candidate."""

from .runtime import (
    AffectEvidenceEvent,
    AffectKind,
    AppraisalDimension,
    EvidenceStrength,
    HCLV08Runtime,
)
from .semantic import V08ExtractionError, V08ExtractionResult, extract_affect_evidence

__all__ = [
    "AffectEvidenceEvent",
    "AffectKind",
    "AppraisalDimension",
    "EvidenceStrength",
    "HCLV08Runtime",
    "V08ExtractionError",
    "V08ExtractionResult",
    "extract_affect_evidence",
]
