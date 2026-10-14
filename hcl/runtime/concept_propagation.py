"""Concept-specific bindings and discovery for the existing execution graph.

No scheduler, provider call, separate task budget or mutable answer cache lives
here. The runner performs every resulting node through its usual checkpoint,
reservation, commit and fresh-delivery gates.
"""
from dataclasses import asdict, replace
import json

from hcl.kernel.concept_registry import ConceptAdoptionIssue, ConceptFollowIssue, ConceptQuery, VERSION
from hcl.kernel.dependencies import QueryDelta, pack_dependencies
from hcl.kernel.types import Delta, InferenceResult, OpResult, SourceHandle, thaw
from hcl.memory import codec
from hcl.memory import concept_registry as registry
from hcl.semantics.concept_version_compiler import digest, host_context

KINDS = ("concept.adopt", "judgment.follow_concepts")


def follow_snapshot(runner, request, goal):
    store = runner.store
    first = store.query_snapshot(request.session_id, request.principal, (), (ConceptQuery("RESULT", goal.base_result_id),))
    proof = codec.decode(thaw(first.query_views["0"]["proof"]))
    concepts = proof.values["program"]["concepts"]
    choices = {c["id"]:c for c in concepts["choices"]}
    queries = [ConceptQuery("RESULT", goal.base_result_id)]
    for binding in goal.bindings:
        uses = [u for u in concepts["uses"] if u["selector"]["kind"] == "CHOICE" and u["selector"]["id"] == binding.choice_id]
        if binding.choice_id not in choices or not uses or any(u["commitment"] is not None for u in uses):
            raise registry.failure("CONCEPT_FOLLOW_CHOICE_INVALID")
        queries.append(ConceptQuery("SELECTION", binding.stream_id, min(u["at"] for u in uses)))
    selected = store.query_snapshot(request.session_id, request.principal, (), tuple(queries))
    positive = {}
    for view in selected.query_views.values():
        if view["status"] != "AVAILABLE":
            status = view["status"]
            raise registry.failure("CONCEPT_SELECTION_"+status, "DENIED" if status == "DENIED" else "NEEDS_RECOMPILE")
        for key, version in view["source_versions"].items():
            if key in positive and positive[key] != version:
                raise registry.failure("CONCEPT_EVIDENCE_VERSION_CONFLICT", "NEEDS_RECOMPILE")
            positive[key] = version
    # Exact data/query/read-set capture in one WAL view, then fresh validation.
    return store.query_snapshot(request.session_id,request.principal,
                                tuple(SourceHandle(k,v) for k,v in sorted(positive.items())),tuple(queries))


def subscription_body(request, goal, snapshot):
    return dict(schema=VERSION,host_context=host_context(snapshot),origin_request_id=request.request_id,
                goal=codec.encode(goal),source_versions=thaw(snapshot.query_views["0"]["source_versions"]))


def subscribe(runner, request, node):
    snapshot = runner.snapshots[node["goal"].issue_id]
    body = subscription_body(request,node["goal"],snapshot)
    source_versions = body["source_versions"]
    result_ids = registry.subscription_ids(request.session_id,request.principal,body)
    results = tuple(InferenceResult(key,registry.SUBSCRIPTION,body,(),tuple(sorted(source_versions)),(),
                                  snapshot.rule_version,"EXPLICIT_HOST_FOLLOW_RELATION") for key in result_ids)
    delta = Delta(snapshot.session_id,snapshot.principal,snapshot.revision,snapshot.access_epoch,
                  snapshot.rule_version,source_versions,results)
    operation = OpResult("concept.subscribe",VERSION,source_versions,("append_inference",),result_ids,(),
                         dict(local_evaluations=0),(),delta)
    # Registration is part of the same single commit/recovery mechanism.
    runner._commit(operation)
    runner.nodes[node["goal"].issue_id+":compute"]["subscription"] = body


def successor_prefix(body):
    return "concept-successor:" + digest(body) + ":"


def adopt_operation(runner, request, goal, snapshot):
    with runner.store._transaction() as db:
        session = runner.store._session(db,request.session_id,request.principal)
        body = registry.adoption_value(runner.store,db,session,request.principal,goal)
    result_id = registry.prefix(request.session_id,request.principal,goal.stream_id)+digest(body)
    value = InferenceResult(result_id,registry.ADOPTION,body,(),(),(),snapshot.rule_version,
                            "EXPLICIT_HOST_ADOPTION_NOT_GLOBAL_TRUTH")
    return OpResult("concept.adopt",VERSION,{},("append_inference",),(result_id,),(),dict(local_evaluations=1),(),
                    Delta(snapshot.session_id,snapshot.principal,snapshot.revision,snapshot.access_epoch,
                          snapshot.rule_version,{},(value,)))


def follow_operation(runner, request, node, snapshot, allowance):
    from hcl.operators.persistent_concepts import compute_persistent
    base = codec.decode(thaw(snapshot.query_views["0"]["proof"]))
    selections = []
    for number,binding in enumerate(node["goal"].bindings,1):
        selection = thaw(snapshot.query_views[str(number)]["selection"])
        selection.pop("concept_id")
        selections.append(dict(selection,choice_id=binding.choice_id))
    operation = compute_persistent(snapshot,node["goal"],allowance,base,tuple(selections))
    body = node["subscription"]
    context = [pack_dependencies(operation.read_set,snapshot.query_dependencies),snapshot.access_epoch,snapshot.rule_version]
    results = tuple(replace(result,result_id=successor_prefix(body)+digest([result.result_id,context]))
                    for result in operation.candidate_delta.new_inferences)
    delta = QueryDelta(snapshot.session_id,snapshot.principal,snapshot.revision,snapshot.access_epoch,
                       snapshot.rule_version,operation.read_set,results,snapshot.query_dependencies)
    return replace(operation,result_refs=tuple(r.result_id for r in results),candidate_delta=delta)


def discover(runner, request):
    changed = False
    for node in tuple(runner.nodes.values()):
        if (node["operation"] != "compute" or node["state"] != "DONE" or node["goal"].kind != "concept.adopt"
                or node.get("propagation_discovered")):
            continue
        rows = registry.consumers(runner.store,request.session_id,request.principal,node["goal"].stream_id)
        for row in rows:
            if row["status"] != "AVAILABLE":
                runner.trace.append(dict(event="UNRESOLVED",goal=node["goal"].issue_id,code="CONCEPT_CONSUMER_"+row["status"]))
                continue
            body = row["body"]
            identity = "concept-revision:"+digest(body)
            if identity+":compute" in runner.nodes:
                continue
            original = codec.decode(body["goal"])
            goal = replace(original,issue_id=identity)
            try:
                snapshot = follow_snapshot(runner,request,goal)
            except Exception as error:
                from hcl.kernel.types import HCLFailure
                if not isinstance(error,HCLFailure):
                    raise
                if error.status not in ("NEEDS_RECOMPILE","DENIED","NEEDS_EVIDENCE"):
                    raise
                runner.trace.append(dict(event="UNRESOLVED",goal=node["goal"].issue_id,code="CONCEPT_CONSUMER_"+error.status))
                continue
            start = successor_prefix(body)
            with runner.store._transaction() as db:
                prior = db.execute("SELECT * FROM inferences WHERE session_id=? AND result_id>=? AND result_id<? ORDER BY commit_revision DESC,result_id DESC LIMIT 1",
                                  (request.session_id,start,start+"~")).fetchone()
                if (prior is not None and prior["epoch"] == snapshot.access_epoch
                        and json.loads(prior["read_set"]) == pack_dependencies(snapshot.source_versions,snapshot.query_dependencies)):
                    # Future/no-op stream changes and unrelated writes do not
                    # run M12/M13/M14 again merely because discovery found them.
                    runner.trace.append(dict(event="CONCEPT_CONSUMER_RETAINED",consumer=digest(body)))
                    continue
            nodes = runner.planner.expand((goal,))
            subscribe_id = identity+":subscribe"
            nodes.pop(subscribe_id)
            compute = nodes[identity+":compute"]
            compute.update(requires=(),subscription=body)
            runner.nodes.update(nodes)
            runner.snapshots[identity] = snapshot
            runner.trace.append(dict(event="CONCEPT_SUCCESSOR_SCHEDULED",consumer=digest(body),
                                     original_request_id=body["origin_request_id"],revision_request_id=request.request_id,
                                     goal=identity,reason="QUERY_DEPENDENCY_CHANGED"))
            changed = True
        node["propagation_discovered"] = True
        changed = True
    return changed
