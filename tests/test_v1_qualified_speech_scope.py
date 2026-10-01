"""Hypothetical source scope must not become an actual public expression."""
import json
import unittest

from hcl.cognition import CognitionWorkspace
from hcl.cognition.core import EvidenceCore
from hcl.cognition.semantic import AuthorizedText, prepare_semantics


QUESTION = 'Which views does this account report?'
SPEECH = 'Eva said, “I believe the gate is clear.”'


def prepare(source):
    workspace = CognitionWorkspace()
    workspace.put_source('scene', source)
    entry = workspace.prepare_reader_entry(QUESTION, source_ids=('scene',))
    return workspace, entry, json.loads(entry.messages[-1]['content'])


class QualifiedSpeechScopeTests(unittest.TestCase):
    def test_explicit_inline_qualifiers_do_not_create_actual_expressions(self):
        for prefix in ('In a hypothetical scenario, ', 'Within this counterfactual scene, ',
                       'Hypothetically, ', 'Counterfactually: '):
            with self.subTest(prefix=prefix):
                source = prefix + SPEECH
                _, entry, payload = prepare(source)
                self.assertFalse(entry.receipt['checked_treatment_present'])
                self.assertEqual(entry.receipt['extraction_calls'], 0)
                self.assertEqual(payload['sources'][0]['text'], source)
                self.assertNotIn('checked_epistemic', payload)

    def test_explicit_scene_preamble_qualifies_following_speech(self):
        for prefix in ('The following conversation was imagined. ',
                       'This dialogue is counterfactual.\n', 'Hypothetical dialogue:\n\n'):
            with self.subTest(prefix=prefix):
                _, entry, payload = prepare(prefix + SPEECH)
                self.assertFalse(entry.receipt['checked_treatment_present'])
                self.assertNotIn('checked_epistemic', payload)

    def test_soft_wraps_preserve_the_inline_qualification(self):
        for prefix in ('In a hypothetical scenario,\n', 'In a hypothetical\nscenario, ',
                       'Within this counterfactual\r\nscene, '):
            with self.subTest(prefix=prefix):
                _, entry, _ = prepare(prefix + SPEECH)
                self.assertFalse(entry.receipt['checked_treatment_present'])

    def test_coordinated_quoted_turns_share_the_outer_qualification(self):
        for lead in ('In a hypothetical scenario, ', 'If '):
            for punctuation in ('', '.'):
                with self.subTest(lead=lead, punctuation=punctuation):
                    source = lead + 'Eva said, “I believe the gate is clear' + punctuation + \
                        '”, and Noor said, “I believe the gate is blocked.”'
                    _, entry, _ = prepare(source)
                    self.assertFalse(entry.receipt['checked_treatment_present'])

    def test_coordinated_hypothetical_plan_cannot_join_actual_state(self):
        source = ('In a hypothetical scenario, Eva said, “I believe the gate is clear”, '
                  'and Noor said, “I plan to call Eva in order to protect the garden if the gate is clear.”\n'
                  'Noor said, “I have an opportunity to call Eva.”\n'
                  'Noor said, “I believe the gate is clear.”')
        _, _, payload = prepare(source)
        self.assertNotIn('checked_plan_feasibility', payload)

    def test_actual_discussion_of_hypotheticals_is_not_a_scene_qualification(self):
        sources = [SPEECH,
            'After reading a hypothetical example, ' + SPEECH,
            'Eva said, “The following conversation was imagined.”\n'
                'Noor said, “I believe the gate is blocked.”',
            'Eva said, “I could imagine a different answer”\n'
                'Noor said, “I believe the gate is blocked.”']
        for source in sources:
            with self.subTest(source=source):
                _, entry, payload = prepare(source)
                self.assertTrue(entry.receipt['checked_treatment_present'])
                speakers = {r['speaker'] for r in payload['checked_epistemic']['epistemic_objects']}
                self.assertIn('Noor' if 'Noor' in source else 'Eva', speakers)

    def test_colon_and_script_utterances_are_not_narration_cues(self):
        sources = [
            'Eva: I disagree. The following conversation was imagined.\nNoor: I believe the gate is blocked.',
            '_Eva._ I disagree. The following conversation was imagined.\n\n_Noor._ I believe the gate is blocked.',
            'Eva: We might discuss a hypothetical scenario\nNoor said, “I believe the gate is blocked.”',
        ]
        for source in sources:
            with self.subTest(source=source):
                _, entry, payload = prepare(source)
                self.assertTrue(entry.receipt['checked_treatment_present'])
                speakers = {r['speaker'] for r in payload['checked_epistemic']['epistemic_objects']}
                self.assertIn('Noor', speakers)

    def test_spoken_reality_phrase_does_not_end_the_narrator_hypothetical(self):
        for turns in (
            'Eva: We need context. In reality, nothing is settled.\nNoor: I believe the gate is blocked.',
            '_Eva._ We need context. In reality, nothing is settled.\n\n_Noor._ I believe the gate is blocked.',
            'Eva said, “In reality, nothing is settled.” Noor said, “I believe the gate is blocked.”',
        ):
            with self.subTest(turns=turns):
                _, entry, _ = prepare('The following conversation was imagined.\n' + turns)
                self.assertFalse(entry.receipt['checked_treatment_present'])

    def test_explicit_actual_scene_resumes_without_promoting_prior_hypothetical(self):
        source = 'The following conversation was imagined. ' + SPEECH + \
            ' In reality, Noor said, “I believe the gate is blocked.”'
        _, _, payload = prepare(source)
        self.assertEqual([r['speaker'] for r in payload['checked_epistemic']['epistemic_objects']], ['Noor'])
        self.assertEqual(payload['sources'][0]['text'], source)

    def test_qualified_plan_does_not_join_actual_opportunity_and_belief(self):
        source = ('In a hypothetical scenario, Eva said, “I plan to call Noor in order to '
                  'protect the garden if the gate is clear.”\n'
                  'Eva said, “I have an opportunity to call Noor.”\n' + SPEECH)
        _, _, payload = prepare(source)
        for actor in payload.get('checked_plan_feasibility', []):
            self.assertEqual(actor['plans'], [])
        self.assertNotIn('checked_plan_feasibility', payload)

    def test_source_revision_cannot_reuse_the_prequalification_expression(self):
        workspace, original, _ = prepare(SPEECH)
        workspace.put_source('scene', 'In a hypothetical scenario, ' + SPEECH)
        with self.assertRaises(ValueError):
            original.current_messages(workspace)
        revised = workspace.prepare_reader_entry(QUESTION, source_ids=('scene',))
        self.assertFalse(revised.receipt['checked_treatment_present'])
        self.assertEqual(json.loads(revised.messages[-1]['content'])['sources'][0]['version'], 2)

    def test_backend_literal_envelope_cannot_remove_source_qualification(self):
        source = 'In a counterfactual scenario, ' + SPEECH
        class Stub:
            def complete_json(self, messages, **kwargs):
                return json.dumps(dict(candidates=[dict(source_id='scene', quote=SPEECH,
                    kind='event', content=dict(speaker_surface='Eva', utterance='I believe the gate is clear.'))]))
        core = EvidenceCore()
        result = prepare_semantics(QUESTION, (AuthorizedText('scene', source),), core=core, backend=Stub())
        candidate = core.claims[result.candidate_ids[0]].content
        self.assertEqual(candidate['proposal']['assertion_scope'], 'CONDITIONAL_OR_EMBEDDED')
        self.assertEqual(candidate['validation']['semantic_support'], 'BOUNDED_LITERAL_FORM')

    def test_reader_keeps_full_source_and_raw_stub_answer_without_extraction(self):
        source = 'In a hypothetical scenario, ' + SPEECH
        workspace, _, _ = prepare(source)
        raw = json.dumps(dict(answer='The expression is inside a hypothetical scenario.',
            source_citations=[dict(source_id='scene', quote=source)],
            uncertainty='Actual speech or private belief is not established.', assumptions='Source-relative reading.'))
        calls = []
        result = workspace.answer_reader_entry(QUESTION, lambda m: calls.append(m) or raw,
            source_ids=('scene',))
        self.assertEqual(result['answer'], raw)
        self.assertEqual(result['answer_raw'], raw)
        self.assertEqual(result['preparation_provider_calls'], 0)
        self.assertEqual(len(calls), 1)
        self.assertEqual(json.loads(calls[0][-2]['content'])['sources'][0]['text'], source)
        self.assertFalse(result['source_citation_audit']['semantic_certification'])


if __name__ == '__main__':
    unittest.main()
