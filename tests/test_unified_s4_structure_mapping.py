"""Independent finite mapping oracles, not gold natural-language analogies."""

from copy import deepcopy
import itertools
import random
import unittest

from hcl.operators.structure_mapping import structural_mappings


def entity(name, kind="thing"):
    return dict(id=name, type=kind)


def predicate(name, *arguments, kind="RELATION"):
    return dict(id=name, kind=kind, arguments=list(arguments))


def e(name):
    return dict(kind="ENTITY", id=name)


def f(name):
    return dict(kind="FACT", id=name)


def fact(name, symbol, *arguments, negated=False):
    return dict(id=name, predicate=symbol, arguments=list(arguments), negated=negated)


def domain(names, facts, predicates=None):
    return dict(
        entities=[entity(name) for name in names],
        predicates=predicates or [predicate("R", "ENTITY:thing", "ENTITY:thing")],
        facts=facts,
    )


def fact_chain(depth, fanout=1, name="x"):
    return domain(
        [name],
        [fact("r0", "R", e(name))]
        + [
            fact(f"r{i}", "H", *(f(f"r{i-1}") for _ in range(fanout)))
            for i in range(1, depth)
        ],
        [predicate("R", "ENTITY:thing"), predicate("H", *["FACT"] * fanout)],
    )


class StructureMappingTests(unittest.TestCase):
    def run_mapping(self, base, target, pairs=None, **kwargs):
        return structural_mappings(base, target, pairs or [["R", "R"]], **kwargs)

    def test_actual_subtree_height_is_independent_of_fact_order(self):
        from hcl.operators.structure_mapping import _domain

        for depth in (1, 16, 17, 32):
            value = fact_chain(depth)
            for rows in (value["facts"], list(reversed(value["facts"]))):
                with self.subTest(depth=depth, reverse=rows[0]["id"] != "r0"):
                    candidate = dict(value, facts=rows)
                    if depth <= 16:
                        _domain(candidate)
                    else:
                        with self.assertRaises(ValueError):
                            _domain(candidate)

    def test_shared_fact_dag_uses_compact_nodes_through_codec(self):
        from unittest.mock import patch
        from hcl.operators import structure_mapping as op
        from hcl.kernel.types import freeze, thaw
        from hcl.memory import codec

        value = fact_chain(16, 4)
        with patch.object(op, "_node_id", wraps=op._node_id) as digest:
            op._domain(value)
        self.assertEqual(digest.call_count, 16)
        for budget in (0, 1000000):
            actual = self.run_mapping(
                value, value, [["R", "R"], ["H", "H"]], max_work=budget
            )
            self.assertLessEqual(actual["work"], budget)
            encoded = codec.dumps(freeze(actual))
            self.assertLess(len(encoded), 100000)
            self.assertEqual(thaw(codec.loads(encoded)), thaw(freeze(actual)))
            for mapping in actual["mappings"]:
                nodes = mapping["projected_expression_nodes"]
                self.assertLessEqual(len(nodes), 16)
                for key, node in nodes.items():
                    self.assertEqual(op._node_id(node), key)
                    self.assertEqual(op._node_id(thaw(node)), key)
                    for kind, child in node[2]:
                        if kind == "FACT":
                            self.assertIn(child, nodes)
                for prediction in mapping["predictions"]:
                    self.assertEqual(
                        nodes[prediction["hypothesis_id"]], prediction["hypothesis"]
                    )
        self.assertTrue(actual["mappings"])

    def test_nested_attributes_use_established_binding_and_only_secondary_penalty(self):
        for ambiguous in (False, True):
            ps = [
                predicate("R", "ENTITY:thing", "ENTITY:thing"),
                predicate("A", "ENTITY:thing", kind="ATTRIBUTE"),
                predicate("B", "ENTITY:thing", kind="ATTRIBUTE"),
                predicate("H", "FACT"),
            ]
            base = domain(
                "ab",
                [
                    fact("r", "R", e("a"), e("b")),
                    fact("aa", "A", e("a")),
                    fact("ab", "A", e("b")),
                    fact("h", "H", f("aa")),
                ],
                ps,
            )
            target = domain(
                "xy",
                [
                    fact("r", "R", e("x"), e("y")),
                    fact("bx", "B", e("x")),
                    fact("nby", "B", e("y"), negated=True),
                    fact("h", "H", f("bx")),
                ],
                ps,
            )
            pairs = [["R", "R"], ["H", "H"], ["A", "B"]] + (
                [["A", "A"]] if ambiguous else []
            )
            rows = self.run_mapping(base, target, pairs)["mappings"]
            row = next(
                r
                for r in rows
                if r["entities"] == dict(a="x", b="y") and "H" in r["predicates"]
            )
            self.assertEqual(row["explicit_counterexamples"], 0)
            self.assertEqual(row["attribute_mismatches"], 1)
            prediction = next(p for p in row["predictions"] if p["base_fact"] == "ab")
            self.assertEqual(prediction["status"], "TARGET_REFUTED")
            self.assertFalse(any(prediction["metric_contributions"].values()))
            check = next(c for c in row["attribute_checks"] if c["base_fact"] == "ab")
            self.assertEqual(check["target_predicate"], "B")
            self.assertEqual(check["counterexample_target_fact"], "nby")

    def test_secondary_attribute_cannot_reuse_occupied_target_predicate(self):
        ps = [
            predicate("R", "ENTITY:thing", "ENTITY:thing"),
            predicate("A", "ENTITY:thing", kind="ATTRIBUTE"),
            predicate("B", "ENTITY:thing", kind="ATTRIBUTE"),
            predicate("C", "ENTITY:thing", kind="ATTRIBUTE"),
            predicate("H", "FACT"),
        ]
        base = domain(
            "ab",
            [
                fact("r", "R", e("a"), e("b")),
                fact("aa", "A", e("a")),
                fact("cb", "C", e("b")),
                fact("h", "H", f("aa")),
            ],
            ps,
        )
        target = domain(
            "xy",
            [
                fact("r", "R", e("x"), e("y")),
                fact("bx", "B", e("x")),
                fact("nby", "B", e("y"), negated=True),
                fact("h", "H", f("bx")),
            ],
            ps,
        )
        out = self.run_mapping(
            base, target, [["R", "R"], ["H", "H"], ["A", "B"], ["C", "B"]]
        )
        row = next(
            r
            for r in out["mappings"]
            if r["entities"] == dict(a="x", b="y") and "H" in r["predicates"]
        )
        check = next(c for c in row["attribute_checks"] if c["base_fact"] == "cb")
        self.assertEqual(check["status"], "ATTRIBUTE_ALIGNMENT_UNDETERMINED")
        self.assertEqual(check["alignment_reason"], "PREDICATE_MAPPING_CONFLICT")
        self.assertEqual(check["target_predicate"], "B")
        self.assertEqual(row["attribute_mismatches"], 0)

    def test_one_to_one_preserves_roles_not_surface_names(self):
        base = domain(["sun", "planet"], [fact("orbit", "R", e("planet"), e("sun"))])
        target = domain(
            ["sun", "electron"], [fact("orbital", "R", e("sun"), e("electron"))]
        )
        out = self.run_mapping(base, target)
        self.assertFalse(out["frontier"])
        self.assertEqual(len(out["mappings"]), 1)
        self.assertEqual(
            out["mappings"][0]["entities"], {"planet": "sun", "sun": "electron"}
        )
        # Repeated argument positions cannot map to two target entities.
        base["facts"][0]["arguments"] = [e("sun"), e("sun")]
        self.assertEqual(self.run_mapping(base, target)["mappings"], [])

    def test_higher_order_arguments_must_share_the_same_mapping(self):
        predicates = [
            predicate("R", "ENTITY:thing", "ENTITY:thing"),
            predicate("CAUSE", "FACT", "FACT"),
        ]
        base = domain(
            "abc",
            [
                fact("r1", "R", e("a"), e("b")),
                fact("r2", "R", e("b"), e("c")),
                fact("c", "CAUSE", f("r1"), f("r2")),
            ],
            predicates,
        )
        target = domain(
            "xyz",
            [
                fact("t1", "R", e("x"), e("y")),
                fact("t2", "R", e("y"), e("z")),
                fact("d", "CAUSE", f("t1"), f("t2")),
            ],
            predicates,
        )
        out = self.run_mapping(base, target, [["R", "R"], ["CAUSE", "CAUSE"]])
        row = out["mappings"][0]
        self.assertEqual(row["entities"], dict(a="x", b="y", c="z"))
        self.assertEqual(row["higher_order_links"], 2)
        self.assertEqual(row["supported_relations"], 3)
        target["facts"][1]["arguments"] = [e("x"), e("z")]
        out = self.run_mapping(base, target, [["R", "R"], ["CAUSE", "CAUSE"]])
        self.assertTrue(all(row["higher_order_links"] == 0 for row in out["mappings"]))
        self.assertTrue(all("c" not in row["facts"] for row in out["mappings"]))

    def test_explicit_counterexample_does_not_destroy_partial_mapping_or_become_fact(
        self,
    ):
        base = domain(
            "abc",
            [
                fact("ab", "R", e("a"), e("b")),
                fact("bc", "R", e("b"), e("c")),
                fact("ac", "R", e("a"), e("c")),
            ],
        )
        target = domain(
            "xyz",
            [
                fact("xy", "R", e("x"), e("y")),
                fact("yz", "R", e("y"), e("z")),
                fact("not-xz", "R", e("x"), e("z"), negated=True),
            ],
        )
        out = self.run_mapping(base, target)
        row = next(
            row
            for row in out["mappings"]
            if row["entities"] == dict(a="x", b="y", c="z")
        )
        prediction = next(p for p in row["predictions"] if p["base_fact"] == "ac")
        self.assertEqual(prediction["status"], "TARGET_REFUTED")
        self.assertEqual(prediction["counterexample_target_fact"], "not-xz")
        self.assertEqual(
            prediction["qualification"], "HYPOTHETICAL_TRANSFER_NOT_TARGET_FACT"
        )
        self.assertEqual(row["explicit_counterexamples"], 1)
        target["facts"].pop()
        row = next(
            row
            for row in self.run_mapping(base, target)["mappings"]
            if row["entities"] == dict(a="x", b="y", c="z")
        )
        self.assertEqual(
            next(p for p in row["predictions"] if p["base_fact"] == "ac")["status"],
            "TARGET_UNDETERMINED",
        )
        self.assertEqual(row["explicit_counterexamples"], 0)
        target["facts"] += [
            fact("yes", "R", e("x"), e("z")),
            fact("no", "R", e("x"), e("z"), negated=True),
        ]
        row = next(
            row
            for row in self.run_mapping(base, target)["mappings"]
            if row["entities"] == dict(a="x", b="y", c="z")
        )
        self.assertEqual(
            next(p for p in row["predictions"] if p["base_fact"] == "ac")["status"],
            "CONFLICTING_TARGET_EVIDENCE",
        )

    def test_attributes_do_not_seed_analogy_but_explicit_mismatches_remain(self):
        predicates = [
            predicate("R", "ENTITY:thing", "ENTITY:thing"),
            predicate("RED", "ENTITY:thing", kind="ATTRIBUTE"),
        ]
        base = domain(
            "ab",
            [fact("r", "R", e("a"), e("b")), fact("red", "RED", e("a"))],
            predicates,
        )
        target = domain(
            "xy",
            [fact("s", "R", e("x"), e("y")), fact("blue", "RED", e("x"), negated=True)],
            predicates,
        )
        out = self.run_mapping(base, target, [["R", "R"], ["RED", "RED"]])
        self.assertEqual(out["mappings"][0]["attribute_mismatches"], 1)
        base["facts"].pop(0)
        target["facts"].pop(0)
        self.assertEqual(
            self.run_mapping(base, target, [["R", "R"], ["RED", "RED"]])["mappings"], []
        )

    def test_predicate_correspondence_is_explicit_and_one_to_one(self):
        ps = [predicate(p, "ENTITY:thing", "ENTITY:thing") for p in "PQ"]
        base = domain(
            "abc",
            [fact("ab", "P", e("a"), e("b")), fact("bc", "P", e("b"), e("c"))],
            ps,
        )
        target = domain(
            "xyz",
            [fact("xy", "P", e("x"), e("y")), fact("yz", "Q", e("y"), e("z"))],
            ps,
        )
        out = self.run_mapping(base, target, [["P", "P"], ["P", "Q"]])
        self.assertTrue(all(len(row["facts"]) == 1 for row in out["mappings"]))
        self.assertEqual(structural_mappings(base, target, [])["mappings"], [])

    def test_budget_prefix_never_claims_global_maximality(self):
        base = domain(
            "abc", [fact("ab", "R", e("a"), e("b")), fact("bc", "R", e("b"), e("c"))]
        )
        target = domain(
            "xyz", [fact("xy", "R", e("x"), e("y")), fact("yz", "R", e("y"), e("z"))]
        )
        complete = self.run_mapping(base, target)
        for budget in range(complete["work"] + 1):
            out = self.run_mapping(base, target, max_work=budget)
            self.assertLessEqual(out["work"], budget)
            if out["frontier"]:
                self.assertTrue(
                    all(
                        r["maximality"] == "SEARCH_PREFIX_ONLY" for r in out["mappings"]
                    )
                )
            else:
                self.assertEqual(out["mappings"], complete["mappings"])
        symmetric = domain(
            "xyz", [fact("xy", "R", e("x"), e("y")), fact("yx", "R", e("y"), e("x"))]
        )
        out = self.run_mapping(base, symmetric, max_mappings=1)
        self.assertIn("MAPPING_OUTPUT_FRONTIER", out["frontier"])

    def test_search_state_storage_is_bounded_separately_from_work(self):
        from unittest.mock import patch

        base = domain("ab", [fact("ab", "R", e("a"), e("b"))])
        target = domain("xy", [fact("xy", "R", e("x"), e("y"))])
        with patch("hcl.operators.structure_mapping.MAX_SEARCH_STATES", 1):
            actual = self.run_mapping(base, target)
        self.assertIn("MAPPING_STATE_STORAGE_FRONTIER", actual["frontier"])
        self.assertTrue(
            all(row["maximality"] == "SEARCH_PREFIX_ONLY" for row in actual["mappings"])
        )

    def test_input_cycles_duplicates_and_sort_mismatch_rejected(self):
        base = domain("ab", [fact("ab", "R", e("a"), e("b"))])
        for mutation in ("duplicate", "cycle", "sort"):
            bad = deepcopy(base)
            if mutation == "duplicate":
                bad["facts"].append(dict(bad["facts"][0], id="duplicate"))
            elif mutation == "cycle":
                bad["predicates"] = [predicate("R", "FACT")]
                bad["facts"][0]["arguments"] = [f("ab")]
            else:
                bad["entities"][0]["type"] = "other"
            with self.assertRaises(ValueError):
                self.run_mapping(bad, base)

    def test_random_three_entity_graphs_against_independent_partial_injections(self):
        rng = random.Random(61012)
        edges = list(itertools.product(range(3), repeat=2))
        for case in range(100):
            a = [edge for edge in edges if rng.random() < 0.3]
            z = [edge for edge in edges if rng.random() < 0.3]
            base = domain(
                [f"b{i}" for i in range(3)],
                [fact(f"b{x}{y}", "R", e(f"b{x}"), e(f"b{y}")) for x, y in a],
            )
            target = domain(
                [f"t{i}" for i in range(3)],
                [fact(f"t{x}{y}", "R", e(f"t{x}"), e(f"t{y}")) for x, y in z],
            )
            candidates = set()
            for assignment in itertools.product((-1, 0, 1, 2), repeat=3):
                mapped = [v for v in assignment if v >= 0]
                if len(mapped) != len(set(mapped)):
                    continue
                supported = [
                    (x, y)
                    for x, y in a
                    if assignment[x] >= 0
                    and assignment[y] >= 0
                    and (assignment[x], assignment[y]) in z
                ]
                if not supported:
                    continue
                used = set(itertools.chain.from_iterable(supported))
                pairs = {("ENTITY", f"b{i}", f"t{assignment[i]}") for i in used}
                pairs |= {
                    ("FACT", f"b{x}{y}", f"t{assignment[x]}{assignment[y]}")
                    for x, y in supported
                }
                candidates.add(frozenset(pairs))
            oracle = {
                v for v in candidates if not any(v < other for other in candidates)
            }
            actual = self.run_mapping(base, target, max_work=1000000, max_mappings=256)
            self.assertFalse(actual["frontier"], (case, actual["frontier"]))
            observed = {
                frozenset(
                    [
                        *(("ENTITY", b, t) for b, t in row["entities"].items()),
                        *(("FACT", b, t) for b, t in row["facts"].items()),
                    ]
                )
                for row in actual["mappings"]
            }
            self.assertEqual(observed, oracle, case)


if __name__ == "__main__":
    unittest.main()
