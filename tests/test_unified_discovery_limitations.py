"""A computed domain prediction retains material caveats through discovery."""

from copy import deepcopy
from dataclasses import replace
import json
import unittest

from hcl import HCL, ExecutionIssue
from hcl.kernel.types import Issue, HCLFailure, thaw
from hcl.models.gateway import ModelGateway, OfflineModelPort
from hcl.runtime.answer import AnswerAssembler
from tests import test_unified_s4_engine as fixtures


class DiscoveryLimitationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ArgumentExecutionTests()
        self.fixture.setUp()
        self.store, self.owner = self.fixture.store, self.fixture.owner
        self.request = replace(
            self.fixture.request,
            budget=replace(
                self.fixture.request.budget,
                max_local_evaluations=4096,
                max_request_bytes=1048576,
                max_output_bytes=1048576,
                max_total_output_bytes=16777216,
                max_context_tokens=1048576,
                max_visible_output_tokens=1048576,
            ),
        )

    def tearDown(self):
        self.fixture.tearDown()

    def template(self, kind):
        candidate = self.fixture.candidate(self.request)
        model = candidate["models"][0]
        if kind == "cycle":
            model["rules"].append(
                dict(
                    id="event-witness",
                    premises=["event"],
                    conclusion="witness",
                    strict=True,
                    assumptions=[],
                    segment_ids=model["rules"][0]["segment_ids"],
                )
            )
        elif kind == "strict":
            model["rules"][0]["strict"] = True
            model["premises"][1]["ordinary"] = False
        return candidate

    def discovery(self, kind, location):
        template = self.template(kind if location == "observed" else "plain")
        refs = template["models"][0]["premises"][0]["segment_ids"]
        context = dict(
            id="observed",
            adapter="argument-model-1",
            template=template,
            features={},
            feature_segments={},
            segment_ids=refs,
        )
        probe = deepcopy(context)
        probe.update(id="future", template=self.template(kind))
        return dict(
            schema="hcl-discovery-candidates-1",
            contexts=[context],
            observations=[
                dict(
                    id="report",
                    context_id="observed",
                    query_id="q",
                    values=[dict(positive=True, opposed=False)],
                    factor_id="factor",
                    provenance_group="source",
                    derived_from=[],
                    segment_ids=refs,
                )
            ],
            probes=(
                []
                if location == "observed"
                else [dict(id="probe", context=probe, query_id="q", segment_ids=refs)]
            ),
            programs=[
                dict(
                    id="fixed",
                    adapter="argument-model-1",
                    latent={},
                    observe=[],
                    transition=[],
                    constraint=[],
                    predict=[
                        dict(
                            id="q", field="argument.acceptance", record_id="event-query"
                        )
                    ],
                )
            ],
            grammar=dict(
                observation_features=[], latent_domains={}, max_expression_size=128
            ),
            search=dict(max_rounds=0, beam=12, new_per_round=4, max_candidates=64),
            unmodeled_segments=[],
        )

    def run_discovery(self, kind, location):
        request = replace(
            self.request,
            request_id=kind + location,
            issue=ExecutionIssue(
                "root", goals=(Issue("discovery", "hypothesis.discover"),)
            ),
        )
        port = OfflineModelPort(json.dumps(self.discovery(kind, location)))
        result = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        ).run_sync(request)
        actual = next(
            r
            for r in self.store.inferences("s", self.owner)
            if r.result_id in result.execution_receipt["result_ids"]
        )
        return request, result, actual

    def test_observed_and_probe_predictions_preserve_direct_argument_limitations(self):
        for kind, code in (
            ("cycle", "CYCLIC_PROOF_FRAGMENT_EXCLUDED"),
            ("strict", "INCONSISTENT_STRICT_CORE"),
        ):
            direct, _ = self.fixture.run_candidate(
                self.template(kind), replace(self.request, request_id="direct-" + kind)
            )
            self.assertEqual(direct.status, "PARTIAL")
            for location in ("observed", "probe"):
                with self.subTest(kind=kind, location=location):
                    _, result, actual = self.run_discovery(kind, location)
                    retained = [
                        r
                        for c in actual.values["prediction_matrix"].values()
                        for r in c["actual_results"]
                    ]
                    retained += [
                        r
                        for p in actual.values["distinguishing_observations"]
                        for e in p["evaluations"].values()
                        for r in e["actual_results"]
                    ]
                    self.assertIn(code, str([r["issues"] for r in retained]))
                    self.assertEqual(result.status, direct.status)
                    self.assertIn(code, result.answer)
                    self.assertIn(code, str(result.claim_records))
                    if location == "probe":
                        self.assertFalse(
                            next(iter(actual.values["prediction_matrix"].values()))[
                                "domain_limitations"
                            ]
                        )
                        self.assertIn(
                            code,
                            str(
                                actual.values["distinguishing_observations"][0][
                                    "domain_limitations"
                                ]
                            ),
                        )

    def test_stripping_scoped_or_global_limitations_is_rejected(self):
        for location in ("observed", "probe"):
            _, result, actual = self.run_discovery("cycle", location)
            self.assertEqual(result.status, "PARTIAL")
            values = thaw(actual.values)
            values["domain_issues"] = []
            mutations = [values]
            values = thaw(actual.values)
            if location == "observed":
                next(iter(values["prediction_matrix"].values()))[
                    "domain_limitations"
                ] = []
            else:
                values["distinguishing_observations"][0]["domain_limitations"] = {}
            mutations.append(values)
            if location == "probe":
                values = thaw(actual.values)
                next(
                    iter(
                        values["distinguishing_observations"][0]["predictions"].values()
                    )
                )["domain_limitations"] = []
                mutations.append(values)
            for bad in mutations:
                with self.assertRaises(HCLFailure):
                    AnswerAssembler()._claim(replace(actual, values=bad))

    def test_partial_probe_retains_issues_when_ancillary_domain_work_is_unfinished(
        self,
    ):
        _, _, actual = self.run_discovery("strict", "probe")
        observed_work = sum(
            c["work"] for c in actual.values["prediction_matrix"].values()
        )
        request = replace(
            self.request,
            request_id="partial-probe",
            budget=replace(
                self.request.budget, max_local_evaluations=observed_work + 1
            ),
            issue=ExecutionIssue(
                "root", goals=(Issue("discovery", "hypothesis.discover"),)
            ),
        )
        port = OfflineModelPort(json.dumps(self.discovery("strict", "probe")))
        result = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        ).run_sync(request)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        actual = next(
            r
            for r in self.store.inferences("s", self.owner)
            if r.result_id in result.execution_receipt["result_ids"]
        )
        probe = actual.values["distinguishing_observations"][0]
        self.assertTrue(probe["predictions"])
        self.assertIn("ARGUMENT_BATCH_FRONTIER", str(probe["domain_limitations"]))
        self.assertIn("INCONSISTENT_STRICT_CORE", str(probe["domain_limitations"]))
        self.assertIn("INCONSISTENT_STRICT_CORE", result.answer)

    def test_incomplete_probe_retains_actual_domain_limitations(self):
        candidate = self.discovery("strict", "probe")
        candidate["programs"][0]["predict"].append(
            dict(id="missing", field="argument.acceptance", record_id="absent-query")
        )
        candidate["probes"][0]["query_id"] = "missing"
        request = replace(
            self.request,
            request_id="missing-probe",
            issue=ExecutionIssue(
                "root", goals=(Issue("discovery", "hypothesis.discover"),)
            ),
        )
        port = OfflineModelPort(json.dumps(candidate))
        result = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        ).run_sync(request)
        self.assertEqual(result.status, "PARTIAL", result.diagnostics)
        actual = next(
            r
            for r in self.store.inferences("s", self.owner)
            if r.result_id in result.execution_receipt["result_ids"]
        )
        probe = actual.values["distinguishing_observations"][0]
        self.assertFalse(probe["predictions"])
        self.assertIn("INCONSISTENT_STRICT_CORE", str(probe["domain_limitations"]))
        self.assertIn("INCONSISTENT_STRICT_CORE", result.answer)
        self.assertIn("INCONSISTENT_STRICT_CORE", str(result.claim_records))

    def test_fresh_stream_and_restarted_replay_preserve_partial_and_scope(self):
        import asyncio
        from hcl.memory.store import StateStore

        request, result, _ = self.run_discovery("cycle", "observed")
        candidate = self.discovery("strict", "probe")
        fresh_request = replace(request, request_id="fresh-stream")
        port = OfflineModelPort(json.dumps(candidate))
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        )

        async def stream(client, request):
            return [e async for e in client.stream(request)]

        fresh = asyncio.run(stream(client, fresh_request))[-1].result
        self.assertEqual(fresh.status, "PARTIAL")
        self.assertIn("INCONSISTENT_STRICT_CORE", fresh.answer)
        path = self.store.path
        self.store.close()
        self.store = StateStore.sqlite(path, revision=True)
        self.fixture.store = self.store
        port = OfflineModelPort("NEVER_SEND")
        client = HCL(
            self.store, principal=self.owner, gateway=ModelGateway(self.store, port)
        )
        replay = client.run_sync(fresh_request)
        streamed = asyncio.run(stream(client, request))[-1].result
        self.assertEqual(
            (replay.status, replay.answer, replay.claim_records),
            (fresh.status, fresh.answer, fresh.claim_records),
        )
        self.assertEqual(
            (streamed.status, streamed.answer, streamed.claim_records),
            (result.status, result.answer, result.claim_records),
        )
        self.assertEqual(port.attempts, 0)


if __name__ == "__main__":
    unittest.main()
