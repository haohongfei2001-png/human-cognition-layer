"""Backward requirements and forward readiness, with bounded evidence feedback.

This is an explainable scheduler, not a learned utility/accuracy estimator.
Nodes and limits come from authenticated task obligations, never source policy.
"""

from hashlib import sha256

from hcl.kernel.types import HCLFailure
from hcl.memory import codec

SUPPORTED_GOALS = frozenset(
    {
        "logic.check_interpretation",
        "logic.compare_semantic_readings",
        "revision.evaluate",
        "mental.simulate",
        "argument.evaluate",
        "hypothesis.discover",
        "interaction.evaluate",
        "affect.evaluate",
        "relationship.evaluate",
        "judgment.evaluate",
        "literature.analyze",
        "analogy.compare",
        "memory.retrieve",
        "concept.adopt", "judgment.follow_concepts",
        "source.report",
        "model.respond",
    }
)


def progress_key(issue, model_version, input_versions, operation, result):
    """Confidence prose is deliberately not a semantic progress signal."""
    return sha256(codec.dumps([issue, model_version, input_versions, operation, result])).hexdigest()


class IssuePlanner:
    version = "issue-obligations-1"

    def expand(self, goals):
        nodes = {}
        for goal in goals:
            if goal.kind not in SUPPORTED_GOALS:
                raise HCLFailure(
                    "INVALID_REQUEST",
                    "planning",
                    "UNSUPPORTED_OBLIGATION",
                    "goals",
                    "The requested obligation has no installed executable operator.",
                )
            requirements = ["subscribe"] if goal.kind == "judgment.follow_concepts" else []
            if goal.kind in (
                "logic.compare_semantic_readings",
                "revision.evaluate",
                "mental.simulate",
        "argument.evaluate",
        "hypothesis.discover",
        "interaction.evaluate",
        "affect.evaluate",
        "relationship.evaluate",
        "judgment.evaluate",
        "literature.analyze",
        "analogy.compare",
                "model.respond",
            ):
                requirements.append("compile" if goal.kind != "model.respond" else "respond")
            if goal.kind not in ("source.report", "model.respond"):
                requirements.append("compute")
            requirements.append("deliver")
            previous = None
            for operation in requirements:
                key = goal.issue_id + ":" + operation
                if key in nodes:
                    raise HCLFailure(
                        "INVALID_REQUEST",
                        "planning",
                        "GOAL_EXPANSION_COLLISION",
                        "goals",
                        "Expanded obligation identities must be unique.",
                    )
                nodes[key] = dict(
                    id=key,
                    goal=goal,
                    operation=operation,
                    requires=() if previous is None else (previous,),
                    state="PENDING",
                    attempts=0,
                    feedback=(),
                    progress=(),
                    result=None,
                )
                previous = key
        return nodes

    def ready(self, nodes):
        return tuple(
            node
            for node in nodes.values()
            if node["state"] == "PENDING" and all(nodes[key]["state"] == "DONE" for key in node["requires"])
        )

    def block_dependents(self, nodes, key):
        changed = {key}
        while True:
            more = {
                name
                for name, node in nodes.items()
                if node["state"] == "PENDING" and set(node["requires"]) & changed
            }
            if not more:
                return
            for name in more:
                nodes[name]["state"] = "BLOCKED"
            changed |= more

    @staticmethod
    def feedback(error=None, result=None):
        """Specific data-derived repair obligations, not 'try harder'."""
        if error is not None:
            d = error.diagnostic
            if (
                d.stage in ("semantic_compile", "revision_compile", "model_compile", "argument_compile", "discovery_compile", "interaction_compile", "affect_compile", "relationship_compile", "judgment_compile", "literature_compile", "concept_compile")
                and error.status == "INVALID_REQUEST"
            ):
                return dict(kind="REPRESENTATION_REPAIR", code=d.code, field=d.field_path)
            return None
        if result is None:
            return None
        values = result.values
        if result.kind == "CONDITIONAL_FOL":
            gaps = tuple(
                sorted({segment for row in values["readings"] for segment in row["unparsed_segments"]})
            )
            if gaps:
                return dict(
                    kind="SOURCE_ALIGNMENT",
                    code="UNPARSED_SOURCE_SEGMENTS",
                    segments=gaps[:4],
                    remaining_count=max(0, len(gaps) - 4),
                )
        return None
