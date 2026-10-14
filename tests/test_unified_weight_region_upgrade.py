"""Actual 233-file 0d025df runtime creates v4/v3 stores before this upgrade.

The predecessor independently computes minimum/tied/no-change/partial joint
certificates and every durable seam. Persistent-v3 uses the bounded three-
positive/two-negative fixture at all seams, retaining two real subscribers,
compressed proof bytes, adopted membership, CAS and old-writer fences.
"""
from contextlib import contextmanager
import inspect
import subprocess
import unittest
from unittest.mock import patch
from hcl.kernel.types import HCLFailure
from hcl.memory.migrations.revision_upgrade import RevisionCutover

from hcl.memory.migrations import revision_upgrade
from scripts import witness_unified_joint_changes as joint
from tests import test_unified_joint_change_upgrade as prior
from tests import test_unified_s23_upgrade as fixtures

BASELINE='0d025dfc733b72a7515c2516ee231ed04936453d'
BASELINE_TREE='0a38795bd7df646cdd3210bf8b8de55442171fbb'
BASELINE_CODE_HASH='ceb99bffedbc109a038973fae8258c8a202d52abbd30ab556902ce78e7b1d5fc'

# Only synthetic candidate generation crosses into the independent old process.
JOINT_PROPOSAL=inspect.getsource(joint.propose).replace('def propose(', 'def joint_propose(')
V4_PROPOSE=r'''
def v4_propose(snapshot, question):
    candidate = joint_propose(snapshot, question)
    spec = candidate['joint_changes']
    if MODE.endswith('ties'):
        argument = candidate['models'][0]['argument']
        premise = next(p for p in argument['premises'] if p['id'] == 'meeting')
        argument['rules'][-1]['premises'] = [premise['literal']]
        spec['edits'].append(dict(kind='PREMISE_RETRACT', source_id='scene', model_id='notice', argument_id='norms', item_id=premise['id'], segment_ids=premise['segment_ids']))
    elif MODE.endswith('nochange'):
        spec['edits'] = spec['edits'][:1]
    elif MODE.endswith('partial'):
        candidate['concepts']['cases'][0]['term'] = None
    return candidate
'''
OLD_PROGRAM=prior.OLD_PROGRAM.replace("root = Path(sys.argv[1])",JOINT_PROPOSAL+'\n'+V4_PROPOSE+'\nroot = Path(sys.argv[1])')
OLD_PROGRAM=OLD_PROGRAM.replace("'v3': repair_propose}","'v3': repair_propose, 'v4': v4_propose}")
OLD_PROGRAM=OLD_PROGRAM.replace("MODE in ('persistent-v3-computed', 'persistent-v3-committed')","MODE.startswith('persistent-v3-')")
OLD_PROGRAM=OLD_PROGRAM.replace("        capture_capsules(thaw(item.values))", """        if family == 'v4':
            assert item.kind == 'CONDITIONAL_JOINT_CHANGE_JUDGMENT'
            search = item.values['joint_search']
            if MODE.endswith('partial'):
                assert not search['complete'] and search['minimum_cardinality'] is None and not search['minimum_witnesses']
            elif MODE.endswith('nochange'):
                assert search['complete'] and search['status'] == 'NO_EXPRESSIBLE_CHANGE'
            else:
                assert search['complete'] and search['minimum_cardinality'] == 2
                assert len(search['minimum_witnesses']) == (2 if MODE.endswith('ties') else 1)
            assert search['adoption_authorized'] is False
        capture_capsules(thaw(item.values))""")


class WeightRegionPredecessorTests(unittest.TestCase):
    forbidden_result_fragment='WEIGHT_REGION'
    repair_profile_overrides={'persistent-v3-completed':'small'}
    rows=staticmethod(prior.JointChangePredecessorUpgradeTests.rows)
    fixture=prior.JointChangePredecessorUpgradeTests.fixture
    assert_inferences_unchanged=prior.JointChangePredecessorUpgradeTests.assert_inferences_unchanged
    assert_capsules_unchanged=prior.JointChangePredecessorUpgradeTests.assert_capsules_unchanged
    exercise_workload=prior.JointChangePredecessorUpgradeTests.exercise_workload

    @classmethod
    def setUpClass(cls):
        tree=subprocess.check_output(['git','rev-parse',BASELINE+'^{tree}'],cwd=fixtures.ROOT,text=True).strip()
        assert tree==BASELINE_TREE
        assert revision_upgrade.WEIGHT_REGION_PREDECESSOR_CODE_HASH==BASELINE_CODE_HASH
        class FrozenRuntime(fixtures.RuntimeUpgradeTests):
            baseline=BASELINE
            code_hash=BASELINE_CODE_HASH
            file_count=233
            old_program=OLD_PROGRAM
            def old(self,schema=3,name='old',*,mode='pins'):
                self.old_program='MODE = '+repr(mode)+'\n'+OLD_PROGRAM
                return super().old(schema,name)
        cls.runtime=FrozenRuntime;cls.runtime.setUpClass();cls.verified_capsule_wires=set()

    @classmethod
    def tearDownClass(cls):cls.runtime.tearDownClass()

    def test_actual_v4_min_ties_nochange_partial_every_checkpoint(self):
        for schema in (3,4):
            for mode in ('judgment-v4-min','judgment-v4-ties','judgment-v4-nochange','judgment-v4-partial'):
                with self.subTest(schema=schema,mode=mode),self.fixture() as fixture:
                    self.exercise_workload(fixture,schema,mode)

    def test_actual_v1_v2_v3_ordinary_checkpoints(self):
        for schema in (3,4):
            for dialect in ('v1','v2','v3'):
                with self.subTest(schema=schema,dialect=dialect),self.fixture() as fixture:
                    self.exercise_workload(fixture,schema,'judgment-'+dialect)

    def test_actual_v3_capsules_two_successors_completed_computed_committed(self):
        for schema in (3,4):
            for state in ('completed','computed','committed'):
                with self.subTest(schema=schema,state=state),self.fixture() as fixture:
                    self.exercise_workload(fixture,schema,'persistent-v3-'+state,erase=state=='completed')

    def test_cache_lifetime_and_all_phase_file_mutations(self):
        for stage in ('prepared','target_activated_unpublished','published'):
            for mutation in ('bytes','symlink','size'):
                with self.subTest(stage=stage,mutation=mutation),self.fixture() as fixture:
                    source,old,process=fixture.old(3,'cache-'+stage+'-'+mutation,mode='pins')
                    target=RevisionCutover(source,fixture.root/'target')
                    touched=[];caches=[];validate=revision_upgrade._HistoryDecodeCache.validate
                    def observe(cache,body):
                        if all(cache is not seen for seen in caches):caches.append(cache)
                        return validate(cache,body)
                    def change(actual):
                        if actual!=stage:return
                        root=(target.directory if stage=='published' else target.stage)/'state.sqlite.objects'
                        path=next(root.iterdir());body=path.read_bytes();touched.append((path,body))
                        if mutation=='bytes':path.write_bytes(body+b' ')
                        elif mutation=='size':path.write_bytes(b'0'*(4*1024*1024+1))
                        else:
                            other=fixture.root/'same-object';other.write_bytes(body);path.unlink();path.symlink_to(other)
                    with patch.object(revision_upgrade._HistoryDecodeCache,'validate',new=observe),patch.object(RevisionCutover,'_checkpoint',side_effect=change):
                        with self.assertRaises((ValueError,HCLFailure)):target._upgrade(fixture.owner)
                    self.assertTrue(touched);self.assertTrue(caches)
                    self.assertTrue(all(not cache._validated and cache._size==0 for cache in caches))
                    for path,body in touched:
                        if not path.parent.exists():path=target.directory/'state.sqlite.objects'/path.name
                        if path.is_symlink():path.unlink()
                        path.write_bytes(body)
                    old_caches=list(caches)
                    with patch.object(revision_upgrade._HistoryDecodeCache,'validate',new=observe):target._upgrade(fixture.owner)
                    self.assertGreater(len(caches),len(old_caches))
                    self.assertTrue(all(not cache._validated for cache in caches))
                    self.assertFalse(fixture.command(process,action='snapshot')['ok'])
                    self.assertFalse(fixture.command(process,action='write')['ok'])

    def test_exact_pin_rejects_hash_indexes_governance_split_controls(self):
        prior.JointChangePredecessorUpgradeTests.test_exact_pin_rejects_changed_hash_indexes_governance_and_split_controls(self)


if __name__=='__main__':unittest.main()
