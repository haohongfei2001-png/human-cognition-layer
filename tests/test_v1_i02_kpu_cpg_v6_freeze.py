"""One-use KPU G v6 package, fairness, cost and raw receipt gate."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.run_i02_kpu_cpg_v6_once import (
    MAX_MAP_BYTES, PACKAGE, SOURCE, SOURCE_ID, build_package, execute, load_package,
    preflight)


class KpuCpgV6FreezeTests(unittest.TestCase):
    def setUp(self):
        # Keep old package rehearsal distinct from the current v3 runtime.
        old = json.loads(PACKAGE.read_text())['hcl_runtime_sha256']
        for target, replacement in (
                ('scripts.run_i02_kpu_cpg_v6_once.runtime_digest', lambda: old),
                ('scripts.run_i02_kpu_cpg_v6_once.validate_runtime_amendment_v2',
                 lambda *args, **kwargs: True)):
            active = patch(target, replacement)
            active.start()
            self.addCleanup(active.stop)

    def test_source_first_freeze_and_ordinary_fairness(self):
        package = load_package()
        self.assertEqual(package, build_package())
        self.assertEqual(package['maximum_provider_calls'], 4)
        self.assertEqual(package['retries'], 0)
        self.assertEqual(package['maximum_map_bytes'], MAX_MAP_BYTES)
        self.assertEqual(package['source_url'], json.loads(SOURCE.read_text())[
            'source_url'])
        self.assertEqual(len(package['source_first_obligation_anchors']), 6)
        gate, arms = preflight(package)
        self.assertEqual(gate['status'], 'PASS_SOURCE_FIRST_CPG_ONLY')
        self.assertEqual(gate['h_ordinary_route'],
                         'DIRECT_NO_COGNITION_TREATMENT_NOT_EXECUTED')
        self.assertLess(gate['all_phase_peak_reservation_usd'],
                        package['budget_cap_usd'])
        self.assertEqual(arms['C'][-1]['content'], arms['P'][-1]['content'])
        ordinary = json.loads(arms['C'][-1]['content'])
        generic = json.loads(arms['G_map'][-1]['content'])
        self.assertEqual(generic['sources'], ordinary['sources'])
        self.assertEqual(generic['question'], ordinary['question'])

    def test_mock_four_phase_run_and_closed_budget(self):
        package = load_package()
        source = json.loads(SOURCE.read_text())['source_text']
        compact = json.dumps(dict(source_index=[dict(id='e1',
            source_id=SOURCE_ID, quote=source[1372:1452])], relations=[],
            answer_plan=[dict(operation='RETRIEVE', evidence_ids=['e1'])],
            open_questions=[]))
        answer = json.dumps(dict(answer='An answer with uncertainty.',
            source_citations=[], uncertainty='Outcome not guaranteed.',
            assumptions='No private motive inferred.'))
        count = []

        def provider(request):
            count.append(request)
            content = compact if len(count) == 3 else answer
            return dict(model='deepseek-v4-pro', created=1790698454,
                choices=[dict(finish_reason='stop',
                    message=dict(content=content))],
                usage=dict(prompt_tokens=500, completion_tokens=100,
                    prompt_cache_hit_tokens=0,
                    prompt_cache_miss_tokens=500))

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'receipt.json'
            receipt = execute(package, provider, output)
            self.assertEqual(receipt['provider_calls'], 4)
            self.assertEqual(receipt['retries'], 0)
            self.assertEqual(receipt['budget_state'],
                             'CLOSED_NO_TRANSFER_NO_RERUN')
            self.assertEqual(receipt['authorization_remaining_usd'], 0)
            self.assertEqual(len(receipt['attempts']), 4)
            self.assertTrue(all('request_raw' in a and 'response_raw' in a
                                for a in receipt['attempts']))
            self.assertEqual(json.loads(count[0]['messages'][-1]['content']),
                             json.loads(count[1]['messages'][-1]['content']))
            with self.assertRaisesRegex(ValueError, 'existing receipt'):
                execute(package, provider, output)

    def test_failed_map_stops_before_g_final_without_retry(self):
        package = load_package()
        count = []

        def provider(request):
            count.append(request)
            content = '{' if len(count) == 3 else json.dumps(dict(
                answer='a', source_citations=[], uncertainty='u', assumptions='a'))
            return dict(model='deepseek-v4-pro', created=1790698454,
                choices=[dict(finish_reason='stop',
                    message=dict(content=content))],
                usage=dict(prompt_tokens=500, completion_tokens=100,
                    prompt_cache_hit_tokens=0,
                    prompt_cache_miss_tokens=500))

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'receipt.json'
            with self.assertRaises(json.JSONDecodeError):
                execute(package, provider, output)
            saved = json.loads(output.read_text())
            self.assertEqual(len(count), 3)
            self.assertEqual(saved['provider_calls'], 3)
            self.assertEqual(saved['status'], 'FAILED_NO_RETRY')
            self.assertEqual(saved['budget_state'],
                             'CLOSED_NO_TRANSFER_NO_RERUN')


if __name__ == '__main__':
    unittest.main()
