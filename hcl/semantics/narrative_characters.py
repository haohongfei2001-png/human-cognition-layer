"""Explicit packet-local M09 bindings, without cross-packet identity inference."""
import json
from hashlib import sha256
from hcl.kernel.types import thaw
from hcl.memory import codec
from hcl.semantics.relationship_compiler import RelationshipCompiler


def validate_bindings(compiler, fragment, arc, program):
    """Check the declared join; discourse positions never supply event times."""
    compiler._keys(arc, "id source_id actor assumptions bindings task")
    for field in ("id", "actor", "source_id"):
        compiler._text(arc[field], 128)
    if not set(compiler._strings(arc["assumptions"], 64)) <= set(fragment["active_assumptions"]):
        raise compiler._invalid("character_binding_assumptions")
    if len(program["models"]) != 1:
        raise compiler._invalid("character_single_model")
    model = program["models"][0]
    if (model["mental"]["source_id"] != arc["source_id"]
            or any(a["source_id"] != arc["source_id"] for a in model["mental"]["agents"])):
        raise compiler._invalid("character_source")
    sources = {s["segment_id"]: s["source_id"] for s in fragment["source_segments"]}
    events = {e["id"]: e for e in fragment["events"]}
    frames = {f["id"]: f for f in fragment["frames"]}
    episodes = {e["id"]: e for e in model["affect"]["episodes"]}
    wanted = {c["episode_id"] for c in (*model["observations"], *model["forecasts"])}
    bindings = arc["bindings"]
    if type(bindings) is not list or not 1 <= len(bindings) <= 32:
        raise compiler._limit("character_bindings")
    bound, times, frame_ids = set(), {}, set()
    for binding in bindings:
        compiler._keys(binding, "episode_id event at")
        compiler._keys(binding["event"], "fragment id")
        ref = binding["event"]
        if (type(ref["fragment"]) is not int or ref["fragment"] != fragment["fragment"]
                or ref["id"] not in events or binding["episode_id"] not in wanted
                or binding["episode_id"] in bound or ref["id"] in times):
            raise compiler._invalid("character_packet_binding")
        episode = episodes[binding["episode_id"]]
        if (type(binding["at"]) is not int or binding["at"] != episode["at"]
                or episode["actor"] != arc["actor"]):
            raise compiler._invalid("character_actor_time")
        bound.add(binding["episode_id"])
        times[ref["id"]] = binding["at"]
        event = events[ref["id"]]
        if not set(event["assumptions"]) <= set(fragment["active_assumptions"]):
            raise compiler._invalid("inactive_character_event")
        here, seen = event["frame"], set()
        frame_ids.add((here["fragment"], here["id"]))
        evidence = list(event["segment_ids"]) + list(episode["segment_ids"])
        while here is not None:
            if (here["fragment"] != fragment["fragment"] or here["id"] not in frames
                    or here["id"] in seen):
                raise compiler._invalid("character_frame_scope")
            seen.add(here["id"])
            frame = frames[here["id"]]
            evidence.extend(frame["segment_ids"])
            here = frame["parent"]
        if any(sources.get(s) != arc["source_id"] for s in evidence):
            raise compiler._invalid("character_original_source")
    if bound != wanted or len(frame_ids) != 1:
        raise compiler._invalid("character_episode_coverage_or_frame")
    validate_arc_clock(compiler, [fragment], dict(fragment=fragment["fragment"], bindings=bindings))


def validate_arc_clock(compiler, fragments, arc):
    """All known event-clock paths apply, even if an order is in a later packet."""
    def key(ref):
        return (ref["fragment"], ref["id"])
    events = {(f["fragment"], e["id"]): e for f in fragments for e in f["events"]}
    active = {f["fragment"]: set(f["active_assumptions"]) for f in fragments}
    times = {key(b["event"]): b["at"] for b in arc["bindings"]}
    adjacency = {}
    for fragment in fragments:
        for order in fragment["orders"]:
            left, right = key(order["left"]), key(order["right"])
            if (left in events and right in events
                    and events[left]["frame"] == events[right]["frame"]
                    and set(order["assumptions"]) <= active[fragment["fragment"]]
                    and all(set(events[k]["assumptions"]) <= active[k[0]] for k in (left, right))):
                adjacency.setdefault(left, []).append((right, order["strict"]))
    for start, at in times.items():
        queue, seen = [(start, False)], set()
        while queue:
            node, strict = queue.pop()
            if (node, strict) in seen:
                continue
            seen.add((node, strict))
            if node in times and (at > times[node] or (strict and at == times[node])):
                raise compiler._invalid("character_event_clock_conflict")
            queue.extend((target, strict or edge) for target, edge in adjacency.get(node, ()))


def compile_arcs(compiler, snapshot, fragment, segments, allowance):
    arcs = fragment["character_arcs"]
    if type(arcs) is not list or len(arcs) > 4:
        raise compiler._limit("character_arcs")
    seen, result = set(), []
    for arc in arcs:
        compiler._keys(arc, "id source_id actor assumptions bindings task")
        compiler._text(arc["id"], 128)
        if arc["id"] in seen:
            raise compiler._invalid("duplicate_character_arc")
        seen.add(arc["id"])
        selected = tuple(s for s in segments if s.source_id == arc["source_id"])
        if not selected:
            raise compiler._invalid("character_source")
        program = thaw(RelationshipCompiler().compile(
            snapshot, selected, json.dumps(arc["task"], ensure_ascii=False), allowance))
        validate_bindings(compiler, fragment, arc, program)
        result.append(dict(id="narrative-character:" + sha256(codec.dumps(
            [fragment["fragment"], arc["id"]])).hexdigest(), fragment=fragment["fragment"],
            local_id=arc["id"], source_id=arc["source_id"], actor=arc["actor"],
            assumptions=arc["assumptions"], bindings=arc["bindings"], program=program))
    return result
