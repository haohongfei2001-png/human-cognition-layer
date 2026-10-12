"""Bounded backfill of independent historical content references.

Used only after an explicit owner-authorized migration validates the source
ledger. References, not content hashes, own lineage. Shared CAS bytes do not
merge independent tasks/sessions into one provenance or deletion unit.
"""
from collections import defaultdict
from hashlib import sha256
import json

from hcl.kernel.dependencies import unpack_dependencies
from hcl.kernel.types import TaskResult
from hcl.memory import codec
from hcl.memory.lineage import binding, retained_bindings

TABLE_KEYS = {"sessions": ("session_id",), "sources": ("session_id", "source_id"),
              "inferences": ("session_id", "result_id"), "tasks": ("task_key",),
              "calls": ("task_key", "call_id")}
SLOTS = frozenset({"object_hash", "request_hash", "result_hash", "response_hash"})


def inventory(events, read_object, *, object_size=None):
    """Return exact retained refs and explicit conservative old query lineage.

    The old inference row has no authenticated-principal field. Its otherwise
    unrecorded query scan scope is therefore a named scoped superset, never
    guessed exact provenance or new read authority. Typed snapshots retain their
    actual historical/selected/corpus bindings independently of final read_set.
    """
    previous, sources, history = {}, defaultdict(dict), defaultdict(list)
    refs, objects, event_owners, owner_bindings, edges = [], {}, {}, defaultdict(set), defaultdict(set)
    qualities, byte_count = defaultdict(set), 0

    def content(digest):
        nonlocal byte_count
        if digest not in objects:
            if len(objects) >= 50000:
                raise ValueError("retention object count bound")
            if object_size is not None:
                size = object_size(digest)
                if not 0 <= size <= 4 * 1024 * 1024:
                    raise ValueError("retention content object bound")
                byte_count += size
                if byte_count > 128 * 1024 * 1024:
                    raise ValueError("retention total content bound")
            objects[digest] = read_object(digest)
        return objects[digest]

    def dependencies(session, packed, owner):
        positive, queries = unpack_dependencies(packed)
        result = {binding(session, source, version) for source, version in positive.items()}
        for dependency in queries:
            query = dependency.query
            scope = set(query.source_scope) if query.source_scope is not None else set(sources[session])
            qualities[owner].add("LEGACY_SCOPED_QUERY_SUPERSET")
            if query.history:
                selected = {}
                for revision, source, version in history[session]:
                    if source in scope and (query.known_at is None or revision <= query.known_at):
                        selected[source] = max(selected.get(source, 0), version)
                result.update(binding(session, source, version) for source, version in selected.items())
            else:
                result.update(binding(session, source, row["version"])
                              for source, row in sources[session].items() if source in scope)
            for result_id in getattr(query, "evidence_result_ids", ()):
                edges[owner].add(("inference", session, result_id))
        return result

    for number, event in enumerate(events):
        if number >= 100000:
            raise ValueError("retention event count bound")
        session, kind = event["session_id"], event["kind"]
        digest = sha256(codec.canonical([session, event["revision"], kind,
                                        event["payload"], event["previous_hash"]]).encode()).hexdigest()
        if (kind not in TABLE_KEYS or event["previous_hash"] != previous.get(session, "")
                or digest != event["event_hash"]):
            raise ValueError("retention source event chain invalid")
        previous[session] = digest
        row = json.loads(event["payload"])
        if row.get("session_id") != session or type(event["seq"]) is not int or event["seq"] in event_owners:
            raise ValueError("retention source event identity invalid")
        if kind in ("tasks", "calls"):
            owner = ("task", session, row["task_key"])
        elif kind == "inferences":
            owner = ("inference", session, row["result_id"])
        elif kind == "sources":
            owner = ("source", session, row["source_id"], row["version"])
            sources[session][row["source_id"]] = row
            history[session].append((event["revision"], row["source_id"], row["version"]))
            owner_bindings[owner].add(binding(session, row["source_id"], row["version"]))
            qualities[owner].add("EXACT_SOURCE_VERSION_RECORD")
        else:
            owner = ("session", session)
        event_owners[event["seq"]] = owner
        for key in ("dependencies", "read_set"):
            if key in row:
                owner_bindings[owner].update(dependencies(session, json.loads(row[key]), owner))
        for slot in sorted(SLOTS & set(row)):
            digest = row[slot]
            if digest is None:
                continue
            value = content(digest)
            origin_refs = set()
            owner_bindings[owner].update(retained_bindings(value, session_id=session, origin_refs=origin_refs))
            edges[owner].update(("inference", origin_session, result_id) for origin_session, result_id in origin_refs)
            qualities[owner].add("CAPTURED_TYPED_CONTENT")
            refs.append(dict(seq=event["seq"], slot=slot, object_hash=digest, owner=owner,
                             disposable=False))
            if kind == "sources" and slot == "object_hash" and value.get("retrieval_index_hash"):
                # Cache metadata is captured without loading disposable cache
                # bytes. Missing caches remain legitimately rebuildable.
                refs.append(dict(seq=event["seq"], slot="retrieval_index_hash",
                                 object_hash=value["retrieval_index_hash"], owner=owner, disposable=True))
            if type(value) is TaskResult:
                for claim in value.claim_records:
                    edges[owner].update(("inference", session, field.result_id) for field in claim.used_result_fields)
    # Task group lineage intentionally covers every historical request/call/
    # failed checkpoint. Minimal final delivery dependencies cannot shrink it.
    queue = list(set(owner_bindings) | set(edges))
    reverse = defaultdict(set)
    recorded_owners = set(event_owners.values())
    for parent, children in edges.items():
        for child in children:
            if child not in recorded_owners:
                raise ValueError("retained result origin is missing")
            reverse[child].add(parent)
    work = 0
    while queue:
        child = queue.pop()
        work += 1
        if work > 1000000:
            raise ValueError("retention lineage propagation bound")
        for parent in reverse[child]:
            before = len(owner_bindings[parent]), len(qualities[parent])
            owner_bindings[parent].update(owner_bindings[child])
            qualities[parent].update(qualities[child])
            if before != (len(owner_bindings[parent]), len(qualities[parent])):
                queue.append(parent)
    return dict(
        references=tuple(dict(row, bindings=frozenset(owner_bindings[row["owner"]]),
                              quality=tuple(sorted(qualities[row["owner"]]))) for row in refs),
        event_bindings={seq: frozenset(owner_bindings[owner]) for seq, owner in event_owners.items()},
        owner_bindings={owner: frozenset(rows) for owner, rows in owner_bindings.items()},
        owner_quality={owner: tuple(sorted(rows)) for owner, rows in qualities.items()},
        event_owners=event_owners,
        event_heads=previous,
    )
