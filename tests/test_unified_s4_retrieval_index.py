import unittest
from dataclasses import replace

from hcl.kernel.types import AccessPolicy, SourceDocument, SourceHandle, thaw
from hcl.memory.index import build_index, terms, validate_index
from hcl.semantics.segments import iter_segments


class RetrievalIndexTests(unittest.TestCase):
    def source(self, text):
        return SourceDocument(SourceHandle("chapter", 1), text, AccessPolicy("t", frozenset({"a"})))

    def test_exact_unicode_regions_and_coverage(self):
        for text in ("", "a\r\nb。 c!\n末尾没有标点", "é 𝛼.\n" * 1000):
            source = self.source(text)
            result = build_index(source)
            segments = tuple(iter_segments(text, "chapter", 1, "SOURCE"))
            self.assertEqual(len(result["regions"]), len(segments))
            for row, segment in zip(result["regions"], segments):
                self.assertEqual(row["segment_id"], segment.segment_id)
                self.assertEqual(text[row["start"]:row["end"]], segment.text)
                self.assertEqual(text.encode()[row["byte_start"]:row["byte_end"]].decode(), segment.text)
            self.assertTrue(result["complete"])
            self.assertEqual(validate_index(result, source), result)
            self.assertEqual(result["semantic_coverage"], "NOT_ESTABLISHED")

    def test_limit_does_not_hide_unknown_tail(self):
        source = self.source("support.\nnot support.\n")
        result = build_index(source, max_regions=1)
        self.assertFalse(result["complete"])
        self.assertEqual(result["indexed_end"], len("support.\n"))
        self.assertEqual(validate_index(result, source), result)
        for change in ({"complete": True}, {"indexed_end": len(source.text)}):
            altered = thaw(result)
            altered.update(change)
            with self.assertRaises(ValueError):
                validate_index(altered, source)

    def test_tokens_and_changed_source_or_cache_reject(self):
        self.assertEqual(terms("CAN'T. 猫吃鱼"), ("can't", "猫", "吃", "鱼", "猫吃", "吃鱼"))
        source = self.source("A cause. A contrary cause.")
        index = build_index(source)
        with self.assertRaises(ValueError):
            validate_index(index, replace(source, text="A cause."))
        changed = thaw(index)
        changed["regions"][0]["counts"]["forged"] = 1
        with self.assertRaises(ValueError):
            validate_index(changed, source)
        with self.assertRaises(UnicodeEncodeError):
            terms("\ud800")

    def test_supplementary_cjk_precedes_python_unicode_word_categories(self):
        for run in ("𠀀𠀁𠀂", "\U00031350\U00031351\U00031352",
                    "\U0002ee50\U0002ee51\U0002ee52", "\U00033470\U00033471\U00033472"):
            self.assertEqual(terms("Before " + run + " AFTER"),
                             ("before", *run, run[:2], run[1:], "after"))
            indexed = build_index(self.source(run + "."))
            self.assertEqual(indexed["regions"][0]["counts"][run[:2]], 1)


if __name__ == "__main__":
    unittest.main()
