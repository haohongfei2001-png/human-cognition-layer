"""Real shipped two-step and single-step judgments retain their original delivered reasons.

Project only the exact 238 runtime Python files from PR448, never predecessor
fixtures, tests, evaluation data or current implementation. Each independent old
process persists completed, returned, unknown, computed and committed tasks.
The shared cutover harness checks immutable proof/claim bytes, no provider
resends, reconstruction, governance, old-writer fencing and revoked-read access.
"""
import inspect
import subprocess
import unittest

from hcl.memory.migrations import revision_upgrade
from tests import test_unified_policy_weight_upgrade as prior
from tests import test_unified_joint_change_upgrade as helpers
from tests import test_unified_s23_upgrade as fixtures

BASELINE = '2c27ff69631657d7498dd4e790850d218d27d019'
BASELINE_TREE = 'd18341445bc2d1ca4021d02c8e7d30325b53ac08'
BASELINE_CODE_HASH = '4b7d34319a0681b80eaa0caa23d8712dd91d38f9864d8e2907bd97526b61fcc5'

# Candidate builders only; the separate process imports the pinned PR448 runtime.
OLD_PROGRAM = prior.OLD_PROGRAM.replace(
    "    candidate = weight_propose(snapshot, question)",
    """    candidate = weight_propose(snapshot, question)
    if '-policy-' in MODE:
        base = policy_propose(snapshot, question)
        model = base['models'][0]; decision = model['decisions'][0]; frame = decision['frameworks'][0]
        frame.update(weights=None, decision_rule='PARETO')
        candidate = dict(base, schema='hcl-judgment-candidates-5', weight_domains=[dict(
            id='policy-values', source_id=model['mental']['source_id'], model_id=model['mental']['id'],
            decision_id=decision['id'], framework_id=frame['id'], decision_rule='EXPECTED', constraints=[],
            origin=frame['origin'], segment_ids=frame['segment_ids'])])""")
OLD_PROGRAM = OLD_PROGRAM.replace(
    "        capture_capsules(thaw(item.values))",
    """        assert 'reasoned_delivery' not in item.values
        if family == 'v5' and '-policy-' in MODE:
            assert item.values['analyses'][0]['policy_horizon'] == 2
            assert item.values['operator_version'] == 's4-two-step-policy-weight-regions-1'
        capture_capsules(thaw(item.values))""")


class WeightDeliveryPredecessorTests(unittest.TestCase):
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
                revision_upgrade.WEIGHT_DELIVERY_PREDECESSOR_CODE_HASH != BASELINE_CODE_HASH):
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
            for dialect, rule in (('v1','expected'), ('v1','maximin'), ('v5','expected'), ('v5','maximin'), ('v5','regret'), ('v5','policy-expected'), ('v5','policy-maximin'), ('v5','policy-regret')):
                mode = 'judgment-' + dialect + '-' + rule
                with self.subTest(schema=schema, rule=rule), self.fixture() as fixture:
                    self.exercise_workload(fixture, schema, mode, erase=rule == 'regret')

    def test_exact_pin_rejects_changed_hash_indexes_governance_and_split_controls(self):
        helpers.JointChangePredecessorUpgradeTests.test_exact_pin_rejects_changed_hash_indexes_governance_and_split_controls(self)


if __name__ == '__main__':
    unittest.main()
