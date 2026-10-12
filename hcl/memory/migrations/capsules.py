"""Source-scoped copies of legacy originals, without re-running migration.

Retention classification is separate from the original evidence disposition.
An opaque report's logical support edges do not prove its text came only from
those sources. Such records remain explicitly unclassified and non-deliverable.
"""
from hashlib import sha256

from hcl.memory import codec
from hcl.memory.lineage import binding

PROTOCOL = "hcl-legacy-capsules-1"
ROOT_SCHEMA = "hcl-legacy-capsule-root-1"
STANDARD_ORIGIN = "CALLER_SUPPLIED_TYPED_SNAPSHOT"


def validate_root(value, namespace, import_hash):
    if (type(value) is not dict or value.get("origin") not in
            (STANDARD_ORIGIN, "UNCLASSIFIED_ORIGIN_RETAINED") or value != dict(
                schema=ROOT_SCHEMA, protocol=PROTOCOL, namespace=namespace,
                import_identity=import_hash, semantics="LEGACY_SUPPORT_AND_REPORTS_ARE_NOT_TRUTH",
                origin=value.get("origin"), authoritative_references="SAME_SQLITE_GOVERNED_CAPSULE_EVENTS")):
        raise ValueError("legacy capsule root contract mismatch")


def _span_source(record, descriptors, sources):
    """Only the complete closed span payload has mechanically checkable origin."""
    if record["kind"] != "SOURCE_SPAN":
        return None
    payload = record["payload"]
    if set(payload) != {"source_id", "version", "start", "end", "quote", "document_sha256"}:
        return None
    source = sources.get((payload["source_id"], payload["version"]))
    descriptor = descriptors[record["old_id"]]
    if source is None or source["text"] is None:
        return None
    start, end, text = payload["start"], payload["end"], source["text"]
    if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text)
            or text[start:end] != payload["quote"] or descriptor["reasons"]
            or descriptor["disposition"] != "MAPPED_TYPED_PROVENANCE"):
        return None
    try:
        if sha256(text.encode("utf-8")).hexdigest() != payload["document_sha256"]:
            return None
    except UnicodeEncodeError:
        return None
    return source


def split_legacy_package(package, *, session_id, import_hash):
    """Copy exact rows/descriptors; never compile or improve the old evidence.

    The caller authenticates the package and host policy before persisting these
    specs. Keys are ephemeral classification inputs, not public identifiers;
    the storage adapter replaces them with namespace-salted opaque identities.
    """
    if (package["schema"] != "hcl-legacy-migration-1"
            or sha256(codec.dumps(package)).hexdigest() != import_hash):
        raise ValueError("exact legacy package identity required")
    original = package["original"]
    if len(original["sources"]) + len(original["records"]) > 4096:
        raise ValueError("legacy capsule inventory bound")
    source_rows = {(row["source_id"], row["version"]): row for row in original["sources"]}
    if len(source_rows) != len(original["sources"]):
        raise ValueError("duplicate legacy source identity")
    source_descriptors, record_descriptors = {}, {}
    source_ordinals, record_ordinals = {}, {}
    for ordinal, descriptor in enumerate(package["records"]):
        # An unsupported legacy record can itself use the SOURCE_DOCUMENT label
        # or a source's old_key. The original typed new identity disambiguates it.
        target = source_descriptors if (descriptor["kind"] == "SOURCE_DOCUMENT"
                                        and type(descriptor["new_id"]) is dict) else record_descriptors
        if descriptor["old_key"] in target:
            raise ValueError("duplicate migration descriptor identity")
        target[descriptor["old_key"]] = descriptor
        (source_ordinals if target is source_descriptors else record_ordinals)[descriptor["old_key"]] = ordinal
    records = {row["old_id"]: row for row in original["records"]}
    if (len(records) != len(original["records"]) or set(records) != set(record_descriptors)
            or set(records) != set(package["record_mapping"])
            or {row["old_key"] for row in source_rows.values()} != set(source_descriptors)
            or set(source_descriptors) != set(package["source_mapping"])):
        raise ValueError("legacy capsule mapping membership mismatch")
    grouped = {}
    for ordinal, row in enumerate(original["sources"]):
        mapped = package["source_mapping"][row["old_key"]]
        descriptor = source_descriptors[row["old_key"]]
        if (mapped != descriptor["new_id"] or mapped["version"] != row["version"]
                or row["source_id"] not in package["host_readers"]):
            raise ValueError("legacy source mapping mismatch")
        key = row["source_id"]
        target = grouped.setdefault(key, dict(source_id=mapped["source_id"], rows=[], mapping={}, descriptors=[],
                                             original_ordinals=[], descriptor_ordinals=[]))
        if target["source_id"] != mapped["source_id"]:
            raise ValueError("one legacy source has inconsistent mapped identities")
        target["rows"].append(row)
        target["mapping"][row["old_key"]] = mapped
        target["descriptors"].append(descriptor)
        target["original_ordinals"].append(ordinal)
        target["descriptor_ordinals"].append(source_ordinals[row["old_key"]])
    if set(grouped) != set(package["host_readers"]):
        raise ValueError("legacy source policy membership mismatch")
    entries, all_bindings = [], set()
    for old_id, group in sorted(grouped.items()):
        bindings = tuple(binding(session_id, group["source_id"], row["version"]) for row in group["rows"])
        all_bindings.update(bindings)
        capsule = dict(schema=PROTOCOL, kind="SOURCE", originals=group["rows"],
                       source_mapping=group["mapping"], descriptors=group["descriptors"],
                       original_ordinals=group["original_ordinals"], descriptor_ordinals=group["descriptor_ordinals"],
                       import_readers=package["host_readers"][old_id])
        # Round-trip equality covers missing/invalid Unicode originals as well
        # as historical, withdrawn and quarantined descriptors. No normalization.
        restored = codec.loads(codec.dumps(capsule))
        if any(codec.dumps(a) != codec.dumps(b) for a, b in zip(group["rows"], restored["originals"])):
            raise ValueError("legacy source bytes changed during capsule split")
        entries.append(dict(key=("source", group["source_id"]), kind="SOURCE", source_id=group["source_id"],
                            versions=sorted(row["version"] for row in group["rows"]),
                            readers=package["host_readers"][old_id], bindings=bindings, value=capsule))
    original_record_ordinals = {row["old_id"]: index for index, row in enumerate(original["records"])}
    for old_id, record in sorted(records.items()):
        descriptor = record_descriptors[old_id]
        if descriptor["new_id"] != package["record_mapping"][old_id]:
            raise ValueError("legacy record mapping mismatch")
        source = _span_source(record, record_descriptors, source_rows)
        bindings = ()
        if source is not None:
            mapped = package["source_mapping"][source["old_key"]]
            bindings = (binding(session_id, mapped["source_id"], mapped["version"]),)
        entries.append(dict(key=("record", old_id), kind="SOURCE_SPAN" if bindings else "UNKNOWN_PROVENANCE",
                            source_id=None, versions=[], readers=[], bindings=bindings,
                            value=dict(schema=PROTOCOL, kind="RECORD", original=record,
                                       original_ordinal=original_record_ordinals[old_id], descriptor_ordinal=record_ordinals[old_id],
                                       record_mapping={old_id: package["record_mapping"][old_id]}, descriptor=descriptor)))
    origin = original["origin"]
    if origin != STANDARD_ORIGIN:
        entries.append(dict(key=("origin",), kind="UNKNOWN_PROVENANCE", source_id=None, versions=[],
                            readers=[], bindings=(), value=dict(schema=PROTOCOL, kind="ORIGIN", original=origin)))
    root = dict(schema=ROOT_SCHEMA, protocol=PROTOCOL, namespace=package["namespace"],
                import_identity=import_hash, semantics="LEGACY_SUPPORT_AND_REPORTS_ARE_NOT_TRUTH",
                origin=STANDARD_ORIGIN if origin == STANDARD_ORIGIN else "UNCLASSIFIED_ORIGIN_RETAINED",
                authoritative_references="SAME_SQLITE_GOVERNED_CAPSULE_EVENTS")
    return dict(root=root, entries=tuple(entries), package_bindings=tuple(sorted(all_bindings)))
