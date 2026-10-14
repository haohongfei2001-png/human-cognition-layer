"""Additive v4: a finite, source-bound language of hypothetical joint edits.

An edit costs one declared selector replacement or one scoped premise/rule
activation retraction. This is not a semantic concept-distance metric. No edit
changes source text, actual cognitive facts, original commitments or adoption.
"""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json

from hcl.kernel.types import freeze, thaw
from hcl.memory import codec
from hcl.semantics.concept_version_compiler import digest, host_context, semantic_definition
from hcl.semantics.judgment_concept_compiler import ConceptJudgmentCompiler

SCHEMA = "hcl-judgment-candidates-4"
LANGUAGE = "DECLARED_SELECTOR_AND_SCOPED_ACTIVATION_RETRACTIONS_1"


def node_count(value):
    """Deterministic bounded validation/serialization units, including leaves."""
    if isinstance(value, dict):
        return 1 + sum(1 + node_count(v) for v in value.values())
    if isinstance(value, (tuple, list)):
        return 1 + sum(node_count(v) for v in value)
    return 1


class JointChangeCompiler(ConceptJudgmentCompiler):
    def _compile_concepts(self, snapshot, segments, raw, allowance):
        if type(raw) is not str or len(raw.encode()) > min(allowance.max_output_bytes, 1048576):
            raise self._limit("candidate_bytes")
        def unique(pairs):
            out = {}
            for key, value in pairs:
                if key in out:
                    raise ValueError("duplicate candidate field")
                out[key] = value
            return out
        data = json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite value")))
        self._keys(data, "schema models concepts joint_changes")
        if data["schema"] != SCHEMA:
            raise ValueError("explicit joint-change dialect required")
        base = deepcopy(data)
        request = base.pop("joint_changes")
        base["schema"] = "hcl-judgment-candidates-2"
        program = thaw(ConceptJudgmentCompiler().compile(snapshot, segments,
            json.dumps(base, ensure_ascii=False), allowance))
        self._keys(request, "baseline target edits")
        concepts = program["concepts"]
        choices = {c["id"]: c for c in concepts["choices"]}
        versions = {v["id"]: v for v in concepts["versions"]}
        baseline = request["baseline"]
        if (type(baseline) is not dict or set(baseline) != set(choices)
                or any(type(v) is not str or v not in choices[k]["versions"] for k, v in baseline.items())
                or any([baseline[c["left"]], baseline[c["right"]]] not in c["allowed_pairs"]
                       for c in concepts["constraints"])):
            raise ValueError("one complete legal baseline is required")
        models = {(m["mental"]["source_id"], m["mental"]["id"]): (i, m)
                  for i, m in enumerate(program["base_program"]["models"])}
        if len(models) != len(program["base_program"]["models"]):
            raise ValueError("unambiguous model namespace required")
        target = request["target"]
        if type(target) is not dict:
            raise ValueError("typed target required")
        if target.get("kind") == "M13_ACCEPTANCE":
            self._keys(target, "kind source_id model_id argument_id query_id")
        elif target.get("kind") == "M14_DECISION":
            self._keys(target, "kind source_id model_id decision_id")
        else:
            raise ValueError("explicit M13 acceptance or M14 joint decision target required")
        for value in target.values():
            self._text(value, 128)
        index, model = models[(target["source_id"], target["model_id"])]
        if target["kind"] == "M13_ACCEPTANCE":
            if (model["argument"]["id"] != target["argument_id"]
                    or target["query_id"] not in {q["id"] for q in model["argument"]["queries"]}):
                raise ValueError("target query differs from its argument namespace")
        elif target["decision_id"] not in {d["id"] for d in model["decisions"]}:
            raise ValueError("target decision absent")
        if type(request["edits"]) is not list or len(request["edits"]) > 32:
            raise ValueError("bounded declared edits required")
        atoms, ignored = {}, []
        for row in request["edits"]:
            if type(row) is not dict:
                raise ValueError("typed edit required")
            if row.get("kind") == "CHOICE_REPLACE":
                self._keys(row, "kind choice_id version_id segment_ids")
                choice, version = choices[row["choice_id"]], versions[row["version_id"]]
                if row["version_id"] not in choice["versions"]:
                    raise ValueError("replacement is not a declared choice alternative")
                allowed = set(choice["segment_ids"]) | set(version["segment_ids"])
                identity = [row["kind"], row["choice_id"], row["version_id"]]
                uses = [u for u in concepts["uses"] if u["selector"] == dict(kind="CHOICE", id=row["choice_id"])]
                consumers = [dict(source_id=m["mental"]["source_id"], model_id=m["mental"]["id"],
                                  argument_id=m["argument"]["id"], premise_id=b["premise_id"], use_id=b["use_id"])
                    for m, bindings in zip(program["base_program"]["models"], program["concept_bindings"])
                    for b in bindings if b["use_id"] in {u["id"] for u in uses}]
                binding = dict(namespace=concepts["namespace"], scope=version["scope"],
                    concept_key=version["concept_key"], frame_kind=version["frame_kind"],
                    semantics=semantic_definition(version), active_assumptions=version["active_assumptions"],
                    uses=uses, consumers=consumers)
            elif row.get("kind") in ("PREMISE_RETRACT", "RULE_RETRACT"):
                self._keys(row, "kind source_id model_id argument_id item_id segment_ids")
                _, m = models[(row["source_id"], row["model_id"])]
                argument = m["argument"]
                if argument["id"] != row["argument_id"]:
                    raise ValueError("retraction argument namespace differs")
                category = "premises" if row["kind"] == "PREMISE_RETRACT" else "rules"
                item = next(p for p in argument[category] if p["id"] == row["item_id"])
                allowed = set(item["segment_ids"])
                identity = [row[k] for k in ("kind", "source_id", "model_id", "argument_id", "item_id")]
                binding = dict(namespace=concepts["namespace"], source_id=row["source_id"],
                    model_id=row["model_id"], argument_id=row["argument_id"], argument_source_id=argument["source_id"],
                    argument_scope=digest([argument["source_id"], argument["id"], argument["frame_kind"]]), frame_kind=argument["frame_kind"],
                    item=deepcopy(item), source_bindings={k: argument["source_bindings"][k] for k in sorted(allowed)})
            else:
                raise ValueError("unsupported edit kind")
            refs = self._strings(row["segment_ids"], 64)
            if not refs or not set(refs) <= allowed:
                raise ValueError("edit must cite its actual declared source anchors")
            normalized = dict(row, segment_ids=sorted(set(refs)))
            if row["kind"] == "CHOICE_REPLACE" and baseline[row["choice_id"]] == row["version_id"]:
                ignored.append(dict(edit=normalized, reason="EXACT_BASELINE_NO_OP"))
                continue
            key = "joint-edit:" + digest(identity)
            if key in atoms:
                atoms[key]["edit"]["segment_ids"] = sorted(set(atoms[key]["edit"]["segment_ids"]) | set(refs))
            else:
                atoms[key] = dict(atom_id=key, edit=normalized, binding=binding, cost=1)
        if len(atoms) > 12:
            raise ValueError("at most twelve distinct declared edit atoms")
        program.update(schema=SCHEMA, candidate=raw, candidate_identity=sha256(raw.encode()).hexdigest(),
            joint_changes=dict(language=LANGUAGE, cost_unit="ONE_DECLARED_SELECTOR_REPLACEMENT_OR_SCOPED_ACTIVATION_RETRACTION",
                baseline=dict(sorted(baseline.items())), target=target, target_model_index=index,
                atoms=[atoms[k] for k in sorted(atoms)], ignored_edits=sorted(ignored, key=codec.canonical),
                adoption_authorized=False),
            validation_units=node_count(data))
        return freeze(program)


def verify_joint_program(program, snapshot, allowance):
    from hcl.semantics.segments import SourceSegment
    from hcl.semantics.judgment_compiler import verify_program_bindings
    data = thaw(program)
    if data["host_context"] != host_context(snapshot) or data["source_versions"] != dict(snapshot.source_versions):
        raise ValueError("joint edit host or sources differ")
    verify_program_bindings(data["base_program"], snapshot, allowance)
    segments = tuple(SourceSegment(**s) for s in data["base_program"]["segments"])
    expected = JointChangeCompiler().compile(snapshot, segments, data["candidate"],
        replace(allowance, max_output_bytes=1048576))
    if codec.canonical(thaw(expected)) != codec.canonical(data):
        raise ValueError("joint edit source, target or finite language changed")
