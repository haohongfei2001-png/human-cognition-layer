"""One actual recipient-specific interpretation feeds M07 and M08 unchanged."""

from copy import deepcopy
from dataclasses import replace
import json
import unittest
from unittest.mock import patch
from hcl.kernel.types import Issue, thaw
from hcl.operators.mental_scene import MentalSceneOperator
from hcl.operators.interaction_model import InteractionModelOperator, verify_interaction
from hcl.operators.affect_model import AffectModelOperator, verify_affect
from hcl.operators.shared_cognition import (
    compute_shared_cognition,
    cognitive_record,
    verify_cognitive_record,
)
from hcl.semantics.interaction_compiler import InteractionCompiler
from hcl.semantics.affect_compiler import AffectCompiler
from hcl.semantics.segments import segment_snapshot
from tests import test_unified_s3_affect as affect_fixtures


class SharedCognitionTests(unittest.TestCase):
    def setUp(self):
        self.f = affect_fixtures.AffectExecutionTests()
        self.f.setUp()

    def tearDown(self):
        self.f.tearDown()

    def inputs(self, content):
        affect = self.f.revised_candidate()
        model = affect["models"][0]
        mental = model["mental"]
        mental["plans"][1]["weights"] = None
        model["episodes"][1]["current_weights"] = None
        refs = mental["events"][1]["segment_ids"]
        interaction = dict(
            mental=deepcopy(mental),
            through=2,
            max_ack_depth=2,
            utterances=[
                dict(
                    id="notice",
                    at=2,
                    speaker="a",
                    audience=["b"],
                    version="v1",
                    literal={"open": True},
                    segment_ids=refs,
                    deliveries=[
                        dict(
                            event_id="new-information",
                            segment_ids=refs,
                            readings=[
                                dict(
                                    actor="b",
                                    contents=[{"open": content}],
                                    versions=["v1"],
                                    segment_ids=refs,
                                )
                            ],
                        )
                    ],
                )
            ],
            acts=[],
            commitments=[],
            games=[],
        )
        snapshot = self.f.store.snapshot(
            "scene", self.f.owner, self.f.request.source_handles
        )
        segments = segment_snapshot(snapshot, self.f.request.question)
        interaction = thaw(
            InteractionCompiler().compile(
                snapshot,
                segments,
                json.dumps(
                    dict(schema="hcl-interaction-candidates-1", models=[interaction])
                ),
                self.f.request.budget,
            )
        )["models"][0]
        affect = thaw(
            AffectCompiler().compile(
                snapshot, segments, json.dumps(affect), self.f.request.budget
            )
        )["models"][0]
        return snapshot, interaction, affect

    def test_recipient_reading_is_computed_once_and_consumed_by_both_domains(self):
        outcomes = []
        for content in (False, True):
            snapshot, interaction, affect = self.inputs(content)
            issue = Issue("shared", "relationship.evaluate")
            budget = self.f.request.budget
            with patch.object(
                MentalSceneOperator,
                "_run",
                autospec=True,
                side_effect=MentalSceneOperator._run,
            ) as computation:
                bundle = compute_shared_cognition(
                    snapshot, issue, budget, interaction, (0, 1, 2)
                )
                shared = {
                    (
                        interaction["mental"]["source_id"],
                        interaction["mental"]["id"],
                    ): bundle
                }
                after = replace(
                    budget,
                    max_local_evaluations=budget.max_local_evaluations
                    - bundle.operation.resource_usage["local_evaluations"],
                )
                m07 = InteractionModelOperator()._run(
                    snapshot,
                    issue,
                    after,
                    dict(models=[interaction]),
                    shared_cognition=shared,
                )
                after = replace(
                    after,
                    max_local_evaluations=after.max_local_evaluations
                    - m07.resource_usage["local_evaluations"],
                )
                m08 = AffectModelOperator()._run(
                    snapshot,
                    issue,
                    after,
                    dict(models=[affect]),
                    shared_cognition=shared,
                )
                self.assertEqual(computation.call_count, 1)
            a = m07.candidate_delta.new_inferences[0]
            b = m08.candidate_delta.new_inferences[0]
            self.assertEqual(
                a.values["models"][0]["actual_mental"],
                b.values["models"][0]["actual_mental"],
            )
            self.assertEqual(
                a.values["models"][0]["actual_mental"]["result_id"],
                bundle.operation.result_refs[0],
            )
            episode = b.values["models"][0]["episodes"][1]
            self.assertIn("new-message-hypothesis", episode["assumption_environments"])
            outcomes.append(
                episode["derived"]["profiles"][0]["appraisal"]["current_value"]["lower"]
            )
            verify_interaction(a.values)
            record = cognitive_record(bundle)
            replayed = verify_cognitive_record(
                record, interaction, snapshot.source_versions, snapshot.rule_version
            )
            verify_affect(
                b.values,
                shared_cognition={
                    (
                        interaction["mental"]["source_id"],
                        interaction["mental"]["id"],
                    ): replayed
                },
            )
            if not content:
                # A domain cannot silently replay the default message meaning.
                with self.assertRaises(ValueError):
                    verify_affect(b.values)
            corrupted = deepcopy(record)
            corrupted["actual"]["values"]["models"][0]["events"] = []
            with self.assertRaises(ValueError):
                verify_cognitive_record(
                    corrupted,
                    interaction,
                    snapshot.source_versions,
                    snapshot.rule_version,
                )
            with self.assertRaises(ValueError):
                bundle.bind(
                    replace(snapshot, access_epoch=snapshot.access_epoch + 1),
                    interaction["mental"],
                )
        self.assertEqual(outcomes, ["-3", "3"])


if __name__ == "__main__":
    unittest.main()
