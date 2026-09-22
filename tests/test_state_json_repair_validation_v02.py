from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

RUNNER_SPEC = importlib.util.spec_from_file_location(
    "repair_runner",
    ROOT / "scripts/run_state_json_repair_validation_v02.py",
)
assert RUNNER_SPEC and RUNNER_SPEC.loader
runner = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(runner)

AGG_SPEC = importlib.util.spec_from_file_location(
    "repair_agg",
    ROOT / "scripts/aggregate_state_json_repair_validation_v02.py",
)
assert AGG_SPEC and AGG_SPEC.loader
agg = importlib.util.module_from_spec(AGG_SPEC)
AGG_SPEC.loader.exec_module(agg)


class FakeInner:
    def __init__(self):
        self.json_calls = 0
        self.text_calls = 0

    def complete_json(self, messages, *, max_tokens, temperature=0.0):
        self.json_calls += 1
        return '{"mode":"SIMPLE"}'

    def complete(self, messages, *, max_tokens, temperature=0.0):
        self.text_calls += 1
        return "plain"


class RepairV02ValidationTests(unittest.TestCase):
    def test_observer_proxies_structured_mode(self):
        inner = FakeInner()
        observed = runner.ObservingRepairBackend(inner)
        got = observed.complete_json([], max_tokens=10)
        self.assertEqual(got, '{"mode":"SIMPLE"}')
        self.assertEqual(inner.json_calls, 1)
        self.assertEqual(inner.text_calls, 0)
        self.assertTrue(observed.attempts[0]["structured_mode"])
        self.assertTrue(observed.attempts[0]["json_object_parseable"])

    def test_pass_requires_24_successful_structured_cases(self):
        rows = []
        for i in range(24):
            rows.append({
                "id": f"x{i}",
                "length_band": "short",
                "complexity": "simple",
                "success": True,
                "failure_class": None,
                "attempts": [{"structured_mode": True}],
            })
        summary = agg.summarize(rows)
        self.assertTrue(summary["repair_pass"])
        self.assertEqual(summary["state_json_exhaustion_count"], 0)

    def test_any_failure_blocks_repair_pass(self):
        rows = []
        for i in range(24):
            rows.append({
                "id": f"x{i}",
                "length_band": "short",
                "complexity": "simple",
                "success": i != 3,
                "failure_class": "state_json_exhaustion" if i == 3 else None,
                "attempts": [{"structured_mode": True}],
            })
        summary = agg.summarize(rows)
        self.assertFalse(summary["repair_pass"])
        self.assertEqual(summary["state_json_exhaustion_count"], 1)

    def test_nonstructured_attempt_blocks_repair_pass(self):
        rows = []
        for i in range(24):
            rows.append({
                "id": f"x{i}",
                "length_band": "short",
                "complexity": "simple",
                "success": True,
                "failure_class": None,
                "attempts": [{"structured_mode": i != 0}],
            })
        self.assertFalse(agg.summarize(rows)["repair_pass"])


if __name__ == "__main__":
    unittest.main()
