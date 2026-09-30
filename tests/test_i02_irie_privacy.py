import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.i02_irie_privacy_preflight import audit, SOURCE, OBLIGATIONS
from scripts.i02_source_qualification_v7 import require_irie_disjoint, require_qualified_confirmation_source_v7
from scripts.run_i02_irie_privacy_cpg_once import load_package, preflight, execute

class PrivacyDevelopmentTests(unittest.TestCase):
    def test_native_ordinary_source_and_treatment_absence(self):
        gate=audit()
        item=json.loads(SOURCE.read_text())
        payload=json.loads(gate['h_final_messages'][-1]['content'])
        self.assertEqual(payload['narrative'],item['source_text'])
        self.assertFalse(gate['h_hnew_calls_allowed'])
        self.assertEqual(gate['source_first_obligation_count'],3)
        self.assertFalse(gate['independent_confirmation_qualified'])

    def test_source_change_and_unsupported_obligation_fail(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'source.json'
            item=json.loads(SOURCE.read_text());item['source_text']+=' User feels shame.'
            p.write_text(json.dumps(item))
            with patch('scripts.i02_irie_privacy_preflight.SOURCE',p):
                with self.assertRaises(ValueError):audit()
            p=Path(d)/'rubric.json'
            row=json.loads(OBLIGATIONS.read_text());row['obligations'][0]['source_quotes']=['not in source']
            p.write_text(json.dumps(row))
            with patch('scripts.i02_irie_privacy_preflight.OBLIGATIONS',p):
                with self.assertRaises(ValueError):audit()

    def test_exposure_excluded_before_history_and_rights(self):
        for c in ({'writing_system_id':'irie-volume34-ai-ethics-case-studies'},
                  {'author_id':'norman-mooradian'}, {'author_id':'calvin-hillis'},
                  {'source_text':json.loads(SOURCE.read_text())['source_text']}):
            with self.assertRaises(ValueError):require_irie_disjoint(c)
            with patch('scripts.i02_source_qualification_v7.require_qualified_confirmation_source_v6') as old:
                with self.assertRaises(ValueError):
                    require_qualified_confirmation_source_v7({},c,{},'.','HEAD')
                old.assert_not_called()
        self.assertTrue(require_irie_disjoint({'author_id':'other','writing_system_id':'other'}))

    def test_frozen_reservation_and_drift(self):
        package=load_package();gate,_=preflight(package)
        self.assertLessEqual(gate['all_phase_peak_reservation_usd'],0.24)
        self.assertEqual(package['maximum_provider_calls'],4)
        package['budget_cap_usd']=1
        with self.assertRaises(ValueError):preflight(package)

    def test_composition_original_source_no_retry_close_and_no_second_output(self):
        package=load_package();item=json.loads(SOURCE.read_text());calls=[]
        def provider(request):
            calls.append(request)
            if len(calls)==3:
                content=json.dumps(dict(source_index=[dict(id='e1',source_id=item['source_id'],
                    quote='All personal data is completely secure and never shared outside of the device and its interface.')],
                    relations=[],answer_plan=[],open_questions=[]))
            else:
                content=json.dumps(dict(answer='Risks are conditional.',uncertainty='Actual reactions unknown.',
                    assumptions='No sharing.',source_citations=[]))
            return dict(model=package['model'],created=1790746100,
                usage=dict(prompt_tokens=100,completion_tokens=100,prompt_cache_hit_tokens=0,prompt_cache_miss_tokens=100),
                choices=[dict(finish_reason='stop',message=dict(content=content))])
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'receipt.json';receipt=execute(package,provider,out)
            self.assertEqual(len(calls),4)
            self.assertEqual(receipt['authorization_remaining_usd'],0)
            self.assertEqual(receipt['budget_state'],'CLOSED_NO_TRANSFER_NO_RERUN')
            self.assertEqual(json.loads(calls[-1]['messages'][-1]['content'])['sources'],
                [dict(source_id=item['source_id'],text=item['source_text'])])
            with self.assertRaises(ValueError):execute(package,provider,out)
            self.assertEqual(len(calls),4)
        def failure(request):
            calls.append(request);raise RuntimeError('simulated unavailable')
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'failed.json'
            with self.assertRaises(RuntimeError):execute(package,failure,out)
            receipt=json.loads(out.read_text())
            self.assertEqual(receipt['provider_calls'],1)
            self.assertEqual(receipt['status'],'FAILED_NO_RETRY')
            self.assertEqual(receipt['authorization_remaining_usd'],0)

if __name__=='__main__':unittest.main()
