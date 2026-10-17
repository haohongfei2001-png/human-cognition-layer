"""Actual M09 consumption and independently recompiled local or explicit joins."""
from dataclasses import replace
from hashlib import sha256
import json
from types import SimpleNamespace

from hcl.kernel.types import Issue, Principal, thaw
from hcl.kernel.execution import ExecutionBudget
from hcl.memory import codec
from hcl.operators.relationship_model import RelationshipModelOperator, verify_relationships
from hcl.operators.literature import identity


def binding_conditions(source):
    refs = source["composition"]["assumption_refs"] if "composition" in source else [
        dict(fragment=source["fragment"], id=a) for a in source["assumptions"]]
    return tuple(sorted({identity(a["fragment"], "assumption", a["id"]) for a in refs}))


def execute_arc(snapshot, source, allowance):
    operation = RelationshipModelOperator().run(snapshot, Issue(source["id"], "relationship.evaluate"),
                                               allowance, source["program"])
    actual = operation.candidate_delta.new_inferences[0]
    record = dict(id=source["id"], fragment=source["fragment"], local_id=source["local_id"],
        actor=source["actor"], source_id=source["source_id"], bindings=thaw(source["bindings"]),
        binding_assumptions=binding_conditions(source),
        input_identity=sha256(codec.dumps(thaw(source))).hexdigest(),
        result_id=actual.result_id, kind=actual.kind, values=thaw(actual.values),
        assumption_environments=actual.assumption_environments,
        counterevidence_ids=actual.counterevidence_ids, source_versions=dict(operation.read_set),
        issues=operation.issues, resource_usage=dict(operation.resource_usage))
    if "composition" in source:
        record["composition"] = thaw(source["composition"])
    return record


def verify_arcs(values, used):
    from hcl.semantics.literature_compiler import LiteratureCompiler, CHARACTER_SCHEMA
    from hcl.semantics.narrative_characters import compile_arcs, validate_arc_clock
    from hcl.semantics.segments import SourceSegment

    inputs = values["inputs"]
    program = inputs["program"]
    # Full packet syntax validation may invoke M12, whose compiler stamps a
    # namespace. That temporary stamp is discarded here; the actual concept
    # certificate and its real namespace are independently checked by M11.
    snapshot = SimpleNamespace(session_id="pure-narrative-certificate",
        principal=Principal("pure", "certificate"), source_versions=values["source_versions"],
        immutable_views={k: SimpleNamespace(text=v) for k, v in inputs["originals"].items()})
    from hcl.semantics.cross_packet_characters import SCHEMA, COMPOSED, compose_shared
    compiled, all_segments = [], []
    byte_ends = {s: 0 for s in inputs["originals"]}
    if program["schema"] == COMPOSED and (any(type(f["fragment"]) is not int for f in program["fragments"])
            or [f["fragment"] for f in program["fragments"]] != list(range(len(program["fragments"])))):
        raise ValueError("shared character packet coverage changed")
    for fragment in program["fragments"]:
        segments = tuple(SourceSegment(**thaw(s), text=inputs["originals"][s["source_id"]][s["start"]:s["end"]])
                         for s in fragment["source_segments"])
        if program["schema"] == COMPOSED:
            for segment in segments:
                expected_id = "segment:" + sha256(json.dumps([
                    segment.kind, segment.source_id, segment.version, segment.source_sha256,
                    segment.start, segment.end], ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
                end = byte_ends[segment.source_id] + len(segment.text.encode())
                if (any(type(getattr(segment, k)) is not int for k in ("version", "start", "end", "byte_start", "byte_end"))
                        or segment.kind != "SOURCE" or segment.segment_id != expected_id
                        or segment.byte_start != byte_ends[segment.source_id] or segment.byte_end != end):
                    raise ValueError("shared character source segment identity changed")
                byte_ends[segment.source_id] = end
        all_segments.extend(segments)
        if program["schema"] == COMPOSED:
            chunk = SimpleNamespace(ordinal=fragment["fragment"], total=len(program["fragments"]), segments=segments)
            raw = {k: thaw(v) for k, v in fragment.items() if k not in ("fragment", "source_segments")}
            recompiled = LiteratureCompiler().compile_fragment(snapshot, chunk, json.dumps(raw),
                replace(ExecutionBudget(), max_output_bytes=1048576))
            if codec.canonical(thaw(recompiled)) != codec.canonical(thaw(fragment)):
                raise ValueError("narrative shared fragment changed")
        if fragment["schema"] == CHARACTER_SCHEMA:
            compiled.extend(compile_arcs(LiteratureCompiler(), snapshot, thaw(fragment), segments,
                replace(ExecutionBudget(), max_output_bytes=1048576)))
    if program["schema"] == COMPOSED:
        compiled.extend(compose_shared(LiteratureCompiler(), snapshot, thaw(program["fragments"]),
            all_segments, replace(ExecutionBudget(), max_output_bytes=1048576)))
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
            binding_assumptions=binding_conditions(source),
            input_identity=sha256(codec.dumps(source)).hexdigest(), result_id=actual.result_id,
            kind=actual.kind, values=thaw(actual.values), assumption_environments=actual.assumption_environments,
            counterevidence_ids=actual.counterevidence_ids, source_versions=dict(operation.read_set),
            issues=operation.issues, resource_usage=dict(operation.resource_usage))
        if "composition" in source:
            expected["composition"] = source["composition"]
        if codec.canonical(thaw(record)) != codec.canonical(expected):
            raise ValueError("narrative character certificate changed")
        used += operation.resource_usage["local_evaluations"]
        issues.update(operation.issues)
    return used, issues
