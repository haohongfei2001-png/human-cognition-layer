"""Finite explicit adoption chains on the existing immutable inference log.

Only opaque semantic/support identities live in the adoption header. Original
source-bearing proofs are read after fresh per-support source authorization.
A lost latest support never silently resurrects an earlier adopted meaning.
"""
from dataclasses import asdict
from hashlib import sha256
import json

from hcl.kernel.types import HCLFailure, InferenceResult, freeze, thaw
from hcl.kernel.concept_registry import ConceptQuery, ConceptDependency, VERSION
from hcl.kernel.dependencies import unpack_dependencies
from hcl.memory import codec
from hcl.operators.concept_proof import pack_proof, unpack_proof
from hcl.semantics.concept_version_compiler import digest, host_context

ADOPTION = "CONCEPT_ADOPTION"
SUBSCRIPTION = "CONCEPT_SUBSCRIPTION"


def failure(code, status="INVALID_REQUEST"):
    return HCLFailure(status, "concept_registry", code, "concepts",
                      "The explicit concept adoption or local revision cannot use its bound evidence.")


def token(session_id, principal, stream):
    return digest([VERSION, session_id, asdict(principal), stream])


def prefix(session_id, principal, stream):
    return "concept-adoption:" + token(session_id, principal, stream) + ":"


def header_rows(store, db, session, principal, stream):
    start = prefix(session["session_id"], principal, stream)
    rows = list(db.execute("SELECT * FROM inferences WHERE session_id=? AND result_id>=? AND result_id<? ORDER BY commit_revision,result_id",
                          (session["session_id"], start, start + "~")))
    if len(rows) > 1024:
        raise failure("CONCEPT_ADOPTION_SCAN_BOUND", "BUDGET_EXHAUSTED")
    headers, previous = [], None
    for row in rows:
        # Header contracts contain hashes only, no original source content.
        value = store._get_object(row["object_hash"])
        if (type(value) is not InferenceResult or value.kind != ADOPTION
                or value.values["host_context"] != dict(session_id=session["session_id"], principal=asdict(principal))
                or value.values["stream_token"] != token(session["session_id"], principal, stream)
                or value.values["expected_head"] != previous or json.loads(row["read_set"])):
            raise failure("CONCEPT_CHAIN_CORRUPT", "FAILED")
        headers.append(value)
        previous = value.result_id
    return headers


def load_proof(store, db, session, principal, result_id):
    row = db.execute("SELECT * FROM inferences WHERE session_id=? AND result_id=?",
                     (session["session_id"], result_id)).fetchone()
    if row is None:
        raise failure("CONCEPT_PROOF_UNAVAILABLE", "NEEDS_EVIDENCE")
    positive, queries = unpack_dependencies(json.loads(row["read_set"]))
    if queries:
        raise failure("CONCEPT_BASE_REQUIRES_RECOMPILE", "NEEDS_RECOMPILE")
    # Rebind immutable source evidence at the current epoch. The old result's
    # epoch is never treated as current authority; each positive is read again.
    try:
        store._validate_dependencies(db, session, principal, positive, session["epoch"], session["rule"])
    except HCLFailure as error:
        if error.status == "STALE_STATE":
            raise failure("CONCEPT_SOURCE_REQUIRES_RECOMPILE", "NEEDS_RECOMPILE") from None
        raise
    result = store._get_object(row["object_hash"])
    if (type(result) is not InferenceResult or result.kind not in ("CONDITIONAL_CONCEPT_JUDGMENT", "CONDITIONAL_CONCEPT_REPAIR_JUDGMENT")
            or thaw(result.values["program"]["host_context"]) != dict(session_id=session["session_id"], principal=asdict(principal))
            or dict(result.values["source_versions"]) != positive or result.rule_version != session["rule"]):
        raise failure("CONCEPT_PROOF_NAMESPACE_MISMATCH", "DENIED")
    return result, positive


def definition(result, *, label=None, semantic_id=None, usability_hash=None):
    values = thaw(result.values)
    matches = [d for d in values["concepts"]["definitions"]
               if (label is None or d["id"] == label)
               and (semantic_id is None or d["definition_version"] == semantic_id)
               and (usability_hash is None or digest(d["withdrawn"]) == usability_hash)]
    if not matches:
        raise failure("CONCEPT_DEFINITION_MISSING")
    selected = sorted(matches, key=lambda d:d["id"])[0]
    if not values["complete"]:
        raise failure("CONCEPT_DEFINITION_FRONTIER", "NEEDS_EVIDENCE")
    return selected


def project(store, db, session, principal, query):
    body = dict(schema=VERSION, query=query.wire(), source_versions={}, origin_result_ids=[])
    if query.mode == "RESULT":
        proof, positive = load_proof(store, db, session, principal, query.key)
        body.update(status="AVAILABLE", proof=pack_proof(proof), source_versions=positive,
                    origin_result_ids=[proof.result_id])
    else:
        rows = header_rows(store, db, session, principal, query.key)
        eligible = [r for r in rows if r.values["effective_at"] <= query.at]
        if not eligible:
            body.update(status="NO_ADOPTED_VERSION", selection=None)
        else:
            latest = eligible[-1]
            errors, supports = [], []
            for result_id in latest.values["support_result_ids"]:
                try:
                    proof, positive = load_proof(store, db, session, principal, result_id)
                    d = definition(proof, semantic_id=latest.values["definition_version"],
                                   usability_hash=latest.values["usability_hash"])
                    if (d["concept_id"] != latest.values["concept_id"]
                            or d["semantic_definition"]["effective_at"] != latest.values["effective_at"]
                            or digest(d["withdrawn"]) != latest.values["usability_hash"]):
                        raise failure("CONCEPT_SUPPORT_MISMATCH", "FAILED")
                    supports.append((proof, positive, d))
                except HCLFailure as error:
                    if error.status not in ("DENIED", "NEEDS_RECOMPILE", "NEEDS_EVIDENCE"):
                        raise
                    errors.append(error.status)
            if not supports:
                # No proof content, source IDs or rejected-support counts escape.
                body.update(status="DENIED" if "DENIED" in errors else "NEEDS_RECOMPILE",
                            selection=None)
            else:
                # Retain only one complete currently authorized proof. Other
                # supports remain independently eligible on the next projection.
                proof, positive, d = sorted(supports, key=lambda s:s[0].result_id)[0]
                body.update(status="AVAILABLE", source_versions=positive, origin_result_ids=[proof.result_id],
                    selection=dict(adoption_id=latest.result_id, definition_version=d["definition_version"],
                        concept_id=d["concept_id"], proof=pack_proof(proof), version_label=d["id"], stream_id=query.key))
    dependency = ConceptDependency(query, sha256(codec.canonical(body).encode()).hexdigest())
    return dependency, freeze(body)


def adoption_value(store, db, session, principal, issue):
    from hcl.runtime.concept_answer import concept_judgment_claim
    values = []
    for identity, label in zip(issue.support_result_ids, issue.version_labels, strict=True):
        proof, _ = load_proof(store, db, session, principal, identity)
        concept_judgment_claim(proof)  # Exact original source/algorithm certificate.
        values.append(definition(proof, label=label))
    identity = values[0]
    if any((d["definition_version"],d["withdrawn"]) != (identity["definition_version"],identity["withdrawn"]) for d in values):
        raise failure("CONCEPT_SUPPORT_MEANINGS_DIFFER")
    prior = header_rows(store, db, session, principal, issue.stream_id)
    actual_head = prior[-1].result_id if prior else None
    if actual_head != issue.expected_head:
        raise failure("CONCEPT_ADOPTION_HEAD_CHANGED", "STALE_STATE")
    if prior and (prior[-1].values["concept_id"] != identity["concept_id"]
                  or prior[-1].values["frame_kind"] != identity["semantic_definition"]["frame_kind"]):
        raise failure("CONCEPT_ADOPTION_FAMILY_CHANGED")
    return dict(schema=VERSION, host_context=dict(session_id=session["session_id"],principal=asdict(principal)),
        stream_id=issue.stream_id, stream_token=token(session["session_id"], principal, issue.stream_id),
        expected_head=issue.expected_head, support_result_ids=sorted(issue.support_result_ids),
        definition_version=identity["definition_version"], concept_id=identity["concept_id"], usability_hash=digest(identity["withdrawn"]),
        effective_at=identity["semantic_definition"]["effective_at"], frame_kind=identity["semantic_definition"]["frame_kind"])


def validate_commit(store, db, session, delta, result):
    if result.kind == ADOPTION:
        # Recheck the exact caller-bound compare-and-adopt contract under the
        # writer transaction, rather than a stale precomputation or last-write.
        body = thaw(result.values)
        if set(body) != {"schema", "host_context", "stream_id", "stream_token", "expected_head", "support_result_ids", "definition_version", "concept_id", "usability_hash", "effective_at", "frame_kind"}:
            raise failure("CONCEPT_ADOPTION_FIELDS")
        supports = body["support_result_ids"]
        if (type(supports) is not list or not 1 <= len(supports) <= 8
                or any(type(key) is not str or not key for key in supports)
                or len(set(supports)) != len(supports)
                or result.assumption_environments or result.premise_ids or result.counterevidence_ids
                or result.coverage != "EXPLICIT_HOST_ADOPTION_NOT_GLOBAL_TRUTH"):
            raise failure("CONCEPT_ADOPTION_SUPPORT_CONTRACT")
        start = "concept-adoption:" + body["stream_token"] + ":"
        if (body["schema"] != VERSION or delta.read_set
                or body["host_context"] != dict(session_id=delta.session_id,principal=asdict(delta.principal))
                or body["stream_token"] != token(delta.session_id,delta.principal,body["stream_id"])
                or not result.result_id.startswith(start)
                or result.result_id != start + digest(body)):
            raise failure("CONCEPT_ADOPTION_IDENTITY")
        row = db.execute("SELECT result_id,object_hash FROM inferences WHERE session_id=? AND result_id>=? AND result_id<? ORDER BY commit_revision DESC,result_id DESC LIMIT 1",
                         (delta.session_id, start, start+"~")).fetchone()
        if (row["result_id"] if row else None) != body["expected_head"]:
            raise failure("CONCEPT_ADOPTION_HEAD_CHANGED", "STALE_STATE")
        if row:
            prior = store._get_object(row["object_hash"])
            if any(prior.values[k] != body[k] for k in ("concept_id", "frame_kind")):
                raise failure("CONCEPT_ADOPTION_FAMILY_CHANGED")
        for result_id in body["support_result_ids"]:
            proof, _ = load_proof(store, db, session, delta.principal, result_id)
            d = definition(proof, semantic_id=body["definition_version"], usability_hash=body["usability_hash"])
            if (d["concept_id"] != body["concept_id"] or d["semantic_definition"]["effective_at"] != body["effective_at"]
                    or digest(d["withdrawn"]) != body["usability_hash"]
                    or d["semantic_definition"]["frame_kind"] != body["frame_kind"]):
                raise failure("CONCEPT_SUPPORT_MISMATCH")
    elif result.kind == SUBSCRIPTION:
        body = thaw(result.values)
        if set(body) != {"schema", "host_context", "origin_request_id", "goal", "source_versions"}:
            raise failure("CONCEPT_SUBSCRIPTION_FIELDS")
        goal = codec.decode(body["goal"])
        from hcl.kernel.concept_registry import ConceptFollowIssue
        if (type(goal) is not ConceptFollowIssue or body["schema"] != VERSION
                or body["host_context"] != dict(session_id=delta.session_id,principal=asdict(delta.principal))):
            raise failure("CONCEPT_SUBSCRIPTION_NAMESPACE", "DENIED")
        proof, positive = load_proof(store, db, session, delta.principal, goal.base_result_id)
        if positive != dict(delta.read_set) or positive != body["source_versions"]:
            raise failure("CONCEPT_SUBSCRIPTION_SOURCE_MISMATCH")
        expected = subscription_ids(delta.session_id, delta.principal, body)
        if result.result_id not in expected:
            raise failure("CONCEPT_SUBSCRIPTION_IDENTITY")


def subscription_ids(session_id, principal, body):
    goal = codec.decode(body["goal"])
    return tuple("concept-use:" + token(session_id, principal, stream) + ":" + digest(body)
                 for stream in sorted({b.stream_id for b in goal.bindings}))


def consumers(store, session_id, principal, stream):
    """Bounded reverse index on opaque host-scoped identities, no full task scan."""
    start = "concept-use:" + token(session_id, principal, stream) + ":"
    with store._transaction() as db:
        session = store._session(db, session_id, principal)
        rows = list(db.execute("SELECT * FROM inferences WHERE session_id=? AND result_id>=? AND result_id<? ORDER BY result_id",
                               (session_id,start,start+"~")))
        if len(rows)>32:
            raise failure("CONCEPT_CONSUMER_FRONTIER", "BUDGET_EXHAUSTED")
        output = []
        for row in rows:
            positive, queries = unpack_dependencies(json.loads(row["read_set"]))
            # Metadata alone is insufficient to expose the stored task name.
            try:
                store._validate_dependencies(db,session,principal,positive,session["epoch"],session["rule"])
            except HCLFailure as error:
                output.append(dict(opaque_id=row["result_id"],status="DENIED" if error.status=="DENIED" else "NEEDS_RECOMPILE"))
                continue
            value = store._get_object(row["object_hash"])
            if value.kind != SUBSCRIPTION or queries or value.values["host_context"] != dict(session_id=session_id,principal=asdict(principal)):
                raise failure("CONCEPT_SUBSCRIPTION_CORRUPT", "FAILED")
            output.append(dict(opaque_id=row["result_id"],status="AVAILABLE",body=thaw(value.values)))
    return output


def authorize_delivery(store, session_id, principal, row):
    """Extra same-principal boundary for additive concept-owned state only."""
    # Native operators and runtime-wrapped successors have different valid IDs.
    # The structured additive kind owns this boundary, never an ID convention.
    result = store._get_object(row["object_hash"])
    if result.kind in ("CONDITIONAL_PERSISTENT_CONCEPT_JUDGMENT", "CONDITIONAL_PERSISTENT_CONCEPT_REPAIR_JUDGMENT"):
        base = unpack_proof(result.values["base_result"])
        host = base.values["program"]["host_context"]
    elif result.kind == "CONDITIONAL_CONCEPT_REPAIR_JUDGMENT":
        host = result.values["program"]["host_context"]
    elif result.kind in (ADOPTION,SUBSCRIPTION):
        host = result.values["host_context"]
    else:
        return  # Existing v1/v2 result contracts remain unchanged.
    if host != dict(session_id=session_id,principal=asdict(principal)):
        raise failure("CONCEPT_RESULT_NAMESPACE_DENIED","DENIED")
