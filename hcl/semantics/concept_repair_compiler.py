"""Additive v3 requests finite counterexample edits; cannot supply predictions."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from hcl.kernel.types import freeze, thaw
from hcl.memory import codec
from hcl.semantics.judgment_concept_compiler import ConceptJudgmentCompiler
from hcl.semantics.concept_version_compiler import host_context

SCHEMA = "hcl-judgment-candidates-3"


class ConceptRepairCompiler(ConceptJudgmentCompiler):
    def _compile_concepts(self, snapshot, segments, raw, allowance):
        if type(raw) is not str or len(raw.encode()) > min(allowance.max_output_bytes,1048576):
            raise self._limit("candidate_bytes")
        def unique(pairs):
            out = {}
            for k,v in pairs:
                if k in out: raise ValueError("duplicate candidate field")
                out[k] = v
            return out
        data = json.loads(raw,object_pairs_hook=unique,
            parse_constant=lambda _:(_ for _ in ()).throw(ValueError("nonfinite value")))
        self._keys(data,"schema models concepts repairs")
        if data["schema"]!=SCHEMA or type(data["repairs"]) is not list or len(data["repairs"])!=1:
            raise ValueError("one finite explicitly scoped repair request required")
        base = deepcopy(data)
        repairs = base.pop("repairs")
        base["schema"]="hcl-judgment-candidates-2"
        program = thaw(ConceptJudgmentCompiler().compile(snapshot,segments,json.dumps(base,ensure_ascii=False),allowance))
        concepts = program["concepts"]
        for row in repairs:
            self._keys(row,"id version_id choice_id segment_ids")
            for field in ("id","version_id","choice_id"): self._text(row[field],64)
            refs=self._strings(row["segment_ids"],64)
            if not refs or not set(refs)<=set(concepts["source_bindings"]):
                raise ValueError("repair requires original source anchors")
            version=next(v for v in concepts["versions"] if v["id"]==row["version_id"])
            choice=next(c for c in concepts["choices"] if c["id"]==row["choice_id"])
            if len(concepts["choices"])!=1 or len(version["criteria"])!=1 or row["version_id"] not in choice["versions"]:
                raise ValueError("repair requires one explicit criterion and one choice")
            if concepts["constraints"] or len(choice["versions"])>2:
                raise ValueError("joint repair constraints require explicit recompilation")
            positive=version["criteria"][0]["positive"]
            if len({codec.canonical(r["term"]) for r in positive})>5:
                raise ValueError("finite partition language bound exceeded")
        program.update(schema=SCHEMA,candidate=raw,candidate_identity=sha256(raw.encode()).hexdigest(),repairs=repairs)
        return freeze(program)


def verify_repair_program(program,snapshot,allowance):
    from hcl.semantics.segments import SourceSegment
    from hcl.semantics.judgment_compiler import verify_program_bindings
    data=thaw(program)
    if data["host_context"]!=host_context(snapshot):
        raise ValueError("repair program host mismatch")
    verify_program_bindings(data["base_program"],snapshot,allowance)
    segments=tuple(SourceSegment(**s) for s in data["base_program"]["segments"])
    expected=ConceptRepairCompiler().compile(snapshot,segments,data["candidate"],replace(allowance,max_output_bytes=1048576))
    if codec.canonical(thaw(expected))!=codec.canonical(data):
        raise ValueError("repair proposal binding changed")
