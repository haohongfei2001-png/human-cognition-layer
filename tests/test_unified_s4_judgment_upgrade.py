"""Exact shipped 214-file main, real old executions and governed side-copy.

Project only hcl Python members from bc17f21. Never rewrite historical pins or
construct old ledgers by changing a current bundle. All content is synthetic.
"""
import inspect
from unittest.mock import patch

from hcl import HCL
from hcl.kernel.types import HCLFailure
from hcl.memory import codec
from hcl.memory.migrations.revision_upgrade import RevisionCutover, M14_PREDECESSOR_CODE_HASH
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.operators.local_model import LocalModelOperator
from hcl.runtime.recovery import RecoveryManager
from scripts import witness_unified_concepts as concepts
from tests import test_unified_s4_narrative_upgrade as previous

DOMAIN_PROGRAM = (
    "from hcl import ExecutionBudget,ExecutionIssue\n"
    "from hcl.semantics.segments import segment_snapshot\n"
    "from unittest.mock import patch\n"
    + inspect.getsource(concepts.propose)
    + r'''
class DomainCrash(BaseException):pass
domain_requests={}
domain_handles=(store.put_source(session,owner,'base',BASE),store.put_source(session,owner,'target',TARGET))
for domain in ('concept','narrative','argument'):
 for name,seam in [('completed',None),('returned','return_persisted'),('unknown','send_started'),('computed','execution_computed'),('committed','execution_effects_committed')]:
  key=domain+'-'+name
  request=TaskRequest(key,'Compare the explicitly declared conditional reading.',domain_handles,session,owner,
   budget=ExecutionBudget(max_mock_calls=1,max_feedback=0,max_local_evaluations=100000,max_request_bytes=1048576,max_context_tokens=1048576,max_output_bytes=1048576,max_total_output_bytes=8000000,max_visible_output_tokens=1048576),
   issue=ExecutionIssue('root',goals=(Issue(key,{'concept':'analogy.compare','narrative':'literature.analyze','argument':'argument.evaluate'}[domain]),)))
  snap=store.snapshot(session,owner,domain_handles)
  candidate=propose(snap,request.question)
  if domain=='narrative':
   candidate=dict(schema='hcl-literature-fragment-1',assumptions=[],active_assumptions=[],frames=[],events=[],mentions=[],orders=[],queries=[],motifs=[],variants=[],comparisons=[],analogies=[dict(id='reading',task=candidate)],unmodeled_segments=[])
  if domain=='argument':
   refs=[s.segment_id for s in segment_snapshot(snap,request.question) if s.kind=='SOURCE']
   candidate=dict(schema='hcl-argument-candidates-1',models=[dict(id='conditional',source_id='base',frame_kind='SOURCE_DISCOURSE',assumptions=[],active_assumptions=[],unmodeled_segments=[],
    literals=[dict(id='q',atom='source-report',negative=False,kind='CLAIM',segment_ids=refs)],
    premises=[dict(id='p',literal='q',ordinary=False,assumptions=[],segment_ids=refs)],rules=[],priorities=[],
    queries=[dict(id='query',literal='q',preferred=False,critical_candidates=[],segment_ids=refs)])])
  port=OfflineModelPort(json.dumps(candidate));client=HCL(store,principal=owner,gateway=ModelGateway(store,port));crashed=False
  def stop_domain(stage):
   global crashed
   if stage==seam and not crashed:crashed=True;raise DomainCrash()
  try:
   with patch.object(store,'_checkpoint',stop_domain):result=client.run_sync(request)
  except DomainCrash:pass
  expected='PARTIAL' if domain=='narrative' else 'COMPLETED'
  if seam:assert crashed,key
  else:assert result.status==expected,(key,result.diagnostics)
  domain_requests[key]=dict(request=codec.dumps(request).decode(),expected=expected,owner_id=store.owner_id)
'''
)
DOMAIN_PROGRAM = "BASE=" + repr(concepts.BASE) + "\nTARGET=" + repr(concepts.TARGET) + "\n" + DOMAIN_PROGRAM
INSERTION = "ledger=TaskBudgetLedger(store);snapshot=store.snapshot(session,owner,(handles['A'],))"
assert previous.OLD_PROGRAM.count(INSERTION) == 1
OLD_PROGRAM = previous.OLD_PROGRAM.replace(INSERTION, DOMAIN_PROGRAM + "\n" + INSERTION).replace(
    "salt=store._revision_control['governance_salt']", "domain_requests=domain_requests,salt=store._revision_control['governance_salt']")


class JudgmentPredecessorUpgradeTests(previous.GovernedNarrativeUpgradeTests):
    baseline = "bc17f21d9bd417a2dc319781079d284160109c72"
    code_hash = M14_PREDECESSOR_CODE_HASH
    file_count = 214

    def test_real_m11_m12_m13_checkpoint_family(self):
        f = self.fixture()
        f.old_program = OLD_PROGRAM
        for schema in (3, 4):
            source, old, process = f.old(schema, 'domains' + str(schema))
            store = RevisionCutover.upgrade(source, f.root / ('successor' + str(schema)), f.owner).open_store()
            self.addCleanup(store.close)
            for name, metadata in old['domain_requests'].items():
                with self.subTest(schema=schema, checkpoint=name):
                    request = codec.loads(metadata['request'].encode())
                    port = OfflineModelPort('NO_NEW_SEND')
                    client = HCL(store, principal=f.owner, gateway=ModelGateway(store, port))
                    if name.endswith('unknown'):
                        with self.assertRaises(HCLFailure) as caught:
                            RecoveryManager(store).resume_execution(request, expected_owner_id=metadata['owner_id'])
                        self.assertEqual(caught.exception.diagnostic.code, 'UNKNOWN_SEND_NO_RESUME')
                        result = client.run_sync(request)
                        self.assertIsNone(result.usage['mock_calls'])
                        self.assertEqual(result.usage['held_mock_calls'], 1)
                        self.assertFalse(result.answer or result.claim_records)
                    else:
                        cached = name.endswith('completed')
                        if cached:
                            task = store._db.execute('SELECT * FROM tasks WHERE request_id=?', (request.request_id,)).fetchone()
                            original = store._get_object(task['result_hash'])
                        else:
                            RecoveryManager(store).resume_execution(request, expected_owner_id=metadata['owner_id'])
                        if name.endswith('returned'):
                            result = client.run_sync(request)
                        else:
                            with patch.object(LocalModelOperator, 'run', side_effect=AssertionError('accepted effect cannot recompute')):
                                result = client.run_sync(request)
                        self.assertEqual(result.status, metadata['expected'], result.diagnostics)
                        self.assertEqual(result.usage['mock_calls'], 1)
                        if cached:
                            self.assertEqual((result.answer, result.claim_records), (original.answer, original.claim_records))
                            self.assertEqual(store._get_object(task['result_hash']), original)
                    self.assertEqual(port.attempts, 0)
            self.assertFalse(f.command(process, action='write')['ok'])
            store.set_readers(old['session'], f.owner, 'target', {'bob'})
            for metadata in old['domain_requests'].values():
                result = HCL(store, principal=f.owner).run_sync(codec.loads(metadata['request'].encode()))
                self.assertEqual(result.status, 'DENIED')
                self.assertFalse(result.answer or result.claim_records)
