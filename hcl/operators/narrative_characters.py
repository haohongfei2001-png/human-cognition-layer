"""Frame-bound M11 consumption of the existing shared M03/M05/M07/M08/M09 path.

This composition neither infers event identity from names nor certifies a
character's private mind. The unchanged domain solver retains its own limits.
"""

from dataclasses import replace
from hashlib import sha256
from hcl.kernel.types import Issue, freeze, thaw
from hcl.memory import codec
from hcl.operators.relationship_model import (
    RelationshipModelOperator,
    verify_relationships,
)


def equal(left, right):
    return codec.dumps(freeze(left)) == codec.dumps(freeze(right))


def frame_resolved(fragments, reference):
    frames = {(f["fragment"], row["id"]): row for f in fragments for row in f["frames"]}
    here, seen = (reference["fragment"], reference["id"]), set()
    while here in frames and here not in seen:
        seen.add(here)
        parent = frames[here]["parent"]
        if parent is None:
            return True
        here = (parent["fragment"], parent["id"])
    return False


def metadata(source, source_versions):
    return dict(
        id=source["id"],
        fragment=source["fragment"],
        local_id=source["local_id"],
        frame=thaw(source["frame"]),
        input_identity=sha256(codec.dumps(thaw(source))).hexdigest(),
        source_versions=dict(source_versions),
        scope="DECLARED_CHARACTER_READING_IN_THIS_NARRATIVE_FRAME",
    )


def uncomputed(source, source_versions, reason):
    return dict(
        metadata(source, source_versions),
        status="UNCOMPUTED",
        result_id=None,
        kind=None,
        values=None,
        assumption_environments=(),
        counterevidence_ids=(),
        issues=(reason,),
        resource_usage=dict(local_evaluations=0),
    )


def computed(source, source_versions, operation):
    actual = operation.candidate_delta.new_inferences[0]
    return dict(
        metadata(source, source_versions),
        status="COMPUTED",
        result_id=actual.result_id,
        kind=actual.kind,
        values=thaw(actual.values),
        assumption_environments=actual.assumption_environments,
        counterevidence_ids=actual.counterevidence_ids,
        issues=operation.issues,
        resource_usage=dict(operation.resource_usage),
    )


def execute_characters(snapshot, allowance, program):
    records, used = [], 0
    for source in program["characters"]:
        if not frame_resolved(program["fragments"], source["frame"]):
            record = uncomputed(
                source, snapshot.source_versions, "CHARACTER_FRAME_UNRESOLVED"
            )
        elif used == allowance.max_local_evaluations:
            record = uncomputed(
                source, snapshot.source_versions, "CHARACTER_MODEL_BUDGET_FRONTIER"
            )
        else:
            operation = RelationshipModelOperator().run(
                snapshot,
                Issue(source["id"], "relationship.evaluate"),
                replace(
                    allowance,
                    max_local_evaluations=allowance.max_local_evaluations - used,
                ),
                source["program"],
            )
            record = computed(source, snapshot.source_versions, operation)
            used += operation.resource_usage["local_evaluations"]
        records.append(record)
    return records, used


def verify_characters(records, program, max_work):
    sources = program["characters"]
    if len(records) != len(sources):
        raise ValueError("narrative character coverage changed")
    used = 0
    for record, source in zip(records, sources):
        if not frame_resolved(program["fragments"], source["frame"]):
            wanted = uncomputed(
                source, program["source_versions"], "CHARACTER_FRAME_UNRESOLVED"
            )
        elif used == max_work:
            wanted = uncomputed(
                source, program["source_versions"], "CHARACTER_MODEL_BUDGET_FRONTIER"
            )
        else:
            values = record["values"]
            if (
                not equal(
                    [row["inputs"] for row in values["models"]],
                    source["program"]["models"],
                )
                or values["issue_id"] != source["id"]
                or not equal(values["source_versions"], program["source_versions"])
                or values["rule_version"] != program["rule_version"]
                or type(values["execution_allowance"]) is not int
                or values["execution_allowance"] != max_work - used
            ):
                raise ValueError("character input, source or allowance changed")
            operation = verify_relationships(values)
            wanted = computed(source, program["source_versions"], operation)
            used += operation.resource_usage["local_evaluations"]
        if not equal(record, wanted):
            raise ValueError(
                "character result differs from its actual frame-bound computation"
            )
    if used > max_work:
        raise ValueError("character work bound exceeded")
    return used
