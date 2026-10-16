"""Real shipped two-step and single-step judgments survive weight composition.

Project only the exact 238 runtime Python files from PR447, never predecessor
fixtures, tests, evaluation data or current implementation. Each independent old
process persists completed, returned, unknown, computed and committed tasks.
The shared cutover harness checks immutable proof/claim bytes, no provider
resends, reconstruction, governance, old-writer fencing and revoked-read access.
"""
import inspect
import subprocess
import unittest

from hcl.memory.migrations import revision_upgrade
from tests import test_unified_bounded_policy_upgrade as prior
from tests import test_unified_joint_change_upgrade as helpers
from tests import test_unified_s23_upgrade as fixtures

BASELINE = 'e3b169abe54578ccbc9c8cb91aea0708ddb2d3df'
BASELINE_TREE = 'fb4c194b59db04f0b7c2efdd156aa1cd66f070d1'
BASELINE_CODE_HASH = '66e1f348de40d69f7988dd8158b7a1e91289acc39aaa41510350ac8bcd30f922'

# Supply only synthetic candidate construction to the exact shipped runtime.
from scripts import witness_unified_bounded_policies as policies
OLD_PROGRAM = prior.OLD_PROGRAM.replace('root = Path(sys.argv[1])',
    inspect.getsource(policies.two_step) + "\ndef policy_propose(snapshot, question):\n"
    "    candidate = two_step(base_propose(snapshot, question))\n"
    "    candidate['models'][0]['decisions'][0]['frameworks'][0]['decision_rule'] = ('MAXIMIN' if MODE.endswith('maximin') else 'EXPECTED')\n"
    "    return candidate\n\nroot = Path(sys.argv[1])")
OLD_PROGRAM = OLD_PROGRAM.replace("'v1': base_propose", "'v1': policy_propose")
OLD_PROGRAM = OLD_PROGRAM.replace(
    "        capture_capsules(thaw(item.values))",
    """        if family == 'v1':
            assert item.kind == 'CONDITIONAL_ACTION_JUDGMENT'
            decision = item.values['models'][0]['decisions'][0]
            assert decision['policy_horizon'] == 2
            assert any(row.get('policy', {}).get('root_action_id') == 'inspect' for row in decision['outcomes'])
        capture_capsules(thaw(item.values))""")



class PolicyWeightPredecessorTests(unittest.TestCase):
    forbidden_result_fragment = 'UNAUTHORIZED_POLICY_WEIGHT_RESULT'
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
                revision_upgrade.POLICY_WEIGHT_PREDECESSOR_CODE_HASH != BASELINE_CODE_HASH):
            raise AssertionError('exact bounded-policy predecessor identity changed')

        class FrozenRuntime(fixtures.RuntimeUpgradeTests):
            baseline = BASELINE
            code_hash = BASELINE_CODE_HASH
            file_count = 238
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

    def test_policy_and_single_step_every_checkpoint_both_schemas(self):
        for schema in (3, 4):
            for dialect, rule in (('v1','expected'), ('v1','maximin'), ('v5','expected'), ('v5','maximin'), ('v5','regret')):
                mode = 'judgment-' + dialect + '-' + rule
                with self.subTest(schema=schema, rule=rule), self.fixture() as fixture:
                    self.exercise_workload(fixture, schema, mode, erase=rule == 'regret')

    def test_exact_pin_rejects_changed_hash_indexes_governance_and_split_controls(self):
        helpers.JointChangePredecessorUpgradeTests.test_exact_pin_rejects_changed_hash_indexes_governance_and_split_controls(self)


if __name__ == '__main__':
    unittest.main()
