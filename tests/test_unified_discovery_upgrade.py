"""Current qualifications over immutable real pre-fix M04 stores/checkpoints."""

import asyncio
from unittest.mock import patch
from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.migrations.revision_upgrade import (
    RevisionCutover,
    M04_DISCOVERY_CODE_HASH,
)
from hcl.models.gateway import OfflineModelPort, ModelGateway
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.recovery import RecoveryManager
from tests import test_unified_s3_discovery_upgrade as previous

DISCOVERY_PROGRAM = r"""
from copy import deepcopy
discovery_requests={}
d_saved_request=request
if schema in (3,4):
 d_handle=store.put_source(session,owner,'discovery-source','Report a supports b. Another report opposes b.')
 d_question='Which proposed mechanism fits the reports?'
 d_segments=segment_snapshot(store.snapshot(session,owner,(d_handle,)),d_question)
 d_sources=[s.segment_id for s in d_segments if s.kind=='SOURCE'];d_queries=[s.segment_id for s in d_segments if s.kind=='QUESTION']
 def d_template(kind):
  literals=[dict(id=k,atom=('b' if k=='not-b' else k),negative=k=='not-b',kind='CLAIM',segment_ids=d_sources) for k in ('a','b','not-b')]
  model=dict(id='argument',source_id='discovery-source',frame_kind='HYPOTHETICAL',assumptions=[],active_assumptions=[],unmodeled_segments=[],literals=literals,
   premises=[dict(id='report',literal='a',ordinary=False,assumptions=[],segment_ids=d_sources),dict(id='denial',literal='not-b',ordinary=kind!='strict',assumptions=[],segment_ids=d_sources)],
   rules=[dict(id='inference',premises=['a'],conclusion='b',strict=kind=='strict',assumptions=[],segment_ids=d_sources)],priorities=[],
   queries=[dict(id='b-query',literal='b',preferred=False,critical_candidates=[],segment_ids=d_queries)])
  if kind=='cycle':model['rules'].append(dict(id='circular-rule',premises=['b'],conclusion='a',strict=True,assumptions=[],segment_ids=d_sources))
  return dict(schema='hcl-argument-candidates-1',models=[model])
 for d_kind in ('cycle','strict'):
  for d_location in ('observed','probe'):
   context=dict(id='observed',adapter='argument-model-1',template=d_template(d_kind if d_location=='observed' else 'plain'),features={},feature_segments={},segment_ids=d_sources)
   probe=deepcopy(context);probe.update(id='future',template=d_template(d_kind))
   candidate=dict(schema='hcl-discovery-candidates-1',contexts=[context],observations=[dict(id='report',context_id='observed',query_id='q',values=[dict(positive=True,opposed=False)],factor_id='factor',provenance_group='source',derived_from=[],segment_ids=d_sources)],
    probes=[] if d_location=='observed' else [dict(id='probe',context=probe,query_id='q',segment_ids=d_sources)],
    programs=[dict(id='fixed',adapter='argument-model-1',latent={},observe=[],transition=[],constraint=[],predict=[dict(id='q',field='argument.acceptance',record_id='b-query')])],
    grammar=dict(observation_features=[],latent_domains={},max_expression_size=128),search=dict(max_rounds=0,beam=12,new_per_round=4,max_candidates=64),unmodeled_segments=[])
   for d_phase,d_seam in [('completed',None),('returned','return_persisted'),('computed','execution_computed'),('committed','execution_effects_committed'),('unknown','send_started')]:
    d_name='-'.join((d_kind,d_location,d_phase))
    request=TaskRequest('discovery-'+d_name,d_question,(d_handle,),session,owner,budget=ExecutionBudget(max_mock_calls=4,max_request_bytes=1048576,max_context_tokens=1048576,max_local_evaluations=4096,max_output_bytes=1048576,max_total_output_bytes=16777216,max_visible_output_tokens=1048576),issue=ExecutionIssue('root',goals=(Issue('discovery-'+d_name,'hypothesis.discover'),)))
    port=OfflineModelPort(json.dumps(candidate));client=HCL(store,principal=owner,gateway=ModelGateway(store,port));d_crashed=False
    def stop_discovery(stage):
     global d_crashed
     if stage==d_seam and not d_crashed:d_crashed=True;raise GraphCrash()
    try:
     with patch.object(store,'_checkpoint',stop_discovery):result=client.run_sync(request)
    except GraphCrash:pass
    if d_seam:assert d_crashed,d_name
    else:assert result.status=='COMPLETED',(d_name,result.status,result.diagnostics)
    discovery_requests[d_name]=dict(request=codec.dumps(request).decode(),attempts=port.attempts)
    if d_phase=='completed':
     for d_cap in ('output',):
      cap_size=len(codec.dumps(result))+128
      cap_budget=replace(request.budget,max_output_bytes=max(cap_size,len(json.dumps(candidate).encode())+128))
      cap_name=d_kind+'-'+d_location+'-capacity-'+d_cap
      cap_request=replace(request,request_id='discovery-'+cap_name,budget=cap_budget,issue=ExecutionIssue('root',goals=(Issue('discovery-'+cap_name,'hypothesis.discover'),)))
      cap_port=OfflineModelPort(json.dumps(candidate));cap_result=HCL(store,principal=owner,gateway=ModelGateway(store,cap_port)).run_sync(cap_request)
      assert cap_result.status=='COMPLETED',(cap_name,cap_result.status,cap_result.diagnostics)
      discovery_requests[cap_name]=dict(request=codec.dumps(cap_request).decode(),attempts=cap_port.attempts)

request=d_saved_request
"""
assert previous.OLD_PROGRAM.count(previous.INSERTION) == 1
OLD_PROGRAM = previous.OLD_PROGRAM.replace(
    previous.INSERTION, DISCOVERY_PROGRAM + "\n" + previous.INSERTION
).replace(
    "'argument_requests':argument_requests",
    "'argument_requests':argument_requests,'discovery_requests':discovery_requests",
)


class M04RuntimeUpgradeTests(previous.S4RuntimeUpgradeTests):
    baseline = "e5f70bbb2afcfef665c6e9d7a7d3da2bb612cc83"
    code_hash = M04_DISCOVERY_CODE_HASH
    file_count = 179

    def test_old_completed_and_checkpoints_receive_current_scoped_qualifications(self):
        self.old_program = OLD_PROGRAM
        for schema in (3, 4):
            with self.subTest(schema=schema):
                source, old, process = self.old(schema, str(schema))
                store = RevisionCutover.upgrade(
                    source, self.root / ("new" + str(schema)), self.owner
                ).open_store()
                original_objects = {
                    p.name: p.read_bytes()
                    for p in source.with_name(source.name + ".objects").iterdir()
                }
                try:
                    for name, metadata in old["discovery_requests"].items():
                        with self.subTest(name=name):
                            request = codec.loads(metadata["request"].encode())
                            port = OfflineModelPort("NEVER_SEND")
                            client = HCL(
                                store,
                                principal=self.owner,
                                gateway=ModelGateway(store, port),
                            )
                            if "-capacity-" in name:
                                result = client.run_sync(request)
                                self.assertEqual(
                                    result.status,
                                    "BUDGET_EXHAUSTED",
                                    result.diagnostics,
                                )
                                self.assertEqual(
                                    result.diagnostics[0].code, "DELIVERY_CAPACITY"
                                )
                                self.assertEqual(result.usage["mock_calls"], 1)
                                self.assertEqual(
                                    result.usage["replay_new_mock_calls"], 0
                                )
                                self.assertFalse(result.answer)
                                self.assertFalse(result.claim_records)
                                self.assertEqual(port.attempts, 0)
                                task = store._db.execute(
                                    "SELECT * FROM tasks WHERE request_id=?",
                                    (request.request_id,),
                                ).fetchone()
                                self.assertEqual(
                                    store._get_object(task["result_hash"]).status,
                                    "COMPLETED",
                                )
                                continue
                            if name.endswith("unknown"):
                                with self.assertRaises(HCLFailure) as caught:
                                    RecoveryManager(store).resume_execution(
                                        request, expected_owner_id=old["owner_id"]
                                    )
                                self.assertEqual(
                                    caught.exception.diagnostic.code,
                                    "UNKNOWN_SEND_NO_RESUME",
                                )
                                result = client.run_sync(request)
                                self.assertIsNone(result.usage["mock_calls"])
                                self.assertEqual(result.usage["held_mock_calls"], 1)
                                self.assertFalse(result.answer)
                                continue
                            if not name.endswith("completed"):
                                RecoveryManager(store).resume_execution(
                                    request, expected_owner_id=old["owner_id"]
                                )

                            async def streamed():
                                return [event async for event in client.stream(request)]

                            def run():
                                return (
                                    asyncio.run(streamed())[-1].result
                                    if "probe" in name
                                    else client.run_sync(request)
                                )

                            if name.endswith(("computed", "committed", "completed")):
                                with patch.object(
                                    LocalModelOperator,
                                    "run",
                                    side_effect=AssertionError("no recomputation"),
                                ):
                                    result = run()
                            else:
                                result = run()
                            code = (
                                "CYCLIC_PROOF_FRAGMENT_EXCLUDED"
                                if name.startswith("cycle")
                                else "INCONSISTENT_STRICT_CORE"
                            )
                            self.assertEqual(
                                result.status, "PARTIAL", result.diagnostics
                            )
                            self.assertIn(code, result.answer)
                            self.assertIn(code, str(result.claim_records))
                            self.assertIn(code, result.unresolved_issues)
                            self.assertEqual(result.usage["mock_calls"], 1)
                            self.assertEqual(port.attempts, 0)
                            if name.endswith("completed"):
                                self.assertTrue(result.execution_receipt["replayed"])
                                self.assertEqual(
                                    result.execution_receipt[
                                        "discovery_delivery_qualification"
                                    ],
                                    "SCOPED_DOMAIN_LIMITATIONS_V1",
                                )
                                task = store._db.execute(
                                    "SELECT * FROM tasks WHERE request_id=?",
                                    (request.request_id,),
                                ).fetchone()
                                historic = store._get_object(task["result_hash"])
                                self.assertEqual(historic.status, "COMPLETED")
                                self.assertNotIn(code, historic.answer)
                    for digest, body in original_objects.items():
                        self.assertEqual(
                            (store.object_root / digest).read_bytes(), body
                        )
                    self.assertFalse(self.command(process, action="write")["ok"])
                    from hcl.memory.store import StateStore
                    from hcl.kernel.types import InferenceResult

                    path = store.path
                    store.close()
                    store = StateStore.sqlite(path, revision=True)
                    peer = StateStore.sqlite(path, revision=True)
                    try:
                        for key in (
                            "cycle-observed-completed",
                            "strict-probe-completed",
                        ):
                            request = codec.loads(
                                old["discovery_requests"][key]["request"].encode()
                            )
                            result = HCL(store, principal=self.owner).run_sync(request)
                            self.assertEqual(result.status, "PARTIAL")
                            self.assertEqual(result.usage["mock_calls"], 1)
                        request = codec.loads(
                            old["discovery_requests"]["cycle-probe-completed"][
                                "request"
                            ].encode()
                        )
                        original = store._get_object
                        revoked = []

                        def revoke_during_historical_inference_read(digest):
                            value = original(digest)
                            if (
                                type(value) is InferenceResult
                                and value.kind == "CONDITIONAL_MECHANISM_DISCOVERY"
                                and not revoked
                            ):
                                peer.set_readers(
                                    old["session"],
                                    self.owner,
                                    "discovery-source",
                                    {"bob"},
                                )
                                revoked.append(True)
                            return value

                        with patch.object(
                            store,
                            "_get_object",
                            revoke_during_historical_inference_read,
                        ):
                            client = HCL(store, principal=self.owner)

                            async def stream_revoked():
                                return [event async for event in client.stream(request)]

                            denied = (
                                client.run_sync(request)
                                if schema == 3
                                else asyncio.run(stream_revoked())[-1].result
                            )
                        self.assertTrue(revoked)
                        self.assertEqual(denied.status, "DENIED")
                        self.assertFalse(denied.answer)
                        self.assertFalse(denied.claim_records)
                        self.assertNotIn(
                            "discovery-source", str(denied.execution_receipt)
                        )
                        self.assertEqual(denied.usage["mock_calls"], 1)
                    finally:
                        peer.close()
                    # Current delivery ACL must still take precedence over old cached content.
                    request = codec.loads(
                        old["discovery_requests"]["cycle-probe-completed"][
                            "request"
                        ].encode()
                    )
                    store.set_readers(
                        old["session"], self.owner, "discovery-source", {"bob"}
                    )
                    denied = HCL(store, principal=self.owner).run_sync(request)
                    self.assertEqual(denied.status, "DENIED")
                    self.assertFalse(denied.answer)
                    self.assertFalse(denied.claim_records)
                finally:
                    store.close()
