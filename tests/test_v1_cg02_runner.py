"""Provider-free verification of the authorized runner's receipts and limits."""
import unittest

from scripts.run_cg02_external_once import BudgetLedger, load_frozen_package, run_with_provider


class CG02RunnerTests(unittest.TestCase):
    def test_frozen_twenty_call_plan_preserves_raw_receipts(self):
        package = load_frozen_package()
        snapshots = []

        def fake_provider(messages):
            return {
                'model': package['model_version'],
                'raw': '{}', 'input_tokens': 100, 'output_tokens': 5,
                'cost_usd': 0.0001518, 'finish_reason': 'stop',
                'provider_price_estimated_cost_usd': 0.0000759,
                'usage_raw': {'prompt_tokens': 100, 'completion_tokens': 5},
                'response_raw': {'model': package['model_version'], 'choices': []},
            }

        result = run_with_provider(fake_provider, package,
            checkpoint=lambda ledger, rows=None: snapshots.append((ledger.calls, len(rows or []))))
        self.assertEqual(result['calls'], 20)
        self.assertEqual(len(result['rows']), 20)
        self.assertLess(result['cost_usd'], 0.30)
        self.assertEqual(result['attempts'][0]['request_raw']['model'], 'deepseek-v4-pro')
        self.assertEqual(result['attempts'][0]['request_raw']['thinking'], {'type': 'disabled'})
        self.assertEqual(result['rows'][0]['response_raw']['model'], package['model_version'])
        self.assertTrue(result['rows'][0]['preflight'] is None)
        self.assertTrue(result['rows'][3]['preflight']['checked_state_in_h'])
        self.assertEqual(snapshots[-1], (20, 20))

    def test_call_cap_stops_before_provider(self):
        package = load_frozen_package()
        ledger = BudgetLedger(package)
        ledger.calls = 20
        called = []
        with self.assertRaisesRegex(ValueError, 'call cap exceeded'):
            ledger.call(lambda messages: called.append(messages),
                package['cases'][0]['messages']['C'])
        self.assertEqual(called, [])


if __name__ == '__main__':
    unittest.main()
