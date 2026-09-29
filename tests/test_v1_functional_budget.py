"""Operational bounds, using fake transport only; no provider or frozen grant."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from scripts.run_cognition_functional_once import BoundedCalls, build_package, execute, ReplayExtraction, FIELDS


def response(content='{}', model='deepseek-flash'):
    return dict(model=model, usage=dict(prompt_tokens=50, completion_tokens=20),
        choices=[dict(finish_reason='stop', message=dict(content=content))])


class FunctionalBudgetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / 'receipt.json'
        self.package = build_package()

    def test_complete_two_calls_and_close(self):
        calls = []
        def transport(request):
            calls.append(request)
            if len(calls) == 1:
                return response(ReplayExtraction().complete_json(request['messages']))
            return response(json.dumps(dict.fromkeys(FIELDS, 'source-bounded fixture')))
        receipt = execute(self.package, transport, self.output)
        self.assertEqual(receipt['provider_calls'], 2)
        self.assertEqual(receipt['authorization_remaining_usd'], 0)
        self.assertIn('REQUIRES_SOURCE_FIRST_REVIEW', receipt['status'])
        self.assertEqual(calls[1]['messages'], receipt['preparation']['actual_final_messages'])
        self.assertTrue(all('response_raw' in a for a in receipt['attempts']))
        self.assertLess(receipt['conservative_guard_spend_usd'], .30)
        self.assertIsNone(receipt['actual_invoice_cost_usd'])
        with self.assertRaisesRegex(ValueError, 'existing receipt'):
            execute(self.package, transport, self.output)
        self.assertEqual(len(calls), 2)

    def test_transport_failure_reserves_and_prevents_later_call(self):
        calls = []
        def transport(request):
            calls.append(request)
            raise TimeoutError('no response')
        ledger = BoundedCalls(self.package, transport, self.output)
        with self.assertRaises(TimeoutError):
            ledger.call('extraction', [])
        with self.assertRaisesRegex(ValueError, 'cannot continue'):
            ledger.call('final', [])
        self.assertEqual(len(calls), 1)
        self.assertEqual(ledger.receipt['conservative_guard_spend_usd'], ledger.receipt['attempts'][0]['reserved_usd'])
        self.assertIsNone(ledger.receipt['estimated_provider_spend_usd'])

    def test_model_mismatch_preserves_raw_and_closes(self):
        ledger = BoundedCalls(self.package, lambda request: response(model='unexpected'), self.output)
        with self.assertRaisesRegex(ValueError, 'contract failed'):
            ledger.call('extraction', [])
        self.assertEqual(ledger.receipt['attempts'][0]['response_raw']['model'], 'unexpected')
        with self.assertRaises(ValueError):
            ledger.call('final', [])

    def test_cap_refuses_before_transport(self):
        package = copy.deepcopy(self.package)
        package['budget_cap_usd'] = .000001
        calls = []
        ledger = BoundedCalls(package, lambda request: calls.append(request), self.output)
        with self.assertRaisesRegex(ValueError, 'hard cap'):
            ledger.call('extraction', [])
        self.assertEqual(calls, [])
        self.assertEqual(ledger.receipt['attempts'], [])

    def test_missing_extraction_channel_refuses_final(self):
        calls = []
        def transport(request):
            calls.append(request)
            return response('{"candidates": []}')
        with self.assertRaises(ValueError):
            execute(self.package, transport, self.output)
        receipt = json.loads(self.output.read_text())
        self.assertEqual(len(calls), 1)
        self.assertEqual(receipt['provider_calls'], 1)
        self.assertEqual(receipt['budget_state'], 'CLOSED_NO_TRANSFER_NO_RERUN')
