"""Generic narrative control retains all source events and uncertainty."""

from __future__ import annotations

import unittest

from hcl.v07.generic_narrative import GenericNarrativeState
from scripts.run_v07_saga_dev_v01 import narrative_events


class GenericNarrativeTests(unittest.TestCase):
    def test_complete_question_blind_timeline_with_source_and_actor_surface(self):
        story = "\n".join([
            "Mira wanted to finish the mural.",
            "Mira bought paint.",
            "Rain began outside.",
            "Mira covered the canvas.",
            "She returned the next day.",
        ])
        state = GenericNarrativeState.from_events(narrative_events(story, "synthetic")).as_dict()
        self.assertEqual(state["event_count"], 5)
        self.assertEqual([x["event_text"] for x in state["timeline"]], story.split("\n"))
        self.assertEqual(state["timeline"][0]["actor_surface"], "Mira")
        self.assertIsNone(state["timeline"][4]["actor_surface"])
        self.assertEqual(state["timeline"][0]["provenance"], "READER_ONLY_NARRATOR")
        self.assertIn("Mira", state["entities"])
        self.assertNotIn("goal_estimates", state)


if __name__ == "__main__":
    unittest.main()
