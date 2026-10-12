"""Exact-source narrative fragments and explicit cross-fragment references.

A proposal supplies interpretation, never temporal answers or form counts.
Reading every packet establishes byte coverage, not semantic completeness.
"""

from dataclasses import asdict
from hashlib import sha256
import json

from hcl.kernel.types import HCLFailure, freeze, thaw
from hcl.memory import codec
from hcl.semantics.compiler import SemanticCompiler

SCHEMA = "hcl-literature-fragment-1"
COMPOSED = "hcl-literature-composed-1"
KINDS = frozenset(
    {
        "NARRATION",
        "QUOTATION",
        "THOUGHT",
        "FREE_INDIRECT",
        "HYPOTHETICAL",
        "COUNTERFACTUAL",
        "INTERPRETATION",
    }
)
FIELDS = "schema assumptions active_assumptions frames events mentions orders queries motifs variants comparisons analogies unmodeled_segments"


def literature_context(snapshot, question):
    from hcl.semantics.segments import segment_snapshot

    return dict(
        schema="hcl-literature-context-1",
        candidate_schema=SCHEMA,
        purpose="PROPOSE_SOURCE_BOUND_NARRATIVE_STRUCTURE_NOT_ANSWERS_COUNTS_OR_AESTHETIC_SCORES",
        fields=FIELDS.split(),
        frame_fields="id parent kind narrator focalizer segment_ids".split(),
        event_fields="id frame description assumptions segment_ids".split(),
        mention_fields="id event frame anchor".split(),
        order_fields="id left right strict assumptions segment_ids".split(),
        query_fields="id left right segment_ids".split(),
        motif_fields="id literal segment_ids".split(),
        variant_fields="id kind anchor replacement segment_ids".split(),
        reorder_variant_fields="id kind parts order segment_ids".split(),
        comparison_fields=["id", "task"],
        analogy_fields=["id", "task"],
        reference_fields=["fragment", "id"],
        anchor_fields=["segment_id", "start", "end", "quote"],
        instructions=(
            "References explicitly name the reading fragment ordinal and local ID. Equal names in distinct fragments are never merged. "
            "Frame parent may be null; narrator/focalizer may be null and are proposed labels, not private identities. "
            "Each event has a frame. Each mention has an exact original anchor and independently identifies the narrated event and presentation frame. "
            "Orders mean left EVENT time < right time when strict=true, otherwise <=. Never infer event chronology from source order. "
            "Cross-frame event clocks remain unresolved. Active assumptions must be declared in this fragment. "
            "Variants are DELETE, REPLACE or REORDER, explicitly hypothetical; their generated words never become source evidence. "
            "REORDER uses 2-16 exact original anchor parts in contiguous source order within one source and this packet, and order is a permutation of their zero-based indexes. It preserves all original pieces without adding words; it changes presentation, never establishes a new story-time relation. "
            "comparisons explicitly group a shared M04 discovery task across fragments by id; task uses hcl-discovery-candidates-1. Contexts/observations remain locally source-bound; a common grammar/search contract and target schema are required. "
            "analogies contains packet-local hcl-structural-candidates-1 tasks; base and target must both be supported by original packet spans. No remembered intertext is evidence. "
            "Use the packet coverage ordinal, retain unmodeled segments, and do not supply computed relations, counts, truth, reliability or beauty scores."
        ),
        source_input_versions=dict(snapshot.source_versions),
        segments=[asdict(s) for s in segment_snapshot(snapshot, question)],
    )


class LiteratureCompiler(SemanticCompiler):
    def _invalid(self, field="candidate"):
        return HCLFailure(
            "INVALID_REQUEST",
            "literature_compile",
            "INVALID_LITERATURE_FRAGMENT",
            field,
            "The proposed narrative fragment violates its exact-source contract.",
        )

    def _limit(self, field):
        return HCLFailure(
            "BUDGET_EXHAUSTED",
            "literature_compile",
            "LITERATURE_COMPILE_BOUND",
            field,
            "The narrative composition exceeds its explicit structural bound.",
        )

    def compile_fragment(self, snapshot, chunk, raw, allowance):
        try:
            return self._fragment(snapshot, chunk, raw, allowance)
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            RecursionError,
            OverflowError,
            UnicodeEncodeError,
        ):
            raise self._invalid() from None

    def _fragment(self, snapshot, chunk, raw, allowance):
        if type(raw) is not str or len(raw.encode()) > min(
            allowance.max_output_bytes, 1048576
        ):
            raise self._limit("candidate_bytes")

        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise self._invalid("duplicate_json_field")
                result[key] = value
            return result

        data = json.loads(
            raw,
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(
                self._invalid("nonfinite_json")
            ),
        )
        self._keys(data, FIELDS)
        if data["schema"] != SCHEMA:
            raise self._invalid("schema")
        sources = {s.segment_id: s for s in chunk.segments}
        if any(s.kind != "SOURCE" for s in sources.values()):
            raise self._invalid("source_segments")
        used = set()

        def refs(value):
            value = self._strings(value, 64)
            if not value or not set(value) <= set(sources):
                raise self._invalid("segment_ids")
            used.update(value)

        def ref(value):
            self._keys(value, "fragment id")
            if (
                type(value["fragment"]) is not int
                or not 0 <= value["fragment"] < chunk.total
            ):
                raise self._invalid("reference_fragment")
            self._text(value["id"], 128)

        def anchor(value):
            self._keys(value, "segment_id start end quote")
            segment = sources.get(value["segment_id"])
            if (
                segment is None
                or type(value["start"]) is not int
                or type(value["end"]) is not int
                or not segment.start <= value["start"] < value["end"] <= segment.end
                or type(value["quote"]) is not str
                or snapshot.immutable_views[segment.source_id].text[
                    value["start"] : value["end"]
                ]
                != value["quote"]
            ):
                raise self._invalid("original_anchor")
            used.add(segment.segment_id)

        assumptions = set(self._strings(data["assumptions"], 64))
        active = set(self._strings(data["active_assumptions"], 64))
        if not active <= assumptions:
            raise self._invalid("active_assumptions")

        def environment(values):
            if not set(self._strings(values, 64)) <= assumptions:
                raise self._invalid("assumptions")

        field_map = dict(
            frames="id parent kind narrator focalizer segment_ids",
            events="id frame description assumptions segment_ids",
            mentions="id event frame anchor",
            orders="id left right strict assumptions segment_ids",
            queries="id left right segment_ids",
            motifs="id literal segment_ids",
            variants="id kind anchor replacement segment_ids",
        )
        for field, keys in field_map.items():
            rows = data[field]
            if type(rows) is not list or len(rows) > 128:
                raise self._limit(field)
            seen = set()
            for row in rows:
                self._keys(
                    row,
                    (
                        "id kind parts order segment_ids"
                        if field == "variants"
                        and type(row) is dict
                        and row.get("kind") == "REORDER"
                        else keys
                    ),
                )
                self._text(row["id"], 128)
                if row["id"] in seen:
                    raise self._invalid("duplicate_" + field)
                seen.add(row["id"])
                if "segment_ids" in row:
                    refs(row["segment_ids"])
                if field == "frames":
                    if row["parent"] is not None:
                        ref(row["parent"])
                    if row["kind"] not in KINDS:
                        raise self._invalid("frame_kind")
                    for key in ("narrator", "focalizer"):
                        if row[key] is not None:
                            self._text(row[key], 256)
                elif field == "events":
                    ref(row["frame"])
                    self._text(row["description"], 512)
                    environment(row["assumptions"])
                elif field == "mentions":
                    ref(row["event"])
                    ref(row["frame"])
                    anchor(row["anchor"])
                elif field in ("orders", "queries"):
                    ref(row["left"])
                    ref(row["right"])
                    if field == "orders":
                        if type(row["strict"]) is not bool:
                            raise self._invalid("strict")
                        environment(row["assumptions"])
                elif field == "motifs":
                    self._text(row["literal"], 256)
                    if not any(
                        row["literal"] in sources[key].text
                        for key in row["segment_ids"]
                    ):
                        raise self._invalid("motif_anchor")
                elif field == "variants" and row["kind"] == "REORDER":
                    from hcl.operators.narrative_variants import reorder_text

                    if (
                        type(row["parts"]) is not list
                        or not 2 <= len(row["parts"]) <= 16
                    ):
                        raise self._invalid("reorder_parts")
                    for part in row["parts"]:
                        anchor(part)
                    source_ids = {
                        sources[p["segment_id"]].source_id for p in row["parts"]
                    }
                    if len(source_ids) != 1:
                        raise self._invalid("reorder_source")
                    reorder_text(
                        snapshot.immutable_views[next(iter(source_ids))].text,
                        row["parts"],
                        row["order"],
                    )
                elif field == "variants":
                    anchor(row["anchor"])
                    if (
                        row["kind"] not in ("DELETE", "REPLACE")
                        or type(row["replacement"]) is not str
                        or len(row["replacement"]) > 4096
                    ):
                        raise self._invalid("variant")
                    row["replacement"].encode()
                    if row["kind"] == "DELETE" and row["replacement"] != "":
                        raise self._invalid("delete_replacement")
        from hcl.semantics.discovery_compiler import DiscoveryCompiler

        if type(data["comparisons"]) is not list or len(data["comparisons"]) > 4:
            raise self._limit("comparisons")
        seen_comparisons = set()
        for comparison in data["comparisons"]:
            self._keys(comparison, "id task")
            self._text(comparison["id"], 128)
            if comparison["id"] in seen_comparisons:
                raise self._invalid("duplicate_comparison")
            seen_comparisons.add(comparison["id"])
            DiscoveryCompiler().compile(
                snapshot,
                chunk.segments,
                json.dumps(comparison["task"], ensure_ascii=False),
                allowance,
            )
            used.update(sources)
        from hcl.semantics.concept_compiler import ConceptCompiler

        if type(data["analogies"]) is not list or len(data["analogies"]) > 4:
            raise self._limit("analogies")
        analogy_ids = set()
        for analogy in data["analogies"]:
            self._keys(analogy, "id task")
            self._text(analogy["id"], 128)
            if analogy["id"] in analogy_ids:
                raise self._invalid("duplicate_analogy")
            analogy_ids.add(analogy["id"])
            ConceptCompiler().compile(
                snapshot,
                chunk.segments,
                json.dumps(analogy["task"], ensure_ascii=False),
                allowance,
            )
            used.update(sources)
        unmodeled = set(self._strings(data["unmodeled_segments"], 1024))
        if not unmodeled <= set(sources) or used | unmodeled != set(sources):
            raise self._invalid("source_coverage")
        data["fragment"] = chunk.ordinal
        data["source_segments"] = [
            {key: value for key, value in asdict(s).items() if key != "text"}
            for s in chunk.segments
        ]
        return freeze(data)

    def compose(self, snapshot, candidates, allowance):
        """All inputs are the durably compiled packet responses, in exact order."""
        fragments = [
            thaw(self.compile_fragment(snapshot, chunk, raw, allowance))
            for chunk, raw in candidates
        ]
        if not fragments or [r["fragment"] for r in fragments] != list(
            range(len(fragments))
        ):
            raise self._invalid("fragment_coverage")
        if any(chunk.total != len(fragments) for chunk, raw in candidates):
            raise self._invalid("fragment_coverage")
        result = dict(
            schema=COMPOSED,
            source_versions=dict(snapshot.source_versions),
            fragments=fragments,
        )
        for name, limit in (
            ("frames", 128),
            ("events", 128),
            ("mentions", 128),
            ("orders", 512),
            ("queries", 256),
            ("motifs", 64),
            ("variants", 16),
        ):
            if sum(len(row[name]) for row in fragments) > limit:
                raise self._limit("composed_" + name)
        # Persisted model proposals keep exact byte anchors, no inferred entity
        # identity or narrator authority. Global reference validation is separate
        # from local parsing and cannot repair a random final packet on failure.
        registry = {
            name: {
                (f["fragment"], row["id"]): row for f in fragments for row in f[name]
            }
            for name in ("frames", "events")
        }
        unresolved = []

        def key(value):
            return (value["fragment"], value["id"])

        def require(value, kind, where):
            if key(value) not in registry[kind]:
                unresolved.append(dict(at=where, target=value, kind=kind))

        for f in fragments:
            for row in f["frames"]:
                if row["parent"] is not None:
                    require(
                        row["parent"], "frames", [f["fragment"], "frames", row["id"]]
                    )
            for row in f["events"]:
                require(row["frame"], "frames", [f["fragment"], "events", row["id"]])
            for row in f["mentions"]:
                require(row["frame"], "frames", [f["fragment"], "mentions", row["id"]])
                require(row["event"], "events", [f["fragment"], "mentions", row["id"]])
            for field in ("orders", "queries"):
                for row in f[field]:
                    for side in ("left", "right"):
                        require(
                            row[side], "events", [f["fragment"], field, row["id"], side]
                        )
        # Cycle detection walks the declared frame ancestry; unresolved parents
        # stay unresolved, never implicitly become root narration.
        for start in registry["frames"]:
            seen = set()
            here = start
            while here in registry["frames"]:
                if here in seen:
                    raise self._invalid("cyclic_frame_ancestry")
                seen.add(here)
                parent = registry["frames"][here]["parent"]
                if parent is None:
                    break
                here = key(parent)
        from hcl.semantics.narrative_hypotheses import compose_comparisons

        result["comparisons"] = compose_comparisons(
            snapshot, fragments, candidates, allowance
        )
        from hcl.semantics.concept_compiler import ConceptCompiler

        result["analogies"] = []
        for fragment, (chunk, raw) in zip(fragments, candidates):
            for analogy in fragment["analogies"]:
                result["analogies"].append(
                    dict(
                        id="narrative-analogy:"
                        + sha256(
                            codec.dumps([fragment["fragment"], analogy["id"]])
                        ).hexdigest(),
                        fragment=fragment["fragment"],
                        local_id=analogy["id"],
                        program=thaw(
                            ConceptCompiler().compile(
                                snapshot,
                                chunk.segments,
                                json.dumps(analogy["task"], ensure_ascii=False),
                                allowance,
                            )
                        ),
                    )
                )
        if len(result["analogies"]) > 16:
            raise self._limit("composed_analogies")
        result["unresolved_references"] = unresolved
        result["candidate_identity"] = sha256(codec.dumps(result)).hexdigest()
        return freeze(result)

    def compile_model(self, snapshot, ast, allowance):
        from hcl.runtime.context import ContextCompiler
        from hcl.runtime.reading_fragments import validated_partition, materialize

        try:
            data = thaw(ast)
            self._keys(data, "question plan returns")
            if type(data["question"]) is not str or type(data["returns"]) is not list:
                raise self._invalid("composition_fields")
            selected = validated_partition(snapshot, data["question"], data["plan"])
            if data["plan"]["purpose"] != "literature_compile" or len(
                data["returns"]
            ) != len(data["plan"]["fragments"]):
                raise self._invalid("composition_coverage")
            compiler = ContextCompiler()
            candidates = []
            for ordinal, raw in enumerate(data["returns"]):
                chunk, wire = materialize(
                    compiler, snapshot, data["question"], selected, ordinal
                )
                candidates.append((chunk, raw))
            return self.compose(snapshot, tuple(candidates), allowance)
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            RecursionError,
            OverflowError,
            UnicodeEncodeError,
        ):
            raise self._invalid("composition") from None
