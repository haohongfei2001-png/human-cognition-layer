"""B01: genuine nested joins and polarity scope, not renamed access fields."""
import json
import unittest

from hcl.cognition import CognitionWorkspace, Attitude, MentalProposition, prepare_epistemic
from hcl.cognition.epistemic import parse_mental_proposition


class EpistemicObjectTests(unittest.TestCase):
    def prepare(self, text, query="What does Mira think Noor believes?", **kwargs):
        w = CognitionWorkspace()
        w.put_source('scene', text)
        return w, prepare_epistemic(w, query, source_ids=('scene',), **kwargs)

    def test_positive_nested_attribution_joins_subject_report_without_detachment(self):
        w, b = self.prepare('Mira said, "I believe Noor believes the gate is open." '
                            'Noor replied, "I do not believe the gate is open."')
        attributed = b.project(w.core, ('Mira', 'Noor'), attitude=Attitude.BELIEF)
        actual_report = b.project(w.core, ('Noor',), attitude=Attitude.BELIEF)
        self.assertEqual(attributed[0]['result'], 'SOURCE_REPORTED_AFFIRM')
        self.assertEqual(actual_report[0]['result'], 'SOURCE_REPORTED_DENY')
        comparison = b.compare_attribution(w.core, 'Mira', 'Noor')
        self.assertEqual(comparison[0]['relation'], 'DIFFERS_FROM_SUBJECT_REPORT')
        self.assertTrue(all(r['private_state'] == 'NOT_ESTABLISHED' for r in attributed + actual_report))
        wire = json.loads(b.messages(w.core, 'Explain this disagreement.', comparisons=comparison)[-1]['content'])
        self.assertEqual(wire['comparisons'], comparison)
        self.assertEqual(len(wire['epistemic_objects']), 2)
        self.assertTrue(wire['epistemic_objects'][0]['private_interpretation']['assumptions'])

    def test_ordinary_question_selects_nested_path_and_real_comparison(self):
        w, b = self.prepare('Mira said, "I believe Noor believes the gate is open." '
                            'Noor said, "I do not believe the gate is open." '
                            'Kai said, "I believe the road is closed."')
        wire = json.loads(b.messages(w.core, 'What does Mira think Noor believes?')[-1]['content'])
        self.assertEqual(wire['selected_holder_path'], ['Mira', 'Noor'])
        self.assertEqual(wire['query_projection'][0]['result'], 'SOURCE_REPORTED_AFFIRM')
        self.assertEqual(wire['comparisons'][0]['relation'], 'DIFFERS_FROM_SUBJECT_REPORT')
        self.assertEqual([r.speaker for r in b.records], ['Mira', 'Noor'])

    def test_outer_denial_differs_from_inner_denial_and_not_other_person(self):
        outer_w, outer = self.prepare('Mira said, "I do not believe Noor believes the gate is open."')
        inner_w, inner = self.prepare('Mira said, "I believe Noor does not believe the gate is open."')
        self.assertEqual(outer.project(outer_w.core, ('Mira', 'Noor'))[0]['result'], 'OUTER_ATTRIBUTION_DENIED')
        self.assertEqual(inner.project(inner_w.core, ('Mira', 'Noor'))[0]['result'], 'SOURCE_REPORTED_DENY')
        self.assertFalse(outer.project(outer_w.core, ('Mira', 'Kai')))
        self.assertFalse(inner.project(inner_w.core, ('Noor',)))

    def test_outer_uncertainty_is_not_inner_uncertainty(self):
        w, b = self.prepare('Mira said, "I am unsure whether Noor believes the gate is open."')
        row = b.project(w.core, ('Mira', 'Noor'))[0]
        self.assertEqual(row['result'], 'OUTER_ATTRIBUTION_UNCERTAIN')
        self.assertEqual(row['unprojected_inner_state'], 'NO_INNER_POLARITY_INFERENCE')
        self.assertEqual(row['chain'][-1]['polarity'], 'AFFIRM')

    def test_knowledge_understanding_exposure_and_belief_claims_remain_distinct(self):
        for verb, attitude in [('know', Attitude.KNOWLEDGE), ('understand', Attitude.UNDERSTANDING),
                               ('heard', Attitude.EXPOSURE), ('believe', Attitude.BELIEF)]:
            w, b = self.prepare(f'Mira said, "I {verb} the gate is open."')
            self.assertEqual(b.project(w.core, ('Mira',), attitude=attitude)[0]['attitude'], attitude.value)
            if attitude != Attitude.BELIEF:
                self.assertFalse(b.project(w.core, ('Mira',), attitude=Attitude.BELIEF))
                self.assertIsNone(b.records[0].private_interpretation_id)
            self.assertEqual(b.project(w.core, ('Mira',))[0]['world_truth'], 'NOT_ESTABLISHED')

    def test_exposure_to_nested_proposition_does_not_become_belief_attribution(self):
        w, b = self.prepare('Mira said, "I heard Noor believes the gate is open." '
                            'Noor said, "I do not believe the gate is open."')
        self.assertEqual(b.project(w.core, ('Mira', 'Noor'))[0]['result'], 'NESTED_CONTENT_NOT_BELIEF_ATTRIBUTION')
        self.assertFalse(b.compare_attribution(w.core, 'Mira', 'Noor'))

    def test_bare_speech_never_automatically_creates_private_belief(self):
        w, b = self.prepare('Mira said, "The gate is open."')
        self.assertEqual(len(b.records), 1)
        self.assertIsNone(b.records[0].private_interpretation_id)
        self.assertFalse(b.project(w.core, ('Mira',), attitude=Attitude.BELIEF))
        self.assertEqual(w.core.claims[b.records[0].expression_id].content['channel'], 'PUBLIC_EXPRESSION')

    def test_third_party_attribution_keeps_reporter_scope(self):
        w, b = self.prepare('Mira said, "Noor believes the gate is open."')
        self.assertEqual(b.records[0].tree.attitude, Attitude.REPORT)
        self.assertFalse(b.project(w.core, ('Noor',)))
        self.assertEqual(b.project(w.core, ('Mira', 'Noor'))[0]['chain'][0]['attitude'], 'REPORTED_ATTRIBUTION')
        self.assertIsNone(b.records[0].private_interpretation_id)

    def test_nested_first_person_deixis_remains_the_actual_quoted_speaker(self):
        tree = parse_mental_proposition('I believe Noor believes I know the gate is open.', 'Mira')
        self.assertEqual(tree.holder, 'Mira')
        self.assertEqual(tree.content.holder, 'Noor')
        self.assertEqual(tree.content.content.holder, 'Mira')
        self.assertEqual(tree.content.content.attitude, Attitude.KNOWLEDGE)
        self.assertEqual(tree.depth, 3)

    def test_depth_limit_does_not_silently_truncate_deep_state_into_fact(self):
        text = 'Mira said, "I believe Noor believes Kai believes Lee believes the gate is open."'
        w, b = self.prepare(text)
        self.assertFalse(b.records)
        self.assertEqual(b.diagnostics[0]['reason'], 'modal_depth_exceeded')
        w, deeper = self.prepare(text, max_depth=4)
        self.assertEqual(deeper.records[0].tree.depth, 4)
        self.assertTrue(deeper.project(w.core, ('Mira', 'Noor', 'Kai', 'Lee')))

    def test_withdrawal_of_subject_support_invalidates_join_not_reporter(self):
        w, b = self.prepare('Mira said, "I believe Noor believes the gate is open." '
                            'Noor said, "I do not believe the gate is open."')
        comparison = b.compare_attribution(w.core, 'Mira', 'Noor')[0]
        target = b.records[1]
        span = w.core.claims[target.expression_id].content['source_span_id']
        invalidated = w.core.withdraw(span)
        self.assertIn(comparison['claim_id'], invalidated)
        self.assertNotIn(b.records[0].expression_id, invalidated)
        self.assertFalse(b.compare_attribution(w.core, 'Mira', 'Noor'))
        self.assertTrue(b.project(w.core, ('Mira', 'Noor')))

    def test_actor_rename_preserves_same_nested_operation(self):
        w, b = self.prepare('Elena wrote, "I think Sam thinks the door is shut." '
                            'Sam stated, "I believe the door is shut."', query='What does Elena think Sam believes?')
        self.assertEqual(b.compare_attribution(w.core, 'Elena', 'Sam')[0]['relation'], 'CONSISTENT_WITH_SUBJECT_REPORT')

    def test_ambiguous_and_indefinite_speakers_do_not_become_people(self):
        for speaker in ('She', 'Nobody', 'Everyone'):
            w, b = self.prepare(f'{speaker} said, "I believe the gate is open."')
            self.assertFalse(b.records)
            self.assertTrue(b.diagnostics)

    def test_same_name_in_different_source_is_not_implicitly_joined(self):
        w = CognitionWorkspace()
        w.put_source('one', 'Mira said, "I believe Noor believes the gate is open."')
        w.put_source('two', 'Noor said, "I do not believe the gate is open."')
        b = prepare_epistemic(w, 'Compare the reports.', source_ids=('one', 'two'))
        self.assertFalse(b.compare_attribution(w.core, 'Mira', 'Noor'))

    def test_hidden_source_and_changed_hidden_content_never_enter_view(self):
        w = CognitionWorkspace()
        w.put_source('public', 'Mira said, "I believe the gate is open."', permitted_observers=('Noor',))
        w.put_source('secret', 'Kai said, "I know the gate is closed."')
        b = prepare_epistemic(w, 'What is available?', source_ids=('public', 'secret'), observer='Noor')
        before = b.messages(w.core, 'What is available?')
        self.assertNotIn('Kai', str(before))
        w.put_source('secret', 'Kai said, "I know the gate is broken."')
        after = prepare_epistemic(w, 'What is available?', source_ids=('public', 'secret'), observer='Noor')
        self.assertEqual(before, after.messages(w.core, 'What is available?'))
