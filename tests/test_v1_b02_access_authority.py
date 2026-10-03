"""B02 receipts and visible statements require the same source-prefix authority."""
import unittest
from unittest.mock import patch

from hcl.cognition import CognitionWorkspace
from hcl.cognition.communication import CommunicationScene
from hcl.cognition.commitments import prepare_commitment
from hcl.cognition.semantic import _local_candidates

PROMISE = 'Mira said, "I promise Noor to deliver the report if the permit arrives."'
SPEECH = 'Mira said, "I believe the gate is open."'
OTHER = 'Mira said, "I believe the road is safe."'
CUE = "Narrator: Noor heard Mira's last statement."
HYPOTHETICAL = 'Narrator: In a hypothetical scene:'
ACTUAL = 'Narrator: In reality:'
QUERY = "What is the status of Mira's promise to Noor to deliver the report?"


class CommunicationAuthorityTests(unittest.TestCase):
    def view(self, *lines, actor='Noor', through_line=None):
        return CommunicationScene('\n'.join(lines), source_id='scene').view(actor, through_line=through_line)

    def test_actual_absent_negative_and_resumed_receipts(self):
        self.assertEqual(self.view(SPEECH).access_audit[0]['status'], 'EXPOSURE_UNKNOWN')
        self.assertEqual(self.view(SPEECH, CUE).visible_text, SPEECH)
        negative = CUE.replace('heard', 'did not hear')
        self.assertEqual(self.view(SPEECH, negative).access_audit[0]['status'], 'REPORTED_NON_EXPOSURE')
        resumed = self.view(SPEECH, HYPOTHETICAL, ACTUAL, CUE)
        self.assertEqual(resumed.visible_text, SPEECH)
        self.assertFalse(resumed.access_audit[-1]['content_transmitted'])
        self.assertEqual(resumed.access_audit[-1]['status'], 'EXPOSURE_UNKNOWN')

    def test_nonactual_access_cues_refuse_instead_of_granting_receipt(self):
        for prefix in (HYPOTHETICAL, 'Narrator: Counterfactually:', 'Narrator: This scene is imagined.'):
            for cue in (CUE, CUE.replace('heard', 'did not hear'),
                        "Narrator: Mira's last statement was publicly available.",
                        'Narrator: Mira sent their last statement privately to Noor.'):
                with self.subTest(prefix=prefix, cue=cue), self.assertRaises(ValueError):
                    self.view(SPEECH, prefix, cue)

    def test_nonactual_latest_target_refuses_all_cue_kinds_without_older_fallback(self):
        for cue in (CUE, CUE.replace('heard', 'did not hear'),
                    "Narrator: Mira's last statement was publicly available.",
                    'Narrator: Mira sent their last statement privately to Noor.'):
            with self.subTest(cue=cue), self.assertRaises(ValueError):
                self.view(SPEECH, HYPOTHETICAL, OTHER, ACTUAL, cue)

    def test_nonactual_own_expression_refuses_without_any_receipt(self):
        with self.assertRaises(ValueError):
            self.view(SPEECH, HYPOTHETICAL, OTHER, actor='Mira')
        self.assertEqual(self.view(SPEECH, HYPOTHETICAL, OTHER).visible_text, '')

    def test_resumption_marker_cannot_be_targeted_as_a_statement(self):
        for cue in ('Narrator: Noor heard the previous statement.',
                    "Narrator: Noor heard Narrator's last statement."):
            with self.subTest(cue=cue), self.assertRaises(ValueError):
                self.view(SPEECH, HYPOTHETICAL, ACTUAL, cue)

    def test_actual_discussion_and_actor_labels_do_not_establish_scene_scope(self):
        actual = 'Mira said, "In a hypothetical scene, I would leave."'
        self.assertEqual(self.view(actual, CUE).visible_text, actual)
        self.assertEqual(self.view(SPEECH, 'Hypothetically: Ordinary words.', CUE).visible_text, SPEECH)
        with self.assertRaises(ValueError):
            self.view(SPEECH, HYPOTHETICAL, 'In Reality: Ordinary words.', CUE)

    def test_existing_embedded_or_unsupported_line_refusals_remain(self):
        for lines in ((SPEECH, '```', CUE, '```'), (SPEECH, '[' + CUE + ']'),
                      (SPEECH, '"' + CUE + '"'), (SPEECH, CUE.replace('heard', 'probably heard'))):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                self.view(*lines)

    def test_prefix_authority_never_reads_future_into_an_earlier_view(self):
        text = '\n'.join((SPEECH, CUE, HYPOTHETICAL, OTHER, 'Unparseable future material.'))
        scene = CommunicationScene(text)
        with patch('hcl.cognition.communication._local_candidates', wraps=_local_candidates) as parse:
            self.assertEqual(scene.view('Noor', through_line=2).visible_text, SPEECH)
            self.assertEqual(parse.call_count, 1)
            self.assertEqual(parse.call_args.args[0].text, '\n'.join((SPEECH, CUE)))
        self.assertFalse(scene.view('Noor', through_line=0).events)
        with self.assertRaises(ValueError):
            scene.view('Noor')

    def test_original_whitespace_crlf_proofs_and_event_identity_are_preserved(self):
        expected = self.view(SPEECH, CUE)
        text = '\t' + SPEECH + '  \r\n  ' + CUE + '\t\r\n'
        actual = CommunicationScene(text, source_id='scene').view('Noor')
        self.assertEqual(actual.events, expected.events)
        self.assertEqual(actual.access_audit[0]['relevant_access_proofs'][0]['quote'], '  ' + CUE + '\t')
        self.assertEqual(actual.access_audit[0]['relevant_access_proofs'][0]['source_line'], 2)
        with self.assertRaises(ValueError):
            CommunicationScene('\t' + SPEECH + '\r\n ' + HYPOTHETICAL + '\r\n  ' + CUE).view('Noor')

    def test_repeated_cue_occurrences_cannot_borrow_actual_authority(self):
        lines = (SPEECH, CUE, HYPOTHETICAL, CUE, ACTUAL, CUE)
        self.assertEqual(self.view(*lines, through_line=2).visible_text, SPEECH)
        with self.assertRaises(ValueError):
            self.view(*lines, through_line=4)
        with self.assertRaises(ValueError):
            self.view(*lines)

    def test_ineligible_speaker_still_counts_towards_native_actor_budget(self):
        names = ('Mira', 'Kai', 'Tess', 'Lina', 'Omar', 'Rae', 'Zed', 'Ivo')
        lines = tuple(f'{name} said, "Ordinary words."' for name in names[:-1])
        with self.assertRaisesRegex(ValueError, 'actor budget'):
            self.view(*lines, HYPOTHETICAL, f'{names[-1]} said, "Ordinary words."')
        self.assertFalse(self.view(*lines, HYPOTHETICAL).events)

    def test_cross_line_candidate_cannot_be_recovered_as_one_line(self):
        with self.assertRaises(ValueError):
            self.view('Mira:', 'Noor said, "Ordinary words."', CUE)

    def test_unsupported_intervening_source_does_not_fall_back_to_older_speech(self):
        with self.assertRaises(ValueError):
            self.view(SPEECH, 'Mira perhaps said something else.', CUE)

    def test_d01_hypothetical_receipt_is_not_conditions_received(self):
        w = CognitionWorkspace()
        w.put_source('scene', '\n'.join((PROMISE, HYPOTHETICAL, CUE)))
        with self.assertRaises(ValueError):
            prepare_commitment(w, QUERY, source_id='scene')
        w.put_source('scene', '\n'.join((PROMISE, HYPOTHETICAL, ACTUAL, CUE)))
        result = prepare_commitment(w, QUERY, source_id='scene')
        self.assertTrue(result.payload['commitment']['conditions_received'])
        self.assertEqual(result.payload['commitment']['private_understanding'], 'NOT_ESTABLISHED')
        self.assertEqual(result.payload['commitment']['obligation'], 'NOT_ESTABLISHED')


if __name__ == '__main__':
    unittest.main()
