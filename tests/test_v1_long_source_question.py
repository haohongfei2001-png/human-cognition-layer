"""Complete ordinary long-source entry: source, access, inference and history."""
import json
import unittest
from pathlib import Path

from hcl.v1 import HCLCognitionLayer, PerspectiveMode, prepare_person_context
from hcl.v1.long_source_question import prepare_long_source_context
from scripts.serious_eval_contract import runtime_digest


def story(speech='Mara said "I believe the bridge is closed."'):
    return ('The archive contains background details. ' * 650) + speech


class LongSourceQuestionTests(unittest.TestCase):
    def setUp(self):
        self.layer = HCLCognitionLayer(lambda _: '')
        self.question = 'What does Mara report believing, and what is still unknown?'

    def test_positive_complete_source_and_literal_anchored_belief(self):
        source = story()
        prepared = prepare_person_context(self.layer, self.question, source)
        payload = json.loads(prepared.messages[-1]['content'])
        self.assertEqual(payload['query'], self.question)
        self.assertEqual(payload['sources'][0]['text'], source)
        self.assertEqual(prepared.preparation_receipt['method'],
                         'complete_long_source_local_evidence_v1')
        self.assertFalse(prepared.preparation_receipt['specialized_cognition_treatment'])
        self.assertEqual(prepared.preparation_receipt['extraction_provider_calls'], 0)
        candidates = payload['cognitive_candidates']
        self.assertTrue(any(c['kind'] == 'proposition' and
                            c['validation']['semantic_support'] == 'BOUNDED_LITERAL_FORM'
                            for c in candidates))
        self.assertNotIn('private_belief_established', json.dumps(payload))

    def test_negative_private_view_never_receives_long_source(self):
        source = story()
        prepared = prepare_person_context(self.layer, self.question, source,
            perspective_mode=PerspectiveMode.CHARACTER_PERSPECTIVE,
            max_context_chars=64000)
        self.assertEqual(prepared.preparation_receipt['failure'],
                         'long_source_private_view_requires_explicit_access_preparation')
        self.assertNotIn(source, json.dumps(prepared.messages))

    def test_composition_question_does_not_invent_specialized_treatment(self):
        prepared = prepare_person_context(self.layer,
            "Explain Mara's belief and conditional responsibility.", story(),
            max_context_chars=64000)
        self.assertFalse(prepared.preparation_receipt['specialized_cognition_treatment'])
        self.assertIn('cognitive_candidates', prepared.messages[-1]['content'])

    def test_local_revision_recomputes_exact_source(self):
        old = prepare_long_source_context(self.question, story(), max_context_chars=64000)
        new_source = story('Mara said "I do not believe the bridge is closed."')
        new = prepare_long_source_context(self.question, new_source, max_context_chars=64000)
        self.assertNotEqual(old.preparation_receipt['source_sha256'],
                            new.preparation_receipt['source_sha256'])
        self.assertEqual(json.loads(new.messages[-1]['content'])['sources'][0]['text'], new_source)

    def test_bounds_and_short_historical_path(self):
        with self.assertRaisesRegex(ValueError, 'bounded complete long source'):
            prepare_long_source_context(self.question, story() * 20)
        short = prepare_person_context(self.layer, self.question, 'Mara said "I believe it."')
        self.assertNotEqual(short.preparation_receipt['method'],
                            'complete_long_source_local_evidence_v1')
        with self.assertRaisesRegex(ValueError, 'final context budget'):
            prepare_person_context(self.layer, self.question, story(),
                                   max_context_chars=20000)

    def test_real_development_smoke_receipt_has_no_efficacy_promotion(self):
        receipt = json.loads(Path('reports/HCL_I02_LONG_SOURCE_ENTRY_DEVELOPMENT_SMOKE.json').read_text())
        self.assertEqual(receipt['runtime_sha256'],
            json.loads(Path('reports/HCL_I02_RUNTIME_AMENDMENT_V3.json').read_text())[
                'amended_hcl_runtime_sha256'])
        self.assertNotEqual(receipt['runtime_sha256'], runtime_digest())
        self.assertTrue(receipt['source_complete_in_final_input'])
        self.assertGreater(receipt['source_chars'], 16000)
        self.assertFalse(receipt['specialized_cognition_treatment'])
        self.assertFalse(receipt['independent_confirmation_qualified'])
        self.assertEqual(receipt['provider_calls'], 0)


if __name__ == '__main__':
    unittest.main()
