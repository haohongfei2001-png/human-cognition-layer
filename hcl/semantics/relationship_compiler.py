"""Source-bound longitudinal hypotheses; no supplied trust, choices or change points."""

from copy import deepcopy
from dataclasses import asdict
import json
from hcl.kernel.types import HCLFailure, freeze, thaw
from hcl.memory import codec
from hcl.operators.agency import rational
from hcl.operators.epistemic import _formula
from hcl.semantics.model_compiler import LocalModelCompiler
from hcl.semantics.interaction_compiler import InteractionCompiler
from hcl.semantics.affect_compiler import AffectCompiler

SCHEMA = "hcl-relationship-candidates-1"
MODEL_FIELDS = "mental interaction affect relationships roles identities observations forecasts mechanisms search"
RELATION_FIELDS = "id observer target domain dimension hypotheses prior factorization updates segment_ids"
UPDATE_FIELDS = (
    "id at event_id condition commitment_id commitment_status likelihoods segment_ids"
)
ROLE_FIELDS = "id actor from_time through_time condition episode_actions segment_ids"
OBSERVATION_FIELDS = "id context_id episode_id action segment_ids"
FORECAST_FIELDS = "id context_id episode_id segment_ids"
MECHANISM_FIELDS = "id label priorities coping_id goal_multipliers respect_roles relationship_effects segment_ids"


def relationship_context(snapshot, question):
    from hcl.semantics.segments import segment_snapshot

    return dict(
        schema="hcl-relationship-context-1",
        candidate_schema=SCHEMA,
        purpose="PROPOSE_SOURCE_BOUND_LONGITUDINAL_MECHANISMS_NOT_TRUST_SCORES_CHANGEPOINTS_OR_ANSWERS",
        model_fields=MODEL_FIELDS.split(),
        relation_fields=RELATION_FIELDS.split(),
        update_fields=UPDATE_FIELDS.split(),
        role_fields=ROLE_FIELDS.split(),
        observation_fields=OBSERVATION_FIELDS.split(),
        forecast_fields=FORECAST_FIELDS.split(),
        mechanism_fields=MECHANISM_FIELDS.split(),
        instructions=(
            "mental is the common M03 input; interaction omits its mental field and supplies M07 fields; affect omits mental and supplies episodes/channels. "
            "Every source mechanism is conditional. Relationship hypotheses have id/label/segment_ids; prior may be null. "
            "factorization explicitly declares CONDITIONAL_INDEPENDENCE_MODEL, never a measured fact. Updates require actual seen/received events and a condition in the observer perspective; optional commitment status also requires the real M07 result. "
            "Roles declare requirements, not self-identification. identities contain id/at/actor/speaker/kind/content/segment_ids with SELF_IDENTIFICATION or OTHER_ATTRIBUTION. "
            "Observations supply source actions, never predictions. Forecasts are hypothetical. Each context references a real M08 episode/plan. "
            "Mechanisms supply normalized goal priorities or a coping_id (then priorities=null), nonnegative goal_multipliers, role sensitivity and conditional relationship multipliers. "
            "relationship_effects have relationship_id/multipliers/segment_ids; multipliers map each relationship hypothesis to each goal. "
            "Search gives max_segments and max_candidates. No supplied complexity scores, fit, posterior, Q, change points or private identity truth."
        ),
        source_input_versions=dict(snapshot.source_versions),
        segments=[asdict(s) for s in segment_snapshot(snapshot, question)],
    )


class RelationshipCompiler(LocalModelCompiler):
    def _invalid(self, field="candidate"):
        return HCLFailure(
            "INVALID_REQUEST",
            "relationship_compile",
            "INVALID_RELATIONSHIP_CANDIDATE",
            field,
            "The proposed longitudinal mechanism violates its typed source-bound contract.",
        )

    def _limit(self, field):
        return HCLFailure(
            "BUDGET_EXHAUSTED",
            "relationship_compile",
            "RELATIONSHIP_COMPILE_BOUND",
            field,
            "The longitudinal model exceeds its explicit finite compilation bound.",
        )

    def compile(self, snapshot, segments, raw_candidate, allowance, *, mental_segments=None):
        try:
            return self._compile_relationship(
                snapshot, segments, raw_candidate, allowance, mental_segments=mental_segments
            )
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

    def _compile_relationship(self, snapshot, segments, raw, allowance, *, mental_segments=None):
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
        if data["schema"] != SCHEMA:
            raise self._invalid("schema")
        source_refs = {s.segment_id for s in segments if s.kind == "SOURCE"}

        def refs(value):
            values = self._strings(value, 64)
            if not values or not set(values) <= source_refs:
                raise self._invalid("source_span")

        def rows(value, maximum, minimum=0):
            if type(value) is not list or not minimum <= len(value) <= maximum:
                raise self._limit("rows")
            return value

        def stamp(value):
            if type(value) is not int or not 0 <= value <= 1000000:
                raise self._invalid("time")

        def identity(row, seen):
            self._text(row["id"], 128)
            if row["id"] in seen:
                raise self._invalid("duplicate_identity")
            seen.add(row["id"])
            refs(row["segment_ids"])

        model_ids = set()
        for model in rows(data["models"], 4, 1):
            self._keys(model, MODEL_FIELDS)
            self._keys(
                model["interaction"],
                "utterances acts commitments games through max_ack_depth",
            )
            self._keys(model["affect"], "episodes channels")
            interaction = thaw(
                InteractionCompiler().compile(
                    snapshot,
                    segments,
                    json.dumps(
                        dict(
                            schema="hcl-interaction-candidates-1",
                            models=[
                                dict(
                                    model["interaction"],
                                    mental=deepcopy(model["mental"]),
                                )
                            ],
                        )
                    ),
                    allowance,
                    mental_segments=mental_segments,
                )
            )["models"][0]
            affect = thaw(
                AffectCompiler().compile(
                    snapshot,
                    segments,
                    json.dumps(
                        dict(
                            schema="hcl-affect-candidates-1",
                            models=[
                                dict(model["affect"], mental=deepcopy(model["mental"]))
                            ],
                        )
                    ),
                    allowance,
                    mental_segments=mental_segments,
                )
            )["models"][0]
            if codec.canonical(interaction["mental"]) != codec.canonical(
                affect["mental"]
            ):
                raise self._invalid("shared_cognitive_input")
            mental = interaction["mental"]
            model["mental"] = mental
            model["interaction"] = {
                k: v for k, v in interaction.items() if k != "mental"
            }
            model["affect"] = {k: v for k, v in affect.items() if k != "mental"}
            key = (mental["source_id"], mental["id"])
            if key in model_ids:
                raise self._invalid("model_identity")
            model_ids.add(key)
            agents = {a["id"] for a in mental["agents"]}
            atoms = {v["id"] for v in mental["variables"]}
            events = {e["id"]: e for e in mental["events"]}
            plans = {p["id"]: p for p in mental["plans"]}
            episodes = {e["id"]: e for e in affect["episodes"]}
            commitments = {c["id"]: c for c in interaction["commitments"]}

            def actor(value):
                if value not in agents:
                    raise self._invalid("actor")

            def formula(value):
                _formula(value, atoms, agents, modal=False)

            relation_ids = set()
            domains = set()
            for relation in rows(model["relationships"], 16):
                self._keys(relation, RELATION_FIELDS)
                identity(relation, relation_ids)
                actor(relation["observer"])
                actor(relation["target"])
                self._text(relation["domain"], 128)
                if relation["observer"] == relation["target"] or relation[
                    "dimension"
                ] not in ("ABILITY", "GOODWILL", "RELIABILITY"):
                    raise self._invalid("directed_relationship")
                key = tuple(
                    relation[k] for k in ("observer", "target", "domain", "dimension")
                )
                if key in domains:
                    raise self._invalid("duplicate_relationship_dimension")
                domains.add(key)
                if relation["factorization"] != "CONDITIONAL_INDEPENDENCE_MODEL":
                    raise self._invalid("factorization_assumption")
                hypotheses = set()
                for h in rows(relation["hypotheses"], 8, 1):
                    self._keys(h, "id label segment_ids")
                    identity(h, hypotheses)
                    self._text(h["label"], 256)
                if relation["prior"] is not None:
                    if (
                        type(relation["prior"]) is not dict
                        or set(relation["prior"]) != hypotheses
                    ):
                        raise self._invalid("prior")
                    values = [rational(v) for v in relation["prior"].values()]
                    if any(v < 0 for v in values) or sum(values) != 1:
                        raise self._invalid("prior")
                update_ids = set()
                last = -1
                for update in rows(relation["updates"], 32):
                    self._keys(update, UPDATE_FIELDS)
                    identity(update, update_ids)
                    stamp(update["at"])
                    formula(update["condition"])
                    event = events[update["event_id"]]
                    if (
                        update["at"] < last
                        or event["at"] > update["at"]
                        or update["at"] > interaction["through"]
                    ):
                        raise self._invalid("update_time")
                    last = update["at"]
                    if update["commitment_id"] is None:
                        if update["commitment_status"] is not None:
                            raise self._invalid("commitment_binding")
                    elif update["commitment_id"] not in commitments or update[
                        "commitment_status"
                    ] not in (
                        "ACTIVE",
                        "FULFILLED",
                        "BREACHED",
                        "BREACHED_THEN_FULFILLED",
                        "RELEASED",
                        "REFUSED",
                        "AWAITING_ACCEPTANCE",
                        "CONDITION_FALSE",
                        "CONDITION_UNRESOLVED",
                    ):
                        raise self._invalid("commitment_binding")
                    if (
                        type(update["likelihoods"]) is not dict
                        or set(update["likelihoods"]) != hypotheses
                        or any(
                            not 0 <= rational(v) <= 1
                            for v in update["likelihoods"].values()
                        )
                    ):
                        raise self._invalid("likelihoods")
            role_ids = set()
            for role in rows(model["roles"], 8):
                self._keys(role, ROLE_FIELDS)
                identity(role, role_ids)
                actor(role["actor"])
                stamp(role["from_time"])
                stamp(role["through_time"])
                formula(role["condition"])
                if (
                    role["from_time"] > role["through_time"]
                    or type(role["episode_actions"]) is not dict
                    or not role["episode_actions"]
                ):
                    raise self._invalid("role_scope")
                for key, actions in role["episode_actions"].items():
                    episode = episodes[key]
                    if episode["actor"] != role["actor"] or not set(
                        self._strings(actions, 32)
                    ) <= {
                        a["id"] for a in plans[episode["plan_id"]]["graph"]["actions"]
                    }:
                        raise self._invalid("role_actions")
            ids = set()
            for narrative in rows(model["identities"], 32):
                self._keys(narrative, "id at actor speaker kind content segment_ids")
                identity(narrative, ids)
                actor(narrative["actor"])
                actor(narrative["speaker"])
                stamp(narrative["at"])
                self._text(narrative["content"], 2048)
                if narrative["kind"] not in (
                    "SELF_IDENTIFICATION",
                    "OTHER_ATTRIBUTION",
                ) or (
                    narrative["kind"] == "SELF_IDENTIFICATION"
                    and narrative["actor"] != narrative["speaker"]
                ):
                    raise self._invalid("identity_narrative")
            ids = set()
            last = -1
            goal_ids = None
            context_actors = set()
            for kind in ("observations", "forecasts"):
                for context in rows(
                    model[kind], 16, 1 if kind == "observations" else 0
                ):
                    self._keys(
                        context,
                        (
                            OBSERVATION_FIELDS
                            if kind == "observations"
                            else FORECAST_FIELDS
                        ),
                    )
                    identity(context, ids)
                    self._text(context["context_id"], 128)
                    episode = episodes[context["episode_id"]]
                    context_actors.add(episode["actor"])
                    if len(context_actors) > 1:
                        raise self._invalid("longitudinal_actor_isolation")
                    if episode["at"] > interaction["through"]:
                        raise self._invalid("context_time")
                    if kind == "observations":
                        if episode["at"] < last or context["action"] not in {
                            a["id"]
                            for a in plans[episode["plan_id"]]["graph"]["actions"]
                        }:
                            raise self._invalid("observed_action")
                        last = episode["at"]
                    elif episode["at"] <= last:
                        raise self._invalid("prospective_time")
                    goals = {g["id"] for g in episode["goals"]}
                    if goal_ids is not None and goals != goal_ids:
                        raise self._invalid("cross_context_goal_identity")
                    goal_ids = goals
            mechanism_ids = set()

            def multipliers(values, keys):
                if (
                    type(values) is not dict
                    or set(values) != keys
                    or any(rational(v) < 0 for v in values.values())
                ):
                    raise self._invalid("priority_multipliers")

            for mechanism in rows(model["mechanisms"], 8, 1):
                self._keys(mechanism, MECHANISM_FIELDS)
                identity(mechanism, mechanism_ids)
                self._text(mechanism["label"], 256)
                multipliers(mechanism["goal_multipliers"], goal_ids)
                if type(mechanism["respect_roles"]) is not bool:
                    raise self._invalid("role_sensitivity")
                if mechanism["coping_id"] is None:
                    multipliers(mechanism["priorities"], goal_ids)
                    if sum(rational(v) for v in mechanism["priorities"].values()) != 1:
                        raise self._invalid("goal_priorities")
                elif mechanism["priorities"] is not None or any(
                    mechanism["coping_id"]
                    not in {c["id"] for c in episodes[context["episode_id"]]["coping"]}
                    for context in (*model["observations"], *model["forecasts"])
                ):
                    raise self._invalid("coping_binding")
                effects = set()
                for effect in rows(mechanism["relationship_effects"], 4):
                    self._keys(effect, "relationship_id multipliers segment_ids")
                    refs(effect["segment_ids"])
                    key = effect["relationship_id"]
                    if key in effects or key not in relation_ids:
                        raise self._invalid("relationship_effect")
                    effects.add(key)
                    relation = next(r for r in model["relationships"] if r["id"] == key)
                    if any(
                        episodes[c["episode_id"]]["actor"] != relation["observer"]
                        for c in (*model["observations"], *model["forecasts"])
                    ):
                        raise self._invalid("relationship_actor")
                    if set(effect["multipliers"]) != {
                        h["id"] for h in relation["hypotheses"]
                    }:
                        raise self._invalid("hypothesis_effect")
                    for values in effect["multipliers"].values():
                        multipliers(values, goal_ids)
            self._keys(model["search"], "max_segments max_candidates")
            for key, maximum in [("max_segments", 8), ("max_candidates", 256)]:
                if (
                    type(model["search"][key]) is not int
                    or not 1 <= model["search"][key] <= maximum
                ):
                    raise self._limit(key)
        return freeze(data)
