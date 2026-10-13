"""Source-bound normative proposals; never supplied permissions or moral winners."""

from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json

from hcl.kernel.types import HCLFailure, freeze, thaw
from hcl.memory import codec
from hcl.operators.agency import rational
from hcl.semantics.model_compiler import LocalModelCompiler
from hcl.semantics.interaction_compiler import InteractionCompiler
from hcl.semantics.argument_compiler import ArgumentCompiler

SCHEMA = "hcl-judgment-candidates-1"
MODEL_FIELDS = "mental interaction argument facts fact_bindings decisions"
DECISION_FIELDS = "id plan_id dimensions scenarios frameworks responsibility_queries segment_ids"
FRAMEWORK_FIELDS = "id label origin decision_rule weights norms assumptions active_assumptions segment_ids"
ORIGINS = ("USER_REPORTED_ADOPTION", "PERSON_REPORTED_ENDORSEMENT", "INSTITUTION_REPORTED", "ANALYST_CONDITIONAL")


def judgment_context(snapshot, question):
    from hcl.semantics.segments import segment_snapshot

    return dict(schema="hcl-judgment-context-1", candidate_schema=SCHEMA,
                purpose="PROPOSE_CONDITIONAL_SINGLE_STEP_NORMATIVE_MODELS_NOT_PERMISSIONS_SCORES_OR_WINNERS",
                model_fields=MODEL_FIELDS.split(), decision_fields=DECISION_FIELDS.split(),
                framework_fields=FRAMEWORK_FIELDS.split(),
                instructions=(
                    "mental is the common M03/M05 model. interaction omits mental and supplies actual M07 inputs. "
                    "argument is a source-bound M13 model. facts have id/kind/role/reference/segment_ids: "
                    "MENTAL_QUERY references query_id, OPPORTUNITY references plan_id/action_id/view (WORLD or SUBJECTIVE), "
                    "COMMITMENT references commitment_id/at/status, CAUSAL references query_id/expected (0 or 1). "
                    "fact_bindings have premise_id/fact_id/expected/segment_ids; bound M13 premises are included only when actual facts establish expected. "
                    "All decisions are explicitly single-step. Dimensions have id/label/state_values/action_costs/segment_ids over the plan graph. "
                    "Scenarios have id/distribution/segment_ids; empty means all actually retained states separately, never uniform probabilities. "
                    "Framework origins have kind/declarer/at/frame_kind/segment_ids. USER_REPORTED_ADOPTION is a source reconstruction, never current user authorization. "
                    "Weights are null for PARETO or explicit normalized rationals for EXPECTED (one scenario) or MAXIMIN. "
                    "Norms have id/label/permitted_actions/guard_fact_ids/argument_query_id/segment_ids. "
                    "M13 disputes and unknown factual guards cannot be assumed false to grant permission. "
                    "responsibility_queries have query_id/factor_ids/segment_ids; acceptance is conditional, not moral truth. "
                    "No predicted labels, Q vectors, uniform default weights, arbitrary code or candidate-granted authority."
                ), source_input_versions=dict(snapshot.source_versions),
                segments=[asdict(s) for s in segment_snapshot(snapshot, question)])


class JudgmentCompiler(LocalModelCompiler):
    def _invalid(self, field="candidate"):
        return HCLFailure("INVALID_REQUEST", "judgment_compile", "INVALID_JUDGMENT_CANDIDATE", field,
                          "The proposed judgment violates its finite source-bound conditional contract.")

    def _limit(self, field):
        return HCLFailure("BUDGET_EXHAUSTED", "judgment_compile", "JUDGMENT_COMPILE_BOUND", field,
                          "The conditional judgment exceeds its explicit compilation bound.")

    def compile(self, snapshot, segments, raw_candidate, allowance):
        try:
            return self._compile_judgment(snapshot, segments, raw_candidate, allowance)
        except (ValueError, TypeError, KeyError, IndexError, RecursionError, OverflowError, ZeroDivisionError):
            raise self._invalid() from None

    def _compile_judgment(self, snapshot, segments, raw, allowance):
        if type(raw) is not str or len(raw.encode()) > min(allowance.max_output_bytes, 1048576):
            raise self._limit("candidate_bytes")

        def unique(pairs):
            out = {}
            for key, value in pairs:
                if key in out:
                    raise self._invalid("duplicate_json_field")
                out[key] = value
            return out

        data = json.loads(raw, object_pairs_hook=unique,
                          parse_constant=lambda _: (_ for _ in ()).throw(self._invalid("nonfinite_value")))
        self._keys(data, "schema models")
        if data["schema"] != SCHEMA:
            raise self._invalid("schema")
        by_id = {s.segment_id: s for s in segments}
        source_refs = {s.segment_id for s in segments if s.kind == "SOURCE"}
        if len(by_id) != len(segments) or not source_refs:
            raise self._invalid("source_segments")

        def refs(value):
            keys = self._strings(value, 64)
            if not keys or not set(keys) <= source_refs:
                raise self._invalid("source_span")

        def rows(value, maximum, minimum=0):
            if type(value) is not list or not minimum <= len(value) <= maximum:
                raise self._limit("rows")
            return value

        def identify(row, seen):
            self._text(row["id"], 128)
            if row["id"] in seen:
                raise self._invalid("duplicate_identity")
            seen.add(row["id"])
            refs(row["segment_ids"])

        def numbers(value, keys, *, normalized=False):
            if type(value) is not dict or set(value) != set(keys):
                raise self._invalid("numeric_dimensions")
            values = [rational(v) for v in value.values()]
            if normalized and (any(v < 0 for v in values) or sum(values) != 1):
                raise self._invalid("probability_or_weight")

        identities = set()
        for model in rows(data["models"], 4, 1):
            self._keys(model, MODEL_FIELDS)
            self._keys(model["interaction"], "utterances acts commitments games through max_ack_depth")
            interaction = thaw(InteractionCompiler().compile(snapshot, segments, json.dumps(dict(
                schema="hcl-interaction-candidates-1", models=[dict(model["interaction"], mental=deepcopy(model["mental"]))])), allowance))["models"][0]
            model["mental"] = mental = interaction["mental"]
            model["interaction"] = {k: v for k, v in interaction.items() if k != "mental"}
            model["argument"] = argument = thaw(ArgumentCompiler().compile(snapshot, segments, json.dumps(dict(
                schema="hcl-argument-candidates-1", models=[model["argument"]])), allowance))["models"][0]
            if argument["frame_kind"] != mental["frame_kind"]:
                raise self._invalid("unbridged_argument_frame")
            identity = (mental["source_id"], mental["id"])
            if identity in identities:
                raise self._invalid("model_identity")
            identities.add(identity)
            plans = {p["id"]: p for p in mental["plans"]}
            queries = {q["id"]: q for q in mental["queries"]}
            causal = {q["id"]: q for q in mental["causal"]}
            commitments = {c["id"]: c for c in interaction["commitments"]}
            argument_queries = {q["id"]: q for q in argument["queries"]}
            fact_ids = set()
            fact_times = {}
            for fact in rows(model["facts"], 32):
                self._keys(fact, "id kind role reference segment_ids")
                identify(fact, fact_ids)
                if fact["role"] not in ("FACT", "KNOWLEDGE", "CONTROL", "FORESEEABILITY", "STATED_INTENTION", "CAUSAL_CONTRIBUTION", "COMMITMENT"):
                    raise self._invalid("factor_role")
                ref = fact["reference"]
                if fact["kind"] == "MENTAL_QUERY":
                    self._keys(ref, "query_id")
                    query = queries[ref["query_id"]]
                    fact_times[fact["id"]] = query["at"]
                elif fact["kind"] == "OPPORTUNITY":
                    self._keys(ref, "plan_id action_id view")
                    plan = plans[ref["plan_id"]]
                    if ref["action_id"] not in {a["id"] for a in plan["graph"]["actions"]} or ref["view"] not in ("WORLD", "SUBJECTIVE"):
                        raise self._invalid("opportunity_reference")
                    fact_times[fact["id"]] = plan["at"]
                elif fact["kind"] == "COMMITMENT":
                    self._keys(ref, "commitment_id at status")
                    if (ref["commitment_id"] not in commitments or type(ref["at"]) is not int
                            or not 0 <= ref["at"] <= interaction["through"]
                            or ref["status"] not in ("ACTIVE", "FULFILLED", "BREACHED", "BREACHED_THEN_FULFILLED", "RELEASED", "REFUSED", "AWAITING_ACCEPTANCE", "CONDITION_FALSE", "CONDITION_UNRESOLVED")):
                        raise self._invalid("commitment_reference")
                    fact_times[fact["id"]] = ref["at"]
                elif fact["kind"] == "CAUSAL":
                    self._keys(ref, "query_id expected")
                    if ref["query_id"] not in causal or type(ref["expected"]) is not int or ref["expected"] not in (0, 1):
                        raise self._invalid("causal_reference")
                    fact_times[fact["id"]] = None
                else:
                    raise self._invalid("fact_kind")
            premises = {p["id"] for p in argument["premises"]}
            bound = set()
            for binding in rows(model["fact_bindings"], 32):
                self._keys(binding, "premise_id fact_id expected segment_ids")
                refs(binding["segment_ids"])
                if (binding["premise_id"] not in premises or binding["premise_id"] in bound
                        or binding["fact_id"] not in fact_ids or type(binding["expected"]) is not bool):
                    raise self._invalid("fact_binding")
                bound.add(binding["premise_id"])
            decisions = set()
            for decision in rows(model["decisions"], 4, 1):
                self._keys(decision, DECISION_FIELDS)
                identify(decision, decisions)
                plan = plans[decision["plan_id"]]
                if plan["graph"]["horizon"] != 1 or plan["at"] > interaction["through"]:
                    raise self._invalid("single_step_decision")
                # Fact-conditioned argument premises may not backfill a decision
                # from a later receipt, control opportunity or commitment state.
                if any(t is not None and t > plan["at"] for t in fact_times.values()):
                    raise self._invalid("future_fact_at_decision")
                for fact in model["facts"]:
                    if fact["role"] in ("KNOWLEDGE", "FORESEEABILITY", "STATED_INTENTION"):
                        if fact["kind"] != "MENTAL_QUERY":
                            raise self._invalid("mental_factor_kind")
                        query = queries[fact["reference"]["query_id"]]
                        formula = query["formula"]
                        if (type(formula) is not dict or formula.get("op") != "believes"
                                or formula["agent"] != plan["actor"] or query["at"] != plan["at"]):
                            raise self._invalid("action_time_actor_factor")
                    if fact["role"] == "CONTROL":
                        if fact["kind"] != "OPPORTUNITY":
                            raise self._invalid("control_factor_kind")
                        reference_plan = plans[fact["reference"]["plan_id"]]
                        if (reference_plan["actor"], reference_plan["at"]) != (plan["actor"], plan["at"]):
                            raise self._invalid("action_time_control_factor")
                    if fact["kind"] == "COMMITMENT" and commitments[fact["reference"]["commitment_id"]]["speaker"] != plan["actor"]:
                        raise self._invalid("commitment_actor_factor")
                actions = {a["id"] for a in plan["graph"]["actions"]}
                dims = set()
                for dimension in rows(decision["dimensions"], 8, 1):
                    self._keys(dimension, "id label state_values action_costs segment_ids")
                    identify(dimension, dims)
                    self._text(dimension["label"], 256)
                    numbers(dimension["state_values"], plan["graph"]["states"])
                    numbers(dimension["action_costs"], actions)
                scenario_ids = set()
                for scenario in rows(decision["scenarios"], 16):
                    self._keys(scenario, "id distribution segment_ids")
                    identify(scenario, scenario_ids)
                    distribution = scenario["distribution"]
                    if not distribution or not set(distribution) <= set(plan["graph"]["states"]):
                        raise self._invalid("scenario_states")
                    numbers(distribution, distribution, normalized=True)
                frameworks = set()
                for framework in rows(decision["frameworks"], 4, 1):
                    self._keys(framework, FRAMEWORK_FIELDS)
                    identify(framework, frameworks)
                    self._text(framework["label"], 256)
                    self._keys(framework["origin"], "kind declarer at frame_kind segment_ids")
                    origin = framework["origin"]
                    refs(origin["segment_ids"])
                    self._text(origin["declarer"], 256)
                    if (origin["kind"] not in ORIGINS or type(origin["at"]) is not int
                            or not 0 <= origin["at"] <= plan["at"] or origin["frame_kind"] != mental["frame_kind"]):
                        raise self._invalid("framework_origin")
                    assumptions = set(self._strings(framework["assumptions"]))
                    if not set(self._strings(framework["active_assumptions"])) <= assumptions:
                        raise self._invalid("framework_assumptions")
                    if framework["weights"] is None:
                        if framework["decision_rule"] != "PARETO":
                            raise self._invalid("unknown_weights")
                    else:
                        numbers(framework["weights"], dims, normalized=True)
                        if framework["decision_rule"] not in ("EXPECTED", "MAXIMIN"):
                            raise self._invalid("decision_rule")
                        if framework["decision_rule"] == "EXPECTED" and len(decision["scenarios"]) > 1:
                            raise self._invalid("expected_probability_scenario")
                    norm_ids = set()
                    for norm in rows(framework["norms"], 16):
                        self._keys(norm, "id label permitted_actions guard_fact_ids argument_query_id segment_ids")
                        identify(norm, norm_ids)
                        self._text(norm["label"], 256)
                        if (not set(self._strings(norm["permitted_actions"], 32)) <= actions
                                or not set(self._strings(norm["guard_fact_ids"], 32)) <= fact_ids
                                or (norm["argument_query_id"] is not None and norm["argument_query_id"] not in argument_queries)):
                            raise self._invalid("norm_binding")
                for query in rows(decision["responsibility_queries"], 16):
                    self._keys(query, "query_id factor_ids segment_ids")
                    refs(query["segment_ids"])
                    if query["query_id"] not in argument_queries or not set(self._strings(query["factor_ids"], 32)) <= fact_ids:
                        raise self._invalid("responsibility_binding")
        data["source_versions"] = dict(snapshot.source_versions)
        data["source_bindings"] = {s.segment_id: {k: v for k, v in asdict(s).items() if k != "text"}
                                   for s in segments if s.kind == "SOURCE"}
        data["candidate"] = raw
        data["candidate_identity"] = sha256(raw.encode()).hexdigest()
        data["segments"] = [asdict(s) for s in segments]
        return freeze(data)



def judgment_qualifications(program):
    assumptions = tuple(sorted({a for model in program["models"] for a in (
        *model["mental"]["active_assumptions"], *model["argument"]["active_assumptions"],
        *(a for d in model["decisions"] for f in d["frameworks"] for a in f["active_assumptions"]))}))
    residuals = tuple(sorted({s for model in program["models"] for s in (
        *model["mental"]["unmodeled_segments"], *model["argument"]["unmodeled_segments"])}))
    return assumptions, residuals


def verify_program_bindings(program, snapshot, allowance):
    """Rebuild the exact host-created compilation from its bounded original input.

    This is a pure certificate, not an authorization token. Original full-source
    hashes, slices and versions must agree; the surrounding engine separately
    checks current ACL and source identity before any delivery.
    """
    from dataclasses import replace
    from hcl.semantics.segments import SourceSegment, iter_segments

    try:
        data = thaw(program)
        if data["candidate_identity"] != sha256(data["candidate"].encode()).hexdigest():
            raise ValueError("candidate identity changed")
        segments = tuple(SourceSegment(**s) for s in data["segments"])
        groups = {}
        for segment in segments:
            if segment.kind == "SOURCE":
                if (segment.source_id not in snapshot.source_versions
                        or segment.version != snapshot.source_versions[segment.source_id]):
                    raise ValueError("source segment is outside the snapshot")
            elif segment.kind != "QUESTION" or segment.source_id is not None or segment.version is not None:
                raise ValueError("invalid segment kind")
            groups.setdefault((segment.kind, segment.source_id, segment.version), []).append(segment)
        if {key[1] for key in groups if key[0] == "SOURCE"} != set(snapshot.source_versions):
            raise ValueError("source scope changed")
        for (kind, source, version), rows in groups.items():
            original = "".join(row.text for row in rows)
            if tuple(iter_segments(original, source, version, kind)) != tuple(rows):
                raise ValueError("original source identity, offsets or bytes changed")
        expected = JudgmentCompiler().compile(snapshot, segments, data["candidate"],
            replace(allowance, max_output_bytes=1048576))
        if codec.canonical(thaw(expected)) != codec.canonical(data):
            raise ValueError("compiled conditions or host-created provenance changed")
    except HCLFailure as error:
        raise ValueError("judgment certificate input no longer compiles") from error
