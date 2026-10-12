"""Compile source-bound structured argument proposals, never acceptance labels."""

from dataclasses import asdict
from hashlib import sha256
from hcl.memory.codec import canonical
import json

from hcl.kernel.types import HCLFailure, freeze
from hcl.operators.argumentation import Literal, Premise, Rule, Theory
from hcl.semantics.compiler import SemanticCompiler

SCHEMA = "hcl-argument-candidates-1"
MODEL_FIELDS = "id source_id frame_kind assumptions active_assumptions unmodeled_segments literals premises rules priorities queries"
FRAMES = {
    "SOURCE_DISCOURSE",
    "QUOTATION",
    "HYPOTHETICAL",
    "COUNTERFACTUAL",
    "INTERPRETATION",
}


def argument_theory(model):
    scope = (
        "argument-scope:"
        + sha256(
            canonical([model["source_id"], model["id"], model["frame_kind"]]).encode()
        ).hexdigest()
    )
    literals = {
        row["id"]: Literal(row["atom"], row["negative"], scope, row["kind"])
        for row in model["literals"]
    }
    return (
        Theory(
            tuple(
                Premise(
                    row["id"],
                    literals[row["literal"]],
                    row["ordinary"],
                    frozenset((*model["assumptions"], *row["assumptions"])),
                )
                for row in model["premises"]
            ),
            tuple(
                Rule(
                    row["id"],
                    tuple(literals[key] for key in row["premises"]),
                    literals[row["conclusion"]],
                    row["strict"],
                    frozenset((*model["assumptions"], *row["assumptions"])),
                )
                for row in model["rules"]
            ),
            tuple((row["better"], row["worse"]) for row in model["priorities"]),
            frozenset(model["active_assumptions"]),
        ),
        literals,
    )


def argument_context(snapshot, question):
    from hcl.semantics.segments import segment_snapshot

    return dict(
        schema="hcl-argument-context-1",
        candidate_schema=SCHEMA,
        purpose="PROPOSE_SOURCE_ANCHORED_PREMISES_RULES_AND_PRIORITIES_NOT_ACCEPTANCE_LABELS",
        model_fields=MODEL_FIELDS.split(),
        literal_fields="id atom negative kind segment_ids".split(),
        premise_fields="id literal ordinary assumptions segment_ids".split(),
        rule_fields="id premises conclusion strict assumptions segment_ids".split(),
        priority_fields="better worse segment_ids".split(),
        query_fields="id literal preferred critical_candidates segment_ids".split(),
        instructions="Reconstruct competing scoped argument models. Separate strict and defeasible rules and ordinary premises. "
        "Negative RULE_APPLICABLE literals explicitly undercut the named rule. Priorities require source anchors. "
        "Do not supply accepted/rejected labels, attack matrices, extensions or precomputed sensitivity. "
        "source_id is the model namespace source, not attribution of every item; anchor it in that source. "
        "Items may cite multiple authorized sources through their exact segment_ids. "
        "Keep unmodeled material and explicit assumptions; source grounding is not premise truth.",
        source_input_versions=dict(snapshot.source_versions),
        segments=[asdict(segment) for segment in segment_snapshot(snapshot, question)],
    )


class ArgumentCompiler(SemanticCompiler):
    def _invalid(self, field="candidate"):
        return HCLFailure(
            "INVALID_REQUEST",
            "argument_compile",
            "INVALID_ARGUMENT_CANDIDATE",
            field,
            "The proposed argument model violates its source-bound executable dialect.",
        )

    def _limit(self, field):
        return HCLFailure(
            "BUDGET_EXHAUSTED",
            "argument_compile",
            "ARGUMENT_COMPILE_BOUND",
            field,
            "The proposed argument model exceeds its finite compilation allowance.",
        )

    def compile(self, snapshot, segments, raw_candidate, allowance):
        try:
            return self._compile(snapshot, segments, raw_candidate, allowance)
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            RecursionError,
            OverflowError,
        ):
            raise self._invalid() from None

    def _compile(self, snapshot, segments, raw, allowance):
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
        self._keys(data, "schema models")
        if (
            data["schema"] != SCHEMA
            or type(data["models"]) is not list
            or not 1 <= len(data["models"]) <= 4
        ):
            raise self._invalid("schema")
        by_id = {s.segment_id: s for s in segments}
        source_ids = {s.segment_id for s in segments if s.kind == "SOURCE"}
        if not source_ids or len(by_id) != len(segments):
            raise self._invalid("source_segments")
        used = set()
        identities = set()

        def refs(keys, query=False):
            keys = self._strings(keys)
            if (
                not keys
                or not set(keys) <= set(by_id)
                or (not query and not set(keys) <= source_ids)
            ):
                raise self._invalid("segment_ids")
            used.update(set(keys) & source_ids)
            model_used.update(keys)

        def rows(model, key, maximum, minimum=0):
            value = model[key]
            if type(value) is not list or not minimum <= len(value) <= maximum:
                raise self._limit(key)
            return value

        for model in data["models"]:
            self._keys(model, MODEL_FIELDS)
            model_used = set()
            identity = self._text(model["id"], 128)
            if (
                model["source_id"] not in snapshot.source_versions
                or model["frame_kind"] not in FRAMES
            ):
                raise self._invalid("source_frame")
            if (model["source_id"], identity) in identities:
                raise self._invalid("model_id")
            identities.add((model["source_id"], identity))
            self._strings(model["assumptions"])
            active = set(self._strings(model["active_assumptions"]))
            unmodeled = self._strings(model["unmodeled_segments"])
            if not set(unmodeled) <= source_ids:
                raise self._invalid("unmodeled_segments")
            used.update(unmodeled)
            literals = set()
            for row in rows(model, "literals", 128, 1):
                self._keys(row, "id atom negative kind segment_ids")
                key = self._text(row["id"], 128)
                self._text(row["atom"], 128)
                if (
                    key in literals
                    or type(row["negative"]) is not bool
                    or row["kind"] not in ("CLAIM", "RULE_APPLICABLE")
                ):
                    raise self._invalid("literal")
                literals.add(key)
                refs(row["segment_ids"])
            declared = set(model["assumptions"])
            all_ids = set()
            rule_ids = set()
            for category in ("premises", "rules"):
                for row in rows(model, category, 64):
                    self._keys(
                        row,
                        (
                            "id literal ordinary assumptions segment_ids"
                            if category == "premises"
                            else "id premises conclusion strict assumptions segment_ids"
                        ),
                    )
                    key = self._text(row["id"], 128)
                    if key in all_ids:
                        raise self._invalid("item_id")
                    all_ids.add(key)
                    declared.update(self._strings(row["assumptions"]))
                    refs(row["segment_ids"])
                    if category == "premises":
                        if (
                            row["literal"] not in literals
                            or type(row["ordinary"]) is not bool
                        ):
                            raise self._invalid("premise")
                    else:
                        rule_ids.add(key)
                        members = self._strings(row["premises"], 8, unique=False)
                        if (
                            not members
                            or not set(members) <= literals
                            or row["conclusion"] not in literals
                            or type(row["strict"]) is not bool
                        ):
                            raise self._invalid("rule")
            if not active <= declared:
                raise self._invalid("active_assumptions")
            for literal in model["literals"]:
                if (
                    literal["kind"] == "RULE_APPLICABLE"
                    and literal["atom"] not in rule_ids
                ):
                    raise self._invalid("undercut_rule")
            for row in rows(model, "priorities", 128):
                self._keys(row, "better worse segment_ids")
                refs(row["segment_ids"])
                if row["better"] not in all_ids or row["worse"] not in all_ids:
                    raise self._invalid("priority")
            queries = set()
            for row in rows(model, "queries", 16, 1):
                self._keys(row, "id literal preferred critical_candidates segment_ids")
                key = self._text(row["id"], 128)
                refs(row["segment_ids"], query=True)
                if (
                    key in queries
                    or row["literal"] not in literals
                    or type(row["preferred"]) is not bool
                ):
                    raise self._invalid("query")
                queries.add(key)
                if not set(self._strings(row["critical_candidates"], 12)) <= all_ids:
                    raise self._invalid("sensitivity_items")
            argument_theory(model)
            if not any(
                by_id[key].source_id == model["source_id"] for key in model_used
            ):
                raise self._invalid("namespace_source_unanchored")
            # Host-created bindings: never accept attribution supplied by the model.
            model["source_bindings"] = {
                key: {
                    name: value
                    for name, value in asdict(by_id[key]).items()
                    if name != "text"
                }
                for key in sorted(model_used | set(unmodeled))
            }
            model["input_source_versions"] = {
                by_id[key].source_id: by_id[key].version
                for key in sorted(model_used | set(unmodeled))
                if key in source_ids
            }
        if not source_ids <= used:
            raise self._invalid("unaccounted_source_segments")
        return freeze(data)


def argument_source_segments(records, premise_ids, rule_ids):
    """Exact proof inputs, including the proposed meaning of its scoped literals."""
    literals = {row["id"]: row for row in records["literals"]}
    segments = set()
    for category, wanted in (("premises", set(premise_ids)), ("rules", set(rule_ids))):
        for row in records[category]:
            if row["id"] not in wanted:
                continue
            segments.update(row["segment_ids"])
            keys = (
                (row["literal"],)
                if category == "premises"
                else (*row["premises"], row["conclusion"])
            )
            for key in keys:
                segments.update(literals[key]["segment_ids"])
    return tuple(sorted(segments))
