"""Exact-head actual dynamic execution witness; fixtures propose meanings only."""

import argparse
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from hcl import HCL, ExecutionBudget, ExecutionIssue, RevisionIssue
from hcl.kernel.types import FormalProblem, Issue, Principal, TaskRequest, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.recovery import RecoveryManager
from hcl.semantics.segments import segment_snapshot
from scripts.witness_unified_s21 import proposal, atom, neg
from scripts.witness_unified_s22 import propose, ref


class Crash(BaseException):
    pass


def witness():
    owner = Principal("synthetic", "owner")
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "state.sqlite"
        store = StateStore.sqlite(path, revision=True)
        store.create_session("witness", owner)
        problem = FormalProblem(
            ("Fa",), "Ga", {"domain": [0], "constants": {"a": 0}, "predicates": {"F": [0], "G": []}}
        )
        handle = store.put_source("witness", owner, "original", "张三不会出席。", formal_problem=problem)
        budget = ExecutionBudget(
            max_mock_calls=4,
            max_output_bytes=65536,
            max_visible_output_tokens=65536,
            max_total_output_bytes=1048576,
        )
        request = TaskRequest(
            "local",
            "能推出张三出席吗？",
            (handle,),
            "witness",
            owner,
            budget=budget,
            issue=ExecutionIssue(
                "task", goals=(Issue("finite", "logic.check_interpretation", "original"),)
            ),
        )

        def execute(req, responses=None):
            port = OfflineModelPort(responses=responses)
            result = HCL(store, principal=owner, gateway=ModelGateway(store, port)).run_sync(req)
            assert result.status in ("COMPLETED", "PARTIAL"), result.diagnostics
            ids = set(result.execution_receipt["result_ids"])
            actual = []
            with store._transaction() as db:
                session = store._session(db, "witness", owner)
                for identity in sorted(ids):
                    row = db.execute(
                        "SELECT * FROM inferences WHERE session_id=? AND result_id=?", ("witness", identity)
                    ).fetchone()
                    store._validate_dependencies(
                        db, session, owner, json.loads(row["read_set"]), row["epoch"], session["rule"]
                    )
                    r = store._get_object(row["object_hash"])
                    actual.append(dict(result_id=r.result_id, kind=r.kind, values=thaw(r.values)))
            rows.append(
                dict(
                    request_id=req.request_id,
                    status=result.status,
                    answer=result.answer,
                    usage=thaw(result.usage),
                    actual_results=actual,
                    consumed=[
                        dict(
                            result_id=f.result_id,
                            field=f.field,
                            path=list(getattr(f, "path", ())),
                            selection=list(getattr(f, "selection", ())),
                            value=thaw(f.value),
                        )
                        for claim in result.claim_records
                        for f in claim.used_result_fields
                    ],
                    fixture_attempts=port.attempts,
                )
            )
            return result, port

        local, port = execute(request)
        assert local.usage["mock_calls"] == port.attempts == 0 and "verified counterexample" in local.answer
        segments = segment_snapshot(store.snapshot("witness", owner, (handle,)), request.question)
        candidate = proposal(segments, [([neg(atom("attends"))], atom("attends"))], "张三")
        bad = dict(candidate, schema="unsupported")
        semantic = replace(
            request,
            request_id="repaired",
            issue=ExecutionIssue(
                "task", goals=(Issue("semantic", "logic.compare_semantic_readings", "original"),)
            ),
        )
        repaired, port = execute(
            semantic, ("{", json.dumps(bad, ensure_ascii=False), json.dumps(candidate, ensure_ascii=False))
        )
        assert port.attempts == 3 and "label=False" in repaired.answer
        audit = RecoveryManager(store).execution_audit(semantic)
        assert audit["calls"][0]["response"] == "{" and len(audit["calls"]) == 3
        # Returned transport is persisted before an abrupt interruption. Only an
        # explicit host handoff resumes the graph and reuses that exact response.
        interrupted = replace(semantic, request_id="interrupted")
        original_owner = store.owner_id
        first_port = OfflineModelPort(json.dumps(candidate, ensure_ascii=False))

        def crash(stage):
            if stage == "return_persisted":
                raise Crash()

        try:
            with patch.object(store, "_checkpoint", crash):
                HCL(store, principal=owner, gateway=ModelGateway(store, first_port)).run_sync(interrupted)
        except Crash:
            pass
        else:
            raise AssertionError("interruption seam not reached")
        store.close()
        store = StateStore.sqlite(path)
        RecoveryManager(store).resume_execution(interrupted, expected_owner_id=original_owner)
        resumed, port = execute(interrupted)
        assert port.attempts == 0 and first_port.attempts == 1 and resumed.usage["mock_calls"] == 1
        # Actual support revision under the very same graph interface uses a
        # separate namespace with complete absence-scope inputs.
        store.close()
        path = Path(directory) / "revision.sqlite"
        store = StateStore.sqlite(path, revision=True)
        store.create_session("witness", owner)
        initial = store.put_source("witness", owner, "initial", "当前限定资料没有收到通知的记录。")
        revision = replace(
            request,
            request_id="absence",
            source_handles=(initial,),
            issue=ExecutionIssue("task", goals=(RevisionIssue("revision"),)),
        )
        data = dict(
            schema="hcl-revision-candidates-1",
            sources=[propose(store, revision, initial, default=True)],
            query=dict(positive=ref("initial", "q"), negative=ref("initial", "not-q")),
        )
        before, _ = execute(revision, (json.dumps(data, ensure_ascii=False),))
        assert "positive=True" in before.answer
        late = store.put_source("witness", owner, "late", "新证据报告同一人物此前收到同一通知。")
        updated = replace(revision, request_id="late", source_handles=(late,))
        data["sources"] = [propose(store, updated, late, late_receipt=True)]
        after, _ = execute(updated, (json.dumps(data, ensure_ascii=False),))
        assert "positive=False" in after.answer and "negative=True" in after.answer
        assert rows[-1]["actual_results"][0]["values"]["absence_watches"]
        store.close()
    root = Path(__file__).resolve().parents[1]
    return dict(
        schema="hcl-unified-s23-witness-1",
        checked_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        runtime_hashes={
            str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
            for p in sorted((root / "hcl").rglob("*.py"))
        },
        provider_calls=0,
        provider_spend_usd="0",
        sealed_content_reads=0,
        rows=rows,
        evidence_scope="ACTUAL_BUDGETED_GRAPH_UNDER_INJECTED_CANDIDATE_MEANINGS",
        not_established=[
            "open semantic extraction",
            "automatic source-faithful task decomposition",
            "cross-chunk semantic composition",
            "semantic alignment/completeness",
            "full S1/S2 or acceptance families",
            "live functionality",
            "effectiveness",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(witness(), ensure_ascii=False, indent=2) + "\n")
