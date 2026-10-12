"""Typed explanation targets and mechanism ASTs for the shared M04 discoverer."""

from dataclasses import asdict
import json

from hcl.kernel.types import HCLFailure, freeze, thaw
from hcl.operators.abduction import (
    evaluate_expression,
    expression_size,
    identity,
    context_identity,
)
from hcl.semantics.compiler import SemanticCompiler
from hcl.semantics.model_compiler import LocalModelCompiler
from hcl.semantics.argument_compiler import ArgumentCompiler

SCHEMA = "hcl-discovery-candidates-1"
ADAPTERS = {"mental-scene-1", "argument-model-1"}
PROGRAM_FIELDS = "id adapter latent observe transition constraint predict"
CONTEXT_FIELDS = "id adapter template features feature_segments segment_ids"
CHANNELS = {"seen_by", "received_by", "understood_by", "trusted_by"}
PREDICTIONS = {
    "mental-scene-1": {
        "belief.possible_values",
        "plan.best_actions",
        "causal.possible_values",
    },
    "argument-model-1": {"argument.acceptance"},
}


def discovery_context(snapshot, question):
    from hcl.semantics.segments import segment_snapshot

    return dict(
        schema="hcl-discovery-context-1",
        candidate_schema=SCHEMA,
        purpose="PROPOSE_EXPLAINANDA_AND_MECHANISMS_NOT_PREDICTED_ANSWERS",
        program_fields=PROGRAM_FIELDS.split(),
        context_fields=CONTEXT_FIELDS.split(),
        instructions="Separate source-observed explanation targets from conditioning features. Supply bounded source-bound mental or argument templates, latent parameters, observation-channel conditions, typed mechanism bindings, constraints and actual solver query selectors. Never supply computed predictions, fit scores or posterior probabilities. Hypothetical probes are not observed evidence. A common residual-guided editor will recompute the actual models. Mark omissions and uncertain reconstruction explicitly.",
        source_input_versions=dict(snapshot.source_versions),
        segments=[asdict(s) for s in segment_snapshot(snapshot, question)],
    )


class DiscoveryCompiler(SemanticCompiler):
    def _invalid(self, field="candidate"):
        return HCLFailure(
            "INVALID_REQUEST",
            "discovery_compile",
            "INVALID_DISCOVERY_CANDIDATE",
            field,
            "The proposed explanation task violates its source-bound mechanism contract.",
        )

    def _limit(self, field):
        return HCLFailure(
            "BUDGET_EXHAUSTED",
            "discovery_compile",
            "DISCOVERY_COMPILE_BOUND",
            field,
            "The proposed explanation task exceeds its bounded compilation allowance.",
        )

    def compile(self, snapshot, segments, raw_candidate, allowance):
        try:
            return self._compile_discovery(snapshot, segments, raw_candidate, allowance)
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            RecursionError,
            OverflowError,
            ZeroDivisionError,
            StopIteration,
        ):
            raise self._invalid() from None

    def _compile_discovery(self, snapshot, segments, raw, allowance):
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
        self._keys(
            data,
            "schema contexts observations probes programs grammar search unmodeled_segments",
        )
        if data["schema"] != SCHEMA:
            raise self._invalid("schema")
        by_id = {s.segment_id: s for s in segments}
        source_ids = {s.segment_id for s in segments if s.kind == "SOURCE"}
        if not source_ids or len(by_id) != len(segments):
            raise self._invalid("source_segments")
        used = set()

        def refs(keys, question=False):
            keys = self._strings(keys)
            if not keys or not set(keys) <= (set(by_id) if question else source_ids):
                raise self._invalid("segment_ids")
            used.update(set(keys) & source_ids)

        def bounded(rows, minimum, maximum, name):
            if type(rows) is not list or not minimum <= len(rows) <= maximum:
                raise self._limit(name)
            return rows

        def scalar(value):
            if type(value) is bool:
                return value
            if type(value) is int and abs(value) <= 1000000:
                return value
            if type(value) is str:
                return self._text(value, 128)
            raise self._invalid("scalar")

        def context(row, hypothetical=False):
            self._keys(row, CONTEXT_FIELDS)
            self._text(row["id"], 128)
            if row["adapter"] not in ADAPTERS:
                raise self._invalid("adapter")
            refs(row["segment_ids"], hypothetical)
            if (
                type(row["features"]) is not dict
                or len(row["features"]) > 32
                or type(row["feature_segments"]) is not dict
            ):
                raise self._invalid("features")
            if set(row["feature_segments"]) != set(row["features"]):
                raise self._invalid("feature_anchors")
            for key, value in row["features"].items():
                self._text(key, 128)
                scalar(value)
                refs(row["feature_segments"][key], hypothetical)
            compiler = (
                LocalModelCompiler()
                if row["adapter"] == "mental-scene-1"
                else ArgumentCompiler()
            )
            compiler.compile(
                snapshot,
                segments,
                json.dumps(row["template"], ensure_ascii=False),
                allowance,
            )
            if len(row["template"]["models"]) != 1:
                raise self._invalid("one_context_model")

        contexts = {}
        for row in bounded(data["contexts"], 1, 16, "contexts"):
            context(row)
            if row["id"] in contexts:
                raise self._invalid("context_id")
            contexts[row["id"]] = row
        adapters = {row["adapter"] for row in contexts.values()}
        if len(adapters) != 1:
            raise self._invalid("one_domain_per_explainandum")
        adapter = next(iter(adapters))
        observations, observation_ids = [], set()
        for row in bounded(data["observations"], 1, 64, "observations"):
            self._keys(
                row,
                "id context_id query_id values factor_id provenance_group derived_from segment_ids",
            )
            for field in (
                "id",
                "context_id",
                "query_id",
                "factor_id",
                "provenance_group",
            ):
                self._text(row[field], 128)
            if row["id"] in observation_ids or row["context_id"] not in contexts:
                raise self._invalid("observation_identity")
            observation_ids.add(row["id"])
            refs(row["segment_ids"])
            self._strings(row["derived_from"], 16)
            bounded(row["values"], 1, 32, "observation_values")
            for value in row["values"]:
                if (
                    type(value) is dict
                    and set(value) == {"positive", "opposed"}
                    and all(type(v) is bool for v in value.values())
                ):
                    continue
                scalar(value)
            observations.append(row)
        # Repeated/derived reports are a connected provenance family, not
        # likelihood factors. Conflicting contents remain separate matrix rows.
        parents = {row["id"]: row["id"] for row in observations}
        context_hashes = {
            key: context_identity(value) for key, value in contexts.items()
        }

        def root(key):
            while parents[key] != key:
                key = parents[key]
            return key

        def join(a, b):
            a, b = root(a), root(b)
            parents[max(a, b)] = min(a, b)

        for row in observations:
            for prior in row["derived_from"]:
                if prior not in parents or prior == row["id"]:
                    raise self._invalid("derived_from")
                join(row["id"], prior)
            for other in observations:
                same_declared = (row["provenance_group"], row["factor_id"]) == (
                    other["provenance_group"],
                    other["factor_id"],
                )
                same_anchor = (
                    context_hashes[row["context_id"]],
                    row["query_id"],
                    sorted(row["segment_ids"]),
                ) == (
                    context_hashes[other["context_id"]],
                    other["query_id"],
                    sorted(other["segment_ids"]),
                )
                if same_declared or same_anchor:
                    join(row["id"], other["id"])
        lineage = {row["id"]: row["derived_from"] for row in observations}
        visited, visiting = set(), set()

        def visit(key):
            if key in visiting:
                raise self._invalid("cyclic_report_lineage")
            if key in visited:
                return
            visiting.add(key)
            for parent in lineage[key]:
                visit(parent)
            visiting.remove(key)
            visited.add(key)

        for key in lineage:
            visit(key)
        families = {}
        for row in observations:
            families.setdefault(root(row["id"]), []).append(row)
        for rows in families.values():
            factor = "factor:" + identity(
                [
                    sorted({key for row in rows for key in row["segment_ids"]}),
                    sorted(
                        {
                            (
                                context_hashes[row["context_id"]],
                                row["query_id"],
                            )
                            for row in rows
                        }
                    ),
                ]
            )
            for row in rows:
                row["declared_factor_id"] = row["factor_id"]
                row["factor_id"] = factor
        probes, probe_ids = [], set()
        for row in bounded(data["probes"], 0, 8, "probes"):
            self._keys(row, "id context query_id segment_ids")
            self._text(row["id"], 128)
            self._text(row["query_id"], 128)
            refs(row["segment_ids"], True)
            context(row["context"], True)
            if row["id"] in probe_ids or row["context"]["adapter"] != adapter:
                raise self._invalid("probe_identity")
            probe_ids.add(row["id"])
            probes.append(row)
        program_ids = set()
        all_contexts = [*contexts.values(), *(p["context"] for p in probes)]
        for program in bounded(data["programs"], 1, 8, "programs"):
            self._keys(program, PROGRAM_FIELDS)
            self._text(program["id"], 128)
            if program["id"] in program_ids or program["adapter"] != adapter:
                raise self._invalid("program_identity")
            program_ids.add(program["id"])
            if type(program["latent"]) is not dict or len(program["latent"]) > 16:
                raise self._invalid("latent")
            for name, value in program["latent"].items():
                self._text(name, 128)
                scalar(value)

            def expression(expr, boolean=False):
                if expression_size(expr) > 128:
                    raise self._limit("expression_size")
                for ctx in all_contexts:
                    value = evaluate_expression(
                        expr, ctx["features"], program["latent"]
                    )
                    scalar(value)
                    if boolean and type(value) is not bool:
                        raise self._invalid("Boolean_expression")

            for binding in bounded(program["observe"], 0, 16, "observe"):
                self._keys(binding, "event_id actor channel when")
                if adapter != "mental-scene-1" or binding["channel"] not in CHANNELS:
                    raise self._invalid("observation_binding")
                for ctx in all_contexts:
                    model = ctx["template"]["models"][0]
                    if binding["event_id"] not in {
                        e["id"] for e in model["events"]
                    } or binding["actor"] not in {a["id"] for a in model["agents"]}:
                        raise self._invalid("observation_target")
                expression(binding["when"], True)
            for binding in bounded(program["transition"], 0, 16, "transition"):
                self._keys(binding, "target value")
                validate_target(
                    adapter, binding["target"], [c["template"] for c in all_contexts]
                )
                expression(binding["value"])
            for expr in bounded(program["constraint"], 0, 16, "constraints"):
                expression(expr, True)
            predictions = set()
            for row in bounded(program["predict"], 1, 16, "predictions"):
                self._keys(row, "id field record_id")
                self._text(row["id"], 128)
                self._text(row["record_id"], 128)
                if row["id"] in predictions or row["field"] not in PREDICTIONS[adapter]:
                    raise self._invalid("prediction_selector")
                predictions.add(row["id"])
            if any(o["query_id"] not in predictions for o in observations) or any(
                p["query_id"] not in predictions for p in probes
            ):
                raise self._invalid("missing_prediction_obligation")
        self._keys(
            data["grammar"], "observation_features latent_domains max_expression_size"
        )
        grammar = data["grammar"]
        self._strings(grammar["observation_features"], 32)
        if any(
            type(c["features"].get(name)) is not bool
            for name in grammar["observation_features"]
            for c in all_contexts
        ):
            raise self._invalid("grammar_features")
        if (
            type(grammar["latent_domains"]) is not dict
            or len(grammar["latent_domains"]) > 16
        ):
            raise self._invalid("latent_domains")
        for name, choices in grammar["latent_domains"].items():
            self._text(name, 128)
            for value in bounded(choices, 1, 8, "latent_choices"):
                scalar(value)
        if (
            type(grammar["max_expression_size"]) is not int
            or not 1 <= grammar["max_expression_size"] <= 128
        ):
            raise self._invalid("expression_bound")
        self._keys(data["search"], "max_rounds beam new_per_round max_candidates")
        for name, maximum, minimum in (
            ("max_rounds", 8, 0),
            ("beam", 12, 1),
            ("new_per_round", 4, 1),
            ("max_candidates", 64, 1),
        ):
            if (
                type(data["search"][name]) is not int
                or not minimum <= data["search"][name] <= maximum
            ):
                raise self._invalid("search_bound")
        self._strings(data["unmodeled_segments"])
        if not set(data["unmodeled_segments"]) <= source_ids:
            raise self._invalid("unmodeled_segments")
        used.update(data["unmodeled_segments"])
        if not source_ids <= used:
            raise self._invalid("unaccounted_source_segments")
        data["source_bindings"] = {
            key: {k: v for k, v in asdict(by_id[key]).items() if k != "text"}
            for key in sorted(used)
        }
        return freeze(data)


def validate_target(adapter, target, templates):
    """Named candidate mechanism locations only; never sources or observed targets."""
    if type(target) is not dict:
        raise ValueError("typed mechanism target required")
    kind = target.get("kind")
    required = {
        "utility": {"kind", "plan_id", "state"},
        "cost": {"kind", "plan_id", "action_id"},
        "ordinary": {"kind", "premise_id"},
        "strict": {"kind", "rule_id"},
    }
    if kind not in required or set(target) != required[kind]:
        raise ValueError("unsupported mechanism edit target")
    for template in templates:
        model = template["models"][0]
        if adapter == "mental-scene-1" and kind in ("utility", "cost"):
            plan = next(p for p in model["plans"] if p["id"] == target["plan_id"])
            if kind == "utility" and target["state"] not in plan["graph"]["utilities"]:
                raise ValueError("unknown utility target")
            if kind == "cost" and target["action_id"] not in {
                a["id"] for a in plan["graph"]["actions"]
            }:
                raise ValueError("unknown action target")
        elif adapter == "argument-model-1" and kind in ("ordinary", "strict"):
            rows, key = (
                (model["premises"], "premise_id")
                if kind == "ordinary"
                else (model["rules"], "rule_id")
            )
            if target[key] not in {r["id"] for r in rows}:
                raise ValueError("unknown argument target")
        else:
            raise ValueError("mechanism adapter mismatch")
