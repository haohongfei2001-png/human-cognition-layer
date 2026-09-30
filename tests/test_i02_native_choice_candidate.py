import json
from pathlib import Path
import unittest
from unittest.mock import patch
from scripts.i02_native_choice_candidate import ordinary_choice,inspect_ordinary,protected_native_row
from scripts.i02_source_qualification_v8 import require_qualified_confirmation_source_v8
from scripts.i02_runtime_amendment_v6 import validate_current

class NativeChoiceTests(unittest.TestCase):
    def test_options_are_question_not_world_source(self):
        task=ordinary_choice('Mina left. No motive was reported.','What does Mina intend?',
            {'A':'Mina intends harm.','B':'Mina feels shame.','C':'Unknown.','D':'Mina admits guilt.'})
        receipt=inspect_ordinary(task,'fixture-only')
        self.assertTrue(receipt['h_source_complete']);self.assertTrue(receipt['h_question_complete'])
        self.assertTrue(receipt['options_in_question_only'])
        self.assertFalse(receipt['native_label_in_input'])
        self.assertNotIn('harm',task['source_text'])

    def test_partial_choice_source_drift_refused(self):
        with self.assertRaises(ValueError):ordinary_choice('Source.','Question?',{'A':'one'})
        with self.assertRaises(ValueError):protected_native_row(b'{"ANSWER":"A"}')

    def test_used_unviewed_entry_probe_never_becomes_confirmation(self):
        with patch('scripts.i02_source_qualification_v8.require_qualified_confirmation_source_v7') as prior:
            with self.assertRaises(ValueError):
                require_qualified_confirmation_source_v8({},
                    {'writing_system_id':'tombench-original-bilingual-social-scenarios'}, {},'.','HEAD')
            prior.assert_not_called()

    def test_actual_before_after_receipt_and_runtime_amendment(self):
        r=json.loads(Path('reports/HCL_I02_NATIVE_CHOICE_DEVELOPMENT_ENTRY.json').read_text())
        self.assertFalse(r['before_certified_v5']['h_source_complete'])
        self.assertTrue(r['entry']['h_source_complete'])
        self.assertEqual(r['before_certified_v5']['source_sha256'],r['entry']['source_sha256'])
        self.assertEqual(r['before_certified_v5']['question_with_options_sha256'],r['entry']['question_with_options_sha256'])
        self.assertEqual(r['before_certified_v5']['h_selected_capabilities'],r['entry']['h_selected_capabilities'])
        self.assertFalse(r['confirmation_qualified']);self.assertFalse(r['model_input_allowed'])
        self.assertFalse(r['source_text_displayed']);self.assertFalse(r['native_labels_displayed'])
        self.assertEqual(r['provider_calls'],0)
        self.assertTrue(validate_current())

if __name__=='__main__':unittest.main()
