import unittest
from scripts.i02_source_holder_budget_v2 import reserve_future_source_audit
from scripts.i02_source_holder_review import messages
from scripts.run_i02_gilman_holder_once import load_package


class FutureBudgetTests(unittest.TestCase):
    def test_native_reasoning_capacity_without_source_loss_or_automatic_authorization(self):
        ordinary=messages('authored-fixture','Mina reports an earlier plan and a later revision. The other actor intent is unknown.')
        before=repr(ordinary);gate=reserve_future_source_audit(ordinary,.18)
        self.assertEqual(repr(ordinary),before)
        self.assertEqual(gate['max_output_tokens'],16384)
        self.assertEqual(gate['client_timeout_seconds'],300)
        self.assertEqual(gate['provider_calls_authorized'],0)
        self.assertFalse(gate['model_semantics_qualified'])
        self.assertFalse(gate['consumed_v1_migration'])

    def test_source_revision_changes_bound_and_insufficient_cap_fails_before_transport(self):
        a=messages('fixture','Mina reports uncertainty.')
        b=messages('fixture','Mina reports uncertainty. ' * 100)
        self.assertGreater(reserve_future_source_audit(b,.18)['peak_reservation_usd'],
                           reserve_future_source_audit(a,.18)['peak_reservation_usd'])
        with self.assertRaises(ValueError):reserve_future_source_audit(b,.001)
        with self.assertRaises(ValueError):reserve_future_source_audit(a[:1],.18)

    def test_consumed_v1_freeze_and_budget_are_unchanged(self):
        p=load_package()
        self.assertEqual(p['max_tokens'],8192)
        self.assertEqual(p['maximum_provider_calls'],1)
        self.assertFalse(p['historical_budget_transfer'])

if __name__=='__main__':unittest.main()
