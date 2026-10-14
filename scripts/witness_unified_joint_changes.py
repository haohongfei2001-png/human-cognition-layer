"""Provider-free joint edit witness through the one ordinary HCL runtime."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile

import hcl
from hcl import HCL, ExecutionBudget, ExecutionIssue
from hcl.kernel.types import Principal, TaskRequest, Issue, thaw
from hcl.memory.store import StateStore
from hcl.models.gateway import ModelGateway, OfflineModelPort
from scripts.witness_unified_concept_judgment import propose as concept_propose, SCENE, PRINCIPLES


def propose(snapshot, question):
    """Two independent positive supports require choice replacement AND withdrawal."""
    data = concept_propose(snapshot, question)
    data["schema"] = "hcl-judgment-candidates-4"
    model = data["models"][0]
    argument = model["argument"]
    extra = deepcopy(argument["rules"][0])
    extra.update(id="independent-care", premises=["known"])
    argument["rules"].append(extra)
    argument["priorities"].append(dict(better=extra["id"], worse="liberty", segment_ids=extra["segment_ids"]))
    data["joint_changes"] = dict(baseline={"meaning": "revised"},
        target=dict(kind="M14_DECISION", source_id="scene", model_id="notice", decision_id="notification"),
        edits=[dict(kind="CHOICE_REPLACE", choice_id="meaning", version_id="original", segment_ids=data["concepts"]["choices"][0]["segment_ids"]),
            dict(kind="RULE_RETRACT", source_id="scene", model_id="notice", argument_id="norms", item_id="independent-care", segment_ids=extra["segment_ids"])])
    return data


def witness():
    owner = Principal("synthetic-joint-change-witness", "owner")
    rows = []
    with tempfile.TemporaryDirectory() as directory:
        store = StateStore.sqlite(Path(directory) / "state.sqlite", revision=True)
        store.create_session("s", owner, {"bob"})
        handles = (store.put_source("s", owner, "scene", SCENE), store.put_source("s", owner, "principles", PRINCIPLES))
        try:
            for mode in ("mixed-joint-m14", "mixed-joint-m13", "interlocked-terminal", "all-ties", "no-expressible-change", "unknown-case", "budget"):
                request = TaskRequest(mode, "哪些最小联合假设改动会改变判断，同时保留原始承诺和事实？", handles, "s", owner,
                    budget=ExecutionBudget(max_mock_calls=1, max_feedback=0,
                        max_local_evaluations=100 if mode == "budget" else 200000,
                        max_request_bytes=1048576, max_context_tokens=1048576, max_output_bytes=1048576,
                        max_total_output_bytes=8000000, max_visible_output_tokens=1048576),
                    issue=ExecutionIssue("root", goals=(Issue(mode, "judgment.evaluate"),)))
                candidate = propose(store.snapshot("s", owner, handles), request.question)
                spec = candidate["joint_changes"]
                if mode == "mixed-joint-m13":
                    spec["target"] = dict(kind="M13_ACCEPTANCE", source_id="scene", model_id="notice", argument_id="norms", query_id="duty")
                elif mode == "interlocked-terminal":
                    c = candidate["concepts"]
                    choice = deepcopy(c["choices"][0]); choice["id"] = "linked"; c["choices"].append(choice)
                    c["constraints"] = [dict(left="meaning", right="linked", allowed_pairs=[["original", "original"], ["revised", "revised"]], segment_ids=choice["segment_ids"])]
                    spec["baseline"]["linked"] = "revised"
                    spec["edits"].append(dict(kind="CHOICE_REPLACE", choice_id="linked", version_id="original", segment_ids=choice["segment_ids"]))
                elif mode == "all-ties":
                    # Withdrawing either the independent rule or its sole premise,
                    # together with the concept replacement, yields all two-edit ties.
                    argument = candidate["models"][0]["argument"]
                    premise = next(p for p in argument["premises"] if p["id"] == "meeting")
                    argument["rules"][-1]["premises"] = [premise["literal"]]
                    spec["edits"].append(dict(kind="PREMISE_RETRACT", source_id="scene", model_id="notice", argument_id="norms", item_id=premise["id"], segment_ids=premise["segment_ids"]))
                elif mode == "no-expressible-change":
                    spec["edits"] = spec["edits"][:1]
                elif mode == "unknown-case":
                    candidate["concepts"]["cases"][0]["term"] = None
                port = OfflineModelPort(json.dumps(candidate, ensure_ascii=False))
                result = HCL(store, principal=owner, gateway=ModelGateway(store, port)).run_sync(request)
                assert result.status == "PARTIAL", (mode, result.diagnostics)
                actual = next(r for r in store.inferences("s", owner) if r.result_id in result.execution_receipt["result_ids"])
                search = actual.values["joint_search"]
                if mode in ("mixed-joint-m14", "mixed-joint-m13", "interlocked-terminal", "all-ties"):
                    assert search["complete"] and search["minimum_cardinality"] == (3 if mode == "interlocked-terminal" else 2), (mode, thaw(search))
                    if mode == "all-ties":
                        assert len(search["minimum_witnesses"]) == 2
                elif mode == "no-expressible-change":
                    assert search["status"] == "NO_EXPRESSIBLE_CHANGE"
                else:
                    assert not search["complete"] and search["minimum_cardinality"] is None and not search["minimum_witnesses"]
                replay_port = OfflineModelPort("NO_NEW_SEND")
                replay = HCL(store, principal=owner, gateway=ModelGateway(store, replay_port)).run_sync(request)
                assert (replay.answer, replay.claim_records) == (result.answer, result.claim_records) and replay_port.attempts == 0
                rows.append(dict(case=mode, status=result.status, usage=thaw(result.usage), actual=thaw(actual.values), answer=result.answer,
                    claim_fields=[f.field for c in result.claim_records for f in c.used_result_fields], offline_attempts=port.attempts, replay_new_attempts=0))
            store.set_readers("s", owner, "principles", {"bob"})
            denied = HCL(store, principal=owner).run_sync(request)
            assert denied.status == "DENIED" and not denied.answer and not denied.claim_records
            rows.append(dict(case="current-source-acl", status=denied.status, answer_absent=True))
        finally:
            store.close()
    root = Path(hcl.__file__).resolve().parents[1]
    return dict(schema="hcl-unified-joint-change-witness-1",
        checked_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        runtime_hashes={str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in sorted((root / "hcl").rglob("*.py"))},
        rows=rows, provider_calls=0, provider_spend_usd=0, sealed_content_reads=0,
        evidence_scope="INTEGRATED_OFFLINE_FINITE_DECLARED_JOINT_MINIMUM_CARDINALITY",
        not_established=["OPEN_LANGUAGE_COMPLETENESS", "SEMANTIC_CONCEPT_DISTANCE_OPTIMALITY", "GLOBAL_MINIMALITY", "AUTOMATIC_ADOPTION",
            "PRINCIPLE_DISCOVERY", "WEIGHT_OPTIMIZATION", "MORAL_TRUTH", "FULL_M13", "FULL_M14", "FULL_S4", "LIVE_EFFECT"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(witness(), ensure_ascii=False, sort_keys=True, indent=2) + "\n")
