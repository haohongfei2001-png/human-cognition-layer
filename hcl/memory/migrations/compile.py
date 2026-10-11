"""Deterministic typed side-copy mapping. No old interpretation becomes a fact."""
from collections import Counter
from hashlib import sha256

from hcl.kernel.scope import identifier
from hcl.kernel.types import FormalProblem, thaw
from hcl.memory import codec
from .types import LegacyRecord, LegacySnapshot, LegacySource

MAX_RECORDS = 4096
MAX_BYTES = 16 * 1024 * 1024
KINDS = {"SOURCE_SPAN", "SOURCE_REPORT", "SYSTEM_INTERPRETATION", "CONDITIONAL_TOOL_RESULT",
         "INTERPRETATION_REVISION", "SCOPED_EVIDENCE_RECEIPT", "REPORT_ASSESSMENT", "ORDER_EVENT", "NARRATIVE_ORDER"}


def source_key(source_id, version):
    return codec.canonical(["source", source_id, version])


def mapped_id(namespace, kind, key):
    return f"migrated-{kind}:" + sha256(codec.canonical([namespace, kind, key]).encode()).hexdigest()


def compile_snapshot(snapshot, namespace):
    if type(snapshot) is not LegacySnapshot or len(snapshot.sources) + len(snapshot.records) > MAX_RECORDS:
        raise ValueError("bounded typed legacy snapshot required")
    identifier(namespace)
    identifier(snapshot.origin)
    sources = []
    seen = set()
    for source in snapshot.sources:
        if type(source) is not LegacySource:
            raise ValueError("typed legacy source required")
        identifier(source.source_id)
        if type(source.version) is not int or source.version < 1 or source.status not in ("CURRENT", "HISTORICAL", "WITHDRAWN"):
            raise ValueError("explicit source version and lifecycle required")
        if source.text is not None and type(source.text) is not str:
            raise ValueError("source text or missing original required")
        if source.formal_problem is not None and type(source.formal_problem) is not FormalProblem:
            raise ValueError("explicit formal interpretation required")
        key = source_key(source.source_id, source.version)
        if key in seen:
            raise ValueError("duplicate legacy source identity")
        seen.add(key)
        sources.append(dict(old_key=key, source_id=source.source_id, version=source.version, text=source.text,
                            status=source.status, metadata=thaw(source.metadata), formal_problem=source.formal_problem))
    raw_records = []
    seen = set()
    for record in snapshot.records:
        if type(record) is not LegacyRecord:
            raise ValueError("typed legacy record required")
        identifier(record.old_id)
        identifier(record.kind)
        if record.old_id in seen or record.status not in ("LEGACY_ONLY", "WITHDRAWN"):
            raise ValueError("unique old record identity and lifecycle required")
        seen.add(record.old_id)
        raw_records.append(dict(old_id=record.old_id, kind=record.kind, payload=thaw(record.payload), status=record.status))
    original = dict(origin=snapshot.origin, sources=sources, records=raw_records)
    if len(codec.dumps(original)) > MAX_BYTES:
        raise ValueError("migration package exceeds the explicit offline import bound")
    source_mapping = {row["old_key"]: {"source_id": mapped_id(namespace, "source", row["source_id"]),
                                       "version": row["version"]} for row in sources}
    record_mapping = {row["old_id"]: mapped_id(namespace, "record", row["old_id"]) for row in raw_records}
    current_counts = Counter(row["source_id"] for row in sources if row["status"] == "CURRENT")
    usable, migrated = [], []
    originals = {(row["source_id"], row["version"]): row for row in sources}
    for row in sources:
        reasons = []
        if row["text"] is None:
            reasons.append("ORIGINAL_DOCUMENT_UNAVAILABLE")
        else:
            try:
                row["text"].encode("utf-8")
            except UnicodeEncodeError:
                reasons.append("INVALID_SOURCE_ENCODING")
        if row["status"] == "CURRENT" and current_counts[row["source_id"]] != 1:
            reasons.append("AMBIGUOUS_CURRENT_VERSION")
        mapped = dict(old_key=row["old_key"], new_id=source_mapping[row["old_key"]], kind="SOURCE_DOCUMENT",
                      lifecycle=row["status"], disposition="QUARANTINED" if reasons else "MAPPED_TYPED_PROVENANCE",
                      reasons=reasons, recoverable_fields=sorted(row), truth="NOT_ESTABLISHED")
        migrated.append(mapped)
        if not reasons and row["status"] == "CURRENT":
            usable.append(row)
    for row in raw_records:
        payload, reasons = row["payload"], []
        kind = row["kind"]
        if kind not in KINDS:
            reasons.append("UNSUPPORTED_LEGACY_KIND")
        converted = {}
        if kind == "SOURCE_SPAN":
            source = originals.get((payload.get("source_id"), payload.get("version")))
            start, end = payload.get("start"), payload.get("end")
            text = source["text"] if source else None
            if text is None:
                reasons.append("ORIGINAL_DOCUMENT_UNAVAILABLE")
            elif any(0xD800 <= ord(char) <= 0xDFFF for char in text):
                reasons.append("INVALID_SOURCE_ENCODING")
            elif (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text)
                  or text[start:end] != payload.get("quote")
                  or sha256(text.encode()).hexdigest() != payload.get("document_sha256")):
                reasons.append("SOURCE_SPAN_IDENTITY_MISMATCH")
            else:
                converted["source"] = source_mapping[source["old_key"]]
        if kind in ("SOURCE_REPORT", "SYSTEM_INTERPRETATION", "CONDITIONAL_TOOL_RESULT"):
            groups = payload.get("supports", [])
            challenges = payload.get("challenges", [])
            interpretation = payload.get("interpretation")
            valid = (type(groups) is list and all(type(group) is list and all(type(ref) is str for ref in group) for group in groups)
                     and type(challenges) is list and all(type(ref) is str for ref in challenges)
                     and (interpretation is None or (type(interpretation) is dict and all(
                         type(interpretation.get(field, [])) is list and all(type(ref) is str for ref in interpretation.get(field, []))
                         for field in ("required_premises", "alternatives", "unknown_conditions")))))
            if not valid:
                reasons.append("INVALID_LEGACY_REFERENCE_SHAPE")
                groups, challenges, interpretation = [], [], None
            refs = [ref for group in groups for ref in group] + challenges
            if payload.get("projection_of") is not None:
                refs.append(payload["projection_of"])
            if interpretation:
                refs += list(interpretation.get("required_premises", ())) + list(interpretation.get("alternatives", ()))
            if any(type(ref) is not str or ref not in record_mapping for ref in refs):
                reasons.append("INCOMPLETE_LEGACY_REFERENCES")
            else:
                converted["support_groups"] = [[record_mapping[ref] for ref in group] for group in groups]
                converted["challenges"] = [record_mapping[ref] for ref in challenges]
                converted["projection_of"] = record_mapping[payload["projection_of"]] if payload.get("projection_of") is not None else None
                if interpretation:
                    converted["interpretation"] = {
                        "required_premises": [record_mapping[ref] for ref in interpretation.get("required_premises", [])],
                        "alternatives": [record_mapping[ref] for ref in interpretation.get("alternatives", [])],
                        "unknown_conditions": interpretation.get("unknown_conditions", []),
                    }
            converted.update(grounding_meaning="RECORDED_DERIVATION_ROOTS_ONLY",
                             actor_identity="SOURCE_LOCAL_NOT_GLOBAL_ENTITY", interpretation_executable=False)
        if kind == "SCOPED_EVIDENCE_RECEIPT":
            reasons.append("SCOPED_RECEIPT_IS_NOT_COMPLETE_CORE_OR_DOCUMENT_HISTORY")
        if kind == "INTERPRETATION_REVISION":
            refs = [payload.get("old"), payload.get("new"), *payload.get("reasons", ())]
            if any(ref not in record_mapping for ref in refs):
                reasons.append("INCOMPLETE_LEGACY_REFERENCES")
            else:
                converted.update(old=record_mapping[refs[0]], new=record_mapping[refs[1]],
                                 reasons=[record_mapping[ref] for ref in refs[2:]],
                                 kind="ANALYST_INTERPRETATION_REVISION_NOT_CHARACTER_CHANGE")
        if kind == "NARRATIVE_ORDER":
            converted.update(order_kind="EXPLICIT_STRICT_BEFORE", calendar_time_established=False,
                             scope="SOURCE_LOCAL", absent_relation="UNRESOLVED_NOT_FALSE")
        if kind == "REPORT_ASSESSMENT":
            converted.update(independent_support_count=None, independence="NOT_ESTABLISHED",
                             correlated_occurrences_are_not_independent=True)
        if kind == "ORDER_EVENT":
            converted.update(time_kind=payload.get("time_kind"), calendar_time_established=False,
                             actor_identity="SOURCE_LOCAL_NOT_GLOBAL_ENTITY")
            reasons.append("EVENT_TEXT_HAS_NO_EXACT_ORIGINAL_OFFSETS")
        migrated.append(dict(old_key=row["old_id"], new_id=record_mapping[row["old_id"]], kind=kind,
                             lifecycle=row["status"], disposition="QUARANTINED" if reasons else "MAPPED_TYPED_PROVENANCE",
                             reasons=reasons, converted=converted, recoverable_fields=sorted(payload), truth="NOT_ESTABLISHED"))
    return dict(schema="hcl-legacy-migration-1", namespace=namespace, original=original,
                source_mapping=source_mapping, record_mapping=record_mapping, records=migrated,
                current_sources=usable, semantics="LEGACY_SUPPORT_AND_REPORTS_ARE_NOT_TRUTH")
