"""Literal-pattern independent oracle; no semantic/aesthetic answer fixtures."""

import random
import unittest

from hcl.operators.narrative_form import PUNCTUATION, measure_form


class NarrativeFormTests(unittest.TestCase):
    def test_unicode_overlaps_linebreaks_and_punctuation_are_exact(self):
        text = "aaaa “秘密秘密”\r\nα𝄞.\n"
        result = measure_form(
            [dict(id="p", text=text)],
            dict(overlap="aa", motif="秘密", supplementary="𝄞"),
            10000,
        )
        row = result["passages"][0]
        self.assertEqual(row["motif_positions"]["overlap"], [0, 1, 2])
        self.assertEqual(
            row["motif_positions"]["motif"],
            [text.index("秘密"), text.index("秘密") + 2],
        )
        self.assertEqual(row["total_utf8_bytes"], len(text.encode()))
        self.assertEqual(
            row["linebreak_positions"], [i for i, c in enumerate(text) if c == "\n"]
        )
        self.assertFalse(result["frontier"])

    def test_random_literal_positions_match_independent_naive_oracle(self):
        rng = random.Random(191)
        for case in range(250):
            text = "".join(rng.choice("aab秘密𝄞。\n") for _ in range(rng.randrange(50)))
            motifs = {
                str(i): "".join(
                    rng.choice("ab秘密𝄞。") for _ in range(rng.randrange(1, 7))
                )
                for i in range(5)
            }
            result = measure_form([dict(id="p", text=text)], motifs, 100000)
            row = result["passages"][0]
            for key, pattern in motifs.items():
                expected = [i for i in range(len(text)) if text.startswith(pattern, i)]
                self.assertEqual(row["motif_positions"][key], expected, (case, key))
            self.assertEqual(
                row["punctuation"],
                {char: text.count(char) for char in set(text) & set(PUNCTUATION)},
            )
            self.assertEqual(row["scanned_characters"], len(text))

    def test_every_small_budget_keeps_known_prefix_and_explicit_unread_scope(self):
        passages = [
            dict(id="early", text="aaaaa。"),
            dict(id="distant", text="Distant counterevidence."),
        ]
        motifs = dict(a="aa", denial="counterevidence")
        full = measure_form(passages, motifs, 10000)
        for budget in range(full["work"] + 2):
            result = measure_form(passages, motifs, budget)
            self.assertLessEqual(result["work"], budget)
            for source, row in zip(passages, result["passages"]):
                prefix = source["text"][: row["scanned_characters"]]
                for key, pattern in motifs.items():
                    expected = [
                        i for i in range(len(prefix)) if prefix.startswith(pattern, i)
                    ]
                    self.assertEqual(row["motif_positions"][key], expected)
                self.assertEqual(
                    row["unread_range"], (len(prefix), len(source["text"]))
                )
            if budget < full["work"]:
                self.assertTrue(result["frontier"])
            else:
                self.assertFalse(result["frontier"])


if __name__ == "__main__":
    unittest.main()
