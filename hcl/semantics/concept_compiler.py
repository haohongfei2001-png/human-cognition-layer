"""Source-anchored structural interpretations, never solved correspondences."""

from dataclasses import asdict
from hashlib import sha256
import json
from hcl.kernel.types import HCLFailure, freeze
from hcl.memory import codec
from hcl.operators.structure_mapping import _domain
from hcl.semantics.compiler import SemanticCompiler

SCHEMA = "hcl-structural-candidates-1"
FIELDS = "id assumptions active_assumptions base target compatibilities max_mappings unmodeled_segments"


def concept_context(snapshot, question):
    from hcl.semantics.segments import segment_snapshot

    return dict(
        schema="hcl-structural-context-1",
        candidate_schema=SCHEMA,
        purpose="PROPOSE_SOURCE_BOUND_RELATIONS_NOT_MAPPINGS_OR_TRANSFER_VERDICTS",
        model_fields=FIELDS.split(),
        induction_fields="id concept_key purpose assumptions active_assumptions positive negative unmodeled_segments".split(),
        example_fields="id term assumptions segment_ids".split(),
        term_fields="kind sort symbol arguments".split(),
        domain_fields=["entities", "predicates", "facts"],
        entity_fields="id type segment_ids".split(),
        predicate_fields="id kind arguments segment_ids".split(),
        fact_fields="id predicate arguments negated assumptions segment_ids".split(),
        reference_fields=["kind", "id"],
        compatibility_fields="base target assumptions segment_ids".split(),
        instructions="Keep base and target source assertions distinct. Predicate kinds are RELATION or ATTRIBUTE; argument sorts are FACT or ENTITY:<declared type>. "
        "FACT arguments may reference earlier or later explicit facts but cannot form expression cycles. Entity labels create no cross-domain identity. "
        "compatibilities declare semantic hypotheses about predicates with equal argument sorts, not solved object/fact matches. "
        "Use explicit negative target evidence; a missing target assertion does not refute a transfer. List inactive assumptions and unmodeled source segments. "
        "inductions optionally supplies grounded typed TERM examples and explicit negative/boundary cases, never a solved pattern. Equal symbols require a common signature; generated variables are solver output only. "
        "Every semantic row requires actual SOURCE anchors; question text and remembered intertext are not evidence. No mapping, fit, confidence or aesthetic score fields are accepted.",
        source_input_versions=dict(snapshot.source_versions),
        segments=[asdict(s) for s in segment_snapshot(snapshot, question)],
    )


class ConceptCompiler(SemanticCompiler):
    def _invalid(self, field="candidate"):
        return HCLFailure(
            "INVALID_REQUEST",
            "concept_compile",
            "INVALID_STRUCTURAL_MODEL",
            field,
            "The structural proposal violates its source-bound typed contract.",
        )

    def compile(self, snapshot, segments, raw, allowance):
        try:
            return self._compile(snapshot, segments, raw, allowance)
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

    def _compile(self, snapshot, segments, raw, allowance):
        if type(raw) is not str or len(raw.encode()) > min(
            allowance.max_output_bytes, 1048576
        ):
            raise self._invalid("candidate_bytes")

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
        self._keys(data, "schema models inductions")
        if (
            data["schema"] != SCHEMA
            or type(data["models"]) is not list
            or not 0 <= len(data["models"]) <= 8
            or type(data["inductions"]) is not list
            or len(data["inductions"]) > 8
            or not (data["models"] or data["inductions"])
        ):
            raise self._invalid("models")
        sources = {s.segment_id: s for s in segments if s.kind == "SOURCE"}
        ids, models = set(), []
        for model in data["models"]:
            self._keys(model, FIELDS)
            self._text(model["id"], 128)
            if model["id"] in ids:
                raise self._invalid("duplicate_model")
            ids.add(model["id"])
            assumptions = set(self._strings(model["assumptions"], 64))
            active = set(self._strings(model["active_assumptions"], 64))
            if (
                not active <= assumptions
                or type(model["max_mappings"]) is not int
                or not 1 <= model["max_mappings"] <= 64
            ):
                raise self._invalid("assumptions_or_output_bound")
            used = set()

            def anchors(value):
                values = set(self._strings(value, 64))
                if not values or not values <= set(sources):
                    raise self._invalid("source_anchors")
                used.update(values)

            def environment(value):
                if not set(self._strings(value, 64)) <= assumptions:
                    raise self._invalid("assumption_environment")

            clean = {}
            for side in ("base", "target"):
                domain = model[side]
                self._keys(domain, "entities predicates facts")
                clean[side] = {}
                for name, fields, limit in (
                    ("entities", "id type segment_ids", 16),
                    ("predicates", "id kind arguments segment_ids", 16),
                    (
                        "facts",
                        "id predicate arguments negated assumptions segment_ids",
                        32,
                    ),
                ):
                    if type(domain[name]) is not list or len(domain[name]) > limit:
                        raise self._invalid("domain_bound")
                    clean[side][name] = []
                    for row in domain[name]:
                        self._keys(row, fields)
                        anchors(row["segment_ids"])
                        if name == "facts":
                            environment(row["assumptions"])
                        clean[side][name].append(
                            {
                                k: v
                                for k, v in row.items()
                                if k not in ("segment_ids", "assumptions")
                            }
                        )
                _domain(clean[side])
            if (
                type(model["compatibilities"]) is not list
                or len(model["compatibilities"]) > 128
            ):
                raise self._invalid("predicate_compatibilities")
            bp = {r["id"]: r for r in clean["base"]["predicates"]}
            tp = {r["id"]: r for r in clean["target"]["predicates"]}
            pairs = set()
            for row in model["compatibilities"]:
                self._keys(row, "base target assumptions segment_ids")
                anchors(row["segment_ids"])
                environment(row["assumptions"])
                pair = (row["base"], row["target"])
                if (
                    pair in pairs
                    or pair[0] not in bp
                    or pair[1] not in tp
                    or bp[pair[0]]["kind"] != tp[pair[1]]["kind"]
                    or bp[pair[0]]["arguments"] != tp[pair[1]]["arguments"]
                ):
                    raise self._invalid("predicate_compatibility")
                pairs.add(pair)
            unmodeled = set(self._strings(model["unmodeled_segments"], 1024))
            if not unmodeled <= set(sources) or used | unmodeled != set(sources):
                raise self._invalid("source_coverage")
            models.append(model)
        from hcl.operators.concept_induction import validate_term

        inductions, induction_ids = [], set()
        for proposal in data["inductions"]:
            self._keys(
                proposal,
                "id concept_key purpose assumptions active_assumptions positive negative unmodeled_segments",
            )
            self._text(proposal["id"], 128)
            self._text(proposal["concept_key"], 128)
            self._text(proposal["purpose"], 512)
            if proposal["id"] in induction_ids:
                raise self._invalid("duplicate_induction")
            induction_ids.add(proposal["id"])
            assumptions = set(self._strings(proposal["assumptions"], 64))
            active = set(self._strings(proposal["active_assumptions"], 64))
            if not active <= assumptions:
                raise self._invalid("induction_assumptions")
            signatures, example_ids, used, sorts = {}, set(), set(), set()
            for label, limit in (("positive", 16), ("negative", 32)):
                examples = proposal[label]
                if (
                    type(examples) is not list
                    or len(examples) > limit
                    or (label == "positive" and not examples)
                ):
                    raise self._invalid("induction_examples")
                for row in examples:
                    self._keys(row, "id term assumptions segment_ids")
                    self._text(row["id"], 128)
                    if row["id"] in example_ids:
                        raise self._invalid("duplicate_example")
                    example_ids.add(row["id"])
                    if not set(self._strings(row["assumptions"], 64)) <= assumptions:
                        raise self._invalid("example_assumptions")
                    selected = set(self._strings(row["segment_ids"], 64))
                    if not selected or not selected <= set(sources):
                        raise self._invalid("example_source")
                    used.update(selected)
                    for symbol, signature in validate_term(row["term"]).items():
                        if signatures.setdefault(symbol, signature) != signature:
                            raise self._invalid("term_signature")
                    sorts.add(row["term"]["sort"])
            unmodeled = set(self._strings(proposal["unmodeled_segments"], 1024))
            if (
                len(sorts) != 1
                or not unmodeled <= set(sources)
                or used | unmodeled != set(sources)
            ):
                raise self._invalid("induction_coverage_or_sort")
            inductions.append(proposal)
        return freeze(
            dict(
                schema=SCHEMA,
                models=models,
                inductions=inductions,
                concept_namespace=sha256(
                    codec.dumps([snapshot.session_id, snapshot.principal])
                ).hexdigest(),
                source_versions=dict(snapshot.source_versions),
                source_bindings={
                    key: {k: v for k, v in asdict(s).items() if k != "text"}
                    for key, s in sources.items()
                },
                input_identity=sha256(codec.dumps(data)).hexdigest(),
            )
        )
