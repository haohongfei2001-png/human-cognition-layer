import json, unittest
from scripts.prepare_v09_counterbench_dev_v01 import (
    source_model,
    query_task,
    reference_values,
    sha,
    CONTRACT,
)
from scripts.run_v09_counterbench_dev_v01 import (
    build_state,
    evaluate_one,
    parse_answer,
    CAPS,
    COST_CAP_USD,
)


class Backend:
    def __init__(self):
        self.inputs = []

    def complete_json(self, messages, **kwargs):
        self.inputs.append(messages)
        return '{"result":"UNKNOWN","reason":"Bounded fixture output."}'


class DevelopmentTests(unittest.TestCase):
    def test_source_only_construction_excludes_query_gold_and_annotations(self):
        source = "We know that A causes B, B causes not C. We observed B"
        item = {
            "case_id": "fixture",
            "source": source,
            "question": "Would C occur if not A instead of A?",
            "source_sha256": sha(source),
            "question_sha256": sha("query"),
            "answer": "POISON-NATIVE-GOLD",
            "meta": {"hidden": "POISON-GENERATOR"},
        }
        rt, m, f, c = build_state(item)
        state = rt.answer_context("fixture")
        state_text = json.dumps(state)
        for forbidden in ["Would C", "POISON", "public_question"]:
            self.assertNotIn(forbidden, state_text)
        self.assertIn(CONTRACT, state["source_view"]["events"][0]["raw_text"])
        backends = {a: Backend() for a in "CPD"}
        result = evaluate_one(item, backends)
        for arm in "CPD":
            released = json.loads(backends[arm].inputs[0][1]["content"])
            self.assertIn(source, released["source"])
            self.assertEqual(
                released["query"]["explicit_factual_assumptions"], {"A": 1, "B": 1}
            )
            self.assertNotIn("POISON", json.dumps(released))
        self.assertIn("source_only_state", result)
        self.assertIn("traces", result["conditional_calculation"])

    def test_native_causal_text_is_not_silently_treated_as_real_world_truth(self):
        m, f, c = source_model("We know that A causes B. We observed B", "fixture")
        target, observations, interventions = query_task(
            "Would B occur if not A instead of A?", m, f
        )
        self.assertEqual(
            reference_values(m, c, target, observations, interventions), [0]
        )
        self.assertEqual(
            m.counterfactual(
                target, observations=observations, interventions=interventions
            )["scope"],
            "CONDITIONAL_ON_DECLARED_MODEL",
        )
        with self.assertRaises(ValueError):
            source_model("A probably causes B", "fixture")
        with self.assertRaises(ValueError):
            source_model("We know that A causes B, and C.", "fixture")

    def test_inconsistent_observation_retained_and_independent_oracle(self):
        m, f, c = source_model(
            "We know that A causes not B, B causes C. We observed B", "fixture"
        )
        target, o, i = query_task("Would C occur if not A instead of A?", m, f)
        self.assertEqual(reference_values(m, c, target, o, i), [])
        self.assertEqual(
            m.counterfactual(target, observations=o, interventions=i)["status"],
            "INCONSISTENT_OBSERVATIONS",
        )

    def test_equal_bounded_answer_schema_and_planning_cap(self):
        self.assertEqual(
            parse_answer('{"result":"NO","reason":"conditional on model"}')["result"],
            "NO",
        )
        for raw in ['{"result":"yes","reason":"a"}', '{"result":"NO"}']:
            with self.assertRaises(ValueError):
                parse_answer(raw)
        bound = (
            sum(x["input_chars"] for x in CAPS.values()) * 0.30
            + sum(x["output_chars"] for x in CAPS.values()) * 1.20
        ) / 1e6
        self.assertLessEqual(bound, COST_CAP_USD)
        self.assertEqual(sum(x["calls"] for x in CAPS.values()), 24)


if __name__ == "__main__":
    unittest.main()
