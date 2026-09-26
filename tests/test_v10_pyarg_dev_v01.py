import unittest
from unittest.mock import patch
from pathlib import Path
from scripts.prepare_v10_pyarg_dev_v01 import graph_from_source, prepared, family
from scripts.run_v10_pyarg_dev_v01 import (
    build_state,
    generic_labels,
    inputs,
    parse_answer,
    evaluate_one,
)

SOURCE = """def exercise():
    a = Argument('a')
    b = Argument('b')
    c = Argument('c')
    arguments = [a,b,c]
    defeats = [Defeat(a,b), Defeat(b,c)]
    af = AbstractArgumentationFramework('f',arguments,defeats)
    hidden_answer = 'POISON'
    assert secret_oracle(af) == hidden_answer
"""


def item():
    graph, source = graph_from_source(SOURCE, "exercise", "af")
    return {
        "case_id": "test",
        "graph": graph,
        "source": source,
        "source_sha256": "s",
        "source_file_sha256": "f",
        "family_sha256": "g",
        "semantics": "grounded",
    }


class UtilityTests(unittest.TestCase):
    def test_source_static_declarations_only_no_assertion_or_execution(self):
        g, s = graph_from_source(SOURCE, "exercise", "af")
        g2, s2 = graph_from_source(
            SOURCE.replace("'POISON'", "'OTHER_GOLD'").replace(
                "secret_oracle(af)", "arbitrary_command()"
            ),
            "exercise",
            "af",
        )
        self.assertEqual((g, s), (g2, s2))
        self.assertNotIn("POISON", s)
        self.assertNotIn("secret_oracle", s)
        with self.assertRaises(ValueError):
            graph_from_source(
                SOURCE.replace("Argument('a')", "read_hidden_annotation()"),
                "exercise",
                "af",
            )

    def test_unsupported_reassignment_cannot_reuse_stale_source_binding(self):
        altered = SOURCE.replace(
            "    arguments = [a,b,c]",
            "    a = read_hidden_annotation()\n    arguments = [a,b,c]",
        )
        with self.assertRaises(ValueError):
            graph_from_source(altered, "exercise", "af")

    def test_generic_exact_solver_not_hcl_runtime_algorithm(self):
        graph = item()["graph"]
        with patch(
            "hcl.v10.runtime.ArgumentFramework.extensions",
            side_effect=AssertionError("HCL not a generic oracle"),
        ):
            self.assertEqual(
                generic_labels(graph, "grounded"),
                [{"IN": ["a", "c"], "OUT": ["b"], "UNDEC": []}],
            )
        self.assertEqual(
            generic_labels(
                {"arguments": ["a", "b"], "attacks": [["a", "b"], ["b", "a"]]},
                "complete",
            ),
            [
                {"IN": [], "OUT": [], "UNDEC": ["a", "b"]},
                {"IN": ["a"], "OUT": ["b"], "UNDEC": []},
                {"IN": ["b"], "OUT": ["a"], "UNDEC": []},
            ],
        )

    def test_source_only_state_precedes_query_and_isomorphism_family(self):
        x = item()
        rt, _ = build_state(x)
        state = rt.answer_context("test")
        y = x | {"semantics": "complete"}
        rt2, _ = build_state(y)
        self.assertEqual(state, rt2.answer_context("test"))
        self.assertNotIn("generic_tool_labellings", state)
        self.assertEqual(
            family(x["graph"]),
            family({"arguments": ["X", "Y", "Z"], "attacks": [["X", "Y"], ["Y", "Z"]]}),
        )

    def test_output_structure_no_oracle_rescue(self):
        raw = '{"labellings":[{"IN":["a"],"OUT":["b"],"UNDEC":["c"]}],"reason":"a formal but incorrect labelling"}'
        # Well-formed wrong result is preserved for comparison, not parser refusal.
        self.assertEqual(
            parse_answer(raw, ["a", "b", "c"])["labellings"][0]["IN"], ["a"]
        )
        for bad in [
            "{}",
            '{"labellings":[],"reason":"x"}',
            raw.replace('"c"', '"b"'),
            raw.replace('"reason":', '"extra":1,"reason":'),
        ]:
            with self.assertRaises(ValueError):
                parse_answer(bad, ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
