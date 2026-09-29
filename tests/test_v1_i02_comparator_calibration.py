"""Provider-free rehearsal of the one-use calibration budget and source gate."""
import json
from pathlib import Path
import tempfile
import unittest

from scripts.i02_musr_calibration import FIRST_GROUP_SHA256
from scripts.run_i02_comparator_calibration_once import (Ledger, build_package,
    load_package, preflight)

SOURCE = Path('/tmp/hcl-i02-musr-object-placements.csv')


class ComparatorCalibrationTests(unittest.TestCase):
    @unittest.skipUnless(SOURCE.exists(), 'pinned calibration file only available locally')
    def test_pinned_source_equal_inputs_and_no_gold(self):
        package = load_package()
        gate, arms = preflight(package, SOURCE)
        self.assertEqual(gate['status'], 'PASS_PROVIDER_FREE_CPG_ONLY')
        self.assertLessEqual(gate['all_phase_peak_reservation_usd'], package['budget_cap_usd'])
        self.assertEqual(gate['h_native_treatment'], 'FAIL_ABSENT_NOT_EVALUATED')
        ordinary = arms['ordinary_payload']
        self.assertNotIn('answer_choice', json.dumps(ordinary))
        self.assertNotIn('answer_index', json.dumps(ordinary))
        for phase in ('C', 'P', 'G_map'):
            self.assertEqual(json.loads(arms[phase][-1]['content']), ordinary)

    def test_four_call_rehearsal_preserves_raw_and_refuses_rerun(self):
        calls = []

        def fake(request):
            calls.append(request)
            if len(calls) == 3:
                content = json.dumps(dict(source_index=[dict(
                    source_id=FIRST_GROUP_SHA256, quote='authored source')], open_questions=[]))
            else:
                content = json.dumps(dict(answer='uncertain source-reported location',
                    source_citations=[], uncertainty='private search not observed', assumptions=[]))
            return dict(model='deepseek-v4-pro', created=1780000000,
                choices=[dict(message=dict(content=content), finish_reason='stop')],
                usage=dict(prompt_tokens=100, completion_tokens=50,
                    prompt_cache_hit_tokens=0, prompt_cache_miss_tokens=100))

        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'receipt.json'
            ledger = Ledger(load_package(), output)
            for phase in ('C', 'P', 'G_map', 'G_final'):
                ledger.call(phase, [dict(role='user', content='authored source')], fake)
            receipt = ledger.receipt
            self.assertEqual(len(calls), 4)
            self.assertEqual(receipt['provider_calls'], 4)
            self.assertEqual(receipt['status'], 'STARTED')
            self.assertLessEqual(receipt['conservative_reserved_usd'], receipt['hard_cap_usd'])
            self.assertEqual(len(json.loads(output.read_text())['attempts']), 4)
            self.assertTrue(all(a['response_raw'] for a in receipt['attempts']))
            with self.assertRaisesRegex(ValueError, 'rerun'):
                Ledger(load_package(), output)
            self.assertEqual(len(calls), 4)

    def test_pre_call_hard_cap_blocks_transport(self):
        package = build_package()
        package['budget_cap_usd'] = 0
        with tempfile.TemporaryDirectory() as folder:
            ledger = Ledger(package, Path(folder) / 'receipt.json')
            with self.assertRaisesRegex(ValueError, 'hard cap'):
                ledger.call('C', [dict(role='user', content='short')],
                            lambda _: self.fail('provider must not be called'))
            self.assertEqual(ledger.receipt['provider_calls'], 0)


if __name__ == '__main__':
    unittest.main()
