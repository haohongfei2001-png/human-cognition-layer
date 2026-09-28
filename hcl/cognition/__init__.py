"""Opt-in shared cognition workspace; historical v1 entry remains available."""
from .core import Claim, ClaimKind, Dependency, EvidenceCore, Interpretation, Scope, SourceSpan
from .workspace import CognitionWorkspace, OperationResult

__all__ = ['Claim', 'ClaimKind', 'Dependency', 'EvidenceCore', 'Interpretation',
           'Scope', 'SourceSpan', 'CognitionWorkspace', 'OperationResult',
           'AuthorizedText', 'SemanticResult', 'prepare_semantics', 'PositionAssessment', 'assess_positions', 'RetainedResult', 'prepare_retained', 'answer_retained']

from .semantic import AuthorizedText, SemanticResult, prepare_semantics

from .positions import PositionAssessment, assess_positions

from .retained import RetainedResult, prepare_retained, answer_retained
