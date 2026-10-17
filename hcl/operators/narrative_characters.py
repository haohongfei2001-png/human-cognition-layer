"""Actual M09 consumption and independently recomputed packet-local certificates."""
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

from hcl.kernel.types import Issue, thaw
from hcl.kernel.execution import ExecutionBudget
from hcl.memory import codec
from hcl.operators.relationship_model import RelationshipModelOperator, verify_relationships
from hcl.operators.literature import identity


def execute_arc(snapshot, source, allowance):
    operation = RelationshipModelOperator().run(snapshot, Issue(source["id"], "relationship.evaluate"),
                                               allowance, source["program"])
    actual = operation.candidate_delta.new_inferences[0]
    return dict(id=source["id"], fragment=source["fragment"], local_id=source["local_id"],
        actor=source["actor"], source_id=source["source_id"], bindings=thaw(source["bindings"]),
        binding_assumptions=tuple(sorted(identity(source["fragment"], "assumption", a) for a in source["assumptions"])),
        input_identity=sha256(codec.dumps(thaw(source))).hexdigest(),
        result_id=actual.result_id, kind=actual.kind, values=thaw(actual.values),
        assumption_environments=actual.assumption_environments,
        counterevidence_ids=actual.counterevidence_ids, source_versions=dict(operation.read_set),
        issues=operation.issues, resource_usage=dict(operation.resource_usage))


def verify_arcs(values, used):
    from hcl.semantics.literature_compiler import LiteratureCompiler, CHARACTER_SCHEMA
    from hcl.semantics.narrative_characters import compile_arcs, validate_arc_clock
    from hcl.semantics.segments import SourceSegment

    inputs = values["inputs"]
    program = inputs["program"]
    snapshot = SimpleNamespace(source_versions=values["source_versions"])
    compiled = []
    for fragment in program["fragments"]:
        if fragment["schema"] == CHARACTER_SCHEMA:
            segments = tuple(SourceSegment(**thaw(s), text=inputs["originals"][s["source_id"]][s["start"]:s["end"]])
                             for s in fragment["source_segments"])
            compiled.extend(compile_arcs(LiteratureCompiler(), snapshot, thaw(fragment), segments,
                replace(ExecutionBudget(), max_output_bytes=1048576)))
    for arc in compiled:
        validate_arc_clock(LiteratureCompiler(), program["fragments"], arc)
    if codec.canonical(compiled) != codec.canonical(thaw(program["character_arcs"])):
        raise ValueError("narrative character compilation changed")
    if len(values["character_arcs"]) != len(compiled):
        raise ValueError("narrative character coverage changed")
    issues = set()
    for record, source in zip(values["character_arcs"], compiled):
        value = record["values"]
        if (value["execution_allowance"] != inputs["max_batches"] - used
                or value["issue_id"] != source["id"]
                or codec.canonical([thaw(m["inputs"]) for m in value["models"]]) != codec.canonical(source["program"]["models"])
                or dict(value["source_versions"]) != dict(values["source_versions"])):
            raise ValueError("narrative character input or allowance changed")
        operation = verify_relationships(value)
        actual = operation.candidate_delta.new_inferences[0]
        expected = dict(id=source["id"], fragment=source["fragment"], local_id=source["local_id"],
            actor=source["actor"], source_id=source["source_id"], bindings=source["bindings"],
            binding_assumptions=tuple(sorted(identity(source["fragment"], "assumption", a) for a in source["assumptions"])),
            input_identity=sha256(codec.dumps(source)).hexdigest(), result_id=actual.result_id,
            kind=actual.kind, values=thaw(actual.values), assumption_environments=actual.assumption_environments,
            counterevidence_ids=actual.counterevidence_ids, source_versions=dict(operation.read_set),
            issues=operation.issues, resource_usage=dict(operation.resource_usage))
        if codec.canonical(thaw(record)) != codec.canonical(expected):
            raise ValueError("narrative character certificate changed")
        used += operation.resource_usage["local_evaluations"]
        issues.update(operation.issues)
    return used, issues
