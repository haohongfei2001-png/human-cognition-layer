"""A02 structural containment is source-relative ambiguity, never world negation."""
import json
from pathlib import Path
import unittest

from hcl.cognition import EvidenceCore
from hcl.cognition.epistemic import check_epistemic_candidates
from hcl.cognition.semantic import AuthorizedText, _local_candidates, prepare_semantics


SPEECH = 'Noor said, "I believe the gate is open."'
REPORT = 'Noor believes the gate is open.'
HYPOTHETICAL = 'The following scene is hypothetical.\n'
EMBEDDED = 'CONDITIONAL_OR_EMBEDDED'
REPORTED = 'SOURCE_REPORT'


class SemanticScopeIsolationTests(unittest.TestCase):
    def assert_speech_scope(self, source, expected, quote=SPEECH, **options):
        rows = _local_candidates(AuthorizedText('scene', source), **options)
        events = [r for r in rows if r['kind'] == 'event' and r['quote'] == quote]
        self.assertEqual(len(events), 1)
        event = events[0]
        self.assertEqual(event['content']['assertion_scope'], expected)
        self.assertEqual(source[event['start']:event['start'] + len(event['quote'])], quote)
        self.assertEqual(event['start'], source.index(quote))
        self.assertIsNone(event['content']['event_time'])
        self.assertIsNone(event['content']['access_time'])
        return rows

    def test_plain_and_inline_condition_controls(self):
        self.assert_speech_scope(SPEECH, REPORTED)
        self.assert_speech_scope('If ' + SPEECH, EMBEDDED)

    def test_all_frozen_proposal_and_boundary_cases(self):
        for name in ('a02_scope_proposal_v1.json', 'a02_scope_boundary_review_v1.json'):
            for case in json.loads(Path('eval', name).read_text())['cases']:
                with self.subTest(case=case['case_id']):
                    expected = case.get('expected_assertion_scope',
                                        case.get('expected_under_proposed_structural_contract'))
                    self.assert_speech_scope(case['source'], expected, quote=case['probe_quote'])

    def test_fenced_and_bracketed_reports_are_retained_as_embedded(self):
        for source in ('```example\n' + SPEECH + '\n```', '[' + SPEECH + ']',
                       '```example\n' + SPEECH, '[' + SPEECH,
                       '[Outer.\n[Inner.]\n' + SPEECH + '\n]'):
            with self.subTest(source=source):
                rows = self.assert_speech_scope(source, EMBEDDED)
                proposition = next(r['content'] for r in rows if r['kind'] == 'proposition')
                self.assertEqual(proposition['reference_binding'], 'UNRESOLVED')
                self.assertEqual(proposition['modality'], 'EXPRESSED_BELIEF_NOT_PRIVATE_TRUTH')

    def test_narrator_declaration_and_resumption_use_outer_channel(self):
        self.assert_speech_scope('Narrator: ' + HYPOTHETICAL + SPEECH, EMBEDDED)
        self.assert_speech_scope(HYPOTHETICAL + 'Narrator: In reality.\n' + SPEECH, REPORTED)
        self.assert_speech_scope(HYPOTHETICAL + SPEECH, EMBEDDED)

    def test_original_narrator_scene_prefix_carries_to_following_copy_cue(self):
        case = json.loads(Path('reports/HCL_RETAINED_ENTRY_SCOPE_BLOCKERS.json').read_text())['cases'][1]
        cue = case['source'].splitlines()[-1]
        self.assert_speech_scope(case['source'], EMBEDDED, quote=cue)
        for prefix in ('In a hypothetical scene:', 'Within the imagined dialogue:',
                       'Hypothetically:', 'Counterfactually:'):
            labels = ('', 'Narrator: ') if ' ' in prefix else ('Narrator: ',)
            for label in labels:
                self.assert_speech_scope(label + prefix + '\n' + SPEECH, EMBEDDED)

    def test_bare_one_word_colon_prefix_is_unresolved_actor_label_grammar(self):
        for heading in ('Hypothetically:', 'Counterfactually:'):
            source = heading + '\n' + SPEECH
            rows = _local_candidates(AuthorizedText('scene', source))
            self.assertFalse(any(r['kind'] == 'event' and r['quote'] == SPEECH for r in rows))
            core = EvidenceCore()
            result = prepare_semantics('What was reported?', (AuthorizedText('scene', source),), core=core)
            records = check_epistemic_candidates(core, 'What was reported?', result).records
            self.assertTrue(all(r.speaker != 'Noor' and isinstance(r.tree, str) for r in records))

    def test_contained_scene_prefix_cannot_suspend_outer_narration(self):
        prefix = 'In a hypothetical scene:'
        for text in ('Mira: ' + prefix, 'Mira said, "' + prefix + '"',
                     '"Narrator: ' + prefix + '"', '[Narrator: ' + prefix + ']',
                     '```example\nNarrator: ' + prefix + '\n```'):
            self.assert_speech_scope(text + '\n' + SPEECH, REPORTED)

    def test_recognized_actor_names_cannot_issue_narration_cues(self):
        for actor in ('Hypothetically', 'Counterfactually'):
            for turn in (actor + ': I believe the gate is open.',
                         actor + ' said, "I believe the gate is open."',
                         '_' + actor + '._ I believe the gate is open.'):
                self.assert_speech_scope(turn + '\n\n' + SPEECH, REPORTED, dialogue_blocks=True)
                self.assert_speech_scope(turn, REPORTED, quote=turn, dialogue_blocks=True)
        turn = 'In Reality: I believe the gate is open.'
        self.assert_speech_scope(HYPOTHETICAL + turn + '\n' + SPEECH, EMBEDDED)

    def test_scene_prefix_resumption_and_later_qualification_keep_order(self):
        prefix = 'Narrator: In a hypothetical scene:\n'
        resumed = prefix + SPEECH + '\nNarrator: In reality.\n'
        later = 'Mira said, "I believe the gate is open."'
        self.assert_speech_scope(resumed + later, EMBEDDED)
        self.assert_speech_scope(resumed + later, REPORTED, quote=later)
        self.assert_speech_scope(resumed + prefix + later, EMBEDDED, quote=later)
        for fake in ('Mira: In reality.', '"Narrator: In reality."',
                     '```example\nNarrator: In reality.\n```'):
            self.assert_speech_scope(prefix + fake + '\n' + SPEECH, EMBEDDED)

    def test_character_discussion_cannot_change_outer_scene(self):
        for turn in ('Mira said, "In reality."', 'Mira: In reality.', '_Mira._ In reality.'):
            self.assert_speech_scope(HYPOTHETICAL + turn + '\n\n' + SPEECH,
                                     EMBEDDED, dialogue_blocks=True)
        self.assert_speech_scope('Mira said, "The following scene is hypothetical."\n' + SPEECH, REPORTED)
        self.assert_speech_scope(HYPOTHETICAL + 'Narrator: The sign said "In reality."\n' + SPEECH, EMBEDDED)

    def test_quoted_scene_vocabulary_cannot_suspend_later_script_turn(self):
        turn = '_Noor._ I believe the gate is open.'
        for prefix in ('Mira said, "This is hypothetical."\n\n',
                       '```example\nHypothetical scene.\n```\n\n'):
            self.assert_speech_scope(prefix + turn, REPORTED, quote=turn, dialogue_blocks=True)

    def test_script_resumption_applies_only_to_subsequent_turns(self):
        earlier = '_Mira._ I believe the gate is open.'
        later = '_Noor._ I believe the gate is open.'
        source = HYPOTHETICAL + '\n' + earlier + '\n\nNarrator: In reality.\n\n' + later
        self.assert_speech_scope(source, EMBEDDED, quote=earlier, dialogue_blocks=True)
        self.assert_speech_scope(source, REPORTED, quote=later, dialogue_blocks=True)
        for qualification in ('In a hypothetical scene,\n', 'A hypothetical scene follows.\n\n'):
            self.assert_speech_scope('In reality.\n\n' + qualification + later,
                                     EMBEDDED, quote=later, dialogue_blocks=True)
            resumed = HYPOTHETICAL + '\n' + earlier + '\n\nNarrator: In reality.\n\n'
            self.assert_speech_scope(resumed + qualification + later,
                                     EMBEDDED, quote=later, dialogue_blocks=True)

    def test_contained_narrator_cannot_resume_outer_scene(self):
        for wrapped in ('[Narrator: In reality.]', '```example\nNarrator: In reality.\n```',
                        '“Narrator: In reality.”'):
            self.assert_speech_scope(HYPOTHETICAL + wrapped + '\n' + SPEECH, EMBEDDED)
        self.assert_speech_scope('“Quoted passage without a closing mark.\nNarrator: In reality.\n' + SPEECH, EMBEDDED)
        for spoken in ('Narrator: "In reality."', 'Narrator said, "In reality."'):
            self.assert_speech_scope(HYPOTHETICAL + spoken + '\n' + SPEECH, EMBEDDED)

    def test_fence_body_delimiters_do_not_leak_after_close(self):
        for body in ('[ literal text', '"unclosed quote', '“unclosed quote', '] literal text'):
            self.assert_speech_scope(HYPOTHETICAL + '```example\n' + body + '\n```\nIn reality.\n' + SPEECH, REPORTED)
            self.assert_speech_scope('```example\n' + body + '\n```\n' + SPEECH, REPORTED)

    def test_inline_ticks_and_shorter_fence_cannot_close_container(self):
        self.assert_speech_scope('```example\nMira said, "Literal ``` closes nothing."\n' + SPEECH, EMBEDDED)
        self.assert_speech_scope('````example\n```\n' + SPEECH + '\n````', EMBEDDED)
        self.assert_speech_scope('````example\n```\n`````\n' + SPEECH, REPORTED)

    def test_stray_closer_cannot_cancel_a_later_opener(self):
        self.assert_speech_scope(HYPOTHETICAL + ']\n[Stage direction.\nIn reality.\n' + SPEECH, EMBEDDED)
        self.assert_speech_scope(']\n' + SPEECH, REPORTED)

    def test_actual_speech_can_discuss_literal_delimiters(self):
        for turn in ('Mira said, "I wrote an opening bracket: [."',
                     'Mira said, "I wrote three backticks: ```."',
                     'Mira: I wrote an opening bracket: [.',
                     'Mira: I wrote an unmatched quote: ".'):
            self.assert_speech_scope(turn + '\n' + SPEECH, REPORTED)
            self.assert_speech_scope(HYPOTHETICAL + turn + '\nNarrator: In reality.\n' + SPEECH, REPORTED)

    def test_actual_transcript_fence_stays_ambiguous_without_frame_admission(self):
        source = 'This is an actual transcript.\n```transcript\n' + SPEECH + '\n```'
        self.assert_speech_scope(source, EMBEDDED)
        core = EvidenceCore()
        result = prepare_semantics('What was reported?', (AuthorizedText('scene', source),), core=core)
        self.assertEqual(result.backend_calls, 0)
        self.assertEqual(result.raw_response, '')
        for key in result.candidate_ids:
            span = core.spans[core.claims[key].content['source_span_id']]
            self.assertEqual(span.quote, source[span.start:span.end])
        request = json.loads(json.loads(result.extraction_messages_json)[-1]['content'])
        self.assertEqual(request['sources'][0]['text'], source)

    def test_closing_container_does_not_clear_hypothetical_scope(self):
        for container in ('[Stage direction.]', '```example\nText.\n```'):
            self.assert_speech_scope(HYPOTHETICAL + container + '\n' + SPEECH, EMBEDDED)

    def test_masking_cannot_join_a_cue_across_removed_qualification(self):
        for label in ('', 'Narrator: '):
            for qualification in ('[unless this is only an example]', '"unless this is an example"'):
                self.assert_speech_scope(HYPOTHETICAL + label + 'In reality' + qualification + '.\n' + SPEECH, EMBEDDED)
                self.assert_speech_scope(HYPOTHETICAL + label + 'In reality' + qualification + '. In reality.\n' + SPEECH, REPORTED)
            self.assert_speech_scope(HYPOTHETICAL + label + 'In reality.\n' + SPEECH, REPORTED)

    def test_backend_minimal_event_gets_local_scope_without_source_rewriting(self):
        source = '```example\n' + SPEECH + '\n```'
        raw = json.dumps({'candidates': [{'source_id': 'scene', 'quote': SPEECH,
            'start': source.index(SPEECH), 'kind': 'event', 'content': {
                'speaker_surface': 'Noor', 'utterance': 'I believe the gate is open.'}}]})
        class Replay:
            def complete_json(self, *args, **kwargs):
                return raw
        core = EvidenceCore()
        result = prepare_semantics('What was reported?', (AuthorizedText('scene', source),),
                                   core=core, backend=Replay())
        self.assertEqual(result.raw_response, raw)
        event = core.claims[result.candidate_ids[0]].content['proposal']
        self.assertEqual(event['assertion_scope'], EMBEDDED)
        self.assertEqual(result.diagnostics[0]['semantic_support'], 'BOUNDED_LITERAL_FORM')

    def test_backend_claimed_source_report_cannot_override_containment(self):
        source = '```example\n' + SPEECH + '\n```'
        candidate = next(r for r in _local_candidates(AuthorizedText('scene', SPEECH))
                         if r['kind'] == 'event')
        candidate['start'] = source.index(SPEECH)
        raw = json.dumps({'candidates': [candidate]})
        class Replay:
            def complete_json(self, *args, **kwargs):
                return raw
        core = EvidenceCore()
        result = prepare_semantics('What was reported?', (AuthorizedText('scene', source),),
                                   core=core, backend=Replay())
        self.assertEqual(result.raw_response, raw)
        self.assertEqual(result.diagnostics[0]['semantic_support'], 'UNVERIFIED_CANDIDATE')
        self.assertFalse(check_epistemic_candidates(core, 'What was reported?', result).records)

    def test_unicode_and_crlf_offsets_are_original_character_offsets(self):
        source = '档案🙂\r\n```example\r\n' + SPEECH + '\r\n```'
        self.assert_speech_scope(source, EMBEDDED)

    def test_narrator_report_uses_same_containment_and_transition_context(self):
        for body in ('[ literal', '"unclosed quote'):
            source = HYPOTHETICAL + '\n```example\n' + body + '\n```\n\nNarrator: In reality.\n\n' + REPORT
            rows = _local_candidates(AuthorizedText('scene', source), narrator_reports=True)
            reports = [r for r in rows if r['content'].get('event_kind') == 'NARRATOR_MENTAL_REPORT']
            self.assertEqual([r['quote'] for r in reports], [REPORT])
        for source in ('```example\n\n' + REPORT + '\n\n```', '[Stage.\n\n' + REPORT + '\n\n]'):
            rows = _local_candidates(AuthorizedText('scene', source), narrator_reports=True)
            self.assertFalse(any(r['content'].get('event_kind') == 'NARRATOR_MENTAL_REPORT' for r in rows))

    def test_narrator_report_consumes_positive_shared_prefix_cues(self):
        def reports(source):
            return [r['quote'] for r in _local_candidates(AuthorizedText('scene', source),
                narrator_reports=True) if r['content'].get('event_kind') == 'NARRATOR_MENTAL_REPORT']
        for prefix in ('In a hypothetical scene:', 'Hypothetically:', 'Counterfactually:'):
            header = 'Narrator: ' + prefix + '\n\n'
            self.assertEqual(reports(header + REPORT), [])
            self.assertEqual(reports(header + 'Narrator: In reality.\n\n' + REPORT), [REPORT])
            self.assertEqual(reports('Narrator: In reality.\n\n' + header + REPORT), [])
            for contained in ('Mira: ' + prefix, '"Narrator: ' + prefix + '"',
                              '```example\nNarrator: ' + prefix + '\n```'):
                self.assertEqual(reports(contained + '\n\n' + REPORT), [REPORT])


if __name__ == '__main__':
    unittest.main()
