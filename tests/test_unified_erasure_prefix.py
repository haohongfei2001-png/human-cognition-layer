"""A new cutover starts at its actual already-redacted source checkpoint."""

import json
import sqlite3
import unittest

from hcl.memory.erasure import authorized_prefix, semantic_hash


class ErasurePrefixTests(unittest.TestCase):
    @staticmethod
    def event(text):
        return dict(
            seq=1,
            session_id="s",
            revision=1,
            kind="test",
            payload=json.dumps({"value": text}),
        )

    def verify(self, original, current, changes):
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        db.execute("CREATE TABLE erasures(erasure_id TEXT,targets TEXT)")
        for number, items in enumerate(changes):
            db.execute(
                "INSERT INTO erasures VALUES(?,?)",
                (
                    str(number),
                    json.dumps(dict(plan={"revision": number}, event_changes=items)),
                ),
            )
        return authorized_prefix(db, [original], [current])

    def test_unchanged_or_contiguous_changes_after_inherited_baseline(self):
        a, b, c = (self.event(name) for name in "abc")
        first = dict(seq=1, before=semantic_hash(a), after=semantic_hash(b))
        second = dict(seq=1, before=semantic_hash(b), after=semantic_hash(c))
        self.assertTrue(self.verify(a, c, [[first], [second]]))
        self.assertTrue(self.verify(b, c, [[first], [second]]))
        self.assertTrue(self.verify(b, b, [[first]]))
        self.assertTrue(self.verify(c, c, [[first], [second]]))

    def test_equal_target_cannot_rollback_a_recorded_postbaseline_erasure(self):
        a, b, c = (self.event(name) for name in "abc")
        first = dict(seq=1, before=semantic_hash(a), after=semantic_hash(b))
        second = dict(seq=1, before=semantic_hash(b), after=semantic_hash(c))
        self.assertFalse(self.verify(a, a, [[first]]))
        self.assertFalse(self.verify(b, b, [[first], [second]]))
        self.assertFalse(self.verify(a, b, [[first], [second]]))
        self.assertTrue(self.verify(c, c, [[first], [second]]))
        self.assertTrue(self.verify(a, a, []))

    def test_unrecorded_or_discontinuous_postbaseline_change_rejected(self):
        a, b, c, d = (self.event(name) for name in "abcd")
        first = dict(seq=1, before=semantic_hash(a), after=semantic_hash(b))
        wrong = dict(seq=1, before=semantic_hash(d), after=semantic_hash(c))
        self.assertFalse(self.verify(b, c, [[first]]))
        self.assertFalse(self.verify(a, c, [[first], [wrong]]))
        self.assertFalse(self.verify(b, c, [[first], [wrong]]))
        self.assertFalse(self.verify(c, b, [[first], [wrong]]))


if __name__ == "__main__":
    unittest.main()
