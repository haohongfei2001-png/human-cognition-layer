"""Source-anchored finite mental/plan/causal model proposals, never answers.

The input is a candidate generative mechanism. Acceptance of its syntax and
anchors does not certify semantic alignment, extraction quality or completeness.
"""

from dataclasses import asdict
import json

from hcl.kernel.types import HCLFailure, freeze
from hcl.operators.agency import Action, PlanModel, rational
from hcl.operators.epistemic import _formula
from hcl.semantics.compiler import SemanticCompiler
from hcl.v09.runtime import CausalModel, StructuralRule

SCHEMA = "hcl-mental-scene-candidates-1"
MODEL_FIELDS = "id source_id frame_kind assumptions active_assumptions unmodeled_segments agents variables events queries plans causal"
EVENT_FIELDS = "id at kind effects seen_by received_by understood_by trusted_by assumptions segment_ids"
KINDS = {"SOURCE_DISCOURSE", "QUOTATION", "HYPOTHETICAL", "COUNTERFACTUAL", "INTERPRETATION"}


def planning_model(data):
    return PlanModel(
        tuple(data["states"]),
        tuple(data["terminal"]),
        data["utilities"],
        tuple(
            Action(
                row["id"],
                row["cost"],
                tuple(row["enabled"]),
                tuple(row["feasible"]),
                row["transitions"],
                row["observations"],
            )
            for row in data["actions"]
        ),
    )


def structural_model(data):
    return CausalModel(
        data["id"],
        data["source_event_id"],
        tuple(data["variables"]),
        tuple(data["exogenous"]),
        tuple(
            StructuralRule(row["target"], row["expression"], row["evidence_text"]) for row in data["rules"]
        ),
    )


def model_context(snapshot, question):
    from hcl.semantics.segments import segment_snapshot

    return dict(
        schema="hcl-mental-scene-context-1",
        candidate_schema=SCHEMA,
        purpose="PROPOSE_SOURCE_ANCHORED_EVENT_OBSERVATION_AND_ACTION_MODELS_NOT_MENTAL_ANSWERS",
        model_fields=MODEL_FIELDS.split(),
        event_fields=EVENT_FIELDS.split(),
        query_fields="id at formula segment_ids".split(),
        plan_fields="id actor at graph bindings weights policy segment_ids".split(),
        instructions=(
            "Propose finite Boolean variables and initial observation channels, then actual event effects and distinct "
            "seen/received/understood/trusted candidates. Never provide resulting beliefs, action Q/scores, choices, "
            "solver labels or executable code. All records require exact source anchors; questions are not facts. "
            "Keep competing source interpretations, explicit persistence/observation assumptions and unmodeled material. "
            "Planning inputs are actions, costs, transitions, observation symbols and goal utilities. "
            "Do not invent calibrated probabilities; absent weights for multiple states remain unresolved."
        ),
        source_input_versions=dict(snapshot.source_versions),
        segments=[asdict(segment) for segment in segment_snapshot(snapshot, question)],
    )


class LocalModelCompiler(SemanticCompiler):
    def _invalid(self, field="candidate"):
        return HCLFailure(
            "INVALID_REQUEST",
            "model_compile",
            "INVALID_LOCAL_MODEL_CANDIDATE",
            field,
            "The candidate mechanism violates its typed source-bound dialect.",
        )

    def _limit(self, field):
        return HCLFailure(
            "BUDGET_EXHAUSTED",
            "model_compile",
            "LOCAL_MODEL_COMPILE_BOUND",
            field,
            "The finite candidate mechanism exceeds its declared compilation bound.",
        )

    def compile(self, snapshot, segments, raw_candidate, allowance):
        try:
            return self._compile_model(snapshot, segments, raw_candidate, allowance)
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

    def _compile_model(self, snapshot, segments, raw_candidate, allowance):
        if type(raw_candidate) is not str or len(raw_candidate.encode()) > min(
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
            raw_candidate,
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(self._invalid("nonfinite_value")),
        )
        self._keys(data, "schema models")
        if (
            data["schema"] != SCHEMA
            or type(data["models"]) is not list
            or not 1 <= len(data["models"]) <= 4
        ):
            raise self._invalid("schema")
        by_id = {segment.segment_id: segment for segment in segments}
        if len(by_id) != len(segments):
            raise self._invalid("segments")
        source_ids = {key for key, segment in by_id.items() if segment.kind == "SOURCE"}
        if not source_ids:
            raise HCLFailure(
                "NEEDS_EVIDENCE",
                "model_compile",
                "NO_MODEL_SOURCES",
                "source_handles",
                "An executable cognitive model needs authorized original evidence.",
            )
        used = set()
        model_ids = set()

        def refs(raw, *, question=False):
            keys = self._strings(raw)
            if not keys or not set(keys) <= set(by_id) or (not question and not set(keys) <= source_ids):
                raise self._invalid("segment_ids")
            used.update(set(keys) & source_ids)
            return keys

        def at(value):
            if type(value) is not int or not 0 <= value <= 1000000:
                raise self._invalid("model_time")

        def rows(model, name, maximum, minimum=0):
            value = model[name]
            if type(value) is not list or not minimum <= len(value) <= maximum:
                raise self._limit(name)
            return value

        for model in data["models"]:
            self._keys(model, MODEL_FIELDS)
            identity = self._text(model["id"], 128)
            if (
                model["source_id"] not in snapshot.source_versions
                or model["frame_kind"] not in KINDS
                or (model["source_id"], identity) in model_ids
            ):
                raise self._invalid("model_scope")
            model_ids.add((model["source_id"], identity))
            self._strings(model["assumptions"])
            active = set(self._strings(model["active_assumptions"]))
            unmodeled = self._strings(model["unmodeled_segments"])
            if not set(unmodeled) <= source_ids:
                raise self._invalid("unmodeled_segments")
            used.update(unmodeled)
            agents = {}
            for agent in rows(model, "agents", 8, 1):
                self._keys(agent, "id label source_id segment_ids")
                key = self._text(agent["id"], 128)
                self._text(agent["label"], 256)
                if key in agents or agent["source_id"] not in snapshot.source_versions:
                    raise self._invalid("agent")
                if any(by_id[r].source_id != agent["source_id"] for r in refs(agent["segment_ids"])):
                    raise self._invalid("agent_source")
                agents[key] = agent

            def agent_refs(value):
                identities = self._strings(value, 8)
                if not set(identities) <= set(agents):
                    raise self._invalid("agent_reference")
                return identities

            atoms = {}
            for variable in rows(model, "variables", 8, 1):
                self._keys(variable, "id initial observed_by segment_ids")
                key = self._text(variable["id"], 128)
                if key in atoms or (
                    variable["initial"] is not None and type(variable["initial"]) is not bool
                ):
                    raise self._invalid("variable")
                agent_refs(variable["observed_by"])
                refs(variable["segment_ids"])
                atoms[key] = variable
            event_ids = set()
            times = set()
            for event in rows(model, "events", 32):
                self._keys(event, EVENT_FIELDS)
                key = self._text(event["id"], 128)
                at(event["at"])
                if key in event_ids or event["at"] in times:
                    raise self._invalid("event_order_ambiguity")
                event_ids.add(key)
                times.add(event["at"])
                if (
                    event["kind"] not in ("change", "message")
                    or type(event["effects"]) is not dict
                    or not set(event["effects"]) <= set(atoms)
                    or any(type(v) is not bool for v in event["effects"].values())
                ):
                    raise self._invalid("event_effects")
                for field in ("seen_by", "received_by", "understood_by", "trusted_by"):
                    agent_refs(event[field])
                if not set(event["understood_by"]) <= set(event["received_by"]):
                    raise self._invalid("message_understanding")
                if not set(event["trusted_by"]) <= set(event["understood_by"]):
                    raise self._invalid("message_trust")
                if event["kind"] == "change" and any(
                    event[field] for field in ("received_by", "understood_by", "trusted_by")
                ):
                    raise self._invalid("change_channels")
                if event["kind"] == "message" and event["seen_by"]:
                    raise self._invalid("message_channels")
                refs(event["segment_ids"])
                self._strings(event["assumptions"])
            declared = set(model["assumptions"]) | {
                a for event in model["events"] for a in event["assumptions"]
            }
            if not active <= declared:
                raise self._invalid("active_assumptions")
            queries = set()
            for query in rows(model, "queries", 32):
                self._keys(query, "id at formula segment_ids")
                key = self._text(query["id"], 128)
                at(query["at"])
                if key in queries:
                    raise self._invalid("query_id")
                queries.add(key)
                _formula(query["formula"], atoms, agents)
                refs(query["segment_ids"], question=True)
            plans = set()
            for plan in rows(model, "plans", 8):
                self._keys(plan, "id actor at graph bindings weights policy segment_ids")
                key = self._text(plan["id"], 128)
                at(plan["at"])
                if key in plans or plan["actor"] not in agents:
                    raise self._invalid("plan_actor")
                plans.add(key)
                refs(plan["segment_ids"])
                graph = plan["graph"]
                self._keys(graph, "states terminal utilities actions horizon")
                self._strings(graph["states"], 128)
                self._strings(graph["terminal"], 128)
                if type(graph["horizon"]) is not int or not 1 <= graph["horizon"] <= 16:
                    raise self._limit("plan_horizon")
                for action in graph["actions"]:
                    self._keys(action, "id cost enabled feasible transitions observations")
                typed = planning_model(graph)
                if type(plan["bindings"]) is not list or not 1 <= len(plan["bindings"]) <= 128:
                    raise self._limit("state_bindings")
                for binding in plan["bindings"]:
                    self._keys(binding, "state when")
                    if binding["state"] not in typed.states:
                        raise self._invalid("state_binding")
                    _formula(binding["when"], atoms, agents, modal=False)
                if plan["weights"] is not None:
                    if type(plan["weights"]) is not dict or not set(plan["weights"]) <= set(typed.states):
                        raise self._invalid("planning_weights")
                    values = [rational(value) for value in plan["weights"].values()]
                    if any(value < 0 for value in values) or sum(values) != 1:
                        raise self._invalid("planning_weights")
                if plan["policy"] is not None:
                    self._keys(plan["policy"], "beta rational_weight habit_weight error_weight habit")
                    for name in ("beta", "rational_weight", "habit_weight", "error_weight"):
                        rational(plan["policy"][name])
            causals = set()
            for causal in rows(model, "causal", 8):
                self._keys(causal, "id model target observations interventions segment_ids")
                key = self._text(causal["id"], 128)
                if key in causals:
                    raise self._invalid("causal_id")
                causals.add(key)
                refs(causal["segment_ids"])
                c = causal["model"]
                self._keys(c, "id source_event_id variables exogenous rules")
                for rule in c["rules"]:
                    self._keys(rule, "target expression evidence_text")
                anchored = tuple(by_id[key].text for key in causal["segment_ids"])
                if any(not any(rule["evidence_text"] in text for text in anchored) for rule in c["rules"]):
                    raise self._invalid("causal_rule_source_excerpt")
                typed = structural_model(c)
                if causal["target"] not in typed.variables:
                    raise self._invalid("causal_target")
                for name in ("observations", "interventions"):
                    if (
                        type(causal[name]) is not dict
                        or not set(causal[name]) <= set(typed.variables)
                        or any(
                            type(value) is not int or value not in (0, 1) for value in causal[name].values()
                        )
                    ):
                        raise self._invalid("causal_assignment")
            if not (queries or plans or causals):
                raise self._invalid("no_computational_obligations")
        if not source_ids <= used:
            raise self._invalid("unaccounted_source_segments")
        return freeze(data)
