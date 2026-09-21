"""Synthetic transport observations; no credential, network, or benchmark data."""
import hashlib
import json
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from hcl.v03.decision_policy import HCLDecisionPolicy
from scripts.hcl_decision_diagnostics import DecisionDiagnosticBackend


class Diagnostics(unittest.TestCase):
    def test_exact_forwarding_return_identity_and_no_content_in_event(self):
        raw = '{"chosen_action_intent":"PRIVATE_SENTINEL"}'
        backend = Mock(); backend.complete.return_value = raw
        events = []; wrapper = DecisionDiagnosticBackend(backend, events.append)
        messages = [{'role':'user', 'content':'SECRET_INPUT_SENTINEL'}]
        self.assertIs(wrapper.complete(messages, max_tokens=4096, temperature=0.0), raw)
        backend.complete.assert_called_once_with(messages, max_tokens=4096, temperature=0.0)
        self.assertIs(backend.complete.call_args.args[0], messages)
        self.assertEqual(events[0]['response_sha256'], hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(events[0]['outcome'], 'accepted_object')
        self.assertNotIn('SENTINEL', json.dumps(events))
        self.assertEqual(set(events[0]), {'call','max_tokens','temperature','outcome','response_bytes','response_sha256'})

    def test_frozen_policy_still_stops_after_three_invalid_outputs(self):
        backend = Mock(); backend.complete.side_effect = ['', '[1,2]', '{"unfinished":']
        events = []; policy = HCLDecisionPolicy(DecisionDiagnosticBackend(backend, events.append))
        with self.assertRaisesRegex(RuntimeError, 'no valid JSON after 3 attempts'):
            policy.build_plan(private_goal='synthetic', visible_context='synthetic', state={}, available_actions=['speak'])
        self.assertEqual(backend.complete.call_count, 3)
        self.assertEqual([e['outcome'] for e in events], ['empty','no_parseable_object','no_parseable_object'])
        self.assertTrue(all(c.kwargs == {'max_tokens':4096,'temperature':0.0} for c in backend.complete.call_args_list))

    def test_original_exception_propagates_once_without_message_disclosure(self):
        failure = RuntimeError('API_SECRET_SENTINEL'); backend = Mock(); backend.complete.side_effect = failure
        events = []; wrapper = DecisionDiagnosticBackend(backend, events.append)
        with self.assertRaises(RuntimeError) as caught:
            wrapper.complete([], max_tokens=4096)
        self.assertIs(caught.exception, failure)
        self.assertEqual(backend.complete.call_count, 1)
        self.assertEqual(events[0]['outcome'], 'transport_exception')
        self.assertNotIn('SENTINEL', json.dumps(events))

    def test_bad_sink_cannot_replace_success_or_failure(self):
        def broken(_): raise OSError('synthetic sink failure')
        backend = Mock(); backend.complete.return_value = '{}'
        wrapper = DecisionDiagnosticBackend(backend, broken)
        self.assertEqual(wrapper.complete([], max_tokens=10), '{}')
        failure = RuntimeError('original'); backend.complete.side_effect = failure
        with self.assertRaises(RuntimeError) as caught: wrapper.complete([], max_tokens=10)
        self.assertIs(caught.exception, failure)
        self.assertEqual(backend.complete.call_count, 2)

    def test_frozen_normalization_and_retry_suffix_unchanged(self):
        raw = '{"strategy_type":"EXIT","verification_status":"EXHAUSTED","fallback_required":false}'
        def run(wrapped):
            backend = Mock(); backend.complete.side_effect = ['invalid', raw]
            events = []; transport = DecisionDiagnosticBackend(backend, events.append) if wrapped else backend
            result = HCLDecisionPolicy(transport).build_plan(private_goal='synthetic',visible_context='synthetic',state={},available_actions=['leave'])
            return result,backend.complete.call_args_list
        self.assertEqual(run(True),run(False))

    def test_actual_runner_opt_in_wraps_only_decision_transport(self):
        from scripts import run_sotopia_hard_one_ab as runner
        class FakeHCL:
            def __init__(self, **kwargs):
                backend = SimpleNamespace(seed=None)
                self.hcl_loop = SimpleNamespace(backend=backend)
                self.decision_policy = SimpleNamespace(backend=backend)
                self.action_checker = SimpleNamespace(backend=backend)
        class FakeDirect:
            def __init__(self, **kwargs): self.direct_backend = SimpleNamespace(seed=None)
        for value in ('', '1'):
            with self.subTest(value=value), patch.dict('os.environ',{'HCL_DECISION_DIAGNOSTICS':value}), patch.object(runner,'HCLSocialAgent',FakeHCL), patch.object(runner,'DirectSocialAgent',FakeDirect), patch.object(runner.AgentProfile,'get',return_value=object()):
                agents = runner.make_agents(agent_ids=['a','b'],tested_index=0,use_hcl=True,seed=42)
                agent = agents[0]
                self.assertEqual(agent.hcl_loop.backend.seed,42)
                self.assertIs(agent.hcl_loop.backend,agent.action_checker.backend)
                if value == '1':
                    self.assertIsInstance(agent.decision_policy.backend,DecisionDiagnosticBackend)
                    self.assertIs(agent.decision_policy.backend.backend,agent.hcl_loop.backend)
                else: self.assertIs(agent.decision_policy.backend,agent.hcl_loop.backend)
                self.assertEqual(agents[1].direct_backend.seed,42)

if __name__ == '__main__': unittest.main()
