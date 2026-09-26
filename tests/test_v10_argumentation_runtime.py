import unittest
from dataclasses import replace
from itertools import product
from hcl.v04.model import EventRecord
from hcl.v10 import Argument, Attack, ArgumentFramework, HCLV10Runtime, SCOPE


def framework(ids=("A", "B", "C"), edges=(("A", "B"), ("B", "C"))):
    return ArgumentFramework(
        "f",
        "s",
        tuple(Argument(a, a) for a in ids),
        tuple(Attack(a, b, a + " attacks " + b) for a, b in edges),
    )


def event(**kw):
    return EventRecord(
        event_id="s",
        source_id="public-independent-fixture",
        raw_text="A B C A attacks B B attacks C",
        valid_time="2026-01-02T00:00:00+00:00",
        recorded_at="2026-01-03T00:00:00+00:00",
        metadata={"argumentation_scope": SCOPE, "reader_only": True},
        **kw
    )


# Independent three-valued legal-labelling oracle; no set-defense solver call.
def reference_labels(ids, edges):
    rows = []
    for values in product(("IN", "OUT", "UNDEC"), repeat=len(ids)):
        d = dict(zip(ids, values))
        valid = True
        for a in ids:
            attackers = [d[x] for x, y in edges if y == a]
            expected = (
                "OUT"
                if "IN" in attackers
                else "IN" if all(v == "OUT" for v in attackers) else "UNDEC"
            )
            if d[a] != expected:
                valid = False
                break
        if valid:
            rows.append(
                {
                    label: sorted(a for a in ids if d[a] == label)
                    for label in ("IN", "OUT", "UNDEC")
                }
            )
    return sorted(rows, key=lambda x: x["IN"])


class ArgumentationTests(unittest.TestCase):
    def test_chain_defeats_defeater(self):
        f = framework()
        self.assertEqual(f.grounded()[0], {"IN": ["A", "C"], "OUT": ["B"], "UNDEC": []})
        self.assertEqual(len(f.grounded()[1]), 3)

    def test_mutual_attack_keeps_alternatives(self):
        f = framework(("A", "B"), (("A", "B"), ("B", "A")))
        self.assertEqual(f.grounded()[0]["UNDEC"], ["A", "B"])
        self.assertEqual(
            [x["IN"] for x in f.extensions("complete")], [[], ["A"], ["B"]]
        )
        r = f.analyse("preferred", "A")
        self.assertTrue(r["credulous"])
        self.assertFalse(r["skeptical"])

    def test_odd_cycle_no_stable_extension_no_vacuous_skepticism(self):
        f = framework(edges=(("A", "B"), ("B", "C"), ("C", "A")))
        r = f.analyse("stable", "A")
        self.assertEqual(r["status"], "NO_EXTENSION")
        self.assertIsNone(r["skeptical"])
        self.assertIsNone(r["credulous"])
        self.assertEqual(f.grounded()[0]["UNDEC"], ["A", "B", "C"])

    def test_self_attack_never_accepted(self):
        f = framework(("A",), (("A", "A"),))
        self.assertEqual(
            f.extensions("complete"), [{"IN": [], "OUT": [], "UNDEC": ["A"]}]
        )

    def test_isolated_argument_skeptically_accepted(self):
        r = framework(edges=(("A", "B"), ("B", "A"))).analyse("preferred", "C")
        self.assertTrue(r["skeptical"])
        self.assertTrue(r["credulous"])
        self.assertTrue(r["not_moral_verdict"])

    def test_all_three_node_graphs_independent_legal_labels(self):
        ids = ("A", "B", "C")
        edges = list(product(ids, repeat=2))
        for mask in range(1 << len(edges)):
            chosen = tuple(e for j, e in enumerate(edges) if mask & (1 << j))
            f = framework(ids, chosen)
            complete = reference_labels(ids, chosen)
            self.assertEqual(f.extensions("complete"), complete)
            least = set.intersection(*(set(x["IN"]) for x in complete))
            self.assertEqual(set(f.grounded()[0]["IN"]), least)
            pref = [
                x
                for x in complete
                if not any(set(x["IN"]) < set(y["IN"]) for y in complete)
            ]
            self.assertEqual(f.extensions("preferred"), pref)
            self.assertEqual(
                f.extensions("stable"), [x for x in complete if not x["UNDEC"]]
            )

    def test_caps_duplicates_unknown_endpoints_and_scope(self):
        for args in [
            dict(arguments=[Argument("A", "A")]),
            dict(arguments=tuple(Argument(str(i), str(i)) for i in range(13))),
            dict(arguments=(Argument("A", "A"), Argument("A", "A"))),
            dict(attacks=(Attack("Z", "A", "Z"),)),
            dict(attacks=(Attack("A", "B", "q"), Attack("A", "B", "r"))),
            dict(scope="GUESSED_SOCIAL_TRUTH"),
        ]:
            with self.assertRaises(ValueError):
                replace(framework(), **args)
        with self.assertRaises(ValueError):
            framework().analyse("majority_vote")
        with self.assertRaises(ValueError):
            framework().analyse(target="Z")

    def test_unseen_source_requires_context(self):
        rt = HCLV10Runtime()
        self.assertEqual(rt.analyse("f")["status"], "SYSTEM_INSUFFICIENT")
        with self.assertRaises(ValueError):
            rt.ingest_framework(framework())

    def test_binding_atomicity_and_replay(self):
        rt = HCLV10Runtime()
        rt.ingest_event(event())
        with self.assertRaises(ValueError):
            rt.ingest_framework(
                replace(framework(), attacks=(Attack("A", "B", "not present"),))
            )
        self.assertEqual(rt.answer_context("f")["frameworks"], [])
        self.assertTrue(rt.ingest_framework(framework()))
        self.assertFalse(rt.ingest_framework(framework()))
        with self.assertRaises(ValueError):
            rt.ingest_framework(replace(framework(), attacks=()))
        self.assertEqual(rt.analyse("f")["grounded"]["IN"], ["A", "C"])

    def test_private_source_no_trace_leak(self):
        rt = HCLV10Runtime()
        rt.ingest_event(event())
        rt.ingest_framework(framework())
        r = rt.analyse("f", target="A", viewer_agent_id="outsider")
        self.assertEqual(r["status"], "SYSTEM_INSUFFICIENT")
        self.assertEqual(r["grounded_steps"], [])
        self.assertIsNone(r["credulous"])

    def test_bitemporal_cuts(self):
        rt = HCLV10Runtime()
        rt.ingest_event(event())
        rt.ingest_framework(framework())
        for kw in [
            dict(event_time="2026-01-01T00:00:00+00:00"),
            dict(knowledge_cutoff="2026-01-02T00:00:00+00:00"),
        ]:
            self.assertEqual(rt.analyse("f", **kw)["status"], "SYSTEM_INSUFFICIENT")
        self.assertEqual(
            rt.analyse(
                "f",
                event_time="2026-01-02T00:00:00+00:00",
                knowledge_cutoff="2026-01-03T00:00:00+00:00",
            )["status"],
            "EXTENSIONS_AVAILABLE",
        )

    def test_context_detached_no_silent_revision(self):
        rt = HCLV10Runtime()
        rt.ingest_event(event())
        rt.ingest_framework(framework())
        ctx = rt.answer_context("f")
        ctx["frameworks"][0]["arguments"][0]["argument_id"] = "CHANGED"
        self.assertEqual(rt.analyse("f")["grounded"]["IN"], ["A", "C"])
        self.assertEqual(rt.answer_context("unknown")["status"], "SYSTEM_INSUFFICIENT")


if __name__ == "__main__":
    unittest.main()
