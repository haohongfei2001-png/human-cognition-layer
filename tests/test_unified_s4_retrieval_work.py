"""Real recorded DAGs share validation without sharing current authority."""
from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from hcl.kernel.dependencies import QueryDelta
from hcl.kernel.retrieval import RetrievalQuery
from hcl.kernel.types import HCLFailure, Principal
from hcl.memory import query_store
from hcl.memory.query_store import QueryStore, RetrievalPreparation
from tests import test_unified_s4_engine as arguments
from tests import test_unified_s4_retrieval as retrieval


class RetrievalWorkTests(unittest.TestCase):
    def argument_fixture(self):
        fixture = arguments.ArgumentExecutionTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        result, _ = fixture.run_candidate()
        self.assertEqual(result.status, "COMPLETED")
        return fixture, fixture.inference(result)

    @staticmethod
    def query():
        return RetrievalQuery(dict(support="目击者", challenge="否认", alternative="星期二"))

    def commit_proofs(self, fixture, snapshot, template, identifiers):
        # Real computed M13 proof values remain untouched. Only the independent
        # immutable effect IDs and actual query-bound commit contexts differ.
        delta = QueryDelta(snapshot.session_id, snapshot.principal, snapshot.revision,
                           snapshot.access_epoch, snapshot.rule_version, snapshot.source_versions,
                           tuple(replace(template, result_id=key) for key in identifiers),
                           snapshot.query_dependencies)
        fixture.store.commit(snapshot.revision, snapshot.source_versions, snapshot.access_epoch, delta)

    def test_diamond_ancestors_compute_once_per_fresh_transaction(self):
        fixture, template = self.argument_fixture()
        query = self.query()
        original = query_store.retrieval_projection
        for level in range(6):
            with patch.object(query_store, "retrieval_projection", wraps=original) as counted:
                snapshot = QueryStore(fixture.store).search("s", fixture.owner, query)
            # Search and its late fresh delivery check each compute every unique
            # ancestor exactly once. Previously this was 2,6,14,30,62,126.
            self.assertEqual(counted.call_count, 2 * (level + 1))
            identifiers = tuple(f"layer-{level}-{n}" for n in range(2))
            self.commit_proofs(fixture, snapshot, template, identifiers)
            query = replace(query, evidence_result_ids=identifiers)
        # An arriving source must still invalidate all open-scope ancestors.
        fixture.store.put_source("s", fixture.owner, "late", "新的否认与反证。")
        with self.assertRaises(HCLFailure) as error:
            QueryStore(fixture.store).search("s", fixture.owner, query)
        self.assertEqual(error.exception.diagnostic.code, "QUERY_DEPENDENCY_CHANGED")

    def test_shallow_memo_hit_never_bypasses_longest_dependency_depth(self):
        fixture, template = self.argument_fixture()
        query, identifiers = self.query(), []
        for level in range(8):
            snapshot = QueryStore(fixture.store).search("s", fixture.owner, query)
            key = f"depth-{level:02d}"
            identifiers.append(key)
            self.commit_proofs(fixture, snapshot, template, (key,))
            query = replace(query, evidence_result_ids=(key,))
        # q3 is first cached near the root, then encountered under q7. Its
        # cached remaining height must still make the nine-layer path fail.
        query = replace(query, evidence_result_ids=(identifiers[3], identifiers[7]))
        with self.assertRaises(HCLFailure) as error:
            QueryStore(fixture.store).search("s", fixture.owner, query)
        self.assertEqual(error.exception.diagnostic.code, "RETRIEVAL_DEPENDENCY_DEPTH")
        self.assertIsNone(fixture.store._retrieval_preparation)
        QueryStore(fixture.store).search("s", fixture.owner, self.query())

    def retrieval_fixture(self):
        fixture = retrieval.RetrievalTests()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.store.put_source("s", fixture.owner, "PRIVATE_ID", "witness event.", readers=frozenset({"a"}))
        return fixture

    def test_memo_separates_principal_and_transaction_write_generation(self):
        fixture = self.retrieval_fixture()
        store, query = fixture.store, fixture.query()
        with store._transaction(True) as db:
            session = store._session(db, "s", fixture.owner)
            first = store._query_projection(db, session, fixture.owner, query)
            self.assertIs(store._query_projection(db, session, fixture.owner, query), first)
            other = store._query_projection(db, session, Principal("t", "b"), query)
            self.assertFalse(other[1]["search_scope"])
            self.assertNotIn("PRIVATE_ID", json.dumps(dict(other[1]["search_scope"])))
            source = dict(db.execute("SELECT * FROM sources").fetchone())
            source.update(version=2, object_hash=store._put_object(dict(text="New denial event.", formal_problem=None)))
            session["revision"] += 1
            store._record(db, "sources", source, session["revision"])
            store._record(db, "sessions", session, session["revision"])
            changed = store._query_projection(db, session, fixture.owner, query)
            self.assertNotEqual(first[0], changed[0])
        self.assertIsNone(store._retrieval_preparation)
        self.assertEqual(fixture.search().query_dependencies[0], changed[0])

    def test_real_unique_query_bound_resets_after_transaction(self):
        fixture = self.retrieval_fixture()
        with fixture.store._transaction() as db:
            session = fixture.store._session(db, "s", fixture.owner)
            for n in range(RetrievalPreparation.LIMITS["projections"]):
                query = replace(fixture.query(), queries=dict(support=f"witness {n}", challenge="denial", alternative="other"))
                fixture.store._query_projection(db, session, fixture.owner, query)
            with self.assertRaises(HCLFailure) as error:
                fixture.store._query_projection(db, session, fixture.owner, fixture.query())
            self.assertEqual(error.exception.diagnostic.code, "RETRIEVAL_PREPARATION_BOUND")
            self.assertEqual(error.exception.diagnostic.field_path, "retrieval.projections")
        fixture.search()

    def test_each_total_work_boundary_is_exact_and_initial_search_is_charged(self):
        for kind, limit in RetrievalPreparation.LIMITS.items():
            preparation = RetrievalPreparation()
            preparation.charge(kind, limit)
            with self.assertRaises(HCLFailure) as error:
                preparation.charge(kind, 1)
            self.assertEqual(error.exception.status, "BUDGET_EXHAUSTED")
            self.assertEqual(preparation.work[kind], limit)
        fixture = self.retrieval_fixture()
        for kind in ("projections", "source_characters", "regions"):
            with patch.object(RetrievalPreparation, "LIMITS", dict(RetrievalPreparation.LIMITS, **{kind: 0})):
                with self.assertRaises(HCLFailure) as error:
                    fixture.search()
                self.assertEqual(error.exception.diagnostic.field_path, "retrieval." + kind)
            self.assertIsNone(fixture.store._retrieval_preparation)


if __name__ == "__main__":
    unittest.main()
