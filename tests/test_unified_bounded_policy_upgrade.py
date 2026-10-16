"""Real shipped single-step judgments survive the opt-in policy increment.

Project only the exact 237 runtime Python files from PR446, never predecessor
fixtures, tests, evaluation data or current implementation. Each independent old
process persists completed, returned, unknown, computed and committed tasks.
The shared cutover harness checks immutable proof/claim bytes, no provider
resends, reconstruction, governance, old-writer fencing and revoked-read access.
"""
import subprocess
import unittest

from hcl.memory.migrations import revision_upgrade
from tests import test_unified_minimax_regret_upgrade as prior
from tests import test_unified_joint_change_upgrade as helpers
from tests import test_unified_s23_upgrade as fixtures

BASELINE = '0405d78473f6774b7288992293d03faf282b6022'
BASELINE_TREE = 'c093324bd234f1e79b8de22d882f947bf9c9afb5'
BASELINE_CODE_HASH = '2b901ca9772698c1106d7f8e06442ef0e25b61a89c1a5e5c60cdf6dc849754da'

# Only synthetic candidate generation is supplied to the independent old process.
OLD_PROGRAM = prior.OLD_PROGRAM.replace(
    "    return candidate\n\nroot = Path(sys.argv[1])",
    "    if MODE.endswith('regret'):\n"
    "        candidate['weight_domains'][0]['decision_rule'] = 'MINIMAX_REGRET'\n"
    "    return candidate\n\nroot = Path(sys.argv[1])")
assert OLD_PROGRAM != prior.OLD_PROGRAM
OLD_PROGRAM = OLD_PROGRAM.replace(
    "        capture_capsules(thaw(item.values))",
    """        if family == 'v5':
            assert item.kind == 'CONDITIONAL_WEIGHT_REGION_JUDGMENT'
            expected_rule = ('MINIMAX_REGRET' if MODE.endswith('regret') else
                             'MAXIMIN' if MODE.endswith('maximin') else 'EXPECTED')
            assert item.values['analyses'][0]['decision_rule'] == expected_rule
        capture_capsules(thaw(item.values))""")


class BoundedPolicyPredecessorTests(unittest.TestCase):
    forbidden_result_fragment = 'POLICY'
    rows = staticmethod(helpers.JointChangePredecessorUpgradeTests.rows)
    fixture = helpers.JointChangePredecessorUpgradeTests.fixture
    assert_inferences_unchanged = helpers.JointChangePredecessorUpgradeTests.assert_inferences_unchanged
    assert_capsules_unchanged = helpers.JointChangePredecessorUpgradeTests.assert_capsules_unchanged
    exercise_workload = helpers.JointChangePredecessorUpgradeTests.exercise_workload

    @classmethod
    def setUpClass(cls):
        tree = subprocess.check_output(
            ['git', 'rev-parse', BASELINE + '^{tree}'], cwd=fixtures.ROOT, text=True).strip()
        if (tree != BASELINE_TREE or
                revision_upgrade.BOUNDED_POLICY_PREDECESSOR_CODE_HASH != BASELINE_CODE_HASH):
            raise AssertionError('exact bounded-policy predecessor identity changed')

        class FrozenRuntime(fixtures.RuntimeUpgradeTests):
            baseline = BASELINE
            code_hash = BASELINE_CODE_HASH
            file_count = 237
            old_program = OLD_PROGRAM

            def old(self, schema=3, name='old', *, mode='pins'):
                self.old_program = 'MODE = ' + repr(mode) + '\n' + OLD_PROGRAM
                return super().old(schema, name)

        cls.runtime = FrozenRuntime
        cls.runtime.setUpClass()
        cls.verified_capsule_wires = set()

    @classmethod
    def tearDownClass(cls):
        cls.runtime.tearDownClass()

    def test_single_step_expected_maximin_regret_every_checkpoint_both_schemas(self):
        for schema in (3, 4):
            for rule in ('expected', 'maximin', 'regret'):
                mode = 'judgment-v5-' + rule
                with self.subTest(schema=schema, rule=rule), self.fixture() as fixture:
                    self.exercise_workload(fixture, schema, mode, erase=rule == 'regret')

    def test_exact_pin_rejects_changed_hash_indexes_governance_and_split_controls(self):
        helpers.JointChangePredecessorUpgradeTests.test_exact_pin_rejects_changed_hash_indexes_governance_and_split_controls(self)


if __name__ == '__main__':
    unittest.main()
