"""Independent syntactic generalization invariants and bounded counterexamples."""

from copy import deepcopy
import itertools
import random
import unittest
from hcl.operators.concept_induction import generalize_examples


def term(symbol, *arguments, sort="Thing"):
    return dict(kind="TERM", sort=sort, symbol=symbol, arguments=list(arguments))


def example(name, value):
    return dict(id=name, term=value)


def independent_match(pattern, value, bindings=None):
    bindings = {} if bindings is None else bindings
    if pattern["sort"] != value["sort"]:
        return False
    if pattern["kind"] == "VARIABLE":
        old = bindings.setdefault(pattern["id"], value)
        return old == value
    if pattern["symbol"] != value["symbol"] or len(pattern["arguments"]) != len(
        value["arguments"]
    ):
        return False
    return all(
        independent_match(a, b, bindings)
        for a, b in zip(pattern["arguments"], value["arguments"])
    )


class ConceptInductionTests(unittest.TestCase):
    def test_repeated_disagreement_preserves_equality_and_rejects_false_boundary(self):
        a, b, c = map(term, "abc")
        positive = [example("a", term("pair", a, a)), example("b", term("pair", b, b))]
        negative = [
            example("mixed", term("pair", a, b)),
            example("novel-diagonal", term("pair", c, c)),
        ]
        value = generalize_examples(positive, negative)
        self.assertEqual(
            value["pattern"]["arguments"][0], value["pattern"]["arguments"][1]
        )
        self.assertEqual(
            [r["status"] for r in value["examples"]],
            ["MATCH", "MATCH", "NO_MATCH", "MATCH"],
        )
        self.assertEqual(value["counterexample_ids"], ("novel-diagonal",))
        self.assertEqual(value["status"], "REFUTED_BY_DECLARED_COUNTEREXAMPLE")

    def test_nested_structure_generalizes_without_relabeling_constants(self):
        positive = [
            example("one", term("P", term("a"), term("f", term("c")))),
            example("two", term("P", term("b"), term("f", term("b")))),
        ]
        value = generalize_examples(positive, [])
        pattern = value["pattern"]
        self.assertEqual(pattern["symbol"], "P")
        self.assertEqual(pattern["arguments"][1]["symbol"], "f")
        self.assertNotEqual(
            pattern["arguments"][0], pattern["arguments"][1]["arguments"][0]
        )
        self.assertTrue(
            all(independent_match(pattern, row["term"]) for row in positive)
        )

    def test_exhaustion_never_asserts_incomplete_pattern_or_unchecked_negative(self):
        positive = [
            example("one", term("P", term("a"), term("a"))),
            example("two", term("P", term("b"), term("b"))),
        ]
        negative = [example("bad", term("P", term("c"), term("c")))]
        full = generalize_examples(positive, negative)
        for budget in range(full["work"] + 1):
            result = generalize_examples(positive, negative, max_work=budget)
            self.assertLessEqual(result["work"], budget)
            if result["frontier"]:
                self.assertEqual(result["status"], "PARTIAL")
            else:
                self.assertEqual(result, full)
            if result["pattern"] is not None:
                self.assertTrue(
                    all(
                        independent_match(result["pattern"], row["term"])
                        for row in positive
                    )
                )
        self.assertIsNone(
            generalize_examples(positive, negative, max_work=1)["pattern"]
        )

    def test_minimality_for_all_depth_one_binary_terms_and_bounded_pattern_language(
        self,
    ):
        constants = [term(c) for c in "abc"]
        ground = [term("pair", a, b) for a, b in itertools.product(constants, repeat=2)]
        # Exhaustively enumerate constant/variable depth-one patterns independently.
        variables = [dict(kind="VARIABLE", sort="Thing", id=i) for i in ("x", "y")]
        patterns = [
            term("pair", a, b)
            for a, b in itertools.product(constants + variables, repeat=2)
        ]
        patterns += variables
        for first, second in itertools.product(ground, repeat=2):
            actual = generalize_examples(
                [example("first", first), example("second", second)], []
            )["pattern"]
            accepts = {i for i, t in enumerate(ground) if independent_match(actual, t)}
            for candidate in patterns:
                if independent_match(candidate, first) and independent_match(
                    candidate, second
                ):
                    self.assertLessEqual(
                        accepts,
                        {
                            i
                            for i, t in enumerate(ground)
                            if independent_match(candidate, t)
                        },
                    )

    def test_three_examples_and_alpha_renaming_keep_correlations(self):
        rng = random.Random(61212)
        for _ in range(100):
            values = [
                term("P", term(rng.choice("abc")), term(rng.choice("abc")))
                for _ in range(3)
            ]
            actual = generalize_examples(
                [example(str(i), t) for i, t in enumerate(values)], []
            )
            self.assertTrue(
                all(independent_match(actual["pattern"], t) for t in values)
            )
            renamed = deepcopy(values)
            for t in renamed:
                for arg in t["arguments"]:
                    arg["symbol"] = "α-" + arg["symbol"]
            other = generalize_examples(
                [example(str(i), t) for i, t in enumerate(renamed)], []
            )
            self.assertEqual(actual["work"], other["work"])
            self.assertEqual(
                [a["kind"] for a in actual["pattern"]["arguments"]],
                [a["kind"] for a in other["pattern"]["arguments"]],
            )

    def test_type_signature_and_proposed_variable_injections_rejected(self):
        with self.assertRaises(ValueError):
            generalize_examples(
                [example("one", term("a")), example("two", term("a", sort="Other"))], []
            )
        with self.assertRaises(ValueError):
            generalize_examples(
                [example("one", dict(kind="VARIABLE", sort="Thing", id="oracle"))], []
            )
        with self.assertRaises(ValueError):
            generalize_examples(
                [
                    example("one", term("P", term("a"))),
                    example("two", term("P", term("a"), term("b"))),
                ],
                [],
            )


if __name__ == "__main__":
    unittest.main()
