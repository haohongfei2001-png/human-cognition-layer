"""B02: exposure paths change real model inputs before semantic generation."""
import json
import unittest
from hcl.cognition import CommunicationScene, Attitude
from hcl.v06.perspective import event_accessible_to

M = 'Mira said, "I believe the gate is open."'
N = 'Noor said, "I do not believe the gate is open."'
K = 'Kai said, "I am unsure whether the road is safe."'


class SpyBackend:
    def __init__(self):
        self.inputs = []

    def complete_json(self, messages, **kwargs):
        self.inputs.append(messages)
        return '{"candidates": []}'


class CommunicationViewTests(unittest.TestCase):
    def scene(self):
        return CommunicationScene('\n'.join((M, "Narrator: Noor heard Mira's last statement.",
            "Narrator: Kai missed Mira's last statement.",
            "Narrator: Mira's last statement was publicly available.", N, K)))

    def test_positive_three_people_get_distinct_real_epistemic_inputs(self):
        scene = self.scene()
        mira, noor, kai = (scene.view(actor) for actor in ('Mira', 'Noor', 'Kai'))
        self.assertEqual(mira.visible_text, M)
        self.assertEqual(noor.visible_text, M + '\n' + N)
        self.assertEqual(kai.visible_text, K)
        for view in (mira, noor, kai):
            w, b = view.epistemic('What was expressed?')
            wire = b.messages(w.core, 'What was expressed?')
            self.assertNotIn('comprehension is established', str(wire))
            self.assertTrue(all(event_accessible_to(e, view.actor) for e in view.events))
        w, b = noor.epistemic('What does Mira believe?')
        self.assertEqual(b.project(w.core, ('Mira',), attitude=Attitude.BELIEF)[0]['result'], 'SOURCE_REPORTED_AFFIRM')
        self.assertFalse(b.project(w.core, ('Noor',), attitude=Attitude.BELIEF))  # query-selected Mira only
        w, b = kai.epistemic('What does Mira believe?')
        self.assertFalse(b.records)

    def test_hearing_does_not_create_listener_belief_or_understanding(self):
        view = CommunicationScene(M + "\nNarrator: Noor heard Mira's last statement.").view('Noor')
        w, b = view.epistemic('Compare the available expressions.')
        self.assertFalse(b.project(w.core, ('Noor',), attitude=Attitude.BELIEF))
        self.assertFalse(b.project(w.core, ('Noor',), attitude=Attitude.UNDERSTANDING))
        self.assertEqual(view.access_audit[0]['comprehension'], 'NOT_ESTABLISHED')
        self.assertEqual(view.access_audit[0]['acceptance'], 'NOT_ESTABLISHED')

    def test_public_availability_is_not_exposure_and_calls_no_backend(self):
        view = CommunicationScene(M + "\nNarrator: Mira's last statement was publicly available.").view('Noor')
        self.assertFalse(view.events)
        self.assertEqual(view.access_audit[0]['status'], 'PUBLIC_AVAILABILITY_EXPOSURE_UNKNOWN')
        backend = SpyBackend()
        _, result = view.semantic('What can Noor access?', backend=backend)
        self.assertFalse(backend.inputs)
        self.assertEqual(result.backend_calls, 0)
        self.assertNotIn(M, result.final_messages_json)

    def test_addressed_private_message_requires_separate_read_receipt(self):
        text = '\n'.join((M, 'Narrator: Mira sent their last statement privately to Noor.',
                          "Narrator: Noor read Mira's last statement."))
        scene = CommunicationScene(text)
        before, after = scene.view('Noor', through_line=2), scene.view('Noor')
        self.assertEqual(before.access_audit[0]['status'], 'ADDRESSED_RECEIPT_UNKNOWN')
        self.assertFalse(before.events)
        self.assertEqual(after.visible_text, M)
        self.assertFalse(scene.view('Kai').events)

    def test_explicit_later_receipt_adds_access_without_changing_earlier_snapshot(self):
        text = '\n'.join((M, "Narrator: Noor missed Mira's last statement.",
                          "Narrator: Noor later heard Mira's last statement."))
        scene = CommunicationScene(text)
        earlier, later = scene.view('Noor', through_line=2), scene.view('Noor')
        self.assertEqual(earlier.access_audit[0]['status'], 'REPORTED_NON_EXPOSURE')
        self.assertEqual(later.access_audit[0]['status'], 'REPORTED_LATER_EXPOSURE')
        self.assertFalse(earlier.events)
        self.assertEqual(later.visible_text, M)
        self.assertFalse(scene.view('Noor', through_line=2).events)

    def test_conflicting_receipt_reports_do_not_guess_access_or_unlearning(self):
        scene = CommunicationScene('\n'.join((M, "Narrator: Noor heard Mira's last statement.",
            "Narrator: Noor did not hear Mira's last statement.")))
        self.assertEqual(scene.view('Noor', through_line=2).visible_text, M)
        disputed = scene.view('Noor')
        self.assertEqual(disputed.access_audit[0]['status'], 'CONFLICTING_EXPOSURE_REPORTS')
        self.assertFalse(disputed.events)
        self.assertNotIn('Noor forgot', str(disputed.access_audit))

    def test_hidden_content_changes_do_not_change_backend_or_epistemic_inputs(self):
        text = '\n'.join((M, "Narrator: Noor heard Mira's last statement.", K,
                          "Narrator: Noor missed Kai's last statement."))
        before = CommunicationScene(text).view('Noor')
        after = CommunicationScene(text.replace('the road is safe', 'the river is impassable')).view('Noor')
        a, b = SpyBackend(), SpyBackend()
        _, first = before.semantic('What was expressed?', backend=a)
        _, second = after.semantic('What was expressed?', backend=b)
        self.assertEqual(a.inputs, b.inputs)
        self.assertEqual(first.messages, second.messages)
        self.assertEqual(before.events, after.events)
        self.assertNotIn('river', str(b.inputs))

    def test_unrelated_hidden_insertion_does_not_change_visible_event_identity(self):
        text = M + "\nNarrator: Noor heard Mira's last statement."
        before = CommunicationScene(text).view('Noor')
        after = CommunicationScene(K + '\n' + text).view('Noor')
        self.assertEqual(before.events, after.events)
        w1, b1 = before.epistemic('What does Mira believe?')
        w2, b2 = after.epistemic('What does Mira believe?')
        self.assertEqual(b1.messages(w1.core, 'What does Mira believe?'), b2.messages(w2.core, 'What does Mira believe?'))

    def test_future_source_not_parsed_into_earlier_snapshot(self):
        text = M + "\nNarrator: Noor heard Mira's last statement.\nUnparseable future material."
        view = CommunicationScene(text).view('Noor', through_line=2)
        self.assertEqual(view.visible_text, M)
        with self.assertRaises(ValueError):
            CommunicationScene(text).view('Noor')

    def test_previous_reference_is_adjacent_and_named_last_reference_is_source_bound(self):
        self.assertEqual(CommunicationScene(M + '\nNarrator: Noor heard the previous statement.').view('Noor').visible_text, M)
        for text in ('Narrator: Noor heard the previous statement.',
            M + "\nNarrator: Noor heard Kai's last statement.",
            M + '\nNarrator: Noor heard the previous statement.\nNarrator: Kai heard the previous statement.'):
            with self.assertRaises(ValueError):
                CommunicationScene(text).view('Noor')

    def test_ambiguous_hypothetical_or_duplicate_recipient_access_rejected(self):
        for cue in ("Narrator: Noor probably heard Mira's last statement.",
                    "Narrator: Noor and Noor heard Mira's last statement.",
                    "Narrator: Noor later missed Mira's last statement."):
            with self.assertRaises(ValueError):
                CommunicationScene(M + '\n' + cue).view('Noor')

    def test_multiple_explicit_recipients_and_empty_past_snapshot(self):
        scene = CommunicationScene(M + "\nNarrator: Noor and Kai heard Mira's last statement.")
        self.assertEqual(scene.view('Noor').visible_text, M)
        self.assertEqual(scene.view('Kai').visible_text, M)
        empty = scene.view('Noor', through_line=0)
        self.assertFalse(empty.events)
        w, b = empty.epistemic('What does Mira believe?')
        self.assertFalse(b.records)
        self.assertEqual(json.loads(b.messages(w.core, 'What does Mira believe?')[-1]['content'])['epistemic_objects'], [])
