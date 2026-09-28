"""Provider-free CG03 runner receipt and cap tests; fake provider only."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from scripts.run_cg03_external_once import (BudgetLedger, CG03Provider,
    load_frozen_package, run_with_provider, main)


class CG03RunnerTests(unittest.TestCase):
    def test_twenty_call_plan_and_raw_receipts(self):
        package = load_frozen_package()
        snapshots = []

        def fake_provider(messages):
            return {'model': package['model_version'], 'raw': '{}',
                'input_tokens': 100, 'output_tokens': 5,
                'cost_usd': 0.0001518, 'finish_reason': 'stop',
                'provider_price_estimated_cost_usd': 0.0000759,
                'usage_raw': {'prompt_tokens': 100, 'completion_tokens': 5},
                'response_raw': {'model': package['model_version'], 'choices': []}}

        result = run_with_provider(fake_provider, package,
            checkpoint=lambda ledger, rows=None: snapshots.append(
                (ledger.calls, len(rows or []))))
        self.assertEqual(result['calls'], 20)
        self.assertEqual(len(result['rows']), 20)
        self.assertLess(result['cost_usd'], package['proposed_new_hard_cap_usd'])
        self.assertEqual(result['attempts'][0]['request_raw']['model'],
                         'deepseek-v4-pro')
        self.assertEqual(result['attempts'][0]['request_raw']['thinking'],
                         {'type': 'disabled'})
        self.assertEqual(result['rows'][0]['response_raw']['model'],
                         package['model_version'])
        self.assertIsNone(result['rows'][0]['preflight'])
        self.assertTrue(result['rows'][3]['preflight']['checked_state_in_h'])
        self.assertEqual(snapshots[-1], (20, 20))

    def test_cap_stops_before_provider(self):
        package = load_frozen_package()
        ledger = BudgetLedger(package)
        ledger.calls = 20
        called = []
        with self.assertRaisesRegex(ValueError, 'call cap exceeded'):
            ledger.call(lambda messages: called.append(messages),
                        package['cases'][0]['messages']['C'])
        self.assertEqual(called, [])
        ledger.calls = 0
        ledger.cost_usd = 0.30
        with self.assertRaisesRegex(ValueError, 'USD hard cap'):
            ledger.call(lambda messages: called.append(messages),
                        package['cases'][0]['messages']['C'])
        self.assertEqual(called, [])

    def test_failed_response_is_preserved_and_not_retried(self):
        package = load_frozen_package()
        ledger = BudgetLedger(package)
        called = []
        raw = {'model': 'unexpected-model', 'choices': [{'message': {'content': '{}'}}]}

        def fake_provider(messages):
            called.append(messages)
            return {'model': 'unexpected-model', 'raw': '{}', 'input_tokens': 100,
                'output_tokens': 5, 'cost_usd': 0.0001518,
                'response_raw': raw}

        with self.assertRaisesRegex(ValueError, 'provider contract'):
            ledger.call(fake_provider, package['cases'][0]['messages']['C'])
        self.assertEqual(len(called), 1)
        self.assertEqual(ledger.calls, 1)
        self.assertEqual(ledger.attempts[0]['result']['response_raw'], raw)
        self.assertGreater(ledger.attempts[0]['failure_reservation_usd'], 0)

    def test_malformed_raw_response_is_preserved(self):
        package = load_frozen_package()
        provider = object.__new__(CG03Provider)
        provider.package = dict(package, maximum_output_tokens_per_call=512)
        raw = {'model': 'deepseek-v4-pro', 'choices': [], 'usage': None}
        response = SimpleNamespace(model_dump=lambda **kwargs: raw)
        provider.client = SimpleNamespace(chat=SimpleNamespace(completions=
            SimpleNamespace(create=lambda **kwargs: response)))
        ledger = BudgetLedger(package)
        with self.assertRaisesRegex(ValueError, 'provider contract'):
            ledger.call(provider, package['cases'][0]['messages']['C'])
        self.assertEqual(ledger.attempts[0]['result']['response_raw'], raw)
        self.assertEqual(ledger.calls, 1)

    def test_absent_grant_stops_before_provider_construction(self):
        with patch.dict('os.environ', {}, clear=True), patch(
                'sys.argv', ['run', '--out', 'unused']), patch(
                'scripts.run_cg03_external_once.CG03Provider') as provider:
            with self.assertRaisesRegex(SystemExit, 'owner grant is absent'):
                main()
            provider.assert_not_called()


if __name__ == '__main__':
    unittest.main()
