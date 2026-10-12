"""Human Cognition Layer's unified public entrypoint.

Historical versioned modules remain importable for certified replay. They are
not silently used as alternate paths by the new API.
"""
from hcl.api import HCL
from hcl.kernel.types import TaskRequest, TaskResult
from hcl.kernel.dependencies import RevisionIssue

__all__ = ["HCL", "TaskRequest", "TaskResult", "RevisionIssue"]
