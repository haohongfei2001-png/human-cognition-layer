"""Turn an actual authorized search/closure projection into an immutable effect."""
from hashlib import sha256

from hcl.kernel.dependencies import QuerySnapshot, QueryDelta, pack_dependencies
from hcl.kernel.retrieval import RetrievalIssue, RetrievalDependency, RETRIEVAL_VERSION
from hcl.kernel.types import InferenceResult, OpResult, HCLFailure
from hcl.memory import codec


def retrieval_issues(view):
    coverage = view["coverage"]
    return tuple(code for condition, code in (
        (bool(coverage["unknown_regions"]), "RETRIEVAL_UNINDEXED_REGIONS"),
        (bool(coverage["missing_recorded_dependencies"]), "RETRIEVAL_MISSING_RECORDED_DEPENDENCY"),
        (bool(coverage["frontier"]), "RETRIEVAL_CLOSURE_FRONTIER"),
    ) if condition)


class RetrievalOperator:
    def run(self, snapshot, issue, budget):
        if (type(snapshot) is not QuerySnapshot or type(issue) is not RetrievalIssue
                or len(snapshot.query_dependencies) != 1
                or type(snapshot.query_dependencies[0]) is not RetrievalDependency
                or snapshot.query_dependencies[0].query != issue.query):
            raise HCLFailure("INVALID_REQUEST", "retrieval", "RETRIEVAL_SNAPSHOT_REQUIRED", "snapshot",
                             "An exact authorized retrieval snapshot is required.")
        if budget.max_local_evaluations < 1:
            raise HCLFailure("BUDGET_EXHAUSTED", "retrieval", "RETRIEVAL_LOCAL_BUDGET", "budget",
                             "The retrieval result cannot be consumed without local allowance.")
        view = snapshot.query_views["0"]
        binding = (snapshot.session_id, snapshot.principal, snapshot.access_epoch, snapshot.rule_version,
                   pack_dependencies(snapshot.source_versions, snapshot.query_dependencies))
        result = InferenceResult("retrieval-result:" + sha256(codec.dumps([issue, view, binding])).hexdigest(),
                                 "RECORDED_EVIDENCE_PACKET", dict(retrieval=view), (),
                                 tuple(snapshot.source_versions), (), snapshot.rule_version,
                                 "RECORDED_RETRIEVAL_NOT_SEMANTIC_COMPLETENESS")
        return OpResult("memory.retrieve", RETRIEVAL_VERSION, snapshot.source_versions,
                        ("append_inference",), (result.result_id,), retrieval_issues(view),
                        dict(local_evaluations=1), (),
                        QueryDelta(snapshot.session_id, snapshot.principal, snapshot.revision,
                                   snapshot.access_epoch, snapshot.rule_version, snapshot.source_versions,
                                   (result,), snapshot.query_dependencies))
