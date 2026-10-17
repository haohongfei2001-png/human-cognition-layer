"""Source-bound goal, forecast and coping mechanisms; computed appraisals forbidden."""

from dataclasses import asdict
import json
from hcl.kernel.types import HCLFailure, freeze, thaw
from hcl.operators.agency import rational
from hcl.operators.affect import validate_observation_coarsening
from hcl.semantics.model_compiler import LocalModelCompiler, SCHEMA as MENTAL_SCHEMA

SCHEMA = "hcl-affect-candidates-1"
from hcl.operators.affect_attribution import SCHEMA as ATTRIBUTION_SCHEMA, VALUES as ATTRIBUTION_VALUES
from hcl.semantics.affect_attribution import validate_bridges, stable_bridges
EPISODE_FIELDS = "id episode_id actor before at plan_id previous_weights current_weights forecast_action goals mappings coping previous_id revision_kind segment_ids"
GOAL_FIELDS = "id label utilities segment_ids"
COPING_FIELDS = "id kind priorities adjustments horizon action_ids observation_overrides segment_ids"


def affect_context(snapshot, question):
    from hcl.semantics.segments import segment_snapshot

    return dict(
        schema="hcl-affect-context-1",
        candidate_schema=SCHEMA,
        purpose="PROPOSE_SOURCE_BOUND_GOALS_FORECASTS_AND_COPING_MECHANISMS_NOT_APPRAISALS_OR_EMOTION_ANSWERS",
        model_fields="mental episodes channels".split(),
        episode_fields=EPISODE_FIELDS.split(),
        goal_fields=GOAL_FIELDS.split(),
        coping_fields=COPING_FIELDS.split(),
        mapping_fields="id label conditions requires_previous segment_ids".split(),
        condition_fields="goal_id dimension value".split(),
        adjustment_fields="id conditions multipliers segment_ids".split(),
        channel_fields="id at actor speaker kind content segment_ids".split(),
        instructions=(
            "mental uses the existing finite M03/M05 source model. Episode plan_id supplies a source-bound "
            "state codebook and real transition/opportunity model. Give separate goal consequence functions, never "
            "computed appraisal, emotion, Q or coping scores. before is a prior state, not a future forecast: "
            "forecast_action must name an explicit prospective transition hypothesis or be null. Unknown weights "
            "stay null. Mapping rules read computed desirability/change_direction/expectation_gap_direction with "
            "NEGATIVE/ZERO/POSITIVE, or computed control with IMPROVABLE/NO_IMPROVEMENT. They are competing "
            "semantic hypotheses. Coping conditions alter goal priorities before actual planning; candidates remain "
            "hypothetical. Channels separately preserve SELF_REPORT, EXPRESSION and ATTRIBUTION, never private truth. "
            "Revision kinds INITIAL/NEW_INFORMATION/GOAL_REVISION/ANALYST_REINTERPRETATION preserve history. "
            "Every factual/semantic mechanism requires exact source spans, never question anchors."
        ),
        source_input_versions=dict(snapshot.source_versions),
        segments=[asdict(s) for s in segment_snapshot(snapshot, question)],
    )


class AffectCompiler(LocalModelCompiler):
    def _invalid(self, field="candidate"):
        return HCLFailure(
            "INVALID_REQUEST",
            "affect_compile",
            "INVALID_AFFECT_CANDIDATE",
            field,
            "The proposed appraisal violates its source-bound finite contract.",
        )

    def _limit(self, field):
        return HCLFailure(
            "BUDGET_EXHAUSTED",
            "affect_compile",
            "AFFECT_COMPILE_BOUND",
            field,
            "The proposed appraisal exceeds its finite compilation bound.",
        )

    def compile(self, snapshot, segments, raw_candidate, allowance, *, mental_segments=None):
        try:
            return self._compile_affect(snapshot, segments, raw_candidate, allowance, mental_segments=mental_segments)
        except (
            ValueError,
            TypeError,
            KeyError,
            IndexError,
            RecursionError,
            OverflowError,
            ZeroDivisionError,
        ):
            raise self._invalid() from None

    def _compile_affect(self, snapshot, segments, raw, allowance, *, mental_segments=None):
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
                self._invalid("nonfinite_value")
            ),
        )
        self._keys(data, "schema models")
        if data["schema"] not in (SCHEMA, ATTRIBUTION_SCHEMA):
            raise self._invalid("schema")
        source_refs = {s.segment_id for s in segments if s.kind == "SOURCE"}

        def refs(value):
            strings = self._strings(value, 64)
            if not strings or not set(strings) <= source_refs:
                raise self._invalid("source_span")

        def rows(value, maximum, minimum=0):
            if type(value) is not list or not minimum <= len(value) <= maximum:
                raise self._limit("rows")
            return value

        def stamp(value):
            if type(value) is not int or not 0 <= value <= 1000000:
                raise self._invalid("time")

        def distribution(value, states, required=False):
            if value is None and not required:
                return
            if type(value) is not dict or not value or not set(value) <= set(states):
                raise self._invalid("weights")
            parsed = [rational(v) for v in value.values()]
            if any(v < 0 for v in parsed) or sum(parsed) != 1:
                raise self._invalid("weights")

        identities = set()
        for model in rows(data["models"], 8, 1):
            self._keys(model, "mental episodes channels")
            base = LocalModelCompiler().compile(
                snapshot,
                segments if mental_segments is None else mental_segments,
                json.dumps(dict(schema=MENTAL_SCHEMA, models=[model["mental"]])),
                allowance,
            )
            mental = thaw(base)["models"][0]
            model["mental"] = mental
            identity = (mental["source_id"], mental["id"])
            if identity in identities:
                raise self._invalid("model_identity")
            identities.add(identity)
            agents = {a["id"] for a in mental["agents"]}
            plans = {p["id"]: p for p in mental["plans"]}
            previous = {}
            for episode in rows(model["episodes"], 16, 1):
                self._keys(episode, EPISODE_FIELDS + (" attributions" if data["schema"] == ATTRIBUTION_SCHEMA else ""))
                for key in ("id", "episode_id"):
                    self._text(episode[key], 128)
                if episode["id"] in previous or episode["actor"] not in agents:
                    raise self._invalid("episode_identity")
                stamp(episode["before"])
                stamp(episode["at"])
                if episode["before"] > episode["at"]:
                    raise self._invalid("episode_time")
                plan = plans[episode["plan_id"]]
                states = plan["graph"]["states"]
                if (
                    len(states) > 32
                    or plan["actor"] != episode["actor"]
                    or plan["at"] != episode["at"]
                ):
                    raise self._invalid("episode_plan_binding")
                for key in ("previous_weights", "current_weights"):
                    distribution(episode[key], states)
                action_ids = {a["id"] for a in plan["graph"]["actions"]}
                if (
                    episode["forecast_action"] is not None
                    and episode["forecast_action"] not in action_ids
                ):
                    raise self._invalid("prospective_action")
                refs(episode["segment_ids"])
                goals = set()
                for goal in rows(episode["goals"], 8, 1):
                    self._keys(goal, GOAL_FIELDS)
                    self._text(goal["id"], 128)
                    self._text(goal["label"], 256)
                    if (
                        goal["id"] in goals
                        or type(goal["utilities"]) is not dict
                        or set(goal["utilities"]) != set(states)
                    ):
                        raise self._invalid("goal_consequences")
                    goals.add(goal["id"])
                    for value in goal["utilities"].values():
                        rational(value)
                    refs(goal["segment_ids"])

                bridges = (validate_bridges(self, episode, mental, goals, refs, rows)
                           if data["schema"] == ATTRIBUTION_SCHEMA else {})

                def conditions(value):
                    for condition in rows(value, 16, 1):
                        if type(condition) is not dict:
                            raise self._invalid("condition")
                        self._keys(condition, "goal_id dimension value" +
                                   (" attribution_id" if condition.get("dimension") == "attribution"
                                    and data["schema"] == ATTRIBUTION_SCHEMA else ""))
                        if condition["goal_id"] not in goals:
                            raise self._invalid("condition_goal")
                        if condition["dimension"] in (
                            "desirability",
                            "change_direction",
                            "expectation_gap_direction",
                        ):
                            allowed = {"NEGATIVE", "ZERO", "POSITIVE"}
                        elif condition["dimension"] == "attribution" and data["schema"] == ATTRIBUTION_SCHEMA:
                            bridge = bridges.get(condition["attribution_id"])
                            if bridge is None or bridge["goal_id"] != condition["goal_id"]:
                                raise self._invalid("condition_attribution_binding")
                            allowed = ATTRIBUTION_VALUES
                        elif condition["dimension"] == "control":
                            allowed = {"IMPROVABLE", "NO_IMPROVEMENT"}
                        else:
                            raise self._invalid("appraisal_dimension")
                        if condition["value"] not in allowed:
                            raise self._invalid("qualitative_value")

                mapping_ids = set()
                for mapping in rows(episode["mappings"], 32):
                    self._keys(
                        mapping, "id label conditions requires_previous segment_ids"
                    )
                    self._text(mapping["id"], 128)
                    self._text(mapping["label"], 256)
                    if mapping["id"] in mapping_ids:
                        raise self._invalid("mapping_identity")
                    mapping_ids.add(mapping["id"])
                    conditions(mapping["conditions"])
                    self._strings(mapping["requires_previous"], 32)
                    refs(mapping["segment_ids"])
                coping_ids = set()
                for coping in rows(episode["coping"], 8):
                    self._keys(coping, COPING_FIELDS)
                    self._text(coping["id"], 128)
                    if coping["id"] in coping_ids or coping["kind"] not in {
                        "PROBLEM_FOCUSED",
                        "AVOIDANCE",
                        "REINTERPRETATION",
                        "SUPPORT_SEEKING",
                    }:
                        raise self._invalid("coping_identity")
                    coping_ids.add(coping["id"])
                    if (
                        type(coping["horizon"]) is not int
                        or not 1 <= coping["horizon"] <= 8
                    ):
                        raise self._limit("coping_horizon")
                    selected = self._strings(coping["action_ids"], 32)
                    if not selected or not set(selected) <= action_ids:
                        raise self._invalid("coping_actions")
                    overrides = coping["observation_overrides"]
                    if type(overrides) is not dict or not set(overrides) <= set(
                        selected
                    ):
                        raise self._invalid("coping_observation_actions")
                    for action_id, values in overrides.items():
                        if type(values) is not dict or set(values) != set(states):
                            raise self._invalid("coping_observation_states")
                        for symbol in values.values():
                            self._text(symbol, 160)
                        original = next(
                            a for a in plan["graph"]["actions"] if a["id"] == action_id
                        )
                        validate_observation_coarsening(
                            original["observations"], values
                        )
                    distribution(coping["priorities"], goals, True)
                    if set(coping["priorities"]) != goals:
                        raise self._invalid("missing_goal_priority")
                    rule_ids = set()
                    for rule in rows(coping["adjustments"], 4):
                        self._keys(rule, "id conditions multipliers segment_ids")
                        self._text(rule["id"], 128)
                        if rule["id"] in rule_ids:
                            raise self._invalid("adjustment_identity")
                        rule_ids.add(rule["id"])
                        conditions(rule["conditions"])
                        if (
                            type(rule["multipliers"]) is not dict
                            or set(rule["multipliers"]) != goals
                        ):
                            raise self._invalid("adjustment_goals")
                        if any(rational(v) < 0 for v in rule["multipliers"].values()):
                            raise self._invalid("negative_priority")
                        refs(rule["segment_ids"])
                    refs(coping["segment_ids"])
                if episode["revision_kind"] not in {
                    "INITIAL",
                    "NEW_INFORMATION",
                    "GOAL_REVISION",
                    "ANALYST_REINTERPRETATION",
                }:
                    raise self._invalid("revision_kind")
                prior = episode["previous_id"]
                if prior is None:
                    if episode["revision_kind"] != "INITIAL":
                        raise self._invalid("unbound_revision")
                    if any(m["requires_previous"] for m in episode["mappings"]):
                        raise self._invalid("unbound_previous_affect")
                else:
                    p = previous[prior]
                    if (p["actor"], p["episode_id"]) != (
                        episode["actor"],
                        episode["episode_id"],
                    ) or p["at"] >= episode["at"]:
                        raise self._invalid("revision_identity_or_time")
                    labels = {m["label"] for m in p["mappings"]}
                    if any(
                        not set(m["requires_previous"]) <= labels
                        for m in episode["mappings"]
                    ):
                        raise self._invalid("unknown_previous_affect")
                    if episode["revision_kind"] == "INITIAL":
                        raise self._invalid("revision_kind")
                    if episode["revision_kind"] == "NEW_INFORMATION":
                        # A belief update cannot silently replace the goal or
                        # coping theory and then attribute its effect to news.
                        stable = (
                            "before",
                            "previous_weights",
                            "forecast_action",
                            "goals",
                            "mappings",
                            "coping",
                        )
                        if any(episode[key] != p[key] for key in stable):
                            raise self._invalid("new_information_changed_mechanism")
                        if data["schema"] == ATTRIBUTION_SCHEMA and stable_bridges(episode) != stable_bridges(p):
                            raise self._invalid("new_information_changed_attribution")
                        old_plan = plans[p["plan_id"]]
                        if any(
                            plan[key] != old_plan[key] for key in ("graph", "bindings")
                        ):
                            raise self._invalid("new_information_changed_plan")
                previous[episode["id"]] = episode
            channel_ids = set()
            for channel in rows(model["channels"], 64):
                self._keys(channel, "id at actor speaker kind content segment_ids")
                self._text(channel["id"], 128)
                self._text(channel["speaker"], 128)
                self._text(channel["content"], 4096)
                stamp(channel["at"])
                refs(channel["segment_ids"])
                if (
                    channel["id"] in channel_ids
                    or channel["actor"] not in agents
                    or channel["kind"]
                    not in {"SELF_REPORT", "EXPRESSION", "ATTRIBUTION"}
                ):
                    raise self._invalid("channel_identity")
                if (
                    channel["kind"] == "SELF_REPORT"
                    and channel["speaker"] != channel["actor"]
                ):
                    raise self._invalid("self_report_speaker")
                channel_ids.add(channel["id"])
        return freeze(data)
