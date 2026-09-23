from __future__ import annotations

import json
import unittest

from hcl.v04 import (
    ActionOption,
    CognitionStore,
    HypothesisGuidedPolicy,
    HypothesisTarget,
    HypothesisTracker,
    ProbeOption,
)
from hcl.v04.schema import SchemaValidationError


class FakeBackend:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.calls.append(messages)
        if not self.outputs:
            raise AssertionError("unexpected call")
        return self.outputs.pop(0)


class ProbePolicyTests(unittest.TestCase):
    def setUp(self):
        self.store = CognitionStore()
        self.tracker = HypothesisTracker(self.store)
        self.target = HypothesisTarget(
            target_id="t",
            subject_agent_id="agent",
            target_kind="MOTIVE",
            question="Why is the agent delaying?",
            candidate_definitions=(
                ("BUSY", "Agent is overloaded."),
                ("AVOIDING", "Agent is avoiding."),
            ),
        )
        self.tracker.create_target(self.target)
        self.state = self.tracker.current("t")
        self.policy = HypothesisGuidedPolicy()

    def tearDown(self):
        self.store.close()

    def test_choose_probe_requires_allowed_id(self):
        probes = (
            ProbeOption("ASK_LOAD", "Ask about workload."),
            ProbeOption("ASK_BLOCKER", "Ask about blockers."),
        )
        backend = FakeBackend([
            json.dumps({
                "probe_id": "BAD",
                "rationale": "bad",
                "targeted_hypotheses": ["BUSY"],
            }),
            json.dumps({
                "probe_id": "ASK_LOAD",
                "rationale": "Distinguishes workload from avoidance.",
                "targeted_hypotheses": ["BUSY", "AVOIDING"],
            }),
        ])
        decision = self.policy.choose_probe(
            self.target, self.state, [], probes, backend
        )
        self.assertEqual(decision.probe_id, "ASK_LOAD")
        self.assertTrue(decision.repaired)
        self.assertEqual(len(backend.calls), 2)

    def test_choose_probe_rejects_unknown_hypothesis_target(self):
        probes = (ProbeOption("ASK", "Ask a question."),)
        bad = json.dumps({
            "probe_id": "ASK",
            "rationale": "reason",
            "targeted_hypotheses": ["NOT_REGISTERED"],
        })
        backend = FakeBackend([bad, bad])
        with self.assertRaises(SchemaValidationError):
            self.policy.choose_probe(
                self.target, self.state, [], probes, backend
            )

    def test_choose_action_requires_rationale(self):
        actions = (
            ActionOption("WAIT", "Wait."),
            ActionOption("ACT", "Act."),
        )
        backend = FakeBackend([
            json.dumps({"action_id": "ACT", "rationale": ""}),
            json.dumps({
                "action_id": "WAIT",
                "rationale": "Evidence remains unresolved.",
            }),
        ])
        decision = self.policy.choose_action(
            self.target, self.state, [], actions, backend
        )
        self.assertEqual(decision.action_id, "WAIT")
        self.assertTrue(decision.repaired)

    def test_policy_does_not_mutate_hypothesis_state(self):
        probes = (ProbeOption("ASK", "Ask."),)
        before = self.tracker.current("t")
        backend = FakeBackend([
            json.dumps({
                "probe_id": "ASK",
                "rationale": "Useful probe.",
                "targeted_hypotheses": ["BUSY"],
            })
        ])
        self.policy.choose_probe(
            self.target, before, [], probes, backend
        )
        after = self.tracker.current("t")
        self.assertEqual(before, after)
        self.assertEqual(len(self.tracker.history("t")), 1)


if __name__ == "__main__":
    unittest.main()
