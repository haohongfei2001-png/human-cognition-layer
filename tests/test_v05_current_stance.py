"""Provider-free tests for HCL v0.5 issue-centered stance state."""

from __future__ import annotations

import unittest

from hcl.v05 import (
    StanceEvent,
    StanceSignal,
    StanceStatus,
    project_current_stance,
)


def ev(
    event_id,
    minute,
    signal,
    value,
    *,
    prior=None,
    subject="agent",
    issue="route",
):
    valid = f"2026-01-01T10:{minute:02d}:00+00:00"
    recorded = f"2026-01-01T10:{minute:02d}:01+00:00"
    return StanceEvent(
        event_id=event_id,
        subject_agent_id=subject,
        issue_key=issue,
        signal=signal,
        value_key=value,
        prior_value_key=prior,
        valid_time=valid,
        system_record_time=recorded,
        evidence_event_ids=(event_id,),
    )


class CurrentStanceCoreTests(unittest.TestCase):
    def test_later_affirm_closes_received_revision_uncertainty(self):
        events = [
            ev("a1", 1, StanceSignal.AFFIRM, "RED"),
            ev("r1", 2, StanceSignal.REVISION_EXPOSURE, "BLUE", prior="RED"),
            ev("u1", 3, StanceSignal.UNRESOLVED, "BLUE"),
            ev("a2", 4, StanceSignal.AFFIRM, "BLUE"),
        ]
        state = project_current_stance(
            events, subject_agent_id="agent", issue_key="route"
        )
        self.assertEqual(state.status, StanceStatus.AFFIRMED)
        self.assertEqual(state.affirmed_value_key, "BLUE")
        self.assertIsNone(state.pending_revision_value_key)

    def test_repeated_confirmation_of_accepted_revision_does_not_reopen(self):
        events = [
            ev("a1", 1, StanceSignal.AFFIRM, "RED"),
            ev("r1", 2, StanceSignal.REVISION_EXPOSURE, "BLUE", prior="RED"),
            ev("a2", 3, StanceSignal.AFFIRM, "BLUE"),
            ev("r2", 4, StanceSignal.REVISION_EXPOSURE, "BLUE", prior="RED"),
        ]
        state = project_current_stance(
            events, subject_agent_id="agent", issue_key="route"
        )
        self.assertEqual(state.status, StanceStatus.AFFIRMED)
        self.assertEqual(state.affirmed_value_key, "BLUE")
        self.assertIsNone(state.pending_revision_value_key)

    def test_rejecting_pending_revision_restores_suspended_value(self):
        events = [
            ev("a1", 1, StanceSignal.AFFIRM, "BETA"),
            ev("r1", 2, StanceSignal.REVISION_EXPOSURE, "GAMMA", prior="BETA"),
            ev("d1", 3, StanceSignal.DENY, "GAMMA"),
        ]
        state = project_current_stance(
            events, subject_agent_id="agent", issue_key="route"
        )
        self.assertEqual(state.status, StanceStatus.AFFIRMED)
        self.assertEqual(state.affirmed_value_key, "BETA")
        self.assertIn("GAMMA", state.rejected_value_keys)
        self.assertIsNone(state.pending_revision_value_key)

    def test_affirm_old_and_deny_new_same_time_projects_old(self):
        base = [
            ev("a1", 1, StanceSignal.AFFIRM, "BETA"),
            ev("r1", 2, StanceSignal.REVISION_EXPOSURE, "GAMMA", prior="BETA"),
        ]
        same_valid = "2026-01-01T10:03:00+00:00"
        same_recorded = "2026-01-01T10:03:01+00:00"
        base.extend(
            [
                StanceEvent(
                    event_id="affirm-old",
                    subject_agent_id="agent",
                    issue_key="route",
                    signal=StanceSignal.AFFIRM,
                    value_key="BETA",
                    valid_time=same_valid,
                    system_record_time=same_recorded,
                ),
                StanceEvent(
                    event_id="deny-new",
                    subject_agent_id="agent",
                    issue_key="route",
                    signal=StanceSignal.DENY,
                    value_key="GAMMA",
                    valid_time=same_valid,
                    system_record_time=same_recorded,
                ),
            ]
        )
        state = project_current_stance(
            base, subject_agent_id="agent", issue_key="route"
        )
        self.assertEqual(state.status, StanceStatus.AFFIRMED)
        self.assertEqual(state.affirmed_value_key, "BETA")
        self.assertIn("GAMMA", state.rejected_value_keys)

    def test_other_agents_world_revision_does_not_change_target(self):
        events = [
            ev("a1", 1, StanceSignal.AFFIRM, "BLUE", subject="target"),
            ev(
                "other-revision",
                2,
                StanceSignal.REVISION_EXPOSURE,
                "GREEN",
                prior="BLUE",
                subject="other",
            ),
        ]
        state = project_current_stance(
            events, subject_agent_id="target", issue_key="route"
        )
        self.assertEqual(state.status, StanceStatus.AFFIRMED)
        self.assertEqual(state.affirmed_value_key, "BLUE")

    def test_historical_cutoff_replays_state_not_present_answer(self):
        events = [
            ev("a1", 1, StanceSignal.AFFIRM, "RED"),
            ev("r1", 2, StanceSignal.REVISION_EXPOSURE, "BLUE", prior="RED"),
            ev("a2", 3, StanceSignal.AFFIRM, "BLUE"),
        ]
        historical = project_current_stance(
            events,
            subject_agent_id="agent",
            issue_key="route",
            event_time="2026-01-01T10:02:30+00:00",
        )
        current = project_current_stance(
            events, subject_agent_id="agent", issue_key="route"
        )
        self.assertEqual(historical.status, StanceStatus.UNRESOLVED)
        self.assertEqual(historical.pending_revision_value_key, "BLUE")
        self.assertEqual(current.status, StanceStatus.AFFIRMED)
        self.assertEqual(current.affirmed_value_key, "BLUE")

    def test_conflicting_affirms_fail_closed(self):
        same_valid = "2026-01-01T10:01:00+00:00"
        same_recorded = "2026-01-01T10:01:01+00:00"
        events = [
            StanceEvent(
                event_id="a-red",
                subject_agent_id="agent",
                issue_key="route",
                signal=StanceSignal.AFFIRM,
                value_key="RED",
                valid_time=same_valid,
                system_record_time=same_recorded,
            ),
            StanceEvent(
                event_id="a-blue",
                subject_agent_id="agent",
                issue_key="route",
                signal=StanceSignal.AFFIRM,
                value_key="BLUE",
                valid_time=same_valid,
                system_record_time=same_recorded,
            ),
        ]
        state = project_current_stance(
            events, subject_agent_id="agent", issue_key="route"
        )
        self.assertEqual(state.status, StanceStatus.CONFLICT)
        self.assertIsNone(state.affirmed_value_key)


if __name__ == "__main__":
    unittest.main()
