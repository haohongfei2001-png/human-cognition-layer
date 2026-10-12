"""Isolated synthetic lineage checks; no erasure API or real-data deletion."""
from dataclasses import replace
import unittest

from hcl.kernel.dependencies import QuerySnapshot
from hcl.kernel.execution import ExecutionCheckpoint, LocalModel, PROTOCOL
from hcl.kernel.types import AccessPolicy, Principal, Snapshot, SourceDocument, SourceHandle
from hcl.memory.lineage import encoded_bindings, retained_bindings, source_token
from hcl.kernel.retrieval import RETRIEVAL_VERSION


class RetainedLineageTests(unittest.TestCase):
    def snapshot(self, source, version=1, session="s"):
        original = SourceDocument(SourceHandle(source, version), "Synthetic private material.",
                                  AccessPolicy("t", frozenset({"a"})))
        return Snapshot(session, Principal("t", "a"), 1, 0, "hcl-rule-1",
                        {source: version}, {}, {source: original})

    def test_failed_unused_checkpoint_branches_retain_exact_source_versions(self):
        a, b = self.snapshot("A", 1), self.snapshot("B", 2)
        model = LocalModel("m", "finite-interpretation-1", {}, {"C": 3})
        checkpoint = ExecutionCheckpoint(PROTOCOL, "owner", "RUNNING",
            {"failed": {"snapshot": a, "state": "FAILED", "previous_results": (model,)},
             "used": {"snapshot": b}}, (), {}, {"values": {"a": a, "b": b}})
        self.assertEqual(retained_bindings(checkpoint, session_id="s"),
                         frozenset({("s", "A", 1), ("s", "B", 2), ("s", "C", 3)}))
        # A minimal final delivery referring only to B cannot replace this set.
        self.assertNotEqual(retained_bindings(b, session_id="s"), retained_bindings(checkpoint, session_id="s"))

    def test_retrieval_statistics_scope_includes_unselected_material(self):
        base = self.snapshot("selected")
        snapshot = QuerySnapshot(base.session_id, base.principal, base.revision, base.access_epoch,
            base.rule_version, base.source_versions, {}, base.immutable_views, (),
            {"q": {"schema": RETRIEVAL_VERSION,
                   "search_scope": {"selected": {"version": 1}, "unread": {"version": 7}},
                   "coverage": {"read_regions": [{"source_id": "selected"}]}}})
        self.assertEqual(retained_bindings(snapshot, session_id="s"),
                         frozenset({("s", "selected", 1), ("s", "unread", 7)}))

    def test_historical_empty_positive_map_and_nested_session_remain_bound(self):
        source = self.snapshot("A", 4, "past")
        historical = QuerySnapshot("past", source.principal, 10, 0, source.rule_version,
            {}, {}, source.immutable_views, (), {}, {"A": {"source_id": "A", "source_version": 4}})
        self.assertEqual(retained_bindings({"old": historical, "new": self.snapshot("A", 5)}, session_id="s"),
                         frozenset({("past", "A", 4), ("s", "A", 5)}))

    def test_no_string_or_model_mapping_key_invents_provenance(self):
        forged = {"source_id": "A", "source_versions": {"B": 2}, "text": "C version 3"}
        self.assertFalse(retained_bindings(forged, session_id="s"))
        cyclic = []
        cyclic.append(cyclic)
        self.assertFalse(retained_bindings(cyclic, session_id="s"))

    def test_opaque_tombstone_binding_is_session_salted_and_version_preserving(self):
        salt = b"a" * 32
        secret = "SOURCE_NAME_PRIVATE_CANARY"
        token = source_token(salt, "s", secret)
        self.assertEqual(len(token), 64)
        self.assertNotIn(secret, token)
        self.assertNotEqual(token, source_token(b"b" * 32, "s", secret))
        self.assertNotEqual(token, source_token(salt, "other", secret))
        self.assertEqual(encoded_bindings(salt, (("s", secret, 1), ("s", secret, 2))),
                         (("s", token, 1), ("s", token, 2)))


if __name__ == "__main__":
    unittest.main()
