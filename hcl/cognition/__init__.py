"""Opt-in shared cognition workspace; historical v1 entry remains available."""
from .core import Claim, ClaimKind, Dependency, EvidenceCore, Interpretation, Scope, SourceSpan
from .workspace import CognitionWorkspace, OperationResult

__all__ = ['Claim', 'ClaimKind', 'Dependency', 'EvidenceCore', 'Interpretation',
           'Scope', 'SourceSpan', 'CognitionWorkspace', 'OperationResult']
