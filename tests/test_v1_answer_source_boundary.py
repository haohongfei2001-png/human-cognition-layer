"""The contract reaches the real answer call; stubs do not prove model compliance."""
import json
import unittest
from hcl.cognition import CognitionWorkspace
from hcl.cognition.reader_entry import _FINAL_ANSWER_POLICY

class AnswerSourceBoundaryTests(unittest.TestCase):
    def test_all_ordinary_routes_receive_inference_boundary_without_source_rewrite(self):
        sources = [
            'Mira closed the workshop door. Theo waited outside.',
            'Omar moved the bench because the passage was blocked.',
            'Nia said, “I intend to repair the fence.”',
            'Sol said, “The workshop is closed.” Ren heard Sol\'s last statement.',
            'Sol said, “The workshop is closed.” Sol\'s last statement was publicly available.',
        ]
        for source in sources:
            with self.subTest(source=source):
                workspace=CognitionWorkspace();workspace.put_source('source',source)
                requests=[]
                raw=json.dumps(dict(answer='A stub interpretation.',source_citations=[source],uncertainty='',assumptions=''))
                result=workspace.answer_reader_entry('What does the source support?',lambda m:requests.append(m) or raw,
                    source_ids=('source',),allow_translation=False)
                self.assertEqual(len(requests),1)
                self.assertEqual(requests[0][-1]['content'],_FINAL_ANSWER_POLICY)
                self.assertIn('Useful ordinary inferences are allowed',_FINAL_ANSWER_POLICY)
                self.assertIn('Preserve an explicitly reported reason',_FINAL_ANSWER_POLICY)
                self.assertIn('material unstated premises in assumptions',_FINAL_ANSWER_POLICY)
                payload=json.loads(requests[0][-2]['content'])
                self.assertEqual(payload['sources'][0]['text'],source)
                self.assertEqual(result['answer_raw'],raw)
                self.assertEqual(result['answer'],raw)
                self.assertFalse(result['source_citation_audit']['semantic_certification'])
                self.assertEqual(result['preparation_provider_calls'],0)
