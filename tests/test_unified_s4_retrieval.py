from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import math
import tempfile
import unittest
from unittest.mock import patch

from hcl.kernel.retrieval import EvidenceNode, RetrievalQuery, ROUTES
from hcl.kernel.dependencies import pack_dependencies, unpack_dependencies
from hcl.kernel.types import Principal, HCLFailure
from hcl.memory import codec
from hcl.memory.index import build_index, terms
from hcl.memory.query_store import QueryStore
from hcl.memory.retrieval import rank_regions, recorded_closure
from hcl.memory.store import StateStore
from hcl.semantics.segments import iter_segments


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "state.sqlite"
        self.store = StateStore.sqlite(self.path, revision=True)
        self.owner = Principal("t", "a")
        self.store.create_session("s", self.owner, frozenset({"b"}))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def query(self, **kw):
        return RetrievalQuery(dict(support="witness event", challenge="denial not event", alternative="alternative cause"), **kw)

    def search(self, query=None):
        return QueryStore(self.store).search("s", self.owner, query or self.query())

    def test_acl_precedes_candidates_counts_and_vectors(self):
        self.store.put_source("s", self.owner, "visible", "A witness saw the event. Another alternative cause.")
        before = self.search()
        self.store.put_source("s", self.owner, "private", "PRIVATE_CANARY denial not event.\n"*100, readers=frozenset({"b"}))
        after = self.search()
        self.assertEqual(before.query_dependencies, after.query_dependencies)
        self.assertEqual(before.query_views, after.query_views)
        self.assertNotIn("PRIVATE_CANARY", codec.dumps(after).decode())
        for source in ("private", "missing"):
            with self.assertRaises(HCLFailure) as error:
                self.search(self.query(source_scope=(source,)))
            self.assertEqual(error.exception.status, "DENIED")

    def test_scope_membership_not_only_top_k_changes_dependency(self):
        self.store.put_source("s", self.owner, "a", "witness event event.")
        before = self.search(self.query(max_hits_per_route=1))
        self.store.put_source("s", self.owner, "z", "an unrelated unread sentence.")
        after = self.search(self.query(max_hits_per_route=1))
        self.assertEqual(before.source_versions, after.source_versions)
        self.assertNotEqual(before.query_dependencies, after.query_dependencies)
        with self.assertRaises(HCLFailure) as error:
            self.store.validate_snapshot(before)
        self.assertEqual(error.exception.diagnostic.code, "QUERY_DEPENDENCY_CHANGED")
        scoped = self.search(self.query(source_scope=("a",)))
        self.store.put_source("s", self.owner, "later", "new material.")
        self.store.validate_snapshot(scoped)
        self.assertFalse(after.query_views["0"]["coverage"]["whole_source_read"])

    def test_restart_exact_wire_projection_and_rebuild(self):
        self.store.put_source("s", self.owner, "a", "witness event. denial event. alternative cause.")
        first = self.search()
        packed = pack_dependencies(first.source_versions, first.query_dependencies)
        self.assertEqual(unpack_dependencies(packed), (dict(first.source_versions), first.query_dependencies))
        self.assertEqual(codec.loads(codec.dumps(first)), first)
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        self.assertEqual(self.search(), first)
        self.store.rebuild_projections()
        self.assertEqual(self.search(), first)
        with self.store._transaction() as db:
            session = self.store._session(db, "s", self.owner)
            row = db.execute("SELECT * FROM sources WHERE source_id='a'").fetchone()
            content = self.store._get_object(row["object_hash"])
            self.assertEqual(self.store._get_object(content["retrieval_index_hash"]), build_index(self.store._source(db, session, self.owner, "a")))
            cached = content["retrieval_index_hash"]
        # Disposable cache removal on this synthetic temporary fixture must not
        # be confused with deleting source content or accepting a missing source.
        (self.store.object_root/cached).unlink()
        self.assertEqual(self.search(), first)
        self.store.rebuild_projections()
        self.assertEqual(self.search(), first)
        # Source-object integrity remains mandatory when cache data is missing.
        row=self.store._db.execute("SELECT object_hash FROM sources WHERE source_id='a'").fetchone()
        (self.store.object_root/row['object_hash']).write_bytes(b'CORRUPT_SYNTHETIC_ORIGINAL')
        with self.assertRaises(HCLFailure) as error:
            self.search()
        self.assertEqual(error.exception.diagnostic.code,'STATE_CORRUPT')

    def test_late_wal_revocation_cannot_deliver_projection(self):
        self.store.put_source("s", self.owner, "a", "PRIVATE_CANARY witness event.")
        peer = StateStore.sqlite(self.path)
        try:
            fired = False
            def check(stage):
                nonlocal fired
                if stage == "before_commit" and not fired:
                    fired = True
                    peer.set_readers("s", self.owner, "a", frozenset({"b"}))
            with patch.object(self.store, "_checkpoint", check):
                with self.assertRaises(HCLFailure) as error:
                    self.search()
            self.assertEqual(error.exception.status, "DENIED")
            self.assertNotIn("PRIVATE_CANARY", str(error.exception))
        finally:
            peer.close()

    def test_old_token_cache_rebuilds_supplementary_runs_without_rewriting_history(self):
        from collections import Counter
        import re
        from hcl.kernel.types import thaw
        from hcl.memory.index import INDEX_VERSION, TOKENIZER

        def old_index(source):
            value = thaw(build_index(source))
            value.update(version="mechanical-regions-bm25-tfidf-1",
                         tokenizer="unicode-casefold-words-cjk-bigrams-1")
            for row in value["regions"]:
                # The old tokenizer saw these supplementary runs as one word,
                # or omitted them when the interpreter UCD did not know them.
                row["counts"] = dict(Counter(re.findall(r"[^\W_]+", source.text[row["start"]:row["end"]])))
            return value

        runs = ("𠀀𠀁𠀂", "\U00031350\U00031351\U00031352",
                "\U0002ee50\U0002ee51\U0002ee52", "\U00033470\U00033471\U00033472")
        with patch("hcl.memory.index.build_index", old_index):
            for n, run in enumerate(runs):
                self.store.put_source("s", self.owner, str(n), run + ".")
        rows = [dict(row) for row in self.store._db.execute("SELECT * FROM sources ORDER BY source_id")]
        originals = {row["object_hash"]: (self.store.object_root / row["object_hash"]).read_bytes() for row in rows}
        caches = {self.store._get_object(key)["retrieval_index_hash"] for key in originals}
        originals.update({key: (self.store.object_root / key).read_bytes() for key in caches})
        self.store.close()
        self.store = StateStore.sqlite(self.path)
        for n, run in enumerate(runs):
            query = RetrievalQuery({route: run[:2] for route in ROUTES}, source_scope=(str(n),))
            view = self.search(query).query_views["0"]
            for route in ROUTES:
                self.assertTrue(view["routes"][route]["hits"])
            self.assertIn(INDEX_VERSION, codec.dumps(view).decode())
            self.assertIn(TOKENIZER, codec.dumps(view).decode())
        self.assertEqual(rows, [dict(row) for row in self.store._db.execute("SELECT * FROM sources ORDER BY source_id")])
        for key, original in originals.items():
            self.assertEqual((self.store.object_root / key).read_bytes(), original)

    def test_forged_packet_is_not_valid_snapshot(self):
        self.store.put_source("s", self.owner, "a", "witness event.")
        first = self.search()
        with self.assertRaises(HCLFailure):
            self.store.validate_snapshot(replace(first, query_views={"0": {"invented": True}}))

    def test_three_routes_and_bounded_unread_are_explicit(self):
        self.store.put_source("s", self.owner, "a", "witness event. " + "irrelevant. "*100 + "denial not event. alternative cause.")
        result = self.search(self.query(max_hits_per_route=1, max_characters=40))
        view = result.query_views["0"]
        self.assertEqual(set(view["routes"]), set(ROUTES))
        for key in ROUTES:
            self.assertTrue(view["routes"][key]["hits"])
        self.assertFalse(view["coverage"]["whole_source_read"])
        self.assertFalse(view["coverage"]["recorded_closure_complete"])
        self.assertTrue(view["coverage"]["frontier"])
        self.assertLessEqual(view["coverage"]["selected_characters"], 40)
        self.assertEqual(view["coverage"]["semantic_completeness"], "NOT_ESTABLISHED")

    def test_recursive_and_or_challenge_alternative_revision_cycles(self):
        segments = {s.segment_id: s for s in iter_segments("A. B. C. D. E.", "book", 1, "SOURCE")}
        keys = list(segments)
        graph = {
            "root": EvidenceNode("root", (keys[0],), (("p", "q"), ("other",)), ("challenge",), ("alternative",), ("revision",)),
            "p": EvidenceNode("p", (keys[1],)), "q": EvidenceNode("q", (keys[2],)),
            "other": EvidenceNode("other", (keys[3],)),
            "challenge": EvidenceNode("challenge", (keys[4],), challenges=("root",)),
            "alternative": EvidenceNode("alternative", (), support_groups=(("p",),)),
            "revision": EvidenceNode("revision", (), revision_reasons=("q",)),
        }
        result = recorded_closure(("root",), graph, segments, max_nodes=32, max_characters=1000)
        self.assertTrue(result["complete"])
        self.assertEqual(set(result["nodes"]), set(graph))
        self.assertEqual(set(result["segments"]), set(segments))
        for limit in range(12):
            cut = recorded_closure(("root",), graph, segments, max_nodes=limit, max_characters=1000)
            self.assertLessEqual(cut["visited"], limit)
            self.assertFalse(cut["complete"])
        changed = dict(graph, q=EvidenceNode("q", (), challenges=("unrecorded",)))
        missing = recorded_closure(("root",), changed, segments, max_nodes=32, max_characters=1000)
        self.assertFalse(missing["complete"])
        self.assertEqual(missing["missing"], ("unrecorded",))

    def test_vector_scores_against_independent_dense_calculation(self):
        rows = [dict(segment_id=str(i), counts=counts) for i, counts in enumerate((dict(a=2,b=1),dict(b=1,c=3),dict(a=1,c=1)))]
        actual = {row["segment_id"]: row for row in rank_regions("a b", rows)}
        vocabulary = sorted({key for row in rows for key in row["counts"]})
        idf = [math.log(4/(1+sum(key in row["counts"] for row in rows)))+1 for key in vocabulary]
        query = [value if key in {"a", "b"} else 0 for key, value in zip(vocabulary, idf)]
        for row in rows:
            vector = [(1+math.log(row["counts"][key]))*weight if key in row["counts"] else 0 for key, weight in zip(vocabulary,idf)]
            expected = sum(a*b for a,b in zip(vector,query))/math.sqrt(sum(a*a for a in vector)*sum(b*b for b in query))
            self.assertAlmostEqual(actual[row["segment_id"]]["tfidf_cosine"], expected)


if __name__ == "__main__":
    unittest.main()
