"""Synthetic transport observations; no credential, network, or benchmark data."""
import hashlib
import json
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

from hcl.v03.answer_loop import HCLAnswerLoop
from hcl.v03.action_checker import HCLActionChecker
from hcl.v03.backends import OpenAICompatibleBackend
from hcl.v03.decision_policy import HCLDecisionPolicy
from scripts.hcl_decision_diagnostics import (
    DecisionDiagnosticBackend,
    ProviderAttemptDiagnosticBackend,
)


class Diagnostics(unittest.TestCase):

    @staticmethod
    def _provider_response(
        content,
        *,
        finish_reason="stop",
        reasoning_content=None,
        prompt_tokens=100,
        completion_tokens=20,
        reasoning_tokens=None,
    ):
        message = SimpleNamespace(
            content=content,
            reasoning_content=reasoning_content,
            refusal=None,
            model_extra={},
        )
        choice = SimpleNamespace(message=message, finish_reason=finish_reason)
        details = SimpleNamespace(reasoning_tokens=reasoning_tokens)
        usage = SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            completion_tokens_details=details,
        )
        return SimpleNamespace(choices=[choice], usage=usage)

    @staticmethod
    def _backend_with_responses(responses):
        class FakeCompletions:
            def __init__(self, items):
                self.items = list(items)
                self.calls = []

            def create(self, **kwargs):
                self.calls.append(kwargs)
                item = self.items.pop(0)
                if isinstance(item, Exception):
                    raise item
                return item

        completions = FakeCompletions(responses)
        backend = object.__new__(OpenAICompatibleBackend)
        backend.client = SimpleNamespace(
            chat=SimpleNamespace(completions=completions)
        )
        backend.model = "deepseek-flash"
        backend.seed = 42
        return backend, completions

    def test_provider_attempt_wrapper_matches_frozen_retry_and_return(self):
        responses = [
            self._provider_response("", finish_reason="length", reasoning_content="PRIVATE_REASONING_SENTINEL", completion_tokens=4096, reasoning_tokens=4096),
            self._provider_response("", finish_reason="stop"),
            self._provider_response('{"ok":true}', finish_reason="stop"),
        ]
        plain, plain_calls = self._backend_with_responses(responses)
        plain_result = plain.complete(
            [{"role": "user", "content": "PRIVATE_PROMPT_SENTINEL"}],
            max_tokens=4096,
            temperature=0.0,
        )

        wrapped_responses = [
            self._provider_response("", finish_reason="length", reasoning_content="PRIVATE_REASONING_SENTINEL", completion_tokens=4096, reasoning_tokens=4096),
            self._provider_response("", finish_reason="stop"),
            self._provider_response('{"ok":true}', finish_reason="stop"),
        ]
        base, wrapped_calls = self._backend_with_responses(wrapped_responses)
        events = []
        wrapped = ProviderAttemptDiagnosticBackend(base, events.append)
        wrapped_result = wrapped.complete(
            [{"role": "user", "content": "PRIVATE_PROMPT_SENTINEL"}],
            max_tokens=4096,
            temperature=0.0,
        )

        self.assertEqual(wrapped_result, plain_result)
        self.assertEqual(wrapped_calls.calls, plain_calls.calls)
        self.assertEqual(len(events), 3)
        self.assertEqual(
            [e["outcome"] for e in events],
            ["content_empty", "content_empty", "content_nonempty"],
        )
        self.assertEqual(events[0]["finish_reason"], "length")
        self.assertEqual(events[0]["reasoning_bytes"], len("PRIVATE_REASONING_SENTINEL".encode()))
        self.assertEqual(events[0]["reasoning_tokens"], 4096)
        self.assertNotIn("SENTINEL", json.dumps(events))
        self.assertNotIn("messages", json.dumps(events).lower())

    def test_provider_attempt_wrapper_preserves_four_empty_limit(self):
        responses = [self._provider_response("") for _ in range(4)]
        base, calls = self._backend_with_responses(responses)
        events = []
        wrapped = ProviderAttemptDiagnosticBackend(base, events.append)
        self.assertEqual(wrapped.complete([], max_tokens=4096), "")
        self.assertEqual(len(calls.calls), 4)
        self.assertEqual(len(events), 4)
        self.assertTrue(all(e["outcome"] == "content_empty" for e in events))

    def test_provider_attempt_wrapper_preserves_exception_identity(self):
        failure = RuntimeError("PRIVATE_PROVIDER_ERROR_SENTINEL")
        base, calls = self._backend_with_responses([failure])
        events = []
        wrapped = ProviderAttemptDiagnosticBackend(base, events.append)
        with self.assertRaises(RuntimeError) as caught:
            wrapped.complete([], max_tokens=4096)
        self.assertIs(caught.exception, failure)
        self.assertEqual(len(calls.calls), 1)
        self.assertEqual(events, [{
            "backend_call": 1,
            "provider_attempt": 1,
            "max_tokens": 4096,
            "temperature": 0.0,
            "outcome": "transport_exception",
        }])
        self.assertNotIn("SENTINEL", json.dumps(events))

    def test_provider_attempt_bad_sink_is_inert(self):
        def broken(_):
            raise OSError("synthetic sink failure")
        response = self._provider_response('{"ok":true}')
        base, calls = self._backend_with_responses([response])
        wrapped = ProviderAttemptDiagnosticBackend(base, broken)
        self.assertEqual(wrapped.complete([], max_tokens=10), '{"ok":true}')
        self.assertEqual(len(calls.calls), 1)

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
        self.assertTrue(all(c.kwargs == {'max_tokens':8192,'temperature':0.0} for c in backend.complete.call_args_list))

    def test_v021a_budget_scope_is_decision_policy_only(self):
        backend = Mock()
        self.assertEqual(HCLDecisionPolicy(backend).max_tokens, 8192)
        self.assertEqual(HCLActionChecker(backend).max_tokens, 4096)
        loop = HCLAnswerLoop(backend)
        self.assertEqual(loop.state_max_tokens, 8192)
        self.assertEqual(loop.answer_max_tokens, 4096)
        self.assertEqual(loop.check_max_tokens, 4096)

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

        cases = [
            ("", "", "plain"),
            ("1", "", "decision"),
            ("", "1", "provider"),
            ("1", "1", "both"),
        ]
        for decision_value, provider_value, expected in cases:
            with (
                self.subTest(expected=expected),
                patch.dict(
                    "os.environ",
                    {
                        "HCL_DECISION_DIAGNOSTICS": decision_value,
                        "HCL_PROVIDER_ATTEMPT_DIAGNOSTICS": provider_value,
                    },
                ),
                patch.object(runner, "HCLSocialAgent", FakeHCL),
                patch.object(runner, "DirectSocialAgent", FakeDirect),
                patch.object(runner.AgentProfile, "get", return_value=object()),
            ):
                agents = runner.make_agents(
                    agent_ids=["a", "b"],
                    tested_index=0,
                    use_hcl=True,
                    seed=42,
                )
                agent = agents[0]
                self.assertEqual(agent.hcl_loop.backend.seed, 42)
                self.assertIs(agent.hcl_loop.backend, agent.action_checker.backend)

                transport = agent.decision_policy.backend
                if expected == "plain":
                    self.assertIs(transport, agent.hcl_loop.backend)
                elif expected == "decision":
                    self.assertIsInstance(transport, DecisionDiagnosticBackend)
                    self.assertIs(transport.backend, agent.hcl_loop.backend)
                elif expected == "provider":
                    self.assertIsInstance(
                        transport, ProviderAttemptDiagnosticBackend
                    )
                    self.assertIs(transport.backend, agent.hcl_loop.backend)
                else:
                    self.assertIsInstance(transport, DecisionDiagnosticBackend)
                    self.assertIsInstance(
                        transport.backend, ProviderAttemptDiagnosticBackend
                    )
                    self.assertIs(
                        transport.backend.backend,
                        agent.hcl_loop.backend,
                    )

                self.assertEqual(agents[1].direct_backend.seed, 42)

if __name__ == '__main__': unittest.main()
