"""Ordinary source-level disagreement without private or normative promotion."""
import json
import unittest

from hcl.v1 import HCLCognitionLayer, PerspectiveMode, prepare_person_context


SOURCE = ('Nora wrote "A public warning is enough evidence for caution."\n'
          'Pax replied "A warning alone does not establish the risk."\n'
          'Mira said "The schedule changed."')
QUERY = "Compare Nora and Pax's arguments about the warning."


class ReaderArgumentQuestionTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda _: '')

    def test_positive_public_argument_source_and_composition(self):
        prepared = prepare_person_context(self.layer, QUERY, SOURCE)
        payload = json.loads(prepared.messages[-1]['content'])
        self.assertEqual(prepared.preparation_receipt['method'],
                         'reader_source_argument_comparison_v1')
        self.assertEqual(payload['sources'][0]['text'], SOURCE)
        self.assertEqual(payload['query'], QUERY)
        self.assertTrue(any(row['kind'] == 'event' for row in payload['cognitive_candidates']))
        self.assertFalse(prepared.preparation_receipt['specialized_cognition_treatment'])
        self.assertIn('not proof', prepared.messages[0]['content'])
        self.assertEqual(prepared.preparation_receipt['extraction_provider_calls'], 0)

    def test_source_revision_recomputes_without_inventing_position(self):
        old = prepare_person_context(self.layer, QUERY, SOURCE)
        changed = SOURCE.replace('does not establish', 'establishes')
        new = prepare_person_context(self.layer, QUERY, changed)
        self.assertNotEqual(old.preparation_receipt['source_sha256'],
                            new.preparation_receipt['source_sha256'])
        self.assertEqual(json.loads(new.messages[-1]['content'])['sources'][0]['text'], changed)

    def test_explicit_statement_prefix_excludes_later_source(self):
        prepared = prepare_person_context(self.layer,
            'At statement 1, Compare Nora and Pax arguments about the warning.', SOURCE)
        payload = json.loads(prepared.messages[-1]['content'])
        self.assertEqual(payload['sources'][0]['text'], SOURCE.splitlines()[0])
        self.assertEqual(payload['source_order_scope']['through_statement'], 1)
        self.assertNotIn('Pax replied', payload['sources'][0]['text'])

    def test_reader_private_normative_queries_do_not_establish_private_or_moral_truth(self):
        for query in ("Compare Nora and Pax's private beliefs about the warning.",
                      "Compare Nora and Pax's arguments about who is morally guilty.",
                      'Is Nora guilty?'):
            prepared = prepare_person_context(self.layer, query, SOURCE)
            state = json.loads(prepared.messages[-1]['content'])
            self.assertEqual(state['sources'][0]['text'], SOURCE)
            self.assertFalse(prepared.preparation_receipt['specialized_cognition_treatment'])
            self.assertFalse(prepared.preparation_receipt['agency_treatment']['private_intention_established'])
            self.assertIn('responsibility', prepared.messages[0]['content'])
        private = prepare_person_context(self.layer, QUERY, SOURCE,
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE)
        self.assertEqual(private.preparation_receipt['failure'],
                         'reader_argument_requires_reader_view')
        self.assertNotIn(SOURCE, json.dumps(private.messages))

    def test_budget_and_historical_specific_question(self):
        with self.assertRaisesRegex(ValueError, 'final context budget'):
            prepare_person_context(self.layer, QUERY, SOURCE, max_context_chars=512)
        historical = prepare_person_context(self.layer, "What does Nora believe?", SOURCE)
        self.assertNotEqual(historical.preparation_receipt['method'],
                            'reader_source_argument_comparison_v1')


if __name__ == '__main__':
    unittest.main()
