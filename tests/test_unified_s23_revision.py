"""Same dynamic graph consumes the real persisted temporal/truth revision kernel."""

from dataclasses import replace
import json
import unittest
from unittest.mock import patch

from hcl import HCL, ExecutionIssue
from hcl.kernel.dependencies import RevisionIssue
from hcl.kernel.types import Issue
from hcl.memory.store import StateStore
from hcl.models.gateway import OfflineModelPort, ModelGateway
from tests import test_unified_s22 as revision_fixtures
from tests import test_unified_s23 as graph_fixtures


class GraphRevisionTests(graph_fixtures.ExecutionGraphTests):
    def proposal(self, *, handle=None, direct=True):
        fixture = revision_fixtures.RevisionExecutionTests()
        fixture.store, fixture.owner, fixture.handle = self.store, self.owner, handle or self.handle
        fixture.request = self.request()
        source, _ = fixture.source()
        if not direct:
            source["roots"] = []
        return fixture.candidate(source)

    def revision_request(self, **kw):
        return self.request((RevisionIssue("revision"),), **kw)

    def test_actual_revision_result_consumed_and_new_evidence_recomputes(self):
        first, port = self.run_request(self.revision_request(), (json.dumps(self.proposal()),))
        self.assertEqual(first.status, "COMPLETED", first.diagnostics)
        self.assertIn("positive=True", first.answer)
        self.assertEqual(port.attempts, 1)
        self.assertGreater(first.usage["local_evaluations"], 0)
        self.handle = self.store.put_source("s", self.owner, "source", "No supporting report remains.")
        request = self.revision_request(request_id="revised")
        second, port = self.run_request(request, (json.dumps(self.proposal(direct=False)),))
        self.assertEqual(second.status, "COMPLETED", second.diagnostics)
        self.assertIn("positive=False", second.answer)
        self.assertEqual(port.attempts, 1)
        old, port = self.run_request(self.revision_request(request_id="execution"))
        self.assertEqual(old.status, "INVALID_REQUEST")  # changed request handles retain fingerprint guard
        self.assertEqual(port.attempts, 0)

    def test_related_query_race_recomputes_only_local_branch_without_resending(self):
        from hcl.operators.local_model import LocalModelOperator

        peer = StateStore.sqlite(self.path)
        original = LocalModelOperator.run
        changed = False

        def run(op, snapshot, issue, allowance):
            nonlocal changed
            result = original(op, snapshot, issue, allowance)
            if issue.kind == "revision.evaluate" and not changed:
                changed = True
                peer.put_source("s", self.owner, "late", "new uncompiled evidence changes indexed coverage")
            return result

        try:
            with patch.object(LocalModelOperator, "run", run):
                result, port = self.run_request(self.revision_request(), (json.dumps(self.proposal()),))
            self.assertEqual(result.status, "COMPLETED", result.diagnostics)
            self.assertEqual(port.attempts, 1)
            self.assertGreaterEqual(result.usage["local_evaluations"], 2)
        finally:
            peer.close()

    def test_revision_and_independent_formal_branch_share_results_without_fixed_chain(self):
        request = self.request(
            (RevisionIssue("revision"), Issue("finite", "logic.check_interpretation", "source"))
        )
        result, port = self.run_request(request, (json.dumps(self.proposal()),))
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertEqual(len(result.claim_records), 2)
        self.assertEqual(port.attempts, 1)
        self.assertIn("positive=True", result.answer)
        self.assertIn("verified counterexample", result.answer)

    def test_fixed_historical_cutoff_and_fresh_cached_acl(self):
        first, _ = self.run_request(self.revision_request(), (json.dumps(self.proposal()),))
        cutoff = first.state_revision
        self.handle = self.store.put_source("s", self.owner, "source", "withdrawn new report")
        current, _ = self.run_request(
            self.revision_request(request_id="current"), (json.dumps(self.proposal(direct=False)),)
        )
        self.assertIn("positive=False", current.answer)
        from hcl.kernel.types import SourceHandle

        old_handle = SourceHandle("source", 1)
        request = self.request(
            (RevisionIssue("old", known_at=cutoff),), request_id="historical", source_handles=(old_handle,)
        )
        # The existing historical index is still consumed. Compile its exact old
        # source candidate at the recorded selector, not the newer source text.
        fixture = revision_fixtures.RevisionExecutionTests()
        fixture.store, fixture.owner, fixture.handle, fixture.request = (
            self.store,
            self.owner,
            old_handle,
            request,
        )
        source, _ = fixture.source(known_at=cutoff)
        result, port = self.run_request(request, (json.dumps(fixture.candidate(source)),))
        self.assertEqual(result.status, "COMPLETED", result.diagnostics)
        self.assertIn("positive=True", result.answer)
        self.store.set_readers("s", self.owner, "source", {"bob"})
        replay, port = self.run_request(request)
        self.assertEqual(replay.status, "DENIED")
        self.assertFalse(replay.answer)
        self.assertEqual(port.attempts, 0)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(
        GraphRevisionTests(name) for name in GraphRevisionTests.__dict__ if name.startswith("test_")
    )
