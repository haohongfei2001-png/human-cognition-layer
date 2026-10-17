"""V3 explicit source-local joins of additive, independently grounded M09 inputs.

A declaration owns static model identity and search policy. Contributions can
only add source-bound records, never replace initial knowledge or mechanisms.
Packet/discourse order is not an event clock. The assembled model still passes
all original M03/M05/M07/M08/M09 bounds and validators.
"""
from copy import deepcopy
from hashlib import sha256
import json

from hcl.kernel.types import thaw
from hcl.memory import codec
from hcl.semantics.relationship_compiler import RelationshipCompiler, MODEL_FIELDS
from hcl.semantics.model_compiler import MODEL_FIELDS as MENTAL_FIELDS
from hcl.semantics.narrative_characters import validate_arc_clock

SCHEMA = "hcl-literature-fragment-3"
COMPOSED = "hcl-literature-composed-3"
# Whitelisted additive collections. Scalars and initial observations are owned
# by the declaration; later packets cannot silently rewrite them.
IDENTIFIER_MAPS = frozenset({
    "effects", "utilities", "priorities", "goal_multipliers", "weights",
    "previous_weights", "current_weights", "prior", "likelihoods",
    "multipliers", "observation_overrides", "transitions", "observations",
    "interventions", "habit", "literal", "speaker_prior", "episode_actions",
})
COLLECTIONS = {
    "mental": {"events": 32, "queries": 32, "plans": 8},
    "interaction": {"utterances": 32, "acts": 32, "commitments": 8, "games": 8},
    "affect": {"episodes": 16, "channels": 32},
    "relationships": 16, "roles": 8, "identities": 32,
    "observations": 16, "forecasts": 16,
}


def key(ref):
    return ref["fragment"], ref["id"]


def paths():
    for parent, fields in COLLECTIONS.items():
        if isinstance(fields, dict):
            for field, bound in fields.items():
                yield (parent, field), bound
        else:
            yield (parent,), fields


def collection(value, path):
    return value[path[0]] if len(path) == 1 else value[path[0]][path[1]]


def semantic_container(field, value):
    return (field in IDENTIFIER_MAPS and isinstance(value, dict)) or (
        field == "contents" and isinstance(value, list))


def grounded_refs(compiler, value, sources, source_id):
    """Every nested evidence reference belongs to this actual reading packet."""
    used = set()
    if isinstance(value, dict):
        for field, item in value.items():
            # These dictionaries have user-declared semantic identifiers as
            # keys, not record field names. A variable named "segment_ids"
            # is not an evidence field. Their values are checked by M03–M09.
            if semantic_container(field, item):
                continue
            if field in ("segment_ids", "unmodeled_segments"):
                refs = compiler._strings(item, 64)
                if (field == "segment_ids" and not refs) or any(
                    sources.get(s) != source_id for s in refs
                ):
                    raise compiler._invalid("character_contribution_source")
                used.update(refs)
            else:
                used.update(grounded_refs(compiler, item, sources, source_id))
    elif isinstance(value, list):
        for item in value:
            used.update(grounded_refs(compiler, item, sources, source_id))
    return used


def validate_local(compiler, fragment, total):
    """Local grounding now; explicit cross-packet dependency closure at compose."""
    sources = {s["segment_id"]: s["source_id"] for s in fragment["source_segments"]}
    active = set(fragment["active_assumptions"])
    used = set()

    def ref(value):
        compiler._keys(value, "fragment id")
        if type(value["fragment"]) is not int or not 0 <= value["fragment"] < total:
            raise compiler._invalid("character_reference")
        compiler._text(value["id"], 128)

    for field in ("character_models", "character_contributions"):
        rows = fragment[field]
        if type(rows) is not list or len(rows) > 4:
            raise compiler._limit(field)
        seen = set()
        for row in rows:
            declaration = field == "character_models"
            compiler._keys(row, "id source_id actor frame assumptions segment_ids " +
                ("model" if declaration else "declaration bindings additions"))
            for name in ("id", "source_id", "actor"):
                compiler._text(row[name], 128)
            if row["id"] in seen:
                raise compiler._invalid("duplicate_" + field)
            seen.add(row["id"])
            if not set(compiler._strings(row["assumptions"], 64)) <= active:
                raise compiler._invalid("character_binding_assumptions")
            ref(row["frame"])
            used.update(grounded_refs(compiler, row, sources, row["source_id"]))
            payload_refs = grounded_refs(compiler, row["model" if declaration else "additions"], sources, row["source_id"])
            if not set(row["segment_ids"]) <= payload_refs:
                raise compiler._invalid("character_unaccounted_contribution_sources")
            if declaration:
                model = row["model"]
                compiler._keys(model, MODEL_FIELDS)
                compiler._keys(model["mental"], MENTAL_FIELDS)
                compiler._text(model["mental"]["id"], 128)
                compiler._keys(model["interaction"], "utterances acts commitments games through max_ack_depth")
                compiler._keys(model["affect"], "episodes channels")
                if (row["frame"]["fragment"] != fragment["fragment"]
                        or model["mental"]["source_id"] != row["source_id"]
                        or any(a["source_id"] != row["source_id"] for a in model["mental"]["agents"])
                        or row["actor"] not in {a["id"] for a in model["mental"]["agents"]}):
                    raise compiler._invalid("character_declaration_identity")
                for path, _ in paths():
                    if collection(model, path) != []:
                        raise compiler._invalid("character_declaration_not_static")
            else:
                ref(row["declaration"])
                additions = row["additions"]
                compiler._keys(additions, " ".join(COLLECTIONS))
                for parent, fields in COLLECTIONS.items():
                    if isinstance(fields, dict):
                        compiler._keys(additions[parent], " ".join(fields))
                for path, bound in paths():
                    values = collection(additions, path)
                    if type(values) is not list or len(values) > bound:
                        raise compiler._limit("character_contribution_rows")
                if type(row["bindings"]) is not list or len(row["bindings"]) > 32:
                    raise compiler._limit("character_bindings")
                seen_episodes = set()
                for binding in row["bindings"]:
                    compiler._keys(binding, "episode_id event at")
                    compiler._text(binding["episode_id"], 128)
                    ref(binding["event"])
                    if (type(binding["at"]) is not int or not 0 <= binding["at"] <= 1000000
                            or binding["episode_id"] in seen_episodes):
                        raise compiler._invalid("character_actor_time")
                    seen_episodes.add(binding["episode_id"])
                wanted = {c["episode_id"] for c in additions["observations"] + additions["forecasts"]}
                wanted.update(e["id"] for e in additions["affect"]["episodes"])
                if seen_episodes != wanted:
                    raise compiler._invalid("character_contribution_binding_coverage")
    return used


def _merge_record(compiler, left, right, source_fields=True):
    """An explicit repeated record may add provenance, never change its meaning."""
    if isinstance(left, dict) and isinstance(right, dict) and set(left) == set(right):
        return {k: sorted(set(left[k]) | set(right[k])) if source_fields and k == "segment_ids"
                else _merge_record(compiler, left[k], right[k], source_fields and not (
                    semantic_container(k, left[k]))) for k in left}
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        return [_merge_record(compiler, a, b, source_fields) for a, b in zip(left, right)]
    if type(left) is not type(right) or left != right:
        raise compiler._invalid("character_conflicting_record")
    return deepcopy(left)


def compose_shared(compiler, snapshot, fragments, segments, allowance):
    declarations, groups, identities = {}, {}, set()
    for fragment in fragments:
        if fragment["schema"] != SCHEMA:
            continue
        validate_local(compiler, fragment, len(fragments))
        for row in fragment["character_models"]:
            identity = (row["source_id"], row["model"]["mental"]["id"])
            if identity in identities:
                raise compiler._invalid("character_duplicate_model_identity")
            identities.add(identity)
            declarations[(fragment["fragment"], row["id"])] = row
        for row in fragment["character_contributions"]:
            groups.setdefault(key(row["declaration"]), []).append((fragment, row))
    if set(groups) != set(declarations):
        raise compiler._invalid("character_declaration_reference")
    if len(declarations) > 16:
        raise compiler._limit("composed_character_models")
    frames = {(f["fragment"], r["id"]): r for f in fragments for r in f["frames"]}
    events = {(f["fragment"], r["id"]): r for f in fragments for r in f["events"]}
    source_ids = {s.segment_id: s.source_id for s in segments}
    active = {f["fragment"]: set(f["active_assumptions"]) for f in fragments}
    result = []
    for declaration_ref, declaration in declarations.items():
        model = deepcopy(declaration["model"])
        bindings, event_episodes, evidence, conditions = {}, {}, set(), []
        contributions = groups[declaration_ref]
        for fragment_id, row in [(declaration_ref[0], declaration)] + [(f["fragment"], r) for f, r in contributions]:
            conditions.extend(dict(fragment=fragment_id, id=a) for a in row["assumptions"])
            evidence.update(grounded_refs(compiler, row, source_ids, declaration["source_id"]))
            if any(row[field] != declaration[field] for field in ("source_id", "actor", "frame")):
                raise compiler._invalid("character_shared_identity_or_frame")
        frame, seen = key(declaration["frame"]), set()
        while True:
            if frame not in frames or frame in seen:
                raise compiler._invalid("character_frame_scope")
            seen.add(frame)
            evidence.update(frames[frame]["segment_ids"])
            parent = frames[frame]["parent"]
            if parent is None:
                break
            frame = key(parent)
        for path, bound in paths():
            rows = {}
            for _, contribution in contributions:
                for record in collection(contribution["additions"], path):
                    compiler._text(record["id"], 128)
                    rows[record["id"]] = (_merge_record(compiler, rows[record["id"]], record)
                        if record["id"] in rows else deepcopy(record))
            if len(rows) > bound:
                raise compiler._limit("composed_character_rows")
            collection(model, path).extend(rows.values())
        episodes = {e["id"]: e for e in model["affect"]["episodes"]}
        base_episodes = {}
        for episode in episodes.values():
            base_identity = (episode["actor"], episode["episode_id"])
            if base_identity in base_episodes:
                # M08 id names a version/display record. Rebranding the same
                # explicitly declared underlying episode cannot add evidence.
                previous = episodes[base_episodes[base_identity]]
                raise compiler._invalid("character_episode_time_conflict" if previous["at"] != episode["at"]
                    else "character_episode_identity_alias")
            base_episodes[base_identity] = episode["id"]
        actions = {}
        for observation in model["observations"]:
            eid = observation["episode_id"]
            if eid in actions and actions[eid] != observation["action"]:
                raise compiler._invalid("character_conflicting_episode_observations")
            actions[eid] = observation["action"]
        wanted = {c["episode_id"] for c in model["observations"] + model["forecasts"]}
        for _, contribution in contributions:
            for binding in contribution["bindings"]:
                eid, event_key = binding["episode_id"], key(binding["event"])
                if eid in bindings and bindings[eid] != binding:
                    raise compiler._invalid("character_conflicting_binding")
                if event_key in event_episodes and event_episodes[event_key] != eid:
                    raise compiler._invalid("character_event_alias")
                bindings[eid], event_episodes[event_key] = binding, eid
                event, episode = events.get(event_key), episodes.get(eid)
                if (event is None or episode is None or event["frame"] != declaration["frame"]
                        or episode["at"] != binding["at"] or episode["actor"] != declaration["actor"]
                        or not set(event["assumptions"]) <= active[event_key[0]]):
                    raise compiler._invalid("character_shared_event_binding")
                evidence.update(event["segment_ids"])
        if set(bindings) != wanted or set(episodes) != wanted:
            raise compiler._invalid("character_episode_coverage")
        if any(source_ids.get(s) != declaration["source_id"] for s in evidence):
            raise compiler._invalid("character_original_source")
        # Sort by declared story time and stable local identity, never packet or
        # discourse order. Forecasts and duplicate factors retain M09 semantics.
        for path, _ in paths():
            def clock(row):
                return episodes[row["episode_id"]]["at"] if path[0] in ("observations", "forecasts") else row.get("at", row.get("from_time", -1))
            collection(model, path).sort(key=lambda r: (clock(r), r["id"]))
        if any(not set(e["assumptions"]) <= set(model["mental"]["active_assumptions"])
               for e in model["mental"]["events"]):
            raise compiler._invalid("inactive_character_cognitive_event")
        # M03 must account for exactly its own grounded inputs, not pretend
        # later M07/M08/M09-only evidence is a cognitive event or unmodeled text.
        # Upper compilers still see/validate the complete joined evidence set.
        source_layers = {name: sorted(grounded_refs(compiler, model[name], source_ids,
            declaration["source_id"])) for name in MODEL_FIELDS.split() if name != "search"}
        selected = tuple(s for s in segments if s.segment_id in evidence)
        mental_segments = tuple(s for s in selected if s.segment_id in source_layers["mental"])
        program = thaw(RelationshipCompiler().compile(snapshot, selected,
            json.dumps(dict(schema="hcl-relationship-candidates-1", models=[model])), allowance,
            mental_segments=mental_segments))
        program["models"][0]["evidence_protocol"] = "explicit-narrative-episode-1"
        arc = dict(id="narrative-shared-character:" + sha256(codec.dumps([
            declaration["source_id"], model["mental"]["id"], declaration["actor"]])).hexdigest(),
            fragment=declaration_ref[0], local_id=declaration_ref[1],
            source_id=declaration["source_id"], actor=declaration["actor"], assumptions=declaration["assumptions"],
            bindings=sorted(bindings.values(), key=lambda b: (b["at"], b["episode_id"])), program=program,
            composition=dict(schema="explicit-character-join-1", declaration=dict(fragment=declaration_ref[0], id=declaration_ref[1]),
                model_id=model["mental"]["id"], frame=declaration["frame"],
                contributions=[dict(fragment=f["fragment"], id=r["id"]) for f, r in contributions],
                assumption_refs=sorted(conditions, key=lambda a: (a["fragment"], a["id"])),
                segment_ids=sorted(evidence), source_layers=source_layers))
        validate_arc_clock(compiler, fragments, arc)
        result.append(arc)
    return result
