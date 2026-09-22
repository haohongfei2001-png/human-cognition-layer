from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]

RUNNER_SPEC = importlib.util.spec_from_file_location(
    "structured_diag",
    ROOT / "scripts/run_structured_output_failure_diagnostic_v01.py",
)
assert RUNNER_SPEC and RUNNER_SPEC.loader
runner = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(runner)

AGG_SPEC = importlib.util.spec_from_file_location(
    "structured_diag_agg",
    ROOT / "scripts/aggregate_structured_output_failure_diagnostic_v01.py",
)
assert AGG_SPEC and AGG_SPEC.loader
agg = importlib.util.module_from_spec(AGG_SPEC)
AGG_SPEC.loader.exec_module(agg)


def fake_response(content, finish_reason="stop", prompt_tokens=10, completion_tokens=5):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
                finish_reason=finish_reason,
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


class StructuredOutputDiagnosticTests(unittest.TestCase):
    def test_valid_json_object_classification(self):
        meta = runner.observe_response(
            fake_response('{"a":1}'),
            hcl_attempt=1,
            provider_call=1,
            duration_ms=12,
        )
        self.assertEqual(meta["category"], "valid_json_object")
        self.assertTrue(meta["full_json_syntax_valid"])
        self.assertEqual(meta["json_top_level_type"], "object")
        self.assertTrue(meta["hcl_object_parseable"])

    def test_valid_json_nonobject_classification(self):
        meta = runner.observe_response(
            fake_response("[1,2]"),
            hcl_attempt=1,
            provider_call=1,
            duration_ms=12,
        )
        self.assertEqual(meta["category"], "valid_json_nonobject")
        self.assertEqual(meta["json_top_level_type"], "array")
        self.assertFalse(meta["hcl_object_parseable"])

    def test_nonparseable_length_classification(self):
        meta = runner.observe_response(
            fake_response('{"a":', finish_reason="length", completion_tokens=8192),
            hcl_attempt=1,
            provider_call=1,
            duration_ms=50,
        )
        self.assertEqual(meta["category"], "nonparseable_length")
        self.assertFalse(meta["full_json_syntax_valid"])
        self.assertFalse(meta["hcl_object_parseable"])

    def test_whitespace_length_is_empty_length(self):
        meta = runner.observe_response(
            fake_response("   \n  ", finish_reason="length", completion_tokens=8192),
            hcl_attempt=1,
            provider_call=1,
            duration_ms=50,
        )
        self.assertEqual(meta["category"], "empty_length")
        self.assertTrue(meta["empty_after_strip"])
        self.assertGreater(meta["response_bytes"], 0)
        self.assertEqual(meta["stripped_response_bytes"], 0)

    def test_embedded_object_recoverable(self):
        meta = runner.observe_response(
            fake_response("prefix {\"a\":1} suffix"),
            hcl_attempt=1,
            provider_call=1,
            duration_ms=12,
        )
        self.assertEqual(meta["category"], "embedded_object_recoverable")
        self.assertFalse(meta["full_json_syntax_valid"])
        self.assertTrue(meta["hcl_object_parseable"])

    def test_aggregate_is_diagnostic_not_repair_gate(self):
        row = {
            "id": "x",
            "length_band": "short",
            "complexity": "simple",
            "success": False,
            "failure_class": "state_json_exhaustion",
            "provider_calls": [
                {
                    "category": "empty_length",
                    "finish_reason": "length",
                    "empty_after_strip": True,
                    "hcl_object_parseable": False,
                    "completion_tokens": 8192,
                    "response_bytes": 8192,
                    "duration_ms": 100,
                    "full_json_syntax_valid": False,
                    "json_top_level_type": None,
                }
            ],
        }
        summary = agg.summarize([row])
        self.assertEqual(summary["provider_call_categories"]["empty_length"], 1)
        self.assertEqual(summary["finish_reason_counts"]["length"], 1)
        self.assertFalse(summary["diagnostic_complete"])


if __name__ == "__main__":
    unittest.main()
