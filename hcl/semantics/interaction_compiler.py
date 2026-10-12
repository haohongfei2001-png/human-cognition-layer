"""Source-bound interaction proposals; no supplied beliefs, policies or verdicts."""

from copy import deepcopy
from dataclasses import asdict
import json

from hcl.kernel.types import HCLFailure, freeze, thaw
from hcl.operators.agency import rational
from hcl.operators.epistemic import _formula
from hcl.semantics.model_compiler import LocalModelCompiler, SCHEMA as MENTAL_SCHEMA

SCHEMA = "hcl-interaction-candidates-1"


def interaction_context(snapshot, question):
    from hcl.semantics.segments import segment_snapshot

    return dict(
        schema="hcl-interaction-context-1",
        candidate_schema=SCHEMA,
        purpose="PROPOSE_SOURCE_BOUND_MESSAGES_INTERPRETATIONS_COMMITMENT_RULES_AND_MESSAGE_GAMES_NOT_RESULTS",
        model_fields="mental utterances acts commitments games through max_ack_depth".split(),
        utterance_fields="id at speaker audience version literal deliveries segment_ids".split(),
        delivery_fields="event_id readings segment_ids".split(),
        reading_fields="actor contents versions segment_ids".split(),
        act_fields="id at actor audience kind refers_to version segment_ids".split(),
        commitment_fields="id offer_id speaker recipient version condition outcome deadline requires_acceptance acceptance activation withdrawal segment_ids".split(),
        game_fields="id at speaker listener plan_id messages prior speaker_prior beta listener_beta depth goal utilities sincere segment_ids".split(),
        instructions=(
            "mental is a hcl-mental-scene-candidates-1 model. Bind delivery to its existing message events; "
            "receipt, understanding, belief acceptance and social acceptance are separate. Preserve original terms versions. "
            "Received contents can differ by actor; multiple readings remain unresolved. Message meanings are declared "
            "finite extensions over an existing one-step listener plan's states. Priors and utility hypotheses must be "
            "explicit; null prior is unknown. Never supply policies, Q, lifecycle status, common knowledge or deception labels. "
            "All facts and hypotheses need original source spans; questions cannot become events."
        ),
        source_input_versions=dict(snapshot.source_versions),
        segments=[asdict(s) for s in segment_snapshot(snapshot, question)],
    )


def query_id(commitment, field, at):
    return "interaction:" + commitment["id"] + ":" + field + ":" + str(at)


def relevant_times(model, commitment):
    offer = next(u for u in model["utterances"] if u["id"] == commitment["offer_id"])
    events = {e["id"]: e for e in model["mental"]["events"]}
    return tuple(
        sorted(
            {
                t
                for t in (
                    offer["at"],
                    commitment["deadline"],
                    model["through"],
                    *(a["at"] for a in model["acts"]),
                    *(e["at"] for e in events.values()),
                )
                if offer["at"] <= t <= model["through"]
            }
        )
    )


class InteractionCompiler(LocalModelCompiler):
    def _invalid(self, field="candidate"):
        return HCLFailure(
            "INVALID_REQUEST",
            "interaction_compile",
            "INVALID_INTERACTION_CANDIDATE",
            field,
            "The proposed interaction violates its source-bound finite contract.",
        )

    def _limit(self, field):
        return HCLFailure(
            "BUDGET_EXHAUSTED",
            "interaction_compile",
            "INTERACTION_COMPILE_BOUND",
            field,
            "The interaction exceeds its explicit finite compilation bound.",
        )

    def compile(self, snapshot, segments, raw_candidate, allowance):
        try:
            return self._compile_interaction(
                snapshot, segments, raw_candidate, allowance
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

    def _compile_interaction(self, snapshot, segments, raw, allowance):
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
        by_id = {s.segment_id: s for s in segments}
        source_ids = {s.segment_id for s in segments if s.kind == "SOURCE"}

        def refs(value):
            values = self._strings(value, 64)
            if not values or not set(values) <= source_ids:
                raise self._invalid("source_span")
            return values

        def rows(value, maximum, minimum=0):
            if type(value) is not list or not minimum <= len(value) <= maximum:
                raise self._limit("rows")
            return value

        def time(value):
            if type(value) is not int or not 0 <= value <= 1000000:
                raise self._invalid("time")

        compiled = []
        for row in rows(data["models"], 8, 1):
            self._keys(
                row, "mental utterances acts commitments games through max_ack_depth"
            )
            mental = row["mental"]
            # Existing compiler still owns the base M03/M05 mechanism and anchors.
            base = LocalModelCompiler().compile(
                snapshot,
                segments,
                json.dumps(dict(schema=MENTAL_SCHEMA, models=[mental])),
                allowance,
            )
            mental = thaw(base)["models"][0]
            row["mental"] = mental
            agents = {a["id"] for a in mental["agents"]}
            atoms = {v["id"] for v in mental["variables"]}
            events = {e["id"]: e for e in mental["events"]}
            plans = {p["id"]: p for p in mental["plans"]}
            if any(q["id"].startswith("interaction:") for q in mental["queries"]):
                raise self._invalid("reserved_query_namespace")
            time(row["through"])
            if (
                type(row["max_ack_depth"]) is not int
                or not 1 <= row["max_ack_depth"] <= 8
            ):
                raise self._limit("ack_depth")

            def actor(value):
                if value not in agents:
                    raise self._invalid("actor")

            def content(value):
                if (
                    type(value) is not dict
                    or not set(value) <= atoms
                    or any(type(v) is not bool for v in value.values())
                ):
                    raise self._invalid("literal_content")

            utterances, bound_events = {}, set()
            for u in rows(row["utterances"], 32):
                self._keys(
                    u, "id at speaker audience version literal deliveries segment_ids"
                )
                self._text(u["id"], 128)
                self._text(u["version"], 128)
                time(u["at"])
                actor(u["speaker"])
                for a in self._strings(u["audience"], 8):
                    actor(a)
                if (
                    u["id"] in utterances
                    or not u["audience"]
                    or u["speaker"] in u["audience"]
                ):
                    raise self._invalid("utterance_identity")
                content(u["literal"])
                refs(u["segment_ids"])
                utterances[u["id"]] = u
                for delivery in rows(u["deliveries"], 16):
                    self._keys(delivery, "event_id readings segment_ids")
                    event = events[delivery["event_id"]]
                    if (
                        event["id"] in bound_events
                        or event["kind"] != "message"
                        or event["at"] < u["at"]
                        or event["effects"] != u["literal"]
                    ):
                        raise self._invalid("delivery_event")
                    if not set(event["received_by"]) <= set(u["audience"]):
                        raise self._invalid("delivery_audience")
                    bound_events.add(event["id"])
                    refs(delivery["segment_ids"])
                    read_actors = set()
                    for reading in rows(delivery["readings"], 8):
                        self._keys(reading, "actor contents versions segment_ids")
                        a = reading["actor"]
                        if a in read_actors or a not in event["received_by"]:
                            raise self._invalid("reading_actor")
                        read_actors.add(a)
                        versions = self._strings(reading["versions"], 4)
                        contents = rows(reading["contents"], 4)
                        if len(versions) != len(contents) or (
                            bool(contents) != (a in event["understood_by"])
                        ):
                            raise self._invalid("reading_understanding")
                        for value in contents:
                            content(value)
                        refs(reading["segment_ids"])
                    if read_actors != set(event["received_by"]):
                        raise self._invalid("missing_recipient_reading")
            act_ids = set()
            for act in rows(row["acts"], 32):
                self._keys(
                    act, "id at actor audience kind refers_to version segment_ids"
                )
                u = utterances[act["id"]]
                if act["id"] in act_ids or (
                    act["at"],
                    act["actor"],
                    act["audience"],
                    act["version"],
                ) != (u["at"], u["speaker"], u["audience"], u["version"]):
                    raise self._invalid("act_utterance_binding")
                if (
                    act["refers_to"] not in utterances
                    or utterances[act["refers_to"]]["at"] >= act["at"]
                ):
                    raise self._invalid("act_reference")
                if act["kind"] not in (
                    "ACCEPT",
                    "REFUSE",
                    "WITHDRAW",
                    "REPORT_FULFILLED",
                    "INTERPRET",
                    "ACK",
                ):
                    raise self._invalid("act_kind")
                act_ids.add(act["id"])
                refs(act["segment_ids"])
            identifiers = set()
            for c in rows(row["commitments"], 8):
                self._keys(
                    c,
                    "id offer_id speaker recipient version condition outcome deadline requires_acceptance acceptance activation withdrawal segment_ids",
                )
                self._text(c["id"], 64)
                if c["id"] in identifiers:
                    raise self._invalid("commitment_id")
                identifiers.add(c["id"])
                offer = utterances[c["offer_id"]]
                if (
                    c["speaker"] != offer["speaker"]
                    or c["recipient"] not in offer["audience"]
                    or c["version"] != offer["version"]
                ):
                    raise self._invalid("original_terms")
                time(c["deadline"])
                if (
                    c["deadline"] < offer["at"]
                    or type(c["requires_acceptance"]) is not bool
                ):
                    raise self._invalid("commitment_rule")
                if c["acceptance"] not in ("QUALIFIED_ACT", "RECEIVED_BY_OFFEROR"):
                    raise self._invalid("acceptance_effect")
                if c["activation"] not in ("CURRENT", "LATCHED") or c[
                    "withdrawal"
                ] not in ("NO_RELEASE", "RECEIVED_RELEASE"):
                    raise self._invalid("commitment_rule")
                refs(c["segment_ids"])
                _formula(c["condition"], atoms, agents, modal=False)
                _formula(c["outcome"], atoms, agents, modal=False)
            identifiers = set()
            for game in rows(row["games"], 8):
                self._keys(
                    game,
                    "id at speaker listener plan_id messages prior speaker_prior beta listener_beta depth goal utilities sincere segment_ids",
                )
                self._text(game["id"], 128)
                if game["id"] in identifiers:
                    raise self._invalid("game_id")
                identifiers.add(game["id"])
                time(game["at"])
                actor(game["speaker"])
                actor(game["listener"])
                plan = plans[game["plan_id"]]
                if (
                    game["speaker"] == game["listener"]
                    or plan["actor"] != game["listener"]
                    or plan["at"] != game["at"]
                    or plan["graph"]["horizon"] != 1
                ):
                    raise self._invalid("shared_one_step_listener_plan")
                states = set(plan["graph"]["states"])
                if len(states) > 32:
                    raise self._limit("game_states")
                message_ids = set()
                for message in rows(game["messages"], 16, 1):
                    self._keys(message, "id meaning cost segment_ids")
                    self._text(message["id"], 128)
                    if (
                        message["id"] in message_ids
                        or not set(self._strings(message["meaning"], 32)) <= states
                        or rational(message["cost"]) < 0
                    ):
                        raise self._invalid("game_message")
                    message_ids.add(message["id"])
                    refs(message["segment_ids"])
                for field in ("prior", "speaker_prior"):
                    if game[field] is not None:
                        if type(game[field]) is not dict or set(game[field]) != states:
                            raise self._invalid("game_prior")
                        weights = [rational(v) for v in game[field].values()]
                        if any(v < 0 for v in weights) or sum(weights) != 1:
                            raise self._invalid("game_prior")
                if (
                    not 0 <= rational(game["beta"]) <= 100
                    or not 0 <= rational(game["listener_beta"]) <= 100
                ):
                    raise self._invalid("game_rationality")
                if type(game["depth"]) is not int or not 0 <= game["depth"] <= 4:
                    raise self._limit("game_depth")
                if (
                    game["goal"] not in ("IDENTIFY", "ACTION")
                    or type(game["sincere"]) is not bool
                ):
                    raise self._invalid("game_goal")
                if game["goal"] == "ACTION":
                    actions = {a["id"] for a in plan["graph"]["actions"]}
                    if set(game["utilities"]) != states or any(
                        set(v) != actions for v in game["utilities"].values()
                    ):
                        raise self._invalid("speaker_action_utilities")
                    for values in game["utilities"].values():
                        for value in values.values():
                            rational(value)
                elif game["utilities"] != {}:
                    raise self._invalid("unused_utilities")
                refs(game["segment_ids"])
            compiled.append(row)
        keys = [(m["mental"]["source_id"], m["mental"]["id"]) for m in compiled]
        if len(set(keys)) != len(keys):
            raise self._invalid("model_identity")
        return freeze(dict(schema=SCHEMA, models=compiled))
