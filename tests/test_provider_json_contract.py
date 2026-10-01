import json,unittest
from pathlib import Path
from types import SimpleNamespace
from scripts.provider_json_contract import validate_json_mode_request,provider_error_receipt
class JSONContractTests(unittest.TestCase):
 def test_explicit_json_required_before_transport_for_all_phases(self):
  for text in ('Return JSON.', 'return json', 'Output a Json object.'):
   self.assertTrue(validate_json_mode_request(dict(response_format=dict(type='json_object'),messages=[dict(role='system',content=text)])))
  with self.assertRaises(ValueError):validate_json_mode_request(dict(response_format=dict(type='json_object'),messages=[dict(role='system',content='Return passes and reasons.')]))
 def test_source_data_keyword_is_not_an_output_instruction(self):
  with self.assertRaises(ValueError):validate_json_mode_request(dict(response_format=dict(type='json_object'),messages=[dict(role='user',content='The source discusses JSON.')]))
 def test_actual_consumed_error_request_refused_offline_no_rerun_or_score_change(self):
  r=json.loads(Path('reports/HCL_DRC003_RAW_RECEIPT.json').read_text());request=r['attempts'][-1]['request_raw']
  with self.assertRaises(ValueError):validate_json_mode_request(request)
  self.assertEqual(r['provider_calls'],14);self.assertEqual(r['status'],'FAILED_NO_RETRY');self.assertIsNone(r['estimated_actual_cost_usd'])
 def test_error_receipt_keeps_available_body_request_id_not_auth_headers(self):
  e=SimpleNamespace(body=dict(error=dict(message='json required')),status_code=400,request_id='request-public',response=SimpleNamespace(headers={'content-type':'application/json','authorization':'do not publish','x-request-id':'request-public'}))
  r=provider_error_receipt(e);self.assertEqual(r['http_status'],400);self.assertEqual(r['error_body'],e.body);self.assertNotIn('authorization',r['response_headers']);self.assertIsNone(r['usage']);self.assertIsNone(r['actual_cost_usd']);self.assertFalse(r['retry_performed'])
 def test_missing_response_not_fabricated_or_credential_echo_published(self):
  r=provider_error_receipt(RuntimeError('failure'));self.assertIsNone(r['http_status']);self.assertIsNone(r['error_body'])
  r=provider_error_receipt(SimpleNamespace(body=dict(error='bad test-secret-key')),redactions=('test-secret-key',));self.assertNotIn('test-secret-key',json.dumps(r));self.assertTrue(r['credential_redaction_requested'])
if __name__=='__main__':unittest.main()
