"""Independent finite partition/LGG/OR oracle for counterexample repairs.

These synthetic tests do not call providers, spend money, read sealed material,
reuse the implementation's anti-unifier/matcher, or infer an open-world law.
Only the public repair_examples entry point is imported by the contract tests.
"""

from copy import deepcopy
from itertools import combinations, permutations, product
import unittest


def term(symbol, *arguments, sort="Thing"):
    return dict(kind="TERM", sort=sort, symbol=symbol, arguments=list(arguments))


def example(identity, value):
    return dict(id=identity, term=value)


def request(mode, person, credential):
    return term(
        "request", term(mode, sort="Mode"), term(person, sort="Person"),
        term(credential, sort="Credential"), sort="Request",
    )


def repair_fixture():
    return (
        [
            example("p-a", request("standard", "a", "signed")),
            example("p-b", request("standard", "b", "signed")),
            example("p-c", request("emergency", "c", "waiver")),
            example("p-d", request("emergency", "d", "waiver")),
        ],
        [
            example("n-e", request("standard", "e", "waiver")),
            example("n-f", request("emergency", "f", "signed")),
        ],
    )


def frozen_term(value):
    """An immutable algebra, deliberately separate from production AST code."""
    if value["kind"] == "VARIABLE":
        return ("var", value["sort"], value["id"])
    return (
        "node", value["sort"], value["symbol"],
        tuple(frozen_term(child) for child in value["arguments"]),
    )


def oracle_lgg(values):
    """Memoize disagreement vectors to retain repeated-variable constraints."""
    disagreement_variables = {}

    def visit(nodes):
        if len(set(nodes)) == 1:
            return nodes[0]
        if len({node[1] for node in nodes}) != 1:
            raise ValueError("the oracle never merges different declared sorts")
        heads = {(node[2], len(node[3])) for node in nodes}
        if len(heads) != 1:
            if nodes not in disagreement_variables:
                disagreement_variables[nodes] = ("var", nodes[0][1], len(disagreement_variables))
            return disagreement_variables[nodes]
        return (
            "node", nodes[0][1], nodes[0][2],
            tuple(visit(tuple(node[3][i] for node in nodes)) for i in range(len(nodes[0][3]))),
        )

    return visit(tuple(frozen_term(value) for value in values))


def alpha_normalized(pattern):
    names = {}

    def visit(node):
        if node[0] == "var":
            key = (node[1], node[2])
            return ("var", node[1], names.setdefault(key, len(names)))
        return ("node", node[1], node[2], tuple(visit(child) for child in node[3]))

    return visit(pattern)


def oracle_match(pattern, value):
    """Return both truth and independently counted recursive node visits."""
    bindings, visited = {}, 0

    def visit(p, ground):
        nonlocal visited
        visited += 1
        if p[1] != ground[1]:
            return False
        if p[0] == "var":
            key = (p[1], p[2])
            if key in bindings:
                return bindings[key] == ground
            bindings[key] = ground
            return True
        if p[2] != ground[2] or len(p[3]) != len(ground[3]):
            return False
        for child, actual in zip(p[3], ground[3]):
            if not visit(child, actual):
                return False
        return True

    accepted = visit(pattern, frozen_term(value))
    return accepted, visited


def oracle_or(patterns, value):
    """Each alternative has its own variable scope, with ordinary OR short circuit."""
    work = 1  # Adapter entry for this complete case.
    for pattern in patterns:
        accepted, cost = oracle_match(pattern, value)
        work += 1 + cost  # Explicit OR alternative, then recursive match.
        if accepted:
            return True, work
    return False, work


def partitions(items):
    """Every unordered nonempty-block partition, once, by recursive insertion."""
    if not items:
        yield ()
        return
    first, *remaining = items
    for suffix in partitions(remaining):
        yield ((first,),) + suffix
        for index in range(len(suffix)):
            yield suffix[:index] + ((first,) + suffix[index],) + suffix[index + 1:]


def partition_key(blocks):
    return tuple(sorted(tuple(sorted(block)) for block in blocks))


def oracle_candidates(positive, negative):
    """Enumerate the test language; production selection is never an input."""
    rows = {row["id"]: row["term"] for row in positive}
    result = {}
    for blocks in partitions(tuple(rows)):
        patterns = tuple(oracle_lgg([rows[key] for key in block]) for block in blocks)
        outcomes = {
            row["id"]: oracle_or(patterns, row["term"])[0]
            for row in positive + negative
        }
        result[partition_key(blocks)] = dict(patterns=patterns, outcomes=outcomes)
    return result


def oracle_size(value):
    """One node for every data container or scalar, excluding mapping keys."""
    if isinstance(value, dict):
        children = value.values()
    elif isinstance(value, (list, tuple)):
        children = value
    else:
        return 1
    return 1 + sum(oracle_size(child) for child in children)


def oracle_profile(candidate, positive, negative):
    """A duplicated labelled ground term is a single evidence factor."""
    terms = {row["id"]: frozen_term(row["term"]) for row in positive + negative}
    profile = dict(explained=set(), contradicted=set(), unknown=set())
    for row in candidate["examples"]:
        factor = (row["expected"], terms[row["id"]])
        if row["status"] == "UNCOMPUTED":
            relation = "unknown"
        elif (row["status"] == "MATCH") == (row["expected"] == "POSITIVE"):
            relation = "explained"
        else:
            relation = "contradicted"
        profile[relation].add(factor)
    return profile


def oracle_pareto(candidates, positive, negative):
    profiles = {row["id"]: oracle_profile(row, positive, negative) for row in candidates}

    def dominates(left, right):
        a, b = profiles[left["id"]], profiles[right["id"]]
        if a["unknown"] or b["unknown"]:
            return False
        weak = (
            a["explained"] >= b["explained"]
            and a["contradicted"] <= b["contradicted"]
            and left["complexity"] <= right["complexity"]
            and left["work"] <= right["work"]
        )
        strict = (
            a != b or left["complexity"] < right["complexity"]
            or left["work"] < right["work"]
        )
        return weak and strict

    return {
        row["id"] for row in candidates
        if not any(other["id"] != row["id"] and dominates(other, row) for other in candidates)
    }


def renamed_term(value, prefix):
    return term(
        prefix + value["symbol"],
        *(renamed_term(child, prefix) for child in value["arguments"]),
        sort=prefix + value["sort"],
    )


class IndependentRepairOracleTests(unittest.TestCase):
    def test_recursive_partition_enumerator_has_bell_counts_and_no_duplicates(self):
        for count, bell in enumerate((1, 1, 2, 5, 15, 52)):
            with self.subTest(count=count):
                actual = list(partitions(tuple(range(count))))
                self.assertEqual(len(actual), bell)
                self.assertEqual(len({partition_key(value) for value in actual}), bell)
                for value in actual:
                    self.assertEqual(sorted(x for block in value for x in block), list(range(count)))
                    self.assertTrue(all(value))

    def test_fixture_has_fifteen_partitions_four_feasible_and_unique_two_block_minimum(self):
        positive, negative = repair_fixture()
        candidates = oracle_candidates(positive, negative)
        feasible = [
            partition for partition, candidate in candidates.items()
            if all(candidate["outcomes"][row["id"]] for row in positive)
            and not any(candidate["outcomes"][row["id"]] for row in negative)
        ]
        self.assertEqual(len(candidates), 15)
        self.assertEqual(len(feasible), 4)
        self.assertEqual(sorted(map(len, feasible)), [2, 3, 3, 4])
        self.assertEqual(
            [partition for partition in feasible if len(partition) == 2],
            [(("p-a", "p-b"), ("p-c", "p-d"))],
        )
        broad = candidates[(("p-a", "p-b", "p-c", "p-d"),)]
        self.assertTrue(all(broad["outcomes"].values()))

    def test_oracle_reuses_correlated_disagreements_and_counts_short_circuit(self):
        pattern = oracle_lgg([
            term("pair", term("a"), term("a")),
            term("pair", term("b"), term("b")),
        ])
        self.assertEqual(pattern[3][0], pattern[3][1])
        self.assertEqual(oracle_match(pattern, term("pair", term("new"), term("new"))), (True, 3))
        self.assertEqual(oracle_match(pattern, term("pair", term("new"), term("other"))), (False, 3))
        self.assertEqual(oracle_match(pattern, term("other", term("new"), term("new"))), (False, 1))
        self.assertEqual(oracle_or((pattern, pattern), term("pair", term("new"), term("new"))), (True, 5))


class ConceptRepairOracleContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Deliberately no production LGG, matcher, partition enumerator, size,
        # factor-profile or Pareto helper is imported into this oracle.
        from hcl.operators.concept_repairs import repair_examples
        cls.repair = staticmethod(repair_examples)

    def assert_complete_candidate(self, candidate, positive, negative):
        supplied = {row["id"]: ("POSITIVE", row["term"]) for row in positive}
        supplied.update({row["id"]: ("NEGATIVE", row["term"]) for row in negative})
        self.assertEqual(len(candidate["examples"]), len(supplied))
        self.assertEqual({row["id"] for row in candidate["examples"]}, set(supplied))
        patterns = tuple(frozen_term(value) for value in candidate["patterns"])
        for row in candidate["examples"]:
            expected, value = supplied[row["id"]]
            self.assertEqual(row["expected"], expected)
            accepted = oracle_or(patterns, value)[0]
            self.assertEqual(row["status"], "MATCH" if accepted else "NO_MATCH")
        self.assertEqual(
            candidate["work"],
            sum(oracle_or(patterns, row["term"])[1] for row in positive + negative),
        )
        self.assertEqual(
            candidate["complexity"],
            oracle_size(dict(adapter="concept-partition-lgg-1", patterns=candidate["patterns"])),
        )
        profile = oracle_profile(candidate, positive, negative)
        for name in ("explained", "contradicted"):
            self.assertEqual(len(candidate["profile"][name]), len(profile[name]))
        self.assertFalse(candidate["profile"]["unmodeled"])
        self.assertFalse(candidate["profile"]["underspecified"])

    def test_all_partitions_actual_predictions_structure_cost_and_pareto_match_oracle(self):
        positive, negative = repair_fixture()
        before = deepcopy((positive, negative))
        actual = self.repair(positive, negative)
        self.assertEqual((positive, negative), before)
        self.assertTrue(actual["complete"])
        self.assertFalse(actual["frontier"])
        self.assertEqual(actual["candidate_completeness"], "EXHAUSTED_DECLARED_PARTITIONS")
        self.assertIsInstance(actual["schema"], str)
        self.assertTrue(actual["language"])
        expected = oracle_candidates(positive, negative)
        candidates = actual["candidates"]
        # Two distinct partitions have the same OR AST. The implementation
        # may share their prediction column, but must retain both witnesses.
        self.assertEqual(len(candidates), 14)
        self.assertEqual(len({row["id"] for row in candidates}), 14)
        by_partition = {
            partition_key(partition): row for row in candidates
            for partition in row["equivalent_partitions"]
        }
        self.assertEqual(sum(len(row["equivalent_partitions"]) for row in candidates), 15)
        for row in candidates:
            self.assertIn(partition_key(row["partition"]), {partition_key(p) for p in row["equivalent_partitions"]})
        self.assertEqual(set(by_partition), set(expected))
        for partition, candidate in by_partition.items():
            with self.subTest(partition=partition):
                self.assert_complete_candidate(candidate, positive, negative)
                self.assertEqual(
                    sorted(alpha_normalized(frozen_term(p)) for p in candidate["patterns"]),
                    sorted(alpha_normalized(p) for p in expected[partition]["patterns"]),
                )
                self.assertEqual(
                    {row["id"]: row["status"] == "MATCH" for row in candidate["examples"]},
                    expected[partition]["outcomes"],
                )
        self.assertEqual(set(actual["pareto_candidate_ids"]), oracle_pareto(candidates, positive, negative))
        feasible = [row for row in candidates if not oracle_profile(row, positive, negative)["contradicted"]]
        self.assertEqual(len(feasible), 4)
        minimum_cost = min(row["complexity"] for row in feasible)
        self.assertEqual(
            set(actual["minimum_consistent_candidate_ids"]),
            {row["id"] for row in feasible if row["complexity"] == minimum_cost},
        )
        minimum_blocks = {row["id"] for row in feasible if len(row["partition"]) == 2}
        self.assertEqual(len(minimum_blocks), 1)
        self.assertEqual(set(actual["minimum_consistent_block_candidate_ids"]), minimum_blocks)
        self.assertEqual(set(actual["minimum_consistent_candidate_ids"]), minimum_blocks)

    def test_minimum_or_predicts_fresh_constants_and_rejects_unseen_crossed_cases(self):
        positive, negative = repair_fixture()
        actual = self.repair(positive, negative)
        selected = set(actual["minimum_consistent_candidate_ids"])
        self.assertEqual(len(selected), 1)
        candidate = next(row for row in actual["candidates"] if row["id"] in selected)
        patterns = tuple(frozen_term(value) for value in candidate["patterns"])
        for mode, person, credential in product(
            ("standard", "emergency", "unseen-mode"),
            ("a", "b", "c", "d", "unseen-person", "另一个人"),
            ("signed", "waiver", "unseen-credential"),
        ):
            expected = (mode, credential) in {("standard", "signed"), ("emergency", "waiver")}
            with self.subTest(mode=mode, person=person, credential=credential):
                self.assertEqual(oracle_or(patterns, request(mode, person, credential))[0], expected)
        wrong_sort = request("standard", "unseen-person", "signed")
        wrong_sort["arguments"][1]["sort"] = "Credential"
        self.assertFalse(oracle_or(patterns, wrong_sort)[0])
        wrong_head = request("standard", "unseen-person", "signed")
        wrong_head["symbol"] = "unseen-request"
        self.assertFalse(oracle_or(patterns, wrong_head)[0])

    def test_identical_complete_term_on_both_sides_has_no_consistent_repair(self):
        positive, negative = repair_fixture()
        negative.append(example("n-conflicting-copy", deepcopy(positive[0]["term"])))
        actual = self.repair(positive, negative)
        self.assertTrue(actual["complete"])
        self.assertEqual(sum(len(row["equivalent_partitions"]) for row in actual["candidates"]), 15)
        self.assertFalse(actual["minimum_consistent_candidate_ids"])
        self.assertFalse(actual["minimum_consistent_block_candidate_ids"])
        for candidate in actual["candidates"]:
            self.assert_complete_candidate(candidate, positive, negative)
            outcomes = {row["id"]: row["status"] for row in candidate["examples"]}
            self.assertEqual(outcomes["p-a"], "MATCH")
            self.assertEqual(outcomes["n-conflicting-copy"], "MATCH")
            self.assertTrue(oracle_profile(candidate, positive, negative)["contradicted"])
        self.assertEqual(set(actual["pareto_candidate_ids"]), oracle_pareto(actual["candidates"], positive, negative))

    def test_reordered_examples_preserve_every_partition_and_generalization(self):
        positive, negative = repair_fixture()
        original = self.repair(positive, negative)

        def semantic_signature(result):
            return {
                partition_key(row["partition"]): (
                    tuple(sorted(alpha_normalized(frozen_term(p)) for p in row["patterns"])),
                    tuple(sorted((e["id"], e["expected"], e["status"]) for e in row["examples"])),
                    row["complexity"], row["work"],
                )
                for row in result["candidates"]
            }

        for order in permutations(positive):
            with self.subTest(order=[row["id"] for row in order]):
                actual = self.repair(list(order), list(reversed(negative)))
                self.assertTrue(actual["complete"])
                self.assertEqual(semantic_signature(actual), semantic_signature(original))
                self.assertEqual(set(actual["pareto_candidate_ids"]), set(original["pareto_candidate_ids"]))

    def test_example_labels_and_bijective_symbols_do_not_change_semantics(self):
        positive, negative = repair_fixture()
        original = self.repair(positive, negative)
        ids = {row["id"]: "renamed-" + str(9 - i) for i, row in enumerate(positive + negative)}
        reverse_ids = {new: old for old, new in ids.items()}
        transformed = [
            example(ids[row["id"]], renamed_term(row["term"], "ζ-"))
            for row in positive + negative
        ]
        actual = self.repair(list(reversed(transformed[:4])), list(reversed(transformed[4:])))
        self.assertTrue(actual["complete"])
        by_partition = {partition_key(row["partition"]): row for row in original["candidates"]}
        for candidate in actual["candidates"]:
            partition = partition_key([[reverse_ids[key] for key in block] for block in candidate["partition"]])
            old = by_partition[partition]
            self.assertEqual(candidate["complexity"], old["complexity"])
            self.assertEqual(
                {reverse_ids[row["id"]]: (row["expected"], row["status"]) for row in candidate["examples"]},
                {row["id"]: (row["expected"], row["status"]) for row in old["examples"]},
            )
            old_patterns = tuple(frozen_term(p) for p in old["patterns"])
            new_patterns = tuple(frozen_term(p) for p in candidate["patterns"])
            for mode, person, credential in product(("standard", "emergency"), ("fresh-a", "fresh-b"), ("signed", "waiver")):
                value = request(mode, person, credential)
                self.assertEqual(oracle_or(old_patterns, value)[0], oracle_or(new_patterns, renamed_term(value, "ζ-"))[0])

    def test_repeated_ground_support_does_not_create_new_partition_or_evidence_weight(self):
        positive, negative = repair_fixture()
        original = self.repair(positive, negative)
        duplicate_positive = positive + [example("p-repeat", deepcopy(positive[0]["term"]))]
        duplicate_negative = negative + [example("n-repeat", deepcopy(negative[0]["term"]))]
        repeated = self.repair(duplicate_positive, duplicate_negative)
        self.assertTrue(repeated["complete"])
        self.assertEqual(len(repeated["candidates"]), len(original["candidates"]))

        def by_patterns(result):
            groups = {}
            for row in result["candidates"]:
                key = tuple(sorted(alpha_normalized(frozen_term(p)) for p in row["patterns"]))
                groups.setdefault(key, []).append(row)
            return groups

        expected_groups, actual_groups = by_patterns(original), by_patterns(repeated)
        self.assertEqual(set(actual_groups), set(expected_groups))
        for key, candidates in actual_groups.items():
            self.assertEqual(len(candidates), len(expected_groups[key]))
            expected = expected_groups[key][0]
            for candidate in candidates:
                self.assert_complete_candidate(candidate, duplicate_positive, duplicate_negative)
                # Repeated reports still incur execution work, never an extra
                # evidence factor. Both costs are independently replayed above.
                self.assertGreater(candidate["work"], expected["work"])
                self.assertEqual(candidate["complexity"], expected["complexity"])
                self.assertEqual(
                    oracle_profile(candidate, duplicate_positive, duplicate_negative),
                    oracle_profile(expected, positive, negative),
                )
                outcomes = {row["id"]: row["status"] for row in candidate["examples"]}
                self.assertEqual(outcomes["p-repeat"], outcomes["p-a"])
                self.assertEqual(outcomes["n-repeat"], outcomes["n-e"])
        self.assertEqual(set(repeated["pareto_candidate_ids"]), oracle_pareto(repeated["candidates"], duplicate_positive, duplicate_negative))

    def test_nested_and_repeated_variables_cannot_be_repaired_into_wildcards(self):
        def pair(a, b):
            return term("envelope", term("pair", term(a), term(b)))

        positive = [example("p-a", pair("a", "a")), example("p-b", pair("b", "b"))]
        negative = [
            example("n-mixed", pair("a", "b")),
            example("n-new-diagonal", pair("c", "c")),
        ]
        actual = self.repair(positive, negative)
        self.assertTrue(actual["complete"])
        self.assertEqual(len(actual["candidates"]), 2)
        for candidate in actual["candidates"]:
            self.assert_complete_candidate(candidate, positive, negative)
            expected = [oracle_lgg([next(row["term"] for row in positive if row["id"] == key) for key in block]) for block in candidate["partition"]]
            self.assertEqual(
                sorted(alpha_normalized(frozen_term(p)) for p in candidate["patterns"]),
                sorted(alpha_normalized(p) for p in expected),
            )
        broad = next(row for row in actual["candidates"] if len(row["partition"]) == 1)
        patterns = tuple(frozen_term(p) for p in broad["patterns"])
        self.assertTrue(oracle_or(patterns, pair("fresh", "fresh"))[0])
        self.assertFalse(oracle_or(patterns, pair("fresh", "different"))[0])

    def test_small_binary_domain_repairs_match_independent_enumeration(self):
        # All four ways to reserve one negative from the Boolean pair domain.
        # None of these uses the request example's two semantic categories.
        ground = [term("pair", term(a), term(b)) for a, b in product("ab", repeat=2)]
        for positive_indexes in combinations(range(4), 3):
            positive = [example("p-" + str(i), ground[i]) for i in positive_indexes]
            negative = [example("n-" + str(i), ground[i]) for i in range(4) if i not in positive_indexes]
            with self.subTest(positive_indexes=positive_indexes):
                expected = oracle_candidates(positive, negative)
                actual = self.repair(positive, negative)
                self.assertTrue(actual["complete"])
                by_partition = {
                    partition_key(partition): row for row in actual["candidates"]
                    for partition in row["equivalent_partitions"]
                }
                self.assertEqual(set(by_partition), set(expected))
                self.assertEqual(len(by_partition), 5)
                for partition, candidate in by_partition.items():
                    self.assert_complete_candidate(candidate, positive, negative)
                    self.assertEqual(
                        sorted(alpha_normalized(frozen_term(p)) for p in candidate["patterns"]),
                        sorted(alpha_normalized(p) for p in expected[partition]["patterns"]),
                    )
                self.assertEqual(set(actual["pareto_candidate_ids"]), oracle_pareto(actual["candidates"], positive, negative))
                feasible = [row for row in actual["candidates"] if not oracle_profile(row, positive, negative)["contradicted"]]
                self.assertTrue(feasible)
                cost = min(row["complexity"] for row in feasible)
                self.assertEqual(set(actual["minimum_consistent_candidate_ids"]), {row["id"] for row in feasible if row["complexity"] == cost})

    def test_five_distinct_positives_cover_all_fifty_two_partitions(self):
        positive, negative = repair_fixture()
        positive.append(example("p-g", request("standard", "g", "signed")))
        actual = self.repair(positive, negative)
        expected = oracle_candidates(positive, negative)
        self.assertTrue(actual["complete"])
        by_partition = {
            partition_key(partition): row for row in actual["candidates"]
            for partition in row["equivalent_partitions"]
        }
        self.assertEqual(len(expected), 52)
        self.assertEqual(set(by_partition), set(expected))
        self.assertEqual(sum(len(row["equivalent_partitions"]) for row in actual["candidates"]), 52)
        for partition, candidate in by_partition.items():
            self.assert_complete_candidate(candidate, positive, negative)
            self.assertEqual(
                sorted(alpha_normalized(frozen_term(p)) for p in candidate["patterns"]),
                sorted(alpha_normalized(p) for p in expected[partition]["patterns"]),
            )
        self.assertEqual(set(actual["pareto_candidate_ids"]), oracle_pareto(actual["candidates"], positive, negative))

    def test_no_counterexample_leaves_consistent_base_without_gratuitous_repairs(self):
        positive, _ = repair_fixture()
        negative = [example("n-wrong-root", term("not-request", sort="Request"))]
        actual = self.repair(positive, negative)
        self.assertTrue(actual["complete"])
        self.assertFalse(actual["triggered_by"])
        self.assertEqual(len(actual["candidates"]), 1)
        candidate = actual["candidates"][0]
        self.assertEqual(len(candidate["partition"]), 1)
        self.assert_complete_candidate(candidate, positive, negative)
        self.assertEqual(actual["status"], "NO_DECLARED_COUNTEREXAMPLE")
        self.assertEqual(actual["candidate_completeness"], "NOT_SEARCHED_NO_COUNTEREXAMPLE")
        self.assertFalse(actual["minimum_consistent_candidate_ids"])
        self.assertFalse(actual["minimum_consistent_block_candidate_ids"])

    def test_equal_cost_repair_tie_survives_with_distinct_out_of_sample_predictions(self):
        def triple(bits):
            return term(
                "tuple3", *(term(str(i) + bit, sort="Slot" + str(i)) for i, bit in enumerate(bits)),
                sort="Tuple",
            )

        positive = [example("p-" + bits, triple(bits)) for bits in ("aaa", "abb", "bab")]
        negative = [example("n-aba", triple("aba"))]
        actual = self.repair(positive, negative)
        expected = oracle_candidates(positive, negative)
        self.assertTrue(actual["complete"])
        self.assertEqual(actual["candidate_completeness"], "EXHAUSTED_DECLARED_PARTITIONS")
        by_partition = {
            partition_key(partition): row for row in actual["candidates"]
            for partition in row["equivalent_partitions"]
        }
        self.assertEqual(set(by_partition), set(expected))
        for partition, candidate in by_partition.items():
            self.assert_complete_candidate(candidate, positive, negative)
            self.assertEqual(
                sorted(alpha_normalized(frozen_term(p)) for p in candidate["patterns"]),
                sorted(alpha_normalized(p) for p in expected[partition]["patterns"]),
            )
        first_key = partition_key((("p-aaa", "p-bab"), ("p-abb",)))
        second_key = partition_key((("p-aaa",), ("p-abb", "p-bab")))
        first, second = by_partition[first_key], by_partition[second_key]
        tied_ids = {first["id"], second["id"]}
        self.assertEqual(len(tied_ids), 2)
        for candidate in (first, second):
            # The numbers are independently recomputed in assert_complete_candidate.
            # This is a genuine tie in coverage, structure AND execution cost.
            self.assertEqual((candidate["complexity"], candidate["work"]), (41, 35))
            self.assertTrue(candidate["consistent"])
            self.assertFalse(oracle_profile(candidate, positive, negative)["contradicted"])
        self.assertEqual(oracle_profile(first, positive, negative), oracle_profile(second, positive, negative))
        self.assertEqual(set(actual["minimum_consistent_candidate_ids"]), tied_ids)
        self.assertEqual(set(actual["minimum_consistent_block_candidate_ids"]), tied_ids)
        self.assertLessEqual(tied_ids, set(actual["pareto_candidate_ids"]))
        self.assertEqual(set(actual["pareto_candidate_ids"]), oracle_pareto(actual["candidates"], positive, negative))
        self.assertFalse(actual["adopted"])

        # These complete new cases are neither training positives nor negatives.
        # Both candidates fit the training observations yet disagree in both
        # directions on the independently enumerated eight-case domain.
        first_patterns = tuple(frozen_term(p) for p in first["patterns"])
        second_patterns = tuple(frozen_term(p) for p in second["patterns"])
        domain = {"".join(bits): triple(bits) for bits in product("ab", repeat=3)}
        predictions = {
            bits: (oracle_or(first_patterns, value)[0], oracle_or(second_patterns, value)[0])
            for bits, value in domain.items()
        }
        self.assertEqual(predictions["baa"], (True, False))
        self.assertEqual(predictions["bbb"], (False, True))
        self.assertEqual(
            {bits for bits, pair in predictions.items() if pair[0] != pair[1]},
            {"baa", "bbb"},
        )
        classes = actual["discovery"]["prediction_classes"]
        shared = [row for row in classes if tied_ids <= set(row["members"])]
        self.assertEqual(len(shared), 1)
        self.assertEqual(shared[0]["status"], "EQUIVALENT_ON_DECLARED_OBLIGATIONS")
        self.assertEqual(shared[0]["scope"], actual["discovery"]["equivalence_scope"])
        self.assertTrue(shared[0]["scope"])
        self.assertFalse(actual["discovery"]["semantic_certified"])
        self.assertEqual(actual["discovery"]["posterior"], "NOT_CALIBRATED")

    def test_prediction_equivalence_scope_binds_changed_negative_ground_terms(self):
        positive, negative = repair_fixture()
        first = self.repair(positive, negative)
        changed = deepcopy(negative)
        changed[0]["term"]["arguments"][1]["symbol"] = "unseen-negative-person"
        second = self.repair(positive, changed)
        self.assertTrue(first["complete"] and second["complete"])

        # The new negative deliberately leaves every computed prediction the
        # same. That does not make the two sets of tested obligations identical.
        def predictions(result):
            return {
                row["id"]: tuple((case["id"], case["expected"], case["status"]) for case in row["examples"])
                for row in result["candidates"]
            }

        self.assertEqual(predictions(first), predictions(second))
        first_scope = first["discovery"]["equivalence_scope"]
        second_scope = second["discovery"]["equivalence_scope"]
        self.assertTrue(first_scope["comparison_identity"])
        self.assertNotEqual(first_scope["comparison_identity"], second_scope["comparison_identity"])
        self.assertNotEqual(first_scope, second_scope)
        first_classes = {
            tuple(row["members"]): row for row in first["discovery"]["prediction_classes"]
        }
        second_classes = {
            tuple(row["members"]): row for row in second["discovery"]["prediction_classes"]
        }
        self.assertEqual(set(first_classes), set(second_classes))
        for members, first_class in first_classes.items():
            second_class = second_classes[members]
            self.assertNotEqual(first_class["class_id"], second_class["class_id"])
            self.assertEqual(first_class["scope"], first_scope)
            self.assertEqual(second_class["scope"], second_scope)
            self.assertEqual(first_class["status"], "EQUIVALENT_ON_DECLARED_OBLIGATIONS")
            self.assertEqual(second_class["status"], "EQUIVALENT_ON_DECLARED_OBLIGATIONS")

    def test_invalid_ground_examples_identity_sorts_and_budget_are_rejected(self):
        positive, negative = repair_fixture()
        invalid_examples = [
            ([], negative),
            (positive + [deepcopy(positive[0])], negative),
            (positive, negative + [example(positive[0]["id"], negative[0]["term"])]),
            ([example("p", None)], []),
            ([example("p", dict(kind="VARIABLE", sort="Request", id="answer"))], []),
            ([example("p", term("same", sort="One"))], [example("n", term("same", sort="Two"))]),
            ([example("p", term("one", sort="One"))], [example("n", term("two", sort="Two"))]),
            (positive + [example("p-" + str(i), request("standard", str(i), "signed")) for i in range(2)], negative),
        ]
        for index, (pos, neg) in enumerate(invalid_examples):
            with self.subTest(invalid_examples=index), self.assertRaises(ValueError):
                self.repair(pos, neg)
        for budget in (-1, True, 1.0, 1000001):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                self.repair(positive, negative, max_work=budget)

    def test_budget_frontier_never_certifies_global_minimum_or_fabricates_predictions(self):
        positive, negative = repair_fixture()
        full = self.repair(positive, negative)
        self.assertGreater(full["work"], 0)
        budgets = sorted({0, 1, 2, 5, 13, 31, 67, 127, full["work"] // 2, full["work"] - 1, full["work"]})
        inputs = {row["id"]: row["term"] for row in positive + negative}
        for budget in budgets:
            with self.subTest(budget=budget):
                actual = self.repair(positive, negative, max_work=budget)
                self.assertLessEqual(actual["work"], budget)
                self.assertEqual(actual["complete"], not bool(actual["frontier"]))
                if actual["complete"]:
                    self.assertEqual(actual, full)
                else:
                    self.assertEqual(actual["candidate_completeness"], "PARTIAL_DECLARED_PARTITIONS")
                    self.assertFalse(actual["minimum_consistent_candidate_ids"])
                    self.assertFalse(actual["minimum_consistent_block_candidate_ids"])
                for candidate in actual["candidates"]:
                    self.assertEqual(len(candidate["examples"]), len(inputs))
                    self.assertEqual({row["id"] for row in candidate["examples"]}, set(inputs))
                    patterns = tuple(frozen_term(p) for p in candidate["patterns"])
                    for row in candidate["examples"]:
                        self.assertIn(row["status"], {"MATCH", "NO_MATCH", "UNCOMPUTED"})
                        if row["status"] != "UNCOMPUTED":
                            accepted = oracle_or(patterns, inputs[row["id"]])[0]
                            self.assertEqual(row["status"], "MATCH" if accepted else "NO_MATCH")
                self.assertEqual(set(actual["pareto_candidate_ids"]), oracle_pareto(actual["candidates"], positive, negative))


if __name__ == "__main__":
    unittest.main()
