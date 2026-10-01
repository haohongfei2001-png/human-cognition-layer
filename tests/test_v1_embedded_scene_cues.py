"""Embedded example/direction text cannot change the outer narrator scene."""
import json
import unittest
from hcl.cognition import CognitionWorkspace
from hcl.cognition.semantic import AuthorizedText, _local_candidates

PREFIX = 'The following conversation was imagined.\n\n'
SPEECH = 'Noor said, “I believe the gate is clear.”'
QUESTION = 'Which views does this account report?'


def prepare(source):
    workspace = CognitionWorkspace()
    workspace.put_source('scene', source)
    entry = workspace.prepare_reader_entry(QUESTION, source_ids=('scene',))
    return workspace, entry, json.loads(entry.messages[-1]['content'])


class EmbeddedSceneCueTests(unittest.TestCase):
    def test_embedded_actual_cue_cannot_restore_imagined_speech(self):
        for embedded in ('[Direction. In reality, a bell rang.]',
                         '[Direction.\nIn the actual scene, a bell rang.]',
                         '```\nIn reality, a bell rang.\n```',
                         '```text\nIn the actual conversation, a bell rang.\n```'):
            with self.subTest(embedded=embedded):
                source = PREFIX + embedded + '\n\n' + SPEECH
                _, entry, payload = prepare(source)
                self.assertFalse(entry.receipt['checked_treatment_present'])
                events = [c['content'] for c in _local_candidates(AuthorizedText('scene', source))
                          if c['content'].get('event_kind') == 'SPEECH_REPORT']
                self.assertEqual([e['assertion_scope'] for e in events], ['CONDITIONAL_OR_EMBEDDED'])
                self.assertEqual(payload['sources'][0]['text'], source)
                self.assertEqual(entry.receipt['extraction_calls'], 0)

    def test_real_transition_after_embedded_example_still_restores_speech(self):
        source = PREFIX + '[Direction. In reality, a bell rang.]\n\n' + SPEECH
        source += '\n\nIn reality, Eva said, “I believe the gate is blocked.”'
        _, _, payload = prepare(source)
        reports = payload['checked_epistemic']['epistemic_objects']
        self.assertEqual([r['speaker'] for r in reports], ['Eva'])

    def test_embedded_hypothetical_declaration_does_not_suspend_actual_speech(self):
        for example in ('[Example. This scene is hypothetical.]',
                        '```\nThis conversation is imagined.\n```'):
            with self.subTest(example=example):
                _, entry, payload = prepare(example + '\n\n' + SPEECH)
                self.assertTrue(entry.receipt['checked_treatment_present'])
                self.assertEqual([r['speaker'] for r in payload['checked_epistemic']['epistemic_objects']], ['Noor'])

    def test_real_later_declaration_still_suspends_speech(self):
        source = '[Example. This scene is hypothetical.]\n\n' + SPEECH
        source += '\n\nThis conversation is imagined.\n\nEva said, “I believe the gate is blocked.”'
        _, _, payload = prepare(source)
        self.assertEqual([r['speaker'] for r in payload['checked_epistemic']['epistemic_objects']], ['Noor'])

    def test_revision_from_actual_to_embedded_invalidates_prepared_state(self):
        workspace, old, _ = prepare(PREFIX + 'In reality, a bell rang.\n\n' + SPEECH)
        workspace.put_source('scene', PREFIX + '[Direction. In reality, a bell rang.]\n\n' + SPEECH)
        with self.assertRaises(ValueError):
            old.current_messages(workspace)
        new = workspace.prepare_reader_entry(QUESTION, source_ids=('scene',))
        self.assertFalse(new.receipt['checked_treatment_present'])

    def test_spoken_delimiters_do_not_embed_later_real_transition(self):
        for utterance in ('I wrote [ in my notebook.', 'I wrote ``` in my notebook.'):
            with self.subTest(utterance=utterance):
                source = PREFIX + 'Eva said, “' + utterance + '”\n\nIn reality, a bell rang.\n\n' + SPEECH
                _, _, payload = prepare(source)
                self.assertEqual([r['speaker'] for r in payload['checked_epistemic']['epistemic_objects']], ['Noor'])


if __name__ == '__main__':
    unittest.main()
