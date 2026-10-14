"""Typed retained-content lineage, distinct from minimal delivery dependencies.

This module does not delete content or infer provenance from text similarity.
The caller supplies the session for contracts without their own session field.
Unknown old provenance needs an explicit scoped conservative migration policy;
an empty set here is never an authorization or proof of content independence.
"""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from hashlib import sha256
import hmac

from hcl.kernel.dependencies import QuerySnapshot
from hcl.kernel.execution import LocalModel
from hcl.kernel.scope import identifier, version_map
from hcl.kernel.types import Delta, Snapshot, SourceDocument, TaskRequest
from hcl.memory import codec

PROTOCOL = "hcl-retained-content-lineage-1"


def binding(session_id, source_id, version):
    identifier(session_id)
    version_map({source_id: version})
    return session_id, source_id, version


def projection_bindings(session_id, projection):
    """Bindings of bytes in an actual host-produced query projection.

    Retrieval corpus statistics depend on the complete search scope, not just
    selected hits. Revision views retain matches/pending/history; callers also
    record the authenticated scan scope at write time where it is broader.
    """
    from hcl.kernel.retrieval import RETRIEVAL_VERSION
    result = set()
    from hcl.kernel.concept_registry import VERSION as CONCEPT_VERSION
    if projection.get("schema") == CONCEPT_VERSION:
        result.update(binding(session_id, source, version) for source, version in projection["source_versions"].items())
    elif projection.get("schema") == RETRIEVAL_VERSION:
        for source_id, row in projection["search_scope"].items():
            result.add(binding(session_id, source_id, row["version"]))
    else:
        for row in projection.get("matches", ()):
            result.add(binding(session_id, row["source_id"], row["source_version"]))
        for source_id, version, _ in projection.get("pending", ()):
            result.add(binding(session_id, source_id, version))
        for row in projection.get("source_history", ()):
            result.add(binding(session_id, row["source_id"], row["source_version"]))
    return frozenset(result)


def retained_bindings(value, *, session_id, origin_refs=None):
    """Walk all typed checkpoint branches, including failed and unused ones.

    No ordinary mapping key, source-looking string or natural-language phrase
    creates a source binding. Only known contracts and host query views do so.
    Node budget also bounds adversarially large synthetic contract containers.
    """
    identifier(session_id)
    result, seen, work = set(), set(), 0

    def visit(item, session):
        nonlocal work
        if item is None or type(item) in (str, bool, int, float):
            return
        key = (id(item), session)
        if key in seen:
            return
        seen.add(key)
        work += 1
        if work > 131072:
            raise ValueError("retained-content lineage traversal bound")
        if isinstance(item, Snapshot):
            session = item.session_id
            result.update(binding(session, source, version) for source, version in item.source_versions.items())
            if type(item) is QuerySnapshot:
                if origin_refs is not None:
                    origin_refs.update((session, result_id) for dependency in item.query_dependencies
                                       for result_id in getattr(dependency.query, "evidence_result_ids", ()))
                for row in item.historical_sources.values():
                    result.add(binding(session, row["source_id"], row["source_version"]))
                for view in item.query_views.values():
                    if origin_refs is not None:
                        origin_refs.update((session, identity) for identity in view.get("origin_result_ids", ()))
                    result.update(projection_bindings(session, view))
        elif isinstance(item, Delta):
            session = item.session_id
            result.update(binding(session, source, version) for source, version in item.read_set.items())
            if origin_refs is not None:
                origin_refs.update((session, result_id) for dependency in getattr(item, "query_dependencies", ())
                                   for result_id in getattr(dependency.query, "evidence_result_ids", ()))
        elif type(item).__name__ == "ConceptAdoptionIssue":
            from hcl.kernel.concept_registry import ConceptAdoptionIssue
            if type(item) is ConceptAdoptionIssue and origin_refs is not None:
                origin_refs.update((session, identity) for identity in item.support_result_ids)
        elif type(item).__name__ == "ConceptFollowIssue":
            from hcl.kernel.concept_registry import ConceptFollowIssue
            if type(item) is ConceptFollowIssue and origin_refs is not None:
                origin_refs.add((session, item.base_result_id))
        elif type(item) is TaskRequest:
            session = item.session_id
            result.update(binding(session, handle.source_id, handle.version) for handle in item.source_handles)
        elif type(item) is SourceDocument:
            result.add(binding(session, item.handle.source_id, item.handle.version))
        elif type(item) is LocalModel:
            result.update(binding(session, source, version) for source, version in item.source_versions.items())
        if is_dataclass(item):
            for field in fields(item):
                visit(getattr(item, field.name), session)
        elif isinstance(item, Mapping):
            for child in item.values():
                visit(child, session)
        elif type(item) in (tuple, list, frozenset):
            for child in item:
                visit(child, session)
        else:
            raise ValueError("unrecognized retained-content contract")

    visit(value, session_id)
    return frozenset(result)


def source_token(salt, session_id, source_id):
    """Opaque source-identity tombstone key; never keep free-form IDs in audit."""
    if type(salt) is not bytes or len(salt) != 32:
        raise ValueError("exact namespace governance salt required")
    identifier(session_id)
    identifier(source_id)
    return hmac.new(salt, codec.canonical([PROTOCOL, session_id, source_id]).encode(), sha256).hexdigest()


def encoded_bindings(salt, bindings):
    normalized = (binding(*item) for item in bindings)
    return tuple(sorted({(session, source_token(salt, session, source), version)
                         for session, source, version in normalized}))
