"""Strict source-bound v2 bridge validation; no calculated attribution inputs."""

from hcl.operators.affect_attribution import VALUES

FIELDS = "id goal_id actor at event_id contributor cause_variable actual_value contrast_value outcome_value observations structures max_world_evaluations segment_ids"


def validate_bridges(compiler, episode, mental, goals, refs, rows):
    atoms = {v["id"] for v in mental["variables"]}
    agents = {a["id"] for a in mental["agents"]}
    causals = {c["id"]: c for c in mental["causal"]}
    events = {e["id"]: e for e in mental["events"]}
    bridges = {}
    for bridge in rows(episode["attributions"], 8):
        compiler._keys(bridge, FIELDS)
        compiler._text(bridge["id"], 128)
        if (bridge["id"] in bridges or bridge["goal_id"] not in goals
                or (bridge["actor"], bridge["at"]) != (episode["actor"], episode["at"])
                or type(bridge["at"]) is not int
                or bridge["contributor"] is not None and bridge["contributor"] not in agents):
            raise compiler._invalid("attribution_identity")
        if bridge["event_id"] not in events or events[bridge["event_id"]]["at"] > episode["at"]:
            raise compiler._invalid("attribution_event_binding")
        bridges[bridge["id"]] = bridge
        refs(bridge["segment_ids"])
        for key in ("actual_value", "contrast_value", "outcome_value"):
            if type(bridge[key]) is not int or bridge[key] not in (0, 1):
                raise compiler._invalid("attribution_contrast")
        if bridge["actual_value"] == bridge["contrast_value"]:
            raise compiler._invalid("attribution_no_intervention")
        if (type(bridge["max_world_evaluations"]) is not int
                or not 0 <= bridge["max_world_evaluations"] <= 4096):
            raise compiler._limit("attribution_world_bound")
        observations = bridge["observations"]
        if type(observations) is not dict or not 1 <= len(observations) <= 24:
            raise compiler._invalid("attribution_observations")
        for binding in observations.values():
            compiler._keys(binding, "atom positive")
            if binding["atom"] not in atoms or type(binding["positive"]) is not bool:
                raise compiler._invalid("attribution_atom_projection")
        seen = set()
        target = None
        for structure in rows(bridge["structures"], 8, 1):
            compiler._keys(structure, "causal_id available_when segment_ids")
            key = structure["causal_id"]
            if key in seen or key not in causals:
                raise compiler._invalid("attribution_causal_identity")
            seen.add(key)
            causal = causals[key]
            if causal["model"]["source_event_id"] not in events:
                raise compiler._invalid("attribution_structure_source_event")
            variables = set(causal["model"]["variables"])
            if (bridge["cause_variable"] not in variables
                    or bridge["cause_variable"] == causal["target"]
                    or not set(observations) <= variables
                    or causal["target"] not in observations
                    or target is not None and causal["target"] != target):
                raise compiler._invalid("attribution_causal_projection")
            target = causal["target"]
            gate = structure["available_when"]
            if (type(gate) is not dict or not gate or not set(gate) <= atoms
                    or any(type(v) is not bool for v in gate.values())):
                raise compiler._invalid("attribution_character_structure_access")
            refs(structure["segment_ids"])
    return bridges


def stable_bridges(episode):
    return [{k: v for k, v in b.items() if k != "at"} for b in episode["attributions"]]
