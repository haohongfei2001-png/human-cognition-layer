"""One-use second-source calibration is source-pinned and no-retry."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import i02_moral_calibration as source
from scripts.run_i02_moral_cpg_calibration_once import (
    build_package, execute, load_package, preflight)


PACKAGE = json.loads(Path('reports/HCL_I02_MORAL_CPG_CALIBRATION_PACKAGE.json').read_text())


def authored_raw():
    row = dict(ID=source.FIRST_ID, norm='People should protect children.',
        situation='Kai is caring for a child.', intention='Kai wants a safe yard.',
        moral_action='Kai puts a guard by the gate.',
        moral_consequence='The child stays safe.',
        immoral_action='Kai leaves a wire by the gate.',
        immoral_consequence='The child touches the wire.')
    first = (json.dumps(row) + '\n').encode()
    # The remaining byte stream has the same row count but is intentionally
    # invalid JSON. The parser must never inspect it for this calibration.
    return first + b'\n' * 11998 + b'x', first


class MoralCPGCalibrationTests(unittest.TestCase):
    def test_frozen_package_and_provider_free_source_gate(self):
        self.assertEqual(PACKAGE, build_package())
        self.assertEqual(PACKAGE['maximum_provider_calls'], 4)
        self.assertEqual(PACKAGE['retries'], 0)
        self.assertEqual(PACKAGE['h_arm_calls'], 0)
        self.assertEqual(PACKAGE['budget_cap_usd'], 0.06)
        self.assertEqual(load_package(), PACKAGE)
        raw, first = authored_raw()
        with patch.object(source, 'SOURCE_SHA256', hashlib.sha256(raw).hexdigest()), \
                patch.object(source, 'FIRST_LINE_SHA256', hashlib.sha256(first).hexdigest()):
            candidate = source.calibration_candidate(raw)
        self.assertEqual(candidate['case_id'], source.FIRST_ID)
        self.assertNotIn('moral_action', candidate['source_text'])
        self.assertIn('Alternative B consequence:', candidate['source_text'])
        with self.assertRaisesRegex(ValueError, 'hash mismatch'):
            source.calibration_candidate(raw + b'!')

    def test_four_call_fake_rehearsal_and_closed_budget(self):
        raw, first = authored_raw()
        package = dict(PACKAGE, source_file_sha256=hashlib.sha256(raw).hexdigest())
        calls = []
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(source, 'SOURCE_SHA256', package['source_file_sha256']), \
                patch.object(source, 'FIRST_LINE_SHA256', hashlib.sha256(first).hexdigest()):
            path = Path(folder) / 'source.jsonl'
            path.write_bytes(raw)
            gate, arms = preflight(package, path)
            self.assertLess(gate['all_phase_peak_reservation_usd'], 0.06)
            quote = 'Source-reported social norm: People should protect children.'

            def fake(request):
                calls.append(request)
                if len(calls) == 3:
                    content = json.dumps(dict(source_index=[dict(
                        source_id=arms['ordinary_payload']['sources'][0]['source_id'],
                        quote=quote)], open_questions=['Was the risk known?']))
                else:
                    content = json.dumps(dict(answer='conditional source report',
                        source_citations=[], uncertainty='risk knowledge unknown',
                        assumptions=[]))
                return dict(model='deepseek-v4-pro', created=1790681274,
                    choices=[dict(message=dict(content=content), finish_reason='stop')],
                    usage=dict(prompt_tokens=100, completion_tokens=50,
                        prompt_cache_hit_tokens=0, prompt_cache_miss_tokens=100))

            output = Path(folder) / 'receipt.json'
            receipt = execute(package, path, fake, output)
            self.assertEqual([a['phase'] for a in receipt['attempts']],
                             ['C', 'P', 'G_map', 'G_final'])
            self.assertEqual(len(calls), 4)
            self.assertEqual(receipt['provider_calls'], 4)
            self.assertEqual(receipt['authorization_remaining_usd'], 0)
            self.assertEqual(receipt['budget_state'], 'CLOSED_NO_TRANSFER_NO_RERUN')
            self.assertLess(receipt['conservative_reserved_usd'], 0.06)
            with self.assertRaisesRegex(ValueError, 'rerun'):
                execute(package, path, fake, output)
            self.assertEqual(len(calls), 4)


if __name__ == '__main__':
    unittest.main()
