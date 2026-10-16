"""Real shipped v5 processes: unchanged certificates and all durable seams."""
import inspect
import subprocess
import unittest
from hcl.memory.migrations import revision_upgrade
from scripts import witness_unified_weight_regions as weight
from tests import test_unified_weight_region_upgrade as prior
from tests import test_unified_joint_change_upgrade as helpers
from tests import test_unified_s23_upgrade as fixtures

BASELINE='2de21ad204ebd834f59bf50cdfe7013809189fbf'
BASELINE_TREE='22117484a5e4185ea422d69cbf61ab531a2db314'
BASELINE_CODE_HASH='6a054db8ccab4ac05a0b2353ab57b7656e58e3420fed051eb6f45acddb2db7b7'
PROPOSAL=inspect.getsource(weight.propose).replace('def propose(', 'def weight_propose(')
PROPOSAL+='''
def v5_propose(snapshot, question):
    candidate = weight_propose(snapshot, question)
    if MODE.endswith('maximin'):
        candidate['weight_domains'][0]['decision_rule'] = 'MAXIMIN'
    return candidate
'''
OLD_PROGRAM=prior.OLD_PROGRAM.replace('root = Path(sys.argv[1])', PROPOSAL+'\nroot = Path(sys.argv[1])')
OLD_PROGRAM=OLD_PROGRAM.replace("'v4': v4_propose}", "'v4': v4_propose, 'v5': v5_propose}")


class RegretPredecessorTests(unittest.TestCase):
    forbidden_result_fragment='UNAUTHORIZED_REGRET_RESULT'
    rows=staticmethod(helpers.JointChangePredecessorUpgradeTests.rows)
    fixture=helpers.JointChangePredecessorUpgradeTests.fixture
    assert_inferences_unchanged=helpers.JointChangePredecessorUpgradeTests.assert_inferences_unchanged
    assert_capsules_unchanged=helpers.JointChangePredecessorUpgradeTests.assert_capsules_unchanged
    exercise_workload=helpers.JointChangePredecessorUpgradeTests.exercise_workload

    @classmethod
    def setUpClass(cls):
        assert subprocess.check_output(['git','rev-parse',BASELINE+'^{tree}'],cwd=fixtures.ROOT,text=True).strip()==BASELINE_TREE
        assert revision_upgrade.MINIMAX_REGRET_PREDECESSOR_CODE_HASH==BASELINE_CODE_HASH
        class FrozenRuntime(fixtures.RuntimeUpgradeTests):
            baseline=BASELINE
            code_hash=BASELINE_CODE_HASH
            file_count=237
            old_program=OLD_PROGRAM
            def old(self,schema=3,name='old',*,mode='pins'):
                self.old_program='MODE = '+repr(mode)+'\n'+OLD_PROGRAM
                return super().old(schema,name)
        cls.runtime=FrozenRuntime;cls.runtime.setUpClass();cls.verified_capsule_wires=set()

    @classmethod
    def tearDownClass(cls):cls.runtime.tearDownClass()

    def test_shipped_expected_and_maximin_every_checkpoint_both_schemas(self):
        for schema in (3,4):
            for mode in ('judgment-v5-expected','judgment-v5-maximin'):
                with self.subTest(schema=schema,mode=mode),self.fixture() as fixture:
                    self.exercise_workload(fixture,schema,mode)


if __name__=='__main__':unittest.main()
