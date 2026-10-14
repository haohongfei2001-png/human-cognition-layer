"""Versioned M12 -> M13/M14 contract, leaving shipped v1 certificates intact."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
from hashlib import sha256

from hcl.kernel.types import freeze, thaw
from hcl.memory import codec
from hcl.semantics.concept_version_compiler import ConceptVersionCompiler, digest, host_context
from hcl.semantics.judgment_compiler import JudgmentCompiler, verify_program_bindings

SCHEMA = "hcl-judgment-candidates-2"


class ConceptJudgmentCompiler(JudgmentCompiler):
    def compile(self, snapshot, segments, raw, allowance):
        try:
            return self._compile_concepts(snapshot, segments, raw, allowance)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError, OverflowError, StopIteration):
            raise self._invalid("concept_versions") from None

    def _compile_concepts(self, snapshot, segments, raw, allowance):
        if type(raw) is not str or len(raw.encode()) > min(allowance.max_output_bytes, 1048576):
            raise self._limit("candidate_bytes")
        def unique(pairs):
            out = {}
            for k, v in pairs:
                if k in out:
                    raise ValueError("duplicate candidate field")
                out[k] = v
            return out
        data = json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite value")))
        self._keys(data, "schema models concepts")
        if data["schema"] != SCHEMA or type(data["models"]) is not list or not 1 <= len(data["models"]) <= 4:
            raise ValueError("finite v2 judgment models required")
        base = deepcopy(data)
        bindings = []
        for model in base["models"]:
            self._keys(model, "mental interaction argument facts fact_bindings decisions concept_bindings")
            bindings.append(model.pop("concept_bindings"))
        base.pop("concepts")
        base["schema"] = "hcl-judgment-candidates-1"
        base_program = thaw(JudgmentCompiler()._compile_judgment(snapshot, segments, json.dumps(base, ensure_ascii=False), allowance))
        concepts = thaw(ConceptVersionCompiler().compile_data(snapshot, segments, data["concepts"]))
        uses = {u["id"]: u for u in concepts["uses"]}
        refs = {s.segment_id for s in segments if s.kind == "SOURCE"}
        checked_pins = set()
        for model, group in zip(base_program["models"], bindings):
            if type(group) is not list or len(group) > 32:
                raise ValueError("bounded conceptual premise bindings required")
            premises = {p["id"]: p for p in model["argument"]["premises"]}
            literals = {l["id"]: l for l in model["argument"]["literals"]}
            already = {b["premise_id"] for b in model["fact_bindings"]}
            atoms, bound = {}, set()
            for binding in group:
                self._keys(binding, "premise_id use_id expected segment_ids")
                if (binding["premise_id"] in already | bound or binding["premise_id"] not in premises
                        or binding["use_id"] not in uses or type(binding["expected"]) is not bool):
                    raise ValueError("unique actual concept classification binding required")
                spans = self._strings(binding["segment_ids"], 64)
                if not spans or not set(spans) <= refs:
                    raise ValueError("concept binding source required")
                bound.add(binding["premise_id"])
                use = uses[binding["use_id"]]
                literal = literals[premises[binding["premise_id"]]["literal"]]
                if (literal["kind"] != "CLAIM" or literal["negative"] != (not binding["expected"])
                        or use["frame_kind"] != model["mental"]["frame_kind"]):
                    raise ValueError("concept polarity/frame changed or undercut used as membership")
                atom = (literal["kind"], literal["atom"])
                if atoms.setdefault(atom, use["id"]) != use["id"]:
                    raise ValueError("concept literal aliases have different uses")
                plans = {p["id"]: p for p in model["mental"]["plans"]}
                if any(use["at"] > plans[d["plan_id"]]["at"] for d in model["decisions"]):
                    raise ValueError("future concept classification at decision")
                if use["commitment"] is not None:
                    checked_pins.add(use["id"])
                    pin = use["commitment"]
                    promise = next(c for c in model["interaction"]["commitments"] if c["id"] == pin["id"])
                    offer = next(u for u in model["interaction"]["utterances"] if u["id"] == promise["offer_id"])
                    if pin["terms_version"] != promise["version"] or use["at"] != offer["at"]:
                        raise ValueError("original commitment terms version or use time changed")
                    if not set(use["segment_ids"]) & set(promise["segment_ids"]):
                        raise ValueError("commitment conceptual use must cite original terms")
            for premise in premises.values():
                l = literals[premise["literal"]]
                if (l["kind"], l["atom"]) in atoms and premise["id"] not in bound:
                    raise ValueError("unbound alias bypasses concept classification")
            for rule in model["argument"]["rules"]:
                l = literals[rule["conclusion"]]
                if (l["kind"], l["atom"]) in atoms:
                    raise ValueError("concept membership cannot be supplied by a parallel rule")
        if {u["id"] for u in uses.values() if u["commitment"] is not None} - checked_pins:
            raise ValueError("commitment use needs an actual bound M07 consumer")
        return freeze(dict(schema=SCHEMA, candidate=raw, candidate_identity=sha256(raw.encode()).hexdigest(),
            base_program=base_program, concepts=concepts, concept_bindings=bindings,
            host_context=host_context(snapshot), source_versions=dict(snapshot.source_versions)))


def concept_judgment_qualifications(program):
    from hcl.semantics.judgment_compiler import judgment_qualifications
    assumptions, residuals = judgment_qualifications(program["base_program"])
    concepts = program["concepts"]
    return (tuple(sorted(set(assumptions) | {a for v in (*concepts["versions"], *concepts["cases"])
                                           for a in v["active_assumptions"]})),
            tuple(sorted(set(residuals) | set(concepts["unmodeled_segments"]))))


def verify_concept_program(program, snapshot, allowance):
    from hcl.semantics.segments import SourceSegment
    data = thaw(program)
    if data["host_context"] != host_context(snapshot):
        raise ValueError("concept program belongs to another host namespace")
    verify_program_bindings(data["base_program"], snapshot, allowance)
    segments = tuple(SourceSegment(**s) for s in data["base_program"]["segments"])
    expected = ConceptJudgmentCompiler().compile(snapshot, segments, data["candidate"],
                                                 replace(allowance, max_output_bytes=1048576))
    if codec.canonical(thaw(expected)) != codec.canonical(data):
        raise ValueError("concept semantic or source binding changed")
