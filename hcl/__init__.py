"""Human Cognition Layer's unified public entrypoint.

Historical versioned modules remain importable for certified replay. They are
not silently used as alternate paths by the new API.
"""
from hcl.api import HCL
from hcl.kernel.types import TaskRequest, TaskResult
from hcl.kernel.dependencies import RevisionIssue
from hcl.kernel.execution import ExecutionIssue, ExecutionBudget, LocalModel
from hcl.kernel.retrieval import RetrievalQuery, RetrievalIssue
from hcl.kernel.concept_registry import ConceptBinding, ConceptAdoptionIssue, ConceptFollowIssue

__all__ = ["ConceptBinding", "ConceptAdoptionIssue", "ConceptFollowIssue", "HCL", "TaskRequest", "TaskResult", "RevisionIssue", "ExecutionIssue", "ExecutionBudget", "LocalModel", "RetrievalQuery", "RetrievalIssue"]
