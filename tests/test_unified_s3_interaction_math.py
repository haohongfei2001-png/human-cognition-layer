"""Independent finite message-game and lifecycle oracles, no proposed labels."""

from copy import deepcopy
import math
import unittest

from hcl.operators.interaction import (
    message_game,
    listener_actions,
    speaker_choices,
    commitment_history,
    acknowledgment_chains,
    interpreted_event,
)
from hcl.operators.epistemic import (
    EpistemicModel,
    update_perspectives,
    remaining_states,
)
from hcl.operators.agency import Action, PlanModel, solve_action_values


class MessageGameTests(unittest.TestCase):
    def setUp(self):
        self.messages = [
            dict(id="R", meaning=["r"], cost="1"),
            dict(id="B", meaning=["b"], cost="0"),
            dict(id="V", meaning=["r", "b"], cost="0"),
        ]

    def test_recursive_listener_matches_independent_closed_form(self):
        result = message_game(
            ("r", "b"), self.messages, {"r": "1/2", "b": "1/2"}, beta="1", depth=1
        )
        expected = 1 / (1 + math.exp(-0.5))
        self.assertEqual(result["status"], "COMPUTED")
        self.assertEqual(result["levels"][0]["listener"]["V"], {"r": 0.5, "b": 0.5})
        self.assertAlmostEqual(result["speaker"]["r"]["V"], expected, places=14)
        self.assertAlmostEqual(result["speaker"]["b"]["V"], 1 - expected, places=14)
        self.assertAlmostEqual(result["listener"]["V"]["r"], expected, places=14)

    @staticmethod
    def plan():
        states = ("r", "b", "success", "harm", "waited")
        transitions = {s: s for s in states}
        cross = Action(
            "cross",
            "0",
            ("r", "b"),
            ("r", "b"),
            dict(transitions, r="success", b="harm"),
            {s: "same" for s in states},
        )
        wait = Action(
            "wait",
            "0",
            ("r", "b"),
            ("r", "b"),
            dict(transitions, r="waited", b="waited"),
            {s: "same" for s in states},
        )
        return PlanModel(
            states,
            ("success", "harm", "waited"),
            dict(r="0", b="0", success="3", harm="-3", waited="0"),
            (cross, wait),
        )

    def test_true_ambiguous_message_changes_actual_m05_q_and_strategy(self):
        computed = message_game(
            ("r", "b"), self.messages, {"r": "1/2", "b": "1/2"}, beta="1", depth=1
        )
        state_q = {
            state: solve_action_values(self.plan(), {state: "1"}, 1)["q"]
            for state in ("r", "b")
        }
        predictions = {
            key: dict(
                posterior=posterior, actions=listener_actions(posterior, state_q, "1")
            )
            for key, posterior in computed["listener"].items()
        }
        expected = 3 * (2 / (1 + math.exp(-0.5)) - 1)
        self.assertAlmostEqual(
            predictions["V"]["actions"]["q"]["cross"], expected, places=14
        )
        self.assertEqual(predictions["V"]["actions"]["best_actions"], ("cross",))
        self.assertEqual(predictions["B"]["actions"]["best_actions"], ("wait",))
        actual_speaker = speaker_choices(
            ("b",),
            None,
            self.messages,
            predictions,
            goal="ACTION",
            utilities={"b": {"cross": "2", "wait": "0"}},
            beta="1",
            sincere=True,
        )
        self.assertEqual(actual_speaker["best_messages"], ("V",))
        self.assertNotIn("R", actual_speaker["policy"])

    def test_missing_prior_zero_likelihood_and_budget_never_become_uniform(self):
        unknown = message_game(("r", "b"), self.messages, None, beta="1", depth=1)
        self.assertFalse(unknown["listener"])
        self.assertEqual(unknown["literal_sets"]["V"], ("b", "r"))
        zero = message_game(
            ("r", "b"), self.messages, {"r": "1", "b": "0"}, beta="1", depth=1
        )
        self.assertFalse(zero["listener"]["B"])
        limited = message_game(
            ("r", "b"),
            self.messages,
            {"r": "1/2", "b": "1/2"},
            beta="1",
            depth=4,
            max_work=7,
        )
        self.assertEqual(limited["status"], "FRONTIER_UNEXPLORED")
        self.assertFalse(limited["listener"])
        self.assertLessEqual(limited["work"], 7)

    def test_false_belief_generated_by_m03_changes_sincere_report(self):
        model = EpistemicModel(
            ("safe",),
            ("a", "b"),
            {"r": {"safe": True}, "d": {"safe": False}},
            {"a": {"r": ("r",), "d": ("r",)}, "b": {"r": ("r", "d"), "d": ("r", "d")}},
            ("d",),
        )
        actual = remaining_states(model, ())
        speaker = remaining_states(model, ("a",))
        self.assertEqual([v["safe"] for v in actual["values"]], [False])
        self.assertEqual([v["safe"] for v in speaker["values"]], [True])
        predictions = {
            key: dict(posterior={state: 1}, actions={})
            for key, state in (("R", "r"), ("B", "b"))
        }
        result = speaker_choices(
            ("r",),
            None,
            self.messages[:2],
            predictions,
            goal="IDENTIFY",
            utilities={},
            beta="1",
            sincere=True,
        )
        self.assertEqual(result["best_messages"], ("R",))
        corrected = speaker_choices(
            ("b",),
            None,
            self.messages[:2],
            predictions,
            goal="IDENTIFY",
            utilities={},
            beta="1",
            sincere=True,
        )
        self.assertEqual(corrected["best_messages"], ("B",))

    def test_recipient_specific_interpretations_reuse_real_event_product(self):
        model = EpistemicModel(
            ("safe",),
            ("a", "b", "c"),
            {"r": {"safe": True}, "d": {"safe": False}},
            {a: {w: ("r", "d") for w in ("r", "d")} for a in ("a", "b", "c")},
            ("d",),
        )
        event = dict(
            id="m",
            assumptions=[],
            received_by=["b", "c"],
            understood_by=["b", "c"],
            trusted_by=["b", "c"],
        )
        readings = [
            dict(actor="b", contents=[dict(safe=True)]),
            dict(actor="c", contents=[dict(safe=False)]),
        ]
        updated, receipt = update_perspectives(
            model, interpreted_event(event, readings, model.agents)
        )
        self.assertIsNotNone(updated, receipt)
        self.assertEqual(
            {v["safe"] for v in remaining_states(updated, ("b",))["values"]}, {True}
        )
        self.assertEqual(
            {v["safe"] for v in remaining_states(updated, ("c",))["values"]}, {False}
        )
        self.assertEqual(
            {v["safe"] for v in remaining_states(updated, ())["values"]}, {False}
        )
        self.assertEqual(
            {v["safe"] for v in remaining_states(updated, ("a",))["values"]},
            {False, True},
        )

    def test_conflicting_new_readings_preserve_alternatives_not_just_prior_belief(self):
        model = EpistemicModel(
            ("safe",),
            ("a", "b"),
            {"only": {"safe": True}},
            {a: {"only": ("only",)} for a in ("a", "b")},
            ("only",),
        )
        event = dict(
            id="ambiguous",
            assumptions=[],
            received_by=["b"],
            understood_by=["b"],
            trusted_by=["b"],
        )
        readings = [dict(actor="b", contents=[{"safe": True}, {"safe": False}])]
        updated, receipt = update_perspectives(
            model, interpreted_event(event, readings, model.agents)
        )
        self.assertIsNotNone(updated, receipt)
        self.assertEqual(
            {v["safe"] for v in remaining_states(updated, ("b",))["values"]},
            {True, False},
        )
        self.assertEqual(
            {v["safe"] for v in remaining_states(updated, ())["values"]}, {True}
        )
        self.assertEqual(
            {v["safe"] for v in remaining_states(updated, ("a",))["values"]}, {True}
        )


class CommitmentTests(unittest.TestCase):
    def setUp(self):
        self.terms = dict(
            offer_id="offer",
            offer_literal={},
            offered_at=1,
            speaker="a",
            recipient="b",
            version="v1",
            deadline=5,
            requires_acceptance=True,
            acceptance="RECEIVED_BY_OFFEROR",
            activation="LATCHED",
            withdrawal="RECEIVED_RELEASE",
        )
        self.acts = [
            dict(
                id="accept",
                at=2,
                actor="b",
                kind="ACCEPT",
                refers_to="offer",
                version="v1",
            )
        ]
        self.deliveries = [
            dict(message_id="offer", actor="b", at=1),
            dict(message_id="accept", actor="a", at=2),
        ]
        self.interpretations = [
            dict(message_id="offer", actor="b", at=1, versions=["v1"], contents=[{}])
        ]
        self.facts = [
            dict(at=t, condition=(True,), outcome=(False,)) for t in (1, 2, 5, 6)
        ]

    def run_terms(self, through=6):
        return commitment_history(
            self.terms,
            self.facts,
            self.acts,
            self.deliveries,
            self.interpretations,
            through=through,
        )

    def test_late_acceptance_does_not_create_retroactive_breach_or_new_terms(self):
        self.acts[0]["at"] = 6
        self.deliveries[1]["at"] = 6
        result = self.run_terms()
        self.assertFalse(result["history"][-1]["accepted"])
        self.assertFalse(result["history"][-1]["breached"])
        self.assertIn("LATE_ACCEPTANCE_EFFECT_UNMODELED", result["frontier"])
        self.assertEqual(result["original_version"], "v1")

    def test_acceptance_receipt_and_latest_interpretation_have_separate_boundaries(
        self,
    ):
        self.deliveries[1]["at"] = 4
        result = self.run_terms()
        self.assertFalse(
            next(row for row in result["history"] if row["at"] == 2)["accepted"]
        )
        self.assertTrue(
            next(row for row in result["history"] if row["at"] == 4)["accepted"]
        )
        self.assertEqual(result["status"], "BREACHED")
        self.terms["acceptance"] = "QUALIFIED_ACT"
        result = self.run_terms()
        self.assertTrue(
            next(row for row in result["history"] if row["at"] == 2)["accepted"]
        )
        self.interpretations.append(
            dict(message_id="offer", actor="b", at=2, versions=["v2"], contents=[{}])
        )
        result = self.run_terms()
        self.assertFalse(result["history"][-1]["accepted"])
        self.assertEqual(result["original_version"], "v1")

    def test_wrong_version_withdrawal_cannot_release_original_terms(self):
        self.acts.append(
            dict(
                id="withdraw",
                at=3,
                actor="a",
                kind="WITHDRAW",
                refers_to="offer",
                version="v2",
            )
        )
        self.deliveries.append(dict(message_id="withdraw", actor="b", at=4))
        result = self.run_terms()
        self.assertEqual(result["status"], "BREACHED")
        self.assertFalse(result["history"][-1]["released"])
        self.assertIn("WITHDRAWAL_VERSION_MISMATCH", str(result["invalid_acts"]))

    def test_post_acceptance_refusal_and_simultaneous_acts_preserve_unresolved_effects(
        self,
    ):
        self.acts.append(
            dict(
                id="refuse",
                at=3,
                actor="b",
                kind="REFUSE",
                refers_to="offer",
                version="v1",
            )
        )
        result = self.run_terms()
        self.assertEqual(result["status"], "BREACHED")
        self.assertIn("POST_ACCEPTANCE_REFUSAL_EFFECT_UNMODELED", result["frontier"])
        self.acts[-1]["at"] = 2
        result = self.run_terms()
        self.assertFalse(result["history"][-1]["accepted"])
        self.assertFalse(result["history"][-1]["breached"])
        self.assertIn("SIMULTANEOUS_COMMITMENT_ACTS_UNORDERED", result["frontier"])

    def test_condition_latches_breach_survives_late_withdrawal(self):
        self.facts[-2]["condition"] = (False,)
        self.acts.append(
            dict(
                id="withdraw",
                at=6,
                actor="a",
                kind="WITHDRAW",
                refers_to="offer",
                version="v1",
            )
        )
        self.deliveries.append(dict(message_id="withdraw", actor="b", at=6))
        result = self.run_terms()
        self.assertEqual(result["status"], "BREACHED")
        self.assertTrue(result["history"][-1]["released"])

    def test_fulfillment_is_not_undone_by_later_state_or_withdrawal(self):
        self.facts[1]["outcome"] = (True,)
        result = self.run_terms()
        self.assertEqual(result["status"], "FULFILLED")
        self.assertFalse(result["history"][-1]["breached"])

    def test_late_receipt_or_different_interpretation_does_not_backfill_acceptance(
        self,
    ):
        self.deliveries[0]["at"] = 3
        result = self.run_terms()
        self.assertEqual(result["status"], "AWAITING_ACCEPTANCE")
        self.assertTrue(result["invalid_acts"])
        self.deliveries[0]["at"] = 1
        self.interpretations[0]["versions"] = ["v2"]
        self.assertEqual(self.run_terms()["status"], "AWAITING_ACCEPTANCE")

    def test_unknown_outcome_and_fulfillment_report_are_not_breach_or_completion(self):
        for fact in self.facts:
            fact["outcome"] = (False, True)
        self.acts.append(
            dict(
                id="report",
                at=5,
                actor="a",
                kind="REPORT_FULFILLED",
                refers_to="offer",
                version="v1",
            )
        )
        result = self.run_terms()
        self.assertEqual(result["status"], "ACTIVE")
        self.assertFalse(result["history"][-1]["fulfilled"])
        self.assertFalse(result["history"][-1]["breached"])

    def test_third_party_withdrawal_does_not_release_commitment(self):
        self.acts.append(
            dict(
                id="withdraw",
                at=3,
                actor="c",
                kind="WITHDRAW",
                refers_to="offer",
                version="v1",
            )
        )
        self.deliveries.append(dict(message_id="withdraw", actor="b", at=3))
        result = self.run_terms()
        self.assertEqual(result["status"], "BREACHED")
        self.assertFalse(result["history"][-1]["released"])

    def test_ack_chain_requires_each_historical_delivery_and_matching_version(self):
        messages = [
            dict(
                id=key,
                at=at,
                speaker=speaker,
                audience=[audience],
                version="v1",
                literal={},
            )
            for key, at, speaker, audience in (
                ("offer", 1, "a", "b"),
                ("meaning", 2, "b", "a"),
                ("confirm", 4, "a", "b"),
            )
        ]
        acts = [
            dict(
                id="meaning",
                at=2,
                actor="b",
                audience=["a"],
                kind="INTERPRET",
                refers_to="offer",
                version="v1",
            ),
            dict(
                id="confirm",
                at=4,
                actor="a",
                audience=["b"],
                kind="ACK",
                refers_to="meaning",
                version="v1",
            ),
        ]
        deliveries = [
            dict(message_id="offer", actor="b", at=1),
            dict(message_id="meaning", actor="a", at=3),
        ]
        self.interpretations.append(
            dict(message_id="meaning", actor="a", at=3, versions=["v1"], contents=[{}])
        )
        self.interpretations.append(
            dict(message_id="confirm", actor="b", at=6, versions=["v1"], contents=[{}])
        )
        result = acknowledgment_chains(
            messages, acts, deliveries, self.interpretations, through=5
        )
        self.assertEqual(result["chains"][-1]["depth"], 2)
        self.assertFalse(result["chains"][-1]["complete"])
        deliveries.append(dict(message_id="confirm", actor="b", at=6))
        self.assertTrue(
            acknowledgment_chains(
                messages, acts, deliveries, self.interpretations, through=6
            )["chains"][-1]["complete"]
        )
        mismatched = deepcopy(self.interpretations)
        mismatched.append(
            dict(message_id="confirm", actor="b", at=6, versions=["v2"], contents=[{}])
        )
        self.assertFalse(
            acknowledgment_chains(messages, acts, deliveries, mismatched, through=6)[
                "chains"
            ][-1]["complete"]
        )
        wrong_content = deepcopy(self.interpretations)
        next(i for i in wrong_content if i["message_id"] == "meaning")["contents"] = [
            {"different": True}
        ]
        denied = acknowledgment_chains(
            messages, acts, deliveries, wrong_content, through=6
        )
        self.assertIn("ACK_CONTENT_NOT_INTERPRETED", str(denied["diagnostics"]))
        missing = [i for i in self.interpretations if i["message_id"] != "meaning"]
        uncomprehended = acknowledgment_chains(
            messages, acts, deliveries, missing, through=6
        )
        self.assertEqual(len(uncomprehended["chains"]), 1)
        self.assertIn("ACK_CONTENT_NOT_INTERPRETED", str(uncomprehended["diagnostics"]))
        deliveries[1]["at"] = 5
        delayed = acknowledgment_chains(
            messages, acts, deliveries, self.interpretations, through=6
        )
        self.assertEqual(len(delayed["chains"]), 1)
        self.assertIn("PRIOR_MESSAGE_NOT_RECEIVED_AT_ACK", str(delayed["diagnostics"]))


if __name__ == "__main__":
    unittest.main()
