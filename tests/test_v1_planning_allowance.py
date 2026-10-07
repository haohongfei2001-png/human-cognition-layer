"""Fixed ordinary planning allowance, fake SDK only; no model-quality claim."""
from decimal import Decimal
import json
import unittest
from types import SimpleNamespace

from hcl.cognition import UniversalHCL, CallAllowance
from hcl.cognition.deepseek_metered import (
    DeepSeekMeteredPort, MeteredPortError, MODEL, INPUT_RATE, OUTPUT_RATE,
    safe_metered_failure_details,
)
from hcl.cognition.universal_entry import PLANNER_POLICY, HCLBoundaryError


class Client:
    max_retries = 0
    base_url = 'https://api.deepseek.com'
    timeout = 180

    def __init__(self, *, planning_tokens=12000, planning_finish='stop', answer_tokens=30):
        self.calls = []
        self.planning_tokens = planning_tokens
        self.planning_finish = planning_finish
        self.answer_tokens = answer_tokens
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **request):
        self.calls.append(request)
        planning = request['messages'][0]['content'] == PLANNER_POLICY
        content = dict(task='Prepare caller rule', operations=[dict(capability='G01',
            question='Prepare caller rule.', source_ids=[], bindings=[])], limitations=[])
        if not planning:
            content = dict(answer='The caller condition requires control.', source_citations=[],
                uncertainty='No actor episode supplied.', assumptions='No external facts used.')
        return dict(model=MODEL, choices=[dict(finish_reason=self.planning_finish if planning else 'stop',
            message=dict(content=json.dumps(content), reasoning_content='PRIVATE_REASONING_CANARY'))],
            usage=dict(prompt_tokens=100, completion_tokens=self.planning_tokens if planning else self.answer_tokens))


class OrdinaryPlanningAllowanceTests(unittest.TestCase):
    def test_defaults_are_explicit_16k_with_phase_specific_effort(self):
        port = DeepSeekMeteredPort(Client())
        messages = [dict(role='user', content='Complete source: 原文 🧠\nNo omissions.')]
        for phase, expected in [('planning', 16384), ('answer', 16384)]:
            request, wire = port.request(phase, messages)
            self.assertEqual(request['max_tokens'], expected)
            self.assertEqual(request['reasoning_effort'], 'high' if phase=='planning' else 'low')
            self.assertEqual(request['thinking'], {'type': 'enabled'})
            self.assertEqual(request['messages'], messages)
            self.assertEqual(json.loads(wire), request)
        self.assertEqual(port.client.calls, [])

    def test_exact_reservation_uses_entire_new_completion_allowance(self):
        port = DeepSeekMeteredPort(Client())
        messages = [dict(role='user', content='Source remains complete.')]
        _, wire = port.request('planning', messages)
        expected = ((2 * len(wire) + 2048) * INPUT_RATE + (16384 + 32) * OUTPUT_RATE) / 1000000
        self.assertEqual(Decimal(port.reservation_usd('planning', messages)), expected)
        self.assertEqual(port.client.calls, [])

    def test_valid_large_completion_reaches_real_native_and_final_without_retry(self):
        client = Client(); port = DeepSeekMeteredPort(client); journal = []
        allowance = CallAllowance(2, '1', 'OFFLINE_CONTROL_ONLY', journal=lambda x: journal.append(x))
        result = UniversalHCL().answer('For this analysis, responsibility requires control.',
            planner_backend=port, answer_backend=port, allowance=allowance)
        self.assertEqual(result['status'], 'ANSWERED_WITH_EXPLICIT_LIMITS')
        self.assertEqual([x['max_tokens'] for x in client.calls], [16384, 16384])
        self.assertTrue(any(x['executed'] for x in result['operations']))
        self.assertNotIn('PRIVATE_REASONING_CANARY', json.dumps([result, journal]))

    def test_old_4k_quote_cannot_fund_the_new_request(self):
        client = Client(); port = DeepSeekMeteredPort(client)
        messages = [dict(role='system', content=PLANNER_POLICY), dict(role='user', content='{}')]
        _, wire = port.request('planning', messages)
        old_hold = ((2 * len(wire) + 2048) * INPUT_RATE + (4096 + 32) * OUTPUT_RATE) / 1000000
        allowance = CallAllowance(2, str(old_hold), 'OFFLINE_OLD_HOLD_ONLY', journal=lambda x: None)
        with self.assertRaisesRegex(HCLBoundaryError, 'COST_ALLOWANCE_EXHAUSTED'):
            allowance.call(port, 'planning', messages)
        self.assertEqual(client.calls, [])
        self.assertEqual(allowance.attempts, [])

    def test_incomplete_return_still_stops_before_native_and_final(self):
        client = Client(planning_tokens=4096, planning_finish='length'); port = DeepSeekMeteredPort(client)
        allowance = CallAllowance(2, '1', 'OFFLINE_FAILURE_ONLY', journal=lambda x: None)
        result = UniversalHCL().answer('For this analysis, responsibility requires control.',
            planner_backend=port, answer_backend=port, allowance=allowance)
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0]['max_tokens'], 16384)
        self.assertTrue(allowance.closed)
        self.assertEqual(result['provider_attempts'][0]['failure_code'], 'INCOMPLETE_ANSWER_NO_RETRY')
        self.assertFalse(any(x['executed'] for x in result.get('operations', [])))

    def test_rejected_12k_usage_is_reported_safely_inside_exact_hold(self):
        client = Client(planning_tokens=12000, planning_finish='length'); port = DeepSeekMeteredPort(client)
        messages = [dict(role='system', content=PLANNER_POLICY)]
        reservation = port.reservation_usd('planning', messages)
        with self.assertRaises(MeteredPortError) as caught:
            port.complete('planning', messages)
        details = safe_metered_failure_details(caught.exception, reservation)
        self.assertEqual(details['finish_reasons'], ['length'])
        self.assertEqual(details['usage']['completion_tokens'], 12000)
        self.assertIn('actual_usd', details)
        self.assertNotIn('PRIVATE_', json.dumps(details))

    def test_outside_16k_plus_margin_remains_rejected(self):
        client = Client(planning_tokens=16384 + 33); port = DeepSeekMeteredPort(client)
        messages = [dict(role='system', content=PLANNER_POLICY)]
        port.reservation_usd('planning', messages)
        with self.assertRaisesRegex(MeteredPortError, 'USAGE_OUTSIDE_FROZEN_BOUND'):
            port.complete('planning', messages)
        self.assertEqual(len(client.calls), 1)

    def test_fixed_answer_limit_rejects_usage_over_its_explicit_margin(self):
        client = Client(answer_tokens=16384 + 33); port = DeepSeekMeteredPort(client)
        messages = [dict(role='user', content='Final source facts')]
        port.reservation_usd('answer', messages)
        with self.assertRaisesRegex(MeteredPortError, 'USAGE_OUTSIDE_FROZEN_BOUND'):
            port.complete('answer', messages)
        self.assertEqual(client.calls[0]['max_tokens'], 16384)
